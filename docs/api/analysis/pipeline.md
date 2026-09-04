# Pipeline анализа зон — справочник

Входная точка — `analyze_zones(df)`: она возвращает билдер, каждый метод которого
возвращает его же, а `.build()` запускает расчёт и отдаёт `ZoneAnalysisResult`.

Пайплайн не привязан к индикатору. Он не знает ни имён колонок, ни словаря типов зон:
и то и другое приносит выбранный индикатор вместе со стратегией детекции.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .with_strategies(swing='zigzag')
    .with_swing_preset('narrow_zone')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(len(result.zones))   # 64
```

Практическая сторона — [Анализ зон на практике](../../user_guide/zone_analysis.md);
здесь описаны методы и их параметры.

## Методы билдера

### `.with_indicator(source, name, **params)`

Какой индикатор посчитать. Необязателен: если нужная колонка уже в кадре, шаг
пропускается, и в `.detect_zones()` колонка адресуется именем.

| `source` | Что это |
|---|---|
| `'custom'` | реализации внутри пакета (`macd`, `sma`, `ema`, `rsi`, `bbands`) |
| `'preloaded'` | индикаторы, рассчитанные заранее и зарегистрированные в фабрике |
| `'pandas_ta'` | всё из `pandas-ta` |
| `'talib'` | всё из TA-Lib, если библиотека установлена |

`**params` уходят в конструктор индикатора **как есть**, поэтому имена там его
собственные: `fast_period=12`, а не `fast=12`.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

macd = analyze_zones(data).with_indicator('custom', 'macd',
                                          fast_period=12, slow_period=26, signal_period=9)
rsi = analyze_zones(data).with_indicator('pandas_ta', 'rsi', length=14)
ao = analyze_zones(data).with_indicator('pandas_ta', 'ao', fast=5, slow=34)

print(type(macd).__name__, type(rsi).__name__, type(ao).__name__)
# ZoneAnalysisBuilder ZoneAnalysisBuilder ZoneAnalysisBuilder
```

### `.detect_zones(strategy, zone_types=None, indicator_role=None, **rules)`

Как искать границы. Пять стратегий и их обязательные правила:

| `strategy` | Обязательные правила | Для чего |
|---|---|---|
| `'zero_crossing'` | `indicator_role` или `indicator_col` | осцилляторы с нулевой линией |
| `'threshold'` | то же + `upper_threshold`, `lower_threshold` | ограниченные осцилляторы |
| `'line_crossing'` | `line1_role`/`line2_role` или `line1_col`/`line2_col` | пары линий |
| `'preloaded'` | `zones_data` | готовые зоны из файла или кадра |
| `'combined'` | `conditions` | несколько условий сразу |

**`indicator_role` вместо имени колонки.** Роль (`'line'`, `'signal'`, `'hist'`,
`'value'`) разрешается по схеме, которую пайплайн построил, когда сам считал индикатор.
Имя колонки собирается из фактических параметров вызова — `fast_period=5` даст
`macd_5_26_9__hist`, — поэтому код, написанный на имя, ломается от смены параметра, а код
на роли не ломается. Имя нужно ровно тогда, когда схемы нет: колонку принесли вы сами.

`zone_types` ограничивает результат перечисленными типами; `None` — без фильтра.

**Порога длительности здесь нет намеренно.** Детекция обязана вернуть полное мощение
таймлайна: отсев коротких зон рвёт его, и соседство зон становится выдумкой. Фильтр
длительности живёт в `.analyze(min_duration=N)` и сообщает, что исключил.

### `.with_strategies(swing=..., shape=..., divergence=..., volatility=..., volume=...)`

Какие семейства метрик считать. Ни одно не включено по умолчанию, кроме свингов и формы.
Зарегистрировано на сегодня:

| Семейство | Доступные значения |
|---|---|
| `swing` | `'zigzag'`, `'find_peaks'`, `'pivot_points'` |
| `shape` | `'statistical'` |
| `divergence` | `'classic'` |
| `volatility` | `'combined'` |
| `volume` | `'standard'` |

