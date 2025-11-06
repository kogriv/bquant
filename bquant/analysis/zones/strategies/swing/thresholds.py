"""Utilities for calculating adaptive swing thresholds."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class SwingThresholds:
    """Container for dynamically computed swing thresholds."""

    zigzag_deviation: float
    peak_prominence: float
    pivot_deviation: float


def _safe_mid_price(close_series: pd.Series) -> Optional[float]:
    """Calculate a stable mid-price value for a zone."""

    if close_series.empty:
        return None

    median = close_series.median()
    if pd.isna(median) or median == 0:
        mean = close_series.mean()
        if pd.isna(mean) or mean == 0:
            return None
        return float(mean)
    return float(median)


def auto_swing_thresholds(
    zone_df: pd.DataFrame, *, base_deviation: float = 0.01
) -> SwingThresholds:
    """Scale swing thresholds based on the price range of a zone."""

    if zone_df.empty:
        return SwingThresholds(
            zigzag_deviation=base_deviation,
            peak_prominence=base_deviation,
            pivot_deviation=base_deviation,
        )

    if not {"high", "low", "close"}.issubset(zone_df.columns):
        raise KeyError("Zone dataframe must contain 'high', 'low', and 'close' columns")

    price_range = float(zone_df["high"].max() - zone_df["low"].min())
    mid_price = _safe_mid_price(zone_df["close"])

    if not mid_price:
        relative_range = base_deviation
    else:
        relative_range = price_range / mid_price

    deviation = max(base_deviation, relative_range * 0.5)
    prominence = max(base_deviation, relative_range * 0.3)
    pivot_dev = max(base_deviation, relative_range * 0.25)

    return SwingThresholds(
        zigzag_deviation=deviation,
        peak_prominence=prominence,
        pivot_deviation=pivot_dev,
    )
