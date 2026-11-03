"""The trade frame — the one object every function of this package reads.

One row is one trade. Four columns are required, four are optional, and nothing is
coerced silently: a frame that does not meet the contract is refused with the name
of the column and what it has to be.

Required: ``entry_time`` and ``exit_time`` (datetime64, exit not before entry),
``side`` (+1 buy / −1 sell), ``net`` (outcome after costs, in whatever unit the caller
evaluates in — ATR of the entry bar, percent of price, money; the package never
rescales it). Optional: ``gross`` (outcome before costs), ``rand`` (expected outcome
of a random entry, see :mod:`.baseline`; ``NaN`` means "no baseline for this trade"),
``hold`` (holding time in bars, needed to attach a baseline), ``mode`` (the label of
the exit the trade used, needed to attach a baseline built with exit modes).

Derived keys: ``year`` and the integer month key ``year * 12 + month - 1`` are taken
from ``entry_time``; the calendar quarter is taken from ``exit_time`` and only by the
quarterly measure.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_integer_dtype, is_numeric_dtype

REQUIRED_COLUMNS = ("entry_time", "exit_time", "side", "net")
OPTIONAL_COLUMNS = ("gross", "rand", "hold", "mode")


def validate_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Return ``trades`` unchanged if it meets the contract; otherwise refuse by name.

    An empty frame with the right columns is valid: every summary reports ``n = 0``.
    """
    if not isinstance(trades, pd.DataFrame):
        raise ValueError(f"a trade frame must be a pandas DataFrame, got {type(trades).__name__}")
    missing = [column for column in REQUIRED_COLUMNS if column not in trades.columns]
    if missing:
        raise ValueError(
            f"trade frame is missing required column(s) {missing}; "
            f"required: {list(REQUIRED_COLUMNS)}, optional: {list(OPTIONAL_COLUMNS)}"
        )
    for column in ("entry_time", "exit_time"):
        if not is_datetime64_any_dtype(trades[column]):
            raise ValueError(
                f"'{column}' must be datetime64, got {trades[column].dtype}; "
                f"parse it before calling (pd.to_datetime)"
            )
        if trades[column].isna().any():
            raise ValueError(f"'{column}' has {int(trades[column].isna().sum())} missing value(s)")
    late = int((trades["exit_time"] < trades["entry_time"]).sum())
    if late:
        raise ValueError(f"{late} trade(s) have exit_time before entry_time")
    side = trades["side"]
    if not is_numeric_dtype(side) or side.isna().any() or not set(np.unique(side.to_numpy())) <= {1, -1}:
        raise ValueError(
            f"'side' must be +1 (buy) or -1 (sell) for every trade, got {sorted(set(side.dropna().unique()))}"
        )
    if not is_numeric_dtype(trades["net"]) or trades["net"].isna().any():
        raise ValueError("'net' must be numeric without missing values — it is the outcome after costs")
    for column in ("gross", "rand"):
        if column in trades.columns and not is_numeric_dtype(trades[column]):
            raise ValueError(f"'{column}' must be numeric, got {trades[column].dtype}")
    if "hold" in trades.columns:
        hold = trades["hold"]
        if not is_integer_dtype(hold) or (hold < 0).any():
            raise ValueError("'hold' must be a non-negative integer number of bars")
    return trades


def month_key(times: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Integer month key ``year * 12 + month - 1`` for each timestamp."""
    index = pd.DatetimeIndex(times)
    return (index.year * 12 + index.month - 1).to_numpy()


def months_between(start, end) -> np.ndarray:
    """Every calendar month from ``start`` to ``end`` inclusive, as integer month keys.

    This is the block list a :class:`~.bootstrap.BlockBootstrap` takes: the months of
    the **segment**, not the months that happen to hold a trade — an empty month is a
    block too, and leaving it out narrows every interval.
    """
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    if last < first:
        raise ValueError(f"months_between: end {last} is before start {first}")
    lo = first.year * 12 + first.month - 1
    hi = last.year * 12 + last.month - 1
    return np.arange(lo, hi + 1)


def month_label(keys: Iterable[int]) -> list[str]:
    """``'YYYY-MM'`` for each integer month key — for reading, not for computing."""
    return [f"{int(k) // 12:04d}-{int(k) % 12 + 1:02d}" for k in keys]
