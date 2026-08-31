# Анализ зон на практике

Страница о решениях, которые принимает аналитик: по чему проводить границу зоны, какой
стратегией её искать и почему две настройки одного и того же индикатора дают разное
число зон.

Что описано в других местах и здесь не повторяется:

| | |
|---|---|
| [Структура результата](zone_analysis_result.md) | поля `ZoneAnalysisResult` и `ZoneInfo`, выгрузка |
| [Pipeline API](../api/analysis/pipeline.md) | справочник всех методов билдера и их параметров |
| [Свинг-стратегии](swing_strategies.md) | выбор алгоритма поиска экстремумов и его настройка |
| [Кэширование](caching.md) | ключи, инвалидация, два уровня |
| [Zone Analyzer Deep Dive](../developer_guide/zone_analyzer_deep_dive.md) | устройство внутри: как это работает в коде |

## Порядок вычислений

1. **Индикатор.** Считается пайплайном (тогда колонки получают канонические имена и
   адресуются ролью) или приносится готовым в кадре.
2. **Детекция.** Одна из пяти стратегий размечает **всю** область определения
   индикатора: зоны идут встык, без дыр. Порога длительности на этом шаге нет
   намеренно — отсев коротких зон рвёт мощение, и соседство зон становится выдумкой.
3. **Признаки.** Для каждой зоны — амплитуда, длительность, форма, свинги, дивергенции,
   волатильность, объём. Набор зависит от того, какие стратегии метрик включены.
4. **Агрегаты.** Распределения, гипотезы, последовательности, при желании —
   кластеризация, регрессия, валидация. Вот здесь работает `min_duration`: короткие зоны
   остаются в `result.zones`, но не входят в статистику, и сколько их — записано в
   `result.metadata['duration_filter']`.

## Решение первое: по чему проведена граница

Один и тот же MACD на одних и тех же данных даёт разное число зон в зависимости от того,
что взято за основу:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones

data = get_sample_data('tv_xauusd_1h')

by_line = analyze_macd_zones(data)                            # zone_basis='line' — умолчание
by_hist = analyze_macd_zones(data, zone_basis='histogram')

print(len(by_line.zones), len(by_hist.zones))   # 32 83
```

Линия MACD меняет знак редко — зоны получаются длинными и устойчивыми. Гистограмма
(разность линии и сигнальной) меняет знак втрое чаще — зоны короче и их больше. Ни один
из ответов не «правильнее»: **выбор основы — это выбор вопроса**. Держите его явным,
потому что дальше от него зависит всё: длительность, амплитуда, число свингов в зоне.

## Пять стратегий детекции

### `zero_crossing` — пересечение нуля

Для осцилляторов с нулевой линией: MACD, AO, CCI, momentum.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .analyze()
    .build()
)

print(len(result.zones))   # 32
```

Значение выше нуля — `bull`, ниже — `bear`, пересечение — граница.

### `threshold` — пороги

Для ограниченных осцилляторов: RSI, Stochastic, Williams %R.

```python
from collections import Counter

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze()
    .build()
)

print(Counter(zone.type for zone in result.zones))
# Counter({'neutral': 32, 'oversold': 18, 'overbought': 14})
```

Область между порогами — не пробел, а собственный тип `neutral`: мощение остаётся полным.

### `line_crossing` — пересечение двух линий

Для пар: MACD/сигнальная, быстрая/медленная скользящая, %K/%D.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('line_crossing', line1_role='line', line2_role='signal')
    .analyze()
    .build()
)

print(len(result.zones))   # 83
```

Восемьдесят три — ровно столько же, сколько даёт `zero_crossing` по гистограмме, и это не
совпадение: гистограмма MACD и есть разность этих двух линий. Одни и те же зоны, два
способа их назвать; выбирайте тот, что честнее описывает вашу гипотезу.

### `preloaded` — зоны пришли снаружи

Разметка эксперта, зоны из другой системы, результат прошлого прогона. Ожидаются колонки
`zone_id`, `type`, `start_time`, `end_time`; источник — CSV, Excel или `DataFrame`.

```python
import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')
time = pd.to_datetime(data['time'])

external = pd.DataFrame({
    'zone_id': [0, 1],
    'type': ['accumulation', 'distribution'],
    'start_time': [time.iloc[10], time.iloc[300]],
    'end_time': [time.iloc[120], time.iloc[420]],
})

result = (
    analyze_zones(data)
    .detect_zones('preloaded', zones_data=external)
    .analyze()
    .build()
)

print([(zone.type, zone.duration) for zone in result.zones])
# [('accumulation', 111), ('distribution', 121)]
```

Словарь типов здесь ваш: `accumulation`/`distribution` анализируются наравне с
`bull`/`bear`, потому что пайплайн на имена типов не смотрит.

### `combined` — несколько условий

`conditions` — список **функций**, каждая принимает кадр и возвращает булеву серию.

```python
from collections import Counter

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones(
        'combined',
        conditions=[
            lambda df: df['RSI_14'] > 55,
            lambda df: df['close'] > df['close'].rolling(50).mean(),
        ],
        logic='AND',
        zone_type_map={True: 'strong', False: 'weak'},
    )
    .analyze()
    .build()
)

