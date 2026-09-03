"""Tests for adaptive swing threshold utilities and pipeline integration."""

from statistics import mean

import pandas as pd
import pytest

from bquant.analysis.zones.pipeline import (
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.strategies.swing.thresholds import auto_swing_thresholds
from bquant.core.config import SWING_PRESETS
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy


def test_auto_thresholds_scale_with_range() -> None:
    narrow_base = pd.Series([100.0, 100.2, 100.3, 100.4, 100.1])
    narrow_zone = pd.DataFrame(
        {
            "high": narrow_base + 0.1,
            "low": narrow_base - 0.1,
            "close": narrow_base,
        }
    )
    wide_zone = pd.DataFrame(
        {
            "high": narrow_base + 5.0,
            "low": narrow_base - 5.0,
            "close": narrow_base + 2.5,
        }
    )

    narrow_thresholds = auto_swing_thresholds(narrow_zone, base_deviation=0.01)
    wide_thresholds = auto_swing_thresholds(wide_zone, base_deviation=0.01)

    for value in (
        narrow_thresholds.zigzag_deviation,
        wide_thresholds.zigzag_deviation,
    ):
        assert value >= 0.01

    assert wide_thresholds.zigzag_deviation > narrow_thresholds.zigzag_deviation

    # The two amplitude floors this class used to carry were removed in G38: they
    # were computed, they scaled, and they zeroed the strategies they reached. This
    # very test is why that went unnoticed — it asserted that a value scales with the
    # range, which the broken value did impeccably.
    assert not hasattr(narrow_thresholds, "peak_min_amplitude")
    assert not hasattr(narrow_thresholds, "pivot_deviation")


@pytest.mark.slow
def test_pipeline_auto_thresholds_matches_kpi() -> None:
    df = get_sample_data("tv_xauusd_1h").set_index("time")

    config = ZoneAnalysisConfig(
        indicator=IndicatorSpec(
            source="custom",
            name="macd",
            parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            zone_types=["bull"],
            rules={"indicator_role": "hist"},
            strategy_name="zero_crossing",
        ),
        perform_clustering=False,
        n_clusters=3,
        run_regression=False,
        run_validation=False,
    )

    pipeline = ZoneAnalysisPipeline(
        config,
        enable_cache=False,
        strategy_auto_thresholds=True,
    )
    pipeline.with_swing_preset("narrow_zone")
    preset = SWING_PRESETS["narrow_zone"]

    result = pipeline.run(df)
    bull_zones = [zone for zone in result.zones if zone.type == "bull"]
    assert bull_zones, "Expected bull zones when validating swing thresholds"

    swing_counts = [
        zone.features["metadata"]["swing_metrics"]["num_swings"]
        for zone in bull_zones
    ]
    assert mean(swing_counts) > 1.0

    sample_metrics = bull_zones[0].features["metadata"]["swing_metrics"]
    assert sample_metrics["strategy_params"]["legs"] == preset.zigzag["legs"]
    assert sample_metrics["strategy_params"]["deviation"] >= 0.01


# -- units contract (G16) -----------------------------------------------------
# The pre-existing test above only checks that thresholds SCALE with range, which both
# the correct and the broken routing satisfy — it caught nothing. These pin the thing
# that actually went wrong: which knob each relative value is allowed to reach.

def _adaptive(name, params):
    from bquant.analysis.zones.strategies.swing.thresholds import _AdaptiveSwingStrategy
    return _AdaptiveSwingStrategy(name, params, base_deviation=0.01)


def test_adaptive_never_sets_find_peaks_prominence() -> None:
    """SwingThresholds are fractions; `prominence` is an amount of price (G16).

    Assigning one to the other handed scipy a threshold of ~0.019 — under two cents on
    an instrument trading near 3350 — and the prominence filter stopped filtering.
    find_peaks derives its own range-adaptive, warm-up-frozen prominence, so the
    adaptive layer must leave it alone.
    """
    df = get_sample_data("tv_xauusd_1h")
    wrapper = _adaptive("find_peaks", {"distance": 3})
    wrapper.calculate_global(df)

    assert wrapper.base_strategy.prominence is None, (
        "adaptive layer must not overwrite find_peaks' prominence — it is absolute "
        "while SwingThresholds are relative"
    )
    # And since G38 it does not touch `min_amplitude_pct` either: the strategy keeps
    # whatever the preset gave it. Units were never the problem here — the value was.
    untouched = FindPeaksSwingStrategy(distance=3)
    assert wrapper.base_strategy.min_amplitude_pct == pytest.approx(
        untouched.min_amplitude_pct), (
        "adaptive layer must leave find_peaks' amplitude floor at its preset value"
    )


def test_adaptive_relative_values_stay_relative() -> None:
    """Every value the layer writes is a fraction, so all must be far below price scale."""
    df = get_sample_data("tv_xauusd_1h")
    price_scale = float(df["close"].median())

    for name, params, attrs in (
        ("zigzag", {"legs": 3, "deviation": 0.008}, ("deviation",)),
        ("find_peaks", {"distance": 3}, ("min_amplitude_pct",)),
        ("pivot_points", {"left_bars": 3, "right_bars": 3}, ("min_amplitude_pct",)),
    ):
        wrapper = _adaptive(name, params)
        wrapper.calculate_global(df)
        for attr in attrs:
            value = getattr(wrapper.base_strategy, attr)
            assert 0 < value < 1, f"{name}.{attr}={value} is not a fraction"
            assert value < price_scale / 100, (
                f"{name}.{attr} looks like a price, not a fraction")


@pytest.mark.slow
@pytest.mark.parametrize("strategy", ["find_peaks", "pivot_points"])
def test_adaptive_mode_does_not_zero_a_strategy(strategy) -> None:
    """Turning the mode on must not cost a strategy every swing it had (G38).

    For nine months `with_auto_swing_thresholds(True)` reduced `find_peaks` and
    `pivot_points` to zero swings in every zone, and a published report read that as
    a property of the strategies. Nothing failed: zero swings is a valid result, and
    the only test on this layer asserted that thresholds *scale*, which the zeroing
    value did perfectly.

    The guard is coverage, not thresholds: with the layer adapting only ZigZag, these
    two must land exactly where they land with the layer switched off.
    """
    from bquant.analysis.zones import analyze_zones

    df = get_sample_data("tv_xauusd_1h")

    def coverage(auto: bool) -> int:
        builder = (
            analyze_zones(df)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_role="hist")
            .with_strategies(swing=strategy)
            .with_swing_preset("narrow_zone")
            .analyze(clustering=False)
            .with_cache(enable=False)
        )
        if auto:
            builder = builder.with_auto_swing_thresholds(True)
        result = builder.build()
        # Swing metrics live under features['metadata']['swing_metrics'] — reading the
        # top level of `features` returns nothing and yields a clean, wrong zero.
        return sum(
            1
            for zone in result.zones
            if (((zone.features or {}).get("metadata") or {}).get("swing_metrics") or {}).get("num_swings", 0) > 0
        )

    without_auto = coverage(auto=False)
    with_auto = coverage(auto=True)

    assert without_auto > 0, "fixture is not exercising the strategy at all"
    assert with_auto == without_auto, (
        f"{strategy}: adaptive mode changed coverage from {without_auto} zones to "
        f"{with_auto} — this layer must adapt ZigZag's deviation and nothing else"
    )


def test_adaptive_find_peaks_still_filters() -> None:
    """The regression that started G16: adaptive mode must not inflate the swing set.

    With the relative value landing in `prominence` the filter was effectively off and
    adaptive mode returned MORE swings than the plain strategy, which is the opposite of
    what turning on adaptive thresholds is meant to do.
    """
    df = get_sample_data("tv_xauusd_1h")
    plain = FindPeaksSwingStrategy(distance=3)
    adaptive = _adaptive("find_peaks", {"distance": 3})

    n_plain = len(plain.calculate_global(df).swing_points)
    n_adaptive = len(adaptive.calculate_global(df).swing_points)

    assert n_adaptive <= n_plain, (
        f"adaptive mode detected MORE swings ({n_adaptive}) than plain ({n_plain}) — "
        "the prominence filter is not doing its job"
    )
