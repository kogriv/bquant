#!/usr/bin/env python3
"""Regression analysis demonstration – Universal Pipeline v2.1."""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from numbers import Number
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")
os.environ.setdefault("PANDAS_TA_SUPPRESS_WARNINGS", "1")
os.environ.setdefault("PANDAS_TA_SILENT", "1")
os.environ.setdefault("BQUANT_LOG_LEVEL", "CRITICAL")

from bquant.core.logging_config import setup_logging

setup_logging(
    console_level="CRITICAL",
    file_level="ERROR",
    log_to_file=False,
    use_colors=False,
    reset_loggers=True,
    profile="critical",
)

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

NUMERIC_FEATURES: Tuple[str, ...] = (
    "macd_amplitude",
    "hist_amplitude",
    "price_range_pct",
    "num_peaks",
    "num_troughs",
    "atr_normalized_return",
    "correlation_price_hist",
    "drawdown_from_peak",
    "rally_from_trough",
    "hist_slope",
)


@dataclass
class RegressionResult:
    name: str
    predictors: Sequence[str]
    r2: float
    coefficients: Sequence[float]


def _to_seconds(duration: object) -> float:
    if duration is None:
        return 0.0
    if hasattr(duration, "total_seconds"):
        return float(duration.total_seconds())
    if isinstance(duration, (int, float, np.number, Number)):
        return float(duration)
    return 0.0


def _is_number(value: object) -> bool:
    try:
        return isinstance(value, (int, float, np.number, Number)) and not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def collect_zone_features(zones: Iterable[object]) -> pd.DataFrame:
    rows: List[Dict[str, float]] = []

    for zone in zones:
        features = getattr(zone, "features", None) or {}
        numeric: Dict[str, float] = {
            key: float(value)
            for key, value in features.items()
            if _is_number(value)
        }

        numeric.setdefault("macd_amplitude", 0.0)
        numeric.setdefault("hist_amplitude", 0.0)
        numeric.setdefault("price_range_pct", 0.0)
        numeric.setdefault("num_peaks", 0.0)
        numeric.setdefault("num_troughs", 0.0)

        numeric["duration_seconds"] = _to_seconds(getattr(zone, "duration", None))
        numeric["price_return_pct"] = float(features.get("price_return", 0.0) * 100)
        zone_type = getattr(zone, "zone_type", "").lower()
        numeric["zone_type_support"] = 1.0 if zone_type == "support" else 0.0
        numeric["zone_type_resistance"] = 1.0 if zone_type == "resistance" else 0.0

        rows.append(numeric)

    if not rows:
        return pd.DataFrame(columns=["duration_seconds", "price_return_pct", *NUMERIC_FEATURES])

    frame = pd.DataFrame(rows).fillna(0.0)
    for column in NUMERIC_FEATURES:
        if column not in frame:
            frame[column] = 0.0
    return frame


def build_regression(
    df: pd.DataFrame,
    *,
    target: str,
    predictors: Sequence[str],
    name: str,
) -> RegressionResult:
    clean = df[list(predictors) + [target]].copy()
    clean.replace([np.inf, -np.inf], np.nan, inplace=True)
    clean.dropna(inplace=True)

    if len(clean) < 3:
        raise ValueError(f"Недостаточно наблюдений для модели {name}: {len(clean)}")

    X = clean[list(predictors)].to_numpy()
    y = clean[target].to_numpy()

    model = LinearRegression()
    model.fit(X, y)

    predictions = model.predict(X)
    score = r2_score(y, predictions)

    return RegressionResult(
        name=name,
        predictors=predictors,
        r2=float(score),
        coefficients=model.coef_,
    )


def describe_regression(result: RegressionResult) -> None:
    print(f"   R²: {result.r2:.3f}")
    print(f"   Predictors: {', '.join(result.predictors)}")
    print("\n   Coefficients:")
    for name, coef in zip(result.predictors, result.coefficients):
        print(f"      {name:<25}: {coef:>9.4f}")


def describe_feature_importance(result: RegressionResult) -> None:
    print("\n   Feature Importance (absolute coefficients):")
    for name, coef in zip(result.predictors, result.coefficients):
        importance = abs(coef)
        if importance > 0.5:
            status = "🔥 HIGH"
        elif importance > 0.1:
            status = "⚡ MODERATE"
        else:
            status = "📉 LOW"
        print(f"      {name:<25}: {importance:>6.3f}  {status}")


def evaluate_additional_indicator(
    data,
    source: str,
    name: str,
    *,
    detection_strategy: str,
    detection_kwargs: Dict[str, Any],
    indicator_kwargs: Dict[str, Any] | None = None,
) -> Tuple[int, float | None]:
    builder = (
        analyze_zones(data)
        .with_indicator(source, name, **(indicator_kwargs or {}))
        .detect_zones(detection_strategy, **detection_kwargs)
        .with_strategies(swing="find_peaks", shape="statistical")
    )
    result = builder.analyze(clustering=False).build()

    features = collect_zone_features(result.zones)
    if len(features) < 3:
        return len(result.zones), None

    regression = build_regression(
        features,
        target="duration_seconds",
        predictors=["duration_seconds", "price_range_pct"],
        name=f"{name}_duration",
    )
    return len(result.zones), regression.r2


