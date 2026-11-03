"""Quarterly measure of a single run: is the result spread over time or made in one stretch?

Input is the balance after each trade, indexed by the trade's exit time. Quarters are
calendar quarters; a quarter's return is the balance at its end over the balance at the
end of the previous quarter (the initial deposit for the first one) minus one.

Two decisions the reference left implicit and the package makes explicit:

* **A quarter with no trades is a quarter.** The balance is carried forward, the return
  is 0 and the quarter is counted — a flat quarter is not a positive one. The reference
  implementation reported it as ``NaN`` and left it out of the count.
* **The stretch after the last high is reported too.** ``longest_underwater_days`` is
  the longest gap between two consecutive new highs and cannot see the stretch that
  runs from the last high to the end of the series — the one that is still open in a
  live run. ``underwater_tail_days`` carries it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

import numpy as np
import pandas as pd

from .criterion import Rule


def quarterly_summary(balance: pd.Series, initial: float, *, top_k: int = 3) -> dict[str, Any]:
    """Quarterly returns and the drawdown numbers of one balance curve.

    Keys: ``q_n``, ``q_pos`` (returns > 0), ``q_median``, ``q_worst``, ``q_mean``,
    ``q_std`` (``ddof=1``), ``q_mean_over_std``, ``max_dd`` (``min(balance / cummax - 1)``
    over trades), ``longest_underwater_days``, ``underwater_tail_days``,
    ``top_k_share`` (share of the total profit made by the ``top_k`` best quarters;
    ``NaN`` when the total profit is not positive), ``final``, ``q_returns`` (a Series
    indexed by quarter end).
    """
    if not isinstance(balance, pd.Series) or not isinstance(balance.index, pd.DatetimeIndex):
        raise ValueError("quarterly_summary: balance must be a Series indexed by exit time (DatetimeIndex)")
    if balance.empty:
        raise ValueError("quarterly_summary: the balance series is empty")
    if balance.isna().any():
        raise ValueError("quarterly_summary: the balance series has missing values")
    if not initial > 0:
        raise ValueError(f"quarterly_summary: initial deposit must be > 0, got {initial}")
    if top_k < 1:
        raise ValueError(f"quarterly_summary: top_k must be >= 1, got {top_k}")

    b = balance.sort_index(kind="stable").astype(float)
    peak = b.cummax()
    drawdown = b / peak - 1
    is_high = b >= peak
    high_times = b.index[is_high]
    gaps = np.diff(high_times.values).astype("timedelta64[D]").astype(int)
    longest = int(gaps.max()) if len(gaps) else 0
    tail = int((b.index[-1] - high_times[-1]).days)

    q_end = b.resample("QE").last().ffill()          # an empty quarter carries the balance
    q_start = q_end.shift(1)
    q_start.iloc[0] = float(initial)
    q_ret = q_end / q_start - 1
    q_profit = q_end - q_start
    total_profit = float(b.iloc[-1] - initial)
    top = float(np.sort(q_profit.to_numpy())[::-1][:top_k].sum())
    top_k_share = top / total_profit if total_profit > 0 else np.nan

    q_std = float(q_ret.std(ddof=1)) if len(q_ret) > 1 else np.nan
    q_mean = float(q_ret.mean())
    return {
        "q_n": int(len(q_ret)),
        "q_pos": int((q_ret > 0).sum()),
        "q_median": float(q_ret.median()),
        "q_worst": float(q_ret.min()),
        "q_mean": q_mean,
        "q_std": q_std,
        "q_mean_over_std": q_mean / q_std if q_std and np.isfinite(q_std) and q_std > 0 else np.nan,
        "max_dd": float(drawdown.min()),
        "longest_underwater_days": longest,
        "underwater_tail_days": tail,
        "top_k_share": float(top_k_share),
        "top_k": int(top_k),
        "final": float(b.iloc[-1]),
        "q_returns": q_ret,
    }


# --- rules over the summary (thresholds proposed by the requester, to be ratified) ----- #

def _get(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key, np.nan)
    return np.nan if value is None else value


@dataclass(frozen=True)
class QuartersPositive(Rule):
    """``q_pos / q_n >= share``."""

    share: float = 2 / 3
    name: ClassVar[str] = "quarters_positive"

    def check(self, row):
        q_n = _get(row, "q_n")
        return bool(q_n > 0 and _get(row, "q_pos") / q_n >= self.share)


@dataclass(frozen=True)
class QuarterMedian(Rule):
    """``q_median >= threshold``."""

    threshold: float = 0.02
    name: ClassVar[str] = "quarter_median"

    def check(self, row):
        return bool(_get(row, "q_median") >= self.threshold)


@dataclass(frozen=True)
class WorstQuarter(Rule):
    """``q_worst >= threshold`` (a floor: −0.25 means no quarter lost more than a quarter)."""

    threshold: float = -0.25
    name: ClassVar[str] = "worst_quarter"

    def check(self, row):
        return bool(_get(row, "q_worst") >= self.threshold)


@dataclass(frozen=True)
class QuarterMeanOverStd(Rule):
    """``q_mean_over_std >= threshold``."""

    threshold: float = 0.4
    name: ClassVar[str] = "quarter_mean_over_std"

    def check(self, row):
        return bool(_get(row, "q_mean_over_std") >= self.threshold)


def default_quarter_rules() -> list[Rule]:
    return [QuartersPositive(), QuarterMedian(), WorstQuarter(), QuarterMeanOverStd()]
