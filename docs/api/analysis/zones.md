# bquant.analysis.zones — Анализ зон

> **Универсальная Архитектура**
> 
> Анализ зон теперь работает с **ЛЮБЫМ индикатором** без изменений кода!
> 
> **Поддерживаемые индикаторы:**
> - ЛЮБОЙ осциллятор: MACD, RSI, AO, CCI, Stochastic, Williams %R, MFI, CMF, ROC
> - Пользовательские индикаторы из pandas_ta (158 индикаторов)
> - Ваши собственные расчеты
> 
> **Ключевая инновация:** `ZoneInfo.indicator_context` - зоны сами описывают свою стратегию детекции
> 
> **Доказанная универсальность:**
> - ✅ 115 тестов с 10+ реальными индикаторами (MACD, RSI, AO, CCI, Stochastic, Williams, MFI, CMF, ROC, custom)
> - ✅ 100% прохождение тестов
> - ✅ FICTIONAL_INDICATOR_99 тест - работает с индикатором, которого не существует!
> - ✅ НЕТ жестко закодированных имен индикаторов
> 
> **Справочник API:**
> - [Универсальные Стратегии](strategies.md) - аналитические стратегии для ЛЮБОГО индикатора
> - [Руководство по Расширению](../developer_guide/zone_detection_strategies.md) - создание пользовательских стратегий

## Обзор

Инструменты работы с торговыми зонами: поддержка/сопротивление, признаки зон, последовательности и кластеризация.

## Универсальная Архитектура (v2.1)

### Ключевая Концепция: indicator_context

Каждая обнаруженная зона содержит словарь `indicator_context`, который описывает **КАК** зона была обнаружена:

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

**Стандартные поля (заполняются стратегией детекции):**
- `detection_indicator`: Имя основного столбца индикатора (например, 'RSI_14', 'macd_hist')
- `detection_strategy`: Используемая стратегия (например, 'zero_crossing', 'threshold', 'line_crossing')
- `signal_line`: Вторичный индикатор для 2-линейных стратегий (например, 'STOCH_D')
- `detection_rules`: Полный словарь правил для справки

**Удобные методы:**
```python
# Get primary indicator column
indicator = zone.get_primary_indicator_column()  # → 'RSI_14'

# Get signal line (if exists)
signal = zone.get_signal_line_column()  # → 'STOCH_D' or None
```

### Примеры с Разными Индикаторами

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

#### RSI (ограниченный индикатор на основе порогов)
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

#### Stochastic (пересечение 2 линий)
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

#### Пользовательский Индикатор (доказывает универсальность!)
```python
# Create your own indicator
df['MY_CUSTOM_OSC'] = df['close'].diff(5) / df['close'].rolling(20).std()

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_CUSTOM_OSC')
    .analyze()
    .build()
)

# ✅ Работает сразу - НЕТ необходимости в изменениях кода!
# Context: {'detection_indicator': 'MY_CUSTOM_OSC', 'detection_strategy': 'zero_crossing'}
```

#### FICTIONAL_INDICATOR_99 (финальное доказательство)

```python
import numpy as np
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h').copy()

# Индикатор, которого НЕ существует в кодовой базе — создаём синусоиду
df['FICTIONAL_INDICATOR_99'] = np.sin(np.linspace(0, 6 * np.pi, len(df))) * 5

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='FICTIONAL_INDICATOR_99')
    .analyze()
    .build()
)

first_zone = result.zones[0]
print(len(result.zones))  # → 4 зоны
print(first_zone.indicator_context['detection_indicator'])  # → 'FICTIONAL_INDICATOR_99'
```

> ✅ **Если работает с индикатором, которого никогда не было в коде,** то архитектура действительно универсальна.



### Что Нового в v2.1

**Универсальный Анализ Зон:**
- ✨ **5 Стратегий Детекции** - zero_crossing, threshold, line_crossing, preloaded, combined
- ✨ **Работает с ЛЮБЫМ индикатором** - MACD, RSI, Stochastic, AO, CCI, custom, etc.
- ✨ **indicator_context** - зоны сами описывают параметры детекции
- ✨ **Pipeline API** - fluent builder с поддержкой кэширования
- ✨ **Доказанная универсальность** - FICTIONAL_INDICATOR_99 тест проходит

**Аналитические Стратегии (67 метрик всего):**
- ✨ **Паттерн Стратегия** для расширяемых метрик (8 стратегий)
- ✨ **Swing анализ:** 23 метрики через 3 стратегии (ZigZag, FindPeaks, PivotPoints)
- ✨ **Shape анализ:** 3 метрики через StatisticalShapeStrategy (универсальный - любой осциллятор)
- ✨ **Детекция дивергенции:** 4 метрики через ClassicDivergenceStrategy (универсальный)
- ✨ **Оценка волатильности:** 10 метрик через CombinedVolatilityStrategy
- ✨ **Volume анализ:** 4 метрики через StandardVolumeStrategy (универсальная корреляция)
- ✨ **Временные метрики:** 2 метрики (peak_time_ratio, trough_time_ratio)

