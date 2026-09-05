# bquant.indicators.macd — removed

> **Removed.** `MACDZoneAnalyzer` and its convenience wrappers (`create_macd_analyzer`,
> `analyze_macd_zones` from `bquant.indicators.macd`) were **removed**
> (deprecated since v2.1). The module `bquant.indicators.macd` no longer exists.

MACD zone analysis is now done with the **Universal Zone Analysis pipeline**, which is
indicator-agnostic. The MACD indicator itself is unchanged and still available via the
indicator factory (`IndicatorFactory` / `with_indicator('custom', 'macd', ...)`).

## Migration

Replace any use of `MACDZoneAnalyzer` with the pipeline:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True)
    .build()
)
print(f"Zones: {len(result.zones)}")
# Zones: 83
```

Or the one-call preset:

```python
from bquant.analysis.zones import analyze_macd_zones
from bquant.data.samples import get_sample_data

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

print(f"Zones: {len(result.zones)}")
# Zones: 32
```

**The two are not the same run.** The preset draws the boundary on the sign of the MACD
*line* (`zone_basis='line'`); the example above uses the histogram, which changes sign
more often. Pass `zone_basis='histogram'` to the preset to reproduce the 83 zones.

## See also

- [Universal Zone Analysis pipeline](../analysis/pipeline.md) — the builder reference.
