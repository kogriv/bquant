# bquant.indicators.macd — MACD и анализ зон (Deprecated)

⚠️ **DEPRECATED:** `MACDZoneAnalyzer` устарел в v2.1. Используйте Universal Pipeline.

## Обзор

`MACDZoneAnalyzer` - это тонкий wrapper с @deprecated decorator, который делегирует всю работу в Universal Pipeline. Сохранен для backward compatibility до v3.0.0.

## Классы

### MACDZoneAnalyzer (Deprecated)

⚠️ **DEPRECATED:** Используйте Universal Pipeline вместо этого класса.

**Deprecation Warning:**
```python
@deprecated(
    message="MACDZoneAnalyzer is deprecated. Use universal API instead: "
            "from bquant.analysis.zones import analyze_zones",
    version="2.0.0",
    removal_version="3.0.0"
)
class MACDZoneAnalyzer:
    # Тонкий wrapper с делегированием в Universal Pipeline
```

**Current Methods (Delegation Pattern):**
- `analyze_complete(df, perform_clustering=True, n_clusters=3) -> ZoneAnalysisResult` - делегирует в Universal Pipeline
- `calculate_macd_with_atr(df) -> DataFrame` - calculate MACD and ATR indicators
- `identify_zones(df) -> List[ZoneInfo]` - identify bull/bear zones

**Helper Methods (Internal):**
- `_zone_to_dict(zone) -> Dict` - convert ZoneInfo to dict for modular analyzers
- `_features_to_dict(features) -> Dict` - convert ZoneFeatures to dict
- `_adapt_statistics_format(stats_data) -> Dict` - adapt statistics format for compatibility

## Migration Guide (v2.1)

### От старого API к новому

**Старый способ (Deprecated):**
```python
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(df)
zones_dict = analyzer._zone_to_dict(zones[0])  # Deprecated
```

**Новый способ (Universal Pipeline):**
```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# Прямой доступ к features
zone_features = result.zones[0].features.get('zone_type')
```

### API Evolution

| Старый API | Новый API | Изменения |
|------------|-----------|-----------|
| `MACDZoneAnalyzer().analyze_complete()` | `analyze_zones().build()` | Fluent builder pattern |
| `_zone_to_dict()` | `zone.features.get()` | Прямой доступ к features |
| `extract_zone_features()` | Автоматически в `.analyze()` | Автоматическое извлечение |
| Hardcoded MACD | Universal API | Работает с любым индикатором |

### Backward Compatibility

**Parameter Adaptation:**
- `fast/slow/signal` → `fast_period/slow_period/signal_period`
- Lazy import для избежания circular dependency
- Identical results - результаты идентичны новому API

**Convenience Presets:**
```python
# Shortcut для MACD
from bquant.analysis.zones.presets import analyze_macd_zones
result = analyze_macd_zones(df, fast=12, slow=26, signal=9)
```

---

### MACDPreloadedIndicator
PRELOADED индикатор для работы с готовыми MACD данными.

- `calculate(data) -> IndicatorResult` - извлечение готовых значений
- `is_trending_up(data, column, threshold) -> bool` - анализ восходящего тренда
- `is_trending_down(data, column, threshold) -> bool` - анализ нисходящего тренда
- `get_crossovers(data, column1, column2) -> Dict` - определение пересечений
- `get_statistics(data) -> Dict` - статистика по данным

**Class methods:**
- `get_default_columns() -> List[str]` - колонки по умолчанию
- `get_info() -> Dict[str, Any]` - информация об индикаторе

## Вспомогательные функции

- `create_macd_analyzer(macd_params=None, zone_params=None) -> MACDZoneAnalyzer`
- `analyze_macd_zones(df, macd_params=None, zone_params=None, perform_clustering=True, n_clusters=3) -> ZoneAnalysisResult`

## Примеры

### Universal Pipeline (Рекомендуемый способ)

```python
from bquant.analysis.zones import analyze_zones

# Universal Pipeline - MACD
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', divergence='classic')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Найдено зон: {len(result.zones)}")
print(f"Статистика: {list(result.statistics.keys())}")
```

### Просмотр зон и признаков (Universal Pipeline)

```python
for zone in result.zones:
    print(f"Зона {zone.zone_type}: {zone.start_time} - {zone.end_time}")
    if zone.features:
        print(f"  Swings: {zone.features.get('num_swings', 0)}")
        print(f"  Divergence: {zone.features.get('has_classic_divergence', False)}")
```

### Convenience Preset для MACD

```python
from bquant.analysis.zones.presets import analyze_macd_zones
result = analyze_macd_zones(df, fast=12, slow=26, signal=9)
```

### Legacy API (Deprecated)

⚠️ **DEPRECATED:** Используйте Universal Pipeline вместо этого.

```python
from bquant.indicators.macd import MACDZoneAnalyzer  # ⚠️ Deprecated

analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(df)  # Показывает deprecation warning
```

### PRELOADED MACD индикатор

```python
from bquant.indicators.preloaded import MACDPreloadedIndicator
from bquant.data.samples import get_sample_data

# Загрузка данных с готовыми MACD значениями
data = get_sample_data('tv_xauusd_1h')

# Создание PRELOADED индикатора
macd_indicator = MACDPreloadedIndicator()

# Получение информации о классе
info = MACDPreloadedIndicator.get_info()
print(f"Type: {info['type']}")
print(f"Required fields: {info['required_fields']}")

# Извлечение данных
result = macd_indicator.calculate(data)
print(f"Extracted columns: {list(result.data.columns)}")

# Анализ трендов
trending_up = macd_indicator.is_trending_up(data, column='macd')
trending_down = macd_indicator.is_trending_down(data, column='macd')
print(f"MACD trending up: {trending_up}")
print(f"MACD trending down: {trending_down}")

# Анализ пересечений
crossovers = macd_indicator.get_crossovers(data)
print(f"Bullish crossovers: {crossovers['bullish_crossovers']}")
print(f"Bearish crossovers: {crossovers['bearish_crossovers']}")
```

### PRELOADED с кастомными колонками

```python
# Создание индикатора только для MACD линии
macd_only = MACDPreloadedIndicator(required_columns=['macd'])

# Создание индикатора для всех доступных колонок
macd_full = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])

# Валидация данных
try:
    is_valid = macd_full.validate_data(data)
    print("Validation passed")
except ValueError as e:
    print(f"Validation failed: {e}")
```

## Замечания

- Для больших датасетов применяется ускоренная NumPy-реализация MACD (`OptimizedIndicators.macd`).
- ATR и производные индикаторы добавляются через `data.processor.calculate_derived_indicators`.
- PRELOADED индикаторы работают с уже готовыми данными без пересчета.
- PRELOADED индикаторы поддерживают гибкую настройку колонок для извлечения.

## См. также

- **[Universal Pipeline](../analysis/pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zone Analysis](../analysis/zones.md)** - Universal API для анализа зон
- **[Zone Detection Strategies](../analysis/strategies.md)** - Детальное описание стратегий
- **[База индикаторов](base.md)** - Базовые классы индикаторов
- **[PRELOADED индикаторы](preloaded.md)** - Работа с готовыми данными
- **[Universal Indicator Factory](factory.md)** - Фабрика индикаторов
