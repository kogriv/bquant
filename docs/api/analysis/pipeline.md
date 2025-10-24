# Universal Zone Analysis Pipeline v2.1

## 📚 Обзор

Universal Zone Analysis Pipeline v2.1 - это современная архитектура для анализа зон любых технических индикаторов. Pipeline использует Fluent Builder Pattern и Two-Layer Architecture для обеспечения максимальной гибкости и универсальности.

## 🏗️ Архитектурные принципы

### Two-Layer Architecture
- **Слой 1:** Zone Detection Strategies (5 типов стратегий)
- **Слой 2:** Universal Zone Analyzer (агностичен к источникам зон)
- **Убрано:** Indicator-specific facades (упрощение с 3 до 2 слоев)

### Fluent Builder Pattern
```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)
```

### True Universality v2.1
- **ZERO hardcoded индикаторов** - работает с любым индикатором
- **indicator_context контракт** - стратегии сами заполняют контекст
- **115 тестов, 100% pass rate** - доказательство универсальности

## 🔧 ZoneAnalysisBuilder - Fluent Interface

### Основные методы

#### `.with_indicator(source, name, **params)`
Настройка индикатора для анализа.

**Поддерживаемые источники:**
- `'preloaded'` - встроенные индикаторы
- `'custom'` - пользовательские индикаторы
- `'pandas_ta'` - библиотека pandas_ta
- `'talib'` - библиотека TA-Lib

**Примеры:**
```python
# MACD
.with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)

# RSI
.with_indicator('pandas_ta', 'rsi', length=14)

# AO (Awesome Oscillator)
.with_indicator('pandas_ta', 'ao', fast=5, slow=34)
```

#### `.detect_zones(strategy, **params)`
Настройка стратегии детекции зон.

**5 Detection Strategies:**
- `'zero_crossing'` - пересечение нулевой линии (MACD, AO)
- `'threshold'` - пороговые значения (RSI, Stochastic)
- `'line_crossing'` - пересечение линий (MA crossovers)
- `'preloaded'` - импорт готовых зон
- `'combined'` - комбинированные правила

**Примеры:**
```python
# Zero crossing для MACD
.detect_zones('zero_crossing', indicator_col='macd_hist')

# Threshold для RSI
.detect_zones('threshold', indicator_col='rsi', 
              upper_threshold=70, lower_threshold=30)

# Line crossing для MA
.detect_zones('line_crossing', line1_col='ma_fast', line2_col='ma_slow')
```

#### `.with_strategies(**strategies)`
Настройка аналитических стратегий.

**Доступные стратегии:**
- `swing` - анализ свингов (find_peaks, pivot_points, zigzag)
- `shape` - анализ формы зон (statistical, geometric)
- `divergence` - детекция дивергенций (classic, hidden)
- `volume` - анализ объемов (standard, correlation)
- `volatility` - анализ волатильности (combined, statistical)

**Примеры:**
```python
# Базовые стратегии
.with_strategies(swing='find_peaks', shape='statistical')

# Расширенные стратегии
.with_strategies(
    swing='zigzag',
    divergence='classic',
    volume='standard',
    volatility='combined'
)
```

#### `.analyze(**options)`
Настройка анализа и обработки.

**Опции:**
- `clustering=True/False` - кластеризация зон
- `n_clusters=3` - количество кластеров
- `hypothesis_tests=True/False` - статистические тесты
- `sequence_analysis=True/False` - анализ последовательностей

**Примеры:**
```python
# Базовый анализ
.analyze(clustering=True, n_clusters=3)

# Полный анализ
.analyze(clustering=True, hypothesis_tests=True, sequence_analysis=True)
```

#### `.with_cache(enable=True, ttl=3600)`
Настройка кэширования для производительности.

**Параметры:**
- `enable=True/False` - включить/выключить кэш
- `ttl=3600` - время жизни кэша в секундах

**Примеры:**
```python
# С кэшированием на 2 часа
.with_cache(enable=True, ttl=7200)

# Без кэширования
.with_cache(enable=False)
```

#### `.build()`
Запуск анализа и получение результата.

**Возвращает:** `ZoneAnalysisResult` объект с результатами анализа.

## 🏭 ZoneAnalysisPipeline - Core Engine

### Configuration-driven подход
Pipeline работает через `ZoneAnalysisConfig` без hardcode, обеспечивая максимальную гибкость.

### Dependency Injection
Все компоненты настраиваются через DI:
- ZoneFeaturesAnalyzer
- HypothesisTestSuite
- ZoneSequenceAnalyzer
- Regression Analyzer
- Validation Suite

### Автоматическая интеграция
```python
# Pipeline автоматически интегрирует все компоненты
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)  # Автоматически включает hypothesis tests
    .build()
)

# Доступ к результатам
print(f"Зон найдено: {len(result.zones)}")
print(f"Статистика: {result.statistics}")
if result.hypothesis_tests:
    print(f"Тесты: {result.hypothesis_tests.results}")
```

## 🎯 UniversalZoneAnalyzer - Agnostic Analyzer

### Zone-agnostic подход
UniversalZoneAnalyzer НЕ ЗНАЕТ откуда зоны (MACD, AO, preloaded, custom) - он работает с любыми зонами универсально.

