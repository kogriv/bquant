"""Признаки и статистика обязаны измерять то, что называют (G60–G63).

Четыре находки аудита, каждая воспроизведена до правки:

* AQ-012/013 — пайплайн ждал колонку `atr` от функции, которая её не считала: на
  флагманском пути `atr_normalized_return` был `None` в 77 зонах из 77; а там, где `atr`
  приносили, формула делила безразмерную доходность на ATR в единицах цены — 0.00013 при
  движении в 0.45 ATR;
* AQ-027 — без колонки индикатора «универсальный» fallback брал первую числовую колонку
  вне короткого списка: preloaded-зоны на сэмпле получали амплитуду осциллятора 87205 и
  корреляцию 0.99 по `accumulation_distribution`;
* AQ-029 — регрессия называлась `predict_*`, объясняя завершённую зону её же признаками;
  `durbin_watson` читался как атрибут, которого нет, — `None`;
* AQ-030 — KS без поправки Лиллиефорса принимал равномерную выборку; Андерсон-Дарлинг
  всегда по 5 %; `test_normality()` — «нормально, если принял хоть один»; `count` считал NaN.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.statistical import StatisticalAnalyzer, ZoneRegressionAnalyzer
# Imported under another name: pytest would otherwise collect `test_normality` as a test.
from bquant.analysis.statistical import test_normality as is_normal
from bquant.analysis.zones import analyze_zones
from bquant.data.processor import calculate_atr, calculate_true_range
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    return get_sample_data("tv_xauusd_1h")


def _macd(frame, **analyze):
    return (
        analyze_zones(frame)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .analyze(clustering=False, **analyze)
        .build()
    )


# --- G60: ATR reaches the zones, in the right units -------------------------------------


def test_the_pipeline_adds_atr_and_the_feature_is_populated(data):
    result = _macd(data)
    assert "atr" in result.data.columns
    expected = calculate_atr(result.data, 14)
    pd.testing.assert_series_equal(result.data["atr"], expected, check_names=False)
    populated = [z for z in result.zones if z.features.get("atr_normalized_return") is not None]
    assert len(populated) == len(result.zones), "the flagship path used to leave it None everywhere"


def test_atr_normalized_return_is_the_move_in_atr_units(data):
    with_atr = data.copy()
    with_atr["atr"] = 20.0
    result = _macd(with_atr)
    zone = result.zones[3]
    start, end = float(zone.data["close"].iloc[0]), float(zone.data["close"].iloc[-1])
    assert zone.features["atr_normalized_return"] == pytest.approx((end - start) / 20.0)
    assert abs(zone.features["atr_normalized_return"]) > abs(zone.features["price_return"]) * 10


def test_the_atr_period_is_a_builder_setting_and_part_of_the_cache_key(data):
    # The key must change with the period, and the builder must refuse a bad one.
    from bquant.analysis.zones.pipeline import ZoneAnalysisConfig, IndicatorSpec
    from bquant.analysis.zones.detection import ZoneDetectionConfig
    make = lambda period: ZoneAnalysisConfig(
        indicator=IndicatorSpec("custom", "macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
        zone_detection=ZoneDetectionConfig(zone_types=["bull", "bear"], rules={"indicator_role": "hist"},
                                           strategy_name="zero_crossing"),
        atr_period=period,
    )
    assert make(14).to_cache_key() != make(20).to_cache_key()
    with pytest.raises(ValueError):
        analyze_zones(data).with_atr_period(0)


def test_calculate_atr_is_the_rolling_mean_of_true_range(data):
    atr = calculate_atr(data, 5)
    assert np.isnan(atr.iloc[:4]).all()
    assert atr.iloc[10] == pytest.approx(calculate_true_range(data).iloc[6:11].mean())


# --- G61: no guessing which column is the oscillator ---------------------------------------


def test_preloaded_zones_do_not_borrow_an_oscillator_from_another_column(data):
    t = pd.to_datetime(data["time"])
    zones = pd.DataFrame({"zone_id": [0, 1], "type": ["bull", "bear"],
                          "start_time": [t.iloc[100], t.iloc[300]], "end_time": [t.iloc[140], t.iloc[330]]})
    result = (analyze_zones(data).detect_zones("preloaded", zones_data=zones)
              .with_cache(enable=False).analyze(clustering=False).build())
    for zone in result.zones:
        assert zone.features["oscillator_amplitude"] is None
        assert zone.features["correlation_price_oscillator"] is None
        assert zone.features["metadata"]["oscillator_column"] is None
        assert zone.features["metadata"].get("shape_metrics") is None


def test_the_oscillator_column_is_named_when_it_exists(data):
    result = _macd(data)
    assert result.zones[0].features["metadata"]["oscillator_column"] == "macd_12_26_9__hist"
    assert result.zones[0].features["oscillator_amplitude"] is not None


# --- G62: the regression says what it is -----------------------------------------------------


def test_the_regression_is_explanatory_and_says_so(data):
    result = _macd(data, regression=True)
    for key in ("duration", "return"):
        model = result.regression_results[key]
        assert "error" not in model
        assert model["metadata"]["kind"] == "in_sample_explanatory"
        assert model["metadata"]["feature_availability"] == "ex_post"
        dw = model["metadata"]["durbin_watson"]
        assert dw is not None and 0.0 < dw < 4.0


def test_the_predict_names_are_gone():
    analyzer = ZoneRegressionAnalyzer()
    assert hasattr(analyzer, "explain_zone_duration") and hasattr(analyzer, "explain_price_return")
    assert not hasattr(analyzer, "predict_zone_duration")
    assert not hasattr(analyzer, "predict_price_return")


# --- G63: normality tests with one semantics ---------------------------------------------------


def test_a_uniform_sample_is_not_normal_under_any_test():
    """The sample the audit measurement used: plain KS with sample-estimated
    parameters accepted it (p above 0.05), Lilliefors does not."""
    from scipy import stats
    from bquant.analysis.statistical import lilliefors_normal

    rng = np.random.default_rng(0)
    rng.normal(0, 1, 300)  # the draw that preceded it in the measurement
    uniform = pd.Series(rng.uniform(-1.7, 1.7, 300))
    # Plain KS against the normal with the sample's own parameters — standardized
    # first, because `kstest(..., args=)` itself breaks on scipy 1.18 with pandas 3.
    standardized = ((uniform - uniform.mean()) / uniform.std()).to_numpy()
    plain_ks_p = stats.kstest(standardized, "norm").pvalue
    assert plain_ks_p > 0.05, "this sample is the one plain KS lets through"

    verdicts = StatisticalAnalyzer({"alpha": 0.05}).normality_test(uniform, alpha=0.05)
    assert set(verdicts) == {"shapiro", "lilliefors", "anderson_darling"}
    stat, p_value = lilliefors_normal(uniform.to_numpy())
    assert verdicts["lilliefors"]["p_value"] == pytest.approx(p_value) and p_value < 0.01
    # The statistic is the KS distance to the normal with the sample's own parameters.
    z = np.sort(((uniform - uniform.mean()) / uniform.std(ddof=1)).to_numpy())
    assert stat == pytest.approx(stats.kstest(z, "norm").statistic)
    assert not any(v["is_normal"] for v in verdicts.values())
    assert is_normal(uniform) is False


def test_a_normal_sample_passes_and_the_helper_needs_every_test():
    rng = np.random.default_rng(1)
    normal = pd.Series(rng.normal(0, 1, 300))
    verdicts = StatisticalAnalyzer().normality_test(normal, alpha=0.05)
    assert all(v["is_normal"] for v in verdicts.values())
    assert is_normal(normal) is True


def test_anderson_darling_uses_the_critical_value_for_alpha():
    from scipy import stats
    rng = np.random.default_rng(2)
    sample = pd.Series(rng.normal(0, 1, 200))
    reference = stats.anderson(sample, dist="norm")
    for alpha, level in ((0.01, 1.0), (0.05, 5.0), (0.10, 10.0)):
        verdict = StatisticalAnalyzer().normality_test(sample, alpha=alpha)["anderson_darling"]
        idx = list(reference.significance_level).index(level)
        assert verdict["critical_value"] == pytest.approx(reference.critical_values[idx])
        assert verdict["alpha"] == alpha
    with pytest.raises(ValueError, match="critical values only for alpha"):
        StatisticalAnalyzer().normality_test(sample, alpha=0.03)


def test_descriptive_count_is_the_non_null_count():
    stats_ = StatisticalAnalyzer().descriptive_statistics(pd.Series([1.0, 2.0, np.nan, 4.0]), "x")
    assert stats_["count"] == 3
