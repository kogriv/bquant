"""Utilities for calculating adaptive swing thresholds."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    Deriving the floor from the *zone* scale instead — dropping the 0.01 floor — is a
    separate, measured direction: it takes those two to 84.4 %. It is not shipped here
    because higher coverage is not by itself evidence that the extra swings are real.
    See ``devref/gaps/swing/g38_adaptive_thresholds_restore_the_threshold_g35_removed_2026-08.md``.
    """

    #: relative price move required by ZigZag
    zigzag_deviation: float


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
        return SwingThresholds(zigzag_deviation=base_deviation)

    if not {"high", "low", "close"}.issubset(zone_df.columns):
        raise KeyError("Zone dataframe must contain 'high', 'low', and 'close' columns")

    price_range = float(zone_df["high"].max() - zone_df["low"].min())
    mid_price = _safe_mid_price(zone_df["close"])

    if not mid_price:
        relative_range = base_deviation
    else:
        relative_range = price_range / mid_price

    deviation = max(base_deviation, relative_range * 0.5)

    return SwingThresholds(zigzag_deviation=deviation)


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
        # find_peaks and pivot_points are deliberately left alone.
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
        # Only what is applied is reported. The two amplitude floors were removed in
        # G38 together with the fields behind them: a metadata key naming a threshold
        # that reaches no strategy is a claim the run cannot support.
        return {'zigzag_deviation': thresholds.zigzag_deviation}
