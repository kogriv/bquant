# Структура результата анализа зон и экспорт в артефакты

> **Для кого этот документ**
>
> Руководство описывает **полную структуру объекта результата** пайплайна анализа зон (`ZoneAnalysisResult`), источники заполнения каждого поля, иерархию вложенных данных, а также **пошаговое получение артефактов** из списка [Best Practices](best_practices.md). Используйте его как единый справочник при работе с результатом и при разборке результата в файлы 01_…08_, full_analysis, summary.

## Связанные материалы

- [Best Practices анализа зон](best_practices.md) — рекомендуемая структура папок и файлов (01_…08_, full_analysis, summary).
- [Анализ зон на практике](zone_analysis.md) — выбор основы зоны, пять стратегий детекции, свинги.
- [Глубокое погружение: Пайплайн анализатора зон](../developer_guide/zone_analyzer_deep_dive.md) — логика шагов и стратегий.
- [API: analysis.zones](../api/analysis/zones.md) — технический справочник по API.

---

## 1. Источники результата

Объект `ZoneAnalysisResult` формируется в двух сценариях.

### 1.1. Пайплайн (рекомендуемый способ)

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag', shape='statistical', divergence='classic',
                     volume='standard', volatility='combined')
    .with_swing_preset('narrow_zone')
    .analyze(clustering=True, n_clusters=3, regression=False, validation=False)
    .build()
)

print(type(result).__name__, len(result.zones))   # ZoneAnalysisResult 83
```

`with_swing_preset('narrow_zone')` здесь можно и опустить — с 0.0.10 это умолчание.
Оставлено явным намеренно: пресет определяет, найдутся ли свинги вообще, и в примере,
который читают как образец, такие вещи лучше видеть — [Свинг-стратегии](swing_strategies.md).

**Этапы пайплайна и что они заполняют:**

| Этап | Метод/компонент | Что попадает в результат |
|------|------------------|--------------------------|
| Подготовка данных | `ZoneAnalysisPipeline._prepare_data()` → `IndicatorFactory.create()` | `result.data` — DataFrame с OHLCV и колонками индикатора |
| Детекция зон | `ZoneDetectionRegistry.get(strategy).detect_zones()` | `result.zones` — список `ZoneInfo`; у каждой зоны заполняются `data`, `indicator_context` |
| Глобальные свинги (если `swing_scope='global'`) | `_calculate_global_swings()` → стратегия свингов `.calculate_global()` | В каждую зону инжектируется `swing_context` (`SwingContext`) |
| Анализ зон | `UniversalZoneAnalyzer.analyze_zones()` | Заполняются `zone.features` у каждой зоны, а также `statistics`, `hypothesis_tests`, `sequence_analysis`, `clustering`, `regression_results`, `validation_results`, `metadata` |

### 1.2. Модульный способ

Если зоны получены отдельно (например, только детекция или preloaded):

```python
from bquant.analysis.zones import (
    UniversalZoneAnalyzer,
    ZoneDetectionConfig,
    ZoneDetectionRegistry,
)
from bquant.data.samples import get_sample_data

# Время на индекс кладём сами: отдельная стратегия, в отличие от пайплайна,
# кадр не нормализует, и `start_time` будет тем, что лежит в индексе.
df_prepared = get_sample_data('tv_xauusd_1h').set_index('time')

detector = ZoneDetectionRegistry.get('zero_crossing')
config = ZoneDetectionConfig(strategy_name='zero_crossing', rules={'indicator_col': 'macd'})
zones = detector.detect_zones(df_prepared, config)

analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df_prepared, perform_clustering=True, n_clusters=3)