**Документация:**
- **Универсальная Архитектура:** См. выше (🟢 v2.1 - стабильно)
- **Паттерн Стратегия:** См. [strategies.md](strategies.md) (🟢 стабильный API)
- **Руководство по Расширению:** См. [developer guide](../developer_guide/zone_detection_strategies.md) (пользовательские стратегии)

### Использование Аналитических Стратегий (v2.1)

🎯 **НОВЫЙ API:** Настройка swing, shape, divergence, volatility и volume стратегий с помощью `.with_strategies()`

**Простой swing анализ:**
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

**Множественные стратегии:**
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

**Доступные стратегии:**
- **swing:** `'find_peaks'`, `'zigzag'`, `'pivot_points'`, или пользовательский экземпляр
- **shape:** `'statistical'` или пользовательский экземпляр (по умолчанию: 'statistical')
- **divergence:** `'classic'` или пользовательский экземпляр
- **volatility:** пользовательский экземпляр (по умолчанию: CombinedVolatilityStrategy)
- **volume:** `'standard'` или пользовательский экземпляр

**Работает с ЛЮБЫМ индикатором:**
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

**Примечания:**
- Характеристики автоматически доступны в `zone.features` (не требуется ручное извлечение)
- Все стратегии опциональны (по умолчанию: None = пропустить)
- Обратно совместимо с существующим кодом

## Universal Pipeline API (v2.1)

### Основные компоненты

#### `analyze_zones(df) -> ZoneAnalysisBuilder`
Точка входа для Universal Pipeline. Возвращает fluent builder для настройки анализа.

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
- **`visualize(mode, **kwargs)`** - встроенная визуализация зон

📊 **[Подробнее о визуализации →](../visualization/zones.md)** - режимы overview/detail/comparison/statistics, backend Plotly/Matplotlib

#### `ZoneInfo`
Модель зоны с полным контекстом:
- `zone_id: int` - уникальный идентификатор
- `type: str` - тип зоны ('bull'/'bear')
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

**Руководство по Миграции:**
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

### Примеры Universal Pipeline

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
        print(f"Зона {zone.zone_id}: {zone.type}")
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

#### Пользовательский Индикатор
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

### Legacy Примеры (Deprecated)

⚠️ **DEPRECATED:** Используйте Universal Pipeline вместо этих примеров:

```python
# Старый способ (Deprecated)
import pandas as pd

from bquant.analysis.zones import find_support_resistance

data = pd.DataFrame(
    {
        "open": [100, 101, 102, 103, 102, 101, 100, 99, 100, 101, 102, 101],
        "high": [101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103, 102],
        "low": [99, 100, 101, 102, 101, 100, 99, 98, 99, 100, 101, 100],
        "close": [100, 101, 102, 102, 101, 100, 100, 99, 100, 101, 102, 101],
        "volume": [1000, 1100, 1080, 1150, 1120, 1090, 1110, 1130, 1140, 1125, 1115, 1105],
    },
    index=pd.date_range("2024-01-01", periods=12, freq="H"),
)

zones = find_support_resistance(data, window=3, min_touches=1)

if zones:
    legacy_zone = zones[0]
    duration_hours = legacy_zone.duration.total_seconds() / 3600
    print(
        f"{legacy_zone.zone_type} zone from {legacy_zone.start_time:%Y-%m-%d %H:%M} "
        f"to {legacy_zone.end_time:%Y-%m-%d %H:%M} ({duration_hours:.0f} hours)"
    )
else:
    print("No support/resistance zones detected with the legacy API.")

# ZoneFeaturesAnalyzer можно использовать как и раньше, передавая словарь зоны.
# Пример:
# zfa = ZoneFeaturesAnalyzer()
# features = zfa.extract_zone_features({
#     "zone_id": legacy_zone.zone_id,
#     "type": legacy_zone.zone_type,
#     "data": data.loc[legacy_zone.start_time : legacy_zone.end_time],
#     "indicator_context": {"detection_strategy": "legacy_support_resistance"},
# })
```

## См. также

- **[Universal Pipeline](pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zone Detection Strategies](strategies.md)** - Детальное описание 5 стратегий детекции
- **[Statistical Analysis](statistical.md)** - Тесты гипотез и статистический анализ
- **[Examples](../../examples/README.md)** - Готовые примеры использования
- **[Migration Guide](../../examples/README.md)** - Переход с legacy API
