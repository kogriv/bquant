#!/usr/bin/env python3
"""G20 measurement — the universal layers only understand `bull`/`bear`.

Zone *detection* is already pluggable: five strategies ship, each declares the
vocabulary it emits, and `threshold` emits `overbought`/`neutral`/`oversold`
while `combined` emits whatever the caller's `zone_type_map` says. The zone
*model* is vocabulary-agnostic too — `Zone.type` is documented as a free label
("bull", "bear", "oversold", etc.).

Everything downstream of the model, however, compares that label against two
string literals. Three separate assumptions are fused into a single `==`:

    1. there are exactly two zone types,
    2. they are mutually opposite,
    3. they are spelled `bull` and `bear`.

So a non-MACD detector produces zones correctly and then loses its direction
metrics, its Markov chain, and its hypothesis tests — silently in two of the
three cases.

This is measured rather than argued because two of the three failures return a
successful-looking result: an all-zero transition matrix and a degenerate runs
test read as findings, not as errors.

Run:
    venv_bquant/bin/python devref/gaps/zone_types/g20/g20_measure.py
"""
from __future__ import annotations

import logging
import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import numpy as np
import pandas as pd

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

DATASET = "tv_xauusd_1h"


def _with_rsi(data: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    import pandas_ta as ta

    data = data.copy()
    data[f"RSI_{length}"] = ta.rsi(data["close"], length=length)
    return data


def _zones(data: pd.DataFrame):
    """A threshold analysis that genuinely finds zones (zone_types explicit — G19)."""
    return (
        analyze_zones(data)
        .detect_zones(
            "threshold",
            indicator_col="RSI_14",
            zone_types=["overbought", "oversold"],
            upper_threshold=70,
            lower_threshold=30,
        )
        .with_cache(False)
        .build()
    )


def _zones_with_analysis(data: pd.DataFrame, zone_types):
    """Threshold analysis with the analytic layers actually run."""
    return (
        analyze_zones(data)
        .detect_zones(
            "threshold",
            indicator_col="RSI_14",
            zone_types=zone_types,
            upper_threshold=70,
            lower_threshold=30,
        )
        .analyze(clustering=False)
        .with_cache(False)
        .build()
    )


def measure_declared_vocabulary() -> None:
    """Every strategy declares its vocabulary. Nothing reads the declaration."""
    from bquant.analysis.zones.detection import ZoneDetectionRegistry  # noqa: F401
    from bquant.analysis.zones.detection.registry import ZoneDetectionRegistry as R

    print("declared vocabulary per strategy (registry metadata):")
    for name, info in sorted(R.list_all_info().items()):
        print(f"  {name:16s} supported_zones={info['supported_zones']}")
    print("  -> an empty list means the vocabulary is determined at runtime "
          "(preloaded reads it\n     from the data, combined from the caller's rules), "
          "not that the strategy has no types.")


def measure_feature_extraction(result) -> None:
    """The direction-dependent metrics are keyed on the two names."""
    from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

    analyzer = ZoneFeaturesAnalyzer()
    features = [analyzer.extract_zone_features(z.to_analyzer_format())
                for z in result.zones]

    types = sorted({f.zone_type for f in features})
    filled = {
        "drawdown_from_peak": sum(f.drawdown_from_peak is not None for f in features),
        "rally_from_trough": sum(f.rally_from_trough is not None for f in features),
        "peak_time_ratio": sum(f.peak_time_ratio is not None for f in features),
        "trough_time_ratio": sum(f.trough_time_ratio is not None for f in features),
    }
    print(f"\nfeature extraction over {len(features)} zones, types={types}:")
    for metric, count in filled.items():
        print(f"  {metric:20s} populated on {count:3d} / {len(features)} zones")
    print("  -> all four are computed for every zone. Before the fix this read "
          "0 / 18 on each\n     line: the branch keyed on the NAME populated two "
          "fields for 'bull', two for\n     'bear' and none for anything else.")


def measure_markov(data: pd.DataFrame) -> None:
    """The Markov path used to return a fabricated answer; now it returns the data.

    Before the fix, on a three-type vocabulary: an all-zero 2x2 matrix, ``states:
    ['bull', 'bear']`` and a stationary distribution of ``[1.0, 0.0]`` — a
    confident claim about a state that never occurs in the series — while the
    generic counter in the same result dict had the transitions right.

    Both vocabularies are run here because the contrast is the point, and it also
    demonstrates why the neutral band belongs in the default set (G19): with the
    signal zones alone, **no two zones are adjacent at all**, so there is nothing
    to build a chain from, and the analysis now says exactly that instead of
    printing zeros.
    """
    for label, zone_types in (
        ("signal zones only", ["overbought", "oversold"]),
        ("all three declared types", ["overbought", "neutral", "oversold"]),
    ):
        result = _zones_with_analysis(data, zone_types)
        sequence = result.sequence_analysis
        markov = sequence["markov_analysis"]
        summary = sequence["sequence_summary"]

        print(f"\nMarkov chain — {label} ({len(result.zones)} zones):")
        print(f"  adjacent pairs: {summary['total_transitions']}, "
              f"discarded across gaps: {summary['discarded_transitions']}")
        print(f"  transitions (generic counter): {sequence['transitions'] or '{}'}")

        if "error" in markov:
            print(f"  markov: {markov['error']}")
            print(f"  states seen: {markov['states']}")
            print("  -> an honest refusal, not a zero matrix presented as a result")
            continue

        print(f"  markov states:        {markov['states']}")
        print(f"  observed transitions: {markov['observed_transitions']}")
        for row in markov["transition_matrix"]:
            print(f"    {row}")
        print(f"  stationary:           "
              f"{[round(v, 4) for v in markov['stationary_distribution']]}")
        print(f"  -> states come from the observed sequence, and the two paths agree: "
              f"{markov['observed_transitions']} == "
              f"{sum(sequence['transitions'].values())}")


def measure_randomness(data: pd.DataFrame) -> None:
    """The runs test is binarised by declared polarity, not by the name 'bull'."""
    result = _zones_with_analysis(data, ["overbought", "neutral", "oversold"])
    tests = result.sequence_analysis["randomness_tests"]

    print("\nrandomness tests (all three declared types):")
    runs = tests["runs_test"]
    if "not_applicable" in runs:
        print(f"  runs_test: not applicable — {runs['not_applicable']}")
    else:
        print(f"  runs_test p={runs['p_value']:.4f}, basis={runs['basis']}")
    uniformity = tests["uniformity_test"]
    if "not_applicable" in uniformity:
        print(f"  uniformity: not applicable — {uniformity['not_applicable']}")
    else:
        print(f"  uniformity: elevated={uniformity['elevated_count']} "
              f"({uniformity['elevated_types']}), "
              f"depressed={uniformity['depressed_count']} "
              f"({uniformity['depressed_types']})")
    print("  -> previously `1 if zone == 'bull' else 0` gave 0 ones and 18 zeros, "
          "and the test\n     answered a question about a series that does not vary.")


def measure_hypothesis(data: pd.DataFrame) -> None:
    """The two vocabulary-bound tests, on a vocabulary that is not bull/bear.

    Before the fix, on this input:

        bull_bear_asymmetry : Insufficient data: need both bull and bear zones
        correlation_drawdown: Insufficient data ... (need at least 10 zones, got 0)

    Both messages blamed the data. There were 18 zones; the filters
    ``zone_type == 'bull'`` and ``== 'bear'`` simply matched none of them.
    """
    from bquant.analysis.statistical.hypothesis_testing import HypothesisTestSuite
    from bquant.analysis.zones.detection import resolve_vocabulary
    from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

    result = _zones_with_analysis(data, ["overbought", "neutral", "oversold"])
    vocabulary = resolve_vocabulary(result.zones)
    analyzer = ZoneFeaturesAnalyzer()
    features = [
        analyzer.extract_zone_features(zone.to_analyzer_format()).to_dict()
        for zone in result.zones
    ]

    suite = HypothesisTestSuite()
    print("\nhypothesis tests bound to the vocabulary:")
    for label, call in (
        ("contrast_asymmetry",
         lambda: suite.test_contrast_asymmetry_hypothesis(features, vocabulary=vocabulary)),
        ("correlation_drawdown",
         lambda: suite.test_correlation_drawdown_hypothesis(features, vocabulary=vocabulary)),
    ):
        try:
            outcome = call()
            print(f"  {label:22s} -> ran: {outcome.hypothesis}")
            if label == "contrast_asymmetry":
                print(f"  {'':22s}    pair tested: {outcome.metadata['pair_tested']}, "
                      f"p={outcome.p_value:.5f}")
            else:
                print(f"  {'':22s}    zones used: "
                      f"{outcome.metadata['zones_used_by_type']}")
        except Exception as exc:
            print(f"  {label:22s} -> {type(exc).__name__}: {exc}")

    print("\n  without a declared vocabulary the same calls decline explicitly:")
    for label, call in (
        ("contrast_asymmetry", lambda: suite.test_contrast_asymmetry_hypothesis(features)),
        ("correlation_drawdown", lambda: suite.test_correlation_drawdown_hypothesis(features)),
    ):
        try:
            call()
            print(f"    {label}: ran (unexpected)")
        except Exception as exc:
            print(f"    {label}: {exc}")
    print("  -> the message names the missing declaration, not a shortage of data.")


def measure_pipeline_surface(data: pd.DataFrame) -> None:
    """What the caller sees, and what the summary now admits."""
    result = _zones_with_analysis(data, ["overbought", "neutral", "oversold"])
    sequence = result.sequence_analysis
    summary = result.hypothesis_tests.results["summary"]

    print("\nwhat the pipeline hands back:")
    print(f"  sequence_summary: adjacency_verified="
          f"{sequence['sequence_summary']['adjacency_verified']}, "
          f"segments={sequence['sequence_summary']['contiguous_segments']}, "
          f"discarded={sequence['sequence_summary']['discarded_transitions']}, "
          f"bars_missing={sequence['sequence_summary']['bars_missing']}")
    print(f"  hypothesis summary: executed={summary['tests_executed']}/"
          f"{summary['total_tests']}, failed={summary['tests_failed']}, "
          f"significance_rate={summary['significance_rate']:.3f}")
    if summary["failed_tests"]:
        for name, message in summary["failed_tests"].items():
            print(f"      {name}: {message}")
    print("  -> the rate is computed over the tests that ran. Previously every test "
          "that raised\n     was still counted in the denominator, diluting the rate "
          "and saying nothing about\n     the gap.")


def main() -> None:
    data = _with_rsi(get_sample_data(DATASET))
    result = _zones(data)
    print(f"dataset: {DATASET}; threshold detection found {len(result.zones)} zones\n")

    measure_declared_vocabulary()
    measure_feature_extraction(result)
    measure_markov(data)
    measure_randomness(data)
    measure_hypothesis(data)
    measure_pipeline_surface(data)


if __name__ == "__main__":
    main()
