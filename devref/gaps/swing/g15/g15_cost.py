#!/usr/bin/env python3
"""G15 part 2 — the two costs the divergence table does not show.

(a) The confirmation floor is MY addition to the candidate fix, so its price has to be
    measured, not assumed: how many swings get their availability pushed back by
    flooring at warm-up-1, and by how many bars.

(b) Are the swings the frozen threshold ADDS material, or noise? A lower threshold
    admits smaller extrema by construction — the question is how much smaller.
    Compared against the baseline population on the same data.
"""
from __future__ import annotations

import itertools
import json
import logging
import os

logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import numpy as np
import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy


class FrozenNoFloor(FindPeaksSwingStrategy):
    """Frozen warm-up threshold, WITHOUT the confirmation floor (to isolate the floor)."""

    def __init__(self, warmup: int, **kw):
        super().__init__(**kw)
        self.warmup = warmup

    def _resolve_prominence(self, data: pd.DataFrame) -> float:
        if self.prominence is not None:
            return float(self.prominence)
        head = data.iloc[: self.warmup]
        return max(float(head["high"].max() - head["low"].min()) * 0.01, 1e-9)


def prominence_of(df: pd.DataFrame, idx: int, swing_type: str) -> float:
    """scipy prominence of one extremum on the full series — its 'size'."""
    from scipy.signal import peak_prominences, find_peaks
    series = df["high"].to_numpy(float) if swing_type == "peak" else -df["low"].to_numpy(float)
    try:
        return float(peak_prominences(series, [idx])[0][0])
    except Exception:
        return float("nan")


def main():
    datasets = ["tv_xauusd_1h", "mt_xauusd_m15"]
    distances = [2, 3, 5, 10]
    warmups = [100, 200, 300]
    rows = []

    for ds, dist, n in itertools.product(datasets, distances, warmups):
        df = get_sample_data(ds)
        base = FindPeaksSwingStrategy(distance=dist, prominence=None)
        frz = FrozenNoFloor(warmup=n, distance=dist, prominence=None)

        cb = base.calculate_global(df)
        cf = frz.calculate_global(df)

        base_keys = {(sp.index, sp.swing_type) for sp in cb.swing_points}
        added = [sp for sp in cf.swing_points if (sp.index, sp.swing_type) not in base_keys]

        # (a) floor cost: how many confirmations move, and by how much
        floor = n - 1
        moved = [sp for sp in cf.swing_points
                 if sp.confirmation_index is not None and sp.confirmation_index < floor]
        deltas = [floor - sp.confirmation_index for sp in moved]

        # (b) size of added vs kept swings
        kept = [sp for sp in cf.swing_points if (sp.index, sp.swing_type) in base_keys]
        p_added = [prominence_of(df, sp.index, sp.swing_type) for sp in added]
        p_kept = [prominence_of(df, sp.index, sp.swing_type) for sp in kept]

        rows.append({
            "dataset": ds, "distance": dist, "warmup": n,
            "n_base": len(cb.swing_points), "n_frozen": len(cf.swing_points),
            "n_added": len(added),
            "floor_moved": len(moved),
            "floor_moved_pct": round(100 * len(moved) / max(len(cf.swing_points), 1), 1),
            "floor_delay_mean": round(float(np.mean(deltas)), 1) if deltas else 0.0,
            "floor_delay_max": int(max(deltas)) if deltas else 0,
            "prom_added_median": round(float(np.nanmedian(p_added)), 4) if p_added else None,
            "prom_kept_median": round(float(np.nanmedian(p_kept)), 4) if p_kept else None,
            "prom_added_max": round(float(np.nanmax(p_added)), 4) if p_added else None,
        })

    out = os.environ.get("G15_COST_OUT", "/tmp/g15_cost.json")
    with open(out, "w") as fh:
        json.dump(rows, fh, indent=2)
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
