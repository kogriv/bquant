"""Tests for adaptive swing threshold utilities and pipeline integration."""

from statistics import mean

import pandas as pd
import pytest

from bquant.analysis.zones.pipeline import (
    IndicatorConfig,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.strategies.swing.thresholds import auto_swing_thresholds
from bquant.core.config import SWING_PRESETS
from bquant.data.samples import get_sample_data


def test_auto_thresholds_scale_with_range() -> None:
    narrow_base = pd.Series([100.0, 100.2, 100.3, 100.4, 100.1])
    narrow_zone = pd.DataFrame(
        {
            "high": narrow_base + 0.1,
            "low": narrow_base - 0.1,
            "close": narrow_base,
        }
    )
    wide_zone = pd.DataFrame(
        {
            "high": narrow_base + 5.0,
            "low": narrow_base - 5.0,
            "close": narrow_base + 2.5,
        }
    )

    narrow_thresholds = auto_swing_thresholds(narrow_zone, base_deviation=0.01)
    wide_thresholds = auto_swing_thresholds(wide_zone, base_deviation=0.01)

    for value in (
        narrow_thresholds.zigzag_deviation,
        narrow_thresholds.peak_prominence,
        narrow_thresholds.pivot_deviation,
        wide_thresholds.zigzag_deviation,
        wide_thresholds.peak_prominence,
        wide_thresholds.pivot_deviation,
    ):
        assert value >= 0.01

    assert wide_thresholds.zigzag_deviation > narrow_thresholds.zigzag_deviation
    assert wide_thresholds.peak_prominence > narrow_thresholds.peak_prominence
    assert wide_thresholds.pivot_deviation > narrow_thresholds.pivot_deviation


@pytest.mark.slow
def test_pipeline_auto_thresholds_matches_kpi() -> None:
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

    pipeline = ZoneAnalysisPipeline(
        config,
        enable_cache=False,
        strategy_auto_thresholds=True,
    )
    pipeline.with_swing_preset("narrow_zone")
    preset = SWING_PRESETS["narrow_zone"]

    result = pipeline.run(df)
    bull_zones = [zone for zone in result.zones if zone.type == "bull"]
    assert bull_zones, "Expected bull zones when validating swing thresholds"

    swing_counts = [
        zone.features["metadata"]["swing_metrics"]["num_swings"]
        for zone in bull_zones
    ]
    assert mean(swing_counts) > 1.0

    sample_metrics = bull_zones[0].features["metadata"]["swing_metrics"]
    assert sample_metrics["strategy_params"]["legs"] == preset.zigzag["legs"]
    assert sample_metrics["strategy_params"]["deviation"] >= 0.01
