"""
ZigZag Swing Strategy - swing detection using pandas-ta ZigZag indicator.

This strategy uses the pandas-ta ZigZag algorithm to identify significant
price swings within a trading zone, filtering out noise and focusing on
meaningful price movements.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ...models import SwingContext, SwingPoint, ZoneInfo
from ..base import SwingMetrics
from ..registry import StrategyRegistry
from .....core.exceptions import AnalysisError
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('zigzag')
@dataclass
class ZigZagSwingStrategy:
    """
    Swing detection using pandas-ta ZigZag algorithm.

    Two thresholds, two units, and the names say which is which (G86):

    ``deviation_pct`` — **percent, exactly as pandas-ta reads it.** ``0.008`` means
    0.008 %, not 0.8 %. Until 0.0.20 the field was called ``deviation`` and documented
    as a fraction ("0.05 = 5%"), while the library's ``nb_zz_backtest`` compares
    ``current_dev > 0.01 * deviation`` and prints the unit in the column it returns
    (``ZIGZAGs_0.008%_3``). The presets kept their digits on purpose: 0.008 and 0.05
    are the values the library has always been reading, and the object they produce
    is the one every swing measurement in this project (G35, G38, G48, G54) and the
    external consumer's acceptance were made on. Measured on ``tv_xauusd_1h``
    (1000 bars, ``legs=3``): 0.008 → 402 pivots, 0.8 → 132. At the preset values the
    threshold sits below one bar's range, so the detector reduces to the extremes of
    the ``legs`` window — ``legs`` is the lever that bites. Raising ``deviation_pct``
    to "honest" 0.8 does not give a better object: under ``backtest=True`` the
    parameter does not bound the size of a leg (at 5.0, 8 of 10 legs on the sample
    are smaller than 5 %), and most of the remaining points become updates of the
    same extreme (61.8 % at 0.8) — see ``devref/gaps/swing/g86_…``.

    ``confirmation_retrace_pct`` — percent of the pivot price the next leg must
    retrace before the pivot counts as causally confirmed (``_confirmation_index``).
    It is a separate quantity by necessity, not by taste: the next pivot *is* the
    first bar where the retrace exceeded the detection threshold, so a confirmation
    defined through the same number lands on the next pivot by construction (measured
    99.2 % of pairs) and carries no information. The defaults (0.8 for ``narrow_zone``,
    5.0 for ``wide_zone``) are the values the old code applied in effect — the
    fraction it believed ``deviation`` to be — and the causal replay contract
    (#110, G54) was verified against them.

    What a "leg" is: ``_build_movements_from_points`` takes every pair of consecutive
    points, so an update (two peaks in a row, the second higher) is a movement too.
    Measured: never contrary to its type, 11–14 % of pairs at the preset values.

    Attributes:
        legs: Number of bars on each side a pivot must dominate (default: 10)
        deviation_pct: pandas-ta reversal threshold, percent (default: 0.05)
        confirmation_retrace_pct: retrace, percent, that confirms a pivot (default: 5.0)
    """
    legs: int = 10
    deviation_pct: float = 0.05
    confirmation_retrace_pct: float = 5.0

    #: Имена, которые отказывают с названной заменой (читает ``StrategyRegistry.get``).
    RETIRED_PARAMS: ClassVar[Dict[str, str]] = {
        'deviation': (
            "`deviation` renamed to `deviation_pct` in 0.0.20 (G86): the value is the "
            "PERCENT pandas-ta reads, not a fraction — 0.008 means 0.008 %. Pass the same "
            "digits as `deviation_pct` to keep the swing object you had; the retrace that "
            "confirms a pivot is now its own `confirmation_retrace_pct` (0.8 for the "
            "narrow_zone preset, 5.0 for wide_zone — what the old code applied in effect)."
        ),
    }

    @property
    def deviation(self) -> float:
        raise AttributeError(self.RETIRED_PARAMS['deviation'])

    @deviation.setter
    def deviation(self, _value: float) -> None:
        raise AttributeError(self.RETIRED_PARAMS['deviation'])

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Run a single ZigZag pass on the full dataset and build context."""

        return self._swing_context(full_data, scope='global')

    def _swing_context(self, full_data: pd.DataFrame, *, scope: str) -> SwingContext:
        """One detector, two scopes.

        ``scope`` only chooses how loudly degradations are reported: on the
        global pass a short or degenerate series is worth a warning, inside a
        zone it is the normal case for a short zone and is logged at debug.

        Until G54 the per-zone path ran its own pandas-ta ZigZag **without**
        ``backtest=True`` — the repainting, centred detector that #110 removed
        from the global pass — so ``per_zone`` and ``global`` compared two
        algorithms, not two scopes: on 17 of the 18 sample zones longer than
        20 bars the two placed their pivots on different bars.
        """

        report = logger.warning if scope == 'global' else logger.debug
        self._validate_input(full_data)

        if len(full_data) < self.legs * 2:
            report(
                "ZigZag %s: data too short (%d bars, need >= %d). "
                "Returning empty SwingContext.",
                scope,
                len(full_data),
                self.legs * 2,
            )
            return self._empty_context(len(full_data), degraded='too_short')

        if self._is_degenerate(full_data):
            report(
                "ZigZag %s: degenerate input (near-constant high/low). "
                "Skipping pandas-ta zigzag and returning empty SwingContext.",
                scope,
            )
            return self._empty_context(len(full_data), degraded='degenerate')

        from .....indicators import LibraryManager

        # ZigZag relies on the pandas-ta 'zigzag' indicator. Until G70 an unavailable
        # detector degraded to an empty context on BOTH scopes, so a caller who asked
        # for ZigZag got a successful result with zero swings — the same object a
        # still market produces (measured: 30 zones, 29 with swings against 30 zones,
        # 0 with swings). The global pass now refuses, for the reason G54 refuses a
        # failed global pass: whoever asked for this detector did not get it. Inside a
        # zone the run continues, but the metrics carry `degraded`.
        try:
            zigzag = LibraryManager.create_indicator(
                'pandas_ta',
                'zigzag',
                legs=self.legs,
                # Процент, как читает библиотека (G86). Не делить и не умножать: число
                # уходит как есть, и имя колонки в ответе (`ZIGZAGs_<число>%_<legs>`)
                # печатает ту же единицу — это оракул, на который смотрит сторож.
                deviation=self.deviation_pct,
                # Issue #110: the default (backtest=False) is a repainting, centred
                # detector — truncating the raw series at as_of relocates/adds/drops
                # earlier pivots, so a pivot with confirmation_index <= as_of is not
                # actually observable then. backtest=True is the non-repainting
                # stream: once a pivot is emitted it never changes under extension
                # (verified empirically in tests/unit/test_swing_replay_causal.py).
                backtest=True,
            )
            result = zigzag.calculate(full_data)
        except Exception as exc:
            if scope == 'global':
                # Текст переписан в G84. Прежний утверждал «the library is not
                # installed or has no indicator by that name» — и это оказалось ложным
                # диагнозом в самом частом случае: библиотека установлена,
                # `pandas_ta.zigzag` на месте, а записи пропали из фабрики. Читателя
                # отправляли переустанавливать то, что стоит. Прежний текст также
                # советовал перейти в `per_zone`, не называя цену: тот режим продолжит
                # работу, но каждая затронутая зона получит
                # `swing_metrics['degraded'] == 'detector_unavailable'`, и этот признак
                # надо читать — иначе нули выглядят измерением.
                raise AnalysisError(
                    f"ZigZag global pass could not run: the 'zigzag' detector was not "
                    f"obtained from the indicator factory ({exc}). The result would be a "
                    f"successful run with zero swings, indistinguishable from a market "
                    f"that did not move. Check that pandas-ta is installed and exposes "
                    f"'zigzag', that BQUANT_SKIP_PANDAS_TA is unset, and that nothing "
                    f"cleared the factory registry in this process; or ask for another "
                    f"swing strategy. Scope 'per_zone' would continue instead of "
                    f"refusing, marking every affected zone with "
                    f"swing_metrics['degraded'] == 'detector_unavailable' — readable, "
                    f"but only if you read it."
                ) from exc
            report(
                "ZigZag %s: pandas-ta 'zigzag' unavailable (%s). "
                "Returning empty SwingContext.",
                scope,
                exc,
            )
            return self._empty_context(len(full_data), degraded='detector_unavailable')

        if result.data.shape[1] < 2:
            report("ZigZag %s: insufficient columns returned, no swings detected", scope)
            return self._empty_context(len(full_data), degraded='detector_unavailable')

        swing_values = result.data.iloc[:, 1].dropna()

        if len(swing_values) < 2:
            report("ZigZag %s: fewer than two swing points detected", scope)
            return self._empty_context(len(full_data))

        swing_points: List[SwingPoint] = []
        indices: List[int] = []

        timestamps = swing_values.index.to_list()
        prices = swing_values.to_list()

        high_arr = full_data['high'].to_numpy(dtype=float)
        low_arr = full_data['low'].to_numpy(dtype=float)

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
            confirmation_index: Optional[int] = None
            if point_id < len(prices) - 1:
                next_price = prices[point_id + 1]
                next_timestamp = timestamps[point_id + 1]
                next_position_arr = full_data.index.get_indexer([next_timestamp])
                if -1 not in next_position_arr:
                    next_position = int(next_position_arr[0])
                    if price != 0:
                        amplitude_to_next = (next_price / price - 1) * 100
                    duration_to_next = max(0, next_position - position)
                    confirmation_index = self._confirmation_index(
                        position, next_position, float(price), swing_type,
                        high_arr, low_arr,
                    )

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
                    strategy_params=self._params(),
                    confirmation_index=confirmation_index,
                )
            )
            indices.append(position)

        # Warm-up (issue #110): the backtest=True detector emits nothing until the
        # second swing forms, so the first two pivots become observable *together*.
        # The first pivot's own deviation-retrace can therefore fall a few bars before
        # the detector actually reports it — pin its availability to the second
        # pivot's (the bar they both first appear at). Later pivots' retrace times are
        # already safe (empirically confirmation_index >= first-appearance).
        if len(swing_points) >= 2 and swing_points[0].confirmation_index is not None \
                and swing_points[1].confirmation_index is not None:
            swing_points[0].confirmation_index = max(
                swing_points[0].confirmation_index,
                swing_points[1].confirmation_index,
            )

        # Nothing is observable before the detector can run at all: this method
        # returns an empty context for fewer than ``legs * 2`` bars, so a pivot
        # claiming confirmation earlier than bar ``legs * 2 - 1`` claims a bar on
        # which a truncated replay would find nothing. Inside short zones the
        # first pivots do land that early (G54: bars 2 and 3 confirmed "at 4"
        # with a six-bar floor); on the full sample they never did, which is why
        # the global oracle never met the case.
        first_observable = self.legs * 2 - 1
        for point in swing_points:
            if point.confirmation_index is not None and point.confirmation_index < first_observable:
                point.confirmation_index = first_observable

        (logger.info if scope == 'global' else logger.debug)(
            "ZigZag %s: detected %d swing points", scope, len(swing_points)
        )

        return SwingContext(
            swing_points=swing_points,
            indices=np.asarray(indices, dtype=int),
            full_data_length=len(full_data),
            strategy_name='zigzag',
            strategy_params=self._params(),
        )

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Aggregate global swing context for a single zone."""

        zone_swings = context.get_swings_for_zone(zone)

        if len(zone_swings) < 2:
            logger.debug(
                "Zone %s: insufficient swings (%d points)", zone.zone_id, len(zone_swings)
            )
            return self._empty_metrics(context.degraded)

        rallies, drops = self._build_movements_from_points(zone_swings)
        return self._aggregate_metrics(rallies, drops)

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate comprehensive swing metrics using ZigZag algorithm on the
        zone's own bars.

        The same detector and the same movement arithmetic as the global pass
        (:meth:`calculate_global` + :meth:`aggregate_for_zone`); the only
        difference is what the detector sees — this zone, nothing outside it.

        Args:
            zone_data: DataFrame with columns: high, low, close, open

        Returns:
            SwingMetrics with all 23 fields populated

        Raises:
            ValueError: If zone_data is empty or missing required columns
        """
        context = self._swing_context(zone_data, scope='per_zone')
        if len(context.swing_points) < 2:
            return self._empty_metrics(context.degraded)
        rallies, drops = self._build_movements_from_points(context.swing_points)
        return self._aggregate_metrics(rallies, drops)

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
            strategy_params=self._params(),
        )

        metrics.validate()

        logger.debug(
            "ZigZag metrics calculated: %d rallies, %d drops, ratio=%.2f",
            rally_count,
            drop_count,
            rally_to_drop_ratio,
        )

        return metrics

    def _params(self) -> Dict[str, Any]:
        return {
            'legs': self.legs,
            'deviation_pct': self.deviation_pct,
            'confirmation_retrace_pct': self.confirmation_retrace_pct,
        }

    def _confirmation_index(
        self,
        position: int,
        next_position: int,
        price: float,
        swing_type: str,
        high_arr: np.ndarray,
        low_arr: np.ndarray,
    ) -> int:
        """Bar by which this ZigZag pivot is causally confirmed.

        A peak is confirmed at the first bar after ``position`` whose low has
        fallen ``confirmation_retrace_pct`` percent below the pivot price; a trough,
        at the first bar whose high has risen that much above it. This is the
        ZigZag-specific realisation of the generic
        :attr:`SwingPoint.confirmation_index` contract: the point at which a
        repainting ZigZag "locks in" the previous swing, i.e. when the next leg
        starts drawing. ``next_position`` is the safe upper bound if no earlier
        crossing is found.

        The retrace is deliberately **not** ``deviation_pct`` (G86): the next pivot
        is itself the first bar where the retrace exceeded the detection threshold,
        so a confirmation defined through the same number would land on the next
        pivot by construction — measured 99.2 % of pairs — and the causal label
        would carry no information.
        """
        retrace = self.confirmation_retrace_pct / 100.0
        if next_position <= position:
            conf = next_position
        else:
            if swing_type == 'peak':
                threshold = price * (1.0 - retrace)
                seg = low_arr[position + 1:next_position + 1]
                hits = np.nonzero(seg <= threshold)[0]
            else:
                threshold = price * (1.0 + retrace)
                seg = high_arr[position + 1:next_position + 1]
                hits = np.nonzero(seg >= threshold)[0]
            conf = position + 1 + int(hits[0]) if len(hits) else next_position
        return conf

    def _empty_metrics(self, degraded: Optional[str] = None) -> SwingMetrics:
        metrics = self._aggregate_metrics([], [])
        metrics.degraded = degraded
        return metrics

    def _empty_context(
        self, full_data_length: int, degraded: Optional[str] = None
    ) -> SwingContext:
        return SwingContext(
            swing_points=[],
            indices=np.array([], dtype=int),
            full_data_length=full_data_length,
            strategy_name='zigzag',
            strategy_params=self._params(),
            degraded=degraded,
        )

    def _is_degenerate(self, data: pd.DataFrame) -> bool:
        """
        Detect input that makes pandas-ta's numba ZigZag segfault.

        The nopython ZigZag kernel has no bounds checking and crashes (native
        SIGSEGV/SIGABRT, uncatchable by try/except) when ``high`` or ``low`` is
        (near-)constant, i.e. lacks enough distinct levels to form pivots over
        ``legs``-bar windows. Real OHLC data has hundreds of distinct levels and
        is never flagged; only degenerate/flat segments are. See
        devref/gaps/zo/zo_issue_numba_linux_testsuite_2026-07.md.
        """
        return (
            data['high'].nunique() < self.legs
            or data['low'].nunique() < self.legs
        )

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
            'params': self._params(),
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
        return self._params()

