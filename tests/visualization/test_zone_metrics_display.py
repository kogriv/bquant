from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.models import ZoneInfo
from bquant.visualization import zones as zones_module


@pytest.fixture
def price_data() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=120, freq="H")
    close = 1800 + np.linspace(0, 24, len(index))
    df = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.2,
            "close": close,
            "volume": np.linspace(1000, 2000, len(index)),
        },
        index=index,
    )
    df["macd_hist"] = np.sin(np.linspace(0, 6, len(index))) * 0.02
    return df


def _make_zone(
    zone_id: int,
    price_data: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    indicator_columns: Iterable[str],
    features: dict | None = None,
) -> ZoneInfo:
    index = price_data.index
    zone_window = price_data.loc[index[start_idx:end_idx], list(indicator_columns)]
    return ZoneInfo(
        zone_id=zone_id,
        type="bull",
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=index[start_idx],
        end_time=index[end_idx],
        duration=end_idx - start_idx + 1,
        data=zone_window,
        features=features,
        indicator_context={"detection_indicator": "macd_hist"},
    )


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zone_detail_with_metrics_annotation(price_data: pd.DataFrame) -> None:
    features = {
        "strength": 0.92,
        "metadata": {
            "swing_metrics": {
                "num_swings": 4,
                "rally_count": 3,
                "drop_count": 1,
                "avg_rally": 0.012,
                "avg_drop": -0.007,
                "rally_to_drop_ratio": 1.55,
                "avg_rally_duration": 3.5,
                "avg_drop_duration": 2.0,
            },
            "shape_metrics": {
                "hist_skewness": 0.42,
                "hist_kurtosis": 2.3,
                "hist_mean": 0.015,
                "hist_std": 0.008,
            },
        },
    }
    zone = _make_zone(5, price_data, 20, 32, ["open", "high", "low", "close", "volume", "macd_hist"], features)

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zone_detail(
        price_data,
        zone,
        show_zone_metrics=True,
        show_zone_stats=False,
        context_bars=5,
    )

    texts = [annotation.text for annotation in fig.layout.annotations]
    metrics_text = next(text for text in texts if "📊 Swing Metrics" in text)

    assert "📊 Swing Metrics" in metrics_text
    assert "📈 Shape Metrics" in metrics_text
    assert "Type:" not in metrics_text


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zone_detail_metrics_not_available(price_data: pd.DataFrame) -> None:
    features = {"metadata": {}}
    zone = _make_zone(6, price_data, 10, 14, ["open", "high", "low", "close"], features)

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zone_detail(
        price_data,
        zone,
        show_zone_metrics=True,
        show_zone_stats=False,
        context_bars=4,
    )

    texts = [annotation.text for annotation in fig.layout.annotations]
    metrics_text = next(text for text in texts if "📊 Swing Metrics" in text)

    assert "📊 Swing Metrics" in metrics_text
    assert "Not available" in metrics_text or "No swing context" in metrics_text or "Zone too short" in metrics_text


@pytest.mark.skipif(not zones_module.PLOTLY_AVAILABLE, reason="Plotly backend unavailable")
def test_plot_zone_detail_retains_basic_stats(price_data: pd.DataFrame) -> None:
    features = {
        "strength": 0.88,
        "metadata": {
            "swing_metrics": None,
        },
    }
    zone = _make_zone(7, price_data, 30, 44, ["open", "high", "low", "close"], features)

    visualizer = zones_module.ZoneVisualizer(backend="plotly")
    fig = visualizer.plot_zone_detail(
        price_data,
        zone,
        show_zone_metrics=False,
        show_zone_stats=True,
        context_bars=6,
    )

    texts = [annotation.text for annotation in fig.layout.annotations]
    stats_text = next(text for text in texts if "Zone #" in text or "Type:" in text)

    assert "Zone #" in stats_text
    assert "bars" in stats_text

