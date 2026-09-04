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
from tests.fixtures.swing_coverage import compare_swing_coverage
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
    data.index = pd.date_range("2024-08-01", periods=len(data), freq="h")
    zones_df = _build_zones_df(data)

    pivot_timestamps = [data.index[i] for i in range(0, len(data), 10)]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    result = (
        analyze_zones(data)
        .with_cache(enable=False)
        .with_strategies(swing="zigzag")
        .with_swing_scope("global")
        .detect_zones("preloaded", zones_data=zones_df)
        .build()
    )

    assert len(result.zones) == len(zones_df)
    context_ids = {id(zone.swing_context) for zone in result.zones}
    assert len(context_ids) == 1

    for zone in result.zones:
        swings = zone.get_zone_swings()
        assert len(swings) >= 2
        assert zone.swing_context is not None


def test_a_failed_global_pass_does_not_become_a_per_zone_result(monkeypatch):
    """A failure in the global pass stops the run instead of changing scope.

    Until G54 the pipeline caught any exception here, logged "falling back to
    per_zone mode" and went on: the caller asked for global swings and received
    per-zone ones, with nothing in the result to say so — and the result went
    into the cache under the global key. The scopes are not interchangeable
    (different visibility; for ZigZag, until G54, a different detector too).
    """
    data = create_sample_ohlcv_data(60)
    data.index = pd.date_range("2024-09-01", periods=len(data), freq="h")
    zones_df = _build_zones_df(data)

    def _raise_global(self, full_data):  # pylint: disable=unused-argument
        raise RuntimeError("forced global failure")

    monkeypatch.setattr(ZigZagSwingStrategy, "calculate_global", _raise_global, raising=False)

    with pytest.raises(RuntimeError, match=r"Global swing calculation failed.*forced global failure") as failure:
        (
            analyze_zones(data)
            .with_cache(enable=False)
            .with_strategies(swing="zigzag")
            .with_swing_scope("global")
            .detect_zones("preloaded", zones_data=zones_df)
            .build()
        )

    assert "per_zone" in str(failure.value)
    assert "with_swing_scope" in str(failure.value)

def test_global_mode_improves_swing_coverage():
    """Global mode should have higher swing coverage than per-zone mode."""

    results = compare_swing_coverage()

    assert results["global"] >= 0.70
    assert results["global"] > results["per_zone"]
    assert results["improvement_pct"] >= 20
