"""Integration tests for the zone-analysis pipeline in global swing mode."""

import os

import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.pipeline import analyze_zones
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy

from tests.fixtures import create_sample_ohlcv_data
from tests.fixtures.swing_mocks import use_fake_zigzag_indicator
from unittest.mock import patch


def _build_zones_df(data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone_id": [0, 1],
            "type": ["bull", "bear"],
            "start_time": [data.index[5], data.index[25]],
            "end_time": [data.index[20], data.index[45]],
        }
    )


def test_pipeline_global_swing_scope(monkeypatch):
    data = create_sample_ohlcv_data(80)
    data.index = pd.date_range("2024-08-01", periods=len(data), freq="H")
    zones_df = _build_zones_df(data)

    pivot_timestamps = [data.index[i] for i in range(0, len(data), 10)]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    result = (
        analyze_zones(data)
        .with_cache(enable=False)
        .with_strategies(swing="zigzag")
        .with_swing_scope("global")
        .detect_zones("preloaded", zones_data=zones_df, zone_types=["any"])
        .build()
    )

    assert len(result.zones) == len(zones_df)
    context_ids = {id(zone.swing_context) for zone in result.zones}
    assert len(context_ids) == 1

    for zone in result.zones:
        swings = zone.get_zone_swings()
        assert len(swings) >= 2
        assert zone.swing_context is not None


def test_fallback_to_per_zone(monkeypatch):
    data = create_sample_ohlcv_data(60)
    data.index = pd.date_range("2024-09-01", periods=len(data), freq="H")
    zones_df = _build_zones_df(data)

    pivot_timestamps = [data.index[i] for i in range(0, len(data), 8)]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    def _raise_global(self, full_data):  # pylint: disable=unused-argument
        raise RuntimeError("forced global failure")

    monkeypatch.setattr(ZigZagSwingStrategy, "calculate_global", _raise_global, raising=False)

    with patch("bquant.analysis.zones.pipeline.logger.warning") as warning_mock:
        result = (
            analyze_zones(data)
            .with_cache(enable=False)
            .with_strategies(swing="zigzag")
            .with_swing_scope("global")
            .detect_zones("preloaded", zones_data=zones_df, zone_types=["any"])
            .build()
        )

    warning_messages = " ".join(call.args[0] for call in warning_mock.call_args_list)
    assert "falling back to per_zone mode" in warning_messages
    assert len(result.zones) == len(zones_df)
    assert all(zone.swing_context is None for zone in result.zones)

    for zone in result.zones:
        assert zone.features is not None
        metadata = zone.features.get("metadata", {})
        assert "swing_metrics" in metadata
        metrics = metadata["swing_metrics"]
        assert isinstance(metrics, dict)
        assert metrics.get("strategy_name") == "zigzag"
