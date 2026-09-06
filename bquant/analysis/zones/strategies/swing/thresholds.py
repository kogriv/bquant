"""Utilities for calculating adaptive swing thresholds."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import numpy as np

import pandas as pd

from ...models import SwingContext, ZoneInfo
from ..base import SwingMetrics
from ..registry import StrategyRegistry


@dataclass(frozen=True)
class SwingThresholds:
    """The swing threshold this layer adapts. One value, because one is applied.

    **The field is RELATIVE — a fraction of price, never an amount of price.** It is
    derived as ``price_range / mid_price * k``, so 0.019 means 1.9%. Routing such a
    value into a knob that expects absolute price units was gap G16: a fraction of
    ~0.019 handed to scipy's ``prominence``, on an instrument trading near 3350, reads
    as under two cents and switches the filter off.

    The class carried two more fields — ``peak_min_amplitude`` and ``pivot_deviation``,
    the amplitude floors for find_peaks and pivot_points. They were measured out in G38.
    Both were computed as ``max(base_deviation, range * k)``, and on zones of ordinary
    size the ``base_deviation`` floor of 0.01 always won — while the ``narrow_zone``
    preset asks for 0.006 and the median zone moves 0.0075. So the "adaptive" value was
    a constant, it was larger than the preset it replaced, and it put the threshold
    above the movement it had to admit. Measured on 77 zones of ``tv_xauusd_1h``:

    =============  ==========  ==============
    strategy       adaptive    layer disabled
    =============  ==========  ==============
    find_peaks     0 %         36.4 %
    pivot_points   0 %         49.4 %
    zigzag         90.9 %      90.9 %
    =============  ==========  ==============

    Two of three strategies were switched off by a mode advertised as adaptation, and
    the third was unaffected. Keeping the fields would mean computing and reporting
    thresholds nobody applies, so they are gone rather than merely unused.

    Deriving the floor from the *zone* scale instead — dropping the 0.01 constant — took
    those two to 84.4 %, and G48 (2026-09-06) proved it by criterion rather than by
    coverage: the set of global swing points is **identical** under the preset floor and
    the zone-scale floor (366 = 366 on ``tv_xauusd_1h``), so the layer admits no new
    pivot — it only stops discarding movements between pivots that ZigZag confirms at
    99–100 % (±2 bars); the metrics computed from them do not degenerate; the ceiling of
    65/77 is zone length (10 of 12 uncovered zones are shorter than the strategy's
    minimum bars); and on ``mt_xauusd_m15`` the constant preset floor gave 3 of 91 zones,
    the zone scale 69–74. The constant floor is replaced by a floor **from the data**:
    the median relative range of one bar. That is ``min_amplitude_pct`` below.
    See ``devref/gaps/swing/g48_zone_scale_thresholds_measured_but_unproven_2026-09.md``.
    """

    #: relative price move required by ZigZag
    zigzag_deviation: float
    #: relative amplitude floor for ``find_peaks`` / ``pivot_points`` — the zone scale
    #: (G48, 2026-09-06): ``max(bar_floor, median zone range × k)``. ``None`` means the
    #: strategy keeps the floor it was constructed with (ZigZag: always ``None``).
    min_amplitude_pct: Optional[float] = None


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


#: Множители плеча G48 — те же 0.3 / 0.25, что стояли в этом слое до G38.
ZONE_SCALE_K: Dict[str, float] = {"find_peaks": 0.3, "pivot_points": 0.25}


def relative_range(frame: pd.DataFrame) -> Optional[float]:
    """Размах кадра долей цены: ``(high.max − low.min) / медиана close``; ``None`` без цены."""
    if frame.empty:
        return None
    mid_price = _safe_mid_price(frame["close"])
    if not mid_price:
        return None
    return float(frame["high"].max() - frame["low"].min()) / mid_price


def bar_floor(frame: pd.DataFrame) -> float:
    """Пол от данных: медианный относительный размах одного бара.

    Движение меньше типичного бара лежит внутри бара и порогом амплитуды быть не
    может. Это замена константе ``base_deviation = 0.01``, которая на зонах обычного
    размера стояла выше и пресета, и самого движения зоны (G38).
    """
    if frame.empty:
        return 0.0
    bars = (frame["high"] - frame["low"]) / frame["close"]
    value = float(bars.median())
    return value if np.isfinite(value) and value > 0 else 0.0


def zone_scale_amplitude(zone_ranges: Sequence[float], k: float, floor: float) -> float:
    """Порог амплитуды от масштаба зон: ``max(floor, медиана размахов × k)`` (G48)."""
    ranges = np.asarray([r for r in zone_ranges if r is not None and np.isfinite(r)], dtype=float)
    if len(ranges) == 0:
        raise ValueError("zone_scale_amplitude: no zone ranges to take the scale from")
    return max(float(floor), float(np.median(ranges)) * k)


def auto_swing_thresholds(
    zone_df: pd.DataFrame,
    *,
    base_deviation: float = 0.01,
    amplitude_k: Optional[float] = None,
    zone_ranges: Optional[Sequence[float]] = None,
) -> SwingThresholds:
    """Пороги свингов из данных: ``deviation`` ZigZag от размаха кадра и, если задан
    ``amplitude_k``, амплитудный пол от масштаба зон (``zone_ranges``; без них — от
    размаха самого ``zone_df``, это режим ``per_zone``)."""

    if zone_df.empty:
        return SwingThresholds(zigzag_deviation=base_deviation)

    if not {"high", "low", "close"}.issubset(zone_df.columns):
        raise KeyError("Zone dataframe must contain 'high', 'low', and 'close' columns")

    frame_range = relative_range(zone_df)
    deviation = max(base_deviation, (frame_range if frame_range is not None else base_deviation) * 0.5)

    min_amplitude_pct = None
    if amplitude_k is not None:
        ranges = list(zone_ranges) if zone_ranges is not None else [frame_range]
        min_amplitude_pct = zone_scale_amplitude(ranges, amplitude_k, bar_floor(zone_df))

    return SwingThresholds(zigzag_deviation=deviation, min_amplitude_pct=min_amplitude_pct)


class AdaptiveSwingStrategy:
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
        self._zone_ranges: Optional[Sequence[float]] = None

    @property
    def amplitude_k(self) -> Optional[float]:
        """Множитель плеча G48 для этой стратегии; ``None`` — слой её амплитуду не трогает."""
        return ZONE_SCALE_K.get(self.base_strategy_name)

    def set_zone_scale(self, zone_ranges: Sequence[float]) -> None:
        """Сообщить слою масштаб зон (относительные размахи) перед ``calculate_global``.

        В ``global`` свинги считаются на всём кадре до того, как известна хоть одна
        зона, а порог амплитуды — свойство зоны, не кадра. Поэтому пайплайн с G48
        детектирует зоны первыми и отдаёт их размахи сюда.
        """
        self._zone_ranges = list(zone_ranges)

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Calculate global swings with adaptive thresholds applied once."""

        if self.amplitude_k is not None and self._zone_ranges is None:
            raise ValueError(
                f"Adaptive {self.base_strategy_name}: the amplitude floor is the zone "
                "scale, and no zone scale was given — call set_zone_scale(zone_ranges) "
                "first (the pipeline does, after detecting zones), or run per_zone"
            )
        thresholds = auto_swing_thresholds(
            full_data,
            base_deviation=self._base_deviation,
            amplitude_k=self.amplitude_k,
            zone_ranges=self._zone_ranges,
        )
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
        """Пороги для одной зоны (``per_zone``): масштаб — размах самой зоны."""
        return auto_swing_thresholds(
            data, base_deviation=self._base_deviation, amplitude_k=self.amplitude_k
        )

    def _apply_thresholds_to_strategy(
        self,
        strategy,
        thresholds: SwingThresholds,
    ) -> None:
        if self.base_strategy_name == 'zigzag':
            strategy.deviation = thresholds.zigzag_deviation
        elif thresholds.min_amplitude_pct is not None and self.amplitude_k is not None:
            # G48: the floor is the zone scale, floored by the data's own bar range —
            # never the 0.01 constant that G38 measured as switching both strategies off.
            strategy.min_amplitude_pct = thresholds.min_amplitude_pct
        # `prominence` of find_peaks is deliberately left alone.
        #
        # `prominence` was removed first (G16): it is absolute, an amount of price, and
        # a fraction assigned to it read as under two cents and switched the filter off.
        # `min_amplitude_pct` survived that round because it is relative, so the units
        # matched — but matching units is not the same as a meaningful value, and G38
        # measured what the value did: it zeroed both strategies outright, because the
        # `max(base_deviation, ...)` floor of 0.01 stands above both the preset (0.006)
        # and the median zone's own movement (0.0075). A threshold above the movement it
        # must admit admits nothing, and "no swings" is indistinguishable from "the
        # market stood still".
        #
        # So this layer adapts ZigZag's `deviation` and nothing else. Both strategies
        # keep the preset's floor, which is what they use with the layer switched off,
        # and find_peaks keeps its own range-adaptive, warm-up-frozen prominence (G15).

    @staticmethod
    def _thresholds_to_dict(thresholds: SwingThresholds) -> Dict[str, float]:
        # Only what is applied is reported: a metadata key naming a threshold that
        # reaches no strategy is a claim the run cannot support (G38).
        out = {'zigzag_deviation': thresholds.zigzag_deviation}
        if thresholds.min_amplitude_pct is not None:
            out['min_amplitude_pct'] = thresholds.min_amplitude_pct
        return out
