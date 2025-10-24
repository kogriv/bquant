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

### Using Analytical Strategies (v2.1)

🎯 **NEW API:** Configure swing, shape, divergence, volatility, and volume strategies using `.with_strategies()`

**Simple swing analysis:**
```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')  # ✅ NEW!
    .analyze(clustering=True)
    .build()
)

# Access swing metrics
zone = result.zones[0]
print(f"Peaks: {zone.features['num_peaks']}")
print(f"Troughs: {zone.features['num_troughs']}")
print(f"Drawdown: {zone.features['drawdown_from_peak']}")
```

**Multiple strategies:**
```python
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='find_peaks',       # Swing detection
        shape='statistical',      # Shape analysis
        divergence='classic',     # Divergence detection
        volume='standard'         # Volume analysis
    )
    .analyze(clustering=True)
    .build()
)

# All features available in zone.features
zone = result.zones[0]
print(f"Swing: {zone.features.get('num_peaks', 0)} peaks")
print(f"Shape: {zone.features.get('skewness', 0)} skewness")
print(f"Divergence: {zone.features.get('has_classic_divergence', False)}")
print(f"Volume: {zone.features.get('volume_indicator_corr', 0)} correlation")
```

**Available strategies:**
- **swing:** `'find_peaks'`, `'zigzag'`, `'pivot_points'`, or custom instance
- **shape:** `'statistical'` or custom instance (default: 'statistical')
- **divergence:** `'classic'` or custom instance
- **volatility:** custom instance (default: CombinedVolatilityStrategy)
- **volume:** `'standard'` or custom instance

**Works with ANY indicator:**
```python
# RSI with swing analysis
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', period=14)
    .detect_zones('threshold', 
                 indicator_col='RSI_14',
                 upper_threshold=70, 
                 lower_threshold=30)
    .with_strategies(swing='pivot_points')  # ✅ Works!
    .build()
)

# Custom indicator with multiple strategies
df['MY_OSC'] = df['close'].diff(5) / df['close'].rolling(20).std()

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_OSC')
    .with_strategies(
        swing='find_peaks',
        shape='statistical'
    )
    .build()
)
```

**Notes:**
- Features are automatically available in `zone.features` (no manual extraction needed)
- All strategies are optional (default: None = skip)
- Backward compatible with existing code

## Universal Pipeline API (v2.1)

### Основные компоненты

#### `analyze_zones(df) -> ZoneAnalysisBuilder`
Entry point для Universal Pipeline. Возвращает fluent builder для настройки анализа.

#### `ZoneAnalysisBuilder`
Fluent interface для настройки анализа:
- `.with_indicator(source, name, **params)` - настройка индикатора
- `.detect_zones(strategy, **params)` - настройка детекции зон
- `.with_strategies(**strategies)` - настройка аналитических стратегий
- `.analyze(**options)` - настройка анализа
- `.with_cache(enable=True, ttl=3600)` - настройка кэширования
- `.build()` - запуск анализа

#### `ZoneAnalysisResult`
Результат анализа с полным набором данных:
- `zones: List[ZoneInfo]` - найденные зоны
- `statistics: Dict` - статистика анализа
- `hypothesis_tests: Optional[HypothesisTestSuite]` - статистические тесты
- `clustering: Optional[Dict]` - результаты кластеризации
- `sequence_analysis: Optional[Dict]` - анализ последовательностей

#### `ZoneInfo`
Модель зоны с полным контекстом:
- `zone_id: int` - уникальный идентификатор
- `zone_type: str` - тип зоны ('bull'/'bear')
- `start_time: Timestamp` - время начала
- `end_time: Timestamp` - время окончания
- `features: Optional[Dict]` - извлеченные характеристики
- `indicator_context: Dict` - контекст индикатора

### Legacy API (Deprecated)

⚠️ **DEPRECATED:** Следующие компоненты устарели в v2.1:

- `Zone` class → `ZoneInfo` dataclass
- `find_support_resistance()` → Universal detection strategies
- `ZoneAnalyzer` → `UniversalZoneAnalyzer` через pipeline
- `extract_zone_features()` → автоматическое извлечение в pipeline

**Migration Guide:**
```python
# Старый способ (Deprecated)
from bquant.analysis.zones import find_support_resistance, extract_zone_features
zones = find_support_resistance(data, window=20, min_touches=2)
features = extract_zone_features(zone_info)

# Новый способ (Universal Pipeline)
from bquant.analysis.zones import analyze_zones
result = (
    analyze_zones(data)
    .detect_zones('threshold', indicator_col='rsi', upper_threshold=70)
    .analyze(clustering=True)
    .build()
)
zones = result.zones
features = zones[0].features  # Автоматически извлечены
```

## Примеры

### Universal Pipeline Examples

#### MACD Analysis
```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', divergence='classic')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Найдено зон: {len(result.zones)}")
for zone in result.zones[:3]:
    if zone.features:
        print(f"Зона {zone.zone_id}: {zone.features.get('zone_type', 'unknown')}")
```

#### RSI Analysis
```python
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .with_strategies(swing='pivot_points', volatility='combined')
    .analyze(clustering=True)
    .build()
)
```

#### Custom Indicator
```python
# Создаем собственный индикатор
data['MY_OSC'] = data['close'].diff(5) / data['close'].rolling(20).std()

result = (
    analyze_zones(data)
    .detect_zones('zero_crossing', indicator_col='MY_OSC')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True)
    .build()
)
```

### Legacy Examples (Deprecated)

⚠️ **DEPRECATED:** Используйте Universal Pipeline вместо этих примеров:

```python
# Старый способ (Deprecated)
from bquant.analysis.zones import find_support_resistance, ZoneFeaturesAnalyzer

zones = find_support_resistance(data, window=20, min_touches=2)
zfa = ZoneFeaturesAnalyzer()
zone_features = zfa.extract_zone_features({'type':'bull', 'data': zone_df})
```

## См. также

- **[Universal Pipeline](pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zone Detection Strategies](strategies.md)** - Детальное описание 5 стратегий детекции
- **[Statistical Analysis](statistical.md)** - Hypothesis tests и статистический анализ
- **[Examples](../../examples/README.md)** - Готовые примеры использования
- **[Migration Guide](../../examples/02_macd_zone_analysis.py)** - Переход с legacy API
