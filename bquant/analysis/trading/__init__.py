"""Trades built from zones by pluggable rules.

:func:`zone_trades` takes zones (a frame, or the result of
:func:`~bquant.analysis.zones.analyze_zones`), bars and optionally per-zone signals, and
returns the trade frame :mod:`bquant.analysis.evaluation` reads — one trade per zone,
by an entry rule, an exit rule, an optional stop and a
:class:`~bquant.analysis.evaluation.CostModel`. Zones that give no trade come back with
a named reason. The rules are objects, not strings:

* entries — :class:`ZoneBarClose` (close of the zone's bar of age ``k``),
  :class:`NextOpen` (open of the bar after the decision);
* exits — :class:`ZoneChange`, :class:`Horizon`, :class:`SignalThreshold`,
  :class:`TrailingAfterSignal`, :class:`TakeProfit`;
* stops — :class:`FixedAtrStop`, :class:`ColumnStop`.

The outcome is in ATR of the decision bar (Wilder's, by default).
"""

from .rules import (
    ColumnStop,
    FixedAtrStop,
    Horizon,
    NextOpen,
    SignalThreshold,
    TakeProfit,
    TrailingAfterSignal,
    ZoneBarClose,
    ZoneChange,
    describe,
)
from .zone_trades import TRADE_COLUMNS, ZoneTrades, zone_trades

__all__ = [
    "zone_trades", "ZoneTrades", "TRADE_COLUMNS",
    "ZoneBarClose", "NextOpen",
    "ZoneChange", "Horizon", "SignalThreshold", "TrailingAfterSignal", "TakeProfit",
    "FixedAtrStop", "ColumnStop",
    "describe",
]
