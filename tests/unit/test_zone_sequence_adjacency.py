"""Sequence analysis reads what it was given (G20 stage 3 + G21).

Two defects are closed here, and they share a shape: the layer assumed things
instead of reading them.

**G20 — the vocabulary.** `_markov_chain_analysis` hardcoded
``states = ['bull', 'bear']`` with a fixed 2x2 matrix. On any other vocabulary no
transition landed in the matrix and the function returned all zeros *as a
success* — together with ``states: ['bull','bear']`` and a stationary
distribution of ``[1.0, 0.0]``, a confident claim about a state that never
occurred. The neighbouring `_calculate_transitions` counted the same data
correctly without knowing any names.

**G21 — adjacency.** Detectors tile the timeline, and the layer reads consecutive
list entries as transitions. `min_duration` (default 2) drops short zones, so the
neighbours of a dropped one stop being adjacent — but the list of type labels
cannot say so: `start_idx`/`end_idx` appeared **zero** times in the module.
Measured on the bundled sample, 8 of 71 MACD "transitions" spanned a gap,
including 7 structurally impossible ``bull -> bull`` pairs (a zero-crossing
detector must alternate).

Analysis: ``devref/gaps/zone_types/`` and ``devref/gaps/sequence/``
"""

import pytest

from bquant.analysis.zones import ZoneType, ZoneVocabulary, analyze_zones
from bquant.analysis.zones.sequence_analysis import ZoneSequenceAnalyzer
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _macd(data, min_duration=1):
    # Порог живёт на стадии анализа: детекция возвращает полное мощение (G21 (c)).
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .analyze(clustering=False, min_duration=min_duration)
        .with_cache(False)
        .build()
    )


@pytest.fixture(scope="module")
def macd_result(data):
    return _macd(data)


@pytest.fixture(scope="module")
def threshold_result(data):
    pytest.importorskip("pandas_ta", reason="pandas-ta not installed")
    import pandas_ta as ta

    frame = data.copy()
    frame["RSI_14"] = ta.rsi(frame["close"], length=14)
    return (
        analyze_zones(frame)
        .detect_zones(
            "threshold",
            indicator_col="RSI_14",
            zone_types=["overbought", "neutral", "oversold"],
            upper_threshold=70,
            lower_threshold=30,
        )
        .analyze(clustering=False)
        .with_cache(False)
        .build()
    )


# --------------------------------------------------------------------------- #
# 1. Segmentation
# --------------------------------------------------------------------------- #
class TestSegmentation:
    @staticmethod
    def _frame(bounds):
        import pandas as pd

        return pd.DataFrame({
            "zone_type": ["a"] * len(bounds),
            "start_idx": [b[0] for b in bounds],
            "end_idx": [b[1] for b in bounds],
        })

    def test_touching_zones_form_one_segment(self):
        frame = self._frame([(0, 2), (3, 5), (6, 9)])
        assert ZoneSequenceAnalyzer._contiguous_segments(frame) == [[0, 1, 2]]

    def test_a_gap_splits_the_segment(self):
        frame = self._frame([(0, 2), (3, 5), (10, 12)])
        assert ZoneSequenceAnalyzer._contiguous_segments(frame) == [[0, 1], [2]]

    def test_missing_boundaries_degrade_to_one_segment_and_say_so(self):
        """Old saved features have no boundaries; behave as before but flag it."""
        import pandas as pd

        frame = pd.DataFrame({"zone_type": ["a", "b", "c"]})
        segments = ZoneSequenceAnalyzer._contiguous_segments(frame)
        assert segments == [[0, 1, 2]]
        summary = ZoneSequenceAnalyzer._adjacency_summary(frame, segments)
        assert summary["adjacency_verified"] is False
        assert summary["discarded_transitions"] == 0

    def test_summary_accounts_for_every_pair(self):
        frame = self._frame([(0, 2), (3, 5), (10, 12), (13, 15)])
        segments = ZoneSequenceAnalyzer._contiguous_segments(frame)
        summary = ZoneSequenceAnalyzer._adjacency_summary(frame, segments)
        assert summary["adjacent_transitions"] + summary["discarded_transitions"] == 3
        assert summary["bars_missing"] == 4  # bars 6..9
        assert summary["gap_sizes"] == [4]


