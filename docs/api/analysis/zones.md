# bquant.analysis.zones — Анализ зон

> **✅ v2.1 - Truly Universal Architecture**
> 
> Zone analysis now works with **ANY indicator** without code changes!
> 
> **Supported indicators:**
> - ANY oscillator: MACD, RSI, AO, CCI, Stochastic, Williams %R, MFI, CMF, ROC
> - Custom indicators from pandas_ta (158 indicators)
> - Your own custom calculations
> 
> **Key innovation:** `ZoneInfo.indicator_context` - zones self-describe their detection strategy
> 
> **Proven universality:**
> - ✅ 115 tests with 10+ real indicators (MACD, RSI, AO, CCI, Stochastic, Williams, MFI, CMF, ROC, custom)
> - ✅ 100% pass rate
> - ✅ FICTIONAL_INDICATOR_99 test - works with indicator that doesn't exist!
> - ✅ NO hardcoded indicator names anywhere
> 
> **API Reference:**
> - [Universal Strategies](strategies.md) - analytical strategies for ANY indicator
> - [Extension Guide](extension_guide.md) - create custom strategies

## Обзор

Инструменты работы с торговыми зонами: поддержка/сопротивление, признаки зон, последовательности и кластеризация.

## Universal Architecture (v2.1)

### Key Concept: indicator_context

Every detected zone contains `indicator_context` dictionary that describes **HOW** the zone was detected:

```python
from bquant.analysis.zones import analyze_zones

result = analyze_zones(df).detect_zones('zero_crossing', indicator_col='RSI_14').build()

# Access zone's detection context
zone = result.zones[0]
context = zone.indicator_context

print(context['detection_indicator'])  # → 'RSI_14'
print(context['detection_strategy'])   # → 'zero_crossing'
print(context['signal_line'])          # → None (single-line indicator)
```

**Standard fields (populated by detection strategy):**
- `detection_indicator`: Primary indicator column name (e.g., 'RSI_14', 'macd_hist')
- `detection_strategy`: Strategy used (e.g., 'zero_crossing', 'threshold', 'line_crossing')
- `signal_line`: Secondary indicator for 2-line strategies (e.g., 'STOCH_D')
- `detection_rules`: Full rules dictionary for reference

**Convenience methods:**
```python
# Get primary indicator column
indicator = zone.get_primary_indicator_column()  # → 'RSI_14'

# Get signal line (if exists)
signal = zone.get_signal_line_column()  # → 'STOCH_D' or None
```

### Examples with Different Indicators

#### MACD (zero-crossing oscillator)
```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'macd_hist', 'detection_strategy': 'zero_crossing'}
```

#### RSI (threshold-based bounded indicator)
```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold',
                 indicator_col='RSI_14',
                 upper_threshold=70,
                 lower_threshold=30)
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'RSI_14', 'detection_strategy': 'threshold'}
```

#### Stochastic (2-line crossing)
```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'stoch', k=14, d=3)
    .detect_zones('line_crossing',
                 line1_col='STOCHk_14_3_3',
                 line2_col='STOCHd_14_3_3')
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'STOCHk_14_3_3', 'signal_line': 'STOCHd_14_3_3'}
```

#### Custom Indicator (proves universality!)
```python
# Create your own indicator
df['MY_CUSTOM_OSC'] = df['close'].diff(5) / df['close'].rolling(20).std()

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_CUSTOM_OSC')
    .analyze()
    .build()
)

# ✅ Works immediately - NO code changes needed!
# Context: {'detection_indicator': 'MY_CUSTOM_OSC', 'detection_strategy': 'zero_crossing'}
```

### Why This Matters

**Before v2.1:** Hardcoded MACD support
- ❌ Only worked with MACD
- ❌ Analytical strategies assumed 'macd_hist' column
- ❌ Required code changes for new indicators

