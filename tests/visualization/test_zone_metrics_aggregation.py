from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.models import ZoneInfo
from bquant.visualization import zones as zones_module


def _make_zone(
    zone_id: int,
    zone_type: str,
    metrics: dict | None,
) -> dict:
    index = pd.date_range("2025-01-01", periods=10, freq="H")
    data = pd.DataFrame(
        {
            "open": np.linspace(100, 102, len(index)),
            "high": np.linspace(101, 103, len(index)),
            "low": np.linspace(99, 101, len(index)),
            "close": np.linspace(100, 102, len(index)),
            "volume": np.linspace(1000, 1100, len(index)),
        },
        index=index,
    )
    zone = ZoneInfo(
        zone_id=zone_id,
        type=zone_type,
        start_idx=2,
        end_idx=6,
        start_time=index[2],
        end_time=index[6],
        duration=5,
        data=data.iloc[2:7],
        features={
            "metadata": metrics or {},
        },
        indicator_context={"detection_indicator": "macd_hist"},
    )
    # normalize to dict via visualizer helper
    visualizer = zones_module.ZoneVisualizer()
    return visualizer._normalize_zone(zone)


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_aggregate_metrics_compact() -> None:
    zones = [
        _make_zone(
            1,
            "bull",
            {
                "swing_metrics": {
                    "num_swings": 4,
                    "rally_count": 3,
                    "drop_count": 1,
                    "avg_rally": 0.012,
                    "avg_drop": -0.007,
                    "rally_to_drop_ratio": 1.4,
                    "avg_rally_duration": 3.5,
                    "avg_drop_duration": 2.0,
                }
            },
        ),
        _make_zone(
            2,
            "bull",
            {
                "swing_metrics": {
                    "num_swings": 6,
                    "rally_count": 4,
                    "drop_count": 2,
                    "avg_rally": 0.015,
                    "avg_drop": -0.009,
                    "rally_to_drop_ratio": 1.6,
                    "avg_rally_duration": 4.0,
                    "avg_drop_duration": 2.3,
                }
            },
        ),
        _make_zone(
            3,
            "bear",
            {
                "swing_metrics": {
                    "num_swings": 3,
                    "rally_count": 1,
                    "drop_count": 2,
                    "avg_rally": 0.008,
                    "avg_drop": -0.012,
                    "rally_to_drop_ratio": 0.65,
                    "avg_rally_duration": 2.2,
                    "avg_drop_duration": 3.1,
                }
            },
        ),
    ]

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zones_on_price_chart(
        price_data=pd.concat([zone["data"] for zone in zones]),
        zones_data=zones,
        show_aggregate_metrics=True,
        aggregate_metrics_mode="compact",
    )

    annotations = [annotation.text for annotation in fig.layout.annotations if "📊" in annotation.text]
    assert any("📊 Bull Zones" in text and "Rally/Drop Ratio" in text for text in annotations)
    assert any("📊 Bear Zones" in text for text in annotations)


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_aggregate_metrics_full_mode() -> None:
    zones = [
        _make_zone(
            10,
            "bull",
            {
                "swing_metrics": {
                    "num_swings": 5,
                    "rally_count": 3,
                    "drop_count": 2,
                    "avg_rally": 0.010,
                    "avg_drop": -0.009,
                    "rally_to_drop_ratio": 1.2,
                    "avg_rally_duration": 3.0,
                    "avg_drop_duration": 2.4,
                }
            },
        ),
        _make_zone(
            11,
            "bull",
            {
                "swing_metrics": {
                    "num_swings": 4,
                    "rally_count": 2,
                    "drop_count": 2,
                    "avg_rally": 0.013,
                    "avg_drop": -0.010,
                    "rally_to_drop_ratio": 1.1,
                    "avg_rally_duration": 3.4,
                    "avg_drop_duration": 2.7,
                }
            },
        ),
    ]

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zones_on_price_chart(
        price_data=pd.concat([zone["data"] for zone in zones]),
        zones_data=zones,
        show_aggregate_metrics=True,
        aggregate_metrics_mode="full",
    )

    annotations = [annotation.text for annotation in fig.layout.annotations if "📊" in annotation.text]
    assert any("Avg Swing Duration" in text for text in annotations)


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_aggregate_metrics_handles_missing_data() -> None:
    zones = [
        _make_zone(21, "bull", {"swing_metrics": None}),
        _make_zone(
            22,
            "bull",
            {
                "swing_metrics": {
                    "num_swings": 0,
                    "rally_count": 0,
                    "drop_count": 0,
                    "avg_rally": None,
                    "avg_drop": None,
                }
            },
        ),
    ]

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zones_on_price_chart(
        price_data=pd.concat([zone["data"] for zone in zones]),
        zones_data=zones,
        show_aggregate_metrics=True,
        aggregate_metrics_mode="compact",
    )

    annotations = [annotation.text for annotation in fig.layout.annotations if "📊" in annotation.text]
    assert any("0/2" in text for text in annotations)