print(len(result.zones), result.zones[0].start_time)
# 30 2025-06-11 20:00:00+07:00
```

Здесь колонка адресуется **именем**: роль (`indicator_role`) разрешается по схеме,
которую строит пайплайн, а без него схемы нет — `rules={'indicator_role': 'hist'}` даст
`ValueError: Missing required rules`.

При этом `result.data` — это переданный `df_prepared`; `result.zones` — тот же список `zones`, у которого анализатор заполнил `zone.features`.

---

## 2. Полная структура `ZoneAnalysisResult`

Тип: `bquant.analysis.zones.models.ZoneAnalysisResult` (dataclass).

| Поле | Тип | Обязательность | Источник (этап/компонент) | Описание |
|------|-----|----------------|----------------------------|----------|
| **zones** | `List[ZoneInfo]` | да | Детекция + анализ | Список зон; после анализа у каждой заполнены `data`, `features`, `indicator_context`, при global — `swing_context`. |
| **statistics** | `Dict[str, Any]` | да | `ZoneFeaturesAnalyzer.analyze_zones_distribution()` → `AnalysisResult.results` | Агрегированная статистика по зонам: total_statistics, duration_distribution, return_distribution, oscillator_amplitude_distribution, line_amplitude_distribution, additional_metrics. В `total_statistics` — `total_zones`, `zones_by_type`, `ratios_by_type` по фактически встреченным типам; `bull_zones_count`/`bear_zones_count`/`bull_ratio`/`bear_ratio` присутствуют **только** у словаря, который содержит эти типы. |
| **hypothesis_tests** | `Dict[str, Any]` | да | `HypothesisTestSuite.run_all_tests()` → `AnalysisResult.results` | Результаты тестов гипотез: `tests` (словарь тестов по имени: `p_value`, `significant`, `effect_size`, `metadata`; или `error`) и `summary` (`total_tests`, `tests_executed`, `tests_failed`, `significant_tests`, `significance_rate`, `alpha_level`, `total_zones`). Словарь, как и `statistics`: до 2026-09-04 здесь лежал сам объект `AnalysisResult`, и в JSON/Parquet он уезжал строкой (G56). |
| **clustering** | `Optional[Dict[str, Any]]` | нет | `ZoneSequenceAnalyzer.cluster_zones()` → `AnalysisResult.results` | Есть только при `analyze(clustering=True)` и при числе зон ≥ n_clusters. Ключи: clustering_summary, cluster_labels, clusters_analysis, feature_importance. |
| **sequence_analysis** | `Optional[Dict[str, Any]]` | нет | `ZoneSequenceAnalyzer.analyze_zone_transitions()` → `AnalysisResult.results` | Есть при числе зон ≥ 3. Переходы между типами зон (bull_to_bear и т.д.), вероятности, детали переходов. |
| **regression_results** | `Optional[Dict[str, Any]]` | нет | `ZoneRegressionAnalyzer` (predict_zone_duration, predict_price_return) → `RegressionResult.to_dict()` | Есть при `analyze(regression=True)` и числе зон > 10. Ключи: `duration`, `return`; под каждым — словарь модели (`r_squared`, `coefficients`, `p_values`, `predictions`, `residuals`, `n_observations`, `metadata`) или `{'error': …}`, если подгонка не удалась. |
| **validation_results** | `Optional[Dict[str, Any]]` | нет | Пайплайн → `ValidationSuite.out_of_sample_test()` | Есть при `analyze(validation=True)`, если проверка посчиталась: `{'out_of_sample': ModelValidationResult.to_dict()}` — частота зон на бар в окнах 70/30, `success`, `degradation_pct`. Что произошло, говорит `metadata['validation']`: `executed` / `failed` (с `reason`) / `not_requested`. |
| **data** | `Optional[pd.DataFrame]` | нет | Пайплайн: выход `_prepare_data()`; модульно: переданный DataFrame | Полный DataFrame с OHLCV и колонками индикаторов. Используется для визуализации и для доступа к «сырым» данным. |
| **metadata** | `Dict[str, Any]` | да (по умолчанию `{}`) | Собирается в `UniversalZoneAnalyzer.analyze_zones()`; `validation` дописывает пайплайн | analysis_timestamp, total_zones, zone_types, clustering_performed, regression_performed, duration_filter, validation (`status`); при наличии — swing_coverage, symbol, timeframe, source, dataset_name из `data.attrs`. |
| **column_schema** | `Optional[ColumnSchema]` | нет | Строится при расчёте индикатора в пайплайне | Карта «(индикатор, роль) → имя колонки»: `('custom.macd_12_26_9', 'hist') → 'macd_12_26_9__hist'` — ключ включает источник, чтобы custom-RSI и pandas-ta-RSI с одним slug не затирали друг друга (G58). Через неё разрешается `indicator_role`; при модульном вызове без пайплайна её нет — тогда колонки адресуются только именем. Методы: `column(indicator, role)`, `roles_of(column)`, `to_dict()`. |

### 2.1. Методы `ZoneAnalysisResult`

| Метод | Назначение |
|-------|------------|
| **save**(filepath, format='pickle', compress=False, include_data=True) | Сохранить результат целиком. Форматы: `pickle`, `json`, `parquet`. |
| **load**(filepath, format='pickle') | Классовый метод: загрузить результат из файла. |
| **to_dict**(include_data=False) | Словарь для JSON-сериализации: зоны (без `data`), `swing_contexts` — один раз на результат, кадр с индексом и типами при `include_data=True`. |
| **visualize**(mode, zone_id=None, date_range=None, symbol=None, timeframe=None, source=None, **kwargs) | Построение графиков: режимы `overview`, `detail`, `comparison`, `statistics`. Требует `result.data` и непустой `result.zones`. |

**Что переживает JSON и parquet (с 2026-09-04, G56).** Все три формата — полный раунд-трип
результата пайплайна: `statistics`, `hypothesis_tests`, `clustering`, `sequence_analysis`,
`regression_results`, `validation_results`, `metadata`, `column_schema`, зоны с признаками и
контекстом детекции, **свинг-контекст** (записывается один раз на результат, после загрузки
`zone.get_zone_swings()` отдаёт те же точки) и, при `include_data=True`, кадр `result.data` с
осью времени и типами колонок. `zone.data` в артефакт не пишется — это срез `result.data` по
`start_idx:end_idx + 1`, и при загрузке с кадром срезы восстанавливаются из него; без кадра
(`include_data=False`) у зон остаётся пустой `DataFrame`. Значения `numpy` (`np.float64`,
`np.bool_`) уезжают числами и булевыми; объект, которого JSON не знает, — `TypeError` с именем
типа, а не строка `repr`. До G56 `hypothesis_tests` уезжал строкой, `np.False_` — строкой
`"False"` (истинной!), свинг-контекст и ось времени терялись.

---

## 3. Полная структура `ZoneInfo` (элемент `result.zones`)

Тип: `bquant.analysis.zones.models.ZoneInfo` (dataclass).

| Поле | Тип | Описание |
|------|-----|----------|
| **zone_id** | `int` | Уникальный идентификатор зоны в рамках данного запуска. |
| **type** | `str` | Тип зоны: `'bull'`, `'bear'`, `'overbought'`, `'oversold'` и т.д. (зависит от стратегии детекции). |
| **start_idx**, **end_idx** | `int` | Индексы начала и конца зоны (iloc) в `result.data`. |
| **start_time**, **end_time** | `datetime` | Временные границы зоны (значения индекса DataFrame). |
| **duration** | `int` | Число баров в зоне. |
| **data** | `pd.DataFrame` | Срез `result.data` за период зоны: OHLCV и колонки индикаторов. |
| **features** | `Optional[Dict[str, Any]]` | Словарь признаков зоны; заполняется анализатором (см. раздел 4). |
| **indicator_context** | `Optional[Dict[str, Any]]` | Контекст детекции; заполняется стратегией детекции. Обязательные ключи: `detection_strategy`, `detection_indicator`; опционально: `signal_line`, `detection_rules`. |
| **swing_context** | `Optional[SwingContext]` | Заполняется только при `swing_scope='global'`. Используется в `get_zone_swings()`. |

Методы `ZoneInfo`:

- **get_zone_swings()** → `List[SwingPoint]` — свинги для зоны (из `swing_context` или пустой список).
- **get_primary_indicator_column()** → имя колонки индикатора из `indicator_context`.
- **get_signal_line_column()** → имя колонки сигнальной линии (если есть).
- **to_analyzer_format()** → словарь для передачи в анализаторы признаков.

Важно: у `ZoneInfo` нет отдельного атрибута `metadata`; все метаданные анализа зоны лежат в **`zone.features['metadata']`**.

---

## 4. Структура `zone.features` (признаки одной зоны)

Словарь `zone.features` формируется из `ZoneFeatures.to_dict()` и содержит поля уровня `ZoneFeatures` плюс вложенный ключ `metadata`.

### 4.1. Поля верхнего уровня (из `ZoneFeatures`)

Присутствие части полей зависит от наличия колонок в данных и от настроенных стратегий.

| Ключ | Тип | Описание |
|------|-----|----------|
| zone_id | int | Идентификатор зоны; то же значение, что в `ZoneInfo.zone_id`. |
| zone_type | str | Тип зоны ('bull', 'bear'). |
| duration | int | Длительность в барах. |
| start_price, end_price | float | Цена на первом и последнем баре зоны. |
| price_return | float | Доходность за зону (end/start - 1). |
| line_amplitude | float, optional | Амплитуда MACD (для MACD-зон, legacy). |
| oscillator_amplitude | float, optional | Амплитуда основного осциллятора (универсально для любого индикатора). |
| price_range_pct | float | Ценовой диапазон в процентах. |
| atr_normalized_return | float, optional | Доходность, нормализованная на ATR (если есть колонка atr). |
| correlation_price_oscillator | float, optional | Корреляция цены и основного индикатора. |
| num_peaks, num_troughs | int, optional | Количество пиков/впадин (find_peaks по high/low). |
| drawdown_from_peak | float, optional | Экскурсия цены от максимума зоны к её концу (`end/max - 1`, ≤ 0). Считается для **любой** зоны. |
| rally_from_trough | float, optional | Экскурсия цены от минимума зоны к её концу (`end/min - 1`, ≥ 0). Считается для **любой** зоны. |
| peak_time_ratio, trough_time_ratio | float, optional | Позиция максимума/минимума в зоне (0.0–1.0). Считаются для **любой** зоны. |
| oscillator_slope | float, optional | Максимальный наклон осциллятора в зоне. |
| **metadata** | **dict** | Вложенный словарь (см. ниже). |

### 4.2. Вложенный словарь `zone.features['metadata']`

Все перечисленные ниже ключи опциональны: их наличие зависит от стратегий и данных.

| Ключ | Описание |
|------|----------|
| data_points | Число баров в зоне. |
| start_timestamp, end_timestamp | Строковое представление времени начала/конца. |
| max_price, min_price, price_range | Ценовые экстремумы в зоне. |
| oscillator_name, oscillator_max/min/avg/std | Имя колонки осциллятора и его статистики (универсально). |
| line_max, line_min, line_avg, line_std, hist_max, hist_min, hist_avg, hist_std | Статистика по **ролям**, которые объявил индикатор и которые есть в кадре. Ключ — роль, а не имя индикатора: раньше здесь стояло `max_macd`, и на зонах RSI это означало бы то же самое, но врало бы именем. |
| atr_start, atr_end, avg_atr | При наличии atr. |
| **swing_calculation_mode** | `'global'` или `'per_zone'`. |
| **swing_metrics** | Словарь метрик свингов (если включена стратегия свингов). См. ниже. |
| **shape_metrics** | Словарь метрик формы (если включена shape-стратегия): hist_skewness, hist_kurtosis, hist_smoothness, strategy_name, strategy_params. |
| **divergence_metrics** | Словарь метрик дивергенций: divergence_type, divergence_count, divergence_strength, divergence_direction, strategy_name, strategy_params. |
| **volatility_metrics** | Словарь метрик волатильности: volatility_score, volatility_regime, bollinger_width_pct и др. **Часть величин может быть `None`** — это «не измерено», а не ноль: полосы Боллинджера считаются по окну `bb_length` (20), и в зоне короче окна боллинджеровских величин не существует, а ATR-часть при этом измерена. Вместе с `volatility_score` отсутствует и `volatility_regime`: композит по шкале 0–10 на две трети складывается из боллинджеровских компонент. У зон короче трёх баров группы нет вовсе. |
| **volume_metrics** | Словарь метрик объёма: avg_volume_zone, volume_indicator_corr и др. (при наличии колонки volume и стратегии). |

### 4.3. Содержимое `metadata['swing_metrics']`

Заполняется стратегией свингов (find_peaks, pivot_points, zigzag). Пример ключей:

- num_swings, rally_count, drop_count  
- avg_rally_pct, avg_drop_pct, max_rally_pct, max_drop_pct, min_rally_pct, min_drop_pct  
- rally_to_drop_ratio  
- rally_amplitude_std, drop_amplitude_std, rally_amplitude_median, drop_amplitude_median  
- avg_rally_duration_bars, avg_drop_duration_bars, max_rally_duration_bars, max_drop_duration_bars  
- avg_rally_speed_pct_per_bar, avg_drop_speed_pct_per_bar, max_rally_speed_pct_per_bar, max_drop_speed_pct_per_bar  
- duration_symmetry  
- strategy_name, strategy_params  

### 4.4. Пример доступа к признакам

```python
# Верхний уровень
duration = zone.features.get('duration')
price_return = zone.features.get('price_return')
num_peaks = zone.features.get('num_peaks')

