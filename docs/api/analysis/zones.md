# `bquant.analysis.zones` — модели зон и словарь типов

Здесь — из чего состоит зона, откуда берутся её типы и что такое вторая, непохожая
модель зоны в этом же пакете. Как запускать анализ — [Pipeline API](pipeline.md) и
[руководство](../../user_guide/zone_analysis.md); что лежит в результате —
[структура результата](../../user_guide/zone_analysis_result.md).

## `ZoneInfo` — участок времени

| Поле | Что это |
|---|---|
| `zone_id` | номер зоны в этом прогоне |
| `type` | имя типа из словаря стратегии детекции |
| `start_idx`, `end_idx` | границы в барах (позиции в `result.data`) |
| `start_time`, `end_time` | границы во времени — значения индекса кадра |
| `duration` | число баров |
| `data` | срез кадра за период зоны |
| `features` | признаки, заполняются анализом |
| `indicator_context` | чем и по каким правилам зона размечена |
| `swing_context` | контекст свингов при глобальном режиме |

Методы: `get_zone_swings()`, `get_primary_indicator_column()`,
`get_signal_line_column()`, `to_analyzer_format()`.

## `indicator_context` — зона знает, чем она размечена

Стратегия детекции подписывает каждую зону: каким рядом и по каким правилам проведена
граница. Благодаря этому стратегии метрик берут **тот самый** ряд, а не угадывают его по
имени колонки.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze()
    .build()
)

zone = result.zones[0]
print(zone.indicator_context['detection_strategy'])
print(zone.get_primary_indicator_column())
print(zone.get_signal_line_column())
# threshold
# RSI_14
# None
```

## `ZoneType` и `ZoneVocabulary` — стратегия объявляет свои типы

Тип зоны — **открытый словарь**. `zero_crossing` называет свои типы `bull`/`bear`,
`threshold` — `overbought`/`neutral`/`oversold`, ваша собственная стратегия может
называть их `regime_a`/`regime_b`/`regime_c`. Ядро не содержит перечня допустимых имён
и не должно его содержать.

Чтобы универсальные слои (метрики зоны, анализ последовательностей, статистика,
визуализация) могли работать с любым словарём, стратегия объявляет **свойства** каждого
типа, а потребитель дискриминирует по ним, а не по имени:

```python
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

### Регистрация собственной стратегии

```python
from bquant.analysis.zones import ZoneType
from bquant.analysis.zones.detection import ZoneDetectionRegistry

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


print(ZoneDetectionRegistry.get_vocabulary('volatility_regime').names())
# ['high_vol', 'low_vol']
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
from bquant.analysis.zones.detection import ZoneDetectionRegistry

vocab = ZoneDetectionRegistry.get_vocabulary('preloaded')
print(vocab.is_declared, vocab.names())
# False []
```

Пустой словарь означает «определяется во время выполнения», а **не** «типов нет» —
потребители читают `is_declared` и в этом случае не фильтруют.

## Анализ последовательностей: примыкание и состояния

`result.sequence_analysis` строится **только по примыкающим зонам**. Детекторы мостят
область определения индикатора, и слой последовательностей читает соседние элементы
списка как переход. По умолчанию (`min_duration=1`) пропусков нет вовсе: зоны стыкуются
точно, и все `total_zones - 1` пар засчитываются. Если вы **просите** отсев
(`.analyze(min_duration=N)`), соседи выброшенной зоны перестают примыкать — и такая пара
переходом не является: между этими зонами было то, чего в выборке нет. Пропуски
считаются, а не замазываются.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze()
    .build()
)

summary = result.sequence_analysis['sequence_summary']
print(len(result.zones), summary['total_transitions'], summary['discarded_transitions'])
print(summary['bars_missing'], summary['contiguous_segments'], summary['adjacency_verified'])
# 83 82 0
# 0 1 True
```

С `min_duration=2` те же данные дают 72 зоны, 63 засчитанных перехода и 8 отброшенных;
пороговый RSI — 30 и 13. Разница целиком создаётся фильтром, а не данными.

**Состояния цепи Маркова берутся из наблюдённой последовательности**, а не из
фиксированной пары:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze()
    .build()
)

markov = result.sequence_analysis['markov_analysis']
print(markov['states'])
print(markov['observed_transitions'])
# ['neutral', 'overbought', 'oversold']
# 63
```

Если ни одна пара зон не примыкает, возвращается `markov['error']` с объяснением, а не
нулевая матрица. Раньше на любом словаре, кроме `bull`/`bear`, функция отдавала нули как
успех — вместе с `states: ['bull','bear']` и стационарным распределением `[1.0, 0.0]`,
то есть уверенным утверждением о состоянии, ни разу не встретившемся в данных.

**Runs-test бинаризуется по объявленной полярности** и считается на самом длинном
сплошном отрезке; при отсутствии объявленных полярностей возвращает `not_applicable` с
причиной вместо константного ряда.

## Вторая ветка: уровни цены

В пакете **две разные вещи называются зоной**, и это не старая и новая версии одной, а
разные предметы:

| | `ZoneInfo` (пайплайн) | `PriceLevelZone` |
|---|---|---|
| Что это | **участок времени**, на котором осциллятор в одном состоянии | **полоса цены**: поддержка, сопротивление |
| Границы | в барах (`start_idx`/`end_idx`) | в цене (`start_price`/`end_price`) |
| Как расположены | идут встык, каждый бар ровно в одной зоне | могут перекрываться, покрывают не всю историю |
| Кто считает | `analyze_zones()` / `UniversalZoneAnalyzer` | `PriceLevelAnalyzer` / `find_support_resistance()` |

Раньше они звались `Zone` и `ZoneInfo`, а анализаторы — `ZoneAnalyzer` и
`UniversalZoneAnalyzer`. Имена намекали на иерархию («базовое против расширенного»), и
этот раздел из-за них однажды был написан как «Deprecated, мигрируйте на пайплайн».
Мигрировать некуда — это разные предметы; разбор в
`../../../devref/gaps/zone_types/g28_one_word_two_concepts_2026-08.md`.

Приставка `Universal` у второго анализатора означает **независимость от конкретного
индикатора**, а не превосходство над первым.

```python
import pandas as pd

from bquant.analysis.zones import find_support_resistance
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

# Время нужно на индексе: границы полосы задаются временем, и длительность
# считается как разница дат. `get_sample_data()` отдаёт кадр со временем в
# колонке `time` и позиционным индексом, поэтому его надо переставить.
data = data.set_index(pd.to_datetime(data['time'])).drop(columns=['time'])

levels = find_support_resistance(data, window=20, min_touches=2)

print(len(levels))
level = levels[0]
print(level.zone_type, round(level.start_price, 1), round(level.end_price, 1), level.strength)
# 8
# support 3281.7 3282.7 0.4
```

## Дальше

| | |
|---|---|
| [Pipeline API](pipeline.md) | билдер, детекция, кэш |
| [Стратегии метрик](strategies.md) | swing, shape, divergence, volatility, volume |
| [Структура результата](../../user_guide/zone_analysis_result.md) | поля результата и выгрузка |
| [Анализ зон на практике](../../user_guide/zone_analysis.md) | какую стратегию детекции выбрать |
| [Extension Guide](../extension_guide.md) | своя стратегия детекции |
