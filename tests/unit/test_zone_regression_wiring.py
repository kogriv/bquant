"""The regression step must actually run, and refuse honestly when it cannot.

Four defects sat on top of each other in this path, and each hid the next.

1. `UniversalZoneAnalyzer` imported `ZoneRegressionAnalyzer` from
   `bquant.analysis.timeseries`, which does not export it — the class lives in
   `bquant.analysis.statistical.regression`. `except ImportError` swallowed the
   miss and logged "ZoneRegressionAnalyzer not available", which reads like a
   missing optional dependency. statsmodels was installed the whole time.
   Consequence: `.analyze(regression=True)` produced **no regression at all**,
   silently, for every caller.

2. With the import fixed, the default predictor list starts with
   `macd_amplitude`, which is `None` for every non-MACD zone. The model frame is
   built with `dropna()`, so one all-NaN column takes every observation with it,
   and the refusal read "Insufficient data for regression: need at least 8
   observations, got 0" — blaming the amount of data for a column that was empty
   by construction. Over RSI zones this raised and killed the whole `build()`.

3. Where predictors are constant across observations, `add_constant` finds a
   constant column already present and does not add `const`; the coefficient
   lookup then failed with a bare `KeyError` surfaced as
   "regression failed: 'const'".

4. Forcing the constant in only moves the problem: the design is rank deficient,
   `OLS` falls back to a pseudo-inverse and returns coefficients that mean
   nothing. A well-formed lie — the failure mode this project keeps digging out.

Each test below fails against the code before the fix.
"""

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.statistical.regression import ZoneRegressionAnalyzer
from bquant.analysis.zones import analyze_zones
from bquant.core.exceptions import StatisticalAnalysisError
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


# --------------------------------------------------------------------------- #
# 1. The step is wired at all
# --------------------------------------------------------------------------- #
def test_analyzer_actually_holds_a_regression_analyzer():
    """The import must resolve — not be swallowed into a warning."""
    from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer

    analyzer = UniversalZoneAnalyzer()
    assert analyzer.regression is not None, (
        "regression analyzer missing: the import was swallowed by except ImportError"
    )
    assert isinstance(analyzer.regression, ZoneRegressionAnalyzer)


def test_pipeline_produces_regression_when_asked(data):
    """`.analyze(regression=True)` must return a fitted model, not None."""
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .analyze(regression=True)
        .build()
    )

    assert result.regression_results, "regression was requested but nothing came back"
    for key in ("duration", "return"):
        model = result.regression_results[key]
        assert not isinstance(model, dict), f"{key} regression failed: {model}"
        assert model.n_observations > 0
        assert 0.0 <= model.r_squared <= 1.0


def test_regression_is_absent_only_when_not_requested(data):
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .build()
    )
    assert result.regression_results is None


# --------------------------------------------------------------------------- #
# 2. An empty predictor must not empty the sample
# --------------------------------------------------------------------------- #
def test_all_nan_predictor_is_dropped_and_named(data):
    """RSI zones have no indicator *line*, so `macd_amplitude` is empty.

    Before the fix this emptied the model frame and the build died with a
    message about the number of observations.
    """
    result = (
        analyze_zones(data)
        .with_indicator("custom", "rsi", period=14)
        .detect_zones("threshold", indicator_col="rsi_14",
                      upper_threshold=70, lower_threshold=30)
        .with_cache(enable=False)
        .analyze(regression=True)
        .build()
    )

    model = result.regression_results["duration"]
    assert not isinstance(model, dict), f"regression should have fitted, got {model}"
    assert model.n_observations > 0

    metadata = model.metadata
    assert "macd_amplitude" in metadata["empty_predictors"], (
        "an empty predictor must be reported, not silently absent"
    )
    assert "macd_amplitude" not in metadata["available_predictors"]
    assert metadata["available_predictors"], "the usable predictors must survive"


def test_every_predictor_empty_is_refused():
    """If nothing is left, say that — do not report 'insufficient data'."""
    features = [
        {"duration": 5 + i, "macd_amplitude": None, "hist_amplitude": None,
         "correlation_price_hist": None, "price_range_pct": None,
         "num_peaks": None, "num_troughs": None}
        for i in range(20)
    ]
    with pytest.raises(StatisticalAnalysisError, match="empty for this zone set"):
        ZoneRegressionAnalyzer().predict_zone_duration(features)


# --------------------------------------------------------------------------- #
# 3 & 4. A design that cannot identify coefficients must be refused
# --------------------------------------------------------------------------- #
def _constant_features(n=15):
    """n identical observations — the shape a duplicated fixture produces."""
    return [
        {"duration": 10, "macd_amplitude": 1.0, "hist_amplitude": 2.0,
         "correlation_price_hist": 0.5, "price_range_pct": 1.5,
         "num_peaks": 2, "num_troughs": 2}
        for _ in range(n)
    ]


def test_rank_deficient_design_is_refused_not_fitted():
    with pytest.raises(StatisticalAnalysisError, match="rank deficient"):
        ZoneRegressionAnalyzer().predict_zone_duration(_constant_features())


def test_refusal_names_the_constant_predictors():
    with pytest.raises(StatisticalAnalysisError) as exc:
        ZoneRegressionAnalyzer().predict_price_return([
            {**f, "price_return": 0.01} for f in _constant_features()
        ])
    message = str(exc.value)
    assert "constant across all observations" in message, message


def test_refusal_is_not_a_bare_keyerror():
    """The old failure surfaced as `regression failed: 'const'`."""
    with pytest.raises(StatisticalAnalysisError) as exc:
        ZoneRegressionAnalyzer().predict_zone_duration(_constant_features())
    assert "'const'" not in str(exc.value)


def test_a_refused_regression_does_not_kill_the_analysis(data):
    """The step is optional; its failure must be reported, not fatal."""
    from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
    from bquant.analysis.zones.models import ZoneInfo

    zones = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .build()
    ).zones

    # Same zone repeated: enough rows to pass the >10 gate, no variation at all.
    duplicated = [zones[0]] * 12
    result = UniversalZoneAnalyzer().analyze_zones(
        duplicated, data, run_regression=True
    )

    assert result.statistics, "the rest of the analysis must still be produced"
    assert isinstance(result.regression_results["duration"], dict)
    assert "error" in result.regression_results["duration"]


# --------------------------------------------------------------------------- #
# The helper itself
# --------------------------------------------------------------------------- #
def test_usable_predictors_splits_and_keeps_order():
    from bquant.analysis.statistical.regression import _usable_predictors
    from bquant.core.logging_config import get_logger

    df = pd.DataFrame({"a": [1.0, np.nan], "b": [np.nan, np.nan], "c": [3.0, 4.0]})
    usable, empty = _usable_predictors(df, ["a", "b", "c"], get_logger(__name__))
    assert usable == ["a", "c"]
    assert empty == ["b"]
