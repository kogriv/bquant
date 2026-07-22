# Полный пайплайн анализа зон BQuant

> 💡 **Ищете концептуальный обзор?**
>
> Этот документ — очень детальное, низкоуровневое описание каждого шага пайплайна. Для более высокоуровневого и концептуального понимания логики работы, рекомендуем сначала прочитать **[Глубокое погружение: Пайплайн анализатора зон](../developer_guide/zone_analyzer_deep_dive.md)**.

Это руководство описывает полный пайплайн анализа зон в BQuant - от начала до конца. Вы узнаете как работает каждый компонент системы и как они взаимодействуют между собой.

## 📚 Связанные материалы

- [Структура результата и экспорт в артефакты](zone_analysis_result.md) — исчерпывающее описание структуры `ZoneAnalysisResult` и `ZoneInfo`, источников полей и кода для экспорта в артефакты (01_…08_, full_analysis, summary).
- [Best Practices анализа зон](best_practices.md) — практические рекомендации по хранению артефактов и модульному использованию.
- [Миграция на Universal Zone Analysis v2](../migration/MIGRATION_v2.md) — переход со старого `MACDZoneAnalyzer` на новый пайплайн.

## 📊 Архитектура (высокоуровневая)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUENT API (analyze_zones)                   │
│                     ZoneAnalysisBuilder                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ZoneAnalysisPipeline                           │
│  (Координатор + Кэширование)                                    │
└────────┬──────────────────────────┬─────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐      ┌──────────────────────────────┐
│ IndicatorFactory│      │  ZoneDetectionStrategy       │
│  (Расчет        │      │  (Детекция зон)              │
│   индикатора)   │      │  - ZeroCrossingDetection     │
└────────┬────────┘      │  - ThresholdDetection        │
         │               │  - LineCrossingDetection     │
         │               │  - PreloadedZonesDetection   │
         │               │  - CombinedRulesDetection    │
         │               └─────────┬────────────────────┘
         │                         │
         └────────┬────────────────┘
                  │
                  ▼
         List[ZoneInfo] (обнаруженные зоны)
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              UniversalZoneAnalyzer                              │
│  (Универсальный оркестратор анализа)                            │
└───┬───────┬──────────┬────────────┬────────────┬───────────────┘
    │       │          │            │            │
    ▼       ▼          ▼            ▼            ▼
┌────────┐ ┌────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│Features│ │Stat│ │Hypoth. │ │Sequence  │ │Regression│
│Extract │ │    │ │Tests   │ │Analysis  │ │(optional)│
└────────┘ └────┘ └────────┘ └──────────┘ └──────────┘
    │       │          │            │            │
    └───────┴──────────┴────────────┴────────────┘
                       │
                       ▼
             ZoneAnalysisResult
```

## Global vs Per-Zone Swing Calculation

**По умолчанию** используется режим `global`: пивоты свингов вычисляются один раз на полном датасете и нарезаются под каждую зону с сохранением соседних точек. Это особенно полезно для широких трендов, которые пересекают границы зон. Для возврата к локальному расчёту используйте `.with_swing_scope('per_zone')`.

| Критерий | `global` (по умолчанию) | `per_zone` |
| --- | --- | --- |
| Контекст расчёта | Свинги считаются на всём DataFrame и шарятся между зонами | Каждый свинг считается на локальном срезе `zone.data` |
| Полнота метрик | Захватываются соседние пивоты, coverage 70–90% | Часто теряются пивоты на границах, coverage 18–62% |
| Производительность | Единовременный расчёт + дешёвая нарезка по зонам | Быстрее на коротких сериях, без подготовки контекста |
| Рекомендуемые сценарии | Production-аналитика, отчёты, исследовательские ноутбуки | Быстрые локальные эксперименты, отладка небольших окон |

### Быстрый старт

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(price_df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag')
    .with_swing_preset('narrow_zone')
    .with_swing_scope('global')  # по умолчанию, можно опустить
    .analyze()
    .build()
)

for zone in result.zones:
    swings = zone.get_zone_swings()  # возвращает SwingPoint, включая соседние пивоты
    swing_mode = zone.features.get('metadata', {}).get('swing_calculation_mode')
    print(zone.zone_id, swing_mode, len(swings))
```

**На что обратить внимание:**

