"""
FindPeaks Swing Strategy - swing detection using scipy.signal.find_peaks.

This strategy uses scipy's find_peaks algorithm to identify local extrema
and filters them by minimum amplitude to get significant swings.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from ...models import SwingContext, SwingPoint, ZoneInfo
from ..base import SwingMetrics
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('find_peaks')
@dataclass
class FindPeaksSwingStrategy:
    """Swing detection using scipy.signal.find_peaks algorithm."""

    prominence: float = None  # Auto-calculate if None
    distance: int = 5
    min_amplitude_pct: float = 0.02  # 2% minimum movement

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Calculate global extrema and convert them into swing context."""

        self._validate_input(full_data)

        prominence_value = self._resolve_prominence(full_data)
        extrema = self._detect_extrema(full_data, prominence_value)

        if len(extrema) < 2:
            logger.warning(
                "FindPeaks global: insufficient extrema detected (%d)",
                len(extrema),
            )
            return SwingContext(
                swing_points=[],
                indices=np.array([], dtype=int),
                full_data_length=len(full_data),
                strategy_name='find_peaks',
                strategy_params=self._build_strategy_params(prominence_value),
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
                    strategy_name='find_peaks',
                    strategy_params=self._build_strategy_params(prominence_value),
                )
            )
            indices.append(index_position)

        logger.info(
            "FindPeaks global: detected %d swing points", len(swing_points)
        )

        return SwingContext(
            swing_points=swing_points,
            indices=np.asarray(indices, dtype=int),
            full_data_length=len(full_data),
            strategy_name='find_peaks',
            strategy_params=self._build_strategy_params(prominence_value),
        )

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Aggregate global swings for a specific zone."""

        zone_swings = context.get_swings_for_zone(zone)

        if len(zone_swings) < 2:
            logger.debug(
                "Zone %s: insufficient global swings (%d points)",
                zone.zone_id,
                len(zone_swings),
            )
            return self._empty_metrics()

        rallies, drops = self._build_movements_from_points(zone_swings)

        if not rallies and not drops:
            logger.debug(
                "Zone %s: no valid movements after amplitude filtering",
                zone.zone_id,
            )
            return self._empty_metrics()

        return self._aggregate_metrics(
            rallies,
            drops,
            params=context.strategy_params,
        )

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """Calculate comprehensive swing metrics using find_peaks algorithm."""

        self._validate_input(zone_data)

        try:
            prominence_value = self._resolve_prominence(zone_data)
            extrema = self._detect_extrema(zone_data, prominence_value)

            if len(extrema) < 2:
                logger.debug(
                    "Not enough extrema detected: %d points (prominence=%.4f, distance=%d)",
                    len(extrema),
                    prominence_value,
                    self.distance,
                )
                return self._empty_metrics()

            rallies, drops = self._build_movements_from_extrema(extrema)

            if not rallies and not drops:
                logger.debug(
                    "Extrema filtered out by amplitude threshold: min_amplitude_pct=%.2f",
                    self.min_amplitude_pct,
                )
                return self._empty_metrics()

            return self._aggregate_metrics(
                rallies,
                drops,
                params=self._build_strategy_params(prominence_value),
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("FindPeaks swing calculation failed: %s", exc, exc_info=True)
            return self._empty_metrics()

    def _detect_extrema(
        self,
        data: pd.DataFrame,
        prominence: float,
    ) -> List[Dict[str, Any]]:
        peaks_idx, _ = find_peaks(
            data['high'].values,
            prominence=prominence,
            distance=self.distance,
        )

        troughs_idx, _ = find_peaks(
            -data['low'].values,
            prominence=prominence,
            distance=self.distance,
        )

        extrema: List[Dict[str, Any]] = []

        for idx in peaks_idx:
            extrema.append(
                {
                    'index': int(idx),
                    'type': 'peak',
                    'price': float(data['high'].iloc[idx]),
                    'timestamp': data.index[idx],
                }
            )

        for idx in troughs_idx:
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
        *,
        params: Optional[Dict[str, Any]] = None,
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
            strategy_name='find_peaks',
            strategy_params=params
            or self._build_strategy_params(
                None if self.prominence is None else float(self.prominence)
            ),
        )

        metrics.validate()

        logger.debug(
            "FindPeaks metrics: %d rallies, %d drops, ratio=%.2f",
            rally_count,
            drop_count,
            rally_to_drop_ratio,
        )

        return metrics

    def _empty_metrics(self) -> SwingMetrics:
        return self._aggregate_metrics(
            [],
            [],
            params=self._build_strategy_params(
                None if self.prominence is None else float(self.prominence)
            ),
        )

    def _validate_input(self, data: pd.DataFrame) -> None:
        required_cols = {'high', 'low', 'close'}
        missing = required_cols.difference(data.columns)
        if missing:
            raise ValueError(f"zone_data must contain columns: {sorted(missing)}")
        if data.empty:
            raise ValueError("zone_data cannot be empty")

    def _resolve_prominence(self, data: pd.DataFrame) -> float:
        if self.prominence is not None:
            return float(self.prominence)
        price_range = float(data['high'].max() - data['low'].min())
        return max(price_range * 0.01, 1e-9)

    def _build_strategy_params(
        self, prominence_value: Optional[float]
    ) -> Dict[str, Any]:
        resolved_prominence: Any
        if prominence_value is not None:
            resolved_prominence = float(prominence_value)
        elif self.prominence is None:
            resolved_prominence = 'auto'
        else:
            resolved_prominence = float(self.prominence)

        return {
            'prominence': resolved_prominence,
            'distance': self.distance,
            'min_amplitude_pct': self.min_amplitude_pct,
        }

    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'FindPeaks',
            'description': 'Swing detection via scipy.signal.find_peaks',
            'params': self._build_strategy_params(self.prominence),
            'calculates': [
                'swing amplitudes (rally/drop)',
                'swing durations (bars)',
                'swing speeds (% per bar)',
                'distribution statistics',
            ],
        }

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration parameters for cache key generation."""
        return {
            'prominence': self.prominence,
            'distance': self.distance,
            'min_amplitude_pct': self.min_amplitude_pct,
        }
