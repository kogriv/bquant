# `bquant.indicators.preloaded` — индикаторы поверх готовых колонок

Индикатор, который ничего не считает. Он читает уже посчитанные значения из кадра —
те, что пришли вместе с данными, — и подаёт их пакету через тот же интерфейс, что и
вычисляемые индикаторы: `calculate()`, роли выходов, метаданные, валидация.

Нужно это там, где индикатор уже есть в выгрузке и пересчитывать его нельзя или незачем:
терминал считал MACD своими формулами, и именно те числа надо анализировать. Встроенный
сэмпл `tv_xauusd_1h` — ровно такой случай: TradingView отдаёт `macd` и `signal` в самих
данных.

В пакете один такой класс — `MACDPreloadedIndicator`. Базовый `PreloadedIndicator`
описан в [base.md](base.md); свой пишется по тому же контракту.

## Прочитать готовые значения

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')
indicator = MACDPreloadedIndicator()

result = indicator.calculate(data)

print(list(result.data.columns))
# ['macd', 'signal']
print(result.metadata['calculation_method'], result.metadata['total_records'])
# extract_existing 1000
print(result.metadata['nan_counts'])
# {'macd': 0, 'signal': 0}
```

`calculation_method: 'extract_existing'` — не украшение, а единственное место, где
сказано, что числа не вычислены здесь. `nan_counts` заполняется всегда, в том числе
нулями: «пропусков нет» и «не считали» должны различаться.

Через фабрику — то же самое:

```python
from bquant.indicators import IndicatorFactory
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
indicator = IndicatorFactory.create('preloaded', 'macd')
print(list(indicator.calculate(data).data.columns))
# ['macd', 'signal']
```

## Какие колонки читать

По умолчанию `['macd', 'signal']`. Список задаётся при создании и действует и при
извлечении, и при валидации:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')

line_only = MACDPreloadedIndicator(required_columns=['macd'])
print(list(line_only.calculate(data).data.columns))
# ['macd']

print(MACDPreloadedIndicator.get_default_columns())
# ['macd', 'signal']
```

> До сентября 2026 параметр не действовал: `get_required_columns` был объявлен в классе
> дважды, и классовый двойник возвращал умолчания независимо от запроса. Разбор —
> `devref/gaps/core/g46_a_method_defined_twice_silently_won_2026-09.md`.

Имена колонок здесь **чужие**: они пришли с данными, и переименовывать их нечего.
Адресация по роли работает как у всех индикаторов:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')
indicator = MACDPreloadedIndicator()

print(indicator.get_output_roles())
# {'line': 'macd', 'signal': 'signal'}
```

Роли назначаются **позиционно**, в порядке `line`, `signal`, `hist` — это контракт
класса, а не догадка по именам. Поэтому `MACDPreloadedIndicator(required_columns=['rsi'])`
прочитает колонку `rsi` и назовёт её ролью `line`; если запрошено больше трёх колонок,
ролей не выдаётся вовсе, потому что контракт исчерпан.

## Валидация

`validate_data()` не возвращает `False` — она либо подтверждает, либо поднимает
`ValueError` с названием того, чего не хватает:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')

print(MACDPreloadedIndicator().validate_data(data))
# True

with_histogram = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])
try:
    with_histogram.validate_data(data)
except ValueError as error:
    print(error)
# Missing required columns for MACD PRELOADED: ['histogram']
```

Колонки `histogram` в выгрузке TradingView нет — есть `macd`, `signal` и `rsi`. Гистограмму
считают разностью линии и сигнала.

Проверяется три вещи: наличие запрошенных колонок, непустота кадра и числовой тип каждой
колонки. Минимум записей — одна: значения уже посчитаны, набирать окно не нужно.

## Статистика и вспомогательные разрезы

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')
indicator = MACDPreloadedIndicator()