- Стратегия свингов задаётся через `with_strategies(swing='...')`, параметры — через `with_swing_preset('narrow_zone')` или `'wide_zone'`. См. [Глубокое погружение](../developer_guide/zone_analyzer_deep_dive.md) и [Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md).
- Режим расчёта сохраняется в `zone.features['metadata']['swing_calculation_mode']` (`'global'` или `'per_zone'`). У `ZoneInfo` нет атрибута `metadata` — он внутри `features`.
- Метод `get_zone_swings()` автоматически выдаёт актуальный список пивотов вне зависимости от режима.
- В режиме `global` алгоритм создаёт один `SwingContext` и шарит его между зонами — экономия времени при большом количестве зон.

### Переключение между режимами в одной сессии

```python
per_zone_result = (
    analyze_zones(price_df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')
    .with_swing_preset('narrow_zone')
    .with_swing_scope('per_zone')
    .build()
)

global_result = (
    analyze_zones(price_df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')
    .with_swing_preset('narrow_zone')
    .with_swing_scope('global')
    .build()
)

comparison = [
    (
        zone.zone_id,
        len(zone.get_zone_swings()),
        len(global_result.zones[idx].get_zone_swings())
    )
    for idx, zone in enumerate(per_zone_result.zones)
]

print('zone_id | per_zone | global')
for zone_id, local_count, global_count in comparison:
    print(f"{zone_id:>7} | {local_count:>7} | {global_count:>6}")
```

Второй запуск переиспользует подготовленный `SwingContext`, поэтому разница во времени минимальна. Такой приём удобно применять в
research-ноутбуках для визуального сравнения режимов.

### Мини-визуализация результатов

```python
import matplotlib.pyplot as plt

zone = global_result.zones[0]
swings = zone.get_zone_swings()

plt.plot(price_df['close'], label='Close price')
# SwingPoint: timestamp, price, swing_type ('peak'/'trough')
plt.scatter([p.timestamp for p in swings], [p.price for p in swings],
            c=['red' if p.swing_type == 'peak' else 'green' for p in swings],
            label='Global swings')
plt.axvspan(zone.start_time, zone.end_time, alpha=0.2, color='steelblue', label='Zone window')
plt.legend()
plt.title('Сравнение зоны с глобальными свингами')
plt.show()
```

Диаграмма наглядно демонстрирует, что свинги включают точки, выходящие за границы зоны, что обеспечивает корректную амплитуду и
длительность движения внутри окна анализа.

## 🔄 Детальный процесс (пошагово)

### Этап 1: Подготовка данных

```python
# Пользователь запускает:
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)
```

**Что происходит:**

```
1. analyze_zones(df) создает ZoneAnalysisBuilder
2. .with_indicator() → сохраняет IndicatorConfig
3. .detect_zones() → сохраняет ZoneDetectionConfig
4. .analyze() → настраивает параметры анализа
5. .build() → запускает pipeline!
```

### Этап 2: Выполнение pipeline

```python
# ZoneAnalysisBuilder.build() создает:
pipeline = ZoneAnalysisPipeline(config, enable_cache=True)
result = pipeline.run(df)
```

**pipeline.run() выполняет:**

```
┌──────────────────────────────────────────────────────────┐
│ 1. ПРОВЕРКА КЭША                                         │
│    ├─ Генерация ключа (hash данных + конфигурация)      │
│    ├─ Проверка cache_manager.get(key)                   │
│    └─ Если найден → вернуть результат (БЫСТРО!)         │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼ (cache miss)
┌──────────────────────────────────────────────────────────┐
│ 2. ПОДГОТОВКА ДАННЫХ (если нужен индикатор)             │
│    ├─ IndicatorFactory.create(source, name, **params)   │
│    ├─ indicator.calculate(df)                           │
│    ├─ Объединение результата с исходным df              │
│    └─ df_prepared (с индикатором)                       │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 3. ДЕТЕКЦИЯ ЗОН                                          │
│    ├─ ZoneDetectionRegistry.get(strategy_name)          │
│    ├─ detector.detect_zones(df_prepared, config)        │
│    └─ List[ZoneInfo] с заполненным indicator_context    │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 4. АНАЛИЗ ЗОН                                            │
│    ├─ UniversalZoneAnalyzer.analyze_zones(zones, df)    │
│    └─ ZoneAnalysisResult                                │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 5. СОХРАНЕНИЕ В КЭШ                                      │
│    └─ cache_manager.put(key, result, ttl=3600)          │
└──────────────────────────────────────────────────────────┘
```

### Этап 3: Детекция зон (пример ZeroCrossingDetection)

