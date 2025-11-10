"""Utilities for calculating adaptive swing thresholds."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

from ...models import SwingContext, ZoneInfo
from ..base import SwingMetrics
from ..registry import StrategyRegistry


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


class _AdaptiveSwingStrategy:
    """Wrapper that adapts swing thresholds for base strategies."""

    def __init__(
        self,
        strategy_name: str,
        base_params: Dict[str, Any],
        *,
        base_deviation: float,
    ) -> None:
        self.base_strategy_name = strategy_name
        self._base_params = dict(base_params)
        self._base_deviation = base_deviation
        self.base_strategy = StrategyRegistry.get_swing_strategy(
            strategy_name, **base_params
        )
        self._global_threshold_cache: Optional[SwingThresholds] = None
        self._last_thresholds: Optional[Dict[str, float]] = None

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Calculate global swings with adaptive thresholds applied once."""

        thresholds = self._calculate_adaptive_thresholds(full_data)
        self._global_threshold_cache = thresholds
        self._last_thresholds = self._thresholds_to_dict(thresholds)
        self._apply_thresholds_to_strategy(self.base_strategy, thresholds)
        return self.base_strategy.calculate_global(full_data)

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Delegate aggregation using previously computed global thresholds."""

        return self.base_strategy.aggregate_for_zone(zone, context)

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """Per-zone calculation with adaptive thresholds."""

        thresholds = self._calculate_adaptive_thresholds(zone_data)
        self._apply_thresholds_to_strategy(self.base_strategy, thresholds)
        self._last_thresholds = self._thresholds_to_dict(thresholds)
        return self.base_strategy.calculate(zone_data)

    def get_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            'name': f'Adaptive{self.base_strategy_name}',
            'description': 'Swing strategy with auto-scaled thresholds',
            'base_params': dict(self._base_params),
            'auto_thresholds': True,
            'base_deviation': self._base_deviation,
        }
        if self._last_thresholds:
            metadata['last_thresholds'] = dict(self._last_thresholds)
        return metadata

    def config_hash(self) -> Dict[str, Any]:
        return {
            'base_strategy': self.base_strategy_name,
            'base_params': dict(self._base_params),
            'base_deviation': self._base_deviation,
        }

    def _calculate_adaptive_thresholds(self, data: pd.DataFrame) -> SwingThresholds:
        return auto_swing_thresholds(data, base_deviation=self._base_deviation)

    def _apply_thresholds_to_strategy(
        self,
        strategy,
        thresholds: SwingThresholds,
    ) -> None:
        if self.base_strategy_name == 'zigzag':
            strategy.deviation = thresholds.zigzag_deviation
        elif self.base_strategy_name == 'find_peaks':
            strategy.prominence = thresholds.peak_prominence
            strategy.min_amplitude_pct = thresholds.peak_prominence
        elif self.base_strategy_name == 'pivot_points':
            strategy.min_amplitude_pct = thresholds.pivot_deviation

    @staticmethod
    def _thresholds_to_dict(thresholds: SwingThresholds) -> Dict[str, float]:
        return {
            'zigzag_deviation': thresholds.zigzag_deviation,
            'peak_prominence': thresholds.peak_prominence,
            'pivot_deviation': thresholds.pivot_deviation,
        }
