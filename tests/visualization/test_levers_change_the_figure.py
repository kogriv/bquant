"""Levers of the zone-visualization path must change the figure they claim to change.

Criterion 12 of the audit — "a knob that is on differs from the same knob off" — was
closed on the flagship builder (G71) and nowhere else. Measuring the visualization
path found `show_gap_lines`: the public method accepted it, threaded it one level
down, and the inner function declared it and never read it. `show_gap_lines=True`
produced a byte-identical figure while the docstring promised dashed lines at
weekend gaps. Same shape as G47, where `theme=` was accepted and ignored.

The second test pins the opposite case: a lever that legitimately does *not* obey,
so that the limit is a decision on the record rather than a silent no-op.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.visualization.utils import generate_dense_axis_labels
from bquant.visualization.zones import ZoneVisualizer


def _frame_with_gaps(sessions: int = 6, bars: int = 24) -> pd.DataFrame:
    """Hourly bars in daily sessions separated by a multi-hour gap."""
    stamps: list[pd.Timestamp] = []
    day = pd.Timestamp("2025-01-06 00:00")
    for _ in range(sessions):
        stamps.extend(pd.date_range(day, periods=bars, freq="h"))
        day += pd.Timedelta(days=2)  # the skipped day is the gap
    index = pd.DatetimeIndex(stamps)
    close = np.linspace(100.0, 110.0, len(index))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(len(index), 1000.0),
        },
        index=index,
    )


def _zones(frame: pd.DataFrame) -> list[dict]:
    return [
        {
            "zone_id": "z1",
            "type": "bull",
            "start_time": frame.index[2],
            "end_time": frame.index[20],
        }
    ]


@pytest.mark.parametrize("time_axis_mode", ["dense", "timeseries"])
def test_show_gap_lines_changes_the_figure(time_axis_mode: str) -> None:
    frame = _frame_with_gaps()
    viz = ZoneVisualizer()
    expected_gaps = len(viz._gap_boundaries(frame.index))
    assert expected_gaps > 0, "fixture carries no gaps, so the lever has nothing to draw"

    off = viz.plot_zones_on_price_chart(frame, _zones(frame), time_axis_mode=time_axis_mode)
    on = viz.plot_zones_on_price_chart(
        frame, _zones(frame), time_axis_mode=time_axis_mode, show_gap_lines=True
    )

    assert on.to_json() != off.to_json(), "show_gap_lines=True left the figure unchanged"
    assert len(on.layout.shapes) - len(off.layout.shapes) == expected_gaps


def test_a_frame_without_gaps_draws_no_lines() -> None:
    """Positive control for the check above: no gaps, no difference in shape count."""
    index = pd.date_range("2025-01-06", periods=48, freq="h")
    close = np.linspace(100.0, 105.0, len(index))
    frame = pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5, "close": close,
         "volume": np.full(len(index), 1000.0)},
        index=index,
    )
    viz = ZoneVisualizer()
    assert viz._gap_boundaries(frame.index) == []

    off = viz.plot_zones_on_price_chart(frame, _zones(frame))
    on = viz.plot_zones_on_price_chart(frame, _zones(frame), show_gap_lines=True)
    assert len(on.layout.shapes) == len(off.layout.shapes)


def test_xaxis_num_ticks_is_a_request_and_the_clamp_is_on_the_record() -> None:
    """`xaxis_num_ticks` is advisory; on a short window it cannot take effect at all.

    Pinned rather than fixed: the floor of 8 is a readability decision. What was wrong
    was not the clamp but that nothing said so — a caller passing 3 got 8 in silence.
    The docstrings now state it; this test keeps statement and behaviour together.
    """
    index = pd.date_range("2025-01-06", periods=41, freq="h")
    positions = list(range(len(index)))

    counts = {
        requested: len(generate_dense_axis_labels(list(index), positions, requested)[0])
        for requested in (3, 5, 16, 40)
    }
    assert len(set(counts.values())) == 1, f"clamp no longer collapses the range: {counts}"

    long_index = pd.date_range("2025-01-06", periods=600, freq="h")
    long_positions = list(range(len(long_index)))
    few = len(generate_dense_axis_labels(list(long_index), long_positions, 8)[0])
    many = len(generate_dense_axis_labels(list(long_index), long_positions, 20)[0])
    assert few != many, "on a long window the request must still reach the axis"
