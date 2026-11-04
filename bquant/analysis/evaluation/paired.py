"""A variant against its base: the paired difference, a contrast of two groups, a placebo.

A study does not ask whether a rule makes money, but whether it does **better than the
same trade without the rule** (the *base*), unit by unit — a zone, a bar. Three pieces:

* :func:`paired_stats` — the mean of ``variant - base`` over the units both have, its
  spread by the month-block bootstrap (:class:`~.BlockBootstrap`), a one-sided ``p`` for
  "the variant is better", and the same mean year by year;
* :func:`contrast_stats` — the difference of the means of two groups of units (after a low
  excursion against after a high one), through centred indicators, on the same bootstrap;
* :func:`permutation_placebo` — the statistic recomputed on shuffled units: if the effect
  survives the shuffle, it did not come from what was shuffled. The statistics it shuffles
  are :class:`SignFlip`, :class:`PermuteFlags` and :class:`PermuteColumn`.

The groups and their quantile thresholds are the caller's: a threshold computed twice by
two libraries can differ in its last bit and move a unit across it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

from .bootstrap import BlockBootstrap

_P_KINDS = ("boot_share", "normal")
_DEGENERATE_SE = 1e-12


def _check_p_kind(p_kind: str) -> None:
    if p_kind not in _P_KINDS:
        raise ValueError(f"p_kind must be one of {_P_KINDS}, got {p_kind!r}")


def _check_min(value: Any, name: str) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a whole number >= 1, got {value!r}")
    return int(value)


def _years_of(d: np.ndarray, month: np.ndarray, min_year_units: int):
    years = month // 12
    table = {int(y): {"n": int((years == y).sum()), "mean_diff": float(d[years == y].mean())} for y in np.unique(years)}
    counted = [y for y, row in table.items() if row["n"] >= min_year_units]
    return table, len(counted), int(sum(table[y]["mean_diff"] > 0 for y in counted))


def _bootstrap(d: np.ndarray, month: np.ndarray, boot_months, B: int, seed: int, p_kind: str) -> Dict[str, Any]:
    means = BlockBootstrap(boot_months, B, seed).means(d, month)
    means = means[np.isfinite(means)]
    se = float(np.std(means, ddof=1)) if len(means) > 1 else np.nan
    mean_diff = float(d.mean()) if len(d) else np.nan
    if not np.isfinite(se) or se < _DEGENERATE_SE:
        p = np.nan                      # no spread: a tie, not evidence
    elif p_kind == "boot_share":
        p = float(np.mean(means <= 0))  # a replicate at zero is "not better"
    else:
        p = float(norm.sf(mean_diff / se))
    return {"mean_diff": mean_diff, "se": se, "p": p, "p_kind": p_kind, "replicates_used": int(len(means))}


def _units(frame: pd.DataFrame, key: str, value: str, month: str, side: str) -> pd.DataFrame:
    missing = [c for c in (key, value, month) if c not in frame.columns]
    if missing:
        raise ValueError(f"the {side} frame has no {missing}")
    if frame[key].duplicated().any():
        dup = frame.loc[frame[key].duplicated(), key].iloc[0]
        raise ValueError(f"the {side} frame has more than one unit with {key} = {dup!r}")
    return frame[[key, value, month]]


def paired_stats(
    variant: pd.DataFrame,
    base: pd.DataFrame,
    *,
    key: str,
    boot_months,
    value: str = "net",
    month: str = "month",
    B: int = 2000,
    seed: int = 1,
    p_kind: str = "boot_share",
    min_year_units: int = 10,
) -> Dict[str, Any]:
    """The variant against its base, unit by unit.

    ``variant`` and ``base`` have one row per unit: ``key`` (``zone_id``, say), ``value``
    (the outcome, ``net`` by default) and ``month`` (the integer key ``year * 12 + month - 1``
    of :func:`~.month_key`). They are matched by ``key`` (an inner join); the unmatched are
    dropped and counted (``n_variant``, ``n_base``, ``n`` paired). ``d = variant - base``.

    ``boot_months`` lists **every** month of the segment, empty ones included — a
    replicate that draws only empty months has no mean and is left out
    (``replicates_used``). ``se`` is the standard deviation of the replicate means;
    ``p`` is one-sided for ``mean_diff > 0``: ``"boot_share"`` — the share of replicate
    means ``<= 0``; ``"normal"`` — ``1 - Φ(mean_diff / se)``. With ``se`` missing or below
    ``1e-12`` there is no spread to judge by, and ``p`` is ``NaN``.

    ``years`` is ``{year: {n, mean_diff}}``; ``years_n`` counts the years with at least
    ``min_year_units`` units and ``years_pos`` those of them with ``mean_diff > 0`` — the
    columns :class:`~.YearsStable` (``positive="years_pos"``) reads.
    """
    _check_p_kind(p_kind)
    min_year_units = _check_min(min_year_units, "min_year_units")
    left = _units(variant, key, value, month, "variant")
    right = _units(base, key, value, month, "base")
    pairs = left.merge(right[[key, value]], on=key, how="inner", suffixes=("_variant", "_base"))
    d = (pairs[f"{value}_variant"] - pairs[f"{value}_base"]).to_numpy(dtype=float)
    months = pairs[month].to_numpy(dtype=np.int64)
    out: Dict[str, Any] = {"n": int(len(d)), "n_variant": int(len(left)), "n_base": int(len(right))}
    out.update(_bootstrap(d, months, boot_months, B, seed, p_kind))
    out["years"], out["years_n"], out["years_pos"] = _years_of(d, months, min_year_units)
    return out


def contrast_stats(
    x,
    flag_a,
    flag_b,
    *,
    month,
    boot_months,
    B: int = 2000,
    seed: int = 1,
    p_kind: str = "boot_share",
    min_year_units: int = 10,
    min_group_units: int = 10,
) -> Dict[str, Any]:
    """``mean(x | a) - mean(x | b)`` for two groups of the same units.

    ``x`` is the outcome per unit, ``flag_a`` / ``flag_b`` the caller's group masks,
    ``month`` the month key per unit. Through centred indicators
    ``w = 1a / n_a - 1b / n_b`` and ``d = x · w · N`` the mean of ``d`` is the difference of
    the group means, and it is bootstrapped by month exactly as :func:`paired_stats`.
    A group with fewer than ``min_group_units`` units makes everything ``NaN``.

    ``years`` are computed **inside** each year: ``{year: {n, n_a, n_b, mean_diff}}`` with
    ``mean_diff = mean_a - mean_b`` over that year's units; a year without one of the
    groups is left out. ``years_n`` / ``years_pos`` as in :func:`paired_stats`.
    """
    _check_p_kind(p_kind)
    min_year_units = _check_min(min_year_units, "min_year_units")
    min_group_units = _check_min(min_group_units, "min_group_units")
    x = np.asarray(x, dtype=float)
    a = np.asarray(flag_a, dtype=bool)
    b = np.asarray(flag_b, dtype=bool)
    months = np.asarray(month, dtype=np.int64)
    if not (x.shape == a.shape == b.shape == months.shape) or x.ndim != 1:
        raise ValueError(f"x, flag_a, flag_b and month must be 1-d of one length, got {x.shape}, {a.shape}, {b.shape}, {months.shape}")
    n_a, n_b = int(a.sum()), int(b.sum())
    out: Dict[str, Any] = {"n": int(len(x)), "n_a": n_a, "n_b": n_b}
    if n_a < min_group_units or n_b < min_group_units:
        out.update({"mean_diff": np.nan, "se": np.nan, "p": np.nan, "p_kind": p_kind, "replicates_used": 0,
                    "years": {}, "years_n": 0, "years_pos": 0})
        return out
    w = a / n_a - b / n_b
    d = x * w * len(x)
    out.update(_bootstrap(d, months, boot_months, B, seed, p_kind))
    years_of = months // 12
    years: Dict[int, Dict[str, Any]] = {}
    for year in np.unique(years_of):
        in_a, in_b = (years_of == year) & a, (years_of == year) & b
        if in_a.any() and in_b.any():
            years[int(year)] = {"n": int(in_a.sum() + in_b.sum()), "n_a": int(in_a.sum()), "n_b": int(in_b.sum()),
                                "mean_diff": float(x[in_a].mean() - x[in_b].mean())}
    counted = [y for y, row in years.items() if row["n"] >= min_year_units]
    out.update({"years": years, "years_n": len(counted), "years_pos": int(sum(years[y]["mean_diff"] > 0 for y in counted))})
    return out


# --------------------------------------------------------------------------- placebo


@dataclass(frozen=True, eq=False)
class SignFlip:
    """``mean(s · d)`` with **balanced** signs from the permutation: ``s_i = +1`` when
    ``perm_i < N // 2``, else ``-1`` — exactly ``N // 2`` plus signs per permutation.

    Under the null the variant and the base are exchangeable inside a unit, so flipping
    the sign of ``d`` is a draw from it. The signs are balanced on purpose (one
    permutation per step, one generator for every statistic); they are not independent
    ±1 and must not be "fixed" into them.
    """

    d: Any

    @property
    def n_units(self) -> int:
        return int(np.asarray(self.d).size)

    def __call__(self, perm: np.ndarray) -> float:
        d = np.asarray(self.d, dtype=float)
        return float((np.where(perm < len(d) // 2, 1.0, -1.0) * d).mean())


@dataclass(frozen=True, eq=False)
class PermuteFlags:
    """``mean(x[a[perm]]) - mean(x[b[perm]])`` — both group masks shuffled by one permutation."""

    x: Any
    flag_a: Any
    flag_b: Any

    @property
    def n_units(self) -> int:
        return int(np.asarray(self.x).size)

    def __call__(self, perm: np.ndarray) -> float:
        x = np.asarray(self.x, dtype=float)
        a, b = np.asarray(self.flag_a, dtype=bool), np.asarray(self.flag_b, dtype=bool)
        return float(x[a[perm]].mean() - x[b[perm]].mean())


@dataclass(frozen=True, eq=False)
class PermuteColumn:
    """``statistic(frame with column shuffled by the permutation)`` — the general case.

    For a caller that rebuilds the trades from a shuffled signal: ``statistic`` takes the
    frame and returns the number to compare with the observed one.
    """

    frame: pd.DataFrame
    column: str
    statistic: Callable[[pd.DataFrame], float]

    def __post_init__(self) -> None:
        if self.column not in self.frame.columns:
            raise ValueError(f"the frame has no column {self.column!r} to shuffle")

    @property
    def n_units(self) -> int:
        return len(self.frame)

    def __call__(self, perm: np.ndarray) -> float:
        shuffled = self.frame.copy()
        shuffled[self.column] = self.frame[self.column].to_numpy()[perm]
        return float(self.statistic(shuffled))


def permutation_placebo(
    observed: float,
    statistic: Callable[[np.ndarray], float],
    *,
    n_perm: int = 200,
    seed: int = 1,
    n_units: Optional[int] = None,
    batched: bool = False,
) -> Dict[str, Any]:
    """How the statistic falls when what it rests on is shuffled.

    ``rng = numpy.random.default_rng(seed)``; ``n_perm`` times in a row
    ``perm = rng.permutation(N)`` — exactly one draw per permutation, none other — and
    ``statistic(perm)``. ``placebo_mean_diff`` is the mean of those values and
    ``placebo_p`` the share of them ``>= observed``, **without** the ``+1`` correction.
    ``N`` is ``statistic.n_units`` (:class:`SignFlip`, :class:`PermuteFlags`,
    :class:`PermuteColumn`) or ``n_units`` for a plain callable.

    ``batched=True`` hands the statistic all permutations at once — an ``(n_perm, N)``
    matrix, drawn from the same generator in the same order — and expects ``n_perm``
    values back: for a statistic that computes every permutation in one vectorised pass
    (:func:`~bquant.analysis.trading.trades_at_exit` with a 2-d ``exit_idx``). The result
    is bit for bit that of the one-by-one call.
    """
    n = n_units if n_units is not None else getattr(statistic, "n_units", None)
    if n is None:
        raise ValueError("a plain statistic needs n_units, the number of units it permutes")
    n = _check_min(n, "n_units")
    n_perm = _check_min(n_perm, "n_perm")
    rng = np.random.default_rng(seed)
    if batched:
        perms = np.array([rng.permutation(n) for _ in range(n_perm)])
        values = np.asarray(statistic(perms), dtype=float)
        if values.shape != (n_perm,):
            raise ValueError(f"a batched statistic must return one value per permutation ({n_perm}), got shape {values.shape}")
    else:
        values = np.array([statistic(rng.permutation(n)) for _ in range(n_perm)], dtype=float)
    return {"placebo_mean_diff": float(values.mean()), "placebo_p": float(np.mean(values >= observed)), "n_perm": n_perm}
