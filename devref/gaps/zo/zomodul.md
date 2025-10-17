# Модульное использование компонентов Zone Analysis

**Дата:** 2025-10-17  
**Версия:** v1.0  
**Связано с:** `zonan.md` (архитектура универсального анализатора зон)  
**Контекст:** Независимое использование компонентов архитектуры

---

## Содержание

1. [Введение: Принципы модульности](#введение)
2. [Граф зависимостей компонентов](#граф)
3. [Сценарии модульного использования](#сценарии)
4. [Сводная таблица](#таблица)
5. [Best Practices](#best-practices)

---

<a name="введение"></a>
## Введение: Принципы модульности

### Ключевая идея

> **"Каждый компонент - самостоятельная единица, работающая со стандартными типами данных."**

Архитектура спроектирована так, чтобы каждый компонент можно было использовать **независимо** от полного pipeline. Это позволяет:

- ✅ Получать промежуточные результаты
- ✅ Сохранять их для последующего использования
- ✅ Переиспользовать в других проектах
- ✅ Комбинировать разными способами
- ✅ Отлаживать пошагово
- ✅ Оптимизировать производительность (не пересчитывать все)

### Стандартные типы данных

Все компоненты работают со стандартными типами:

| Тип | Описание | Сериализация |
|-----|----------|--------------|
| `pd.DataFrame` | OHLCV + индикаторы | CSV, parquet, pickle |
| `List[ZoneInfo]` | Детектированные зоны | pickle, JSON (через to_dict) |
| `List[ZoneFeatures]` | Признаки зон | CSV, JSON (через to_dict) |
| `Dict[str, Any]` | Результаты анализа | JSON, pickle |
| `ZoneAnalysisResult` | Полный результат | pickle, JSON, parquet (встроенные методы) |

---

<a name="граф"></a>
## Граф зависимостей компонентов

### Визуальное представление

```
┌─────────────────────────────────────────────────────────────┐
│ УРОВЕНЬ 1: Независимые компоненты                          │
│ (требуют только pd.DataFrame с данными)                     │
└─────────────────────────────────────────────────────────────┘
│
├─→ IndicatorFactory.create()
│   Input:  pd.DataFrame (OHLCV)
│   Output: IndicatorResult (DataFrame с индикатором)
│   Save:   indicator_data.to_parquet('indicator.parquet')
│
└─→ ZoneDetectionStrategy.detect_zones()
    Input:  pd.DataFrame (OHLCV + индикаторы)
    Output: List[ZoneInfo]
    Save:   pickle.dump(zones, file) или zones_to_csv(zones, 'zones.csv')

┌─────────────────────────────────────────────────────────────┐
│ УРОВЕНЬ 2: Анализ признаков                                │
│ (требует List[ZoneInfo])                                    │
└─────────────────────────────────────────────────────────────┘
│
└─→ ZoneFeaturesAnalyzer.extract_all_zones_features()
    Input:  List[ZoneInfo]
    Output: List[ZoneFeatures]
    Save:   features_df.to_csv('features.csv')

┌─────────────────────────────────────────────────────────────┐
│ УРОВЕНЬ 3: Статистические компоненты                       │
│ (требует List[ZoneFeatures] или List[Dict])                │
└─────────────────────────────────────────────────────────────┘
│
├─→ ZoneFeaturesAnalyzer.analyze_zones_distribution()
│   Input:  List[Dict] (zone features)
│   Output: Dict (statistics)
│   Save:   json.dump(stats, file)
│
├─→ HypothesisTestSuite.run_all_tests()
│   Input:  List[Dict] (zone features)
│   Output: Dict (hypothesis results)
│   Save:   json.dump(hypotheses, file)
│
├─→ ZoneSequenceAnalyzer.analyze_zone_transitions()
│   Input:  List[ZoneFeatures]
│   Output: Dict (sequence results)
│   Save:   json.dump(sequence, file)
│
└─→ ZoneRegressionAnalyzer.predict_*()
    Input:  List[Dict] (zone features)
    Output: Dict (regression results)
    Save:   json.dump(regression, file)

┌─────────────────────────────────────────────────────────────┐
│ УРОВЕНЬ 4: Координация                                     │
│ (требует List[ZoneInfo] + pd.DataFrame)                    │
└─────────────────────────────────────────────────────────────┘
│
└─→ UniversalZoneAnalyzer.analyze_zones()
    Input:  List[ZoneInfo], pd.DataFrame
    Output: ZoneAnalysisResult
    Save:   result.save('result.pkl')

┌─────────────────────────────────────────────────────────────┐
│ УРОВЕНЬ 5: Полный Pipeline (опциональная обертка)          │
│ (требует только pd.DataFrame + конфигурация)               │
└─────────────────────────────────────────────────────────────┘
│
└─→ ZoneAnalysisPipeline / Builder
    Input:  pd.DataFrame, ZoneAnalysisConfig
    Output: ZoneAnalysisResult (с автоматическим кэшированием)
    Save:   result.save('result.pkl')
```

### Правило независимости

**Компоненты уровня N зависят только от уровней < N, но НЕ зависят от уровней > N**

Это означает:
- ✅ `ZoneDetectionStrategy` можно использовать без `UniversalZoneAnalyzer`
- ✅ `ZoneFeaturesAnalyzer` можно использовать без `HypothesisTestSuite`
- ✅ `UniversalZoneAnalyzer` можно использовать без `Pipeline`
- ❌ `ZoneDetectionStrategy` НЕ требует `Pipeline`

---

<a name="сценарии"></a>
## Сценарии модульного использования

### Сценарий 1: Только детекция зон (без анализа)

**Use Case:** Быстрое определение зон для экспорта в торговую систему (MT5, cTrader)

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones.models import ZoneInfo
import pickle
import pandas as pd

# 1. Детектируем зоны
detector = ZoneDetectionRegistry.get('zero_crossing')
zones = detector.detect_zones(
    df_with_macd,
    ZoneDetectionConfig(
        strategy_name='zero_crossing',
        min_duration=3,
        rules={'indicator_col': 'macd'}
    )
)

# 2. Работаем с зонами
print(f"Detected {len(zones)} zones")
for zone in zones[:5]:
    print(f"Zone {zone.zone_id}: {zone.type}, "
          f"duration={zone.duration}, "
          f"start={zone.start_time}, "
          f"end={zone.end_time}")

# 3. Сохраняем только зоны (pickle - полные объекты ZoneInfo)
with open('detected_zones.pkl', 'wb') as f:
    pickle.dump(zones, f)

# 4. Экспорт в CSV (легкая версия без zone.data)
zones_df = pd.DataFrame([
    {
        'zone_id': z.zone_id,
        'type': z.type,
        'start_time': z.start_time,
        'end_time': z.end_time,
        'duration': z.duration,
        'start_idx': z.start_idx,
        'end_idx': z.end_idx
    }
    for z in zones
])
zones_df.to_csv('detected_zones.csv', index=False)

# 5. Экспорт для MT5 (специальный формат)
mt5_zones = []
for z in zones:
    mt5_zones.append({
        'id': z.zone_id,
        'direction': 1 if z.type == 'bull' else -1,
        'start_bar': z.start_idx,
        'end_bar': z.end_idx,
        'start_price': z.data['close'].iloc[0] if len(z.data) > 0 else 0,
        'end_price': z.data['close'].iloc[-1] if len(z.data) > 0 else 0
    })

pd.DataFrame(mt5_zones).to_csv('mt5_zones.csv', index=False)

# ===== Позже загружаем и используем =====

# Загрузка полных зон
with open('detected_zones.pkl', 'rb') as f:
    loaded_zones = pickle.load(f)

print(f"Loaded {len(loaded_zones)} zones")
# Готово для дальнейшего анализа или визуализации
```

### Сценарий 2: Анализ готовых зон (без детекции)

**Use Case:** Анализ зон, полученных из внешнего источника или предыдущего запуска

```python
from bquant.analysis.zones import UniversalZoneAnalyzer
import pickle

# 1. Загружаем готовые зоны (из предыдущего запуска или внешнего источника)
with open('detected_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

# Или из preloaded (CSV от эксперта)
from bquant.analysis.zones.detection.preloaded import load_preloaded_zones
zones = load_preloaded_zones('expert_zones.csv', df, time_tolerance='5min')

# 2. Создаем анализатор
analyzer = UniversalZoneAnalyzer()

# 3. Анализируем только зоны (БЕЗ повторной детекции!)
result = analyzer.analyze_zones(
    zones, 
    df_with_macd,
    perform_clustering=True,
    n_clusters=3,
    run_regression=False
)

# 4. Работаем с результатами
print(f"Statistics:")
print(f"  Bull zones: {result.statistics.get('bull_zones', 0)}")
print(f"  Bear zones: {result.statistics.get('bear_zones', 0)}")
print(f"  Average duration: {result.statistics.get('avg_duration', 0):.1f}")

print(f"\nHypothesis tests:")
for test_name, test_result in result.hypothesis_tests.items():
    print(f"  {test_name}: p-value={test_result['p_value']:.4f}")

# 5. Сохраняем результаты анализа
result.save('zone_analysis_results.pkl')
result.save('zone_analysis_summary.json', format='json', include_data=False)

# 6. Визуализация без повторного анализа
fig = result.visualize('overview')
fig.show()
```

### Сценарий 3: Только извлечение признаков зон

**Use Case:** Feature engineering для ML моделей или экспорт метрик

```python
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
import pickle

# 1. Загружаем зоны
with open('detected_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

# 2. Создаем анализатор признаков с конкретными стратегиями
features_analyzer = ZoneFeaturesAnalyzer(
    swing_strategy=ZigZagSwingStrategy(legs=10, deviation=0.05),
    shape_strategy=StatisticalShapeStrategy(),
    # Остальные стратегии = None (не используем)
)

# 3. Извлекаем только признаки (БЕЗ статистики, гипотез, кластеризации)
zones_features = features_analyzer.extract_all_zones_features(zones)

# 4. Работаем с признаками
print(f"Extracted features for {len(zones_features)} zones")
for zf in zones_features[:3]:
    print(f"\nZone {zf.zone_id} ({zf.zone_type}):")
    print(f"  Duration: {zf.duration} bars")
    print(f"  Swings: {zf.swing_count}")
    print(f"  Max rally: {zf.max_rally_amplitude:.2f}%")
    print(f"  Max drop: {zf.max_drop_amplitude:.2f}%")
    print(f"  Volatility: {zf.avg_volatility_pct:.2f}%")
    print(f"  Shape: {zf.zone_shape}")

# 5. Экспорт признаков в CSV (для ML или внешнего анализа)
features_df = pd.DataFrame([zf.to_dict() for zf in zones_features])
features_df.to_csv('zone_features.csv', index=False)

# 6. Экспорт в parquet (оптимально для больших данных)
features_df.to_parquet('zone_features.parquet')

# ===== Позже загружаем и используем =====

# Загрузка признаков
features_df = pd.read_csv('zone_features.csv')

# Фильтрация по критериям
bull_zones = features_df[features_df['zone_type'] == 'bull']
high_volatility = features_df[features_df['avg_volatility_pct'] > 2.0]
long_duration = features_df[features_df['duration'] > 10]

print(f"Bull zones: {len(bull_zones)}")
print(f"High volatility zones: {len(high_volatility)}")
print(f"Long duration zones: {len(long_duration)}")
```

### Сценарий 4: Только статистический анализ

**Use Case:** Получение только статистики без кластеризации и регрессии

```python
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
import json

# Загружаем признаки зон (из CSV предыдущего запуска)
features_df = pd.read_csv('zone_features.csv')
features_list = features_df.to_dict('records')

# Только статистический анализ
analyzer = ZoneFeaturesAnalyzer()
statistics = analyzer.analyze_zones_distribution(features_list)

# Работаем со статистикой
print(f"Zone Statistics:")
print(f"  Total zones: {statistics.get('total_zones', 0)}")
print(f"  Bull zones: {statistics.get('bull_zones', 0)}")
print(f"  Bear zones: {statistics.get('bear_zones', 0)}")
print(f"  Average duration: {statistics.get('avg_duration', 0):.1f} bars")
print(f"  Average return: {statistics.get('avg_price_return', 0):.2%}")
print(f"  Win rate: {statistics.get('win_rate', 0):.1%}")

# Сохранение только статистики
with open('zone_statistics.json', 'w') as f:
    json.dump(statistics, f, indent=2, default=str)

# Простая визуализация статистики
import matplotlib.pyplot as plt

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))

# Распределение типов зон
ax1.bar(['Bull', 'Bear'], [statistics['bull_zones'], statistics['bear_zones']])
ax1.set_title('Zones by Type')

# Распределение длительности
ax2.hist(features_df['duration'], bins=20)
ax2.set_title('Duration Distribution')

# Распределение доходности
ax3.hist(features_df['price_return'], bins=20)
ax3.set_title('Return Distribution')

# Duration vs Return
ax4.scatter(features_df['duration'], features_df['price_return'], 
            c=features_df['zone_type'].map({'bull': 'blue', 'bear': 'red'}))
ax4.set_xlabel('Duration')
ax4.set_ylabel('Return')
ax4.set_title('Duration vs Return')

plt.tight_layout()
plt.savefig('zone_statistics.png')
```

### Сценарий 5: Только тестирование гипотез

**Use Case:** Проверка конкретных гипотез о зонах

```python
from bquant.analysis.statistical import HypothesisTestSuite
import json

# Загружаем признаки
features_df = pd.read_csv('zone_features.csv')
features_list = features_df.to_dict('records')

# Только тестирование гипотез
hypothesis_suite = HypothesisTestSuite()
hypothesis_results = hypothesis_suite.run_all_tests(features_list)

print("Hypothesis Test Results:")
print("=" * 60)

for test_name, result in hypothesis_results.items():
    print(f"\n{test_name}:")
    print(f"  Null hypothesis: {result.get('null_hypothesis', 'N/A')}")
    print(f"  p-value: {result['p_value']:.4f}")
    print(f"  Significant (α=0.05): {result['significant']}")
    print(f"  Test statistic: {result.get('test_statistic', 'N/A')}")
    
    if result['significant']:
        print(f"  ✅ Reject null hypothesis")
    else:
        print(f"  ❌ Cannot reject null hypothesis")

# Сохранение результатов гипотез
with open('hypothesis_tests.json', 'w') as f:
    json.dump(hypothesis_results, f, indent=2, default=str)

# Извлечение только значимых результатов
significant_tests = {
    name: result 
    for name, result in hypothesis_results.items() 
    if result['significant']
}

print(f"\nSignificant tests: {len(significant_tests)}/{len(hypothesis_results)}")
```

### Сценарий 6: Только анализ последовательностей

**Use Case:** Изучение переходов между зонами и паттернов

```python
from bquant.analysis.zones.sequence_analysis import ZoneSequenceAnalyzer
import json

# Загружаем признаки
features_df = pd.read_csv('zone_features.csv')
# Конвертируем в ZoneFeatures объекты (если нужно) или используем dict
features_list = features_df.to_dict('records')

# Только анализ последовательностей
sequence_analyzer = ZoneSequenceAnalyzer()
sequence_results = sequence_analyzer.analyze_zone_transitions(features_list)

print("Zone Sequence Analysis:")
print("=" * 60)

# Матрица переходов
print("\nTransition Matrix:")
print(sequence_results['transition_matrix'])

# Средняя длительность переходов
print(f"\nAverage transition duration: {sequence_results['avg_transition_duration']:.1f} bars")

# Наиболее частые паттерны
print("\nMost common patterns:")
for pattern, count in sequence_results.get('common_patterns', {}).items():
    print(f"  {pattern}: {count} occurrences")

# Сохранение результатов анализа последовательностей
with open('sequence_analysis.json', 'w') as f:
    json.dump(sequence_results, f, indent=2, default=str)

# Кластеризация зон (опционально)
clustering = sequence_analyzer.cluster_zones(features_list, n_clusters=3)

print(f"\nClustering:")
print(f"  Number of clusters: {clustering.get('n_clusters', 0)}")
print(f"  Cluster labels: {clustering.get('labels', [])}")

with open('zone_clustering.json', 'w') as f:
    json.dump(clustering, f, indent=2, default=str)
```

### Сценарий 7: Пошаговое построение с сохранением промежуточных результатов

**Use Case:** Длительный анализ с возможностью продолжить с любого шага

```python
# ========== ШАГ 1: Расчет индикатора ==========
from bquant.indicators import IndicatorFactory

print("Step 1: Calculating indicator...")
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26, signal=9)
indicator_result = indicator.calculate(df)

# Объединяем с OHLCV
df_with_macd = df.copy()
for col in indicator_result.data.columns:
    df_with_macd[col] = indicator_result.data[col]

# Сохранение промежуточного результата
df_with_macd.to_parquet('step1_indicator_data.parquet')
print("✓ Step 1 saved: step1_indicator_data.parquet")

# ------- МОЖНО ОСТАНОВИТЬСЯ И ПРОДОЛЖИТЬ ПОЗЖЕ -------

# ========== ШАГ 2: Детекция зон ==========
print("\nStep 2: Detecting zones...")

# Загружаем данные с индикатором
df_with_macd = pd.read_parquet('step1_indicator_data.parquet')

from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig

detector = ZoneDetectionRegistry.get('zero_crossing')
zones = detector.detect_zones(
    df_with_macd,
    ZoneDetectionConfig(
        strategy_name='zero_crossing',
        min_duration=2,
        rules={'indicator_col': 'macd'}
    )
)

# Сохранение зон
with open('step2_zones.pkl', 'wb') as f:
    pickle.dump(zones, f)
print(f"✓ Step 2 saved: {len(zones)} zones in step2_zones.pkl")

# ------- МОЖНО ОСТАНОВИТЬСЯ И ПРОДОЛЖИТЬ ПОЗЖЕ -------

# ========== ШАГ 3: Извлечение признаков ==========
print("\nStep 3: Extracting features...")

# Загружаем зоны
with open('step2_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

features_analyzer = ZoneFeaturesAnalyzer()
zones_features = features_analyzer.extract_all_zones_features(zones)

# Сохранение признаков
features_df = pd.DataFrame([zf.to_dict() for zf in zones_features])
features_df.to_csv('step3_features.csv', index=False)
print(f"✓ Step 3 saved: {len(zones_features)} zone features in step3_features.csv")

# ------- МОЖНО ОСТАНОВИТЬСЯ И ПРОДОЛЖИТЬ ПОЗЖЕ -------

# ========== ШАГ 4: Статистический анализ ==========
print("\nStep 4: Statistical analysis...")

# Загружаем признаки
features_df = pd.read_csv('step3_features.csv')
features_list = features_df.to_dict('records')

# Статистика
statistics = features_analyzer.analyze_zones_distribution(features_list)

with open('step4_statistics.json', 'w') as f:
    json.dump(statistics, f, indent=2, default=str)
print("✓ Step 4 saved: step4_statistics.json")

# ------- МОЖНО ОСТАНОВИТЬСЯ И ПРОДОЛЖИТЬ ПОЗЖЕ -------

# ========== ШАГ 5: Тестирование гипотез ==========
print("\nStep 5: Hypothesis testing...")

from bquant.analysis.statistical import HypothesisTestSuite

hypothesis_suite = HypothesisTestSuite()
hypothesis_results = hypothesis_suite.run_all_tests(features_list)

with open('step5_hypotheses.json', 'w') as f:
    json.dump(hypothesis_results, f, indent=2, default=str)
print("✓ Step 5 saved: step5_hypotheses.json")

# ------- ШАГ 6, 7, 8... и т.д. по необходимости -------
```

### Сценарий 8: Комбинирование результатов разных стратегий детекции

**Use Case:** Сравнение зон от разных индикаторов или правил

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer
import pickle

# Детекция зон по MACD (zero crossing)
detector_macd = ZoneDetectionRegistry.get('zero_crossing')
zones_macd = detector_macd.detect_zones(
    df_with_indicators,
    ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_col': 'macd'}
    )
)

# Детекция зон по RSI (threshold)
detector_rsi = ZoneDetectionRegistry.get('threshold')
zones_rsi = detector_rsi.detect_zones(
    df_with_indicators,
    ZoneDetectionConfig(
        strategy_name='threshold',
        zone_types=['overbought', 'oversold'],
        rules={
            'indicator_col': 'rsi',
            'upper_threshold': 70,
            'lower_threshold': 30
        }
    )
)

# Сохраняем отдельно
with open('macd_zones.pkl', 'wb') as f:
    pickle.dump(zones_macd, f)

with open('rsi_zones.pkl', 'wb') as f:
    pickle.dump(zones_rsi, f)

# Анализируем каждый набор зон независимо
analyzer = UniversalZoneAnalyzer()

macd_analysis = analyzer.analyze_zones(zones_macd, df_with_indicators)
rsi_analysis = analyzer.analyze_zones(zones_rsi, df_with_indicators)

# Сохраняем результаты анализа
macd_analysis.save('macd_analysis.pkl')
rsi_analysis.save('rsi_analysis.pkl')

# Сравнение результатов
comparison = {
    'macd': {
        'total_zones': len(zones_macd),
        'avg_duration': macd_analysis.statistics['avg_duration'],
        'win_rate': macd_analysis.statistics.get('win_rate', 0)
    },
    'rsi': {
        'total_zones': len(zones_rsi),
        'avg_duration': rsi_analysis.statistics['avg_duration'],
        'win_rate': rsi_analysis.statistics.get('win_rate', 0)
    }
}

with open('strategy_comparison.json', 'w') as f:
    json.dump(comparison, f, indent=2)

print("Comparison of detection strategies:")
print(json.dumps(comparison, indent=2))
```

### Сценарий 9: Работа с preloaded зонами (внешние данные)

**Use Case:** Анализ зон, размеченных экспертом или торговой системой

```python
from bquant.analysis.zones.detection.preloaded import load_preloaded_zones
from bquant.analysis.zones import UniversalZoneAnalyzer

# 1. Загружаем зоны из внешнего источника
# Формат CSV: zone_id, type, start_time, end_time
zones = load_preloaded_zones(
    zones_path='expert_markup/zones_expert.csv',
    ohlcv_data=df,
    time_tolerance='5min',
    min_duration=2
)

print(f"Loaded {len(zones)} zones from expert markup")

# 2. Сохраняем как стандартные ZoneInfo для переиспользования
with open('expert_zones.pkl', 'wb') as f:
    pickle.dump(zones, f)

# 3. Анализируем зоны эксперта
analyzer = UniversalZoneAnalyzer()
expert_analysis = analyzer.analyze_zones(zones, df)

# 4. Сравниваем с автоматической детекцией
detector = ZoneDetectionRegistry.get('zero_crossing')
auto_zones = detector.detect_zones(df, config)

auto_analysis = analyzer.analyze_zones(auto_zones, df)

# Сравнение качества
comparison = {
    'expert': {
        'zones': len(zones),
        'win_rate': expert_analysis.statistics.get('win_rate', 0),
        'avg_return': expert_analysis.statistics.get('avg_price_return', 0)
    },
    'automatic': {
        'zones': len(auto_zones),
        'win_rate': auto_analysis.statistics.get('win_rate', 0),
        'avg_return': auto_analysis.statistics.get('avg_price_return', 0)
    }
}

print("\nExpert vs Automatic zones:")
print(json.dumps(comparison, indent=2, default=str))
```

### Сценарий 10: Визуализация без полного анализа

**Use Case:** Быстрая визуализация зон без тяжелых вычислений

```python
from bquant.visualization import ZoneVisualizer
import pickle

# Загружаем только зоны (БЕЗ анализа!)
with open('detected_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

# Загружаем данные с индикаторами
df_with_macd = pd.read_parquet('step1_indicator_data.parquet')

# Быстрая визуализация без статистики
visualizer = ZoneVisualizer()

# Общий график
fig1 = visualizer.plot_zones_on_price_chart(
    df_with_macd, 
    zones, 
    title='MACD Zones Quick View'
)
fig1.show()

# Детальный просмотр конкретной зоны
fig2 = visualizer.plot_zone_detail(
    zones[3],  # 4-я зона
    df_with_macd,
    context_bars=15
)
fig2.show()

# Сравнение нескольких зон
selected_zones = [zones[i] for i in [0, 3, 7, 12]]
fig3 = visualizer.plot_zones_comparison(selected_zones, df_with_macd)
fig3.show()

# Сохранение графиков
fig1.write_html('zones_overview.html')
fig2.write_html('zone_3_detail.html')
fig3.write_html('zones_comparison.html')
```

### Сценарий 11: Feature engineering для ML

**Use Case:** Подготовка данных для машинного обучения

```python
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# 1. Загружаем зоны и извлекаем признаки
with open('detected_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

features_analyzer = ZoneFeaturesAnalyzer()
zones_features = features_analyzer.extract_all_zones_features(zones)

# 2. Конвертируем в DataFrame для ML
features_df = pd.DataFrame([zf.to_dict() for zf in zones_features])

# 3. Подготовка данных для ML
# Выбираем признаки для обучения
feature_columns = [
    'duration', 'price_return', 'swing_count',
    'max_rally_amplitude', 'max_drop_amplitude',
    'avg_volatility_pct', 'volume_trend'
]

X = features_df[feature_columns].fillna(0)
y = (features_df['price_return'] > 0).astype(int)  # Бинарная классификация

# 4. Обучение модели
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# 5. Оценка
accuracy = model.score(X_test, y_test)
print(f"Model accuracy: {accuracy:.2%}")

# 6. Сохранение модели
with open('zone_predictor_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# 7. Сохранение конфигурации признаков
ml_config = {
    'feature_columns': feature_columns,
    'model_type': 'RandomForestClassifier',
    'accuracy': accuracy,
    'training_date': datetime.now().isoformat()
}

with open('ml_config.json', 'w') as f:
    json.dump(ml_config, f, indent=2)
```

### Сценарий 12: Кастомный анализ с выбором компонентов

**Use Case:** Использование только нужных компонентов анализа

```python
from bquant.analysis.zones import UniversalZoneAnalyzer
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.analysis.statistical import HypothesisTestSuite
# Другие компоненты НЕ импортируем

# Загружаем зоны
with open('detected_zones.pkl', 'rb') as f:
    zones = pickle.load(f)

# Создаем КАСТОМНЫЙ анализатор (только нужные компоненты через DI)
custom_analyzer = UniversalZoneAnalyzer(
    features_analyzer=ZoneFeaturesAnalyzer(),
    hypothesis_suite=HypothesisTestSuite(),
    # sequence_analyzer=None,  # НЕ используем
    # regression_analyzer=None,  # НЕ используем
    # validation_suite=None  # НЕ используем
)

# Анализ только с выбранными компонентами
result = custom_analyzer.analyze_zones(
    zones,
    df,
    perform_clustering=False,  # Отключаем кластеризацию
    run_regression=False       # Отключаем регрессию
)

# Результат содержит только features + statistics + hypotheses
print("Result contains:")
print(f"  Zones: {len(result.zones)}")
print(f"  Statistics: {bool(result.statistics)}")
print(f"  Hypotheses: {bool(result.hypothesis_tests)}")
print(f"  Sequence analysis: {bool(result.sequence_analysis)}")  # None
print(f"  Regression: {bool(result.regression_results)}")  # None

# Сохранение облегченного результата
result.save('lightweight_analysis.pkl')
```

---

<a name="таблица"></a>
## Сводная таблица модульного использования

### Что можно получить и как сохранить

| Что нужно | Компоненты | Код получения | Сохранение | Формат |
|-----------|-----------|---------------|------------|--------|
| **Только зоны** | `ZoneDetectionStrategy` | `detector.detect_zones(df, config)` | `pickle.dump(zones)` | pkl, CSV (metadata) |
| **Только признаки** | Detector + `ZoneFeaturesAnalyzer` | `analyzer.extract_all_zones_features(zones)` | `features_df.to_csv()` | CSV, parquet |
| **Только статистика** | Features + `analyze_zones_distribution()` | `analyzer.analyze_zones_distribution(features)` | `json.dump(stats)` | JSON |
| **Только гипотезы** | Features + `HypothesisTestSuite` | `suite.run_all_tests(features)` | `json.dump(hypotheses)` | JSON |
| **Только последовательности** | Features + `ZoneSequenceAnalyzer` | `analyzer.analyze_zone_transitions(features)` | `json.dump(sequence)` | JSON |
| **Только регрессия** | Features + `ZoneRegressionAnalyzer` | `analyzer.predict_zone_duration(features)` | `json.dump(regression)` | JSON |
| **Только визуализация** | Zones + `ZoneVisualizer` | `visualizer.plot_zone_detail(zone, df)` | `fig.write_html()` | HTML, PNG, SVG |
| **Частичный анализ** | Detector + Custom Analyzer | `analyzer.analyze_zones(zones, df, ...)` | `result.save()` | pkl, JSON |
| **Полный анализ** | `Pipeline` / `Builder` | `builder.build()` | `result.save()` | pkl, JSON, parquet |

### Форматы сохранения для каждого типа данных

| Тип данных | Рекомендуемый формат | Альтернативы | Размер | Скорость |
|------------|---------------------|--------------|--------|----------|
| `List[ZoneInfo]` | pickle | CSV (metadata only) | Средний | Быстро |
| `pd.DataFrame` (features) | CSV, parquet | pickle | Зависит | CSV: медленно, parquet: быстро |
| `Dict` (statistics, hypotheses) | JSON | pickle | Малый | Быстро |
| `ZoneAnalysisResult` | pickle | JSON (без data), parquet | Большой | pickle: быстро |
| `plotly.Figure` | HTML | PNG, SVG, JSON | Средний | HTML: быстро |

---

<a name="best-practices"></a>
## Best Practices модульного использования

### 1. Когда использовать модульный подход

**Используйте модульный подход, если:**

✅ Нужно остановиться на промежуточном этапе  
✅ Хотите переиспользовать результаты детекции зон  
✅ Планируете batch обработку множества инструментов  
✅ Нужны только конкретные метрики (не весь анализ)  
✅ Работаете с внешними зонами (preloaded)  
✅ Интегрируете с другими системами  
✅ Разрабатываете ML модели на основе признаков зон  
✅ Создаете custom pipeline с нестандартной логикой  

**Используйте полный Pipeline, если:**

✅ Нужен стандартный end-to-end анализ  
✅ Однократное выполнение  
✅ Не требуются промежуточные результаты  
✅ Хотите максимальную простоту использования  

### 2. Рекомендуемая структура хранения результатов

```
results/
├── {instrument}_{timeframe}/
│   ├── 01_indicator_data.parquet       # Данные с индикатором
│   ├── 02_zones.pkl                    # Детектированные зоны (ZoneInfo)
│   ├── 02_zones.csv                    # Metadata зон (легкая версия)
│   ├── 03_features.csv                 # Признаки зон
│   ├── 04_statistics.json              # Статистика
│   ├── 05_hypotheses.json              # Результаты гипотез
│   ├── 06_sequence.json                # Анализ последовательностей
│   ├── 07_clustering.json              # Кластеризация (если есть)
│   ├── 08_regression.json              # Регрессия (если есть)
│   ├── full_analysis.pkl               # Полный ZoneAnalysisResult
│   ├── summary.json                    # Сводка (JSON без DataFrame)
│   └── visualizations/
│       ├── overview.html
│       ├── zone_3_detail.html
│       └── zones_comparison.html
```

### 3. Паттерны переиспользования

#### Паттерн 1: Detect Once, Analyze Many

```python
# Детекция зон один раз
zones = detector.detect_zones(df, config)
with open('zones.pkl', 'wb') as f:
    pickle.dump(zones, f)

# Множественные анализы с разными параметрами
for n_clusters in [2, 3, 4, 5]:
    analyzer = UniversalZoneAnalyzer()
    result = analyzer.analyze_zones(zones, df, n_clusters=n_clusters)
    result.save(f'analysis_clusters_{n_clusters}.pkl')
```

#### Паттерн 2: Extract Once, Use Everywhere

```python
# Извлечение признаков один раз
zones_features = features_analyzer.extract_all_zones_features(zones)
features_df = pd.DataFrame([zf.to_dict() for zf in zones_features])
features_df.to_csv('features.csv', index=False)

# Использование в разных местах
# - ML модель
# - Статистический анализ
# - Визуализация распределений
# - Экспорт в BI системы
```

#### Паттерн 3: Incremental Analysis

```python
# День 1: Детекция
zones = detect_zones(...)
save(zones, 'zones_day1.pkl')

# День 2: Признаки
zones = load('zones_day1.pkl')
features = extract_features(zones)
save(features, 'features_day2.csv')

# День 3: Статистика
features = load('features_day2.csv')
statistics = analyze_statistics(features)
save(statistics, 'stats_day3.json')

# День 4: Полный отчет
zones = load('zones_day1.pkl')
result = full_analysis(zones, df)
result.save('final_report.pkl')
```

### 4. Управление версиями результатов

```python
from datetime import datetime

# Версионирование результатов с timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Сохранение с версией
zones_file = f'results/zones_{timestamp}.pkl'
with open(zones_file, 'wb') as f:
    pickle.dump(zones, f)

analysis_file = f'results/analysis_{timestamp}.pkl'
result.save(analysis_file)

# Создание симлинка на latest
import os
os.symlink(zones_file, 'results/zones_latest.pkl')
os.symlink(analysis_file, 'results/analysis_latest.pkl')

# Загрузка последней версии
with open('results/zones_latest.pkl', 'rb') as f:
    latest_zones = pickle.load(f)
```

### 5. Интеграция с существующими системами

#### Экспорт зон в MT5 format

```python
def export_zones_to_mt5(zones: List[ZoneInfo], output_file: str):
    """Экспорт зон в формат для MT5 EA."""
    mt5_data = []
    
    for z in zones:
        mt5_data.append({
            'id': z.zone_id,
            'type': 1 if z.type == 'bull' else -1,
            'start_time': z.start_time.strftime('%Y.%m.%d %H:%M'),
            'end_time': z.end_time.strftime('%Y.%m.%d %H:%M'),
            'start_bar': z.start_idx,
            'end_bar': z.end_idx,
            'bars': z.duration
        })
    
    df = pd.DataFrame(mt5_data)
    df.to_csv(output_file, index=False)
    
    print(f"Exported {len(zones)} zones to {output_file}")

# Использование
export_zones_to_mt5(zones, 'mt5_zones.csv')
```

#### Импорт зон из MT5

```python
def import_zones_from_mt5(mt5_file: str, ohlcv_data: pd.DataFrame) -> List[ZoneInfo]:
    """Импорт зон из MT5 формата."""
    from bquant.analysis.zones.detection.preloaded import PreloadedZonesDetection
    
    # Читаем MT5 формат
    mt5_df = pd.read_csv(mt5_file)
    
    # Конвертируем в стандартный формат
    zones_df = pd.DataFrame({
        'zone_id': mt5_df['id'],
        'type': mt5_df['type'].map({1: 'bull', -1: 'bear'}),
        'start_time': pd.to_datetime(mt5_df['start_time']),
        'end_time': pd.to_datetime(mt5_df['end_time'])
    })
    
    # Загружаем через PreloadedZonesDetection
    detector = PreloadedZonesDetection()
    config = ZoneDetectionConfig(
        strategy_name='preloaded',
        rules={'zones_data': zones_df}
    )
    
    return detector.detect_zones(ohlcv_data, config)

# Использование
zones = import_zones_from_mt5('mt5_expert_zones.csv', df)
```

---

## Заключение

### Ключевые возможности модульного использования

1. **Детекция без анализа** - получить только зоны
2. **Анализ готовых зон** - использовать внешние/preloaded зоны
3. **Частичный анализ** - только нужные компоненты (через DI)
4. **Пошаговое выполнение** - сохранение на каждом шаге
5. **Переиспользование результатов** - загрузка промежуточных данных
6. **Комбинирование стратегий** - сравнение разных детекций
7. **Интеграция с внешними системами** - импорт/экспорт в MT5, cTrader, etc.
8. **Feature engineering** - подготовка данных для ML
9. **Визуализация без анализа** - быстрый просмотр зон
10. **Кастомные pipeline** - построение своей логики из компонентов

### Преимущества

✅ **Гибкость** - используйте только то, что нужно  
✅ **Производительность** - не пересчитывайте лишнее  
✅ **Переиспользование** - сохраняйте промежуточные результаты  
✅ **Отладка** - проверяйте каждый шаг отдельно  
✅ **Интеграция** - легко встраивается в существующие системы  
✅ **Масштабируемость** - batch обработка с сохранением  

### API Summary

```python
# Уровень 1: Детекция
zones = detector.detect_zones(df, config)
zones = load_preloaded_zones(csv, df)

# Уровень 2: Признаки
features = features_analyzer.extract_all_zones_features(zones)

# Уровень 3: Статистика
stats = features_analyzer.analyze_zones_distribution(features)
hypotheses = hypothesis_suite.run_all_tests(features)
sequence = sequence_analyzer.analyze_zone_transitions(features)

# Уровень 4: Координация
result = analyzer.analyze_zones(zones, df)

# Уровень 5: Pipeline (опционально)
result = analyze_zones(df).detect_zones(...).build()
```

**Каждый уровень независим и может использоваться отдельно!**

---

**Дата создания:** 2025-10-17  
**Авторы:** AI Assistant (Claude Sonnet 4.5), Ivan  
**Версия:** v1.0  
**Статус:** Companion Guide to zonan.md

