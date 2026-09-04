"""``per_zone`` and ``global`` are two scopes of one ZigZag, not two ZigZags.

Until G54 ``ZigZagSwingStrategy.calculate()`` built its own pandas-ta ZigZag without
``backtest=True`` — the repainting, centred detector that #110 removed from the
global pass. Measured on the embedded sample, ``narrow_zone`` preset: on 17 of the 18
zones longer than 20 bars the two paths placed their pivots on different bars (same
prices, indices shifted by up to five bars), so durations, speeds and every metric
built on them disagreed between the scopes — and the case study comparing the scopes
was comparing detectors.

The contract now: on the same bars, the per-zone path yields exactly the pivots the
global path yields, and every one of them is replay-safe under truncation of the
zone's own bars, as the global oracle in ``test_swing_replay_causal.py`` requires.
"""

import importlib.util

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.data.samples import get_sample_data

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pandas_ta") is None,
    reason="needs the real pandas-ta detector",
)

STRATEGY = ZigZagSwingStrategy(legs=3, deviation=0.008)   # the narrow_zone preset


@pytest.fixture(scope="module")
def long_zones():
    result = (
        analyze_zones(get_sample_data("tv_xauusd_1h"))
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_strategies(swing="zigzag")
        .with_swing_scope("per_zone")
        .analyze(clustering=False)
        .build()
    )
    zones = [z for z in result.zones if z.duration >= 20]
    assert len(zones) >= 10, "the sample is expected to carry at least ten zones of 20+ bars"
    return zones


def _pivots(context):
    return [(sp.index, sp.swing_type, round(sp.price, 4)) for sp in context.swing_points]


def test_the_per_zone_path_yields_the_global_detectors_pivots(long_zones):
    for zone in long_zones:
        through_global = STRATEGY.calculate_global(zone.data)
        through_per_zone = STRATEGY._swing_context(zone.data, scope="per_zone")
        assert _pivots(through_per_zone) == _pivots(through_global), zone.zone_id


def test_per_zone_metrics_equal_the_global_aggregation_on_the_same_bars(long_zones):
    for zone in long_zones:
        context = STRATEGY.calculate_global(zone.data)
        if len(context.swing_points) < 2:
            continue
        rallies, drops = STRATEGY._build_movements_from_points(context.swing_points)
        expected = STRATEGY._aggregate_metrics(rallies, drops)

        actual = STRATEGY.calculate(zone.data)

        assert actual.num_swings == expected.num_swings
        assert actual.avg_rally_pct == pytest.approx(expected.avg_rally_pct)
        assert actual.avg_drop_duration_bars == pytest.approx(expected.avg_drop_duration_bars)


def test_per_zone_pivots_are_replay_safe_inside_the_zone(long_zones):
    violations = []
    for zone in long_zones:
        full = STRATEGY._swing_context(zone.data, scope="per_zone")
        for sp in full.swing_points:
            ci = sp.confirmation_index
            if ci is None or ci >= len(zone.data):
                continue
            truncated = STRATEGY._swing_context(zone.data.iloc[: ci + 1], scope="per_zone")
            if (sp.index, sp.swing_type, round(sp.price, 4)) not in _pivots(truncated):
                violations.append((zone.zone_id, sp.index, ci))
    assert violations == [], violations
