# bquant.indicators.macd — MACD и анализ зон

## Обзор

Современный анализатор зон MACD: расчёт индикаторов, идентификация зон (bull/bear), извлечение признаков, статистика, гипотезы, последовательности, кластеризация.

## Классы

### MACDZoneAnalyzer

**Current Methods:**
- `calculate_macd_with_atr(df) -> DataFrame` - calculate MACD and ATR indicators
- `identify_zones(df) -> List[ZoneInfo]` - identify bull/bear zones
- `analyze_complete(df, perform_clustering=True, n_clusters=3) -> ZoneAnalysisResult` - complete analysis using modular architecture

**Helper Methods:**
- `_zone_to_dict(zone) -> Dict` - convert ZoneInfo to dict for modular analyzers
- `_features_to_dict(features) -> Dict` - convert ZoneFeatures to dict
- `_adapt_statistics_format(stats_data) -> Dict` - adapt statistics format for compatibility

## Migration Notice (Phase 4, v0.X.X)

### Removed Methods

The following methods have been **removed** in Phase 4:

| Method | Removed | Replacement |
|--------|---------|-------------|
| `calculate_zone_features()` | Phase 4 | Use `ZoneFeaturesAnalyzer.extract_zone_features()` |
| `analyze_zones_distribution()` | Phase 4 | Use `ZoneFeaturesAnalyzer.analyze_zones_distribution()` |
| `test_hypotheses()` | Phase 4 | Use `HypothesisTestSuite` from `bquant.analysis.statistical` |
| `analyze_zone_sequences()` | Phase 4 | Use `ZoneSequenceAnalyzer.analyze_zone_transitions()` |
| `cluster_zones_by_shape()` | Phase 4 | Use `ZoneSequenceAnalyzer.cluster_zones()` |

### Why Removed?

These methods duplicated functionality from modular analyzers in `bquant.analysis.*`.
The modular analyzers are:
- More flexible (Strategy Pattern)
- Better tested
- More maintainable
- Extensible

### Recommended Approach

Use `analyze_complete()` which automatically delegates to modular analyzers:

```python
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(df)

# All analysis is performed using modular analyzers:
# - ZoneFeaturesAnalyzer (features)
# - HypothesisTestSuite (statistical tests)
# - ZoneSequenceAnalyzer (sequences, clustering)
```

### For Direct Access to Modular Analyzers

```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer, ZoneSequenceAnalyzer
from bquant.analysis.statistical import HypothesisTestSuite

# Features
features_analyzer = ZoneFeaturesAnalyzer()
features = features_analyzer.extract_zone_features(zone_dict)

# Statistical tests
test_suite = HypothesisTestSuite()
results = test_suite.run_all_tests(zones_features)

# Sequences and clustering
seq_analyzer = ZoneSequenceAnalyzer()
transitions = seq_analyzer.analyze_zone_transitions(zones_features)
clusters = seq_analyzer.cluster_zones(zones_features, n_clusters=3)
```

**See also:**
- [Zone Analysis](../analysis/zones.md) - zone features and strategies
- [Strategies Documentation](../analysis/strategies.md) - Strategy Pattern (stable API)
- [Statistical Analysis](../analysis/statistical.md) - hypothesis tests, regression, validation
- `devref/gaps/phase4_completion_report.md` - technical details

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

### Полный анализ зон MACD

```python
from bquant.indicators.macd import MACDZoneAnalyzer

an = MACDZoneAnalyzer()
res = an.analyze_complete(df)
print(len(res.zones), res.statistics.keys())
```

### Просмотр зон и признаков

```python
for z in res.zones:
    print(z.type, z.start_time, z.end_time, z.duration)
    if z.features:
        print(z.features['macd_amplitude'], z.features['price_return'])
```

### Сценарий с удобной функцией

```python
from bquant.indicators.macd import analyze_macd_zones
res = analyze_macd_zones(df, perform_clustering=False)
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

- [База индикаторов](base.md)
- [PRELOADED индикаторы](preloaded.md)
- [Фабрика и библиотека](factory.md)
