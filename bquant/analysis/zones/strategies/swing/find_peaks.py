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
    # Warm-up window for the auto threshold (G15). Only used when `prominence`
    # is None; see `_resolve_prominence` for why it exists.
    prominence_warmup: int = 200

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Calculate global extrema and convert them into swing context."""

        self._validate_input(full_data)

        prominence_value = self._resolve_prominence(
            full_data, warmup=self._active_warmup()
        )
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

        high_arr = full_data['high'].to_numpy(dtype=float)
        low_arr = full_data['low'].to_numpy(dtype=float)
        full_len = len(full_data)

        # Detection series per swing type (troughs are found on the negated lows,
        # exactly as in `_detect_extrema`) plus their *unfiltered* local maxima —
        # the raw input scipy's `distance` filter operates on, needed to settle
        # that filter's verdict in `_distance_settled_bar`.
        series_by_type = {'peak': high_arr, 'trough': -low_arr}
        maxima_by_type = {
            swing_type: find_peaks(series)[0]
            for swing_type, series in series_by_type.items()
        }

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

            confirmation_index = self._confirmation_index(
                index_position,
                prominence_value,
                series_by_type[point['type']],
                maxima_by_type[point['type']],
                full_len,
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
                    confirmation_index=confirmation_index,
                )
            )
            indices.append(index_position)

        # Warm-up (issue #110 follow-up / G14): a context is only emitted once at
        # least two extrema exist (see the guard above), so a lone first extremum
        # is not yet observable at its own confirmation — it appears together with
        # the second one. Pin its availability to the second's, as ZigZag does.
        if len(swing_points) >= 2 and swing_points[0].confirmation_index is not None \
                and swing_points[1].confirmation_index is not None:
            swing_points[0].confirmation_index = max(
                swing_points[0].confirmation_index,
                swing_points[1].confirmation_index,
            )

        # Warm-up floor (G15). While fewer than `prominence_warmup` bars exist the
        # frozen threshold is still computed on a shorter window, i.e. it is a
        # different number — so nothing may be declared available yet. Without this
        # the freeze leaves exactly the same hole, merely a narrower one. A series
        # that has not reached the end of its warm-up confirms nothing at all.
        warmup = self._active_warmup()
        if warmup:
            floor = warmup - 1
            if floor >= full_len:
                logger.warning(
                    "FindPeaks global: series of %d bars is shorter than the "
                    "auto-prominence warm-up (%d), so no swing can be declared "
                    "causally available — every confirmation_index is None. "
                    "Pass an explicit `prominence`, or lower `prominence_warmup`, "
                    "if you need availability markers on a series this short.",
                    full_len,
                    warmup,
                )
            for swing_point in swing_points:
                if swing_point.confirmation_index is None:
                    continue
                if floor >= full_len:
                    swing_point.confirmation_index = None
                elif swing_point.confirmation_index < floor:
                    swing_point.confirmation_index = floor

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

    def _distance_settled_bar(
        self, index: int, series: np.ndarray, maxima: np.ndarray
    ) -> int:
        """Bar by which scipy's ``distance`` verdict for ``index`` stops changing.

        scipy applies ``distance`` *before* ``prominence``, greedily over **all**
        raw local maxima by descending height: an extremum is dropped when a
        higher one survives strictly within ``distance`` of it. That verdict is
        therefore **not** settled at ``index + distance`` — the neighbour that
        suppresses this extremum may itself be dropped later by a still higher
        one further right, reviving this extremum. Observed on the embedded
        sample: the peak at 178 is suppressed by 180 until 182 becomes visible
        and removes 180, so 178 only appears two bars after ``index + distance``.

        The verdict depends on the transitive *suppression chain*: every local
        maximum within ``distance`` that is at least as high, then their own
        suppressors, and so on (heights are non-decreasing along the chain, so it
        terminates). A chain member at ``p`` has its own neighbourhood fully
        observable at ``p + distance``; the chain — and hence this extremum's
        verdict — is settled at the latest such bar.
        """
        settled = index + self.distance
        seen = {index}
        frontier = [index]

        while frontier:
            q = frontier.pop()
            lo = np.searchsorted(maxima, q - self.distance, side='right')
            hi = np.searchsorted(maxima, q + self.distance, side='left')
            for candidate in maxima[lo:hi]:
                p = int(candidate)
                # only an at-least-as-high neighbour can suppress; ties are taken
                # as suppressors (conservative — never confirms too early)
                if p in seen or series[p] < series[q]:
                    continue
                seen.add(p)
                frontier.append(p)
                settled = max(settled, p + self.distance)

        return settled

    def _confirmation_index(
        self,
        index: int,
        prominence: float,
        series: np.ndarray,
        maxima: np.ndarray,
        full_len: int,
    ) -> Optional[int]:
        """Bar by which this find_peaks extremum is causally confirmed.

        ``series`` is the detection series for this extremum's type (highs for
        peaks, negated lows for troughs, as in :meth:`_detect_extrema`), so the
        extremum is a maximum of ``series`` either way; ``maxima`` are that
        series' unfiltered local maxima.

        An extremum survives the global pass only if it clears BOTH the
        ``distance`` and ``prominence`` filters, so it becomes causally known at
        the later of two events:

        * **distance settling** — the bar at which the suppression chain around
          it resolves, see :meth:`_distance_settled_bar` (never earlier than
          ``index + distance``);
        * **prominence retrace** — the first bar after ``index`` at which the
          right base falls ``prominence`` below the pivot. Truncation can only
          shorten the right-base interval, so the computed prominence grows
          monotonically with observed bars: once this bar is reached the
          prominence filter stays cleared. The left base does not depend on
          truncation and already clears the threshold for a kept extremum.

        Returns ``max`` of the two (both are necessary), or ``None`` if the pivot
        cannot yet be confirmed within the available data (retrace not reached, or
        the settling bar lies past the end — a still-forming tail swing). This is
        the ``find_peaks`` realisation of the generic
        :attr:`SwingPoint.confirmation_index` contract, verified replay-safe by
        ``tests/unit/test_swing_replay_causal`` (G14).
        """
        hits = np.nonzero(series[index + 1:] <= series[index] - prominence)[0]
        if not len(hits):
            return None
        prominence_bar = index + 1 + int(hits[0])
        conf = max(self._distance_settled_bar(index, series, maxima), prominence_bar)
        return conf if conf < full_len else None

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

    def _active_warmup(self) -> Optional[int]:
        """Warm-up length in force, or None when it does not apply.

        An explicitly configured ``prominence`` is a constant — it needs no warm-up
        and must not delay any confirmation. The window only governs the auto path.
        """
        if self.prominence is not None:
            return None
        warmup = int(self.prominence_warmup or 0)
        return warmup if warmup > 1 else None

    def _resolve_prominence(
        self, data: pd.DataFrame, *, warmup: Optional[int] = None
    ) -> float:
        """Resolve the prominence threshold, optionally frozen on a warm-up window.

        With ``warmup`` set (the global path), the threshold is derived from the
        first ``warmup`` bars only. That is what makes it replay-stable: truncating
        the series to ``data[:t+1]`` for any ``t >= warmup`` leaves those bars
        untouched, so the threshold is identical on replay.

        Without it (the per-zone path) the whole window is used, as before — a zone
        handed to :meth:`calculate` is already closed, so there is no growing
        window to defend against.

        The unfrozen full-window form was the G15 defect: ``high.max()`` can only
        rise and ``low.min()`` can only fall, so the threshold was monotonically
        non-decreasing in t, and an extremum clearing the early, smaller threshold
        could fail the later, larger one and vanish — after a consumer had been
        told it was available.
        """
        if self.prominence is not None:
            return float(self.prominence)
        window = data.iloc[:warmup] if warmup else data
        price_range = float(window['high'].max() - window['low'].min())
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

        params: Dict[str, Any] = {
            'prominence': resolved_prominence,
            'distance': self.distance,
            'min_amplitude_pct': self.min_amplitude_pct,
        }
        # Only meaningful on the auto path, but it changes the produced swings, so
        # it must reach the cache key whenever it is in force (see CACHE_VERSION).
        if self._active_warmup():
            params['prominence_warmup'] = int(self.prominence_warmup)
        return params

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