# --------------------------------------------------------------------------- #
# 2. G21 — no transition is reported across a gap
# --------------------------------------------------------------------------- #
class TestAdjacency:
    def test_zero_crossing_never_reports_a_self_transition(self, macd_result):
        """The sharpest invariant: this detector alternates by construction.

        A zone ends where the indicator crosses zero, so the next zone must be of
        the other type. `bull -> bull` is not rare, it is impossible — and 7 of
        them were being reported at the default min_duration.
        """
        transitions = macd_result.sequence_analysis["transitions"]
        self_loops = {
            name: count for name, count in transitions.items()
            if name.split("_to_")[0] == name.split("_to_")[1]
        }
        assert not self_loops, (
            f"zero_crossing reported transitions into the same type: {self_loops}; "
            "these can only come from counting across a discarded zone"
        )

    @pytest.mark.parametrize("min_duration", [1, 2, 3, 5])
    def test_alternation_holds_at_every_min_duration(self, data, min_duration):
        result = _macd(data, min_duration=min_duration)
        matrix = result.sequence_analysis["markov_analysis"]["transition_matrix"]
        diagonal = [matrix[i][i] for i in range(len(matrix))]
        assert not any(diagonal), (
            f"min_duration={min_duration}: the Markov diagonal is {diagonal}, so "
            "zones of the same type are being treated as consecutive"
        )

    def test_nothing_is_discarded_at_the_default(self, macd_result):
        """At the default the zones tile the indicator exactly — no gaps at all.

        This is what G21 variant (c) bought: the threshold left detection, so
        there is nothing to bridge. It is also the stronger statement, because
        the adjacency machinery is what proves it rather than assumes it.
        """
        summary = macd_result.sequence_analysis["sequence_summary"]
        assert summary["adjacency_verified"] is True
        assert summary["discarded_transitions"] == 0
        assert summary["bars_missing"] == 0
        assert summary["total_transitions"] == summary["total_zones"] - 1

    def test_a_requested_filter_is_reported_not_hidden(self, data):
        """Ask for the filter and the gaps it makes are counted, not bridged."""
        result = _macd(data, min_duration=2)
        summary = result.sequence_analysis["sequence_summary"]

        assert summary["adjacency_verified"] is True
        assert summary["total_transitions"] + summary["discarded_transitions"] == (
            summary["total_zones"] - 1
        )
        assert summary["discarded_transitions"] > 0, (
            "min_duration=2 drops zones on the bundled sample; if this is zero "
            "the adjacency check is not running"
        )

        # И то же самое — в метаданных результата, а не только в сводке.
        excluded = result.metadata["duration_filter"]
        assert excluded["min_duration"] == 2
        assert excluded["zones_excluded"] > 0
        assert excluded["zones_analysed"] == summary["total_zones"]
        # Исключённые зоны никуда не делись: они остаются в result.zones.
        assert len(result.zones) == (
            excluded["zones_analysed"] + excluded["zones_excluded"]
        )

    def test_markov_counts_match_the_transition_counter(self, macd_result):
        """The generic counter and the Markov path must agree.

        They disagreed before: one counted correctly, the other returned zeros.
        """
        sequence = macd_result.sequence_analysis
        assert sequence["markov_analysis"]["observed_transitions"] == sum(
            sequence["transitions"].values()
        )


