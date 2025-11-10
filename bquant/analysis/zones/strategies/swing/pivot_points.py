"""
Pivot Points Swing Strategy - swing detection using N-bar pivot patterns.

This strategy identifies swing points using classic technical analysis pivot
patterns, where a pivot high is a bar whose high is greater than N bars before
and after it, and a pivot low is a bar whose low is less than N bars before
and after it.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ...models import SwingContext, SwingPoint, ZoneInfo
from ..base import SwingMetrics
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('pivot_points')
@dataclass
class PivotPointsSwingStrategy:
    """Swing detection using classic Pivot Points (N-bar pattern)."""

    left_bars: int = 2
    right_bars: int = 2
    min_amplitude_pct: float = 0.015  # 1.5% minimum movement

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Compute pivot-based swing points on the full dataset."""

        self._validate_input(full_data)

        min_bars = self.left_bars + self.right_bars + 1
        if len(full_data) < min_bars:
            logger.warning(
                "PivotPoints global: not enough bars for pivot pattern (%d < %d)",
                len(full_data),
                min_bars,
            )
            return SwingContext(
                swing_points=[],
                indices=np.array([], dtype=int),
                full_data_length=len(full_data),
                strategy_name='pivot_points',
                strategy_params=self._strategy_params(),
            )

        pivot_highs = self._find_pivot_highs(full_data)
        pivot_lows = self._find_pivot_lows(full_data)

        extrema = self._combine_extrema(full_data, pivot_highs, pivot_lows)

        if len(extrema) < 2:
            logger.warning(
                "PivotPoints global: insufficient extrema detected (%d)",
                len(extrema),
            )
            return SwingContext(
                swing_points=[],
                indices=np.array([], dtype=int),
                full_data_length=len(full_data),
                strategy_name='pivot_points',
                strategy_params=self._strategy_params(),
            )

        swing_points: List[SwingPoint] = []
        indices: List[int] = []

        for point_id, point in enumerate(extrema):
            timestamp = point['timestamp']
            ts = (
                timestamp.to_pydatetime()
                if hasattr(timestamp, "to_pydatetime")
                else timestamp
            )
            index_position = int(point['index'])
            price = point['price']

            amplitude_to_next: Optional[float] = None
            duration_to_next: Optional[int] = None
            if point_id < len(extrema) - 1:
                next_point = extrema[point_id + 1]
                next_price = next_point['price']
                if price != 0:
                    amplitude_to_next = (next_price / price - 1) * 100
                duration_to_next = max(
                    0, int(next_point['index']) - index_position
                )

            swing_points.append(
                SwingPoint(
                    point_id=point_id,
                    timestamp=ts,
                    index=index_position,
                    price=float(price),
                    swing_type=point['type'],
                    amplitude_to_next=amplitude_to_next,
                    duration_to_next=duration_to_next,
                    strategy_name='pivot_points',
                    strategy_params=self._strategy_params(),
                )
            )
            indices.append(index_position)

        logger.info(
            "PivotPoints global: detected %d swing points", len(swing_points)
        )

        return SwingContext(
            swing_points=swing_points,
            indices=np.asarray(indices, dtype=int),
            full_data_length=len(full_data),
            strategy_name='pivot_points',
            strategy_params=self._strategy_params(),
        )

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Aggregate global pivot swings for the specified zone."""

        zone_swings = context.get_swings_for_zone(zone)

        if len(zone_swings) < 2:
            logger.debug(
                "Zone %s: insufficient pivot swings (%d points)",
                zone.zone_id,
                len(zone_swings),
            )
            return self._empty_metrics()

        rallies, drops = self._build_movements_from_points(zone_swings)

        if not rallies and not drops:
            logger.debug(
                "Zone %s: no valid pivot movements after amplitude filtering",
                zone.zone_id,
            )
            return self._empty_metrics()

        return self._aggregate_metrics(rallies, drops)

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """Calculate comprehensive swing metrics using pivot patterns."""

        self._validate_input(zone_data)

        min_bars = self.left_bars + self.right_bars + 1
        if len(zone_data) < min_bars:
            logger.debug(
                "Not enough bars for pivot pattern: %d < %d",
                len(zone_data),
                min_bars,
            )
            return self._empty_metrics()

        try:
            pivot_highs = self._find_pivot_highs(zone_data)
            pivot_lows = self._find_pivot_lows(zone_data)

            extrema = self._combine_extrema(zone_data, pivot_highs, pivot_lows)

            if len(extrema) < 2:
                logger.debug(
                    "Not enough pivot points detected: highs=%d, lows=%d",
                    len(pivot_highs),
                    len(pivot_lows),
                )
                return self._empty_metrics()

            rallies, drops = self._build_movements_from_extrema(extrema)

            if not rallies and not drops:
                logger.debug(
                    "Pivot movements filtered by amplitude threshold %.2f",
                    self.min_amplitude_pct,
                )
                return self._empty_metrics()

            return self._aggregate_metrics(rallies, drops)

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("PivotPoints swing calculation failed: %s", exc, exc_info=True)
            return self._empty_metrics()

    def _combine_extrema(
        self,
        data: pd.DataFrame,
        pivot_highs: List[int],
        pivot_lows: List[int],
    ) -> List[Dict[str, Any]]:
        extrema: List[Dict[str, Any]] = []

        for idx in pivot_highs:
            extrema.append(
                {
                    'index': int(idx),
                    'type': 'peak',
                    'price': float(data['high'].iloc[idx]),
                    'timestamp': data.index[idx],
                }
            )

        for idx in pivot_lows:
            extrema.append(
                {
                    'index': int(idx),
                    'type': 'trough',
                    'price': float(data['low'].iloc[idx]),
                    'timestamp': data.index[idx],
                }
            )

        extrema.sort(key=lambda item: item['index'])
        return extrema

    def _build_movements_from_extrema(
        self, extrema: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        rallies: List[Dict[str, float]] = []
        drops: List[Dict[str, float]] = []

        for i in range(1, len(extrema)):
            prev = extrema[i - 1]
            curr = extrema[i]

            duration_bars = int(curr['index'] - prev['index'])
            if duration_bars <= 0 or prev['price'] == 0:
                continue

            price_change_pct = (curr['price'] / prev['price'] - 1) * 100
            if abs(price_change_pct) < self.min_amplitude_pct * 100:
                continue

            movement = {
                'amplitude_pct': abs(price_change_pct),
                'duration_bars': duration_bars,
                'speed_pct_per_bar': abs(price_change_pct) / duration_bars,
            }

            if price_change_pct > 0:
                rallies.append(movement)
            elif price_change_pct < 0:
                drops.append(movement)

        return rallies, drops

    def _build_movements_from_points(
        self, swings: List[SwingPoint]
    ) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        rallies: List[Dict[str, float]] = []
        drops: List[Dict[str, float]] = []

        for i in range(len(swings) - 1):
            curr = swings[i]
            nxt = swings[i + 1]

            duration_bars = nxt.index - curr.index
            if duration_bars <= 0 or curr.price == 0:
                continue

            price_change_pct = (nxt.price / curr.price - 1) * 100
            if abs(price_change_pct) < self.min_amplitude_pct * 100:
                continue

            movement = {
                'amplitude_pct': abs(price_change_pct),
                'duration_bars': int(duration_bars),
                'speed_pct_per_bar': abs(price_change_pct) / duration_bars,
            }

            if price_change_pct > 0:
                rallies.append(movement)
            elif price_change_pct < 0:
                drops.append(movement)

        return rallies, drops

    def _aggregate_metrics(
        self,
        rallies: List[Dict[str, float]],
        drops: List[Dict[str, float]],
    ) -> SwingMetrics:
        rally_count = len(rallies)
        drop_count = len(drops)

        if rally_count > 0:
            rally_amps = [r['amplitude_pct'] for r in rallies]
            avg_rally_pct = float(np.mean(rally_amps))
            max_rally_pct = float(np.max(rally_amps))
            min_rally_pct = float(np.min(rally_amps))
            rally_amplitude_std = float(np.std(rally_amps))
            rally_amplitude_median = float(np.median(rally_amps))
        else:
            avg_rally_pct = max_rally_pct = min_rally_pct = 0.0
            rally_amplitude_std = rally_amplitude_median = 0.0

        if drop_count > 0:
            drop_amps = [d['amplitude_pct'] for d in drops]
            avg_drop_pct = float(np.mean(drop_amps))
            max_drop_pct = float(np.max(drop_amps))
            min_drop_pct = float(np.min(drop_amps))
            drop_amplitude_std = float(np.std(drop_amps))
            drop_amplitude_median = float(np.median(drop_amps))
        else:
            avg_drop_pct = max_drop_pct = min_drop_pct = 0.0
            drop_amplitude_std = drop_amplitude_median = 0.0

        if rally_count > 0:
            rally_durs = [r['duration_bars'] for r in rallies]
            avg_rally_duration_bars = float(np.mean(rally_durs))
            max_rally_duration_bars = int(np.max(rally_durs))
        else:
            avg_rally_duration_bars = 0.0
            max_rally_duration_bars = 0

        if drop_count > 0:
            drop_durs = [d['duration_bars'] for d in drops]
            avg_drop_duration_bars = float(np.mean(drop_durs))
            max_drop_duration_bars = int(np.max(drop_durs))
        else:
            avg_drop_duration_bars = 0.0
            max_drop_duration_bars = 0

        if rally_count > 0:
            rally_speeds = [r['speed_pct_per_bar'] for r in rallies]
            avg_rally_speed_pct_per_bar = float(np.mean(rally_speeds))
            max_rally_speed_pct_per_bar = float(np.max(rally_speeds))
        else:
            avg_rally_speed_pct_per_bar = 0.0
            max_rally_speed_pct_per_bar = 0.0

        if drop_count > 0:
            drop_speeds = [d['speed_pct_per_bar'] for d in drops]
            avg_drop_speed_pct_per_bar = float(np.mean(drop_speeds))
            max_drop_speed_pct_per_bar = float(np.max(drop_speeds))
        else:
            avg_drop_speed_pct_per_bar = 0.0
            max_drop_speed_pct_per_bar = 0.0

        rally_to_drop_ratio = (
            avg_rally_pct / avg_drop_pct if avg_drop_pct > 0 else 0.0
        )
        duration_symmetry = (
            avg_rally_duration_bars / avg_drop_duration_bars
            if avg_drop_duration_bars > 0
            else 0.0
        )

        num_swings = min(rally_count, drop_count)

        metrics = SwingMetrics(
            num_swings=num_swings,
            avg_rally_pct=avg_rally_pct,
            avg_drop_pct=avg_drop_pct,
            max_rally_pct=max_rally_pct,
            max_drop_pct=max_drop_pct,
            rally_to_drop_ratio=rally_to_drop_ratio,
            rally_count=rally_count,
            drop_count=drop_count,
            min_rally_pct=min_rally_pct,
            min_drop_pct=min_drop_pct,
            rally_amplitude_std=rally_amplitude_std,
            drop_amplitude_std=drop_amplitude_std,
            rally_amplitude_median=rally_amplitude_median,
            drop_amplitude_median=drop_amplitude_median,
            avg_rally_duration_bars=avg_rally_duration_bars,
            avg_drop_duration_bars=avg_drop_duration_bars,
            max_rally_duration_bars=max_rally_duration_bars,
            max_drop_duration_bars=max_drop_duration_bars,
            avg_rally_speed_pct_per_bar=avg_rally_speed_pct_per_bar,
            avg_drop_speed_pct_per_bar=avg_drop_speed_pct_per_bar,
            max_rally_speed_pct_per_bar=max_rally_speed_pct_per_bar,
            max_drop_speed_pct_per_bar=max_drop_speed_pct_per_bar,
            duration_symmetry=duration_symmetry,
            strategy_name='pivot_points',
            strategy_params=self._strategy_params(),
        )

        metrics.validate()

        logger.debug(
            "PivotPoints metrics: %d rallies, %d drops, ratio=%.2f",
            rally_count,
            drop_count,
            rally_to_drop_ratio,
        )

        return metrics

    def _empty_metrics(self) -> SwingMetrics:
        return self._aggregate_metrics([], [])

    def _validate_input(self, data: pd.DataFrame) -> None:
        required_cols = {'high', 'low', 'close'}
        missing = required_cols.difference(data.columns)
        if missing:
            raise ValueError(f"zone_data must contain columns: {sorted(missing)}")
        if data.empty:
            raise ValueError("zone_data cannot be empty")

    def _find_pivot_highs(self, data: pd.DataFrame) -> List[int]:
        highs = data['high'].values
        pivot_indices: List[int] = []

        for i in range(self.left_bars, len(highs) - self.right_bars):
            is_pivot = all(
                highs[i] > highs[i - j] for j in range(1, self.left_bars + 1)
            )

            if is_pivot:
                is_pivot = all(
                    highs[i] > highs[i + j] for j in range(1, self.right_bars + 1)
                )

            if is_pivot:
                pivot_indices.append(i)

        return pivot_indices

    def _find_pivot_lows(self, data: pd.DataFrame) -> List[int]:
        lows = data['low'].values
        pivot_indices: List[int] = []

        for i in range(self.left_bars, len(lows) - self.right_bars):
            is_pivot = all(
                lows[i] < lows[i - j] for j in range(1, self.left_bars + 1)
            )

            if is_pivot:
                is_pivot = all(
                    lows[i] < lows[i + j] for j in range(1, self.right_bars + 1)
                )

            if is_pivot:
                pivot_indices.append(i)

        return pivot_indices

    def _strategy_params(self) -> Dict[str, Any]:
        return {
            'left_bars': self.left_bars,
            'right_bars': self.right_bars,
            'min_amplitude_pct': self.min_amplitude_pct,
        }

    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'PivotPoints',
            'description': 'Swing detection via classic pivot patterns',
            'params': self._strategy_params(),
            'calculates': [
                'pivot-based swing amplitudes',
                'pivot durations (bars)',
                'swing speed statistics',
            ],
        }

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration parameters for cache key generation."""
        return self._strategy_params()
