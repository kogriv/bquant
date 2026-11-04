"""Trades from zones: zones + bars (+ signals) + rules → the trade frame of :mod:`~bquant.analysis.evaluation`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ...data.processor import calculate_atr
from ..evaluation.costs import CostModel, rollover_nights
from .inputs import bar_length, signal_table, zones_frame
from .rules import (
    ColumnStop,
    Entry,
    Exit,
    ExitAt,
    FixedAtrStop,
    Horizon,
    NextOpen,
    SignalThreshold,
    Stop,
    TakeProfit,
    TrailingAfterSignal,
    ZoneBarClose,
    ZoneChange,
)

TRADE_COLUMNS = (
    "zone_id", "k", "side", "decision_time", "entry_time", "exit_time", "hold", "mode", "exit_reason",
    "entry_price", "exit_price", "atr_points", "gross_points", "cost_points", "nights", "net_points",
    "gross", "net", "mfe", "mae", "dur", "stop_and_take_same_bar",
)
SKIPPED_COLUMNS = ("zone_id", "reason")


@dataclass(frozen=True, eq=False)
class ZoneTrades:
    """What :func:`zone_trades` returns: the trades, and the zones that gave none and why.

    ``trades`` is a trade frame :func:`~bquant.analysis.evaluation.validate_trades`
    accepts: ``net`` and ``gross`` are in ATR of the decision bar, ``mode`` is the name
    of the exit rule (one per call — a key for
    :func:`~bquant.analysis.evaluation.random_entry_baseline`), ``exit_reason`` what
    actually closed the trade. ``skipped`` has ``zone_id`` and ``reason``:
    ``zone_shorter_than_k``, ``no_next_bar``, ``atr_nan_at_decision_bar``, ``no_side``,
    ``exit_before_entry``, ``exit_beyond_data``.
    """

    trades: pd.DataFrame
    skipped: pd.DataFrame


class _Skip(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class _Builder:
    def __init__(self, bars, signals, point, atr, costs, triple_weekday):
        self.n = len(bars)
        self.index = bars.index
        self.o, self.h, self.l, self.c = (bars[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
        self.spread = bars["spread"].to_numpy(dtype=float) if "spread" in bars.columns else None
        self.atr = atr
        self.point = point
        self.costs = costs
        self.triple = triple_weekday
        self.signals = signals

    # ------------------------------------------------------------------ signals
    def _signal(self, zid, k, column, purpose):
        rows = self.signals.get(zid)
        if rows is None or k not in rows.index:
            raise ValueError(f"{purpose} needs the signal row (zone_id={zid!r}, k={k}), and there is none")
        if column not in rows.columns:
            raise ValueError(f"{purpose} needs the signal column {column!r}, and the signal frame has none")
        return rows.at[k, column]

    def _first_signal_bar(self, zone, k, rule):
        rows = self.signals.get(zone.zone_id)
        if rows is None:
            return None
        if rule.signal not in rows.columns:
            raise ValueError(f"{rule.name} needs the signal column {rule.signal!r}, and the signal frame has none")
        for age, row in rows.iterrows():
            if age < rule.k_min or age <= k:
                continue
            value = row[rule.signal]
            if pd.isna(value) or value < rule.thr:
                continue
            if any(row[col] != val for col, val in rule.require.items()):
                continue
            return zone.start_idx + int(age)
        return None

    # ------------------------------------------------------------------ steps
    def entry(self, zone, rule: Entry):
        s, e = zone.start_idx, zone.end_idx
        if isinstance(rule, ZoneBarClose):
            j = s + rule.k
            if j > e:
                raise _Skip("zone_shorter_than_k")
            entry_idx, entry_price = j, self.c[j]
        else:
            j = s
            if j + 1 >= self.n:
                raise _Skip("no_next_bar")
            entry_idx, entry_price = j + 1, self.o[j + 1]
        if not np.isfinite(self.atr[j]):
            raise _Skip("atr_nan_at_decision_bar")
        if rule.side == "signal":
            value = self._signal(zone.zone_id, rule.k, rule.side_column, "side='signal'")
            if pd.isna(value) or value == 0:
                raise _Skip("no_side")
            side = 1 if value > 0 else -1
        else:
            side = int(zone.side) if rule.side == "zone" else -int(zone.side)
        return j, entry_idx, entry_price, side

    def rule_exit(self, zone, rule: Exit, j, k, entry_idx, entry_price, side, unit) -> Tuple[int, float, str]:
        if isinstance(rule, ZoneChange):
            x = zone.end_idx + 1
            if x >= self.n:
                raise _Skip("exit_beyond_data")
            return x, self.c[x], "zone_change"
        if isinstance(rule, Horizon):
            x, reason = j + rule.h, "horizon"
            if rule.cap is not None and x >= zone.end_idx + 1:
                x, reason = zone.end_idx + 1, "zone_change"     # not later than the zone change
            if x >= self.n:
                raise _Skip("exit_beyond_data")
            return x, self.c[x], reason
        if isinstance(rule, ExitAt):
            wanted = int(zone.exit_idx)
            if wanted <= j:
                raise _Skip("exit_before_entry")
            x = min(wanted, zone.end_idx + 1)
            if x >= self.n:
                raise _Skip("exit_beyond_data")
            return x, self.c[x], "exit_at" if wanted < zone.end_idx + 1 else "zone_change"
        x_fb, price_fb, _ = self.rule_exit(zone, rule.fallback, j, k, entry_idx, entry_price, side, unit)
        if isinstance(rule, (SignalThreshold, TrailingAfterSignal)):
            x_s = self._first_signal_bar(zone, k, rule)
            if x_s is None:
                return x_fb, price_fb, "fallback"
            if isinstance(rule, SignalThreshold):
                return x_s, self.c[x_s], "signal"
            path = side * (self.c[x_s:x_fb + 1] - entry_price) / unit
            give_back = np.maximum.accumulate(path) - path
            hit = np.flatnonzero(give_back >= rule.s_atr)
            if len(hit):
                x = x_s + int(hit[0])
                return x, self.c[x], "trail"
            return x_fb, price_fb, "fallback"
        target = entry_price + side * self._take_level(zone, k, rule) * unit
        for i in range(j + 1, x_fb + 1):
            if (side > 0 and self.h[i] >= target) or (side < 0 and self.l[i] <= target):
                return i, target, "take"
        return x_fb, price_fb, "fallback"

    def _take_level(self, zone, k, rule: TakeProfit) -> float:
        if rule.level_atr is not None:
            return float(rule.level_atr)
        forecast = self._signal(zone.zone_id, k, rule.forecast, "TakeProfit(share_of_forecast)")
        return float(rule.share_of_forecast) * float(forecast)

    def stop_level(self, zone, k, stop: Optional[Stop]) -> Optional[float]:
        if stop is None:
            return None
        if isinstance(stop, FixedAtrStop):
            return float(stop.value)
        value = self._signal(zone.zone_id, k, stop.column, f"ColumnStop({stop.column!r})")
        if pd.isna(value) or not value > 0:
            raise ValueError(f"the stop column {stop.column!r} at (zone_id={zone.zone_id!r}, k={k}) is {value!r}, not a positive distance")
        return float(value)

    def trade(self, zone, entry: Entry, exit_: Exit, stop: Optional[Stop]) -> Dict[str, Any]:
        j, entry_idx, entry_price, side = self.entry(zone, entry)
        k = entry.k
        atr_points = float(self.atr[j])
        unit = atr_points * self.point                     # one ATR of the decision bar, in price
        x, exit_price, reason = self.rule_exit(zone, exit_, j, k, entry_idx, entry_price, side, unit)
        level = self.stop_level(zone, k, stop)
        both = False
        if level is not None:
            stop_price = entry_price - side * level * unit
            for i in range(j + 1, x + 1):
                if (side > 0 and self.l[i] <= stop_price) or (side < 0 and self.h[i] >= stop_price):
                    x, exit_price, reason = i, stop_price, "stop"      # the stop wins its bar
                    break
            if reason == "stop" and isinstance(exit_, TakeProfit):
                target = entry_price + side * self._take_level(zone, k, exit_) * unit
                both = bool((side > 0 and self.h[x] >= target) or (side < 0 and self.l[x] <= target))
        high, low = self.h[j + 1:x + 1].max(), self.l[j + 1:x + 1].min()
        favourable = (high - entry_price) if side > 0 else (entry_price - low)
        adverse = (entry_price - low) if side > 0 else (high - entry_price)
        gross_points = side * (exit_price - entry_price) / self.point
        nights = int(rollover_nights(self.index[entry_idx], self.index[x] + self.bar, triple_weekday=self.triple)[0])
        if self.costs is None:
            cost = 0.0
        else:
            cost = float(self.costs.round_trip(self.spread, [entry_idx], [side], [nights])[0])
        net_points = gross_points - cost
        return {
            "zone_id": zone.zone_id, "k": k, "side": side,
            "decision_time": self.index[j], "entry_time": self.index[entry_idx], "exit_time": self.index[x],
            "hold": int(x - j), "mode": exit_.name, "exit_reason": reason,
            "entry_price": float(entry_price), "exit_price": float(exit_price), "atr_points": atr_points,
            "gross_points": gross_points, "cost_points": cost, "nights": nights, "net_points": net_points,
            "gross": gross_points / atr_points, "net": net_points / atr_points,
            "mfe": max(0.0, favourable / unit), "mae": max(0.0, adverse / unit),
            "dur": int(zone.end_idx + 1 - zone.start_idx), "stop_and_take_same_bar": both,
        }


def zone_trades(
    bars: pd.DataFrame,
    zones: Any,
    *,
    point: float,
    entry: Entry = ZoneBarClose(),
    exit: Exit = ZoneChange(),
    stop: Optional[Stop] = None,
    costs: Optional[CostModel] = None,
    signals: Optional[pd.DataFrame] = None,
    atr: Optional[Any] = None,
    atr_period: int = 14,
    bar: Optional[pd.Timedelta] = None,
) -> ZoneTrades:
    """Build one trade per zone by the rules given; see :mod:`.rules` for each rule.

    ``bars`` — OHLC with a ``DatetimeIndex`` on the broker's server clock (and a
    ``spread`` column in points when ``costs`` takes the spread of the bar). ``zones`` —
    a frame with ``zone_id, start_idx, end_idx, side`` (positions in ``bars``), or the
    result of :func:`~bquant.analysis.zones.analyze_zones` / a list of its zones
    (``bull`` → +1, ``bear`` → -1). ``signals`` — rows keyed by ``zone_id`` and ``k``
    (a snapshot at the close of bar ``s + k``) for the rules that read them.

    ``point`` is the price of one point. ``atr`` is in **price** (default: Wilder's ATR
    of ``atr_period`` from :func:`~bquant.data.calculate_atr`); the outcome unit is
    ``atr[j]`` of the decision bar. ``costs`` is a
    :class:`~bquant.analysis.evaluation.CostModel` (spread of the **entry** bar) or
    ``None`` for no costs; the nights are counted either way, closing at the end of the
    exit bar, with the triple night of ``costs`` (Wednesday without a model). ``bar`` —
    the length of one bar, by default the most common step of the index.

    A stop is checked on every bar of the window ``j + 1 … x`` and wins its bar over a
    take, a signal or the exit rule: the order inside a bar is not known. At a stop the
    gross outcome is exactly minus its distance; MFE and MAE are taken over the window
    actually held.
    """
    if not isinstance(bars, pd.DataFrame) or not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("bars must be a DataFrame with a DatetimeIndex (server time)")
    missing = [c for c in ("open", "high", "low", "close") if c not in bars.columns]
    if missing:
        raise ValueError(f"bars have no {missing}")
    if isinstance(point, bool) or not isinstance(point, (int, float)) or not point > 0:
        raise ValueError(f"point must be a positive number, got {point!r}")
    for value, kinds, name in ((entry, (ZoneBarClose, NextOpen), "entry"),
                               (exit, (ZoneChange, Horizon, SignalThreshold, TrailingAfterSignal, TakeProfit, ExitAt), "exit")):
        if not isinstance(value, kinds):
            raise ValueError(f"{name} must be one of {[k.__name__ for k in kinds]}, got {value!r}")
    if stop is not None and not isinstance(stop, (FixedAtrStop, ColumnStop)):
        raise ValueError(f"stop must be FixedAtrStop, ColumnStop or None, got {stop!r}")
    if costs is not None and not isinstance(costs, CostModel):
        raise ValueError(f"costs must be a CostModel or None, got {costs!r}")
    if costs is not None and costs.spread == "bar" and "spread" not in bars.columns:
        raise ValueError("this cost model takes the spread of the entry bar, and the bars have no 'spread' column")

    if atr is None:
        atr_price = calculate_atr(bars, period=atr_period, method="wilder").to_numpy(dtype=float)
    else:
        atr_price = np.asarray(atr, dtype=float)
        if atr_price.shape != (len(bars),):
            raise ValueError(f"atr must have one value per bar ({len(bars)}), got shape {atr_price.shape}")

    frame = zones_frame(zones, len(bars), exit.column if isinstance(exit, ExitAt) else None)
    builder = _Builder(bars, signal_table(signals), float(point), atr_price / float(point), costs,
                       costs.triple_weekday if costs is not None else 2)
    builder.bar = pd.Timedelta(bar) if bar is not None else bar_length(bars.index)

    trades: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for zone in frame.itertuples(index=False):
        try:
            trades.append(builder.trade(zone, entry, exit, stop))
        except _Skip as why:
            skipped.append({"zone_id": zone.zone_id, "reason": why.reason})
    return ZoneTrades(
        trades=pd.DataFrame(trades, columns=list(TRADE_COLUMNS)),
        skipped=pd.DataFrame(skipped, columns=list(SKIPPED_COLUMNS)),
    )