# --------------------------------------------------------------------------- #
# 3. G20 — states and direction come from the data and the declaration
# --------------------------------------------------------------------------- #
class TestVocabularyDriven:
    def test_states_are_the_observed_types_not_two_literals(self, threshold_result):
        markov = threshold_result.sequence_analysis["markov_analysis"]
        assert markov["states"] == ["neutral", "overbought", "oversold"]
        assert len(markov["transition_matrix"]) == 3
        assert markov["observed_transitions"] > 0, (
            "a three-type vocabulary used to yield an all-zero 2x2 matrix"
        )

    def test_stationary_distribution_describes_observed_states(self, threshold_result):
        markov = threshold_result.sequence_analysis["markov_analysis"]
        distribution = markov["stationary_distribution"]
        assert len(distribution) == len(markov["states"])
        assert sum(distribution) == pytest.approx(1.0)
        # Previously [1.0, 0.0] over states that never occurred.
        assert all(value > 0 for value in distribution), (
            f"a state with zero stationary mass among {markov['states']} suggests "
            "the matrix is not being filled from the observed sequence"
        )

    def test_runs_test_binarises_by_declared_polarity(self, threshold_result):
        runs = threshold_result.sequence_analysis["randomness_tests"]["runs_test"]
        assert "not_applicable" not in runs, runs
        assert runs["basis"]["binarised_by"] == "declared polarity (+1 vs -1)"

    def test_undeclared_polarity_declines_instead_of_degenerating(self):
        """Without declared polarity the test must say so, not return a constant.

        The old code binarised `== 'bull'`, so an unrecognised vocabulary produced
        an all-zero series and a test about a variable that does not vary.
        """
        analyzer = ZoneSequenceAnalyzer()
        vocabulary = ZoneVocabulary.coerce(["regime_a", "regime_b"])
        sequence = ["regime_a", "regime_b", "regime_a", "regime_b"]
        result = analyzer._test_sequence_randomness(
            sequence, [[0, 1, 2, 3]], vocabulary
        )
        assert "not_applicable" in result["runs_test"]
        assert "polarity" in result["runs_test"]["not_applicable"]

    def test_declared_polarity_on_a_custom_vocabulary_works(self):
        """Any vocabulary works once its properties are declared."""
        analyzer = ZoneSequenceAnalyzer()
        vocabulary = ZoneVocabulary.coerce([
            ZoneType("regime_a", polarity=+1, counterpart="regime_b"),
            ZoneType("regime_b", polarity=-1, counterpart="regime_a"),
        ])
        sequence = ["regime_a", "regime_b"] * 6
        result = analyzer._test_sequence_randomness(
            sequence, [list(range(len(sequence)))], vocabulary
        )
        assert "not_applicable" not in result["runs_test"]
        assert result["uniformity_test"]["elevated_types"] == ["regime_a"]

    def test_sequence_layer_holds_no_zone_type_literals(self):
        """AST pin: the two names must not come back as code.

        Checked on the parse tree, not the text: the module still mentions them in
        the comments explaining what was removed.
        """
        import ast
        import inspect

        from bquant.analysis.zones import sequence_analysis

        tree = ast.parse(inspect.getsource(sequence_analysis))
        docstrings = {
            node.body[0].value
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Module))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        offenders = [
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and node.value in ("bull", "bear")
            and node not in docstrings
        ]
        assert not offenders, f"zone-type literals back in the code: {offenders}"


# --------------------------------------------------------------------------- #
# 4. Hypothesis summary tells the truth about what ran
# --------------------------------------------------------------------------- #
class TestHypothesisSummary:
    @pytest.mark.parametrize("fixture", ["macd_result", "threshold_result"])
    def test_every_test_runs_on_both_vocabularies(self, fixture, request):
        """Two of seven used to fail on MACD and on any threshold vocabulary."""
        result = request.getfixturevalue(fixture)
        summary = result.hypothesis_tests.results["summary"]
        assert summary["tests_failed"] == 0, summary["failed_tests"]
        assert summary["tests_executed"] == summary["total_tests"]

    def test_significance_rate_counts_only_executed_tests(self, macd_result):
        """A test that did not run is not an insignificant result.

        It used to land in the denominator all the same, diluting the rate while
        saying nothing about the gap.
        """
        summary = macd_result.hypothesis_tests.results["summary"]
        expected = summary["significant_tests"] / summary["tests_executed"]
        assert summary["significance_rate"] == pytest.approx(expected)

    def test_contrast_pair_is_named_in_the_result(self, threshold_result):
        asymmetry = threshold_result.hypothesis_tests.results["tests"]["contrast_asymmetry"]
        assert asymmetry["metadata"]["pair_tested"] == ["overbought", "oversold"]
