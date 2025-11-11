from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.models import SwingContext, SwingPoint, ZoneInfo
from bquant.visualization import zones as zones_module


def _make_zone_with_context() -> ZoneInfo:
    index = pd.date_range("2024-01-01", periods=12, freq="D")
    data = pd.DataFrame({"close": np.linspace(100, 106, len(index))}, index=index)

    swing_points = [
        SwingPoint(
            point_id=0,
            timestamp=index[2],
            index=2,
            price=float(data.iloc[2]["close"]),
            swing_type="peak",
        ),
        SwingPoint(
            point_id=1,
            timestamp=index[5],
            index=5,
            price=float(data.iloc[5]["close"]),
            swing_type="trough",
        ),
    ]

    swing_context = SwingContext(
        swing_points=swing_points,
        indices=np.array([2, 5]),
        full_data_length=len(index),
        strategy_name="zigzag",
        strategy_params={"deviation": 0.05},
    )

    return ZoneInfo(
        zone_id=1,
        type="bull",
        start_idx=2,
        end_idx=5,
        start_time=index[2],
        end_time=index[5],
        duration=4,
        data=data.iloc[2:6],
        features={"metadata": {}},
        indicator_context={"detection_indicator": "close"},
        swing_context=swing_context,
    )


def test_prepare_zone_data_preserves_swing_context() -> None:
    zone = _make_zone_with_context()
    visualizer = zones_module.ZoneVisualizer()

    normalized = visualizer._prepare_zone_data([zone])

    assert len(normalized) == 1
    entry = normalized[0]
    assert entry["swing_context"] is zone.swing_context
    assert entry["original_zone"] is zone


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_add_annotation_plotly() -> None:
    import plotly.graph_objects as go  # type: ignore

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = go.Figure()

    visualizer._add_annotation(fig, text="Test<br>Annotation", position="top-left")

    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Test<br>Annotation"


def test_validate_and_get_config_unknown_param_warning() -> None:
    visualizer = zones_module.ZoneVisualizer()

    with pytest.warns(UserWarning, match="Unknown parameters"):
        value, cleaned = visualizer._validate_and_get_config(
            "show_indicators",
            explicit_value=None,
            kwargs={"unknown_param": True},
            default=True,
            allowed_kwargs={"show_indicators"},
        )

    assert value is True
    assert cleaned == {}


def test_validate_and_get_config_prefers_explicit_value() -> None:
    visualizer = zones_module.ZoneVisualizer()

    value, cleaned = visualizer._validate_and_get_config(
        "show_indicators",
        explicit_value=False,
        kwargs={"show_indicators": True},
        default=True,
        allowed_kwargs={"show_indicators"},
    )

    assert value is False
    assert cleaned == {}

