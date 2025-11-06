"""Integration tests for swing parameter presets in the zone pipeline."""

from statistics import mean

import pytest

from bquant.analysis.zones.pipeline import (
    IndicatorConfig,
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
        indicator=IndicatorConfig(
            source="custom",
            name="macd",
            params={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            min_duration=2,
            zone_types=["bull"],
            rules={"indicator_col": "macd_hist"},
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
