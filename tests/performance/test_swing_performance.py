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
def test_global_scope_reaches_the_indicator_once(monkeypatch):
    """The claim behind global swing scope, stated as a count.

    Global scope exists so the swing detector runs **once** over the dataset and
    each zone then slices the result; per-zone scope runs it once per zone. That
    is a property of the call graph, not of the clock, and it holds identically
    on a loaded machine and an idle one.

    This test replaced a wall-clock assertion (`ratio <= 1.5` between the two
    modes). That assertion was not wrong about the intent, but it was measured
    with a stopwatch inside a full test run: under load the two modes do not
    slow down proportionally, and it failed roughly every other full run while
    passing every time it was run alone. A check that fails at random teaches
    people to ignore failures, which is worse than not having it.
    """
    dataset_size = 50_000
    data = generate_synthetic_ohlcv(dataset_size, freq="min")
    pivot_timestamps = evenly_spaced_pivots(data, count=20)
    zones = _build_zones(data, dataset_size)

    # --- global: one pass over the whole frame, then slicing ------------------
    calls = use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)
    strategy = ZigZagSwingStrategy(legs=3, deviation=0.01)
    context = strategy.calculate_global(data)
    for zone in zones:
        strategy.aggregate_for_zone(zone, context)

    assert len(calls) == 1, (
        f"global scope reached the indicator {len(calls)} times for {len(zones)} "
        "zones; the whole point is that it goes once"
    )
    assert calls[0] == dataset_size
    global_bars = sum(calls)

    # --- per_zone: one pass per zone ------------------------------------------
    calls.clear()
    for zone in zones:
        strategy.calculate(zone.data)

    assert len(calls) == len(zones), (
        f"per-zone scope reached the indicator {len(calls)} times for "
        f"{len(zones)} zones"
    )
    per_zone_bars = sum(calls)

    # Bars actually handed to the detector — the work that scope decides.
    assert global_bars == dataset_size
    assert per_zone_bars == sum(zone.duration for zone in zones)


@pytest.mark.performance
@pytest.mark.slow
def test_slicing_a_zone_does_not_scale_with_the_dataset(monkeypatch):
    """Aggregation per zone must be a slice, not a re-scan.

    The counts above stay right even if `aggregate_for_zone` walked the entire
    swing list every time, so this is the part a count cannot see. It is stated
    as scaling rather than as an absolute: growing the dataset ten-fold with the
    ten times as many pivots and the same number of zones must not grow the
    aggregation time ten-fold. (An earlier draft held the pivot count fixed at
    20, which made the check vacuous: walking twenty points is cheap however
    large the frame.)

    Timing is taken as the **minimum** of three runs. Contention can only ever
    add time, so the minimum is the measurement least disturbed by whatever else
    the machine is doing.
    """
    def aggregate_time(dataset_size: int) -> float:
        data = generate_synthetic_ohlcv(dataset_size, freq="min")
        # Пивотов пропорционально размеру набора, зон — фиксировано. Именно так
        # повторный обход всего списка свингов на каждую зону становится дороже
        # вместе с данными, а срез — нет. С фиксированными 20 пивотами тест был
        # бы пустым: обойти двадцать точек дёшево при любом размере кадра.
        pivot_timestamps = evenly_spaced_pivots(data, count=dataset_size // 20)
        use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)
        zones = _build_zones(data, dataset_size, count=20)
        strategy = ZigZagSwingStrategy(legs=3, deviation=0.01)
        context = strategy.calculate_global(data)

        best = float("inf")
        for _ in range(3):
            started = time.perf_counter()
            for zone in zones:
                strategy.aggregate_for_zone(zone, context)
            best = min(best, time.perf_counter() - started)
        return best

    small = aggregate_time(10_000)
    large = aggregate_time(100_000)

    # Ten times the data and ten times the pivots, the same 20 zones: a slice
    # stays flat, a re-scan grows ten-fold. The bound is deliberately loose — it
    # is there to catch the re-scan, not to police microseconds.
    # Замер: рост 2.08x при десятикратных данных — это настоящая работа (в зону
    # попадает больше пивотов), а не повторный обход. Порог 4.0 отделяет её от
    # ~10x, которые дал бы обход всего списка на каждую зону.
    assert large <= small * 4.0, (
        f"aggregation grew from {small*1000:.2f}ms to {large*1000:.2f}ms when the "
        "dataset and the pivot count grew 10x with the zone count unchanged — "
        "that looks like a re-scan of the full swing list per zone, not a slice"
    )


def _build_zones(data, dataset_size: int, count: int = 40):
    """Evenly spaced non-overlapping zones over the synthetic frame."""
    zones = []
    zone_length = max(200, dataset_size // 30)
    for zone_id, start in enumerate(range(50, dataset_size - zone_length, zone_length)):
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
        if len(zones) >= count:
            break
    return zones