```python
class ZeroCrossingDetection:
    def detect_zones(self, data, config):
        # 1. Валидация
        config.validate(required_rules=['indicator_col'])
        indicator_col = config.rules['indicator_col']

        # 2. Извлечение индикатора
        indicator_values = data[indicator_col].values

        # 3. Опциональное сглаживание
        if smooth_window:
            indicator_values = smooth(indicator_values)

        # 4. Поиск пересечений нуля
        signs = np.sign(indicator_values)
        sign_changes = np.where(np.diff(signs) != 0)[0] + 1

        # 5. Создание зон
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1

            # Фильтр по min_duration
            if duration < config.min_duration:
                continue

            # Определение типа зоны
            zone_type = 'bull' if mean_value > 0 else 'bear'

            # Создание ZoneInfo с indicator_context
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=data.index[start_idx],
                end_time=data.index[end_idx],
                duration=duration,
                data=data.iloc[start_idx:end_idx + 1],
                indicator_context={
                    'detection_strategy': 'zero_crossing',
                    'detection_indicator': indicator_col,
                    'signal_line': None,
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)

        return zones
```

### Этап 4: Анализ зон (UniversalZoneAnalyzer)

```python
class UniversalZoneAnalyzer:
    def analyze_zones(self, zones, data, perform_clustering, n_clusters, ...):
        # 1. Извлечение признаков из каждой зоны
        zones_features = self.features.extract_all_zones_features(zones)

        # Записать признаки обратно в ZoneInfo
        for zone, features in zip(zones, zones_features):
            zone.features = features.to_dict()

        # 2. Статистический анализ
        statistics = self.features.analyze_zones_distribution(zones_features)

        # 3. Тестирование гипотез
        hypothesis_tests = self.hypotheses.run_all_tests(zones_features)

        # 4. Анализ последовательностей (если >= 3 зоны)
        sequence_analysis = None
        if len(zones) >= 3:
            sequence_analysis = self.sequences.analyze_zone_transitions(zones_features)

        # 5. Кластеризация (опционально)
        clustering = None
        if perform_clustering and len(zones) >= n_clusters:
            clustering = self.sequences.cluster_zones(zones_features, n_clusters)

        # 6. Регрессия (опционально, если >= 10 зон)
        regression_results = None
        if run_regression and len(zones) > 10:
            regression_results = self.regression.predict_zone_duration(...)

        # 7. Валидация (опционально, если >= 20 зон)
        validation_results = None
        if run_validation and len(zones) > 20:
            validation_results = self.validation.validate(...)

        # Сборка результата
        return ZoneAnalysisResult(
            zones=zones,
            statistics=statistics,
            hypothesis_tests=hypothesis_tests,
            sequence_analysis=sequence_analysis,
            clustering=clustering,
            regression_results=regression_results,
            validation_results=validation_results,
            data=data,
            metadata={...}
        )
```

## 🧩 Ключевые модели данных

### ZoneInfo (одна зона)

```python
@dataclass
class ZoneInfo:
    zone_id: int                    # Уникальный ID
    type: str                       # 'bull', 'bear', 'overbought', 'oversold'
    start_idx: int                  # Начальный индекс (iloc)
    end_idx: int                    # Конечный индекс (iloc)
    start_time: datetime            # Время начала
    end_time: datetime              # Время окончания
    duration: int                   # Длительность в барах
    data: pd.DataFrame              # Данные зоны (OHLCV + индикаторы)
    features: Dict[str, Any]        # Признаки (заполняется после анализа)
    indicator_context: Dict[str, Any]  # v2.1: Контекст детекции
    swing_context: Optional[SwingContext]  # При глобальном режиме (по умолчанию)

    # indicator_context содержит:
    # {'detection_strategy': 'zero_crossing', 'detection_indicator': 'macd_hist', ...}

    def get_zone_swings(self) -> List[SwingPoint]:  # Свинги зоны (из swing_context)
```

**Важно:** у `ZoneInfo` нет атрибута `metadata`. Метаданные (в т.ч. `swing_calculation_mode`, `swing_metrics`) лежат в `zone.features['metadata']`.

### ZoneAnalysisResult (результат анализа)

```python
@dataclass
class ZoneAnalysisResult:
    zones: List[ZoneInfo]              # Все обнаруженные зоны
    statistics: Dict[str, Any]         # Статистики (среднее, медиана, std)
    hypothesis_tests: Dict[str, Any]   # Результаты статистических тестов
    clustering: Optional[Dict]         # Результаты кластеризации
    sequence_analysis: Optional[Dict]  # Анализ последовательностей
    regression_results: Optional[Dict] # Регрессионный анализ
    validation_results: Optional[Dict] # Валидация
    data: Optional[pd.DataFrame]       # Исходный DataFrame
    metadata: Dict[str, Any]           # Метаданные

    # Методы:
    def save(filepath, format='pickle')   # Сохранение результата
    def visualize(mode='overview')        # Визуализация

# load — метод класса:
loaded = ZoneAnalysisResult.load('results/zones.pkl', format='pickle')
```

