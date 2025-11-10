"""Performance and memory checks for global swing computation."""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.models import SwingContext, SwingPoint, ZoneInfo
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy

from tests.fixtures.swing_mocks import (
    evenly_spaced_pivots,
    generate_synthetic_ohlcv,
    use_fake_zigzag_indicator,
)


@pytest.mark.performance
def test_memory_consumption_estimate():
    size = 1_000
    swing_points = [
        SwingPoint(
            point_id=i,
            timestamp=datetime(2024, 1, 1) + timedelta(minutes=i),
            index=i,
            price=100.0 + i * 0.1,
            swing_type="peak" if i % 2 == 0 else "trough",
            strategy_name="zigzag",
            strategy_params={"legs": 2},
        )
        for i in range(size)
    ]

    context = SwingContext(
        swing_points=swing_points,
        indices=np.arange(size, dtype=int),
        full_data_length=size * 2,
        strategy_name="zigzag",
        strategy_params={"legs": 2},
    )

    total_bytes = (
        sys.getsizeof(context)
        + sys.getsizeof(context.indices)
        + sys.getsizeof(context.swing_points)
        + sum(sys.getsizeof(sp) for sp in swing_points)
        + sum(sys.getsizeof(sp.strategy_params) for sp in swing_points)
    )

    avg_bytes = total_bytes / size
    expected_bytes = 264
    tolerance = 0.5

    assert expected_bytes * (1 - tolerance) <= avg_bytes <= expected_bytes * (1 + tolerance)


@pytest.mark.performance
@pytest.mark.slow
def test_benchmark_global_vs_perzone(monkeypatch):
    dataset_sizes = [10_000, 50_000, 100_000]

    for dataset_size in dataset_sizes:
        data = generate_synthetic_ohlcv(dataset_size, freq="min")
        pivot_timestamps = evenly_spaced_pivots(data, count=20)
        use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

        zones = []
        zone_length = max(200, dataset_size // 30)
        step = zone_length
        zone_id = 0
        for start in range(50, dataset_size - zone_length, step):
            end = start + zone_length - 1
            zone_df = data.iloc[start : end + 1]
            zones.append(
                ZoneInfo(
                    zone_id=zone_id,
                    type="bull" if zone_id % 2 == 0 else "bear",
                    start_idx=start,
                    end_idx=end,
                    start_time=zone_df.index[0].to_pydatetime(),
                    end_time=zone_df.index[-1].to_pydatetime(),
                    duration=len(zone_df),
                    data=zone_df.copy(),
                )
            )
            zone_id += 1
            if len(zones) >= 40:
                break

        strategy = ZigZagSwingStrategy(legs=3, deviation=0.01)

        global_start = time.perf_counter()
        context = strategy.calculate_global(data)
        global_time = time.perf_counter() - global_start

        global_zone_start = time.perf_counter()
        for zone in zones:
            strategy.aggregate_for_zone(zone, context)
        global_zone_time = time.perf_counter() - global_zone_start

        per_zone_start = time.perf_counter()
        for zone in zones:
            # Per-zone workflow recalculates metrics once per zone (matching production).
            strategy.calculate(zone.data)
        per_zone_time = time.perf_counter() - per_zone_start

        ratio = (global_time + global_zone_time) / max(per_zone_time, 1e-9)
        assert ratio <= 1.5, f"Global mode too slow for {dataset_size} bars: {ratio:.2f}x"
