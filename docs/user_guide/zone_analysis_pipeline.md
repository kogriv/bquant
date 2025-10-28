# Полный пайплайн анализа зон BQuant

Это руководство описывает полный пайплайн анализа зон в BQuant - от начала до конца. Вы узнаете как работает каждый компонент системы и как они взаимодействуют между собой.

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
    start_idx: int                  # Начальный индекс
    end_idx: int                    # Конечный индекс
    start_time: datetime            # Время начала
    end_time: datetime              # Время окончания
    duration: int                   # Длительность в барах
    data: pd.DataFrame              # Данные зоны (OHLCV + индикаторы)
    features: Dict[str, Any]        # Признаки (заполняется после анализа)
    indicator_context: Dict[str, Any]  # v2.1: Контекст детекции

    # indicator_context содержит:
    # {
    #     'detection_strategy': 'zero_crossing',
    #     'detection_indicator': 'macd_hist',
    #     'signal_line': None,
    #     'detection_rules': {...}
    # }
```

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
    def save(filepath, format='pickle')  # Сохранение результата
    def load(filepath, format='pickle')  # Загрузка результата
    def visualize(mode='overview')       # Визуализация
```

## 🎯 Стратегии детекции зон

### 1. ZeroCrossingDetection (пересечение нуля)

**Применение:** MACD, AO, CCI, любой осциллятор с нулевой линией

```python
config = ZoneDetectionConfig(
    min_duration=2,
    zone_types=['bull', 'bear'],
    rules={'indicator_col': 'macd_histogram'},
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

**ZoneFeaturesAnalyzer** извлекает:

```python
zone.features = {
    # Базовые
    'duration': 15,
    'mean_price': 2050.5,
    'price_change': 12.3,

    # Форма (ShapeStrategy)
    'skewness': -0.5,
    'kurtosis': 2.3,
    'trend': 'upward',

    # Swing точки (SwingStrategy)
    'num_peaks': 3,
    'num_troughs': 2,
    'avg_swing_amplitude': 5.2,

    # Дивергенции (DivergenceStrategy)
    'has_divergence': True,
    'divergence_type': 'bullish',

    # Объем (VolumeStrategy)
    'avg_volume': 15000,
    'volume_trend': 'increasing',
    'volume_indicator_corr': 0.65,

    # Волатильность (VolatilityStrategy)
    'volatility': 0.015,
    'volatility_change': 0.002
}
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
        swing='find_peaks',
        shape='statistical',
        divergence='classic',
        volume='standard'
    )
    .analyze(clustering=True, n_clusters=3, regression=True)
    .with_cache(enable=True, ttl=7200)
    .build()
)

# Результат с полным анализом
print(f"Зон: {len(result.zones)}")
print(f"Кластеры: {result.clustering}")
print(f"Гипотезы: {result.hypothesis_tests}")

# Сохранение
result.save('results/macd_zones.pkl')

# Визуализация
fig = result.visualize('overview')
fig.show()
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
    .with_strategies(swing='find_peaks')  # Работает сразу!
    .build()
)
# БЕЗ изменений в коде BQuant!
```

## 💾 Кэширование и персистентность

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

- [API Reference: zones module](../api/analysis/zones.md)
- [Examples: 02a_universal_zones.py](../../examples/02a_universal_zones.py)
- [Developer Guide: Zone Detection Strategies](../developer_guide/zone_detection_strategies.md)
- [Core Concepts](core_concepts.md)
- [Quick Start](quick_start.md)
