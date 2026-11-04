"""The outcome at a given exit bar, for every zone at once and for many sets of exit bars.

A placebo recomputes the outcome for hundreds of shuffled exit bars. Calling
:func:`~bquant.analysis.trading.zone_trades` with :class:`~.ExitAt` per set would rebuild
every trade in Python each time; here the parts that depend only on the zone — the entry,
the stop level, the first bar that touches the stop, the running high and low of the
window — are computed once, and every set of exit bars is a vectorised lookup into them.

The result is the same, bit for bit, as ``zone_trades(..., exit=ExitAt())`` on the same
exit bars.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd

from ...data.processor import calculate_atr
from ..evaluation.costs import CostModel, rollover_nights
from .rules import ColumnStop, Entry, FixedAtrStop, NextOpen, Stop, ZoneBarClose
from .inputs import bar_length, signal_table, zones_frame
from .zone_trades import SKIPPED_COLUMNS, TRADE_COLUMNS, ZoneTrades


@dataclass(frozen=True, eq=False)
class ExitMatrix:
    """Outcomes for ``n_sets`` sets of exit bars over ``n_zones`` zones (rows × columns).

    ``net`` and ``gross`` are in ATR of the decision bar, ``hold`` in bars; a cell without
    a trade is ``NaN`` there, and ``skip_reason`` names why (otherwise ``None``).
    ``exit_reason`` is ``exit_at``, ``zone_change`` or ``stop`` (``None`` when skipped).
    Columns follow the order of the zone frame, ``zone_id`` gives their ids.
    """

    zone_id: np.ndarray
    net: np.ndarray
    gross: np.ndarray
    hold: np.ndarray
    exit_reason: np.ndarray
    skip_reason: np.ndarray


class _Zones:
    """Everything about the zones that does not depend on the exit bar."""

    def __init__(self, bars, frame, entry, stop, costs, signals, point, atr_price, bar):
        n = len(bars)
        self.n = n
        self.index = bars.index
        self.c = bars["close"].to_numpy(dtype=float)
        o = bars["open"].to_numpy(dtype=float)
        h = bars["high"].to_numpy(dtype=float)
        l = bars["low"].to_numpy(dtype=float)
        self.spread = bars["spread"].to_numpy(dtype=float) if "spread" in bars.columns else None
        self.point = point
        self.costs = costs
        self.triple = costs.triple_weekday if costs is not None else 2
        self.bar = bar
        atr = atr_price / point

        zid = frame["zone_id"].to_numpy()
        s = frame["start_idx"].to_numpy(dtype=np.int64)
        e = frame["end_idx"].to_numpy(dtype=np.int64)
        zside = frame["side"].to_numpy(dtype=np.int64)
        self.zone_id, self.end = zid, e
        k = entry.k
        skip = np.full(len(frame), None, dtype=object)

        if isinstance(entry, ZoneBarClose):
            j = s + k
            skip[j > e] = "zone_shorter_than_k"
            entry_idx = j.copy()
            safe = np.minimum(j, n - 1)
            entry_price = self.c[safe]
        else:
            j = s.copy()
            skip[(j + 1 >= n) & (skip == None)] = "no_next_bar"  # noqa: E711
            entry_idx = j + 1
            entry_price = o[np.minimum(j + 1, n - 1)]
        safe_j = np.minimum(j, n - 1)
        atr_j = atr[safe_j]
        skip[~np.isfinite(atr_j) & (skip == None)] = "atr_nan_at_decision_bar"  # noqa: E711

        if entry.side == "signal":
            values = self._signal_column(signals, zid, k, entry.side_column, "side='signal'", skip)
            side = np.where(values > 0, 1, -1)
            skip[((values == 0) | np.isnan(values)) & (skip == None)] = "no_side"  # noqa: E711
        else:
            side = zside if entry.side == "zone" else -zside

        live = skip == None  # noqa: E711
        if stop is None:
            level = np.full(len(frame), np.nan)
        elif isinstance(stop, FixedAtrStop):
            level = np.full(len(frame), float(stop.value))
        else:
            level = self._signal_column(signals, zid, k, stop.column, f"ColumnStop({stop.column!r})", skip)
            bad = live & ~(level > 0)
            if bad.any():
                z = zid[np.flatnonzero(bad)[0]]
                raise ValueError(f"the stop column {stop.column!r} at (zone_id={z!r}, k={k}) is not a positive distance")

        self.j, self.entry_idx, self.entry_price, self.side = j, entry_idx, entry_price, side.astype(np.int64)
        self.atr_points = atr_j
        self.unit = atr_j * point
        self.skip, self.live, self.k = skip, live, k
        self.dur = e + 1 - s
        self.has_stop = stop is not None
        self.stop_price = entry_price - side * level * self.unit

        # the window of every live zone: bars j + 1 … min(e + 1, n - 1), laid end to end
        first = j + 1
        last = np.minimum(e + 1, n - 1)
        length = np.where(live, np.maximum(last - first + 1, 0), 0)
        self.offset = np.concatenate([[0], np.cumsum(length)[:-1]])
        total = int(length.sum())
        seg = np.repeat(np.arange(len(frame)), length)
        pos = np.arange(total) - np.repeat(self.offset, length) + np.repeat(first, length)
        hi, lo = h[pos], l[pos]
        groups = pd.Series(seg)
        self.run_high = pd.Series(hi).groupby(groups).cummax().to_numpy()
        self.run_low = pd.Series(lo).groupby(groups).cummin().to_numpy()
        # the first bar of the window that touches the stop (n when none does)
        self.stop_bar = np.full(len(frame), n, dtype=np.int64)
        if self.has_stop and total:
            seg_side = side[seg]
            touched = np.where(seg_side > 0, lo <= self.stop_price[seg], hi >= self.stop_price[seg])
            hit = np.flatnonzero(touched)
            if len(hit):
                first_hit = pd.Series(pos[hit]).groupby(seg[hit]).min()
                self.stop_bar[first_hit.index.to_numpy()] = first_hit.to_numpy()

    @staticmethod
    def _signal_column(signals, zid, k, column, purpose, skip):
        values = np.full(len(zid), np.nan)
        table = signals
        for i, z in enumerate(zid):
            if skip[i] is not None:
                continue
            rows = table.get(z)
            if rows is None or k not in rows.index:
                raise ValueError(f"{purpose} needs the signal row (zone_id={z!r}, k={k}), and there is none")
            if column not in rows.columns:
                raise ValueError(f"{purpose} needs the signal column {column!r}, and the signal frame has none")
            values[i] = float(rows.at[k, column])
        return values

    def outcomes(self, exit_idx: np.ndarray):
        """Arrays over the cells of ``exit_idx`` (shape ``(..., n_zones)``)."""
        n = self.n
        shape = exit_idx.shape
        j = np.broadcast_to(self.j, shape)
        end1 = np.broadcast_to(self.end + 1, shape)
        skip = np.array(np.broadcast_to(self.skip, shape), dtype=object)
        open_ = skip == None  # noqa: E711
        before = open_ & (exit_idx <= j)
        skip[before] = "exit_before_entry"
        x = np.minimum(exit_idx, end1)
        beyond = open_ & ~before & (x >= n)
        skip[beyond] = "exit_beyond_data"
        ok = skip == None  # noqa: E711

        reason = np.where(exit_idx < end1, "exit_at", "zone_change").astype(object)
        stop_bar = np.broadcast_to(self.stop_bar, shape)
        stopped = ok & (stop_bar <= x)
        x = np.where(stopped, stop_bar, x)
        reason[stopped] = "stop"
        safe_x = np.where(ok, x, np.broadcast_to(self.j, shape) + 1).clip(0, n - 1)
        entry_price = np.broadcast_to(self.entry_price, shape)
        stop_price = np.broadcast_to(self.stop_price, shape)
        exit_price = np.where(stopped, stop_price, self.c[safe_x])
        cell = np.broadcast_to(self.offset, shape) + (safe_x - j - 1)
        cell = np.where(ok, cell, 0)
        side = np.broadcast_to(self.side, shape)
        unit = np.broadcast_to(self.unit, shape)
        if len(self.run_high):
            high, low = self.run_high[cell], self.run_low[cell]
        else:
            high = low = np.full(shape, np.nan)
        favourable = np.where(side > 0, high - entry_price, entry_price - low)
        adverse = np.where(side > 0, entry_price - low, high - entry_price)
        return {"ok": ok, "skip": skip, "x": x, "reason": reason, "exit_price": exit_price,
                "favourable": favourable, "adverse": adverse, "side": side, "unit": unit,
                "entry_price": entry_price}

    def money(self, side, entry_idx, x, entry_price, exit_price):
        """Gross points, nights and cost for flat arrays of live cells."""
        gross_points = side * (exit_price - entry_price) / self.point
        nights = rollover_nights(self.index[entry_idx], self.index[x] + self.bar, triple_weekday=self.triple)
        if self.costs is None:
            cost = np.zeros(len(side))
        else:
            cost = np.asarray(self.costs.round_trip(self.spread, entry_idx, side, nights), dtype=float)
        return gross_points, nights, cost


def _prepare(bars, zones, point, entry, stop, costs, signals, atr, atr_period, bar):
    if not isinstance(bars, pd.DataFrame) or not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("bars must be a DataFrame with a DatetimeIndex (server time)")
    missing = [c for c in ("open", "high", "low", "close") if c not in bars.columns]
    if missing:
        raise ValueError(f"bars have no {missing}")
    if isinstance(point, bool) or not isinstance(point, (int, float)) or not point > 0:
        raise ValueError(f"point must be a positive number, got {point!r}")
    if not isinstance(entry, (ZoneBarClose, NextOpen)):
        raise ValueError(f"entry must be ZoneBarClose or NextOpen, got {entry!r}")
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
    frame = zones_frame(zones, len(bars))
    step = pd.Timedelta(bar) if bar is not None else bar_length(bars.index)
    return _Zones(bars, frame, entry, stop, costs, signal_table(signals), float(point), atr_price, step)


def _exit_bars(exit_idx: Any, n_zones: int) -> np.ndarray:
    array = np.asarray(exit_idx)
    if array.ndim not in (1, 2) or array.shape[-1] != n_zones:
        raise ValueError(f"exit_idx must have one bar per zone ({n_zones}) per row, got shape {array.shape}")
    if not np.issubdtype(array.dtype, np.integer):
        raise ValueError(f"exit_idx must be whole bar positions, got dtype {array.dtype}")
    return array.astype(np.int64)


def trades_at_exit(
    bars: pd.DataFrame,
    zones: Any,
    exit_idx: Any,
    *,
    point: float,
    entry: Entry = ZoneBarClose(),
    stop: Optional[Stop] = None,
    costs: Optional[CostModel] = None,
    signals: Optional[pd.DataFrame] = None,
    atr: Optional[Any] = None,
    atr_period: int = 14,
    bar: Optional[pd.Timedelta] = None,
):
    """The outcome when every zone leaves at a given bar — one set, or many at once.

    ``exit_idx`` holds one absolute bar position per zone, in the order of ``zones``. A
    1-d ``exit_idx`` returns :class:`~.ZoneTrades`, equal bit for bit to
    ``zone_trades(..., exit=ExitAt())``. A 2-d one, ``(n_sets, n_zones)``, returns an
    :class:`ExitMatrix` with one row per set — a cell without a trade is ``NaN`` and the
    rest of its row is kept. The rules are those of :class:`~.ExitAt`: ``x = min(exit_idx,
    e + 1)``, ``exit_idx <= j`` gives no trade, a stop wins its bar; the other arguments
    are those of :func:`~bquant.analysis.trading.zone_trades`.
    """
    zones_ = _prepare(bars, zones, point, entry, stop, costs, signals, atr, atr_period, bar)
    wanted = _exit_bars(exit_idx, len(zones_.zone_id))
    got = zones_.outcomes(wanted)
    ok = got["ok"]
    k_entry = np.broadcast_to(zones_.entry_idx, wanted.shape)

    gross_points = np.full(wanted.shape, np.nan)
    net_points = np.full(wanted.shape, np.nan)
    nights = np.zeros(wanted.shape, dtype=np.int64)
    cost = np.full(wanted.shape, np.nan)
    if ok.any():
        g, nt, c = zones_.money(got["side"][ok], k_entry[ok], got["x"][ok], got["entry_price"][ok], got["exit_price"][ok])
        gross_points[ok], nights[ok], cost[ok] = g, nt, c
        net_points[ok] = g - c
    atr_points = np.broadcast_to(zones_.atr_points, wanted.shape)

    if wanted.ndim == 2:
        hold = np.where(ok, got["x"] - np.broadcast_to(zones_.j, wanted.shape), np.nan)
        reasons = np.where(ok, got["reason"], None)
        skip = np.where(ok, None, got["skip"])
        return ExitMatrix(zone_id=zones_.zone_id, net=np.where(ok, net_points / atr_points, np.nan),
                          gross=np.where(ok, gross_points / atr_points, np.nan), hold=hold,
                          exit_reason=reasons, skip_reason=skip)

    rows = np.flatnonzero(ok)
    unit = got["unit"][rows]
    index = zones_.index
    trades = pd.DataFrame({
        "zone_id": zones_.zone_id[rows],
        "k": np.full(len(rows), zones_.k, dtype=np.int64),
        "side": got["side"][rows].astype(np.int64),
        "decision_time": index[zones_.j[rows]],
        "entry_time": index[zones_.entry_idx[rows]],
        "exit_time": index[got["x"][rows]],
        "hold": (got["x"][rows] - zones_.j[rows]).astype(np.int64),
        "mode": np.full(len(rows), "exit_at", dtype=object),
        "exit_reason": got["reason"][rows],
        "entry_price": got["entry_price"][rows].astype(float),
        "exit_price": got["exit_price"][rows].astype(float),
        "atr_points": zones_.atr_points[rows].astype(float),
        "gross_points": gross_points[rows],
        "cost_points": cost[rows],
        "nights": nights[rows].astype(np.int64),
        "net_points": net_points[rows],
        "gross": gross_points[rows] / zones_.atr_points[rows],
        "net": net_points[rows] / zones_.atr_points[rows],
        "mfe": np.maximum(0.0, got["favourable"][rows] / unit),
        "mae": np.maximum(0.0, got["adverse"][rows] / unit),
        "dur": zones_.dur[rows].astype(np.int64),
        "stop_and_take_same_bar": np.zeros(len(rows), dtype=bool),
    }, columns=list(TRADE_COLUMNS))
    skipped_rows = np.flatnonzero(~ok)
    skipped = pd.DataFrame({"zone_id": zones_.zone_id[skipped_rows], "reason": got["skip"][skipped_rows]},
                           columns=list(SKIPPED_COLUMNS))
    return ZoneTrades(trades=trades.reset_index(drop=True), skipped=skipped.reset_index(drop=True))