Список получен из `StrategyRegistry` прогоном, а не переписан: незарегистрированное имя
отвергается сразу и называет доступные — `ValueError: Unknown shape strategy: geometric.
Available: ['statistical']`.

Смена стратегии или её параметров меняет ключ кэша, поэтому сравнивать варианты можно
с включённым кэшем. Так было не всегда: до версии схемы 16 `shape`, `divergence`,
`volatility` и `volume` в ключ не входили, и включённая стратегия молча получала
результат прошлого прогона, посчитанный без неё (G36).

### `.with_swing_preset(name)`

Пороги для свинг-стратегий. Пресетов **два**: `'narrow_zone'` (по умолчанию) и
`'wide_zone'` (`SWING_PRESETS` в `bquant/core/config.py`); имена говорят, под какую
ширину зоны набор откалиброван.

`wide_zone` требует движения в 2% цены — больше размаха типичной зоны на часовом золоте,
и две стратегии из трёх при нём не находят ничего. До 0.0.10 он был умолчанием под
именем `default`. Таблица покрытия —
[Свинг-стратегии](../../user_guide/swing_strategies.md).

### `.with_swing_scope(scope)`

Где искать пивоты: `'global'` (умолчание) — один раз на всём кадре, с нарезкой по зонам и
сохранением соседних точек; `'per_zone'` — внутри каждой зоны отдельно.

### `.with_auto_swing_thresholds(enable=True)`

Вывести пороги из самих данных вместо констант пресета. На встроенном сэмпле меняет
`deviation` у ZigZag с `0.05` на `0.031`, покрытие при этом не меняется.

**Сегодня режим применим только к ZigZag.** У `find_peaks` и `pivot_points` он поднимает
`min_amplitude_pct` выше размаха типичной зоны и обнуляет улов — 0 зон из 83 против 32 и
41 без него. Разбор и числа —
[Свинг-стратегии](../../user_guide/swing_strategies.md).

### `.with_cache(enable=True, ttl=3600)`

Двухуровневый кэш (память + диск), включён по умолчанию, TTL в секундах. Ключ строится из
хэша данных, конфигурации и подписи свинг-настроек. См. предупреждение выше и
[Кэширование](../../user_guide/caching.md).

### `.analyze(clustering=True, n_clusters=3, regression=False, validation=False, min_duration=1)`

Что считать после детекции. `min_duration` — порог **отчётности**: зоны короче остаются в
`result.zones`, но не входят в агрегаты, и сколько их — записано в
`result.metadata['duration_filter']`.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(min_duration=5)
    .build()
)

report = result.metadata['duration_filter']
print(len(result.zones), report['zones_analysed'], report['zones_excluded'])
# 83 59 24
```

`validation=True` — out-of-sample проверка настроенной детекции: кадр делится 70/30,
детекция прогоняется на каждой части, и частота зон **на бар** обязана удержаться в пороге
набора (20 % по умолчанию). Сравнивается частота, а не число зон: окна разной длины
содержат разное число чего угодно. Итог — в `result.validation_results['out_of_sample']`
(см. [`ValidationSuite`](statistical.md#валидация-моделей-validationsuite)), а
`result.metadata['validation']['status']` различает `executed`, `failed` (с причиной) и
`not_requested`. До 2026-09-04 флаг принимался и не исполнялся (G55).

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(validation=True)
    .build()
)

check = result.validation_results['out_of_sample']
print(result.metadata['validation']['status'], check['success'])
print(check['train_metrics']['total_zones'], check['metadata']['train_size'],
      check['test_metrics']['total_zones'], check['metadata']['test_size'])
print(round(check['metadata']['train_value'], 4), round(check['metadata']['test_value'], 4),
      round(check['degradation_pct'], 1))
# executed True
# 52.0 700 26.0 300
# 0.0743 0.0867 -16.7
```

52 зоны против 26 — по счётчикам «падение вдвое»; на бар — 0.074 против 0.087, частота на
тесте на 16.7 % выше, в пороге. Свой порог — через
`UniversalZoneAnalyzer(validation_suite=ValidationSuite(0.1))` в `ZoneAnalysisPipeline`;
свою метрику или walk-forward — вызовом набора вручную.

### `.build()`

