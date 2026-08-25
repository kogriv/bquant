"""Zone colouring follows declared polarity, not the type name (G20, stage 4).

`visualization/zones.py` held 29 of the 55 consumer-side `bull`/`bear` literals —
the largest single count in the package, and the simplest to fix, because none of
it was logic: it was choosing a colour and a caption.

The defect: the palette was a dict keyed by name with `self.zone_colors['bull']`
as the fallback. A zone of any other type — `overbought`, `regime_a` — was
silently drawn in the bullish colour, so the chart asserted a direction nobody had
declared. The matplotlib paths did the same through
`'lightblue' if zone_type == 'bull' else 'lightpink'`, which additionally made
every non-bull zone look bearish.

Analysis: ``devref/gaps/zone_types/g20_zone_type_vocabulary_2026-08-24.md``
"""

import pytest

from bquant.analysis.zones import ZoneType, ZoneVocabulary, analyze_zones
from bquant.data.samples import get_sample_data
from bquant.visualization.zones import ZoneVisualizer


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def macd_zones(data):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(False)
        .build()
    ).zones


@pytest.fixture(scope="module")
def threshold_zones(data):
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
        .with_cache(False)
        .build()
    ).zones


def _visualizer_for(zones):
    visualizer = ZoneVisualizer()
    visualizer._prepare_zone_data(zones)
    return visualizer


class TestPolarityColouring:
    def test_macd_colours_are_unchanged(self, macd_zones):
        """The fix must not move the colours for the vocabulary that worked."""
        visualizer = _visualizer_for(macd_zones)
        assert visualizer._zone_style("bull")["line"] == "#00ff88"
        assert visualizer._zone_style("bear")["line"] == "#ff4444"

    def test_other_vocabularies_get_their_own_direction(self, threshold_zones):
        """Previously all three would have fallen back to the bullish colour."""
        visualizer = _visualizer_for(threshold_zones)
        elevated = visualizer._zone_style("overbought")["line"]
        depressed = visualizer._zone_style("oversold")["line"]
        neutral = visualizer._zone_style("neutral")["line"]

        assert len({elevated, depressed, neutral}) == 3, (
            f"the three declared polarities collapsed to {elevated}, {depressed}, "
            f"{neutral}"
        )
        assert elevated == "#00ff88"
        assert depressed == "#ff4444"

    def test_undeclared_type_is_not_painted_as_directional(self, threshold_zones):
        """An unknown name must not inherit somebody else's direction."""
        visualizer = _visualizer_for(threshold_zones)
        unknown = visualizer._zone_style("regime_x")["line"]
        assert unknown != visualizer._zone_style("overbought")["line"]
        assert unknown != visualizer._zone_style("oversold")["line"]

    def test_backends_agree_on_direction(self, threshold_zones):
        """Plotly and matplotlib must not disagree about which way a zone points.

        They did: the plotly palette used green/red while the matplotlib paths used
        `lightblue` for bull and `lightpink` for everything else, so the same zone
        read as bullish on one backend and bearish on the other.
        """
        visualizer = _visualizer_for(threshold_zones)
        assert visualizer._zone_color_mpl("overbought") == "lightgreen"
        assert visualizer._zone_color_mpl("oversold") == "lightpink"
        assert visualizer._zone_color_mpl("neutral") == "lightgrey"

    def test_labels_come_from_the_declaration(self, threshold_zones, macd_zones):
        assert _visualizer_for(macd_zones)._zone_label("bull") == "Bullish"
        assert _visualizer_for(threshold_zones)._zone_label("oversold") == "Oversold"

    def test_label_falls_back_to_the_name(self, threshold_zones):
        assert _visualizer_for(threshold_zones)._zone_label("regime_x") == "regime_x"

    def test_named_override_wins_over_polarity(self, macd_zones):
        """The override dict stays a user-facing knob, not a way to guess meaning."""
        visualizer = _visualizer_for(macd_zones)
        visualizer.zone_colors["bull"] = {"fill": "rgba(1,2,3,0.5)", "line": "#010203"}
        assert visualizer._zone_style("bull")["line"] == "#010203"


class TestVocabularyAdoption:
    def test_vocabulary_is_taken_from_the_zones(self, threshold_zones):
        visualizer = _visualizer_for(threshold_zones)
        assert visualizer.vocabulary.names() == ["overbought", "neutral", "oversold"]
        assert visualizer.vocabulary.is_declared

    def test_plain_dicts_without_context_degrade_to_neutral(self):
        """No detection context means no declared direction — so paint none."""
        visualizer = ZoneVisualizer()
        visualizer._prepare_zone_data([
            {"type": "regime_a", "start_time": None, "end_time": None},
            {"type": "regime_b", "start_time": None, "end_time": None},
        ])
        assert visualizer.vocabulary.names() == ["regime_a", "regime_b"]
        assert visualizer.vocabulary.is_declared  # names present, properties absent
        assert visualizer._zone_style("regime_a") == visualizer._zone_style("regime_b")


class TestAggregation:
    def test_swing_metrics_group_by_observed_types(self, threshold_zones):
        """Aggregation used to bucket into 'bull'/'bear' and drop everything else."""
        visualizer = _visualizer_for(threshold_zones)
        zones = visualizer._prepare_zone_data(threshold_zones)
        aggregated = visualizer._aggregate_zone_metrics_mvp(zones)

        assert aggregated is not None, (
            "no metrics aggregated for a threshold vocabulary; the buckets are "
            "probably still keyed by 'bull'/'bear'"
        )
        assert set(aggregated) <= {"overbought", "neutral", "oversold"}
        assert set(aggregated), aggregated

    def test_aggregation_orders_elevated_before_depressed(self, threshold_zones):
        visualizer = _visualizer_for(threshold_zones)
        zones = visualizer._prepare_zone_data(threshold_zones)
        keys = list(visualizer._aggregate_zone_metrics_mvp(zones))
        polarities = [visualizer.vocabulary.polarity_of(k) for k in keys]
        assert polarities == sorted(polarities, key=lambda p: {1: 0, 0: 1, -1: 2}[p])


def test_visualization_holds_no_zone_type_literals():
    """AST pin over both visualization modules."""
    import ast
    import inspect

    from bquant.visualization import charts, zones

    for module in (zones, charts):
        tree = ast.parse(inspect.getsource(module))
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
        assert not offenders, f"{module.__name__}: zone-type literals in code: {offenders}"
