"""Test helpers for mocking swing strategies and synthetic OHLCV data."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from bquant.indicators.base import IndicatorConfig, IndicatorResult, IndicatorSource


@dataclass
class FakeZigZagIndicator:
    """Minimal indicator stub that mimics pandas-ta ZigZag output."""

    pivot_timestamps: Sequence[pd.Timestamp]

    def __post_init__(self) -> None:
        self._pivot_set = {pd.Timestamp(ts) for ts in self.pivot_timestamps}
        self._config = IndicatorConfig(
            name="fake_zigzag",
            parameters={},
            source=IndicatorSource.CUSTOM,
            columns=["zigzag", "zigzag_points"],
            description="Synthetic ZigZag output for tests",
        )

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        values = pd.Series(np.nan, index=data.index, dtype=float)
        closes = data["close"]
        for ts in data.index:
            if ts in self._pivot_set:
                values.loc[ts] = float(closes.loc[ts])
        df = pd.DataFrame({"zigzag": values, "zigzag_points": values}, index=data.index)
        return IndicatorResult(name="fake_zigzag", data=df, config=self._config)


def _make_factory(pivot_timestamps: Sequence[pd.Timestamp]):
    def _factory(cls, library_name: str, indicator_name: str, **kwargs):  # type: ignore[override]
        return FakeZigZagIndicator(pivot_timestamps)

    return classmethod(_factory)


def use_fake_zigzag_indicator(monkeypatch, pivot_timestamps: Sequence[pd.Timestamp]) -> None:
    """Patch LibraryManager.create_indicator to return a deterministic stub."""

    from bquant.indicators import LibraryManager

    monkeypatch.setattr(
        LibraryManager,
        "create_indicator",
        _make_factory(pivot_timestamps),
        raising=False,
    )


@contextmanager
def fake_zigzag_indicator_context(pivot_timestamps: Sequence[pd.Timestamp]):
    """Context manager alternative for non-pytest usage (e.g., notebooks)."""

    from bquant.indicators import LibraryManager

    original_create = LibraryManager.create_indicator
    LibraryManager.create_indicator = _make_factory(pivot_timestamps)
    try:
        yield
    finally:
        LibraryManager.create_indicator = original_create


def generate_synthetic_ohlcv(periods: int, freq: str = "H") -> pd.DataFrame:
    """Create deterministic OHLCV series for tests and benchmarks."""

    index = pd.date_range("2024-01-01", periods=periods, freq=freq)
    base = np.linspace(0, np.pi * 4, periods)
    close = 100 + np.sin(base) * 5 + np.cos(base / 2) * 2
    high = close + 1.5
    low = close - 1.5
    open_ = close + np.sin(base / 3) * 0.5
    volume = np.linspace(1_000, 2_000, periods)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )


def evenly_spaced_pivots(data: pd.DataFrame, count: int) -> Sequence[pd.Timestamp]:
    """Select evenly spaced timestamps to use as synthetic swing pivots."""

    if count <= 0:
        return []

    step = max(1, len(data) // count)
    indices = list(range(0, len(data), step))
    if indices[-1] != len(data) - 1:
        indices.append(len(data) - 1)
    return [data.index[i] for i in dict.fromkeys(indices)]
