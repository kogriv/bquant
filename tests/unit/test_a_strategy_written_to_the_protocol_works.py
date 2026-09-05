"""Стратегия, написанная по объявленному протоколу, обязана работать (G68).

Найдено волной 5 прохода по докам, под `docs/api/extension_guide.md`: страница учила
писать стратегии по протоколам из `strategies/base.py`, а протоколы объявляли не те
сигнатуры, что зовёт `ZoneFeaturesAnalyzer`:

* `ShapeCalculationStrategy.calculate_shape(zone_data)` — анализатор зовёт
  `calculate(zone_data, indicator_col=...)`;
* `DivergenceCalculationStrategy.calculate_divergence(zone_data)` — зовётся с
  `indicator_col` и `indicator_line_col`;
* `VolumeCalculationStrategy` объявлял `calculate_volatility` — копия соседнего протокола;
* свинговая стратегия с `calculate_global`, но без `aggregate_for_zone`, проходила
  проверку пайплайна и в `global`-режиме давала 0 зон со свингами: ошибка ловилась
  внутри анализатора и превращалась в `swing_metrics = None`.

Замер: стратегия формы, написанная ровно по протоколу, получала `shape_metrics: None`;
свинговая без `aggregate_for_zone` — `zones_with_swings: 0` из 77 и 77 предупреждений.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones import ZoneFeaturesAnalyzer, analyze_zones
from bquant.core.exceptions import AnalysisError
from bquant.analysis.zones.models import SwingContext, SwingPoint
from bquant.analysis.zones.strategies.base import (
    DivergenceMetrics,
    ShapeMetrics,
    SwingMetrics,
    VolumeCalculationStrategy,
)
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def zone():
    data = get_sample_data("tv_xauusd_1h")
    result = (analyze_zones(data)
              .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
              .detect_zones("zero_crossing", indicator_role="hist")
              .with_cache(enable=False).analyze(clustering=False).build())
    z = result.zones[3]
    return {"zone_id": z.zone_id, "type": z.type, "duration": z.duration,
            "data": z.data, "indicator_context": z.indicator_context}


class ProtocolShape:
    def calculate(self, zone_data, indicator_col):
        return ShapeMetrics(hist_skewness=0.5, hist_kurtosis=0.0, hist_smoothness=0.2,
                            strategy_name="proto_shape", strategy_params={"indicator_col": indicator_col})

    def get_metadata(self):
        return {"strategy": "proto_shape"}


class ProtocolDivergence:
    def calculate_divergence(self, zone_data, indicator_col, indicator_line_col=None):
        return DivergenceMetrics(divergence_type="none", divergence_count=0, divergence_strength=0.0,
                                 divergence_direction="none", strategy_name="proto_div",
                                 strategy_params={"indicator_col": indicator_col})

    def get_metadata(self):
        return {"strategy": "proto_div"}


def test_shape_and_divergence_strategies_written_to_the_protocol_are_used(zone):
    analyzer = ZoneFeaturesAnalyzer(shape_strategy=ProtocolShape(), divergence_strategy=ProtocolDivergence())
    features = analyzer.extract_zone_features(zone)

    assert features.metadata["shape_metrics"]["strategy_name"] == "proto_shape"
    assert features.metadata["shape_metrics"]["strategy_params"]["indicator_col"] == "macd_12_26_9__hist"
    assert features.metadata["divergence_metrics"]["strategy_name"] == "proto_div"


def test_the_volume_protocol_names_the_method_the_analyzer_calls():
    assert "calculate_volume" in VolumeCalculationStrategy.__protocol_attrs__
    assert "calculate_volatility" not in VolumeCalculationStrategy.__protocol_attrs__


def test_a_strategy_missing_a_method_is_refused_at_construction():
    class OldProtocolShape:  # what the Protocol used to declare
        def calculate_shape(self, zone_data):
            return None

        def get_metadata(self):
            return {}

    with pytest.raises(TypeError, match="shape strategy OldProtocolShape lacks \\['calculate'\\]"):
        ZoneFeaturesAnalyzer(shape_strategy=OldProtocolShape())


def test_a_wrong_signature_is_an_error_not_a_none(zone):
    """The method exists, so construction passes; the call fails — and that
    failure must surface, not turn into `shape_metrics = None`."""

    class WrongSignatureShape:
        def calculate(self, zone_data):  # no indicator_col
            return None

        def get_metadata(self):
            return {}

    analyzer = ZoneFeaturesAnalyzer(shape_strategy=WrongSignatureShape())
    # The outer handler of extract_zone_features wraps it as AnalysisError, and
    # the cause is in the message; until G68 it was swallowed and became None.
    with pytest.raises(AnalysisError, match="indicator_col"):
        analyzer.extract_zone_features(zone)


class HalfGlobalSwing:
    """calculate_global without aggregate_for_zone — used to yield 0 swings silently."""

    def calculate(self, zone_data):
        return SwingMetrics.empty("half") if hasattr(SwingMetrics, "empty") else _empty("half")

    def calculate_global(self, full_data):
        return SwingContext(swing_points=[], indices=np.array([], dtype=int),
                            full_data_length=len(full_data), strategy_name="half", strategy_params={})

    def get_metadata(self):
        return {"strategy": "half"}


def _empty(name):
    zeros = dict.fromkeys(
        ("avg_rally_pct", "avg_drop_pct", "max_rally_pct", "max_drop_pct", "min_rally_pct", "min_drop_pct",
         "rally_amplitude_std", "drop_amplitude_std", "rally_amplitude_median", "drop_amplitude_median",
         "avg_rally_duration_bars", "avg_drop_duration_bars", "avg_rally_speed_pct_per_bar",
         "avg_drop_speed_pct_per_bar", "max_rally_speed_pct_per_bar", "max_drop_speed_pct_per_bar"), 0.0)
    return SwingMetrics(num_swings=0, rally_count=0, drop_count=0, rally_to_drop_ratio=1.0,
                        max_rally_duration_bars=0, max_drop_duration_bars=0, duration_symmetry=1.0,
                        strategy_name=name, strategy_params={}, **zeros)


def test_global_scope_refuses_a_swing_strategy_without_aggregate_for_zone():
    data = get_sample_data("tv_xauusd_1h")
    builder = (analyze_zones(data)
               .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
               .detect_zones("zero_crossing", indicator_role="hist")
               .with_cache(enable=False).analyze(clustering=False))
    with pytest.raises(RuntimeError, match="lacks \\['aggregate_for_zone'\\]"):
        builder.with_strategies(swing=HalfGlobalSwing()).build()
    # In per-zone scope the same strategy is complete and runs.
    result = builder.with_strategies(swing=HalfGlobalSwing()).with_swing_scope("per_zone").build()
    assert result.metadata["swing_coverage"]["zones_with_swings"] == 0
    assert all(z.features["metadata"]["swing_metrics"] is not None for z in result.zones)
