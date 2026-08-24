#!/usr/bin/env python3
"""G19 measurement — the default `zone_types` silences two detection strategies.

`ZoneDetectionConfig.__post_init__` fills an unset `zone_types` with
``['bull', 'bear']``:

    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = ['bull', 'bear']

Its own docstring says something different — "None = все возможные для стратегии"
(None = every type the strategy can produce). The code instead hardcodes the
vocabulary of the MACD-shaped detectors.

Every detector then filters its output through that list:

    if zone_type not in config.zone_types:
        continue

For `zero_crossing`, `line_crossing` and `preloaded` — which emit `bull`/`bear` —
the default is harmless. For `threshold` (`overbought`/`neutral`/`oversold`) and
`combined` (`active`/`inactive` by default, or whatever `zone_type_map` says) the
intersection with `['bull', 'bear']` is EMPTY, so every zone is discarded and the
caller gets a silent, successful, empty result.

This is measured rather than argued because the consequence is easy to misread as
"the thresholds did not match this data": the detector logs `Detected 0 zones` and
nothing indicates that zones were found and then filtered away.

Run:
    venv_bquant/bin/python devref/gaps/detection/g19/g19_measure.py
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import pandas as pd

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.detection.base import ZoneDetectionConfig
from bquant.analysis.zones.detection.combined import CombinedRulesDetection
from bquant.data.samples import get_sample_data

DATASET = "tv_xauusd_1h"


def _rsi(data: pd.DataFrame, length: int = 14) -> pd.Series:
    import pandas_ta as ta

    return ta.rsi(data["close"], length=length)


def measure_default_vocabulary() -> None:
    """What each detector emits, versus what an unset `zone_types` lets through.

    The old default filled an unset `zone_types` with ``['bull', 'bear']``, so the
    two detectors whose vocabulary is anything else lost every zone they found.
    """
    from bquant.analysis.zones.detection.base import ZoneDetectionConfig

    emitted = {
        "zero_crossing": ["bull", "bear"],
        "line_crossing": ["bull", "bear"],
        "preloaded": ["<from the imported data>"],
        "threshold": ["overbought", "neutral", "oversold"],
        "combined": ["<from the caller's zone_type_map>"],
    }
    old_default = ["bull", "bear"]
    unset = ZoneDetectionConfig()

    print(f"unset zone_types is now {unset.zone_types!r} "
          f"(was implicitly {old_default})")
    print("detector        emits                                  "
          "old default / now")
    for name, types in emitted.items():
        concrete = [t for t in types if not t.startswith("<")]
        survived_old = bool([t for t in concrete if t in old_default])
        old_verdict = "ok" if survived_old else "NOTHING SURVIVED"
        now_verdict = "all pass" if all(unset.accepts(t) for t in concrete) else "filtered"
        print(f"  {name:14s} {str(types):38s} {old_verdict:16s} / {now_verdict}")


def measure_threshold(data: pd.DataFrame) -> None:
    """The documented RSI example, with and without an explicit zone_types."""
    data = data.copy()
    data["RSI_14"] = _rsi(data)

    above = int((data["RSI_14"] > 70).sum())
    below = int((data["RSI_14"] < 30).sum())
    print(f"\nthreshold: bars above 70 = {above}, below 30 = {below} "
          f"(so zones certainly exist in this data)")

    for zone_types in (None, ["overbought", "oversold"], ["overbought", "neutral", "oversold"]):
        result = (
            analyze_zones(data)
            .detect_zones(
                "threshold",
                indicator_col="RSI_14",
                zone_types=zone_types,
                upper_threshold=70,
                lower_threshold=30,
            )
            .with_cache(False)
            .build()
        )
        print(f"  zone_types={str(zone_types):46s} -> {len(result.zones):3d} zones")


def measure_combined(data: pd.DataFrame) -> None:
    """The second example from CombinedRulesDetection's own docstring."""
    data = data.copy()
    data["RSI_14"] = _rsi(data)
    conditions = [lambda df: df["RSI_14"] > 70]

    print("\ncombined (the docstring's own OR example, which omits zone_types):")
    for zone_types in (None, ["overbought", "neutral"]):
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=zone_types,
            rules={
                "conditions": conditions,
                "logic": "OR",
                "zone_type_map": {True: "overbought", False: "neutral"},
            },
            strategy_name="combined",
        )
        zones = CombinedRulesDetection().detect_zones(data, config)
        print(f"  zone_types={str(zone_types):46s} -> {len(zones):3d} zones")


def measure_readme_example(data: pd.DataFrame) -> None:
    """The Quick Start block from README.md, verbatim.

    Two defects stack here. `indicator_col='rsi'` does not name the computed column
    (`RSI_14`); it happens to resolve because the bundled sample ships its own `rsi`
    column from the TradingView export — that part is the G8 family. Then G19
    discards whatever was found. Correcting only the column name still yields zero.
    """
    print("\nREADME Quick Start, verbatim:")
    result = (
        analyze_zones(data)
        .with_indicator("pandas_ta", "rsi", length=14)
        .detect_zones("threshold", indicator_col="rsi",
                      upper_threshold=70, lower_threshold=30)
        .analyze(clustering=True)
        .with_cache(False)
        .build()
    )
    print(f"  as written                       -> Found {len(result.zones)} zones")

    fixed_col = (
        analyze_zones(data)
        .with_indicator("pandas_ta", "rsi", length=14)
        .detect_zones("threshold", indicator_col="RSI_14",
                      upper_threshold=70, lower_threshold=30)
        .analyze(clustering=True)
        .with_cache(False)
        .build()
    )
    print(f"  with the column name corrected   -> Found {len(fixed_col.zones)} zones")

    fixed_both = (
        analyze_zones(data)
        .with_indicator("pandas_ta", "rsi", length=14)
        .detect_zones("threshold", indicator_col="RSI_14",
                      zone_types=["overbought", "oversold"],
                      upper_threshold=70, lower_threshold=30)
        .analyze(clustering=True)
        .with_cache(False)
        .build()
    )
    print(f"  column name + zone_types         -> Found {len(fixed_both.zones)} zones")


def main() -> None:
    data = get_sample_data(DATASET)
    print(f"dataset: {DATASET}\n")
    measure_default_vocabulary()
    measure_threshold(data)
    measure_combined(data)
    measure_readme_example(data)


if __name__ == "__main__":
    main()