stats = indicator.get_statistics(data)
print(sorted(stats))
# ['macd', 'signal']
print({k: round(v, 4) for k, v in stats['macd'].items() if k != 'nan_count'})
# {'count': 1000, 'min': -14.9674, 'max': 17.3877, 'mean': 0.2169, 'std': 6.7231, 'median': -0.0756}
```

Пересечения линии и сигнала — по двум первым запрошенным колонкам, если не указано иное:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')

crossovers = MACDPreloadedIndicator().get_crossovers(data)
print(crossovers['bullish_crossovers'], crossovers['bearish_crossovers'])
# 39 38
print(crossovers['bullish_indices'][:2])
# [6, 20]
```

Индексы возвращаются из индекса кадра, а счётчики — как `numpy.int64`; при сериализации
в JSON их придётся привести к `int`.

### `is_trending_up` / `is_trending_down` — ловушка порога

Обе смотрят только на **два последних** значения и обе сравнивают их не только между
собой, но и с порогом:

```
is_trending_up   = last > previous  и  last > threshold
is_trending_down = last < previous  и  last < threshold
```

Порог по умолчанию — `0.0`. Отсюда результат, который читается как отсутствие данных:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')
indicator = MACDPreloadedIndicator()

print(indicator.is_trending_up(data), indicator.is_trending_down(data))
# False False
print(round(data['macd'].iloc[-2], 3), round(data['macd'].iloc[-1], 3))
# -5.557 -5.398
```

MACD вырос, но остался отрицательным — поэтому «вверх» не сработало из-за порога, а
«вниз» не сработало из-за направления. Два `False` здесь означают «растёт ниже нуля», а
не «ничего не известно». Для роста без привязки к нулю порог задаётся явно:
`is_trending_up(data, threshold=float('-inf'))`.

Это методы для быстрого разреза, а не для анализа: они не смотрят дальше последней пары
баров. Тренд, наклон и форма — в [зонном анализе](../analysis/zones.md).

## Зоны на готовых значениях

Пайплайн строит зоны по колонкам, которые уже есть в кадре: `.with_indicator()` просто
не вызывается, а колонка адресуется **по имени**:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h').copy()
data['hist'] = data['macd'] - data['signal']

result = (
    analyze_zones(data)
    .detect_zones('zero_crossing', indicator_col='hist')
    .analyze(clustering=False)
    .build()
)
print(len(result.zones))
# 78
```

Здесь именно `indicator_col`, а не `indicator_role`: роли объявляет индикатор, а его в
этом прогоне нет — колонки пришли с данными. Попытка адресоваться ролью даёт понятный
отказ, а не молчаливый промах.

Не путайте с одноимённой **стратегией детекции** `preloaded`: она импортирует готовые
зоны (из CSV или кадра с `zone_id`, `type`, `start_time`, `end_time`), а не готовые
значения индикатора. Подробности — в [справочнике зон](../analysis/zones.md).

## Свой PRELOADED-индикатор

Наследуйте `PreloadedIndicator` и реализуйте `calculate()` и `validate_data()`; роли
выходов и список колонок — по контракту из [base.md](base.md). Полный разбор с примером
целиком — [extension_guide.md](../extension_guide.md).

Что стоит держать в голове, судя по разбору G46:

1. **Не объявляйте один метод дважды.** Второе определение молча побеждает, и Python не
   предупреждает. Если нужен и классовый доступ к умолчаниям, и экземплярный к
   запрошенному — это два разных имени.
2. **Отказывайте, а не возвращайте `False`.** Пустой результат и «данные не подошли»
   должны различаться на вызывающей стороне.
3. **Ноль — это результат замера.** `None` вместо нуля превращает измеренное в
   неизвестное.

## См. также

- [base.md](base.md) — базовые классы, роли, контракт имён колонок
- [custom.md](custom.md) — встроенные вычисляемые индикаторы
- [factory.md](factory.md) — `IndicatorFactory` и источники
- [extension_guide.md](../extension_guide.md) — как написать свой индикатор
