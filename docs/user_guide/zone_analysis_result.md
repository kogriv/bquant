# Структура результата анализа зон и экспорт в артефакты

> **Для кого этот документ**
>
> Руководство описывает **полную структуру объекта результата** пайплайна анализа зон (`ZoneAnalysisResult`), источники заполнения каждого поля, иерархию вложенных данных, а также **пошаговое получение артефактов** из списка [Best Practices](best_practices.md). Используйте его как единый справочник при работе с результатом и при разборке результата в файлы 01_…08_, full_analysis, summary.

## Связанные материалы

- [Best Practices анализа зон](best_practices.md) — рекомендуемая структура папок и файлов (01_…08_, full_analysis, summary).
- [Zone Analysis Guide](zone_analysis.md) — полный пайплайн, архитектура, примеры вызова.
- [Глубокое погружение: Пайплайн анализатора зон](../developer_guide/zone_analyzer_deep_dive.md) — логика шагов и стратегий.
- [API: analysis.zones](../api/analysis/zones.md) — технический справочник по API.

---

## 1. Источники результата

Объект `ZoneAnalysisResult` формируется в двух сценариях.

### 1.1. Пайплайн (рекомендуемый способ)

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag', shape='statistical', divergence='classic', volume='standard', volatility='combined')
    .analyze(clustering=True, n_clusters=3, regression=False, validation=False)
    .build()
)
# result — ZoneAnalysisResult
```

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
from bquant.analysis.zones import ZoneDetectionRegistry, ZoneDetectionConfig, UniversalZoneAnalyzer

detector = ZoneDetectionRegistry.get('zero_crossing')
config = ZoneDetectionConfig(strategy_name='zero_crossing', rules={'indicator_col': 'macd_hist'}, min_duration=2)
zones = detector.detect_zones(df_prepared, config)

analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df_prepared, perform_clustering=True, n_clusters=3)
# result — тот же ZoneAnalysisResult
```

При этом `result.data` — это переданный `df_prepared`; `result.zones` — тот же список `zones`, у которого анализатор заполнил `zone.features`.

---

## 2. Полная структура `ZoneAnalysisResult`

Тип: `bquant.analysis.zones.models.ZoneAnalysisResult` (dataclass).

| Поле | Тип | Обязательность | Источник (этап/компонент) | Описание |
|------|-----|----------------|----------------------------|----------|
| **zones** | `List[ZoneInfo]` | да | Детекция + анализ | Список зон; после анализа у каждой заполнены `data`, `features`, `indicator_context`, при global — `swing_context`. |
| **statistics** | `Dict[str, Any]` | да | `ZoneFeaturesAnalyzer.analyze_zones_distribution()` → `AnalysisResult.results` | Агрегированная статистика по зонам: total_statistics, duration_distribution, return_distribution, hist_amplitude_distribution (или macd_amplitude_distribution), additional_metrics. |
| **hypothesis_tests** | `Dict[str, Any]` или объект с атрибутом `.results` | да | `HypothesisTestSuite.run_all_tests()` | Результаты тестов гипотез. Если объект — у него есть `.results` с ключами `tests` (словарь тестов по имени) и `summary`. В коде часто: `getattr(result.hypothesis_tests, 'results', result.hypothesis_tests)`. |
| **clustering** | `Optional[Dict[str, Any]]` | нет | `ZoneSequenceAnalyzer.cluster_zones()` → `AnalysisResult.results` | Есть только при `analyze(clustering=True)` и при числе зон ≥ n_clusters. Ключи: clustering_summary, cluster_labels, clusters_analysis, feature_importance. |
| **sequence_analysis** | `Optional[Dict[str, Any]]` | нет | `ZoneSequenceAnalyzer.analyze_zone_transitions()` → `AnalysisResult.results` | Есть при числе зон ≥ 3. Переходы между типами зон (bull_to_bear и т.д.), вероятности, детали переходов. |
| **regression_results** | `Optional[Dict[str, Any]]` | нет | `ZoneRegressionAnalyzer` (predict_zone_duration, predict_price_return) | Есть при `analyze(regression=True)` и числе зон > 10. Ключи: `duration`, `return` (модели/предсказания). |
| **validation_results** | `Optional[Dict[str, Any]]` | нет | `ValidationSuite` | Есть при `analyze(validation=True)` и числе зон > 20; в текущей реализации может не выполняться. |
| **data** | `Optional[pd.DataFrame]` | нет | Пайплайн: выход `_prepare_data()`; модульно: переданный DataFrame | Полный DataFrame с OHLCV и колонками индикаторов. Используется для визуализации и для доступа к «сырым» данным. |
| **metadata** | `Dict[str, Any]` | да (по умолчанию `{}`) | Собирается в `UniversalZoneAnalyzer.analyze_zones()` | analysis_timestamp, total_zones, zone_types, clustering_performed, regression_performed; при наличии — symbol, timeframe, source, dataset_name из `data.attrs`. |

### 2.1. Методы `ZoneAnalysisResult`

| Метод | Назначение |
|-------|------------|
| **save**(filepath, format='pickle', compress=False, include_data=True) | Сохранить результат целиком. Форматы: `pickle`, `json`, `parquet`. |
| **load**(filepath, format='pickle') | Классовый метод: загрузить результат из файла. |
| **to_dict**(include_data=False) | Словарь для JSON-сериализации; зоны сериализуются через `_zone_to_dict` (без `zone.data`). |
| **visualize**(mode, zone_id=None, date_range=None, symbol=None, timeframe=None, source=None, **kwargs) | Построение графиков: режимы `overview`, `detail`, `comparison`, `statistics`. Требует `result.data` и непустой `result.zones`. |

