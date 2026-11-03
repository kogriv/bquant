"""Summary of a candidate's trades, the multiplicity correction, and the rules that judge it.

A candidate — a combination of signal, side, filter, horizon, whatever the caller
tried — yields a trade frame. :func:`trial_stats` folds it into one row: mean outcome
with a month-block interval, the advantage over the random-entry baseline with its
interval, standard error and one-sided ``p``, the years. :class:`Criterion` takes a
table of such rows, corrects the ``p`` values for everything that was tried
(Benjamini–Hochberg with ``m_total`` **from the caller** — the package keeps no registry
of variants), applies its rules and writes ``pass``.

``p`` is ``norm.sf(excess_mean / excess_se)``: the normal approximation with the
bootstrap standard error. The share of replicates (``p_boot``, reported for checking)
has resolution ``1 / (B + 1)``, too coarse once thousands of variants are corrected
together.

Rules are objects with thresholds in their fields: a threshold changes by making a new
object, not by editing code, and ``describe()`` records it. Inequalities are exactly
as written in each rule's docstring; a value that lands on a strict threshold has not
passed it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm

from .bootstrap import BlockBootstrap
from .trades import month_key, validate_trades


# --- summary -------------------------------------------------------------------------- #

def trial_stats(
    trades: pd.DataFrame,
    bootstrap: BlockBootstrap,
    *,
    level: float = 0.95,
    min_year_trades: int = 10,
) -> dict[str, Any]:
    """One row of numbers for a candidate's trade frame.

    Keys: ``n``, ``long_share``, ``net_mean``, ``net_lo``, ``net_hi``, ``hit``;
    ``gross_mean`` and ``cost_mean`` when ``gross`` is present; ``hold_mean`` when
    ``hold`` is; ``rand_mean``, ``excess_mean``, ``excess_lo``, ``excess_hi``,
    ``excess_se``, ``p``, ``p_boot`` from the ``rand`` column (all ``NaN`` without it —
    the advantage is not computed, not assumed); ``years`` (per year: ``n``, ``net``,
    ``ex``), ``years_n`` (years with at least ``min_year_trades`` trades),
    ``years_net_pos`` and ``years_ex_pos`` among those. An empty frame gives
    ``{"n": 0}``.

    A trade whose ``rand`` is ``NaN`` counts in ``n`` and in ``net`` but not in the
    advantage — there is no baseline to subtract.
    """
    validate_trades(trades)
    n = int(len(trades))
    if n == 0:
        return {"n": 0}
    net = trades["net"].to_numpy(dtype=float)
    month = month_key(trades["entry_time"])
    year = trades["entry_time"].dt.year.to_numpy()

    net_lo, net_hi, _, _ = bootstrap.interval(net, month, level)
    out: dict[str, Any] = {
        "n": n,
        "long_share": float((trades["side"].to_numpy() > 0).mean()),
        "net_mean": float(net.mean()),
        "net_lo": net_lo,
        "net_hi": net_hi,
        "hit": float((net > 0).mean()),
    }
    if "gross" in trades.columns:
        gross = trades["gross"].to_numpy(dtype=float)
        out["gross_mean"] = float(np.nanmean(gross))
        out["cost_mean"] = float(np.nanmean(gross - net))
    if "hold" in trades.columns:
        out["hold_mean"] = float(trades["hold"].to_numpy(dtype=float).mean())

    if "rand" in trades.columns:
        rand = trades["rand"].to_numpy(dtype=float)
        has = np.isfinite(rand)
        ex = (net - rand)[has]
    else:
        rand = np.full(n, np.nan)
        has = np.zeros(n, dtype=bool)
        ex = np.array([], dtype=float)

    if len(ex):
        excess_mean = float(ex.mean())
        excess_lo, excess_hi, se, replicates = bootstrap.interval(ex, month[has], level)
        p = float(norm.sf(excess_mean / se)) if np.isfinite(se) and se > 0 else np.nan
        p_boot = (
            float((1 + np.sum((replicates - excess_mean) >= excess_mean)) / (len(replicates) + 1))
            if len(replicates) else np.nan
        )
        rand_mean = float(rand[has].mean())
    else:
        excess_mean = excess_lo = excess_hi = se = p = p_boot = rand_mean = np.nan
    out.update({
        "rand_mean": rand_mean,
        "excess_mean": excess_mean,
        "excess_lo": excess_lo,
        "excess_hi": excess_hi,
        "excess_se": se,
        "p": p,
        "p_boot": p_boot,
    })

    per_year = pd.DataFrame({"year": year, "net": net, "ex": np.where(has, net - rand, np.nan)})
    years = per_year.groupby("year").agg(n=("net", "size"), net=("net", "mean"), ex=("ex", "mean"))
    qualified = years[years["n"] >= min_year_trades]
    out["years"] = {
        int(y): {"n": int(r.n), "net": float(r.net), "ex": float(r.ex)} for y, r in years.iterrows()
    }
    out["years_n"] = int(len(qualified))
    out["years_net_pos"] = int((qualified["net"] > 0).sum())
    out["years_ex_pos"] = int((qualified["ex"] > 0).sum())
    return out


# --- multiplicity --------------------------------------------------------------------- #

def benjamini_hochberg(p, m_total: int) -> np.ndarray:
    """``q`` values for ``p`` under ``m = max(m_total, number of non-NaN p)`` tests.

    ``m_total`` is everything that was tried — on this segment, in earlier searches,
    including the variants that never made it into the table because they had too few
    trades. The tests missing from the table count as ``p = 1``: the correction does not
    get looser because candidates were discarded along the way. ``NaN`` entries are not
    ranked and come back ``NaN``.
    """
    p = np.asarray(p, dtype=float)
    if p.ndim != 1:
        raise ValueError("benjamini_hochberg: p must be one-dimensional")
    if m_total < 0:
        raise ValueError(f"benjamini_hochberg: m_total must be >= 0, got {m_total}")
    q = np.full(len(p), np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    if len(pv) == 0:
        return q
    if (pv < 0).any() or (pv > 1).any():
        raise ValueError("benjamini_hochberg: p values must lie in [0, 1]")
    m = max(int(m_total), len(pv))
    order = np.argsort(pv, kind="stable")
    ranked = pv[order] * m / (np.arange(len(pv)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    qq = np.empty(len(pv))
    qq[order] = np.minimum(ranked, 1.0)
    q[ok] = qq
    return q


# --- rules ---------------------------------------------------------------------------- #

class Rule(ABC):
    """A named check over one summary row; the threshold lives in the object's fields."""

    name: ClassVar[str] = "rule"

    @abstractmethod
    def check(self, row: Mapping[str, Any]) -> bool:
        ...

    def describe(self) -> dict[str, Any]:
        return {"rule": type(self).__name__, "name": self.name,
                **{f.name: getattr(self, f.name) for f in fields(self)}}  # type: ignore[arg-type]


