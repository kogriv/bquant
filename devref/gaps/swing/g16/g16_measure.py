#!/usr/bin/env python3
"""G16 measurement — what the adaptive threshold layer actually does to each strategy.

`auto_swing_thresholds` returns RELATIVE quantities (`price_range / mid_price * k`).
`_AdaptiveSwingStrategy._apply_thresholds_to_strategy` routes them per strategy:

    zigzag        -> deviation           (relative)  ✔ units match
    pivot_points  -> min_amplitude_pct   (relative)  ✔ units match
    find_peaks    -> min_amplitude_pct   (relative)  ✔
                  -> prominence          (ABSOLUTE, price units)  ✘ units clash

The last one is G16: a fraction (~0.019) lands in a knob scipy reads as an amount of
price. Gold trades near 3350, so the filter is handed a threshold of under two cents
and stops filtering.

The naive repair — multiplying by price to get "real" units — is measured here too, and
it is worse: the `* 0.3` coefficient only makes sense in the relative domain (0.3 x 6.2%
= 1.9%, a sensible move), and converting it yields ~30% of the whole observed range.

The proposed repair is to stop setting `prominence` from the adaptive layer at all:
find_peaks already derives its own range-adaptive prominence (`price_range * 0.01`), and
since G15 that one is frozen on a warm-up window and replay-safe. The adaptive layer then
contributes only what it can express correctly — the relative amplitude floor.
"""
from __future__ import annotations

import itertools
import json
import logging
import os

logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.analysis.zones.strategies.swing.thresholds import (
    _AdaptiveSwingStrategy,
    auto_swing_thresholds,
)


class LegacyAdaptive(_AdaptiveSwingStrategy):
    """Pre-G16 routing: the relative value is also pushed into find_peaks' prominence."""

    def _apply_thresholds_to_strategy(self, strategy, thresholds) -> None:
        if self.base_strategy_name == "zigzag":
            strategy.deviation = thresholds.zigzag_deviation
        elif self.base_strategy_name == "find_peaks":
            strategy.prominence = thresholds.peak_min_amplitude          # the units clash
            strategy.min_amplitude_pct = thresholds.peak_min_amplitude
        elif self.base_strategy_name == "pivot_points":
            strategy.min_amplitude_pct = thresholds.pivot_deviation


class NaiveUnitCast(_AdaptiveSwingStrategy):
    """The repair that looks obvious and is wrong: scale the fraction back to price."""

    def _apply_thresholds_to_strategy(self, strategy, thresholds) -> None:
        if self.base_strategy_name == "find_peaks":
            mid = float(self._reference_price)
            strategy.prominence = thresholds.peak_min_amplitude * mid
            strategy.min_amplitude_pct = thresholds.peak_min_amplitude
        else:
            super()._apply_thresholds_to_strategy(strategy, thresholds)


class ProposedAdaptive(_AdaptiveSwingStrategy):
    """The proposed routing: never touch `prominence`, leave it on the strategy's own auto.

    Kept explicit so the intended behaviour can be measured before it ships, and so the
    shipped class can be checked against it afterwards (they must agree).
    """

    def _apply_thresholds_to_strategy(self, strategy, thresholds) -> None:
        if self.base_strategy_name == "zigzag":
            strategy.deviation = thresholds.zigzag_deviation
        elif self.base_strategy_name == "find_peaks":
            strategy.min_amplitude_pct = thresholds.peak_min_amplitude
        elif self.base_strategy_name == "pivot_points":
            strategy.min_amplitude_pct = thresholds.pivot_deviation


def effective_params(strategy) -> dict:
    base = strategy.base_strategy
    return {
        k: round(float(v), 6)
        for k, v in (
            ("deviation", getattr(base, "deviation", None)),
            ("prominence", getattr(base, "prominence", None)),
            ("min_amplitude_pct", getattr(base, "min_amplitude_pct", None)),
        )
        if v is not None
    }


CONFIGS = {
    "zigzag": {"legs": 3, "deviation": 0.008},
    "find_peaks": {"distance": 3},
    "pivot_points": {"left_bars": 3, "right_bars": 3},
}


def run(dataset: str, name: str, mode: str) -> dict:
    df = get_sample_data(dataset)
    params = CONFIGS[name]
    cls = {"legacy": LegacyAdaptive, "naive": NaiveUnitCast,
           "proposed": ProposedAdaptive, "shipped": _AdaptiveSwingStrategy}[mode]
    strategy = cls(name, params, base_deviation=0.01)
    if mode == "naive":
        strategy._reference_price = float(df["close"].median())
    ctx = strategy.calculate_global(df)
    keys = {(sp.index, sp.swing_type) for sp in ctx.swing_points}
    return {
        "dataset": dataset, "strategy": name, "mode": mode,
        "n_swings": len(ctx.swing_points),
        "effective": effective_params(strategy),
        "_keys": keys,
    }


def main():
    datasets = ["tv_xauusd_1h", "mt_xauusd_m15"]
    rows = []
    for ds, name in itertools.product(datasets, CONFIGS):
        by_mode = {}
        for mode in ("legacy", "naive", "proposed", "shipped"):
            try:
                by_mode[mode] = run(ds, name, mode)
            except Exception as exc:  # naive only defines find_peaks behaviour
                by_mode[mode] = {"error": f"{type(exc).__name__}: {exc}"}
        legacy = by_mode["legacy"]
        for mode, r in by_mode.items():
            if "error" in r:
                continue
            if mode != "legacy" and "_keys" in legacy:
                r["added_vs_legacy"] = len(r["_keys"] - legacy["_keys"])
                r["removed_vs_legacy"] = len(legacy["_keys"] - r["_keys"])
            r.pop("_keys", None)
            rows.append(r)
        legacy.pop("_keys", None)

    # what the raw threshold numbers look like, per dataset
    context = {}
    for ds in datasets:
        df = get_sample_data(ds)
        t = auto_swing_thresholds(df, base_deviation=0.01)
        rng = float(df["high"].max() - df["low"].min())
        mid = float(df["close"].median())
        context[ds] = {
            "price_range": round(rng, 2),
            "mid_price": round(mid, 2),
            "relative_range": round(rng / mid, 4),
            "zigzag_deviation": round(t.zigzag_deviation, 6),
            "peak_min_amplitude_relative": round(t.peak_min_amplitude, 6),
            "pivot_deviation": round(t.pivot_deviation, 6),
            "naive_cast_to_price": round(t.peak_min_amplitude * mid, 2),
            "find_peaks_own_auto": round(rng * 0.01, 2),
        }

    out = os.environ.get("G16_OUT", "/tmp/g16_results.json")
    with open(out, "w") as fh:
        json.dump({"context": context, "results": rows}, fh, indent=2, ensure_ascii=False)
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
