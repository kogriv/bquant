# bquant.analysis.zones — Анализ зон

> 💡 **Хотите понять, как это работает?**
>
> Этот документ — технический справочник по API. Для глубокого концептуального разбора внутренней логики пайплайна, читайте наше руководство **[Глубокое погружение: Пайплайн анализатора зон](../../developer_guide/zone_analyzer_deep_dive.md)**.

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
> - [Руководство по Расширению](../../developer_guide/zone_detection_strategies.md) - создание пользовательских стратегий
> - [Модели глобальных свингов](zones/global_swings_models.md) — `SwingPoint`, `SwingContext`, `ZoneInfo.get_zone_swings()`
> - [Пайплайн с поддержкой global scope](zones/global_swings_pipeline.md) — `_calculate_global_swings`, `_inject_swing_context`
> - [Стратегии свингов v2](zones/global_swings_strategies.md) — протокол `SwingCalculationStrategy` и ZigZag/FindPeaks/PivotPoints

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
- **Руководство по Расширению:** См. [developer guide](../../developer_guide/zone_detection_strategies.md) (пользовательские стратегии)

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

> 📖 **Полный справочник по методам билдера** (`.with_indicator()`, `.detect_zones()`,
> `.with_strategies()`, `.analyze()`, `.with_cache()`, `.with_swing_scope()`, `.build()`) —
> в канонической странице [Universal Pipeline](pipeline.md). Ниже — только модели данных
> результата.

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
- `type: str` - метка типа зоны (`'bull'`, `'overbought'`, `'regime_a'` — открытый словарь; смысл метки объявляет стратегия, см. `ZoneType` ниже)
- `start_time: Timestamp` - время начала
- `end_time: Timestamp` - время окончания
- `features: Optional[Dict]` - извлеченные характеристики
- `indicator_context: Dict` - контекст индикатора

#### `zone_types=None` означает «не фильтровать»

Параметр `zone_types` в `detect_zones(...)` сужает результат до перечисленных типов.
**Если его не передать, фильтра нет** — стратегия отдаёт все типы, которые нашла:

```python
# Все три полосы осциллятора: overbought, neutral, oversold
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14',
                  upper_threshold=70, lower_threshold=30)
    .build()
)

# Только сигнальные зоны
signal_only = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14',
                  zone_types=['overbought', 'oversold'],
                  upper_threshold=70, lower_threshold=30)
    .build()
)
```

На встроенном сэмпле: 44 зоны без фильтра, 18 с ним.

> **Изменение поведения (2026-08-24).** Раньше не переданный `zone_types` молча
> подменялся на `['bull', 'bear']` — словарь MACD-подобных детекторов. Каждый детектор
> фильтрует свой вывод через этот список, поэтому `threshold` и `combined` возвращали
> **пустой успешный результат**: зоны находились и тут же отбрасывались, а лог сообщал
> «Detected 0 zones», неотличимо от «порогам нечего было ловить».
>
> **Нейтральная полоса входит в набор по умолчанию, и это важно для анализа
> последовательностей.** Без неё зоны покрывают лишь 11% таймлайна и **ни одна пара
> соседних зон не примыкает**, поэтому переход `overbought → oversold` означал бы
> «перекупленность, потом неизвестно сколько ничего, потом перепроданность». С
> нейтральными пороговый детектор мостит таймлайн так же, как MACD (97.9% против 98.9%),
> и его последовательности сопоставимы с MACD-овскими.

#### Анализ последовательностей: примыкание и состояния

`result.sequence_analysis` строится **только по примыкающим зонам**. Детекторы
мостят таймлайн, и слой последовательностей читает соседние элементы списка как
переход — но `min_duration` (дефолт `2`) отбрасывает короткие зоны, и соседи
отброшенной перестают примыкать. Пара, разделённая пропуском, переходом не
является: между этими зонами было то, чего в выборке нет.

```python
summary = result.sequence_analysis['sequence_summary']
print(summary['total_transitions'])        # засчитано переходов
print(summary['discarded_transitions'])    # отброшено как непримыкающие
print(summary['bars_missing'])             # сколько баров потеряно в пропусках
print(summary['contiguous_segments'])      # на сколько сплошных отрезков распалась серия
print(summary['adjacency_verified'])       # False, если границы зон недоступны
```

На встроенном сэмпле при дефолтном `min_duration=2`: MACD даёт 63 засчитанных
перехода и 8 отброшенных, пороговый RSI (все три типа) — 30 и 13.

**Состояния цепи Маркова берутся из наблюдённой последовательности**, а не из
фиксированной пары:

```python
markov = result.sequence_analysis['markov_analysis']
print(markov['states'])                 # ['neutral', 'overbought', 'oversold']
print(markov['observed_transitions'])   # совпадает с суммой transitions
```