def _get(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key, np.nan)
    return np.nan if value is None else value


@dataclass(frozen=True)
class MinTrades(Rule):
    """``n >= n_min``."""

    n: int = 100
    name: ClassVar[str] = "min_trades"

    def check(self, row):
        return bool(_get(row, "n") >= self.n)


@dataclass(frozen=True)
class NetPositive(Rule):
    """``net_mean > 0``; with ``use_ci`` also ``net_lo > 0``."""

    use_ci: bool = False
    name: ClassVar[str] = "net_positive"

    def check(self, row):
        if _get(row, "n") == 0 or np.isnan(_get(row, "n")):
            return False
        return bool(_get(row, "net_mean") > 0 and (not self.use_ci or _get(row, "net_lo") > 0))


@dataclass(frozen=True)
class YearsStable(Rule):
    """``years_n >= min_years`` and ``years_net_pos >= ceil(share * years_n - 1e-9)``."""

    share: float = 2 / 3
    min_years: int = 2
    name: ClassVar[str] = "years_stable"

    def check(self, row):
        years_n = _get(row, "years_n")
        if np.isnan(years_n) or years_n < self.min_years:
            return False
        return bool(_get(row, "years_net_pos") >= np.ceil(self.share * years_n - 1e-9))


@dataclass(frozen=True)
class BeatsRandom(Rule):
    """``excess_lo > margin`` and ``q < alpha`` (``q`` is ``NaN`` → not passed)."""

    alpha: float = 0.05
    margin: float = 0.0
    name: ClassVar[str] = "beats_random"

    def check(self, row):
        if _get(row, "n") == 0 or np.isnan(_get(row, "n")):
            return False
        return bool(_get(row, "excess_lo") > self.margin and _get(row, "q") < self.alpha)


@dataclass(frozen=True)
class MinEffect(Rule):
    """``excess_mean >= threshold`` — the advantage is worth having, not merely non-zero."""

    threshold: float
    name: ClassVar[str] = "min_effect"

    def check(self, row):
        return bool(_get(row, "excess_mean") >= self.threshold)


def apply_rules(row: Mapping[str, Any], rules: Sequence[Rule]) -> dict[str, bool]:
    """``{'ok_<name>': bool, ..., 'pass': all}`` for one row."""
    flags = {f"ok_{rule.name}": bool(rule.check(row)) for rule in rules}
    flags["pass"] = all(flags.values()) if flags else True
    return flags


@dataclass
class Criterion:
    """A set of rules; :meth:`evaluate` corrects ``p``, applies the rules, writes ``pass``."""

    rules: list = field(default_factory=list)
    name: str = "criterion"

    def evaluate(self, table: pd.DataFrame, m_total: int) -> pd.DataFrame:
        """Add ``q`` (Benjamini–Hochberg over ``m_total`` tests), ``m_total``, one
        ``ok_<rule>`` column per rule and ``pass`` to a copy of ``table``.

        A row with fewer trades than the :class:`MinTrades` rule asks for gets
        ``p = NaN`` **before** the correction: its ``p`` rests on a bootstrap over a few
        months and is not ranked — but it stays inside ``m_total``, so the correction is
        only stricter for having tried it.
        """
        out = table.copy()
        p = out["p"].to_numpy(dtype=float).copy() if "p" in out else np.full(len(out), np.nan)
        min_trades = next((r for r in self.rules if isinstance(r, MinTrades)), None)
        if min_trades is not None and "n" in out:
            p[out["n"].fillna(0).to_numpy(dtype=float) < min_trades.n] = np.nan
        out["q"] = benjamini_hochberg(p, m_total)
        out["m_total"] = int(m_total)
        rows = out.to_dict("records")
        flags = [apply_rules(row, self.rules) for row in rows]
        for key in (list(flags[0].keys()) if flags else [f"ok_{r.name}" for r in self.rules] + ["pass"]):
            out[key] = [f[key] for f in flags] if flags else []
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "correction": "Benjamini-Hochberg over m_total tests supplied by the caller",
            "rules": [rule.describe() for rule in self.rules],
        }


def default_criterion(min_trades: int = 100) -> Criterion:
    """``MinTrades(min_trades)``, ``NetPositive()``, ``YearsStable(2/3)``, ``BeatsRandom(0.05, 0.0)``."""
    return Criterion(rules=[MinTrades(min_trades), NetPositive(), YearsStable(2 / 3), BeatsRandom(0.05, 0.0)])