# Метаданные и свинги
meta = zone.features.get('metadata') or {}
swing_metrics = meta.get('swing_metrics') or {}
rally_count = swing_metrics.get('rally_count')
avg_rally_pct = swing_metrics.get('avg_rally_pct')
rally_to_drop_ratio = swing_metrics.get('rally_to_drop_ratio')

# Режим расчёта свингов
swing_mode = meta.get('swing_calculation_mode')  # 'global' | 'per_zone'
```

---

## 5. Вспомогательные типы (в контексте результата)

### 5.1. SwingPoint (при использовании `zone.get_zone_swings()`)

- point_id, timestamp, index, price, swing_type ('peak' | 'trough')  
- amplitude_to_next, duration_to_next (optional)  
- strategy_name, strategy_params  

### 5.2. SwingContext (в `zone.swing_context`)

- swing_points: List[SwingPoint]  
- indices: np.ndarray (позиции свингов)  
- full_data_length, strategy_name, strategy_params  
- slice(start_idx, end_idx), get_swings_for_zone(zone)  

При сериализации в JSON/parquet `zone.data` не пишется: это срез `result.data`, и при загрузке с кадром (`include_data=True`) он восстанавливается из него; без кадра остаётся пустым. `swing_context` пишется один раз на результат (`swing_contexts`), зона хранит номер своего контекста; после загрузки `zone.get_zone_swings()` отдаёт те же точки, что до сохранения.

---

## 6. Соответствие полей результата и артефактам (Best Practices)

Рекомендуемая структура каталогов и файлов приведена в [Best Practices](best_practices.md). Ниже — явное соответствие «поле/источник в результате → артефакт».

| Артефакт | Поле/источник в результате | Примечание |
|----------|----------------------------|------------|
| **01_indicator_data.parquet** | `result.data` | Полный DataFrame (OHLCV + индикаторы). |
| **02_zones.pkl** | `result.zones` | Список `ZoneInfo` целиком (в т.ч. с `zone.data`, `zone.features`, `swing_context`). |
| **02_zones.csv** | Производное от `result.zones` | «Лёгкая» таблица: идентификатор, type, start_time, end_time, duration и т.п. без больших полей. Формат формируется вручную. |
| **03_features.csv** | `result.zones[i].features` по всем зонам | Таблица признаков: одна строка на зону; колонки — ключи из `zone.features` (при необходимости с развёрнутым `metadata`). |
| **04_statistics.json** | `result.statistics` | Словарь как есть. |
| **05_hypotheses.json** | `result.hypothesis_tests` | Словарь как есть (`tests`, `summary`). |
| **06_sequence.json** | `result.sequence_analysis` | Словарь как есть. |
| **07_clustering.json** | `result.clustering` | Словарь как есть. |
| **08_regression.json** | `result.regression_results` | Словарь как есть. |
| **full_analysis.pkl** | Весь объект `result` | `result.save('full_analysis.pkl')` — полный дамп. |
| **summary.json** | `result.metadata` + при необходимости выжимка из `result.statistics` | Отдельного поля в модели нет; схему summary задаёт пользователь. |
| **visualizations/** | — | Генерируются вызовами `result.visualize(...)`; в структуру результата не входят. |

---

## 7. Как получить артефакты: примеры кода

Предполагается, что `result` — уже полученный `ZoneAnalysisResult` (пайплайн или модульный вызов). Базовый каталог: `out_dir = Path('results/XAUUSD_1h')` (или `results/{instrument}_{timeframe}`).

### 7.1. 01_indicator_data.parquet

```python
if result.data is not None and not result.data.empty:
    result.data.to_parquet(out_dir / '01_indicator_data.parquet', index=True)
