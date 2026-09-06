"""Validation script for docs/api/analysis/statistical.md examples."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bquant.analysis import AnalysisResult
from bquant.analysis.statistical import (
    HypothesisTestSuite,
    StatisticalAnalyzer,
    ZoneRegressionAnalyzer,
    run_all_hypothesis_tests,
    run_single_hypothesis_test,
)
from bquant.analysis.validation import ValidationSuite


# ---------------------------------------------------------------------------
# Data generation (mirrors the documentation examples)
# ---------------------------------------------------------------------------

def generate_sample_zones(seed: int = 42, count: int = 120) -> list[dict]:
    rng = np.random.default_rng(seed)
    base_price = 2050.0
    zones: list[dict] = []

    for idx in range(count):
        zone_type = "bull" if idx % 2 == 0 else "bear"
        duration = int(rng.integers(5, 45))
        price_return = float(rng.normal(0.018 if zone_type == "bull" else -0.012, 0.015))
        hist_slope = float(rng.normal(0.35 if zone_type == "bull" else -0.30, 0.10))
        macd_amplitude = float(rng.normal(1.20, 0.25))
        hist_amplitude = float(abs(rng.normal(0.90, 0.20)))
        price_range_pct = float(abs(rng.normal(0.025, 0.010)))
        num_peaks = int(rng.integers(1, 5))
        num_troughs = int(rng.integers(1, 5))
        num_swings = num_peaks + num_troughs
        hist_skewness = float(rng.normal(0.0, 0.4))
        volatility_score = float(rng.normal(0.6, 0.15))
        divergence_strength = float(rng.normal(0.5, 0.2))
        correlation_price_hist = float(rng.uniform(-0.2, 0.95))
        price_return_atr = float(abs(price_return) + rng.uniform(0.004, 0.020))
        atr = float(rng.uniform(0.3, 1.5))
        start_price = float(base_price + rng.normal(0, 45) + idx * rng.normal(0.5, 0.3))

        zone = {
            "zone_id": idx,
            "zone_type": zone_type,
            "duration": duration,
            "price_return": price_return,
            "hist_slope": hist_slope,
            "macd_amplitude": macd_amplitude,
            "hist_amplitude": hist_amplitude,
            "price_range_pct": price_range_pct,
            "num_peaks": num_peaks,
            "num_troughs": num_troughs,
            "num_swings": num_swings,
            "hist_skewness": hist_skewness,
            "volatility_score": volatility_score,
            "divergence_strength": divergence_strength,
            "correlation_price_hist": correlation_price_hist,
            "price_return_atr": price_return_atr,
            "atr": atr,
            "drawdown_from_peak": float(abs(rng.normal(0.03, 0.01))),
            "rally_from_trough": float(abs(rng.normal(0.035, 0.01))),
            "start_price": start_price,
        }

        zones.append(zone)

    return zones


def generate_market_data(seed: int = 7, periods: int = 360) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0008, 0.008, periods)
    close = 2000.0 * np.cumprod(1 + returns)
    open_ = np.concatenate(([close[0]], close[:-1]))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.0005, 0.01, periods))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.0005, 0.01, periods))
    volume = rng.integers(15_000, 45_000, periods)
    indicator = pd.Series(close).rolling(5).mean().fillna(method="bfill")
    duration_proxy = rng.integers(5, 30, periods)

    dates = pd.date_range("2024-01-01", periods=periods, freq="H")
    market_data = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "indicator": indicator,
            "duration_proxy": duration_proxy,
        },
        index=dates,
    )

    return market_data


ZONES_FEATURES = generate_sample_zones()
MARKET_DATA = generate_market_data()


def analyze_for_validation(
    data: pd.DataFrame, min_duration: int = 6, min_amplitude: float = 0.004
) -> AnalysisResult:
    analyzer = StatisticalAnalyzer({"alpha": 0.05, "min_sample_size": 5})
    # Run core analysis to mirror the documentation behaviour
    analyzer.analyze(data[["close", "indicator"]])

    returns = data["close"].pct_change().dropna()
    event_count = int((returns.abs() > min_amplitude).sum())
    total_zones = max(event_count // max(min_duration, 1), 1)

    return AnalysisResult(
        analysis_type="statistical_validation",
        results={
            "total_zones": float(total_zones),
            "avg_return": float(returns.mean()),
            "volatility": float(returns.std()),
        },
        data_size=len(data),
        metadata={
            "min_duration": min_duration,
            "min_amplitude": min_amplitude,
            "event_count": event_count,
        },
    )


# ---------------------------------------------------------------------------
# Documentation scenarios
# ---------------------------------------------------------------------------

def validate_statistical_analyzer_examples() -> None:
    analyzer = StatisticalAnalyzer({"alpha": 0.05})
    series = pd.Series([1, 2, 3, 4, 5, 6], dtype=float)
    stats = analyzer.descriptive_statistics(series)
    normality = analyzer.normality_test(series)

    assert math.isclose(stats["mean"], 3.5)
    assert "shapiro" in normality

    df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 1, 2, 3, 4]})
    analyzer_small = StatisticalAnalyzer({"min_sample_size": 5})
    correlations = analyzer_small.correlation_analysis(df["a"], df["b"])
    ttest = analyzer_small.t_test(df["a"], df["b"])

    assert "pearson" in correlations
    assert "t_statistic" in ttest


def validate_hypothesis_examples() -> None:
    all_tests = run_all_hypothesis_tests(ZONES_FEATURES, alpha=0.05)
    assert all_tests["summary"]["total_tests"] >= 6

    support = run_single_hypothesis_test(
        ZONES_FEATURES,
        "support_resistance",
        price_levels=[1950.0, 2050.0, 2150.0],
    )
    assert len(support.metadata["price_levels"]) == 3

    suite = HypothesisTestSuite(alpha=0.05)
    duration = suite.test_zone_duration_hypothesis(ZONES_FEATURES)
    asymmetry = suite.test_bull_bear_asymmetry_hypothesis(ZONES_FEATURES)
    corr_drawdown = suite.test_correlation_drawdown_hypothesis(ZONES_FEATURES)
    stationarity = suite.test_zone_duration_stationarity(ZONES_FEATURES)
    auto_sr = suite.test_support_resistance_hypothesis(ZONES_FEATURES)
    manual_sr = suite.test_support_resistance_hypothesis(
        ZONES_FEATURES, price_levels=[1950.0, 2050.0, 2150.0], tolerance_pct=0.5
    )
    full_suite = suite.run_all_tests(ZONES_FEATURES)

    assert duration.metadata["long_zones_count"] > 0
    assert asymmetry.metadata["bull_zones_count"] > 0
    assert corr_drawdown.metadata["high_corr_count"] > 0
    assert stationarity.statistic is not None
    assert auto_sr.metadata["price_levels_count"] >= 1
    assert manual_sr.metadata["near_level_count"] > 0
    assert full_suite.results["summary"]["total_tests"] == len(full_suite.results["tests"])


def validate_regression_examples() -> None:
    regressor = ZoneRegressionAnalyzer()
    duration_model = regressor.predict_zone_duration(ZONES_FEATURES)
    custom_model = regressor.predict_zone_duration(
        ZONES_FEATURES,
        predictors=[
            "num_swings",
            "hist_skewness",
            "volatility_score",
            "divergence_strength",
            "price_return_atr",
        ],
    )
    return_model = regressor.predict_price_return(
        ZONES_FEATURES,
        predictors=[
            "duration",
            "macd_amplitude",
            "correlation_price_hist",
            "hist_slope",
            "num_peaks",
        ],
    )

    assert duration_model.r_squared is not None
    assert len(custom_model.coefficients) >= 2
    assert return_model.r_squared is not None


def validate_validation_suite_examples() -> None:
    validator = ValidationSuite(degradation_threshold=0.25)

    oos = validator.out_of_sample_test(
        analyze_for_validation,
        MARKET_DATA,
        train_ratio=0.7,
        metric_key="total_zones",
    )
    assert oos.metadata["split_index"] > 0

    wf = validator.walk_forward_test(
        analyze_for_validation,
        MARKET_DATA,
        train_window=120,
        test_window=60,
        step_size=60,
        metric_key="total_zones",
    )
    assert wf.metadata["iterations_count"] >= 1

    sensitivity = validator.sensitivity_analysis(
        analyze_for_validation,
        MARKET_DATA,
        param_ranges={
            "min_duration": [4, 6, 8],
            "min_amplitude": [0.003, 0.004, 0.005],
        },
        metric_key="total_zones",
    )
    assert sensitivity.metadata["stability_score"] >= 0
    assert isinstance(sensitivity.metadata["best_params"], dict)

    monte_carlo = validator.monte_carlo_test(
        analyze_for_validation,
        MARKET_DATA,
        n_simulations=32,
        metric_key="total_zones",
        shuffle_method="prices",
    )
    assert monte_carlo.metadata["successful_simulations"] >= 10


if __name__ == "__main__":
    validate_statistical_analyzer_examples()
    validate_hypothesis_examples()
    validate_regression_examples()
    validate_validation_suite_examples()

    print("All statistical documentation examples executed successfully.")
