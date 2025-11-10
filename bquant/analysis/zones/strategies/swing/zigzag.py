"""
ZigZag Swing Strategy - swing detection using pandas-ta ZigZag indicator.

This strategy uses the pandas-ta ZigZag algorithm to identify significant
price swings within a trading zone, filtering out noise and focusing on
meaningful price movements.
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


@StrategyRegistry.register_swing_strategy('zigzag')
@dataclass
class ZigZagSwingStrategy:
    """
    Swing detection using pandas-ta ZigZag algorithm.
    
    This strategy identifies swing points by finding price reversals that exceed
    a specified percentage threshold. It provides comprehensive metrics including
    amplitudes, durations, speeds, and distributions of both rally and drop movements.
    
    Attributes:
        legs: Number of bars to confirm a pivot (default: 10)
        deviation: Minimum percentage move to qualify as swing (default: 0.05 = 5%)
    """
    legs: int = 10
    deviation: float = 0.05  # 5% minimum movement

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Run a single ZigZag pass on the full dataset and build context."""

        self._validate_input(full_data)

        if len(full_data) < self.legs * 2:
            raise ValueError(
                f"Insufficient data for ZigZag: {len(full_data)} bars < {self.legs * 2}"
            )

        from .....indicators import LibraryManager

        zigzag = LibraryManager.create_indicator(
            'pandas_ta',
            'zigzag',
            legs=self.legs,
            deviation=self.deviation,
        )
        result = zigzag.calculate(full_data)

        if result.data.shape[1] < 2:
            logger.warning(
                "ZigZag returned insufficient columns, no swings detected"
            )
            return SwingContext(
                swing_points=[],
                indices=np.array([], dtype=int),
                full_data_length=len(full_data),
                strategy_name='zigzag',
                strategy_params={'legs': self.legs, 'deviation': self.deviation},
            )

        swing_values = result.data.iloc[:, 1].dropna()

        if len(swing_values) < 2:
            logger.warning(
                "ZigZag detected fewer than two swing points in global mode"
            )
            return SwingContext(
                swing_points=[],
                indices=np.array([], dtype=int),
                full_data_length=len(full_data),
                strategy_name='zigzag',
                strategy_params={'legs': self.legs, 'deviation': self.deviation},
            )

        swing_points: List[SwingPoint] = []
        indices: List[int] = []

        timestamps = swing_values.index.to_list()
        prices = swing_values.to_list()

        for point_id, (timestamp, price) in enumerate(zip(timestamps, prices)):
            ts = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
            position_arr = full_data.index.get_indexer([timestamp])
            if -1 in position_arr:
                logger.debug("Timestamp %s from ZigZag output not present in data index", timestamp)
                continue
            position = int(position_arr[0])

            if point_id > 0:
                prev_price = prices[point_id - 1]
                swing_type = 'peak' if price > prev_price else 'trough'
            else:
                if len(prices) > 1:
                    swing_type = 'trough' if prices[1] > price else 'peak'
                else:
                    swing_type = 'trough'

            amplitude_to_next: Optional[float] = None
            duration_to_next: Optional[int] = None
            if point_id < len(prices) - 1:
                next_price = prices[point_id + 1]
                next_timestamp = timestamps[point_id + 1]
                next_position_arr = full_data.index.get_indexer([next_timestamp])
                if -1 not in next_position_arr:
                    next_position = int(next_position_arr[0])
                    if price != 0:
                        amplitude_to_next = (next_price / price - 1) * 100
                    duration_to_next = max(0, next_position - position)

            swing_points.append(
                SwingPoint(
                    point_id=point_id,
                    timestamp=ts,
                    index=position,
                    price=float(price),
                    swing_type=swing_type,
                    amplitude_to_next=amplitude_to_next,
                    duration_to_next=duration_to_next,
                    strategy_name='zigzag',
                    strategy_params={'legs': self.legs, 'deviation': self.deviation},
                )
            )
            indices.append(position)

        logger.info("ZigZag global: detected %d swing points", len(swing_points))

        return SwingContext(
            swing_points=swing_points,
            indices=np.asarray(indices, dtype=int),
            full_data_length=len(full_data),
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation},
        )

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Aggregate global swing context for a single zone."""

        zone_swings = context.get_swings_for_zone(zone)

        if len(zone_swings) < 2:
            logger.debug(
                "Zone %s: insufficient swings (%d points)", zone.zone_id, len(zone_swings)
            )
            return self._empty_metrics()

        rallies, drops = self._build_movements_from_points(zone_swings)
        return self._aggregate_metrics(rallies, drops)

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate comprehensive swing metrics using ZigZag algorithm.

        Args:
            zone_data: DataFrame with columns: high, low, close, open

        Returns:
            SwingMetrics with all 23 fields populated

        Raises:
            ValueError: If zone_data is empty or missing required columns
        """
        self._validate_input(zone_data)

        try:
            # Import LibraryManager dynamically to avoid circular imports
            from .....indicators import LibraryManager

            # Create ZigZag indicator
            zigzag = LibraryManager.create_indicator(
                'pandas_ta',
                'zigzag',
                legs=self.legs,
                deviation=self.deviation
            )
            
            # Calculate ZigZag
            result = zigzag.calculate(zone_data)
            
            # Extract swing data
            # ZigZag may return 1-3 columns depending on results
            # Usually: Column 0=signal, 1=values, 2=distance
            # But if no swings found, may return only 1 column
            
            if result.data.shape[1] < 2:
                # Not enough columns - no swings detected
                logger.debug(
                    f"ZigZag returned only {result.data.shape[1]} column(s), no swings detected"
                )
                return self._empty_metrics()
            
            swing_signal = result.data.iloc[:, 0]
            swing_values = result.data.iloc[:, 1]
            
            # Get swing points (non-NaN values)
            swing_points = swing_values.dropna()

            if len(swing_points) < 2:
                logger.debug(
                    f"Not enough swings detected: {len(swing_points)} points "
                    f"(legs={self.legs}, deviation={self.deviation})"
                )
                return self._empty_metrics()

            rallies, drops = self._build_movements_from_series(
                swing_points,
                zone_data.index,
            )
            return self._aggregate_metrics(rallies, drops)

        except Exception as e:
            logger.error(f"ZigZag swing calculation failed: {e}", exc_info=True)
            # Return empty metrics on error
            return self._empty_metrics()
    def _build_movements_from_series(
        self,
        swing_points: pd.Series,
        time_index: pd.Index,
    ) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        rallies: List[Dict[str, float]] = []
        drops: List[Dict[str, float]] = []

        for i in range(1, len(swing_points)):
            prev_price = swing_points.iloc[i - 1]
            curr_price = swing_points.iloc[i]

            prev_idx = swing_points.index[i - 1]
            curr_idx = swing_points.index[i]

            prev_pos = time_index.get_loc(prev_idx)
            curr_pos = time_index.get_loc(curr_idx)
            duration_bars = curr_pos - prev_pos

            if duration_bars <= 0 or prev_price == 0:
                continue

            price_change_pct = (curr_price / prev_price - 1) * 100

            movement = {
                'amplitude_pct': abs(price_change_pct),
                'duration_bars': int(duration_bars),
                'speed_pct_per_bar': abs(price_change_pct) / duration_bars
                if duration_bars > 0
                else 0.0,
            }

            if price_change_pct > 0:
                rallies.append(movement)
            elif price_change_pct < 0:
                drops.append(movement)

        return rallies, drops

    def _build_movements_from_points(
        self,
        swings: List[SwingPoint],
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
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation},
        )

        metrics.validate()

        logger.debug(
            "ZigZag metrics calculated: %d rallies, %d drops, ratio=%.2f",
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

    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'ZigZag',
            'description': 'Swing detection via pandas-ta ZigZag algorithm',
            'params': {
                'legs': self.legs,
                'deviation': self.deviation
            },
            'source': 'pandas-ta library via LibraryManager',
            'calculates': [
                'swing amplitudes (rally/drop)',
                'swing durations (bars)',
                'swing speeds (% per bar)',
                'distributions (std, median)',
                'symmetry metrics'
            ]
        }

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration parameters for cache key generation."""
        return {
            'legs': self.legs,
            'deviation': self.deviation
        }

