#!/usr/bin/env python3
"""G21 measurement — `min_duration` silently turns a tiling into a gapped partition.

Every shipped detector produces zones that *tile* the timeline: each bar belongs
to exactly one zone, and zone `i+1` starts where zone `i` ended. Sequence
analysis is built on that: it takes the ordered list of zone *types* and reads
consecutive entries as a transition. It never looks at `start_idx`/`end_idx` —
grep the module, the fields do not appear.

`min_duration` (default: 2) drops zones shorter than the threshold. The zones on
either side of a dropped one are then no longer adjacent, but the sequence
analysis cannot tell: it still reports a transition between them. The transition
"bull -> bear" may in fact mean "bull, then a bar of bear that was discarded,
then bear" — or, with a larger threshold, a longer stretch of discarded history.

Measured rather than argued because the defect is invisible from the result: the
transition counts, the Markov matrix and the runs test are all well-formed. Only
comparing zone boundaries against the source frame reveals the gaps.

Run:
    venv_bquant/bin/python devref/gaps/sequence/g21/g21_measure.py
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import pandas as pd

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

DATASET = "tv_xauusd_1h"
DEFAULT_MIN_DURATION = 2  # ZoneDetectionConfig.min_duration


def _with_rsi(data: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    import pandas_ta as ta

    data = data.copy()
    data[f"RSI_{length}"] = ta.rsi(data["close"], length=length)
    return data


def _coverage(zones, n_bars: int):
    """Bars covered, and the gaps between consecutive zones."""
    zones = sorted(zones, key=lambda z: z.start_idx)
    covered = sum(z.end_idx - z.start_idx + 1 for z in zones)
    gaps = [
        b.start_idx - a.end_idx - 1
        for a, b in zip(zones, zones[1:])
        if b.start_idx > a.end_idx + 1
    ]
    return len(zones), covered, len(gaps), sum(gaps)


def _threshold(data, min_duration):
    return (
        analyze_zones(data)
        .detect_zones(
            "threshold",
            indicator_col="RSI_14",
            zone_types=["overbought", "neutral", "oversold"],
            upper_threshold=70,
            lower_threshold=30,
            min_duration=min_duration,
        )
        .with_cache(False)
        .build()
    ).zones


def _zero_crossing(data, min_duration):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist", min_duration=min_duration)
        .with_cache(False)
        .build()
    ).zones


def measure_tiling(data: pd.DataFrame) -> None:
    """At min_duration=1 the partition tiles. Every gap above that is ours."""
    n = len(data)
    for label, detect in (
        ("threshold RSI (all three types)", _threshold),
        ("zero_crossing MACD (the flagship path)", _zero_crossing),
    ):
        print(f"\n{label}:")
        for md in (1, 2, 3, 5):
            zones, covered, n_gaps, lost = _coverage(detect(data, md), n)
            mark = "  <- default" if md == DEFAULT_MIN_DURATION else ""
            print(
                f"  min_duration={md}: zones={zones:3d} covered={covered:4d}/{n} "
                f"({100 * covered / n:5.1f}%) gaps={n_gaps:2d} bars_lost={lost:3d}{mark}"
            )
        print("  -> min_duration=1 tiles with zero gaps; every gap above it is "
              "introduced by the filter.")


def measure_fictitious_transitions(data: pd.DataFrame) -> None:
    """How many reported transitions are between non-adjacent zones."""
    print("\nfictitious transitions at the default min_duration:")
    for label, detect in (
        ("threshold RSI", _threshold),
        ("zero_crossing MACD", _zero_crossing),
    ):
        zones = sorted(detect(data, DEFAULT_MIN_DURATION), key=lambda z: z.start_idx)
        pairs = list(zip(zones, zones[1:]))
        fictitious = [(a, b) for a, b in pairs if b.start_idx > a.end_idx + 1]
        print(f"  {label:20s} {len(fictitious):2d} of {len(pairs)} reported "
              f"transitions span a gap "
              f"({100 * len(fictitious) / len(pairs):.1f}%)")
        for a, b in fictitious[:3]:
            print(f"      '{a.type}' -> '{b.type}' actually skips "
                  f"{b.start_idx - a.end_idx - 1} bar(s)")


def measure_impossible_transitions(data: pd.DataFrame) -> None:
    """The sharpest form: transitions the detector cannot physically produce.

    `zero_crossing` splits the series where the indicator crosses zero, so its
    zones must strictly alternate bull/bear — a `bull -> bull` transition is not
    a rare event, it is impossible. Any that appear are artefacts of the filter.
    """
    print("\nstructurally impossible transitions (zero_crossing must alternate):")
    for md in (1, DEFAULT_MIN_DURATION):
        zones = sorted(_zero_crossing(data, md), key=lambda z: z.start_idx)
        same = [(a, b) for a, b in zip(zones, zones[1:]) if a.type == b.type]
        mark = "  <- default" if md == DEFAULT_MIN_DURATION else ""
        print(f"  min_duration={md}: {len(same):2d} of {len(zones) - 1} consecutive "
              f"pairs share a type{mark}")
    print("  -> zero at min_duration=1, so the alternation is real and the filter "
          "breaks it.\n     Those pairs enter the transition matrix as "
          "'bull -> bull' counts.")


def measure_analysis_no_longer_counts_across_gaps(data: pd.DataFrame) -> None:
    """What the analysis now does with those gaps.

    The gaps themselves are unchanged — dropping short zones is what
    ``min_duration`` is for, and that is the caller's choice (variant **a** of the
    fix; making ``min_duration`` a reporting filter instead of a detection filter
    remains open). What changed is that the analysis no longer *counts across*
    them: a pair separated by a gap is not reported as a transition, the count of
    discarded pairs is published, and the impossible ``bull -> bull`` entries are
    gone from the Markov matrix.
    """
    print("\nwhat the analysis reports at the default min_duration:")
    for label, detect in (
        ("threshold RSI", _threshold_analysed),
        ("zero_crossing MACD", _zero_crossing_analysed),
    ):
        result = detect(data, DEFAULT_MIN_DURATION)
        summary = result.sequence_analysis["sequence_summary"]
        markov = result.sequence_analysis["markov_analysis"]
        diagonal = (
            [markov["transition_matrix"][i][i] for i in range(len(markov["states"]))]
            if "transition_matrix" in markov else []
        )
        print(f"  {label}:")
        print(f"    zones={summary['total_zones']}, "
              f"transitions counted={summary['total_transitions']}, "
              f"discarded across gaps={summary['discarded_transitions']}, "
              f"bars missing={summary['bars_missing']}")
        print(f"    markov states={markov.get('states')}, diagonal={diagonal}")
    print("  -> the diagonal is the invariant: for zero_crossing it must be all "
          "zeros, because\n     a zone ends where the indicator crosses zero and the "
          "next zone is the other type.")


def _threshold_analysed(data, min_duration):
    return (
        analyze_zones(data)
        .detect_zones(
            "threshold",
            indicator_col="RSI_14",
            zone_types=["overbought", "neutral", "oversold"],
            upper_threshold=70,
            lower_threshold=30,
            min_duration=min_duration,
        )
        .analyze(clustering=False)
        .with_cache(False)
        .build()
    )


def _zero_crossing_analysed(data, min_duration):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist", min_duration=min_duration)
        .analyze(clustering=False)
        .with_cache(False)
        .build()
    )


def measure_blindness() -> None:
    """Boundaries now reach the layer that needs them.

    Before the fix `start_idx`/`end_idx` appeared zero times in the module: it
    consumed an ordered list of type labels, so adjacency could only be assumed.
    """
    import inspect

    from bquant.analysis.zones import sequence_analysis

    source = inspect.getsource(sequence_analysis)
    print("\nwhat the sequence layer can see:")
    for field in ("start_idx", "end_idx", "start_time", "end_time"):
        print(f"  '{field}' occurrences in sequence_analysis.py: {source.count(field)}")
    print("  -> non-zero counts mean adjacency is checked against the zone "
          "boundaries.\n     Before the fix every one of these was 0.")


def main() -> None:
    data = _with_rsi(get_sample_data(DATASET))
    print(f"dataset: {DATASET}, {len(data)} bars")
    measure_tiling(data)
    measure_fictitious_transitions(data)
    measure_impossible_transitions(data)
    measure_analysis_no_longer_counts_across_gaps(data)
    measure_blindness()


if __name__ == "__main__":
    main()
