# Sample-данные — `bquant.data.samples`

Два датасета, вшитых в пакет. Они всегда на месте, не требуют внешних файлов и на них
написаны все примеры этой документации.

## Что есть

Список не переписывайте отсюда — спрашивайте у пакета:

```python
from bquant.data.samples import list_datasets

for entry in list_datasets():
    print(f"{entry['name']:<15} {entry['rows']} строк, {entry['columns_count']} колонок, "
          f"{entry['size_kb']} КБ — {entry['source']}")
# tv_xauusd_1h    1000 строк, 15 колонок, 542.4 КБ — TradingView via OANDA
# mt_xauusd_m15   1000 строк, 7 колонок, 202.5 КБ — MetaTrader
```

| | `tv_xauusd_1h` | `mt_xauusd_m15` |
|---|---|---|
| Источник | TradingView через OANDA | MetaTrader |
| Инструмент | XAUUSD | XAUUSD |
| Таймфрейм | 1 час | 15 минут |
| Период | 2025-06-11 20:00 … 2025-08-12 13:00 (+07:00) | 2025-08-07 19:15 … 2025-08-22 16:00 |
| Строк | 1000 | 1000 |
| Помимо OHLCV | `accumulation_distribution`, `macd`, `signal`, `rsi`, `rsi_based_ma`, четыре колонки маркеров дивергенций | `spread` |

Колонки `macd`, `signal`, `rsi` — **выгрузка TradingView**, а не выход индикатора пакета:
их посчитал источник, у них свои параметры и своё именование. Индикатор пакета назвал бы
их `macd_12_26_9__line` и `rsi_14`. Читать готовые колонки умеет
[preloaded-индикатор](../indicators/preloaded.md).

## Загрузка

```python
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')                 # DataFrame по умолчанию
records = get_sample_data('tv_xauusd_1h', format='dict')  # список словарей

print(type(df).__name__, df.shape)
print(type(records).__name__, len(records), type(records[0]).__name__)
# DataFrame (1000, 15)
# list 1000 dict
```

`format` принимает `'pandas'`/`'dataframe'` и `'dict'`/`'list'`. Имя `load_sample_data`
— тот же вызов под старым именем.

## Метаданные

```python
from bquant.data.samples import get_dataset_info

info = get_dataset_info('mt_xauusd_m15')

print(info['name'], '|', info['timeframe'], '|', info['rows'])
print(info['period_start'], '→', info['period_end'])
print(info['columns'])
# MetaTrader XAUUSD 15M | 15M | 1000
# 2025-08-07T19:15:00 → 2025-08-22T16:00:00
# ['time', 'open', 'high', 'low', 'close', 'volume', 'spread']
```

**Осторожно с ключом `name`.** В `get_dataset_info()` это человеческое название
(`'MetaTrader XAUUSD 15M'`), а в элементах `list_datasets()` — идентификатор
(`'mt_xauusd_m15'`), тот самый, что принимает `get_sample_data()`. Одно слово, два разных
предмета.

## Проверка целостности

```python
from bquant.data.samples import list_dataset_names, validate_dataset

for name in list_dataset_names():
    result = validate_dataset(name)
    print(name, result['is_valid'], result['errors'])
    print('   период:', result['stats']['period'])
# tv_xauusd_1h True []
#    период: {'declared': ['2025-06-11T20:00:00+07:00', '2025-08-12T13:00:00+07:00'], 'actual': ['2025-06-11T20:00:00+07:00', '2025-08-12T13:00:00+07:00']}
# mt_xauusd_m15 True []
#    период: {'declared': ['2025-08-07T19:15:00', '2025-08-22T16:00:00'], 'actual': ['2025.08.07 19:15', '2025.08.22 16:00']}
```

Сверяются число строк, набор колонок и **объявленный период против несомого**. Последнее
появилось 2026-09-01: до того период не проверялся вовсе, и `mt_xauusd_m15` объявлял май
там, где нёс август, а валидация отвечала `is_valid: True` — вердикт о том, чего не
смотрели (`devref/gaps/data/g40_…`). Совпадение теперь видно в `stats['period']`:
«проверено» должно быть отличимо от «пропущено» и в успешном случае.

## Поиск и сравнение

```python
from bquant.data.samples import (find_datasets, get_datasets_by_symbol,
                                 get_datasets_by_timeframe, get_datasets_by_source)

print(find_datasets(symbol='XAUUSD'))
print(get_datasets_by_timeframe('1H'), get_datasets_by_source('MetaTrader'))
# ['mt_xauusd_m15', 'tv_xauusd_1h']
# ['tv_xauusd_1h'] ['mt_xauusd_m15']
```

