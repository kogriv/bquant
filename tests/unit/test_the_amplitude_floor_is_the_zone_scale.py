"""Порог амплитуды `find_peaks`/`pivot_points` в адаптивном режиме — масштаб зоны (G48).

Замер 2026-09-06 (`research/notebooks/06_swing_scale_threshold_study.py`):

* множество глобальных точек под порогом пресета (0.006) и под порогом от масштаба зоны
  (0.0023 на `tv_xauusd_1h`) **одно и то же** — 366 = 366; слой не добавляет пивотов, он
  перестаёт выбрасывать движения между пивотами, которые ZigZag подтверждает на 99–100 %
  (±2 бара);
* метрики зон, посчитанные из этих движений, не вырождаются (`rally_to_drop_ratio` медиана
  1.10, `duration_symmetry` ровно 1.0 у 5 зон из 37 против 2 из 28 у пресета);
* потолок 65/77 — длина зоны: 10 из 12 непокрытых короче минимума баров стратегии;
* на `mt_xauusd_m15` константа пресета давала 3 зоны из 91, масштаб зоны — 67 и 72;
* пол — от данных (медианный размах бара), не константа 0.01, которая в G38 обнуляла обе
  стратегии.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.cache import ZoneAnalysisCache
from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy, SWING_PRESETS
from bquant.analysis.zones.strategies.swing.thresholds import (
    ZONE_SCALE_K,
    AdaptiveSwingStrategy,
    bar_floor,
    relative_range,
    zone_scale_amplitude,
)
from bquant.data.samples import get_sample_data


def _build(dataset, strategy, auto, scope="global"):
    builder = (
        analyze_zones(get_sample_data(dataset))
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_strategies(swing=strategy)
        .with_swing_preset("narrow_zone")
        .with_swing_scope(scope)
        .with_cache(enable=False)
        .analyze(clustering=False)
    )
    return (builder.with_auto_swing_thresholds(True) if auto else builder).build()


def _coverage(result):
    return result.metadata["swing_coverage"]["zones_with_swings"]


def test_the_zone_scale_admits_no_new_pivot():
    """Одни и те же глобальные точки под пресетом и под масштабом зоны."""
    data = get_sample_data("tv_xauusd_1h")
    zones = _build("tv_xauusd_1h", "find_peaks", auto=False).zones
    preset = FindPeaksSwingStrategy(**SWING_PRESETS["narrow_zone"].find_peaks)
    wrapper = AdaptiveSwingStrategy("find_peaks", SWING_PRESETS["narrow_zone"].find_peaks, base_deviation=0.01)
    wrapper.set_zone_scale([relative_range(z.data) for z in zones])
    assert set(map(int, preset.calculate_global(data).indices)) == set(map(int, wrapper.calculate_global(data).indices))
    assert wrapper.base_strategy.min_amplitude_pct < preset.min_amplitude_pct


@pytest.mark.parametrize("strategy, off, on", [("find_peaks", 28, 65), ("pivot_points", 38, 63)])
def test_global_coverage_on_the_hourly_sample_is_the_measured_number(strategy, off, on):
    assert _coverage(_build("tv_xauusd_1h", strategy, auto=False)) == off
    assert _coverage(_build("tv_xauusd_1h", strategy, auto=True)) == on


@pytest.mark.parametrize("strategy, off, on", [("find_peaks", 3, 67), ("pivot_points", 3, 72)])
def test_the_constant_preset_floor_switched_both_strategies_off_on_m15(strategy, off, on):
    """Второй датасет: пресетный 0.006 стоит выше медианного размаха зоны 0.0028."""
    assert _coverage(_build("mt_xauusd_m15", strategy, auto=False)) == off
    assert _coverage(_build("mt_xauusd_m15", strategy, auto=True)) == on


def test_per_zone_takes_the_scale_from_the_zone_itself():
    result = _build("tv_xauusd_1h", "find_peaks", auto=True, scope="per_zone")
    assert _coverage(result) == 30
    params = [z.features["metadata"]["swing_metrics"]["strategy_params"] for z in result.zones
              if (z.features["metadata"].get("swing_metrics") or {}).get("num_swings", 0) > 0]
    floors = {round(p["min_amplitude_pct"], 6) for p in params}
    assert len(floors) > 1, "per_zone must derive a different floor per zone, not one constant"


def test_the_floor_is_the_bar_range_not_a_constant():
    frame = pd.DataFrame({"high": [101.0] * 20, "low": [99.0] * 20, "close": [100.0] * 20})
    assert bar_floor(frame) == pytest.approx(0.02)
    # tiny zones on a frame with 2 % bars: the floor wins, and it is not 0.01
    assert zone_scale_amplitude([0.001, 0.002], 0.3, bar_floor(frame)) == pytest.approx(0.02)
    assert zone_scale_amplitude([0.1, 0.2], 0.3, bar_floor(frame)) == pytest.approx(0.045)
    with pytest.raises(ValueError, match="no zone ranges"):
        zone_scale_amplitude([], 0.3, 0.0)


def test_global_without_a_zone_scale_is_refused_not_guessed():
    wrapper = AdaptiveSwingStrategy("pivot_points", SWING_PRESETS["narrow_zone"].pivot_points, base_deviation=0.01)
    with pytest.raises(ValueError, match="set_zone_scale"):
        wrapper.calculate_global(get_sample_data("tv_xauusd_1h"))


def test_zigzag_is_untouched_and_the_applied_threshold_is_reported():
    zigzag = AdaptiveSwingStrategy("zigzag", SWING_PRESETS["narrow_zone"].zigzag, base_deviation=0.01)
    assert zigzag.amplitude_k is None
    zigzag.calculate_global(get_sample_data("tv_xauusd_1h"))
    assert "min_amplitude_pct" not in zigzag.get_metadata()["last_thresholds"]
    result = _build("tv_xauusd_1h", "find_peaks", auto=True)
    params = next(z.features["metadata"]["swing_metrics"]["strategy_params"] for z in result.zones
                  if (z.features["metadata"].get("swing_metrics") or {}).get("strategy_params"))
    assert 0 < params["min_amplitude_pct"] < 0.006
    assert set(ZONE_SCALE_K) == {"find_peaks", "pivot_points"}


def test_the_cache_schema_moved_with_the_threshold():
    assert ZoneAnalysisCache.CACHE_VERSION >= 27