```

### 7.2. 02_zones.pkl

```python
import pickle

with open(out_dir / '02_zones.pkl', 'wb') as f:
    pickle.dump(result.zones, f)
```

### 7.3. 02_zones.csv (лёгкая мета-информация)

```python
import pandas as pd

rows = []
for z in result.zones:
    rows.append({
        'zone_id': z.zone_id,
        'type': z.type,
        'start_time': z.start_time,
        'end_time': z.end_time,
        'start_idx': z.start_idx,
        'end_idx': z.end_idx,
        'duration': z.duration,
    })
pd.DataFrame(rows).to_csv(out_dir / '02_zones.csv', index=False)
```

### 7.4. 03_features.csv

Признаки лежат в `zone.features`; у части ключей значения — вложенные словари (metadata). Для плоской таблицы можно взять только верхний уровень и при необходимости развернуть часть metadata.

```python
import pandas as pd

def zone_features_to_flat_row(z):
    feats = z.features or {}
    row = {k: v for k, v in feats.items() if k != 'metadata' and not isinstance(v, dict)}
    row['zone_id'] = z.zone_id
    row['type'] = z.type
    meta = feats.get('metadata') or {}
    if meta.get('swing_metrics'):
        sm = meta['swing_metrics']
        row['rally_count'] = sm.get('rally_count')
        row['drop_count'] = sm.get('drop_count')
        row['avg_rally_pct'] = sm.get('avg_rally_pct')
        row['avg_drop_pct'] = sm.get('avg_drop_pct')
        row['rally_to_drop_ratio'] = sm.get('rally_to_drop_ratio')
    if meta.get('swing_calculation_mode'):
        row['swing_calculation_mode'] = meta['swing_calculation_mode']
    return row