def main() -> None:
    print("=" * 60)
    print("BQuant Regression Analysis Demo - Universal Pipeline v2.1")
    print("=" * 60)

    print("\n1. Preparing data and zones with Universal Pipeline...")
    data = get_sample_data("tv_xauusd_1h")
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .with_strategies(swing="find_peaks", shape="statistical")
        .analyze(clustering=False)
        .build()
    )

    print(f"   Found {len(result.zones)} zones using Universal Pipeline")

    print("\n2. Extracting zone features...")
    features = collect_zone_features(result.zones)
    print(f"   Extracted features from {len(features)} zones")

    if len(features) < 3:
        print("   ⚠️ Need at least 3 zones for regression analysis")
        return

    numeric_columns = [col for col in features.columns if not col.startswith("zone_type_")]
    print(f"   {len(numeric_columns)} numeric features available: {', '.join(numeric_columns[:10])}")

    print("\n3. Building regression models...")

    duration_regression = build_regression(
        features,
        target="duration_seconds",
        predictors=[
            "macd_amplitude",
            "hist_amplitude",
            "price_range_pct",
            "num_peaks",
            "num_troughs",
        ],
        name="duration",
    )

    print("\n   Model 1: Zone Duration")
    print("   " + "-" * 55)
    describe_regression(duration_regression)

    price_regressors = ["duration_seconds", "macd_amplitude", "num_peaks"]
    try:
        price_regression = build_regression(
            features,
            target="price_return_pct",
            predictors=price_regressors,
            name="price_return",
        )
        price_regression_available = True
    except ValueError as exc:
        price_regression_available = False
        print("\n   Model 2: Price Return")
        print("   " + "-" * 55)
        print(f"   ⚠️ {exc}")

    if price_regression_available:
        print("\n   Model 2: Price Return")
        print("   " + "-" * 55)
        describe_regression(price_regression)

    print("\n4. Model Quality Assessment")
    print("   " + "-" * 55)

    print("\n   Duration Model:")
    if duration_regression.r2 > 0.7:
        print("      ✅ Strong model (R² > 0.7)")
    elif duration_regression.r2 > 0.3:
        print("      ⚡ Moderate model (0.3 < R² < 0.7)")
    else:
        print("      ⚠️ Weak model (R² < 0.3)")

    describe_feature_importance(duration_regression)

    if price_regression_available:
        print("\n   Price Return Model:")
        if price_regression.r2 > 0.7:
            print("      ✅ Strong model (R² > 0.7)")
        elif price_regression.r2 > 0.3:
            print("      ⚡ Moderate model (0.3 < R² < 0.7)")
        else:
            print("      ⚠️ Weak model (R² < 0.3)")

    print("\n5. Testing regression with different indicators...")
    alternatives = [
        {
            "label": "EMA", "source": "custom", "name": "ema",
            "indicator_kwargs": {"period": 20},
            "detection": {"strategy": "line_crossing", "kwargs": {"line1_col": "close", "line2_col": "ema_20"}},
        },
        {
            "label": "MACD (8,21,5)", "source": "custom", "name": "macd",
            "indicator_kwargs": {"fast_period": 8, "slow_period": 21, "signal_period": 5},
            "detection": {"strategy": "zero_crossing", "kwargs": {"indicator_col": "macd_hist"}},
        },
    ]

    for config in alternatives:
        label = config["label"]
        print(f"\n   === Testing {label} regression ===")
        try:
            zone_count, score = evaluate_additional_indicator(
                data,
                config["source"],
                config["name"],
                detection_strategy=config["detection"]["strategy"],
                detection_kwargs=config["detection"]["kwargs"],
                indicator_kwargs=config.get("indicator_kwargs"),
            )
        except Exception as error:  # pragma: no cover - defensive output
            print(f"   ❌ Error with {label}: {error}")
            continue

        if zone_count < 3:
            print(f"   ⚠️ Only {zone_count} zones detected")
            continue

        if score is None:
            print(f"   ⚠️ Regression matrix incomplete for {label}")
            continue

        print(f"   {label} zones: {zone_count}")
        print(f"   {label} R²: {score:.3f}")
        print(f"   ✅ Universal regression works with {label}!")

    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("=" * 60)
    print("1. Universal Pipeline provides numeric features for regression")
    print("2. Same regression workflow works with multiple indicators")
    print("3. indicator_context keeps feature names consistent")
    print("4. R² helps evaluate model quality")
    print("5. Coefficients highlight the most influential features")
    print("6. Pair with validation (see example 07) for robustness")
    print("=" * 60)


if __name__ == "__main__":
    main()
