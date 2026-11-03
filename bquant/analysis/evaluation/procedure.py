"""Does picking the best run on the back window beat not picking at all?

Input: one row per (window, run) with the back-window result, the forward-window result
and the run's parameters. Per window the chosen run is the one with the highest ``back``
(ties → the lower run number); it is set against three things that do not pick:
the run with the **default** parameters (exactly one row must match, otherwise ``NaN``),
the **mean over the grid** (a run drawn at random), and the **oracle** (the best
forward — an upper bound nobody reaches). Over the series: sums, medians, share of
positive windows, and the paired-difference ``t`` of chosen minus each baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd


@dataclass
class ProcedureResult:
    """``per_window`` (one row per window), ``series`` (one row per variant:
    sum, median, share_pos, min, max over windows), ``paired`` (one row per
    comparison: ``mean_diff``, ``t``, ``share_pos``, ``n``)."""

    per_window: pd.DataFrame
    series: pd.DataFrame
    paired: pd.DataFrame


def _paired_t(d: np.ndarray) -> float:
    d = d[np.isfinite(d)]
    if len(d) > 2 and d.std(ddof=1) > 0:
        return float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d))))
    return np.nan


def evaluate_procedure(
    runs: pd.DataFrame,
    defaults: Mapping[str, float],
    *,
    window_col: str = "window",
    pass_col: str = "pass",
    back_col: str = "back",
    forward_col: str = "forward",
) -> ProcedureResult:
    """Evaluate a pick-on-back, trade-forward procedure over a series of windows.

    ``defaults`` maps parameter column → default value; a window where the number of
    rows matching every default is not exactly one gets ``defaults = NaN``. Per window:
    ``chosen``, ``defaults``, ``grid_mean``, ``grid_median``, ``grid_pos_share``
    (share of forwards > 0), ``percentile`` (share of forwards **strictly below** the
    chosen one — 0.5 is what a random pick would score), ``oracle``.
    """
    needed = [window_col, pass_col, back_col, forward_col, *defaults]
    missing = [c for c in needed if c not in runs.columns]
    if missing:
        raise ValueError(f"evaluate_procedure: runs table is missing column(s) {missing}")
    if not defaults:
        raise ValueError("evaluate_procedure: defaults must name at least one parameter column")
    if runs.empty:
        raise ValueError("evaluate_procedure: runs table is empty")

    rows = []
    for window, group in runs.groupby(window_col, sort=True):
        ordered = group.sort_values([back_col, pass_col], ascending=[False, True], kind="stable")
        chosen = ordered.iloc[0]
        mask = np.ones(len(group), dtype=bool)
        for key, value in defaults.items():
            mask &= np.isclose(group[key].to_numpy(dtype=float), float(value))
        default_rows = group[mask]
        forward = group[forward_col].to_numpy(dtype=float)
        rows.append({
            "window": window,
            "chosen": float(chosen[forward_col]),
            "chosen_pass": chosen[pass_col],
            "defaults": float(default_rows[forward_col].iloc[0]) if len(default_rows) == 1 else np.nan,
            "grid_mean": float(forward.mean()),
            "grid_median": float(np.median(forward)),
            "grid_pos_share": float((forward > 0).mean()),
            "percentile": float((forward < float(chosen[forward_col])).mean()),
            "oracle": float(forward.max()),
            "runs": int(len(group)),
        })
    per_window = pd.DataFrame(rows)

    def over_series(x: pd.Series) -> dict:
        v = x.to_numpy(dtype=float)
        v = v[np.isfinite(v)]
        if len(v) == 0:
            return {"sum": np.nan, "median": np.nan, "share_pos": np.nan, "min": np.nan, "max": np.nan, "n": 0}
        return {"sum": float(v.sum()), "median": float(np.median(v)), "share_pos": float((v > 0).mean()),
                "min": float(v.min()), "max": float(v.max()), "n": int(len(v))}

    series = pd.DataFrame(
        {name: over_series(per_window[name]) for name in ("chosen", "defaults", "grid_mean", "oracle")}
    ).T
    series.index.name = "variant"

    paired_rows = {}
    for baseline in ("grid_mean", "defaults"):
        d = (per_window["chosen"] - per_window[baseline]).to_numpy(dtype=float)
        finite = d[np.isfinite(d)]
        paired_rows[f"chosen_vs_{baseline}"] = {
            "mean_diff": float(finite.mean()) if len(finite) else np.nan,
            "t": _paired_t(d),
            "share_pos": float((finite > 0).mean()) if len(finite) else np.nan,
            "n": int(len(finite)),
        }
    paired = pd.DataFrame(paired_rows).T
    paired.index.name = "comparison"
    return ProcedureResult(per_window=per_window, series=series, paired=paired)