rows = [zone_features_to_flat_row(z) for z in result.zones]
pd.DataFrame(rows).to_csv(out_dir / '03_features.csv', index=False)
```

Альтернатива: сохранять полный `zone.features` в виде строки JSON по строкам или нормализовать вложенные словари (например, через `pd.json_normalize`).

### 7.5. 04_statistics.json, 05_hypotheses.json, 06_sequence.json, 07_clustering.json, 08_regression.json

```python
import json

def save_json(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, default=str, ensure_ascii=False)

save_json(result.statistics, out_dir / '04_statistics.json')

save_json(result.hypothesis_tests, out_dir / '05_hypotheses.json')

if result.sequence_analysis is not None:
    save_json(result.sequence_analysis, out_dir / '06_sequence.json')
if result.clustering is not None:
    save_json(result.clustering, out_dir / '07_clustering.json')
if result.regression_results is not None:
    save_json(result.regression_results, out_dir / '08_regression.json')
```

### 7.6. full_analysis.pkl

```python
result.save(out_dir / 'full_analysis.pkl', format='pickle', include_data=True)
# или с сжатием:
result.save(out_dir / 'full_analysis.pkl.gz', format='pickle', compress=True, include_data=True)
```

### 7.7. summary.json

```python
from collections import Counter

summary = {
    **result.metadata,
    'zones_count': len(result.zones),
    # То же распределение есть в result.statistics['total_statistics']['zones_by_type'];
    # здесь считаем сами, чтобы сводка не зависела от того, включались ли агрегаты.
    'zones_by_type': dict(Counter(zone.type for zone in result.zones)),
}
save_json(summary, out_dir / 'summary.json')
```

### 7.8. Визуализации

```python
# Требуют result.data и result.zones
fig_overview = result.visualize('overview', title='Zones overview')
fig_overview.write_html(out_dir / 'visualizations' / 'overview.html')

