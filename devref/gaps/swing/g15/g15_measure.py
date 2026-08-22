#!/usr/bin/env python3
"""G15 measurement harness — is a frozen warm-up prominence worth its semantic cost?

The defect: with ``prominence=None`` (the find_peaks DEFAULT) the threshold is
``(high.max() - low.min()) * 0.01`` over the WHOLE observed window, so it is
monotonically non-decreasing in t. An extremum that cleared the early, smaller
threshold can fail the later, larger one and vanish — after a consumer was told
it was available. No confirmation_index can repair a filter that keeps moving.

The candidate fix has TWO parts, and the second is easy to forget:
  1. freeze the threshold on the first N bars: ``(high[:N].max() - low[:N].min()) * 0.01``.
     Under truncation to t+1 >= N the first N bars are unchanged, so the threshold is
     identical on replay — that is the whole point.
  2. floor confirmation_index at N-1. Without it a swing could be confirmed while
     t < N, where the window is still short and the threshold still differs — the
     same hole, merely narrower.

Measured per (dataset x distance x policy):
  * replay-safety, both directions, using the SHIPPED oracle definitions
  * detection divergence vs the current policy on full history (added/removed/Jaccard)
  * the threshold trajectory itself (how far it actually travels)
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

os.environ.setdefault("BQUANT_LOG_LEVEL", "ERROR")

import logging

logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import numpy as np
import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy


# --------------------------------------------------------------------------
# Policies
# --------------------------------------------------------------------------

class LegacyExpandingProminence(FindPeaksSwingStrategy):
    """The pre-G15 behaviour: auto threshold over the WHOLE observed window.

    Kept so the defect stays reproducible after the fix shipped. This is what the
    `current` policy measured before 2026-08-22 — the threshold grows with every
    new bar, so an extremum that cleared the early, smaller value can fail the
    later, larger one and vanish.
    """

    def _active_warmup(self):  # no freeze, no confirmation floor
        return None

    def _resolve_prominence(self, data: pd.DataFrame, *, warmup=None) -> float:
        if self.prominence is not None:
            return float(self.prominence)
        price_range = float(data["high"].max() - data["low"].min())
        return max(price_range * 0.01, 1e-9)


def build(policy: str, distance: int):
    """`current` = the shipped legacy behaviour; `frozen-N` = the shipped fix."""
    if policy == "current":
        return LegacyExpandingProminence(distance=distance, prominence=None)
    if policy.startswith("frozen"):
        n = int(policy.split("-")[1])
        return FindPeaksSwingStrategy(
            distance=distance, prominence=None, prominence_warmup=n
        )
    raise ValueError(policy)


# --------------------------------------------------------------------------
# Oracle (identical semantics to tests/unit/test_swing_replay_causal.py)
# --------------------------------------------------------------------------

def _present(context, sp) -> bool:
    return any(
        t.index == sp.index and t.swing_type == sp.swing_type
        and abs(t.price - sp.price) < 1e-6
        for t in context.swing_points
    )


def repaint_violations(strategy, df) -> int:
    full = strategy.calculate_global(df)
    n = 0
    for sp in full.swing_points:
        ci = sp.confirmation_index
        if ci is None or ci >= len(df):
            continue
        if not _present(strategy.calculate_global(df.iloc[: ci + 1]), sp):
            n += 1
    return n


def vanish_violations(strategy, df, step: int) -> tuple[int, int, list]:
    """Swings a consumer could act on at bar t that are absent from full history.

    Returns (occurrences, distinct swings, a few examples). Occurrences double-count a
    swing seen at several checkpoints; the distinct count is the honest headline.
    """
    full = strategy.calculate_global(df)
    n = 0
    distinct = set()
    examples = []
    for t in range(50, len(df), step):
        ctx = strategy.calculate_global(df.iloc[: t + 1])
        for sp in ctx.swing_points:
            if sp.confirmation_index is None or sp.confirmation_index > t:
                continue
            if not _present(full, sp):
                n += 1
                distinct.add((sp.index, sp.swing_type))
                if len(examples) < 5:
                    examples.append(
                        {"seen_at_bar": t, "index": int(sp.index),
                         "type": sp.swing_type, "price": round(float(sp.price), 2)}
                    )
    return n, len(distinct), examples


def key_set(ctx) -> set:
    return {(sp.index, sp.swing_type) for sp in ctx.swing_points}


def threshold_trajectory(df, warmups) -> dict:
    """How far the current (expanding) threshold actually travels, and the frozen values."""
    hi = df["high"].to_numpy(dtype=float)
    lo = df["low"].to_numpy(dtype=float)
    run_max = np.maximum.accumulate(hi)
    run_min = np.minimum.accumulate(lo)
    traj = (run_max - run_min) * 0.01
    out = {
        "current_at_50": float(traj[50]),
        "current_final": float(traj[-1]),
        "growth_x": float(traj[-1] / traj[50]) if traj[50] > 0 else None,
    }
    for n in warmups:
        out[f"frozen_{n}"] = float((hi[:n].max() - lo[:n].min()) * 0.01)
    return out


# --------------------------------------------------------------------------
# Job
# --------------------------------------------------------------------------

@dataclass
class Job:
    dataset: str
    distance: int
    policy: str
    step: int


def run_job(job: Job) -> dict:
    df = get_sample_data(job.dataset)
    strat = build(job.policy, job.distance)
    base = build("current", job.distance)

    t0 = time.perf_counter()
    ctx = strat.calculate_global(df)
    ctx_base = base.calculate_global(df)

    ks, kb = key_set(ctx), key_set(ctx_base)
    inter = len(ks & kb)
    union = len(ks | kb)

    res = {
        "dataset": job.dataset,
        "distance": job.distance,
        "policy": job.policy,
        "n_swings": len(ctx.swing_points),
        "n_swings_current": len(ctx_base.swing_points),
        "added_vs_current": len(ks - kb),
        "removed_vs_current": len(kb - ks),
        "jaccard": round(inter / union, 4) if union else 1.0,
        "repaint": repaint_violations(strat, df),
        "n_confirmed": sum(1 for sp in ctx.swing_points if sp.confirmation_index is not None),
    }
    occ, distinct, examples = vanish_violations(strat, df, job.step)
    res["vanish_occurrences"] = occ
    res["vanish_distinct"] = distinct
    res["vanish_examples"] = examples
    res["secs"] = round(time.perf_counter() - t0, 1)
    return res


def main():
    datasets = ["tv_xauusd_1h", "mt_xauusd_m15"]
    distances = [2, 3, 5, 10]
    warmups = [50, 100, 150, 200, 300, 500]
    policies = ["current"] + [f"frozen-{n}" for n in warmups]
    step = int(os.environ.get("G15_STEP", "25"))

    jobs = [
        Job(d, dist, p, step)
        for d, dist, p in itertools.product(datasets, distances, policies)
    ]
    print(f"jobs: {len(jobs)}  (step={step})", flush=True)

    workers = int(os.environ.get("G15_WORKERS", str(min(os.cpu_count() or 4, 24))))
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(run_job, jobs))
    elapsed = time.perf_counter() - t0

    traj = {d: threshold_trajectory(get_sample_data(d), warmups) for d in datasets}

    out = {
        "elapsed_s": round(elapsed, 1),
        "workers": workers,
        "step": step,
        "thresholds": traj,
        "results": results,
    }
    path = os.environ.get("G15_OUT", "/tmp/g15_results.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {path} in {elapsed:.1f}s with {workers} workers", flush=True)


if __name__ == "__main__":
    main()
