# Swing strategy configuration

Swing metrics inside the zone analysis pipeline can now be tuned explicitly
through presets or derived dynamically from the zone price range. This guide
shows how to apply both options when orchestrating a run.

## Applying a preset

`bquant.core.config.SWING_PRESETS` bundles consistent parameter sets for the
ZigZag, Find Peaks, and Pivot Points strategies. Use
`ZoneAnalysisPipeline.with_swing_preset()` (or the builder shortcut) to deploy
one of the presets across all swing components before triggering the analysis.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data("tv_xauusd_1h").set_index("time")

result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_col="macd_hist")
    .with_strategies(swing="zigzag")
    .with_swing_preset("narrow_zone")
    .analyze(clustering=False)
    .build()
)

bull_zones = [zone for zone in result.zones if zone.type == "bull"]
print(bull_zones[0].features["metadata"]["swing_metrics"])  # preset parameters propagate here
```

The example above switches the pipeline to the `narrow_zone` preset, tightening
ZigZag legs/deviation and the complementary thresholds so narrow bands register
swing pivots.

## Enabling adaptive thresholds

When working with instruments that span a wide price range, enable adaptive
thresholds to recompute ZigZag deviation and prominence values on a per-zone
basis. The fluent builder exposes `.with_auto_swing_thresholds(True)` while the
`ZoneAnalysisPipeline` constructor provides the underlying
`strategy_auto_thresholds` flag.

```python
from bquant.analysis.zones.pipeline import ZoneAnalysisConfig, ZoneAnalysisPipeline

pipeline = ZoneAnalysisPipeline(
    config=my_config,
    enable_cache=False,
    strategy_auto_thresholds=True,
    auto_threshold_base_deviation=0.01,
)
pipeline.with_swing_preset("default")  # optional baseline
result = pipeline.run(df)
```

Adaptive mode falls back to the preset parameters whenever the computed range is
smaller than `auto_threshold_base_deviation`, ensuring stability across thin
zones. Combine the toggle with JSON exports from
`research/notebooks/validate_swing_pivots.py` to compare KPI shifts before
rolling the changes into production.