## 🎯 Стратегии детекции зон

### 1. ZeroCrossingDetection (пересечение нуля)

**Применение:** MACD, AO, CCI, любой осциллятор с нулевой линией

```python
config = ZoneDetectionConfig(
    min_duration=2,
    zone_types=['bull', 'bear'],
    rules={'indicator_col': 'macd_hist'},  # custom MACD создаёт колонку macd_hist
    strategy_name='zero_crossing'
)
```

**Алгоритм:**
- Индикатор > 0 → 'bull' зона
- Индикатор < 0 → 'bear' зона
- Пересечение нуля = граница зоны

### 2. ThresholdDetection (пороговые значения)

**Применение:** RSI, Stochastic, Williams %R

```python
config = ZoneDetectionConfig(
    min_duration=3,
    zone_types=['overbought', 'oversold'],
    rules={
        'indicator_col': 'rsi',
        'upper_threshold': 70,
        'lower_threshold': 30
    },
    strategy_name='threshold'
)
```

**Алгоритм:**
- Индикатор > upper_threshold → 'overbought'
- Индикатор < lower_threshold → 'oversold'
- Между порогами → нет зоны

### 3. LineCrossingDetection (пересечение линий)

**Применение:** MA crossover, MACD line/signal, Stochastic %K/%D

```python
config = ZoneDetectionConfig(
    min_duration=2,
    zone_types=['bull', 'bear'],
    rules={
        'line1_col': 'sma_fast',
        'line2_col': 'sma_slow'
    },
    strategy_name='line_crossing'
)
```

**Алгоритм:**
- line1 > line2 → 'bull' зона
- line1 < line2 → 'bear' зона
- Пересечение = граница зоны

### 4. PreloadedZonesDetection (внешние данные)

**Применение:** Зоны из CSV, Excel, database, другой системы

```python
config = ZoneDetectionConfig(
    rules={'zones_data': 'zones.csv'},
    strategy_name='preloaded'
)
```

### 5. CombinedRulesDetection (комбинированные правила)

**Применение:** Сложная логика с несколькими условиями

```python
config = ZoneDetectionConfig(
    rules={
        'conditions': [
            {'type': 'lambda', 'func': lambda row: row['rsi'] > 70},
            {'type': 'threshold', 'col': 'volume', 'threshold': 1000000}
        ]
    },
    strategy_name='combined'
)
```

## 🔬 Извлечение признаков

**ZoneFeaturesAnalyzer** заполняет `zone.features`. Структура — смесь полей верхнего уровня и вложенного `metadata`:

```python
zone.features = {
    # Верхний уровень (ZoneFeatures)
    'zone_id': 'bull_0',
    'zone_type': 'bull',
    'duration': 15,
    'start_price': 2050.0,
    'end_price': 2062.3,
    'price_return': 0.006,
    'hist_amplitude': 0.012,
    'num_peaks': 3,
    'num_troughs': 2,
    'peak_time_ratio': 0.73,
    'drawdown_from_peak': -0.002,
    # ...

    # Вложенные метрики (по стратегиям)
    'metadata': {
        'swing_calculation_mode': 'global',  # или 'per_zone'
        'swing_metrics': {
            'rally_count': 4,
            'drop_count': 3,
            'avg_rally_pct': 0.5,
            'avg_drop_pct': -0.3,
            'num_swings': 7,
            'rally_to_drop_ratio': 1.2,
        },
        'shape_metrics': {'hist_skewness': -0.5, 'hist_kurtosis': 2.3, ...},
        'divergence_metrics': {'divergence_type': 'none', 'divergence_count': 0, ...},
        'volatility_metrics': {...},
        'volume_metrics': {'volume_indicator_corr': 0.65, ...},
    }
}
```

Пример доступа к метрикам свингов (для анализа состоятельности):

```python
swing_metrics = zone.features.get('metadata', {}).get('swing_metrics', {})
rally_count = swing_metrics.get('rally_count')
avg_rally_pct = swing_metrics.get('avg_rally_pct')
```

## 📈 Примеры использования

### Минимальный пример (MACD)

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('mt_xauusd_m15')

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .build()
)

print(f"Найдено зон: {len(result.zones)}")
```

### Полный пример (с кастомизацией)

```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=5)
    .with_strategies(
        swing='zigzag',
        shape='statistical',
        divergence='classic',
        volume='standard'
    )
    .with_swing_preset('narrow_zone')
    .with_swing_scope('global')
    .analyze(clustering=True, n_clusters=3, regression=True)
    .with_cache(enable=True, ttl=7200)
    .build()
)

