"""Random-entry baseline: what the same entry would earn on a random bar of the same year.

A buy in a year the market rose wins on average whatever the signal was. The baseline
takes that out: for every (year, side, holding time) it is the **exact mean** of the
outcome over **all** bars of the segment whose holding window ``e … e + H - 1`` lies
inside the segment — not a sample. The trade's advantage (``excess``) is its own
outcome minus this expectation; :func:`~.criterion.trial_stats` reads it from the
``rand`` column.

The outcome function is the caller's: it receives entry bar positions, a holding time
and a side and returns the net outcome of each entry in the caller's unit (costs and
scaling, such as dividing by the entry bar's ATR, happen there). The package only
decides which bars are eligible and takes the mean.
"""

from __future__ import annotations

from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .trades import validate_trades

OutcomeFunction = Callable[[np.ndarray, int, int], np.ndarray]


def random_entry_baseline(
    index: pd.DatetimeIndex,
    outcome: OutcomeFunction,
    holds: Iterable[int],
    *,
    lo: int = 0,
    hi: int | None = None,
    by_hour: bool = False,
) -> pd.DataFrame:
    """Expectation table over ``(year[, hour], side, hold)``.

    Args:
        index: Timestamps of the bars (one per bar, increasing).
        outcome: ``outcome(entries, hold, side) -> ndarray`` — net outcome for each
            entry bar position, same length as ``entries``; ``NaN`` where undefined
            (those bars are left out of the mean).
        holds: Holding times (bars) to tabulate — usually ``unique(trades.hold)``.
        lo, hi: First and last bar position of the segment (inclusive); ``hi`` defaults
            to the last bar. Warm-up of an indicator the outcome needs is expressed
            through ``lo``.
        by_hour: Also key by the hour of the entry bar.

    Returns:
        A frame with columns ``year``, (``hour``,) ``side``, ``hold``, ``expectation``,
        ``bars`` — one row per non-empty cell. A cell with no eligible bar is absent
        (and reads as ``NaN`` when attached).
    """
    index = pd.DatetimeIndex(index)
    n = len(index)
    if n == 0:
        raise ValueError("random_entry_baseline: the bar index is empty")
    if hi is None:
        hi = n - 1
    if not (0 <= lo <= hi < n):
        raise ValueError(f"random_entry_baseline: need 0 <= lo <= hi < {n}, got lo={lo}, hi={hi}")
    years = index.year.to_numpy()
    hours = index.hour.to_numpy()
    rows = []
    for hold in sorted({int(h) for h in holds}):
        if hold < 1:
            raise ValueError(f"random_entry_baseline: hold must be >= 1 bar, got {hold}")
        entries = np.arange(lo, hi - hold + 2)  # e + hold - 1 <= hi
        if len(entries) == 0:
            continue
        for side in (1, -1):
            values = np.asarray(outcome(entries, hold, side), dtype=float)
            if values.shape != entries.shape:
                raise ValueError(
                    f"outcome(entries, hold={hold}, side={side}) returned shape {values.shape}, "
                    f"expected {entries.shape}"
                )
            ok = np.isfinite(values)
            keys = {"year": years[entries][ok]}
            if by_hour:
                keys["hour"] = hours[entries][ok]
            cell = pd.DataFrame({**keys, "value": values[ok]})
            if cell.empty:
                continue
            grouped = cell.groupby(list(keys), sort=True)["value"].agg(["mean", "size"]).reset_index()
            grouped = grouped.rename(columns={"mean": "expectation", "size": "bars"})
            grouped["side"] = side
            grouped["hold"] = hold
            rows.append(grouped)
    columns = ["year", *(["hour"] if by_hour else []), "side", "hold", "expectation", "bars"]
    if not rows:
        return pd.DataFrame(columns=columns)
    table = pd.concat(rows, ignore_index=True)[columns]
    table["bars"] = table["bars"].astype(int)
    return table


def attach_random_baseline(trades: pd.DataFrame, table: pd.DataFrame, *, by_hour: bool = False) -> pd.DataFrame:
    """Return ``trades`` with a ``rand`` column looked up from ``table``.

    Keys are the entry year (and hour), ``side`` and ``hold``; a trade whose cell is
    absent gets ``NaN`` — it stays in ``n`` but drops out of the advantage.
    """
    validate_trades(trades)
    if "hold" not in trades.columns:
        raise ValueError("attach_random_baseline needs a 'hold' column (holding time in bars)")
    keys = ["year", *(["hour"] if by_hour else []), "side", "hold"]
    missing = [k for k in keys + ["expectation"] if k not in table.columns]
    if missing:
        raise ValueError(f"baseline table is missing column(s) {missing}; build it with random_entry_baseline")
    lookup = trades[["entry_time", "side", "hold"]].copy()
    lookup["year"] = lookup["entry_time"].dt.year
    if by_hour:
        lookup["hour"] = lookup["entry_time"].dt.hour
    merged = lookup.merge(table[keys + ["expectation"]], on=keys, how="left", validate="many_to_one")
    out = trades.copy()
    out["rand"] = merged["expectation"].to_numpy()
    return out
