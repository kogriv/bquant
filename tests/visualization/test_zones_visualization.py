"""Tests for zone visualization routines."""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.models import ZoneAnalysisResult, ZoneInfo
from bquant.visualization import zones as zones_module

AVAILABLE_BACKENDS: List[str] = []
if getattr(zones_module, "PLOTLY_AVAILABLE", False):
    AVAILABLE_BACKENDS.append("plotly")
if getattr(zones_module, "MATPLOTLIB_AVAILABLE", False):
    AVAILABLE_BACKENDS.append("matplotlib")

if not AVAILABLE_BACKENDS:
    pytest.skip("No visualization backend available for zone charts", allow_module_level=True)


@pytest.fixture
def price_data() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=80, freq="D")
    close = 100 + np.linspace(0, 6, len(index))
    open_ = close - 0.2
    high = close + 1.1
    low = close - 1.3
    volume = np.linspace(1000, 2000, len(index))

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )

    df["ema_fast"] = pd.Series(close, index=index).ewm(span=5, adjust=False).mean()
    df["ema_slow"] = pd.Series(close, index=index).ewm(span=12, adjust=False).mean()
    df["momentum"] = df["close"] - df["ema_slow"]
    df["trend_strength"] = df["ema_fast"] - df["ema_slow"]
    return df


def _extract_indicator_names(fig, backend: str) -> Iterable[str]:
    if backend == "plotly":
        import plotly.graph_objects as go  # type: ignore

        return [trace.name for trace in fig.data if isinstance(trace, go.Scatter)]

    import matplotlib.pyplot as plt  # type: ignore

    ax = fig.axes[0]
    names = [
        line.get_label()
        for line in ax.get_lines()
        if line.get_label() not in {"Close"}
    ]
    plt.close(fig)
    return names


@pytest.mark.parametrize("backend", AVAILABLE_BACKENDS)
def test_plot_zone_detail_uses_indicator_metadata(price_data: pd.DataFrame, backend: str) -> None:
    index = price_data.index
    start_idx, end_idx = 10, 22
    zone_window = price_data.loc[index[start_idx - 2] : index[end_idx + 2], ["ema_fast", "momentum"]]

    zone = ZoneInfo(
        zone_id=1,
        type="bull",
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=index[start_idx],
        end_time=index[end_idx],
        duration=end_idx - start_idx + 1,
        data=zone_window,
        features={"indicator_columns": ["ema_fast"], "strength": 1.25},
        indicator_context={"detection_indicator": "ema_fast", "signal_line": "momentum"},
    )

    visualizer = zones_module.ZoneVisualizer(backend=backend)
    fig = visualizer.plot_zone_detail(price_data, zone, context_bars=5)

    indicator_names = set(_extract_indicator_names(fig, backend))
    assert indicator_names == {"ema_fast", "momentum"}


@pytest.mark.parametrize("backend", AVAILABLE_BACKENDS)
def test_plot_zone_detail_auto_detects_from_zone_data(price_data: pd.DataFrame, backend: str) -> None:
    index = price_data.index
    start_idx, end_idx = 25, 36
    zone_window = price_data.loc[index[start_idx - 1] : index[end_idx + 1], ["ema_slow", "trend_strength"]]

    zone = ZoneInfo(
        zone_id=7,
        type="bear",
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=index[start_idx],
        end_time=index[end_idx],
        duration=end_idx - start_idx + 1,
        data=zone_window,
        features=None,
        indicator_context=None,
    )

    visualizer = zones_module.ZoneVisualizer(backend=backend)
    fig = visualizer.plot_zone_detail(price_data, zone, context_bars=3)

    indicator_names = set(_extract_indicator_names(fig, backend))
    assert indicator_names == {"ema_slow", "trend_strength"}


