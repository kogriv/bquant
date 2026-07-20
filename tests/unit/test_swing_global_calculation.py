"""Unit tests covering global swing calculation workflows."""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.models import ZoneInfo, SwingContext, SwingPoint
from bquant.analysis.zones.strategies.swing import (
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy,
    ZigZagSwingStrategy,
)
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


def test_zigzag_confirmation_index_causal(monkeypatch, synthetic_data):
    """confirmation_index is causal: > index, <= next pivot, None only for the last."""

    pivot_indices = [0, 5, 10, 15, 19]
    pivot_timestamps = [synthetic_data.index[i] for i in pivot_indices]
    use_fake_zigzag_indicator(monkeypatch, pivot_timestamps)

    strategy = ZigZagSwingStrategy(legs=2, deviation=0.01)
    context = strategy.calculate_global(synthetic_data)
    swings = context.swing_points

    assert len(swings) == len(pivot_indices)
    for i, sp in enumerate(swings[:-1]):
        nxt = swings[i + 1]
        assert sp.confirmation_index is not None, "non-terminal pivot must be confirmed"
        # a pivot is never known at or before its own bar, and no later than the
        # next pivot (which already exceeds the deviation threshold)
        assert sp.index < sp.confirmation_index <= nxt.index
    # the last, still-forming swing has no confirmed reversal within the data
    assert swings[-1].confirmation_index is None


def test_pivot_points_confirmation_index_fractal(synthetic_data):
    """pivot_points confirms exactly right_bars after the pivot (fixed window)."""

    strategy = PivotPointsSwingStrategy(left_bars=2, right_bars=2)
    context = strategy.calculate_global(synthetic_data)
    swings = context.swing_points

    assert len(swings) >= 2
    n = context.full_data_length
    for sp in swings:
        # the N-bar pattern completes exactly right_bars later; always causal and
        # inside the data (pivots are only detected for index <= n - right_bars - 1)
        assert sp.confirmation_index == sp.index + strategy.right_bars
        assert sp.index < sp.confirmation_index < n


def test_find_peaks_confirmation_index_causal(synthetic_data):
    """find_peaks confirmation is causal and respects the distance window."""

    strategy = FindPeaksSwingStrategy(distance=3)
    context = strategy.calculate_global(synthetic_data)
    swings = context.swing_points

    assert len(swings) >= 2
    n = context.full_data_length
    for sp in swings:
        if sp.confirmation_index is None:
            continue
        # never known at/before its own bar; never past the data end
        assert sp.index < sp.confirmation_index < n
        # distance stabilisation is a lower bound on availability
        assert sp.confirmation_index >= sp.index + strategy.distance
    # on real sample data at least one non-tail extremum must confirm
    assert any(sp.confirmation_index is not None for sp in swings)


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


@pytest.mark.parametrize(
    ("strategy_cls", "kwargs"),
    [
        (ZigZagSwingStrategy, {"legs": 3, "deviation": 0.02}),
        (FindPeaksSwingStrategy, {"prominence": 0.02, "distance": 5, "min_amplitude_pct": 0.02}),
        (PivotPointsSwingStrategy, {"left_bars": 2, "right_bars": 2, "min_amplitude_pct": 0.02}),
    ],
    ids=["zigzag", "find_peaks", "pivot_points"],
)
def test_calculate_global_handles_short_dataset(strategy_cls, kwargs):
    """All swing strategies should return empty context for datasets that are too short."""

    short_data = pd.DataFrame(
        {
            "open": [1.0, 1.1, 1.2],
            "high": [1.1, 1.2, 1.3],
            "low": [0.9, 1.0, 1.1],
            "close": [1.0, 1.1, 1.2],
        },
        index=pd.date_range("2024-03-01", periods=3, freq="H"),
    )

    strategy = strategy_cls(**kwargs)
    context = strategy.calculate_global(short_data)

    assert isinstance(context, SwingContext)
    assert len(context.swing_points) == 0