**After v2.1:** True Universality
- ✅ Works with ANY indicator
- ✅ Analytical strategies read from `indicator_context`
- ✅ NO code changes for new indicators
- ✅ Proven with FICTIONAL_INDICATOR_99 (indicator that doesn't exist!)

**Reference:** See `devref/gaps/zo/zouni_v2.md` for complete architecture specification

### What's New in v2.1

**Universal Zone Analysis:**
- ✨ **5 Detection Strategies** - zero_crossing, threshold, line_crossing, preloaded, combined
- ✨ **Works with ANY indicator** - MACD, RSI, Stochastic, AO, CCI, custom, etc.
- ✨ **indicator_context** - zones self-describe detection parameters
- ✨ **Pipeline API** - fluent builder with caching support
- ✨ **Proven universality** - FICTIONAL_INDICATOR_99 test passes

**Analytical Strategies (67 total metrics):**
- ✨ **Strategy Pattern** for extensible metrics (8 strategies)
- ✨ **Swing analysis:** 23 metrics via 3 strategies (ZigZag, FindPeaks, PivotPoints)
- ✨ **Shape analysis:** 3 metrics via StatisticalShapeStrategy (universal - any oscillator)
- ✨ **Divergence detection:** 4 metrics via ClassicDivergenceStrategy (universal)
- ✨ **Volatility assessment:** 10 metrics via CombinedVolatilityStrategy
- ✨ **Volume analysis:** 4 metrics via StandardVolumeStrategy (universal correlation)
- ✨ **Time metrics:** 2 metrics (peak_time_ratio, trough_time_ratio)

**Documentation:**
- **Universal Architecture:** See above (🟢 v2.1 - stable)
- **Strategy Pattern:** See [strategies.md](strategies.md) (🟢 stable API)
- **Extension Guide:** See [extension_guide.md](extension_guide.md) (custom strategies)

## Классы и функции

- Базовые сущности:
  - `Zone`: модель зоны (id, type, times, prices, strength, confidence, metadata)
  - `ZoneAnalyzer`:
    - `identify_support_resistance(data, window=20, min_touches=2) -> List[Zone]`
    - `analyze_zone_breaks(data, zones) -> Dict`
    - `analyze(data, window=20, min_touches=2) -> AnalysisResult`
  - Утилита: `find_support_resistance(data, window=20, min_touches=2) -> List[Zone]`

- Признаки зон (`zone_features`):
  - `ZoneFeatures` — dataclass характеристик
  - `ZoneFeaturesAnalyzer`:
    - `extract_zone_features(zone_info) -> ZoneFeatures`
    - `analyze_zones_distribution(zones_features) -> AnalysisResult`
    - `get_zone_features_summary(zones_features) -> Dict`
  - Утилиты:
    - `analyze_zones_distribution(zones_features, ...) -> Dict`
    - `extract_zone_features(zone_info, ...) -> Dict`

- Последовательности (`sequence_analysis`):
  - `TransitionAnalysis`, `ClusterAnalysis`
  - `ZoneSequenceAnalyzer`:
    - `analyze_zone_transitions(zones_features) -> AnalysisResult`
    - `cluster_zones(zones_features, n_clusters=3, features_to_use=None) -> AnalysisResult`
  - Утилиты:
    - `create_zone_sequence_analysis(zones_features, min_sequence_length=3) -> Dict`
    - `cluster_zone_shapes(zones_features, n_clusters=3) -> Dict`

## Примеры

Поддержка/сопротивление:
```python
from bquant.analysis.zones import find_support_resistance

zones = find_support_resistance(data, window=20, min_touches=2)
print(len(zones))
```

Извлечение признаков:
```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

zfa = ZoneFeaturesAnalyzer()
zone_features = zfa.extract_zone_features({'type':'bull', 'data': zone_df})
print(zone_features.to_dict())
```

Анализ последовательностей:
```python
from bquant.analysis.zones import ZoneSequenceAnalyzer

zsa = ZoneSequenceAnalyzer(min_sequence_length=3)
res = zsa.analyze_zone_transitions(zones_features)
print(res.results['transition_probabilities'])
```

## См. также

- [База анализа](base.md)
- [Статистический анализ](statistical.md)