fig_detail = result.visualize('detail', zone_id=result.zones[0].zone_id, context_bars=30)
fig_detail.write_html(out_dir / 'visualizations' / 'zone_0_detail.html')

fig_cmp = result.visualize('comparison', max_zones=4)
fig_cmp.write_html(out_dir / 'visualizations' / 'zones_comparison.html')
```

(Имена файлов и способ сохранения фигуры зависят от backend визуализатора — Plotly/Matplotlib; здесь приведён пример для Plotly.)

### 7.9. Полный скрипт экспорта

```python
from pathlib import Path
from tempfile import mkdtemp
import json
import pickle
import pandas as pd
from bquant.analysis.zones import analyze_macd_zones
from bquant.analysis.zones.models import ZoneAnalysisResult
from bquant.data.samples import get_sample_data

def export_result_to_artifacts(result: ZoneAnalysisResult, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if result.data is not None and not result.data.empty:
        result.data.to_parquet(out_dir / '01_indicator_data.parquet', index=True)

    with open(out_dir / '02_zones.pkl', 'wb') as f:
        pickle.dump(result.zones, f)

    zones_meta = [{'zone_id': z.zone_id, 'type': z.type, 'start_time': z.start_time,
                   'end_time': z.end_time, 'duration': z.duration} for z in result.zones]
    pd.DataFrame(zones_meta).to_csv(out_dir / '02_zones.csv', index=False)

    def flat_row(z):
        feats = z.features or {}
        row = {k: v for k, v in feats.items() if k != 'metadata' and not isinstance(v, dict)}
        row['zone_id'], row['type'] = z.zone_id, z.type
        meta = feats.get('metadata') or {}
        for key in ('swing_calculation_mode', 'swing_metrics'):
            if key in meta:
                row[key] = meta[key]
        return row
    pd.DataFrame([flat_row(z) for z in result.zones]).to_csv(out_dir / '03_features.csv', index=False)

    def j(obj, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2, default=str, ensure_ascii=False)

    j(result.statistics, out_dir / '04_statistics.json')
    j(result.hypothesis_tests, out_dir / '05_hypotheses.json')
    if result.sequence_analysis is not None:
        j(result.sequence_analysis, out_dir / '06_sequence.json')
    if result.clustering is not None:
        j(result.clustering, out_dir / '07_clustering.json')
    if result.regression_results is not None:
        j(result.regression_results, out_dir / '08_regression.json')

    result.save(out_dir / 'full_analysis.pkl', format='pickle', include_data=True)

    summary = {**result.metadata, 'zones_count': len(result.zones)}
    j(summary, out_dir / 'summary.json')

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))
out_dir = Path(mkdtemp())            # в работе — results/XAUUSD_1h
export_result_to_artifacts(result, out_dir)