При сохранении в JSON/parquet поле `zone.data` в зонах не включается (слишком большой объём); при pickle по умолчанию сохраняется весь объект, включая `result.data` и `zone.data` у каждой зоны.

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
| zone_id | str/int | Идентификатор зоны. |
| zone_type | str | Тип зоны ('bull', 'bear'). |
| duration | int | Длительность в барах. |
| start_price, end_price | float | Цена на первом и последнем баре зоны. |
| price_return | float | Доходность за зону (end/start - 1). |
| macd_amplitude | float, optional | Амплитуда MACD (для MACD-зон, legacy). |
| hist_amplitude | float, optional | Амплитуда основного осциллятора (универсально для любого индикатора). |
| price_range_pct | float | Ценовой диапазон в процентах. |
| atr_normalized_return | float, optional | Доходность, нормализованная на ATR (если есть колонка atr). |
| correlation_price_hist | float, optional | Корреляция цены и основного индикатора. |
| num_peaks, num_troughs | int, optional | Количество пиков/впадин (find_peaks по high/low). |
| drawdown_from_peak | float, optional | Просадка от пика (для бычьих зон). |
| rally_from_trough | float, optional | Отскок от минимума (для медвежьих зон). |
| peak_time_ratio, trough_time_ratio | float, optional | Позиция пика/впадины в зоне (0.0–1.0). |
| hist_slope | float, optional | Максимальный наклон осциллятора в зоне. |
| **metadata** | **dict** | Вложенный словарь (см. ниже). |

### 4.2. Вложенный словарь `zone.features['metadata']`

Все перечисленные ниже ключи опциональны: их наличие зависит от стратегий и данных.

| Ключ | Описание |
|------|----------|
| data_points | Число баров в зоне. |
| start_timestamp, end_timestamp | Строковое представление времени начала/конца. |
| max_price, min_price, price_range | Ценовые экстремумы в зоне. |
| oscillator_name, oscillator_max/min/avg/std | Имя колонки осциллятора и его статистики (универсально). |
| max_macd, min_macd, macd_amplitude, avg_hist, hist_std и т.д. | При наличии колонок MACD — доп. метрики. |
| atr_start, atr_end, avg_atr | При наличии atr. |
| **swing_calculation_mode** | `'global'` или `'per_zone'`. |
| **swing_metrics** | Словарь метрик свингов (если включена стратегия свингов). См. ниже. |
| **shape_metrics** | Словарь метрик формы (если включена shape-стратегия): hist_skewness, hist_kurtosis, hist_smoothness, strategy_name, strategy_params. |
| **divergence_metrics** | Словарь метрик дивергенций: divergence_type, divergence_count, divergence_strength, divergence_direction, strategy_name, strategy_params. |
| **volatility_metrics** | Словарь метрик волатильности: volatility_score, volatility_regime, bollinger_width_pct и др. |
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

При сериализации результата в JSON/parquet поле `zone.data` в каждой зоне не сохраняется; при загрузке из JSON/parquet у зон восстанавливается пустой DataFrame. Поле `swing_context` при сериализации через `_zone_to_dict` не включается (в текущей реализации в словарь зоны попадают zone_id, type, start_idx, end_idx, start_time, end_time, duration, features, indicator_context).

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
| **05_hypotheses.json** | `result.hypothesis_tests` или `getattr(result.hypothesis_tests, 'results', result.hypothesis_tests)` | Рекомендуется сохранять `.results`, если тип — объект с атрибутом `results`. |
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

# hypothesis_tests может быть объектом с .results
ht = getattr(result.hypothesis_tests, 'results', result.hypothesis_tests)
save_json(ht, out_dir / '05_hypotheses.json')

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
summary = {
    **result.metadata,
    'zones_count': len(result.zones),
}
if result.statistics and isinstance(result.statistics, dict):
    total = result.statistics.get('total_statistics') or {}
    summary['bull_zones'] = total.get('bull_zones_count')
    summary['bear_zones'] = total.get('bear_zones_count')
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
import json
import pickle
import pandas as pd
from bquant.analysis.zones.models import ZoneAnalysisResult

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
    j(getattr(result.hypothesis_tests, 'results', result.hypothesis_tests), out_dir / '05_hypotheses.json')
    if result.sequence_analysis is not None:
        j(result.sequence_analysis, out_dir / '06_sequence.json')
    if result.clustering is not None:
        j(result.clustering, out_dir / '07_clustering.json')
    if result.regression_results is not None:
        j(result.regression_results, out_dir / '08_regression.json')

    result.save(out_dir / 'full_analysis.pkl', format='pickle', include_data=True)

    summary = {**result.metadata, 'zones_count': len(result.zones)}
    j(summary, out_dir / 'summary.json')

# Использование:
# export_result_to_artifacts(result, Path('results/XAUUSD_1h'))
```

---

## 8. Загрузка сохранённого результата

```python
from bquant.analysis.zones.models import ZoneAnalysisResult

# Полный результат из pickle
result = ZoneAnalysisResult.load('results/XAUUSD_1h/full_analysis.pkl', format='pickle')

# Из JSON (без DataFrame)
result = ZoneAnalysisResult.load('results/XAUUSD_1h/full_analysis.json', format='json')
# result.data будет None, если не был сохранён в JSON
```

После загрузки из JSON или parquet у зон в `zone.data` будет пустой DataFrame; при необходимости его можно восстановить по `result.data` и `zone.start_idx`/`zone.end_idx`, если сохраняли 01_indicator_data.parquet отдельно.