print(Counter(zone.type for zone in result.zones))
# Counter({'weak': 47, 'strong': 46})
```

**Своему словарю типов — своя цена.** Два теста гипотез (`contrast_asymmetry` и
`correlation_drawdown`) требуют, чтобы у типов была объявлена противоположность и
полярность; для пары `strong`/`weak` их нет, и тесты **отказываются, называя причину**, а
не возвращают правдоподобное число. В `result.hypothesis_tests` у них будет `error`
вместо `p_value`.

## Зона знает, как она была найдена

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze()
    .build()
)

print(result.zones[0].indicator_context)
# {'detection_strategy': 'zero_crossing',
#  'detection_indicator': 'macd_12_26_9__hist',
#  'signal_line': None,
#  'detection_rules': {'indicator_col': 'macd_12_26_9__hist'}}
```

Благодаря этому стратегии метрик берут **тот самый** индикатор, по которому зона
размечена, а не угадывают его по имени колонки.

## Любой индикатор, включая ваш собственный

Схемы у чужой колонки нет, поэтому адресуемся именем:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h').copy()
data['my_oscillator'] = data['close'].diff(5) / data['close'].rolling(20).std()

result = (
    analyze_zones(data)
    .detect_zones('zero_crossing', indicator_col='my_oscillator')
    .with_strategies(swing='zigzag')
    .analyze()
    .build()
)

print(len(result.zones))   # 237
```

Ни строчки в BQuant для этого менять не нужно.

## Свинги: пресет решает больше, чем стратегия

Свинг-метрики зоны лежат в `zone.features['metadata']['swing_metrics']`, точки —
в `zone.get_zone_swings()`. Две настройки влияют на результат сильнее прочих:

- **`.with_swing_scope()`** — где искать пивоты: `global` (умолчание) считает их один раз
  на всём кадре и нарезает по зонам, сохраняя соседние точки; `per_zone` считает внутри
  каждой зоны отдельно и теряет экстремумы на границах.
- **`.with_swing_preset()`** — с какими порогами. Пресетов два: `default` и
  `narrow_zone`. **Умолчание рассчитано на широкие зоны**, и на типичных MACD-зонах
  часового золота две стратегии из трёх не находят при нём ничего:

| Стратегия | `default`, `per_zone` | `default`, `global` | `narrow_zone`, `per_zone` | `narrow_zone`, `global` |
|---|---|---|---|---|
| `zigzag` | 12/32 | 26/32 | 23/32 | **29/32** |
| `find_peaks` | 0/32 | 0/32 | 14/32 | 20/32 |
| `pivot_points` | 0/32 | 2/32 | 10/32 | 23/32 |

Доля зон, у которых нашёлся хотя бы один свинг; 32 зоны MACD по линии на `tv_xauusd_1h`.

Ноль в этой таблице **не сообщает о себе**: `num_swings: 0` выглядит так же, как честно
измеренное отсутствие движения. Если свинг-метрики пустые у всех зон — проверьте пресет
прежде, чем делать выводы о рынке. Разбор:
`devref/gaps/swing/g35_default_preset_measures_nothing_and_says_nothing_2026-08.md`.

Подробности выбора и настройки — [Свинг-стратегии](swing_strategies.md).

## Детекция без анализа

Стратегии доступны отдельно от пайплайна — когда нужны только границы:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.detection import ZoneDetectionConfig, ZoneDetectionRegistry

# Время на индекс здесь кладём сами — см. ниже, почему.
data = get_sample_data('tv_xauusd_1h').set_index('time')

detector = ZoneDetectionRegistry.get('zero_crossing')
config = ZoneDetectionConfig(rules={'indicator_col': 'macd'})

zones = detector.detect_zones(data, config)
print(len(zones), zones[0].type, zones[0].start_time)
# 30 bull 2025-06-11 20:00:00+07:00
```

Две вещи, которые пайплайн делает за вас, а здесь придётся сделать самому.

**Колонка адресуется именем, а не ролью.** Роль разрешается по схеме индикатора, которую
строит пайплайн; без пайплайна схемы нет, и `rules={'indicator_role': 'hist'}` даёт
`ValueError: Missing required rules`.

**Время на индекс кладёте вы.** `ZoneInfo.start_time` — это значение индекса, каким его
дали. Передадите кадр с позиционным индексом — получите `start_time = 0`: поле честное,
вход не тот. Пайплайн переносит время из колонки сам, отдельная стратегия — нет.

Тридцать зон, а не тридцать две, потому что `macd` — готовая колонка из набора данных, а
не наш пересчёт по тем же периодам.

Имя в реестре и класс за ним:

| Имя для `.detect_zones()` | Класс | Обязательные правила |
|---|---|---|
| `zero_crossing` | `ZeroCrossingDetection` | `indicator_col` (или роль через билдер) |
| `threshold` | `ThresholdDetection` | `indicator_col`, `upper_threshold`, `lower_threshold` |
| `line_crossing` | `LineCrossingDetection` | `line1_col`, `line2_col` |
| `preloaded` | `PreloadedZonesDetection` | `zones_data` |
| `combined` | `CombinedRulesDetection` | `conditions` |

Классы экспортируются из `bquant.analysis.zones.detection` — их же наследуют, когда
добавляют свою стратегию (см. [Extension Guide](../api/extension_guide.md)).

## Дальше

| | |
|---|---|
| [Структура результата](zone_analysis_result.md) | что лежит в `result` и как это выгрузить |
| [Свинг-стратегии](swing_strategies.md) | пороги, пресеты, адаптивные параметры |
| [Pipeline API](../api/analysis/pipeline.md) | все методы билдера |
| [Кэширование](caching.md) | когда повторный прогон бесплатен |
| [Практика](best_practices.md) | рабочие паттерны и хранение артефактов |