Запускает расчёт и возвращает [`ZoneAnalysisResult`](../../user_guide/zone_analysis_result.md).

## Конфигурация объектами

Билдер — обёртка над тремя dataclass'ами. Когда конфигурация приходит из файла или
собирается программно, их создают напрямую:

```python
from bquant.analysis.zones.pipeline import (
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
    ZoneDetectionConfig,
)
from bquant.data.samples import get_sample_data

config = ZoneAnalysisConfig(
    indicator=IndicatorSpec(
        source='custom',
        name='macd',
        parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
    ),
    zone_detection=ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_role': 'hist'},
    ),
    min_duration=3,
    perform_clustering=True,
    n_clusters=3,
)

result = ZoneAnalysisPipeline(config, enable_cache=False).run(get_sample_data('tv_xauusd_1h'))
print(len(result.zones))   # 83
```

`IndicatorSpec` — это **заявка на расчёт**: какой индикатор посчитать и с какими
параметрами. Не путайте с `bquant.indicators.IndicatorConfig`, который описывает уже
*посчитанный* индикатор. До 2026-08-24 оба класса назывались одинаково, и различать их
приходилось по контексту; старое имя убрано без алиаса.

## `indicator_context` — зона знает, чем она размечена

Каждую зону стратегия детекции подписывает: каким индикатором и по каким правилам она
найдена.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('line_crossing', line1_role='line', line2_role='signal')
    .analyze()
    .build()
)

print(result.zones[0].indicator_context)
# {'detection_strategy': 'line_crossing',
#  'detection_indicator': 'macd_12_26_9__line',
#  'signal_line': 'macd_12_26_9__signal',
#  'detection_rules': {'line1_col': 'macd_12_26_9__line', 'line2_col': 'macd_12_26_9__signal'}}
```

Благодаря этому стратегии метрик берут тот самый ряд, по которому проведена граница, и не
угадывают его по имени колонки.

## Отказы, которые вы увидите

Шаг, которому не хватило данных, не роняет анализ и **не возвращает правдоподобное
число**: он кладёт под своим ключом `error` с причиной.

**Регрессия** (`regression=True`, нужно больше 10 зон) попадает в
`result.regression_results` — словарь с ключами `duration` и `return`; под каждым —
словарь `RegressionResult.to_dict()` (`r_squared`, `coefficients`, `p_values`, `predictions`,
`residuals`, `n_observations`, `metadata`), а не объект: результат обязан переживать
JSON/Parquet без потерь. Неудачная подгонка — словарь с ключом `error`:

- **пустой предиктор.** Набор по умолчанию начинается с `line_amplitude` — амплитуды
  *линии* индикатора. У осциллятора без линии (RSI, AO) её нет, предиктор пуст во всех
  зонах; он выбрасывается, его имя попадает в `metadata['empty_predictors']`, модель
  считается по остальным;
- **вырожденная матрица плана.** Если наблюдения не различаются или предикторы линейно
  зависимы, коэффициенты не определены — отказ явный.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(regression=True)
    .build()
)

model = result.regression_results['duration']
if 'error' in model:
    print('регрессия не построена:', model['error'])
else:
    print(round(model['r_squared'], 3), model['n_observations'])
    print('выброшены как пустые:', model['metadata']['empty_predictors'])
```

**Тесты гипотез** отказываются так же: у теста, которому не хватило данных или словаря
типов, вместо `p_value` лежит `error` с причиной. Для собственного словаря типов
(`strong`/`weak` и т.п.) это норма: `contrast_asymmetry` и `correlation_drawdown` требуют
объявленных противоположности и полярности.

## Дальше

| | |
|---|---|
| [Анализ зон на практике](../../user_guide/zone_analysis.md) | какую стратегию выбрать и почему |
| [Структура результата](../../user_guide/zone_analysis_result.md) | что лежит в `ZoneAnalysisResult` |
| [Стратегии метрик](strategies.md) | swing, shape, divergence, volatility, volume |
| [Зоны: модели и детекция](zones.md) | `ZoneInfo`, словарь типов, реестр стратегий |
| [Extension Guide](../extension_guide.md) | как добавить свою стратегию |
