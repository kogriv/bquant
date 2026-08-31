"""Integration tests for swing parameter presets in the zone pipeline."""

from statistics import mean

import pytest

from bquant.analysis.zones.pipeline import (
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.core.config import SWING_PRESETS
from bquant.data.samples import get_sample_data


@pytest.mark.slow
def test_narrow_zone_applies_parameters():
    df = get_sample_data("tv_xauusd_1h").set_index("time")

    config = ZoneAnalysisConfig(
        indicator=IndicatorSpec(
            source="custom",
            name="macd",
            parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            zone_types=["bull"],
            rules={"indicator_role": "hist"},
            strategy_name="zero_crossing",
        ),
        perform_clustering=False,
        n_clusters=3,
        run_regression=False,
        run_validation=False,
    )

    pipeline = ZoneAnalysisPipeline(config, enable_cache=False)
    pipeline.with_swing_preset("narrow_zone")

    preset = SWING_PRESETS["narrow_zone"]
    zigzag = pipeline.swing_strategies["zigzag"]
    assert zigzag.legs == preset.zigzag["legs"]
    assert zigzag.deviation == pytest.approx(preset.zigzag["deviation"])

    find_peaks = pipeline.swing_strategies["find_peaks"]
    assert find_peaks.prominence == pytest.approx(preset.find_peaks["prominence"])
    assert find_peaks.distance == preset.find_peaks["distance"]
    assert find_peaks.min_amplitude_pct == pytest.approx(
        preset.find_peaks["min_amplitude_pct"]
    )

    pivot_points = pipeline.swing_strategies["pivot_points"]
    assert pivot_points.min_amplitude_pct == pytest.approx(
        preset.pivot_points["min_amplitude_pct"]
    )

    result = pipeline.run(df)
    bull_zones = [zone for zone in result.zones if zone.type == "bull"]
    assert bull_zones, "Expected bull zones to be present"

    swing_counts = [
        zone.features["metadata"]["swing_metrics"]["num_swings"]
        for zone in bull_zones
    ]
    density = mean(swing_counts)
    assert density > 1.0

    sample_metrics = bull_zones[0].features["metadata"]["swing_metrics"]
    assert sample_metrics["strategy_params"]["legs"] == preset.zigzag["legs"]
    assert sample_metrics["strategy_params"]["deviation"] == pytest.approx(
        preset.zigzag["deviation"]
    )


def test_the_default_preset_is_named_for_what_it_is():
    """Умолчание — свойство набора порогов, а не его имя.

    До 0.0.10 умолчанием был пресет по имени `default`, и на типичных зонах часового
    золота две стратегии свингов из трёх не находили при нём ничего: его
    `min_amplitude_pct` — 2% цены при медианном размахе зоны 1.2% (G35). Умолчанием
    стал `narrow_zone`, а прежний набор переименован в `wide_zone` — по ширине зоны,
    под которую он откалиброван.

    Имя `default` не должно вернуться ни к какому пресету: оно называет положение в
    списке, а не свойство, и разъезжается с реальностью ровно тогда, когда положение
    меняется.
    """

    from bquant.core.config import DEFAULT_SWING_PRESET, SWING_PRESETS

    assert DEFAULT_SWING_PRESET == "narrow_zone"
    assert set(SWING_PRESETS) == {"narrow_zone", "wide_zone"}
    assert DEFAULT_SWING_PRESET in SWING_PRESETS

    assert SWING_PRESETS["wide_zone"].find_peaks["min_amplitude_pct"] == 0.02
    assert SWING_PRESETS["narrow_zone"].find_peaks["min_amplitude_pct"] == 0.006
