from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.models import SwingContext, SwingPoint, ZoneInfo
from bquant.visualization import zones as zones_module


def _build_price_data() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=50, freq="H")
    close = 1800 + np.linspace(0, 10, len(index))
    df = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.9,
            "close": close,
            "volume": np.linspace(1000, 1500, len(index)),
        },
        index=index,
    )
    return df


def _make_zone_with_swing_context(zone_id: int, price_data: pd.DataFrame) -> ZoneInfo:
    index = price_data.index
    start_idx, end_idx = 10, 20
    swing_points = [
        SwingPoint(
            point_id=0,
            timestamp=index[start_idx],
            index=start_idx,
            price=float(price_data.iloc[start_idx]["close"]),
            swing_type="peak",
        ),
        SwingPoint(
            point_id=1,
            timestamp=index[start_idx + 3],
            index=start_idx + 3,
            price=float(price_data.iloc[start_idx + 3]["close"]),
            swing_type="trough",
        ),
        SwingPoint(
            point_id=2,
            timestamp=index[end_idx],
            index=end_idx,
            price=float(price_data.iloc[end_idx]["close"]),
            swing_type="peak",
        ),
    ]
    swing_context = SwingContext(
        swing_points=swing_points,
        indices=np.array([sp.index for sp in swing_points]),
        full_data_length=len(index),
        strategy_name="zigzag",
        strategy_params={"deviation": 0.05},
    )
    return ZoneInfo(
        zone_id=zone_id,
        type="bull",
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=index[start_idx],
        end_time=index[end_idx],
        duration=end_idx - start_idx + 1,
        data=price_data.iloc[start_idx:end_idx + 1],
        features={"metadata": {}},
        indicator_context={"detection_indicator": "close"},
        swing_context=swing_context,
    )


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zone_detail_with_swings_adds_traces() -> None:
    price_data = _build_price_data()
    zone = _make_zone_with_swing_context(1, price_data)

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zone_detail(
        price_data,
        zone,
        show_swings=True,
        swing_marker_size=12,
    )

    trace_names = {trace.name for trace in fig.data}
    assert "Swing Peaks" in trace_names
    assert "Swing Troughs" in trace_names


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zone_detail_swings_without_context_graceful() -> None:
    price_data = _build_price_data()
    zone = ZoneInfo(
        zone_id=2,
        type="bull",
        start_idx=5,
        end_idx=12,
        start_time=price_data.index[5],
        end_time=price_data.index[12],
        duration=8,
        data=price_data.iloc[5:13],
        features={"metadata": {}},
        indicator_context={"detection_indicator": "close"},
        swing_context=None,
    )

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zone_detail(
        price_data,
        zone,
        show_swings=True,
    )

    trace_names = {trace.name for trace in fig.data if trace.name}
    assert "Swing Peaks" not in trace_names
    assert "Swing Troughs" not in trace_names


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zones_on_price_chart_with_swings() -> None:
    price_data = _build_price_data()
    zone1 = _make_zone_with_swing_context(10, price_data)
    zone2 = _make_zone_with_swing_context(11, price_data)

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zones_on_price_chart(
        price_data,
        [zone1, zone2],
        show_swings=True,
        swing_marker_size=9,
    )

    trace_names = {trace.name for trace in fig.data if trace.name}
    assert "Swing Peaks" in trace_names
    assert "Swing Troughs" in trace_names