@pytest.mark.parametrize("backend", AVAILABLE_BACKENDS)
def test_plot_zones_comparison_filters_and_limits(price_data: pd.DataFrame, backend: str) -> None:
    index = price_data.index
    zones = [
        {
            "zone_id": 1,
            "type": "bull",
            "start_idx": 5,
            "end_idx": 12,
            "start_time": index[5],
            "end_time": index[12],
            "duration": 8,
            "data": price_data.loc[index[4] : index[13], ["ema_fast", "momentum"]],
            "features": {"indicator_columns": ["ema_fast"]},
            "indicator_context": {"signal_line": "momentum"},
        },
        {
            "zone_id": 2,
            "type": "bear",
            "start_idx": 18,
            "end_idx": 24,
            "start_time": index[18],
            "end_time": index[24],
            "duration": 7,
            "data": price_data.loc[index[17] : index[25], ["ema_slow", "trend_strength"]],
            "features": {"indicator_columns": ["ema_slow"]},
            "indicator_context": {"indicator_columns": ["trend_strength"]},
        },
        {
            "zone_id": 3,
            "type": "bull",
            "start_idx": 45,
            "end_idx": 50,
            "start_time": index[45],
            "end_time": index[50],
            "duration": 6,
            "data": price_data.loc[index[44] : index[51], ["ema_fast"]],
            "features": None,
            "indicator_context": None,
        },
    ]

    date_range = (index[0], index[30])

    visualizer = zones_module.ZoneVisualizer(backend=backend)
    fig = visualizer.plot_zones_comparison(
        price_data,
        zones,
        max_zones=1,
        date_range=date_range,
    )

    indicator_names = set(_extract_indicator_names(fig, backend))
    assert indicator_names == {"1 · ema_fast", "1 · momentum"}


def _make_zone_info(
    zone_id: int,
    start_idx: int,
    end_idx: int,
    price_data: pd.DataFrame,
    columns: Iterable[str],
    zone_type: str = "bull",
    features: dict | None = None,
    indicator_context: dict | None = None,
) -> ZoneInfo:
    index = price_data.index
    zone_window = price_data.loc[index[max(0, start_idx - 2)] : index[min(len(index) - 1, end_idx + 2)], list(columns)]
    return ZoneInfo(
        zone_id=zone_id,
        type=zone_type,
        start_idx=start_idx,
        end_idx=end_idx,
        start_time=index[start_idx],
        end_time=index[end_idx],
        duration=end_idx - start_idx + 1,
        data=zone_window,
        features=features,
        indicator_context=indicator_context,
    )


def test_zone_analysis_result_visualize_respects_backend_and_kwargs(
    price_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_backend = "matplotlib" if "matplotlib" in AVAILABLE_BACKENDS else AVAILABLE_BACKENDS[0]

    zones = [
        _make_zone_info(
            1,
            6,
            14,
            price_data,
            columns=["ema_fast", "momentum"],
            zone_type="bull",
            features={"indicator_columns": ["ema_fast"], "strength": 1.4},
            indicator_context={"detection_indicator": "ema_fast", "signal_line": "momentum"},
        ),
        _make_zone_info(
            2,
            20,
            26,
            price_data,
            columns=["ema_slow", "trend_strength"],
            zone_type="bear",
            features={"indicator_columns": ["ema_slow"], "indicators": ["trend_strength"]},
            indicator_context=None,
        ),
        _make_zone_info(
            3,
            42,
            48,
            price_data,
            columns=["ema_fast"],
            zone_type="bull",
            features=None,
            indicator_context=None,
        ),
    ]

    result = ZoneAnalysisResult(
        zones=zones,
        statistics={"count": len(zones)},
        hypothesis_tests={},
        data=price_data,
        metadata={"source": "unit-test"},
    )

    init_kwargs: list[dict] = []
    original_init = zones_module.ZoneVisualizer.__init__

    def tracking_init(self, *args, **kwargs):
        init_kwargs.append(dict(kwargs))
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(zones_module.ZoneVisualizer, "__init__", tracking_init)

    detail_fig = result.visualize(
        mode="detail",
        zone_id=1,
        backend=target_backend,
        visualizer_config={"width": 900},
    )

    comparison_fig = result.visualize(
        mode="comparison",
        backend=target_backend,
        max_zones=1,
        date_range=(price_data.index[0], price_data.index[30]),
        visualizer_config={"width": 910},
    )

    assert init_kwargs[0]["backend"] == target_backend
    assert init_kwargs[0]["width"] == 900
    assert init_kwargs[1]["backend"] == target_backend
    assert init_kwargs[1]["width"] == 910

    detail_names = set(_extract_indicator_names(detail_fig, target_backend))
    assert detail_names == {"ema_fast", "momentum"}

    comparison_names = set(_extract_indicator_names(comparison_fig, target_backend))
    assert comparison_names == {"1 · ema_fast", "1 · momentum"}
