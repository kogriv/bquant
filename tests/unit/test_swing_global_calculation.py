"""Unit tests covering global swing calculation workflows."""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.models import ZoneInfo, SwingContext, SwingPoint
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.analysis.zones.strategies.swing.thresholds import (
    _AdaptiveSwingStrategy,
    auto_swing_thresholds,
)

from tests.fixtures import create_sample_ohlcv_data
from tests.fixtures.swing_mocks import use_fake_zigzag_indicator


@pytest.fixture
def synthetic_data():
    """Provide deterministic OHLCV data for swing tests."""

    df = create_sample_ohlcv_data(40)
    df.index = pd.date_range("2024-01-01", periods=len(df), freq="H")
    return df


def _make_zone(df: pd.DataFrame, start: int, end: int, zone_id: int = 0) -> ZoneInfo:
    slice_df = df.iloc[start : end + 1]
    return ZoneInfo(
        zone_id=zone_id,
        type="bull" if zone_id % 2 == 0 else "bear",
        start_idx=start,
        end_idx=end,
        start_time=slice_df.index[0].to_pydatetime(),
        end_time=slice_df.index[-1].to_pydatetime(),
        duration=len(slice_df),
        data=slice_df.copy(),
    )


def test_zigzag_global_vs_isolated(monkeypatch, synthetic_data):
    """Global mode keeps additional swings compared to isolated calculation."""

    pivot_indices = [0, 5, 10, 15, 19]
    pivot_timestamps = [synthetic_data.index[i] for i in pivot_indices]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    strategy = ZigZagSwingStrategy(legs=2, deviation=0.01)
    context = strategy.calculate_global(synthetic_data)

    zone = _make_zone(synthetic_data, 5, 15, zone_id=1)
    global_metrics = strategy.aggregate_for_zone(zone, context)
    per_zone_metrics = strategy.calculate(zone.data)

    zone_swings = context.get_swings_for_zone(zone)

    assert [sp.index for sp in zone_swings] == [0, 5, 10, 15, 19]
    assert global_metrics.rally_count == 2
    assert global_metrics.drop_count == 2
    assert per_zone_metrics.rally_count == 1
    assert per_zone_metrics.drop_count == 1
    assert global_metrics.num_swings > per_zone_metrics.num_swings


def test_swing_context_slice_with_neighbors():
    """SwingContext.slice should include neighbour pivots to keep amplitudes."""

    base = datetime(2024, 1, 1)
    timestamps = [base + timedelta(hours=h) for h in range(0, 50, 10)]
    swing_points = [
        SwingPoint(
            point_id=i,
            timestamp=ts,
            index=i * 10,
            price=100.0 + i,
            swing_type="peak" if i % 2 == 0 else "trough",
        )
        for i, ts in enumerate(timestamps)
    ]
    context = SwingContext(
        swing_points=swing_points,
        indices=np.asarray([sp.index for sp in swing_points], dtype=int),
        full_data_length=100,
        strategy_name="zigzag",
        strategy_params={"legs": 2},
    )

    sliced = context.slice(20, 20)
    assert [sp.index for sp in sliced] == [10, 20, 30]


def test_adaptive_thresholds_global_mode(monkeypatch):
    """Adaptive wrapper should compute thresholds on the full dataset once."""

    data = create_sample_ohlcv_data(60)
    data.index = pd.date_range("2024-02-01", periods=len(data), freq="H")
    pivot_timestamps = [data.index[i] for i in range(0, len(data), 10)]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    adaptive = _AdaptiveSwingStrategy("zigzag", {"legs": 2, "deviation": 0.02}, base_deviation=0.01)
    context = adaptive.calculate_global(data)

    expected_thresholds = auto_swing_thresholds(data, base_deviation=0.01)
    assert adaptive._global_threshold_cache == expected_thresholds  # pylint: disable=protected-access
    assert adaptive.base_strategy.deviation == pytest.approx(expected_thresholds.zigzag_deviation)
    assert isinstance(context, SwingContext)

    zone = ZoneInfo(
        zone_id=0,
        type="bull",
        start_idx=5,
        end_idx=20,
        start_time=data.index[5].to_pydatetime(),
        end_time=data.index[20].to_pydatetime(),
        duration=16,
        data=data.iloc[5:21].copy(),
    )
    metrics = adaptive.aggregate_for_zone(zone, context)
    assert metrics.strategy_name == "zigzag"
