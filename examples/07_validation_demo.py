#!/usr/bin/env python3
"""Model validation demonstration – Universal Pipeline v2.1."""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")
os.environ.setdefault("BQUANT_LOG_LEVEL", "CRITICAL")
os.environ.setdefault("PANDAS_TA_SUPPRESS_WARNINGS", "1")
os.environ.setdefault("PANDAS_TA_SILENT", "1")
os.environ.setdefault("BQUANT_CACHE_DISABLED", "1")

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

NUMERIC_FEATURE_KEYS: Tuple[str, ...] = (
    "macd_amplitude",
    "hist_amplitude",
    "price_range_pct",
    "atr_normalized_return",
    "correlation_price_hist",
    "num_peaks",
    "num_troughs",
    "drawdown_from_peak",
    "rally_from_trough",
    "hist_slope",
)

PREDICTORS: Tuple[str, ...] = (
    "duration_minutes",
    "num_swings",
    "hist_amplitude",
    "price_range_pct",
    "abs_price_return_pct",
)


@dataclass
class LinearModel:
    coefficients: Tuple[float, ...]
    intercept: float
    r2: float


@dataclass
class OutOfSampleMetrics:
    train_r2: float
    test_r2: float
    degradation_pct: float
    coefficients: Tuple[float, ...]


@dataclass
class WalkForwardMetrics:
    windows: int
    mean_r2: float
    std_r2: float
    min_r2: float
    max_r2: float
    stability: float


@dataclass
class MonteCarloMetrics:
    real_r2: float
    synthetic_mean: float
    synthetic_std: float
    p_value: float


@dataclass
class IndicatorEvaluation:
    label: str
    zone_count: int
    r2: float | None


