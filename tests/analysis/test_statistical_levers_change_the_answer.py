"""Levers of the statistical path must change the answer they claim to change.

A dead lever in visualization gives a wrong picture; here it gives a **number
presented as a result**. The lever table over `bquant.analysis.statistical`
(§7.3 of the readiness snapshot) found one: `ZoneRegressionAnalyzer(alpha=...)`
was documented as the significance level for the analysis and decided nothing but
whether an INFO line was logged — the verdict it produced was computed and thrown
away, so two analyzers built with different alphas returned identical results.

The second test pins the opposite case, so the limit is on the record rather than
silent: `descriptive_statistics(name=...)` labels a debug line and nothing else.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.statistical import StatisticalAnalyzer
from bquant.analysis.statistical.regression import ZoneRegressionAnalyzer
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def zone_features() -> list[dict]:
    data = get_sample_data("tv_xauusd_1h")
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .analyze()
        .build()
    )
    features = [zone.features for zone in result.zones]
    assert len(features) > 30, "too few zones for a regression to say anything"
    return features


@pytest.mark.parametrize("method", ["explain_zone_duration", "explain_price_return"])
def test_constructor_alpha_reaches_the_result(zone_features, method: str) -> None:
    strict = getattr(ZoneRegressionAnalyzer(alpha=0.001), method)(zone_features).to_dict()
    loose = getattr(ZoneRegressionAnalyzer(alpha=0.5), method)(zone_features).to_dict()

    assert strict["metadata"]["alpha"] == 0.001
    assert loose["metadata"]["alpha"] == 0.5

    strict_names = set(strict["metadata"]["significant_predictors"])
    loose_names = set(loose["metadata"]["significant_predictors"])
    assert strict_names != loose_names, "alpha changed nothing in the reported result"
    assert strict_names < loose_names, "a stricter alpha must not admit more predictors"


def test_the_p_values_themselves_do_not_move_with_alpha(zone_features) -> None:
    """Positive control for the test above: alpha must change the verdict, not the fit.

    Without this, an implementation that refitted the model per alpha would also
    pass — and would be wrong in a way that is much harder to notice.
    """
    strict = ZoneRegressionAnalyzer(alpha=0.001).explain_zone_duration(zone_features).to_dict()
    loose = ZoneRegressionAnalyzer(alpha=0.5).explain_zone_duration(zone_features).to_dict()
    assert strict["p_values"] == loose["p_values"]
    assert strict["r_squared"] == loose["r_squared"]


def test_descriptive_statistics_name_is_a_log_label_only() -> None:
    """Pinned, not fixed: the return type is Dict[str, float] and has no room for it.

    What was wrong was the silence — the docstring said "Название данных" next to a
    result that never carries it. The docstring now says where the name goes; this
    keeps the statement and the behaviour together.
    """
    series = pd.Series(np.random.default_rng(11).normal(size=200))
    analyzer = StatisticalAnalyzer()

    default = analyzer.descriptive_statistics(series)
    named = analyzer.descriptive_statistics(series, name="ATR")

    assert default == named
    assert all(isinstance(value, (int, float)) for value in named.values())
    assert "ATR" not in str(named)
