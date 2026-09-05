# `bquant.data.loader` — загрузка данных

Чтение OHLCV из CSV: определение кодировки, нормализация имён колонок, разбор времени и
перенос его в индекс.

## Функции

| Сигнатура | Что делает |
|---|---|
| `load_ohlcv_data(file_path, symbol=None, timeframe=None, validate_data=True)` | читает один файл |
| `load_symbol_data(symbol, timeframe, data_source='tradingview', quote_provider='default')` | находит файл по конфигурации и читает его |
| `load_xauusd_data(timeframe='1h')` | то же для XAUUSD |
| `load_all_data_files(data_dir=None)` | читает все CSV каталога |
| `get_data_info(df)` | сводка по загруженному кадру |
| `get_available_symbols(data_dir=None)` | какие символы есть в каталоге |
| `get_available_timeframes(symbol, data_dir=None)` | какие таймфреймы есть **у символа** |

`get_available_timeframes()` требует символ — без него вопрос не имеет смысла, и
до 2026-09-01 эта страница объявляла его необязательным.

## Чтение файла

Пример самодостаточен: файл делается из встроенных данных, потому что внешних CSV в
репозитории нет и быть не должно.

```python
import tempfile
from pathlib import Path

from bquant.data.loader import get_data_info, load_ohlcv_data
from bquant.data.samples import get_sample_data

path = Path(tempfile.mkdtemp()) / 'XAUUSD_1h.csv'
get_sample_data('tv_xauusd_1h').to_csv(path, index=False)

df = load_ohlcv_data(path, symbol='XAUUSD', timeframe='1h')

print(df.shape, type(df.index).__name__)
print(df.columns[:5].tolist())
# (1000, 14) DatetimeIndex
# ['open', 'high', 'low', 'close', 'volume']
```

**Колонки `time` в результате нет** — она стала индексом. Это отличает загрузчик от
`get_sample_data()`, который отдаёт время колонкой при позиционном индексе. Разница
существенна: `resample_ohlcv()` и `detect_market_sessions()` требуют `DatetimeIndex` и на
кадре из sample-данных откажут, пока время не переставлено (`resolve_time_index()`).
Разбор двух контрактов — `devref/gaps/detection/g30_…`.

## Файл MetaTrader без заголовка

Выгрузка терминала — шесть колонок без имён: время, `open`, `high`, `low`, `close`,
`volume` (седьмая и дальше получают имена `col_6`, …). Формат распознаётся по сырому
семплу **до** чтения: первая колонка разбирается как время в каждой строке (строка
заголовка `time` — нет), колонки 1–5 числовые.

```python
import tempfile
from pathlib import Path

import pandas as pd

from bquant.data.loader import load_ohlcv_data
from bquant.data.samples import get_sample_data

rows = get_sample_data('tv_xauusd_1h').head(20)
path = Path(tempfile.mkdtemp()) / 'XAUUSDH1.csv'
with open(path, 'w') as handle:
    for _, row in rows.iterrows():
        stamp = pd.Timestamp(row['time']).strftime('%Y.%m.%d %H:%M:%S')
        handle.write(f"{stamp},{row['open']},{row['high']},{row['low']},{row['close']},{int(row['volume'])}\n")

df = load_ohlcv_data(path, validate_data=False)

print(len(df), df.columns.tolist())
print(df.index[0], type(df.index).__name__)
# 20 ['open', 'high', 'low', 'close', 'volume']
# 2025-06-11 20:00:00 DatetimeIndex
```

До 2026-09-05 такой файл читался **после** попытки с `index_col=0`, которая отнимала
колонку, — проверка «шесть колонок» не проходила, первая строка данных становилась
заголовком, а цены — именами колонок (`['3336.94', '3344.77', …]`); 19 строк вместо 20,
и ничего не падало (G57).

## Что известно о загруженном кадре

```python
import tempfile
from pathlib import Path

from bquant.data.loader import get_data_info, load_ohlcv_data
from bquant.data.samples import get_sample_data

path = Path(tempfile.mkdtemp()) / 'XAUUSD_1h.csv'
get_sample_data('tv_xauusd_1h').to_csv(path, index=False)
info = get_data_info(load_ohlcv_data(path))

print(sorted(info.keys()))
print(info['rows'], round(info['memory_usage_mb'], 3))
print(str(info['date_range']['start']), '→', str(info['date_range']['end']))
# ['columns', 'data_types', 'date_range', 'memory_usage_mb', 'missing_values', 'rows']
# 1000 0.114
# 2025-06-11 20:00:00+07:00 → 2025-08-12 13:00:00+07:00
```

`date_range` содержит два ключа, `start` и `end`, и значения в нём — `Timestamp`, а не
строки.

## Загрузка по символу и таймфрейму

```python
from bquant.data.loader import load_symbol_data
```

`load_symbol_data('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')`
собирает путь через `bquant.core.config.get_data_path()` и читает файл. Каталог данных
по умолчанию — `DATA_DIR` из конфигурации; в чистой установке он пуст, поэтому вызов
завершится `DataLoadingError` с именем пути, которого не нашлось. Это не отказ функции,
а отсутствие файла: положите данные в каталог или укажите путь напрямую через
`load_ohlcv_data()`.

`load_xauusd_data(timeframe='1h')` — то же самое с зафиксированными символом и
провайдером; других параметров у неё нет.

## Что есть в каталоге

```python
from bquant.data.loader import get_available_symbols, get_available_timeframes

print(get_available_symbols())
# []
```

Пустой список означает пустой `DATA_DIR`, а не отсутствие поддержки. Имея символ, можно
спросить его таймфреймы: `get_available_timeframes('XAUUSD')`.

`load_all_data_files()` читает все CSV каталога и возвращает словарь «имя файла →
кадр». Рекурсии нет, шаблон имени не настраивается — параметров, кроме `data_dir`,
у функции не существует.

## Логирование

Загрузчик пишет контекстно — символ и таймфрейм попадают в каждую строку:

```text
bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Loading data from: …
bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Detected encoding: ascii
bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Successfully loaded 1000 rows
```

Приглушить:

```python
import logging

logging.getLogger('bquant.data.loader').setLevel(logging.WARNING)
```

## Дальше

| | |
|---|---|
| [Sample-данные](samples.md) | что можно взять без файлов |
| [Обработка](processor.md) | чистка, ресемплинг, признаки |
| [Валидация](validator.md) | что с данными не так |
| [Конфигурация](../core/config.md) | `DATA_DIR`, пути, провайдеры |
