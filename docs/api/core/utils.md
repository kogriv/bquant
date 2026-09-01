# `bquant.core.utils` — утилиты

Восемь функций общего назначения плюс декоратор устаревания. Ничего специфичного для
анализа зон здесь нет — это то, что нужно любому скрипту поверх пакета.

| Сигнатура | Что делает |
|---|---|
| `calculate_returns(prices, method='simple', periods=1)` | доходности ряда цен |
| `normalize_data(data, method='zscore', columns=None)` | нормировка кадра |
| `validate_ohlcv_columns(data, strict=True)` | есть ли обязательные колонки |
| `memory_usage_info(data)` | сколько кадр занимает в памяти |
| `save_results(data, filepath, format='csv', **kwargs)` | сохранить результат |
| `ensure_directory(path)` | создать каталог, если его нет |
| `create_timestamp(format='compact')` | метка времени для имён файлов |
| `setup_project_logging(name='bquant', level=None, …)` | логгер проекта |
| `deprecated(message)` | декоратор устаревания |

## Доходности

```python
from bquant.core.utils import calculate_returns
from bquant.data.samples import get_sample_data

close = get_sample_data('tv_xauusd_1h')['close']

simple = calculate_returns(close, method='simple')
log_returns = calculate_returns(close, method='log')

print(round(float(simple.iloc[1]), 6), round(float(log_returns.iloc[1]), 6))
print(bool(simple.isna().iloc[0]), len(simple))
# 0.002293 0.00229
# True 1000
```

Первое значение — `NaN`: сравнивать не с чем. Длина ряда сохраняется, поэтому результат
можно приложить к исходному кадру без выравнивания. `periods` задаёт горизонт: `1` —
бар к бару, `24` — сутки к суткам на часовых данных.

## Нормировка

```python
from bquant.core.utils import normalize_data
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')[['open', 'high', 'low', 'close']]
normalized = normalize_data(data, method='zscore')

print(list(normalized.columns))
print(round(float(normalized['close'].mean()), 10), round(float(normalized['close'].std()), 4))
# ['open', 'high', 'low', 'close']
# -0.0 1.0
```

Колонки **заменяются**, а не добавляются — в отличие от
[`normalize_prices()`](../data/processor.md) из модуля обработки, которая дописывает
`*_normalized`. Две похожие функции с разным поведением: здесь нормируется произвольный
кадр, там — цены OHLC внутри пайплайна данных.

## Проверка структуры

```python
from bquant.core.utils import validate_ohlcv_columns
from bquant.data.samples import get_sample_data

check = validate_ohlcv_columns(get_sample_data('tv_xauusd_1h'))

print(sorted(check))
print(check['is_valid'], check['missing_required'], check['missing_optional'])
# ['extra_columns', 'is_valid', 'messages', 'missing_optional', 'missing_required']
# True [] []
```

Лишние колонки не делают кадр невалидным — они попадают в `extra_columns` и в
`messages`. Это проверка **наличия**, а не качества; за качеством —
[валидатор данных](../data/validator.md).

## Память

```python
from bquant.core.utils import memory_usage_info
from bquant.data.samples import get_sample_data

info = memory_usage_info(get_sample_data('tv_xauusd_1h'))

print(sorted(info))
print(info['shape'], round(float(info['total_memory_mb']), 3))
# ['columns_memory_mb', 'dtypes', 'index_memory_mb', 'shape', 'total_memory_mb']
# (1000, 15) 0.176
```

## Сохранение и каталоги

```python
import tempfile
from pathlib import Path

from bquant.core.utils import create_timestamp, ensure_directory, save_results
from bquant.data.samples import get_sample_data

directory = ensure_directory(Path(tempfile.mkdtemp()) / 'results')
path = directory / f'zones_{create_timestamp()}.csv'

ok = save_results(get_sample_data('tv_xauusd_1h').head(10), path, index=False)

print(ok, path.exists())
print(len(create_timestamp()), create_timestamp('readable')[:2])
# True True
# 15 20
```

`create_timestamp()` даёт компактную метку вида `20260901_191317` — годится для имени
файла; `'readable'` даёт `2026-09-01 19:13:17` — для текста. `save_results()` возвращает
`bool`, а не путь, и понимает `format='csv'`, `'json'`, `'excel'`; лишние именованные
аргументы уходят в pandas.

## Устаревание

```python
from bquant.core.utils import deprecated


@deprecated("используйте new_method()")
def old_method():
    return 'работает'


print(old_method())
# работает
```

`DeprecationWarning` выдаётся при первом вызове за сессию, запись уходит в лог, а метод
продолжает работать. Так помечают то, что снимут в следующих версиях.

В этом репозитории декоратор применяется редко и осознанно: переименования проводятся
целиком, одним изменением, без окна совместимости и алиасов. `@deprecated` нужен для
внешнего API, у которого есть чужие вызывающие, а не для внутренних правок.

## Логгер проекта

```python
from bquant.core.utils import setup_project_logging

logger = setup_project_logging(name='bquant', level='WARNING')
print(logger.name)
# bquant
```

Тонкая обёртка над [`setup_logging()`](logging.md) для скриптов, которым не нужны
профили и модульные уровни. Всё, что сложнее одного уровня, настраивается там.

## Дальше

| | |
|---|---|
| [Логирование](logging.md) | профили и модульные уровни |
| [Конфигурация](config.md) | пути и параметры по умолчанию |
| [Обработка данных](../data/processor.md) | `normalize_prices()` и другие соседи |
