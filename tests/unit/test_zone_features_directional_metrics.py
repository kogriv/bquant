"""Directional zone metrics are computed for every zone (G20, stage 2).

`zone_features` used to gate four metrics behind the zone-type *name*:

    if zone_type == 'bull':
        drawdown_from_peak = ...; peak_time_ratio = ...
    elif zone_type == 'bear':
        rally_from_trough = ...; trough_time_ratio = ...

The branch did not compute the metrics differently — it discarded three of the
four. All four derive from `end_price`, `max_price`, `min_price` and the
positions of the extrema, every one of which is computed unconditionally before
the branch, so all four are defined for any zone whatever it is called.

Two consequences followed. Zones from any other vocabulary (`overbought`,
`regime_a`, …) received none of the four. And the consumer immediately tried to
undo the loss: `hypothesis_testing` took `abs()` of both excursions "for
uniformity", reconstructing the quantity the branch had split.

Which of the four is *interesting* is now the consumer's question, answered from
the declared polarity of the zone type rather than from its name.

Analysis: ``devref/gaps/zone_types/g20_zone_type_vocabulary_2026-08-24.md``
"""

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.data.samples import get_sample_data

DIRECTIONAL_FIELDS = (
    "drawdown_from_peak",
    "rally_from_trough",
    "peak_time_ratio",
    "trough_time_ratio",
)


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _features(result):
    analyzer = ZoneFeaturesAnalyzer()
    return [
        analyzer.extract_zone_features(zone.to_analyzer_format())
        for zone in sorted(result.zones, key=lambda z: z.start_idx)
    ]


@pytest.fixture(scope="module")
def macd_features(data):
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(False)
        .build()
    )
    return _features(result)


@pytest.fixture(scope="module")
def threshold_features(data):
    pytest.importorskip("pandas_ta", reason="pandas-ta not installed")
    import pandas_ta as ta

    frame = data.copy()
    frame["RSI_14"] = ta.rsi(frame["close"], length=14)
    result = (
        analyze_zones(frame)
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
    return _features(result)


# --------------------------------------------------------------------------- #
# 1. Every zone gets every metric, whatever its vocabulary
# --------------------------------------------------------------------------- #
def test_macd_zones_get_all_four_metrics(macd_features):
    assert macd_features, "fixture produced no zones"
    for feature in macd_features:
        for field in DIRECTIONAL_FIELDS:
            assert getattr(feature, field) is not None, (
                f"zone {feature.zone_id} ({feature.zone_type}) is missing {field}"
            )


def test_non_macd_vocabulary_gets_all_four_metrics(threshold_features):
    """The case that was broken: names outside {'bull', 'bear'} got nothing."""
    assert threshold_features, "fixture produced no zones"
    assert {f.zone_type for f in threshold_features} == {"overbought", "oversold"}
    for feature in threshold_features:
        for field in DIRECTIONAL_FIELDS:
            assert getattr(feature, field) is not None, (
                f"zone {feature.zone_id} ({feature.zone_type}) is missing {field}"
            )


# --------------------------------------------------------------------------- #
# 2. The change is strictly additive — bull/bear numbers must not move
# --------------------------------------------------------------------------- #
def test_metrics_match_their_definitions(macd_features):
    """Pins the formulas, so a later refactor cannot quietly redefine them.

    Verified against the pre-change implementation on 2026-08-24: across 72 MACD
    zones, 144 fields went None -> populated and **zero** fields changed value.
    These assertions restate the formulas the old branch used, so that guarantee
    stays checkable without the old code.
    """
    for feature in macd_features:
        meta = feature.metadata
        max_price, min_price = meta["max_price"], meta["min_price"]
        assert feature.drawdown_from_peak == pytest.approx(
            feature.end_price / max_price - 1
        )
        assert feature.rally_from_trough == pytest.approx(
            feature.end_price / min_price - 1
        )


def test_excursion_signs_are_consistent(macd_features, threshold_features):
    """An excursion from the high is never positive, from the low never negative.

    Independent of any vocabulary — which is the point: these are properties of
    the price path, not of what the zone is called.
    """
    for feature in list(macd_features) + list(threshold_features):
        assert feature.drawdown_from_peak <= 0, feature.zone_id
        assert feature.rally_from_trough >= 0, feature.zone_id


def test_time_ratios_are_within_the_zone(macd_features, threshold_features):
    for feature in list(macd_features) + list(threshold_features):
        assert 0.0 <= feature.peak_time_ratio < 1.0, feature.zone_id
        assert 0.0 <= feature.trough_time_ratio < 1.0, feature.zone_id


# --------------------------------------------------------------------------- #
# 3. The name must no longer decide anything here
# --------------------------------------------------------------------------- #
def test_extraction_does_not_dispatch_on_zone_type_name():
    """A pin against the exact recurrence: comparing the type name to a literal.

    Checked on the AST rather than on the text, because the text still mentions
    'bull' and 'bear' — in the comment that explains why the branch was removed,
    and in the docstring describing the input. Prose about the defect is not the
    defect. Comments do not survive parsing, and docstrings are skipped
    explicitly, so what remains is code.
    """
    import ast
    import inspect
    import textwrap

    from bquant.analysis.zones import zone_features

    tree = ast.parse(
        textwrap.dedent(
            inspect.getsource(zone_features.ZoneFeaturesAnalyzer.extract_zone_features)
        )
    )

    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }

    offenders = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and node.value in ("bull", "bear")
        and node not in docstrings
    ]

    assert not offenders, (
        f"the literals {offenders} are back in the code of extract_zone_features; "
        "directional behaviour belongs to the declared polarity of the zone type, "
        "not to its name"
    )


# --------------------------------------------------------------------------- #
# 4. Downstream consequence: the price-return regression was half-blind
# --------------------------------------------------------------------------- #
def test_price_return_regression_sees_both_zone_types(macd_features):
    """`predict_price_return` used to fit on bull zones only, without saying so.

    Its default predictor list includes `drawdown_from_peak`, and it drops rows
    with NaN. While that metric was populated for bull zones alone, every bear
    zone was silently removed from the sample: measured on 2026-08-24, the model
    fitted **33 of 72 zones** and reported an R^2 of 0.863 for what was presented
    as a fit over the zone set. With all four metrics computed for every zone it
    fits 66 of 72, and R^2 falls to 0.699 — the earlier figure was flattering
    because it described half the data.

    The pin is the sample, not the R^2: a fit must not silently exclude a whole
    zone type.
    """
    pytest.importorskip("statsmodels", reason="statsmodels not installed")

    from bquant.analysis.statistical.regression import ZoneRegressionAnalyzer

    features = [f.to_dict() for f in macd_features]
    types = {f["zone_type"] for f in features}
    assert len(types) > 1, "fixture must contain more than one zone type"

    result = ZoneRegressionAnalyzer().predict_price_return(features)

    # Every zone carries the directional predictors now, so the only rows the
    # model may drop are those missing an unrelated predictor.
    assert result.n_observations > len(features) * 0.7, (
        f"regression fitted on {result.n_observations} of {len(features)} zones — "
        "a whole zone type is probably being dropped through a NaN predictor again"
    )