print(sorted(p.name for p in out_dir.iterdir()))
# ['01_indicator_data.parquet', '02_zones.csv', '02_zones.pkl', '03_features.csv',
#  '04_statistics.json', '05_hypotheses.json', '06_sequence.json', '07_clustering.json',
#  'full_analysis.pkl', 'summary.json']
```

---

## 8. Загрузка сохранённого результата

```python
from pathlib import Path
from tempfile import mkdtemp

from bquant.analysis.zones import analyze_macd_zones
from bquant.analysis.zones.models import ZoneAnalysisResult
from bquant.data.samples import get_sample_data

out_dir = Path(mkdtemp())
analyze_macd_zones(get_sample_data('tv_xauusd_1h')).save(out_dir / 'full_analysis.pkl')

result = ZoneAnalysisResult.load(out_dir / 'full_analysis.pkl', format='pickle')

print(len(result.zones), result.data is not None, len(result.zones[0].data))
# 32 True 3
```

Из JSON результат читается тем же методом (`format='json'`). Сохранённый с
`include_data=True`, он возвращается с кадром, осью времени и срезами `zone.data`; сохранённый
без кадра — с `result.data = None` и пустыми `zone.data`, но со свингами и всеми разделами.

> **Важно (с 2026-08-24).** Четыре метрики — `drawdown_from_peak`, `rally_from_trough`,
> `peak_time_ratio`, `trough_time_ratio` — считаются для **каждой** зоны, независимо от её
> типа. Раньше они были привязаны к имени типа: у `bull`-зоны заполнялись две из четырёх,
> у `bear` — другие две, а у зоны с любым другим именем (`overbought`, `regime_a`, …) —
> ни одной. Ветвление не считало их по-разному, оно их отбрасывало: все четыре выводятся
> из цены закрытия зоны и её экстремумов и определены всегда.
>
> Какая из четырёх содержательна — решает потребитель по объявленной **полярности** типа
> зоны (`ZoneVocabulary.polarity_of`, см. [zones.md](../api/analysis/zones.md)): у
> приподнятой зоны говорящая величина — просадка от пика, у подавленной — отскок от
> минимума.
>
> **Побочное следствие, о котором стоит знать при сравнении со старыми результатами.**
> `ZoneRegressionAnalyzer.predict_price_return` включает `drawdown_from_peak` в набор
> предикторов по умолчанию и отбрасывает строки с пропусками. Пока метрика была только у
> `bull`-зон, модель молча обучалась **на половине выборки**: 33 зоны из 72 на встроенном
> сэмпле, с R² = 0.863. Теперь обучается на 66 из 72, и R² = 0.699. Прежнее число было
> завышено не потому, что модель была лучше, а потому, что описывало половину данных,
> выдавая это за описание всех зон.