# Результат с полным анализом
print(f"Зон: {len(result.zones)}")
print(f"Кластеры: {result.clustering}")
print(f"Гипотезы: {result.hypothesis_tests.results if hasattr(result.hypothesis_tests, 'results') else result.hypothesis_tests}")

# Сохранение
result.save('results/macd_zones.pkl')

# Визуализация
fig = result.visualize('overview', title='Price + Zones')
fig.show()

# Детальный разбор одной зоны (см. раздел «Визуализация» ниже)
detail = result.visualize(
    'detail',
    zone_id=result.zones[0].zone_id,
    context_bars=30,
)
detail.show()

# Сравнение нескольких зон с выбором backend визуализатора
comparison = result.visualize(
    'comparison',
    backend='matplotlib',
    max_zones=4,
)
comparison.show()

# Быстрый обзор статистики зон
stats = result.visualize('statistics', title='Zone Statistics Summary')
stats.show()

> ⚠️ Визуализатор требует исходный ``DataFrame`` и список зон. Если
> результат был сохранён без ``data`` или вы очистили ``result.zones``,
> метод выдаст понятную ошибку с подсказкой.
```

### Модульное использование (только детекция)

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig

detector = ZoneDetectionRegistry.get('zero_crossing')
config = ZoneDetectionConfig(
    min_duration=2,
    rules={'indicator_col': 'macd_hist'}
)

zones = detector.detect_zones(df, config)
# zones = List[ZoneInfo] без анализа
```

## 🎨 Уникальные особенности v2.1

### indicator_context - Самоописывающиеся зоны

Каждая зона "знает" как она была обнаружена:

```python
zone = result.zones[0]
ctx = zone.indicator_context

print(f"Индикатор: {ctx['detection_indicator']}")  # 'macd_hist'
print(f"Стратегия: {ctx['detection_strategy']}")   # 'zero_crossing'
print(f"Signal line: {ctx['signal_line']}")        # None или колонка

# Это позволяет analytical strategies работать с правильным индикатором!
```

### Универсальность - работает с ЛЮБЫМ индикатором

```python
# Кастомный индикатор (любая формула!)
df['MY_CUSTOM'] = (df['close'].diff(5) / df['close'].rolling(20).std())

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_CUSTOM')
    .with_strategies(swing='zigzag')  # Работает сразу!
    .build()
)
# БЕЗ изменений в коде BQuant!
```

## 💾 Кэширование и персистентность

Подробное описание: **[Справочник по кэшированию](caching.md)** — архитектура, настройка, очистка.

```python
# Автоматическое кэширование (2-level: memory + disk)
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_cache(enable=True, ttl=3600)  # 1 час TTL
    .build()
)

# Сохранение в разных форматах
result.save('results/zones.pkl', format='pickle')         # Быстро, все данные
result.save('results/zones.json', format='json')          # Читаемо, без DataFrame
result.save('results/zones.parquet', format='parquet')    # Компактно, columnar

# Загрузка
from bquant.analysis.zones.models import ZoneAnalysisResult
loaded = ZoneAnalysisResult.load('results/zones.pkl')
```

## 🚀 Главные преимущества

- ✅ **Универсальность** - один API для всех индикаторов
- ✅ **Модульность** - можно использовать отдельные компоненты
- ✅ **Расширяемость** - легко добавить новые стратегии
- ✅ **Производительность** - автоматическое кэширование
- ✅ **Удобство** - fluent API + presets
- ✅ **Самодокументирование** - indicator_context в каждой зоне

## 📚 Дополнительные ресурсы

- [Структура результата анализа зон и экспорт в артефакты](zone_analysis_result.md) — полная структура объекта результата и получение артефактов из Best Practices
- [Справочник по кэшированию](caching.md) — работа с кэшем (zone analysis и общий)
- [API Reference: zones module](../api/analysis/zones.md)
- [Глубокое погружение: Пайплайн анализатора зон](../developer_guide/zone_analyzer_deep_dive.md) — описание `with_swing_preset`, `with_strategies`, структура `zone.features`
- [Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md) — покрытие zigzag/find_peaks/pivot_points, режимы `per_zone`/`global`
- [Examples: 02a_universal_zones.py](../../examples/02a_universal_zones.py)
- [Developer Guide: Zone Detection Strategies](../developer_guide/zone_detection_strategies.md)
- [Core Concepts](core_concepts.md)
- [Quick Start](quick_start.md)