### Component Integration
Автоматическая интеграция компонентов:
- **ZoneFeaturesAnalyzer** - извлечение характеристик зон
- **HypothesisTestSuite** - статистические тесты
- **ZoneSequenceAnalyzer** - анализ последовательностей
- **Regression Analyzer** - регрессионный анализ (опционально)
- **Validation Suite** - валидация моделей (опционально)

### Strategy Support
Поддержка всех типов стратегий через DI:
- Swing strategies (find_peaks, pivot_points, zigzag)
- Shape strategies (statistical, geometric)
- Divergence strategies (classic, hidden)
- Volume strategies (standard, correlation)
- Volatility strategies (combined, statistical)

## 📊 indicator_context Contract

### True Universality v2.1
Стратегии сами заполняют контекст, обеспечивая ZERO hardcoded индикаторов.

### Standard Fields
```python
indicator_context = {
    'line1_col': 'macd_hist',      # Основная линия индикатора
    'line2_col': 'macd_signal',    # Вторичная линия (если есть)
    'indicator_name': 'macd',      # Имя индикатора
    'source_type': 'custom',       # Тип источника
    'params': {...}                # Параметры индикатора
}
```

### Strategy Usage
```python
def detect_zones(self, data, config):
    context = config.indicator_context
    line1_col = context.get('line1_col')  # Универсальный доступ
    indicator_name = context.get('indicator_name')
    
    # Стратегия работает с любым индикатором
    # без hardcode названий колонок
```

## 🚀 Практические примеры

### Пример 1: MACD Analysis
```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# MACD анализ с полным pipeline
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', divergence='classic')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

# Результаты
print(f"Найдено зон: {len(result.zones)}")
for i, zone in enumerate(result.zones[:3]):
    if zone.features:
        print(f"Зона {i}: {zone.features.get('zone_type', 'unknown')}")
```

### Пример 2: RSI Analysis
```python
# RSI анализ с threshold detection
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

### Пример 3: AO Analysis
```python
# AO (Awesome Oscillator) анализ
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
    .detect_zones('zero_crossing', indicator_col='ao')
    .with_strategies(swing='zigzag', shape='statistical')
    .analyze(clustering=True, hypothesis_tests=True)
    .build()
)
```

### Пример 4: Caching для производительности
```python
# С кэшированием для больших данных
result = (
    analyze_zones(data)
    .with_cache(enable=True, ttl=7200)  # Кэш на 2 часа
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)
```

## 🔄 Migration Guide

### От старого API к новому

**Старый способ (Deprecated):**
```python
from bquant.indicators import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)
zones_dict = analyzer._zone_to_dict(zones[0])  # Deprecated
```

**Новый способ (Universal Pipeline):**
```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# Прямой доступ к features
zone_features = result.zones[0].features.get('zone_type')
```

### Ключевые изменения
- `MACDZoneAnalyzer().analyze_complete()` → `analyze_zones().build()`
- `_zone_to_dict()` → `zone.features.get()`
- Hardcoded индикаторы → Universal API
- 3-слойная архитектура → 2-слойная архитектура

## 🎯 Преимущества Universal Pipeline v2.1

### Упрощение
- **2 слоя вместо 3** - убраны indicator-specific facades
- **Единый API** для всех индикаторов
- **Автоматическая интеграция** компонентов

### Универсальность
- **Работает с ЛЮБЫМ индикатором** из IndicatorFactory
- **ZERO hardcoded** названий колонок
- **115 тестов, 100% pass rate** - доказательство универсальности

### Производительность
- **Автоматическое кэширование** (память + диск)
- **Performance benchmarks** - zones/sec измерения
- **Code simplification** - ~200 lines net reduction

### Расширяемость
- **Strategy Pattern** - легко добавлять новые стратегии
- **Dependency Injection** - настраиваемые компоненты
- **Registry Pattern** - автоматическая регистрация

## 🔗 Связанные разделы

### 📚 Core API
- **[Quick Start](../../user_guide/quick_start.md)** - Быстрый старт с Universal Pipeline
- **[Zone Detection Strategies](strategies.md)** - Детальное описание 5 стратегий
- **[Statistical Analysis](statistical.md)** - Hypothesis tests и статистика
- **[Zone Analysis Models](zones.md)** - ZoneInfo, ZoneAnalysisResult

### 🎯 Learning Path
- **[Examples](../../examples/README.md)** - Готовые примеры использования
- **[Deep Dive Tutorial](../../research/notebooks/03_zones_universal.py)** - Comprehensive analysis
- **[Advanced Features](../../research/notebooks/03_analysis_new_features.py)** - Swing, divergence, regression
- **[Migration Guide](../../examples/02_macd_zone_analysis.py)** - Переход с legacy API

### 🏗️ Developer Resources
- **[Architecture Patterns](../../developer_guide/README.md)** - Design Patterns, Extension Points
- **[Testing Framework](../../tests/integration/)** - Integration tests, Backward compatibility
- **[Visualization](../../api/visualization/README.md)** - Zone visualization, Statistical plots
- **[Indicators](../../api/indicators/README.md)** - IndicatorFactory, Custom indicators

## 💡 Советы по использованию

1. **Начните с простого** - один индикатор, базовая стратегия
2. **Используйте кэширование** - для больших данных и повторных анализов
3. **Экспериментируйте со стратегиями** - разные комбинации дают разные результаты
4. **Изучайте indicator_context** - понимание контракта поможет в расширении
5. **Используйте hypothesis tests** - для статистической валидации результатов

---

**Следующий шаг:** [Zone Detection Strategies](strategies.md) 🎯
