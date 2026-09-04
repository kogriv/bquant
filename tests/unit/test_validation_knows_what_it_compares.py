"""Вердикт валидации обязан знать, что он сравнивает (G55).

До 2026-09-04 `ValidationSuite` сравнивал одно число по имени ключа, и этого не хватало
на вердикт трижды:

* **счётчик на окнах разной длины.** Умолчание `total_zones` на разбиении 70/30:
  стационарный процесс с одной зоной на десять баров давал 28 против 12 — «деградация
  57 %», `success=False`. И именно эти 57 % README называл правильным ответом после G39;
* **без направления.** `abs(degradation)`: метрика, выросшая вдвое на тесте, — провал;
  метрика «меньше — лучше», упавшая вдвое, — тоже провал. Нулевая база давала
  «0 %, устойчиво» при любом тестовом значении;
* **Monte Carlo.** `percentile_real` хранил `np.percentile(sims, доля)` — значение метрики,
  подписанное как ранг; `success` требовал «выше p95» для любой метрики.

И четвёртое, в пайплайне: `.analyze(validation=True)` проходил через builder, пресеты и
конфиг, анализатор писал «requested but not executed», `validation_results` оставался
`None` — неотличимо от «не просили».

Теперь метрика описывается `MetricSpec(key, direction, per_bar)`, умолчания нет,
вердикт строится по направлению, нулевая база — отказ, ранг — ранг, а пайплайн
исполняет проверку и различает три состояния в метаданных.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.validation import MetricSpec, ValidationSuite
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.pipeline import (
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.core.exceptions import AnalysisError
from bquant.data.samples import get_sample_data

RATE = MetricSpec("total_zones", direction="stable", per_bar=True)
HIGHER = MetricSpec("score", direction="higher_is_better")
LOWER = MetricSpec("score", direction="lower_is_better")
STABLE = MetricSpec("score", direction="stable")


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({"close": 2000 + np.cumsum(rng.normal(0, 2, 400))})


def one_zone_per_ten_bars(window: pd.DataFrame) -> dict:
    """Стационарный процесс: частота зон не зависит от окна."""

    return {"total_zones": float(len(window) // 10)}


def score_doubles_on_test(window: pd.DataFrame) -> dict:
    """Обучающее окно (280 баров) даёт 10, тестовое (120) — 20."""

    return {"score": 10.0 if len(window) > 200 else 20.0}


# --- AQ-005: счётчик на окнах разной длины --------------------------------------


def test_a_stationary_process_holds_out_of_sample(data):
    """28 зон на 280 барах и 12 на 120 — одна и та же частота, а не падение вдвое."""

    result = ValidationSuite().out_of_sample_test(one_zone_per_ten_bars, data, RATE)

    assert result.metadata["train_value"] == pytest.approx(0.1)
    assert result.metadata["test_value"] == pytest.approx(0.1)
    assert result.degradation_pct == pytest.approx(0.0)
    assert result.success is True


def test_a_stationary_process_holds_walk_forward(data):
    """Окна 200 против 50: без нормировки счётчик падал бы «на 75 %» в каждой итерации."""

    result = ValidationSuite().walk_forward_test(
        one_zone_per_ten_bars, data, RATE, train_window=200, test_window=50, step_size=50
    )

    assert result.degradation_pct == pytest.approx(0.0)
    assert result.success is True
    assert all(
        it["train_value"] == pytest.approx(it["test_value"])
        for it in result.metadata["iterations_detail"]
    )


def test_a_raw_count_on_unequal_windows_is_still_a_raw_count(data):
    """`per_bar=False` — сознательный выбор пользователя, и тогда 28 против 12 сравниваются как есть."""

    result = ValidationSuite().out_of_sample_test(
        one_zone_per_ten_bars, data, MetricSpec("total_zones", "stable", per_bar=False)
    )

    assert result.metadata["train_value"] == 28.0
    assert result.metadata["test_value"] == 12.0
    assert result.success is False


def test_the_metric_has_to_be_a_spec(data):
    """Голое имя ключа — не описание метрики; умолчания больше нет."""

    with pytest.raises(AnalysisError, match="MetricSpec"):
        ValidationSuite().out_of_sample_test(one_zone_per_ten_bars, data, "total_zones")

    with pytest.raises(TypeError):
        ValidationSuite().out_of_sample_test(one_zone_per_ten_bars, data)


# --- AQ-006: направление и нулевая база --------------------------------------------


def test_an_improvement_is_not_a_degradation(data):
    """Метрика выросла вдвое там, где больше — лучше: это успех с отрицательной деградацией."""

    result = ValidationSuite().out_of_sample_test(score_doubles_on_test, data, HIGHER)

    assert result.degradation_pct == pytest.approx(-100.0)
    assert result.success is True


def test_lower_is_better_reads_a_rise_as_worse_and_a_drop_as_better(data):
    doubled = ValidationSuite().out_of_sample_test(score_doubles_on_test, data, LOWER)
    assert doubled.degradation_pct == pytest.approx(100.0)
    assert doubled.success is False

    halves = lambda w: {"score": 20.0 if len(w) > 200 else 10.0}
    halved = ValidationSuite().out_of_sample_test(halves, data, LOWER)
    assert halved.degradation_pct == pytest.approx(-50.0)
    assert halved.success is True


def test_stable_fails_on_a_move_in_either_direction(data):
    up = ValidationSuite().out_of_sample_test(score_doubles_on_test, data, STABLE)
    down = ValidationSuite().out_of_sample_test(
        lambda w: {"score": 20.0 if len(w) > 200 else 10.0}, data, STABLE
    )

    assert up.success is False and down.success is False
    within = ValidationSuite().out_of_sample_test(
        lambda w: {"score": 10.0 if len(w) > 200 else 11.0}, data, STABLE
    )
    assert within.success is True


def test_a_zero_baseline_is_refused_not_called_stable(data):
    """`train=0, test=7` читалось как «0 %, устойчиво»."""

    zero_then_seven = lambda w: {"score": 0.0 if len(w) > 200 else 7.0}

    with pytest.raises(AnalysisError, match="train value is 0"):
        ValidationSuite().out_of_sample_test(zero_then_seven, data, HIGHER)


def test_zero_against_zero_is_a_measured_no_change(data):
    result = ValidationSuite().out_of_sample_test(lambda w: {"score": 0.0}, data, HIGHER)

    assert result.degradation_pct == 0.0
    assert result.success is True


def test_direction_is_rejected_when_it_is_not_one_of_the_three():
    with pytest.raises(ValueError, match="direction"):
        MetricSpec("score", direction="bigger")


# --- AQ-007: Monte Carlo -------------------------------------------------------------


def test_percentile_rank_is_a_rank_not_the_metric_value(data):
    """Стационарная метрика в середине своего распределения: ранг 50, а не значение 0.1."""

    result = ValidationSuite().monte_carlo_test(
        one_zone_per_ten_bars, data, RATE, n_simulations=20
    )

    assert result.metadata["real_value"] == pytest.approx(0.1)
    assert result.metadata["percentile_rank"] == pytest.approx(50.0)
    assert "percentile_real" not in result.metadata


def test_monte_carlo_verdict_follows_the_direction(data):
    """Реальные данные дают меньше, чем любая симуляция: успех только если меньше — лучше."""

    def loss(window: pd.DataFrame) -> dict:
        # На реальном ряде шаг — 2 пункта; `full` генерирует ряд с тем же std
        # доходностей, но метрика штрафует за отклонение от исходного ряда.
        return {"score": float(np.abs(window["close"].values - data["close"].values).sum())}

    lower = ValidationSuite().monte_carlo_test(loss, data, LOWER, n_simulations=20, shuffle_method="full")
    higher = ValidationSuite().monte_carlo_test(loss, data, HIGHER, n_simulations=20, shuffle_method="full")

    assert lower.metadata["real_value"] == 0.0
    assert lower.metadata["percentile_rank"] == pytest.approx(0.0)
    assert lower.success is True
    assert higher.success is False
    assert lower.metadata["success_rule"] == "real < p05 of simulations"


# --- direction in sensitivity analysis --------------------------------------------------


def test_sensitivity_best_follows_the_direction(data):
    scaled = lambda w, k=1.0: {"score": 10.0 * k}
    ranges = {"k": [0.5, 1.0, 2.0]}

    best_high = ValidationSuite().sensitivity_analysis(scaled, data, ranges, HIGHER)
    best_low = ValidationSuite().sensitivity_analysis(scaled, data, ranges, LOWER)
    no_best = ValidationSuite().sensitivity_analysis(scaled, data, ranges, STABLE)

    assert best_high.metadata["best_params"] == {"k": 2.0}
    assert best_low.metadata["best_params"] == {"k": 0.5}
    assert no_best.metadata["best_params"] is None
    assert no_best.metadata["stability_score"] == best_high.metadata["stability_score"]


# --- AQ-009: the pipeline flag ---------------------------------------------------------


def _builder(sample: pd.DataFrame):
    return (
        analyze_zones(sample)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
    )


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    return get_sample_data("tv_xauusd_1h")


def test_validation_true_is_executed_and_says_so(sample):
    result = _builder(sample).analyze(validation=True).build()

    assert result.metadata["validation"]["status"] == "executed"
    oos = result.validation_results["out_of_sample"]
    assert oos["validation_type"] == "out_of_sample"
    assert oos["metadata"]["metric"] == {"key": "total_zones", "direction": "stable", "per_bar": True}
    # Что сравнивалось: зоны на бар в двух окнах, а не сырые 52 против 26.
    assert oos["metadata"]["train_size"] + oos["metadata"]["test_size"] == len(sample)
    assert oos["metadata"]["train_value"] == pytest.approx(
        oos["train_metrics"]["total_zones"] / oos["metadata"]["train_size"]
    )
    assert isinstance(oos["success"], bool)
    assert result.metadata["validation"]["success"] is oos["success"]


def test_validation_false_is_recorded_as_not_requested(sample):
    result = _builder(sample).analyze(validation=False).build()

    assert result.validation_results is None
    assert result.metadata["validation"] == {"status": "not_requested"}


def test_a_validation_that_cannot_be_computed_is_recorded_as_failed(sample):
    """Не `None` без объяснения: `failed` с причиной, чтобы отличаться от «не просили»."""

    class RefusingSuite(ValidationSuite):
        def out_of_sample_test(self, *args, **kwargs):
            raise AnalysisError("no verdict on this input")

    config = ZoneAnalysisConfig(
        indicator=IndicatorSpec(
            source="custom",
            name="macd",
            parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            zone_types=["bull", "bear"],
            rules={"indicator_role": "hist"},
            strategy_name="zero_crossing",
        ),
        perform_clustering=False,
        run_validation=True,
    )
    pipeline = ZoneAnalysisPipeline(
        config,
        zone_analyzer=UniversalZoneAnalyzer(validation_suite=RefusingSuite()),
        enable_cache=False,
    )
    result = pipeline.run(sample)

    assert result.validation_results is None
    assert result.metadata["validation"]["status"] == "failed"
    assert "no verdict on this input" in result.metadata["validation"]["reason"]