Если ни одна пара зон не примыкает, возвращается `markov['error']` с объяснением, а
не нулевая матрица. Раньше на любом словаре, кроме `bull`/`bear`, функция отдавала
нули как успех — вместе с `states: ['bull','bear']` и стационарным распределением
`[1.0, 0.0]`, то есть уверенным утверждением о состоянии, ни разу не встретившемся
в данных.

**Runs-test бинаризуется по объявленной полярности** и считается на самом длинном
сплошном отрезке; при отсутствии объявленных полярностей возвращает
`not_applicable` с причиной вместо константного ряда.

#### `ZoneType` и `ZoneVocabulary` — стратегия объявляет свои типы зон

Тип зоны — **открытый словарь**. `zero_crossing` называет свои типы `bull`/`bear`,
`threshold` — `overbought`/`neutral`/`oversold`, ваша собственная стратегия может
называть их `regime_a`/`regime_b`/`regime_c`. Ядро не содержит перечня допустимых имён
и не должно его содержать.

Чтобы универсальные слои (метрики зоны, анализ последовательностей, статистика,
визуализация) могли работать с любым словарём, стратегия объявляет **свойства** каждого
типа, а потребитель дискриминирует по ним, а не по имени:

```python
from bquant.analysis.zones import ZoneType, ZoneVocabulary
from bquant.analysis.zones.detection import ZoneDetectionRegistry

vocab = ZoneDetectionRegistry.get_vocabulary('threshold')

print(vocab.names())
# ['overbought', 'neutral', 'oversold']

print(vocab.polarity_of('overbought'), vocab.polarity_of('neutral'))
# 1 0

print(vocab.contrast_pairs())
# [('overbought', 'oversold')]
```

**Свойства (закрытый словарь):**

| Поле | Значения | Смысл |
|---|---|---|
| `name` | любая непустая строка | метка, попадающая в `ZoneInfo.type` |
| `polarity` | `+1` / `-1` / `0` / `None` | положение на оси **того ряда, по которому зона выделена**: приподнят / подавлен / объявленно нейтрален / ось не упорядочена |
| `counterpart` | имя типа или `None` | контрастная пара для тестов, сравнивающих два набора зон |
| `label` | строка или `None` | подпись для графиков; по умолчанию `name` |

`polarity` — про **индикатор, а не про цену**. «`bull` = цена растёт» — допущение MACD;
для `overbought` по RSI оно натянуто, а для зон волатильности бессмысленно. Поэтому
`+1` означает «ряд приподнят относительно своей нейтральной точки» (гистограмма MACD выше
нуля, RSI выше верхнего порога, волатильность высокая).

`polarity=None` — это **объявленное отсутствие направления**, а не «неизвестно».
Потребитель обязан отреагировать явно: пропустить направленную метрику и сообщить об этом.

**Регистрация собственной стратегии:**

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry
from bquant.analysis.zones import ZoneType

@ZoneDetectionRegistry.register(
    'volatility_regime',
    description='Split the series into high/low volatility regimes',
    supported_zones=[
        ZoneType('high_vol', polarity=+1, counterpart='low_vol', label='High volatility'),
        ZoneType('low_vol', polarity=-1, counterpart='high_vol', label='Low volatility'),
    ],
    required_rules=['indicator_col', 'threshold'],
)
class VolatilityRegimeDetection:
    def detect_zones(self, data, config):
        ...
```

Голые строки тоже принимаются (`supported_zones=['high_vol', 'low_vol']`) — они
поднимаются до дескрипторов без объявленных свойств. Стратегия при этом работает, но
универсальные слои сообщат о неприменимости направленного анализа вместо того, чтобы
угадывать направление по имени.

**Пара выводится, если объявление опущено**, но только когда противоположный знак
представлен единственным типом. При `strong_bull`/`weak_bull` (оба `+1`) однозначного
ответа нет, и `counterpart_of()` вернёт `None` вместо того, чтобы выбрать произвольно —
поэтому для словарей из трёх и более типов пару лучше объявлять явно.

**Словарь, определяемый во время выполнения.** У `preloaded` типы приходят из
импортируемых данных, у `combined` — из `rules['zone_type_map']` вызывающего. Такие
стратегии передают `supported_zones=None`, и их словарь помечен `is_declared == False`:

```python
vocab = ZoneDetectionRegistry.get_vocabulary('preloaded')
print(vocab.is_declared, vocab.names())
# False []
```

Пустой словарь означает «определяется во время выполнения», а **не** «типов нет» —
потребители читают `is_declared` и в этом случае не фильтруют.


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
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70)
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
    .detect_zones('threshold', indicator_col='RSI_14', 
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
