# Данные — `bquant.data`

Пять модулей: откуда взять кадр, как его причесать, как проверить, чем описать и что
уже лежит в пакете.

| Модуль | Отвечает на вопрос | Страница |
|---|---|---|
| `samples` | что можно взять прямо сейчас, без файлов | [Sample-данные](samples.md) |
| `loader` | как прочитать свой CSV | [Загрузка](loader.md) |
| `processor` | как почистить, пересобрать, добавить признаки | [Обработка](processor.md) |
| `validator` | что с этими данными не так | [Валидация](validator.md) |
| `schemas` | какие поля обязательны и каким правилам подчиняются | [Схемы](schemas.md) |

## С чего начинать

Со встроенных данных: они всегда на месте, у них известны границы, и на них написаны
все примеры документации.

```python
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

print(data.shape)
print(list(data.columns[:6]))
print(data['time'].iloc[0], '→', data['time'].iloc[-1])
# (1000, 15)
# ['time', 'open', 'high', 'low', 'close', 'volume']
# 2025-06-11 20:00:00+07:00 → 2025-08-12 13:00:00+07:00
```

Время здесь **колонка**, а не индекс. Пайплайн зон переставляет его сам; функциям,
которым нужен `DatetimeIndex` (ресемплинг, сессии, непрерывность ряда), его надо дать —
для этого есть `resolve_time_index()`.

## Свой файл

```python
import tempfile
from pathlib import Path

from bquant.data.loader import load_ohlcv_data
from bquant.data.samples import get_sample_data

path = Path(tempfile.mkdtemp()) / 'XAUUSD_1h.csv'
get_sample_data('tv_xauusd_1h').to_csv(path, index=False)

df = load_ohlcv_data(path, symbol='XAUUSD', timeframe='1h')

print(df.shape, type(df.index).__name__)
# (1000, 14) DatetimeIndex
```

Колонок стало 14, а не 15: `time` ушёл в индекс. Загрузчик и sample-данные отдают кадр
**по-разному**, и это не мелочь — половина функций обработки требует `DatetimeIndex`, а
половина работает с любым. Подробности — [загрузка](loader.md).

## Проверить

```python
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_ohlcv_data

report = validate_ohlcv_data(get_sample_data('tv_xauusd_1h'))

print(report['is_valid'], report['issues'])
print(report['warnings'])
# True []
# ['High missing data ratio: 26.67%']
```

Предупреждение настоящее и объяснимое: четыре колонки маркеров дивергенций TradingView
заполнены только на сигнальных барах, а в выгрузке пусты целиком — четыре пустых колонки
из пятнадцати и дают 26.67%. Разбор — [валидация](validator.md).

## Подготовить к анализу

```python
from bquant.data.processor import clean_ohlcv_data, prepare_data_for_analysis
from bquant.data.samples import get_sample_data

clean = clean_ohlcv_data(get_sample_data('tv_xauusd_1h'))
prepared = prepare_data_for_analysis(clean)

print(prepared.shape, prepared.index[0])
# (951, 36) 49
```

Снято ровно 49 строк — прогрев самого длинного окна (`price_ma_50`). До 2026-09-01 та же
пара вызовов давала кадр `(0, 36)`: отсев пропусков шёл по всем колонкам сразу, и одна
пустая колонка уносила выборку целиком (`devref/gaps/data/g41_…`).

## Описать схемой

```python
from bquant.data.samples import get_sample_data
from bquant.data.schemas import validate_with_schema

data = get_sample_data('tv_xauusd_1h')

print(validate_with_schema(data, 'ohlcv').is_valid)
print(validate_with_schema(data, 'macd').issues)
# True
# ["Missing required fields: ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']"]
```

Второй вердикт верен: колонки MACD в сэмпле называются `macd` и `signal` — это выгрузка
TradingView, а не выход индикатора пакета. До 2026-09-01 обе строки печатали `True`
(`devref/gaps/data/g42_…`).

## Логирование

Модули данных пишут подробно — при работе из research-скрипта это мешает:

```python
import logging

logging.getLogger('bquant.data').setLevel(logging.WARNING)
```

Подробнее — [управление логированием](../core/logging.md).

## Дальше

| | |
|---|---|
| [Индикаторы](../indicators/README.md) | что считать поверх этого кадра |
| [Анализ зон](../analysis/README.md) | куда кадр идёт дальше |
| [Ядро](../core/README.md) | конфигурация, кэш, логирование |