INDICATOR_VARIANTS: Tuple[Dict[str, object], ...] = (
    {
        "label": "MACD (12,26,9)",
        "source": "custom",
        "name": "macd",
        "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "detection": {"strategy": "zero_crossing", "kwargs": {"indicator_col": "macd_hist"}},
    },
    {
        "label": "EMA (20) vs Close",
        "source": "custom",
        "name": "ema",
        "params": {"period": 20},
        "detection": {
            "strategy": "line_crossing",
            "kwargs": {"line1_col": "close", "line2_col": "ema_20"},
        },
    },
    {
        "label": "SMA (50) vs Close",
        "source": "custom",
        "name": "sma",
        "params": {"period": 50},
        "detection": {
            "strategy": "line_crossing",
            "kwargs": {"line1_col": "close", "line2_col": "sma_50"},
        },
    },
)


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert arbitrary value to float without raising exceptions."""

    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result) or math.isinf(result):
        return default
    return result


def summarize_zone(zone: object) -> Dict[str, float]:
    """Extract numeric features from ZoneInfo with deterministic fallbacks."""

    features = dict(getattr(zone, "features", {}) or {})
    metadata = features.pop("metadata", {}) or {}

    summary: Dict[str, float] = {}
    duration_bars = _safe_float(getattr(zone, "duration", None))
    if duration_bars <= 0.0 and isinstance(metadata, dict):
        duration_bars = _safe_float(metadata.get("data_points"), 0.0)
    summary["duration_bars"] = duration_bars
    summary["duration_minutes"] = duration_bars * 60.0

    price_return = _safe_float(features.get("price_return"), 0.0)
    summary["price_return_pct"] = price_return * 100.0
    summary["abs_price_return_pct"] = abs(summary["price_return_pct"])

    zone_type = str(getattr(zone, "type", "")).lower()
    summary["is_bullish"] = 1.0 if zone_type in {"bull", "bullish", "support"} else 0.0
    summary["is_bearish"] = 1.0 if zone_type in {"bear", "bearish", "resistance"} else 0.0

    swing_metrics = metadata.get("swing_metrics") if isinstance(metadata, dict) else {}
    if not isinstance(swing_metrics, dict):
        swing_metrics = {}

    summary["num_swings"] = _safe_float(swing_metrics.get("num_swings"), 0.0)
    summary["avg_rally_pct"] = _safe_float(swing_metrics.get("avg_rally_pct"), 0.0)
    summary["avg_drop_pct"] = _safe_float(swing_metrics.get("avg_drop_pct"), 0.0)
    summary["avg_rally_speed"] = _safe_float(
        swing_metrics.get("avg_rally_speed_pct_per_bar"), 0.0
    )
    summary["avg_drop_speed"] = _safe_float(
        swing_metrics.get("avg_drop_speed_pct_per_bar"), 0.0
    )

    for key in NUMERIC_FEATURE_KEYS:
        summary[key] = _safe_float(features.get(key), 0.0)

    return summary


def collect_zone_features(zones: Iterable[object]) -> List[Dict[str, float]]:
    """Build a normalized feature matrix for downstream validation."""

    prepared: List[Dict[str, float]] = []
    for zone in zones:
        summary = summarize_zone(zone)
        if summary:
            prepared.append(summary)
    return prepared


def run_pipeline(
    data,
    *,
    source: str,
    name: str,
    params: Dict[str, object],
    detection_strategy: str,
    detection_kwargs: Dict[str, object],
):
    """Build zones with Universal Pipeline for the provided indicator."""

    builder = analyze_zones(data)
    builder = builder.with_indicator(source, name, **params)
    builder = builder.detect_zones(detection_strategy, **detection_kwargs)
    builder = builder.with_strategies(swing="find_peaks", shape="statistical")
    return builder.analyze(clustering=False).build()


def build_matrix(rows: Sequence[Dict[str, float]], columns: Sequence[str]) -> np.ndarray:
    matrix = np.zeros((len(rows), len(columns)), dtype=float)
    for idx, row in enumerate(rows):
        matrix[idx, :] = [row.get(column, 0.0) for column in columns]
    return matrix


def predict(model: LinearModel, matrix: np.ndarray) -> np.ndarray:
    coeffs = np.asarray(model.coefficients, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, coeffs.size)
    return matrix @ coeffs + model.intercept


def run_linear_regression(X: np.ndarray, y: np.ndarray) -> LinearModel | None:
    if len(X) < 3:
        return None

    if X.ndim == 1:
        X = X.reshape(-1, 1)

    ones = np.ones((X.shape[0], 1), dtype=float)
    design = np.hstack([X, ones])

    try:
        solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    except np.linalg.LinAlgError:
        return None

    predictions = design @ solution
    mean_y = float(np.mean(y))
    ss_tot = float(np.sum((y - mean_y) ** 2))
    if ss_tot <= 0.0:
        r2 = 0.0
    else:
        ss_res = float(np.sum((y - predictions) ** 2))
        r2 = max(0.0, 1.0 - ss_res / ss_tot)

    coefficients = tuple(float(value) for value in solution[:-1])
    intercept = float(solution[-1])
    return LinearModel(coefficients=coefficients, intercept=intercept, r2=r2)


def evaluate_out_of_sample(features: Sequence[Dict[str, float]]) -> OutOfSampleMetrics | None:
    if len(features) < 6:
        return None

    split_idx = max(3, int(len(features) * 0.7))
    train = features[:split_idx]
    test = features[split_idx:]
    if len(test) < 2:
        return None

    X_train = build_matrix(train, PREDICTORS)
    y_train = np.array([row["duration_minutes"] for row in train], dtype=float)
    model = run_linear_regression(X_train, y_train)
    if model is None:
        return None

    X_test = build_matrix(test, PREDICTORS)
    y_test = np.array([row["duration_minutes"] for row in test], dtype=float)
    y_pred = predict(model, X_test)

    mean_y = float(np.mean(y_test))
    ss_tot = float(np.sum((y_test - mean_y) ** 2))
    if ss_tot <= 0.0:
        test_r2 = 0.0
    else:
        ss_res = float(np.sum((y_test - y_pred) ** 2))
        test_r2 = max(0.0, 1.0 - ss_res / ss_tot)

    degradation = 0.0
    if model.r2 > 0.0:
        degradation = max(0.0, (model.r2 - test_r2) / model.r2 * 100.0)

    return OutOfSampleMetrics(
        train_r2=float(model.r2),
        test_r2=float(test_r2),
        degradation_pct=float(degradation),
        coefficients=model.coefficients,
    )


def evaluate_walk_forward(
    features: Sequence[Dict[str, float]],
    *,
    window: int = 18,
    step: int = 6,
) -> WalkForwardMetrics | None:
    if len(features) < window:
        return None

    scores: List[float] = []
    for start in range(0, len(features) - window + 1, step):
        block = features[start : start + window]
        matrix = build_matrix(block, PREDICTORS[:3])
        target = np.array([row["duration_minutes"] for row in block], dtype=float)
        model = run_linear_regression(matrix, target)
        if model is not None:
            scores.append(model.r2)

    if not scores:
        return None

    scores_array = np.array(scores, dtype=float)
    mean_r2 = float(scores_array.mean())
    std_r2 = float(scores_array.std())
    min_r2 = float(scores_array.min())
    max_r2 = float(scores_array.max())
    stability = float(1.0 - (std_r2 / mean_r2)) if mean_r2 > 0 else 0.0

    return WalkForwardMetrics(
        windows=len(scores),
        mean_r2=mean_r2,
        std_r2=std_r2,
        min_r2=min_r2,
        max_r2=max_r2,
        stability=stability,
    )


def evaluate_indicator_scenarios(data) -> List[IndicatorEvaluation]:
    evaluations: List[IndicatorEvaluation] = []

    for spec in INDICATOR_VARIANTS:
        label = str(spec["label"])
        try:
            detection = spec["detection"]
            result = run_pipeline(
                data,
                source=str(spec["source"]),
                name=str(spec["name"]),
                params=dict(spec["params"]),
                detection_strategy=str(detection["strategy"]),
                detection_kwargs=dict(detection["kwargs"]),
            )
            zones = list(result.zones)
            features = collect_zone_features(zones)
            r2_value: float | None = None
            if len(features) >= 4:
                matrix = build_matrix(features, PREDICTORS[:3])
                target = np.array([row["duration_minutes"] for row in features], dtype=float)
                model = run_linear_regression(matrix, target)
                if model is not None:
                    r2_value = float(model.r2)
            evaluations.append(IndicatorEvaluation(label=label, zone_count=len(zones), r2=r2_value))
        except Exception as exc:  # noqa: BLE001 - демонстрация отказоустойчивости
            print(f"   {label}: ошибка – {exc}")
    return evaluations


def evaluate_monte_carlo(
    features: Sequence[Dict[str, float]],
    *,
    iterations: int = 48,
) -> MonteCarloMetrics | None:
    if len(features) < 10:
        return None

    matrix = build_matrix(features, PREDICTORS[:3])
    target = np.array([row["duration_minutes"] for row in features], dtype=float)

    base_model = run_linear_regression(matrix, target)
    if base_model is None:
        return None

    rng = np.random.default_rng(42)
    synthetic_scores: List[float] = []

    for _ in range(iterations):
        shuffled = rng.permutation(target)
        model = run_linear_regression(matrix, shuffled)
        if model is not None:
            synthetic_scores.append(model.r2)

    if not synthetic_scores:
        return None

    synthetic_array = np.array(synthetic_scores, dtype=float)
    synthetic_mean = float(synthetic_array.mean())
    synthetic_std = float(synthetic_array.std())
    real_r2 = float(base_model.r2)
    p_value = float(np.mean(synthetic_array >= real_r2))

    return MonteCarloMetrics(
        real_r2=real_r2,
        synthetic_mean=synthetic_mean,
        synthetic_std=synthetic_std,
        p_value=p_value,
    )


def status_icon(condition: bool) -> str:
    return "✅" if condition else "⚠️"


def print_best_practices() -> None:
    print("Validation Best Practices:")
    print("1. Минимум – проверка Out-of-Sample на отложенной выборке")
    print("2. Walk-forward контроль устойчивости для временных рядов")
    print("3. Проверяйте чувствительность к наборам индикаторов")
    print("4. Монте-Карло отделяет реальные закономерности от шума")
    print("5. Универсальный Pipeline гарантирует одинаковые фичи")
    print("6. indicator_context удерживает названия колонок стабильными")
    print("7. Фиксируйте критерии готовности (degradation, stability, p-value)")


def print_resources(resources: Sequence[str]) -> None:
    print("Дополнительные материалы:")
    for relative in resources:
        target = PROJECT_ROOT / relative
        exists = target.exists()
        print(f" - {status_icon(exists)} {relative}")


def main() -> None:
    print("=" * 70)
    print("BQuant Model Validation Demo – Universal Pipeline v2.1")
    print("=" * 70)

    data = get_sample_data("tv_xauusd_1h")
    print("\n1. Подготовка данных и базовых зон")
    print("   --------------------------------")
    print(f"   Строк: {len(data)}, колонки: {list(data.columns[:6])}…")

    base_result = run_pipeline(
        data,
        source="custom",
        name="macd",
        params={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        detection_strategy="zero_crossing",
        detection_kwargs={"indicator_col": "macd_hist"},
    )
    zones = list(base_result.zones)
    print(f"   Найдено зон: {len(zones)}")

    features = collect_zone_features(zones)
    print(f"   Сформировано строк признаков: {len(features)}")

    out_of_sample = evaluate_out_of_sample(features)
    print("\n2. Out-of-Sample проверка (70/30)")
    print("   --------------------------------")
    if out_of_sample is None:
        print("   ⚠️ Недостаточно данных для разделения train/test")
    else:
        print(f"   Train R²: {out_of_sample.train_r2:.3f}")
        print(f"   Test R²: {out_of_sample.test_r2:.3f}")
        print(f"   Degradation: {out_of_sample.degradation_pct:.1f}%")
        coeff_names = ", ".join(f"{name}: {coef:.3f}" for name, coef in zip(PREDICTORS, out_of_sample.coefficients))
        print(f"   Коэффициенты: {coeff_names}")

    walk_forward = evaluate_walk_forward(features)
    print("\n3. Walk-forward проверка (rolling window)")
    print("   ---------------------------------------")
    if walk_forward is None:
        print("   ⚠️ Недостаточно окон для оценки устойчивости")
    else:
        print(f"   Окон: {walk_forward.windows}")
        print(f"   Mean R²: {walk_forward.mean_r2:.3f}")
        print(f"   Std R²: {walk_forward.std_r2:.3f}")
        print(f"   Min/Max R²: {walk_forward.min_r2:.3f}/{walk_forward.max_r2:.3f}")
        print(f"   Stability score: {walk_forward.stability:.3f}")

    print("\n4. Чувствительность к индикаторам")
    print("   --------------------------------")
    indicator_evals = evaluate_indicator_scenarios(data)
    for evaluation in indicator_evals:
        r2_part = f", R²: {evaluation.r2:.3f}" if evaluation.r2 is not None else ", R²: недоступен"
        print(f"   {evaluation.label}: зон={evaluation.zone_count}{r2_part}")

    monte_carlo = evaluate_monte_carlo(features)
    print("\n5. Монте-Карло тест (перестановки)")
    print("   --------------------------------")
    if monte_carlo is None:
        print("   ⚠️ Недостаточно данных для перестановочных тестов")
    else:
        print(f"   Real R²: {monte_carlo.real_r2:.3f}")
        print(f"   Synthetic mean R²: {monte_carlo.synthetic_mean:.3f}")
        print(f"   Synthetic std R²: {monte_carlo.synthetic_std:.3f}")
        print(f"   P-value: {monte_carlo.p_value:.4f}")

    print("\n6. Итоговая оценка готовности")
    print("   --------------------------------")
    criteria = []
    if out_of_sample is not None:
        criteria.append(("Out-of-Sample degradation < 20%", out_of_sample.degradation_pct < 20))
    if walk_forward is not None:
        criteria.append(("Walk-forward stability > 0.6", walk_forward.stability > 0.6))
    if indicator_evals:
        valid = [item for item in indicator_evals if item.r2 is not None]
        if valid:
            spread = max(item.r2 for item in valid) - min(item.r2 for item in valid)
            criteria.append(("Индикаторы дают схожий результат", spread < 0.3))
    if monte_carlo is not None:
        criteria.append(("P-value < 0.05", monte_carlo.p_value < 0.05))

    passed = sum(1 for _, ok in criteria if ok)
    total = len(criteria)
    print(f"   Пройдено критериев: {passed}/{total}")
    for label, ok in criteria:
        print(f"   {status_icon(ok)} {label}")

    print("\n7. Рекомендации и ссылки")
    print("   --------------------------------")
    print_best_practices()
    print()
    print_resources(
        (
            "docs/api/analysis/zones.md",
            "docs/examples/README.md",
            "examples/02a_universal_zones.py",
        )
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
