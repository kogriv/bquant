"""Edge-case coverage for swing context slicing and aggregation."""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.models import SwingContext, SwingPoint, ZoneInfo
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy

from tests.fixtures import create_sample_ohlcv_data


def _make_swing_point(point_id: int, index: int, price: float) -> SwingPoint:
    timestamp = datetime(2024, 1, 1) + timedelta(hours=index)
    swing_type = "peak" if point_id % 2 == 0 else "trough"
    return SwingPoint(
        point_id=point_id,
        timestamp=timestamp,
        index=index,
        price=price,
        swing_type=swing_type,
        strategy_name="zigzag",
        strategy_params={"legs": 2},
    )


def _make_context(indices, prices, full_length: int | None = None) -> SwingContext:
    swing_points = [
        _make_swing_point(i, idx, price)
        for i, (idx, price) in enumerate(zip(indices, prices))
    ]
    if full_length is None:
        full_length = max(indices) + 1 if indices else 0
    return SwingContext(
        swing_points=swing_points,
        indices=np.asarray(indices, dtype=int),
        full_data_length=full_length,
        strategy_name="zigzag",
        strategy_params={"legs": 2},
    )


def _make_zone(df: pd.DataFrame, start_idx: int, end_idx: int, zone_id: int = 0) -> ZoneInfo:
    slice_df = df.iloc[start_idx : end_idx + 1]
    return ZoneInfo(
        zone_id=zone_id,
        type="bull" if zone_id % 2 == 0 else "bear",
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=slice_df.index[0].to_pydatetime(),
        end_time=slice_df.index[-1].to_pydatetime(),
        duration=len(slice_df),
        data=slice_df.copy(),
    )


def test_single_bar_zone():
    data = create_sample_ohlcv_data(100)
    data.index = pd.date_range("2024-03-01", periods=len(data), freq="H")

    context = _make_context(
        [10, 30, 50, 70, 90],
        [100.0, 100.0, 100.0, 100.0, 100.0],
        full_length=len(data),
    )

    zone = _make_zone(data, 50, 50, zone_id=1)
    swings = context.get_swings_for_zone(zone)
    assert [sp.index for sp in swings] == [30, 50, 70]

    strategy = ZigZagSwingStrategy()
    metrics = strategy.aggregate_for_zone(zone, context)
    assert metrics.num_swings == 0
    assert metrics.rally_count == 0
    assert metrics.drop_count == 0


def test_zone_without_internal_swings():
    data = create_sample_ohlcv_data(100)
    data.index = pd.date_range("2024-03-01", periods=len(data), freq="H")

    context = _make_context(
        [10, 50, 90],
        [110.0, 90.0, 130.0],
        full_length=len(data),
    )

    zone = _make_zone(data, 20, 40, zone_id=2)
    swings = context.get_swings_for_zone(zone)
    assert [sp.index for sp in swings] == [10, 50]

    strategy = ZigZagSwingStrategy()
    metrics = strategy.aggregate_for_zone(zone, context)
    assert metrics.rally_count + metrics.drop_count == 1
    assert metrics.num_swings in (0, 1)


def test_zone_at_dataset_boundaries():
    data = create_sample_ohlcv_data(100)
    data.index = pd.date_range("2024-03-01", periods=len(data), freq="H")

    context = _make_context(
        [5, 30, 50, 70, 95],
        [100.0, 120.0, 90.0, 130.0, 95.0],
        full_length=len(data),
    )

    zone_start = _make_zone(data, 0, 10, zone_id=3)
    swings_start = context.get_swings_for_zone(zone_start)
    assert [sp.index for sp in swings_start] == [5, 30]
    assert swings_start[0].index >= 0

    zone_end = _make_zone(data, 90, 99, zone_id=4)
    swings_end = context.get_swings_for_zone(zone_end)
    assert [sp.index for sp in swings_end] == [70, 95]
    assert swings_end[-1].index <= 99


def test_overlapping_zones():
    data = create_sample_ohlcv_data(120)
    data.index = pd.date_range("2024-04-01", periods=len(data), freq="H")

    context = _make_context(
        [20, 40, 60, 80],
        [100.0, 120.0, 90.0, 130.0],
        full_length=len(data),
    )

    zone_a = _make_zone(data, 20, 60, zone_id=5)
    zone_b = _make_zone(data, 40, 80, zone_id=6)

    strategy = ZigZagSwingStrategy()
    metrics_a = strategy.aggregate_for_zone(zone_a, context)
    metrics_b = strategy.aggregate_for_zone(zone_b, context)

    assert metrics_a.strategy_name == metrics_b.strategy_name == "zigzag"
    assert context.get_swings_for_zone(zone_a)[0].index == 20
    assert context.get_swings_for_zone(zone_b)[-1].index == 80


def test_zone_with_all_peaks_or_all_troughs():
    data = create_sample_ohlcv_data(80)
    data.index = pd.date_range("2024-05-01", periods=len(data), freq="H")

    context = _make_context(
        [10, 20, 30, 40],
        [90.0, 100.0, 110.0, 120.0],
        full_length=len(data),
    )

    zone = _make_zone(data, 10, 40, zone_id=7)
    strategy = ZigZagSwingStrategy()
    metrics = strategy.aggregate_for_zone(zone, context)

    assert metrics.drop_count == 0
    assert metrics.rally_count == 3
    assert metrics.rally_to_drop_ratio >= 0


def test_zone_exactly_matching_swing_boundaries():
    data = create_sample_ohlcv_data(100)
    data.index = pd.date_range("2024-06-01", periods=len(data), freq="H")

    context = _make_context(
        [10, 30, 50, 70, 90],
        [100.0, 120.0, 90.0, 130.0, 95.0],
        full_length=len(data),
    )

    zone = _make_zone(data, 30, 70, zone_id=8)
    swings = context.slice(zone.start_idx, zone.end_idx)
    assert [sp.index for sp in swings] == [10, 30, 50, 70, 90]


def test_empty_swing_context():
    data = create_sample_ohlcv_data(50)
    data.index = pd.date_range("2024-07-01", periods=len(data), freq="H")

    context = SwingContext(
        swing_points=[],
        indices=np.asarray([], dtype=int),
        full_data_length=len(data),
        strategy_name="zigzag",
        strategy_params={},
    )

    zone = _make_zone(data, 10, 20, zone_id=9)
    assert context.get_swings_for_zone(zone) == []

    strategy = ZigZagSwingStrategy()
    metrics = strategy.aggregate_for_zone(zone, context)
    assert metrics.num_swings == 0
    assert metrics.avg_rally_pct == 0.0
