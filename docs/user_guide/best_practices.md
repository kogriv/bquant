# Практика: паттерны и артефакты

Приёмы, которые окупаются, когда анализ перестаёт быть разовым: как не пересчитывать
одно и то же, где хранить результаты и что отдавать наружу.

## Пайплайн или сборка вручную

**`analyze_zones(...).build()`** — когда нужен обычный анализ от начала до конца, и
промежуточные шаги не интересуют. Одна цепочка возвращает `ZoneAnalysisResult`.

**Компоненты по отдельности** (`IndicatorFactory`, стратегии детекции,
`UniversalZoneAnalyzer`) — когда:

- нужно остановиться на промежуточном шаге, например только на детекции;
- одни и те же зоны анализируются многократно с разными настройками;
- между шагами вставляется своя логика;
- зоны приходят снаружи и пересчитывать индикатор незачем;
- поверх признаков строится ML или своя статистика, а не отчёт.

Цена ручной сборки — то, что пайплайн делает молча: перенос времени на индекс и схему
колонок (роли вместо имён). См. [Анализ зон на практике](zone_analysis.md).

## Считать один раз, анализировать много

Детекция дешевле анализа, а зоны от настроек анализа не зависят. Разделите их:

```python
from bquant.analysis.zones import UniversalZoneAnalyzer, ZoneDetectionConfig, ZoneDetectionRegistry
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h').set_index('time')

# Один раз: границы зон
detector = ZoneDetectionRegistry.get('zero_crossing')
zones = detector.detect_zones(data, ZoneDetectionConfig(rules={'indicator_col': 'macd'}))

# Много раз: разные настройки анализа поверх тех же зон
for n_clusters in (2, 3, 4):
    result = UniversalZoneAnalyzer().analyze_zones(zones, data, n_clusters=n_clusters)
    quality = result.clustering['clustering_summary']['clustering_quality']
    print(n_clusters, round(quality['silhouette_score'], 3))
# 2 0.467
# 3 0.415
# 4 0.434
```

Один список зон, три анализа. Обратите внимание: `analyze_zones()` **дописывает**
`features` в те же объекты `ZoneInfo`, так что список после первого прохода уже не
«чистый» — если нужна независимость прогонов, детектируйте заново или делайте
`copy.deepcopy`.

## Признаки — в таблицу, дальше своими средствами

```python
import pandas as pd

from bquant.analysis.zones import analyze_macd_zones
from bquant.data.samples import get_sample_data

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

features = pd.DataFrame([
    {k: v for k, v in (zone.features or {}).items() if k != 'metadata'}
    for zone in result.zones
])

print(features.shape, list(features.columns[:5]))
# (32, 20) ['zone_id', 'zone_type', 'duration', 'start_price', 'end_price']
```

Дальше это обычный `DataFrame` — ML, статистика, BI. Вложенные метрики стратегий лежат в
`features['metadata']` и разворачиваются отдельно; как именно — в
[Структуре результата](zone_analysis_result.md).

## Структура артефактов

Единообразная иерархия окупается на второй же неделе:

```
results/
└── {instrument}_{timeframe}/
    ├── 01_indicator_data.parquet    # данные с индикаторами (result.data)
    ├── 02_zones.pkl                 # объекты ZoneInfo целиком
    ├── 02_zones.csv                 # лёгкая мета: границы, тип, длительность
    ├── 03_features.csv              # признаки зон
    ├── 04_statistics.json           # распределения и агрегаты
    ├── 05_hypotheses.json           # гипотезы и p-value
    ├── 06_sequence.json             # переходы между зонами
    ├── 07_clustering.json           # кластеризация
    ├── 08_regression.json           # модели прогноза, если считались
    ├── full_analysis.pkl            # весь ZoneAnalysisResult
    ├── summary.json                 # краткая сводка
    └── visualizations/
        ├── overview.html
        ├── zone_3_detail.html
        └── zones_comparison.html
```

Готовая функция экспорта, которая раскладывает результат именно так, — в
[Структуре результата](zone_analysis_result.md), раздел «Полный скрипт экспорта».

## Версии результатов

```python
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp

from bquant.analysis.zones import analyze_macd_zones
from bquant.data.samples import get_sample_data

out_dir = Path(mkdtemp())
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))
result.save(out_dir / f'analysis_{stamp}.pkl')

latest = out_dir / 'analysis_latest.pkl'
latest.unlink(missing_ok=True)
latest.symlink_to(out_dir / f'analysis_{stamp}.pkl')

print(latest.is_symlink(), latest.resolve().name.startswith('analysis_'))
# True True
```

Ссылка на «последний» результат снимает с интеграций необходимость знать про метку
времени. На Windows создание симлинка требует прав — там надёжнее копия или файл-указатель
с именем.

## Что помнить при интеграции

- **Отдать зоны наружу (MT5, cTrader, свои скрипты).** Достаточно CSV с колонками
  `zone_id`, `type`, `start_time`, `end_time` — в этом же формате их читает обратно
  стратегия `preloaded`. Круг замыкается: выгруженное можно вернуть в анализ.
- **Принять зоны снаружи.** `detect_zones('preloaded', zones_data=...)` — и дальше всё как
  обычно; словарь типов при этом ваш, пайплайн на имена типов не смотрит.
- **Не предполагать `bull`/`bear`.** В `total_statistics` универсальный ответ —
  `zones_by_type`; поля `bull_*`/`bear_*` есть только у словаря, который эти типы
  содержит. Программе, читающей сводку, проверять надо наличие ключа, а не его значение.
- **Сравнивать стратегии можно с включённым кэшем.** Ключ различает и стратегию, и её
  параметры; см. [Кэширование](caching.md). До версии схемы 16 не различал.

## Связанные материалы

| | |
|---|---|
| [Структура результата](zone_analysis_result.md) | поля результата и готовый экспорт в артефакты |
| [Анализ зон на практике](zone_analysis.md) | выбор основы зоны и стратегии детекции |
| [Кэширование](caching.md) | ключи, инвалидация, когда выключать |
| [Pipeline API](../api/analysis/pipeline.md) | справочник билдера |