`find_datasets()` принимает `symbol`, `timeframe` и `source` вместе; три односложные
сестры — по одному критерию каждая. Таймфрейм сравнивается без учёта регистра. Множество
результатов у них совпадает, **порядок — нет**: `find_datasets()` сортирует, остальные
отдают в порядке реестра. Полагаться на порядок не стоит нигде.

```python
from bquant.data.samples import compare_sample_datasets

diff = compare_sample_datasets('tv_xauusd_1h', 'mt_xauusd_m15')

print(sorted(diff['common_columns']))
print(diff['unique_columns']['mt_xauusd_m15'])
print(diff['comparison']['timeframes'])
# ['close', 'high', 'low', 'open', 'time', 'volume']
# ['spread']
# ['1H', '15M']
```

## Статистика и предпросмотр

```python
from bquant.data.samples import get_data_statistics, get_sample_preview

stats = get_data_statistics('tv_xauusd_1h')
print(stats['total_records'], stats['total_columns'])
print({k: round(v, 2) for k, v in stats['column_statistics']['close'].items()
       if k in ('min_value', 'max_value', 'mean_value')})
# 1000 15
# {'min_value': 3263.82, 'max_value': 3448.49, 'mean_value': 3350.64}

print(get_sample_preview('mt_xauusd_m15', 1))
# [{'time': '2025.08.07 19:15', 'open': 3390.72, 'high': 3391.52, 'low': 3389.29, 'close': 3389.69, 'volume': 2072.0, 'spread': 0.0}]
```

Формат времени у датасетов разный — `'2025-06-11T20:00:00+07:00'` у TradingView и
`'2025.08.07 19:15'` у MetaTrader: каждый несёт то, что дал источник. В `DataFrame`
обе формы приводятся к `datetime`.

## Конвертация формата

```python
from bquant.data.samples import convert_to_dataframe, convert_to_list_of_dicts, get_sample_data

records = get_sample_data('tv_xauusd_1h', format='dict')
frame = convert_to_dataframe(records, 'tv_xauusd_1h')
back = convert_to_list_of_dicts(frame, 'tv_xauusd_1h')

print(frame.shape, frame['time'].dtype)
print(len(back), type(back[0]['time']).__name__)
# (1000, 15) datetime64[ns, UTC+07:00]
# 1000 Timestamp
```

Обратная конвертация **не даёт исходных строк**: время возвращается объектом
`Timestamp`, потому что через `DataFrame` оно уже разобрано. Круг не замкнут, и
рассчитывать на побайтовое совпадение с `format='dict'` нельзя.

## Печать карточек

```python
from bquant.data.samples import print_datasets_info, print_sample_data_status
```

Обе печатают и ничего не возвращают: `print_datasets_info()` — карточку каждого
датасета, `print_sample_data_status()` — сводку по всем. Для программного доступа есть
`list_datasets()` и `get_dataset_info()`.

## Откуда берутся встроенные данные

`SampleDataGenerator` — то, чем они сделаны: он читает исходные CSV загрузчиком пакета и
пишет из них Python-модули в `bquant/data/samples/embedded/`.

```python
from bquant.data.samples import SampleDataGenerator
```

Три метода: `validate_source_files()` — есть ли исходники на месте,
`generate_embedded_data(name)` — один датасет, `generate_all()` — все. Обычный вызов —
через `scripts/data/extract_samples.py`. Всё это нужно только тому, кто обновляет сами
sample-данные; чтобы ими пользоваться, генератор не требуется.

**Исходных CSV в репозитории нет** — это внешние выгрузки, и без них генератор ничего не
сделает. Метаданные, которые он записывает в сгенерированный файл, не совпадают с
реестром в `datasets.py`: у `mt_xauusd_m15` они испорчены на извлечении (MT-CSV идёт без
заголовка, и первая строка данных попала в список колонок). API читает реестр, поэтому на
работу это не влияет; разбор — `devref/gaps/data/g40_…`, §5.

## Ограничения

* По 1000 строк в каждом датасете — этого хватает на демонстрацию и на тесты, но не на
  статистику: 83 зоны MACD при детекции по гистограмме, 32 по линии.
* Только XAUUSD и только два источника.
* Данные статические. Обновление — `scripts/data/extract_samples.py`, которому нужны
  исходные CSV; в репозитории их нет и не должно быть.
* Лицензия — open data, для исследований и обучения. Не для торговли.

## Дальше

| | |
|---|---|
| [Загрузка](loader.md) | как читать свои файлы |
| [Обработка](processor.md) | что делать с кадром дальше |
| [Preloaded-индикатор](../indicators/preloaded.md) | как читать готовые колонки `macd`/`signal` |
| [Анализ зон](../analysis/README.md) | ради чего всё это |
