# bquant.data.loader — Загрузка данных

## Обзор

Функции для загрузки OHLCV‑данных из CSV и по символу/таймфрейму на основе конфигурации. Включает нормализацию колонок, разбор дат, валидацию структуры.

## Основные функции

- `load_ohlcv_data(file_path, symbol=None, timeframe=None, validate_data=True) -> DataFrame`
  - Загружает CSV, нормализует имена колонок (`open/high/low/close/volume`), пытается распарсить дату, опционально валидирует структуру.

- `load_symbol_data(symbol, timeframe, data_source='tradingview', quote_provider='default', validate_data=True) -> DataFrame`
  - Находит путь с помощью `bquant.core.config.get_data_path()` и загружает файл.

- `load_xauusd_data(timeframe='1h', data_source='tradingview', quote_provider='oanda') -> DataFrame`
  - Удобный хелпер для XAUUSD.

- `load_all_data_files(data_dir=None, pattern='*.csv', recursive=False) -> Dict[str, DataFrame]`
  - Загружает все подходящие файлы из директории (по умолчанию `DATA_DIR`), без рекурсии по умолчанию.

- Информация/списки:
  - `get_data_info(df) -> Dict[str, Any]`
  - `get_available_symbols(data_dir=None) -> List[str]`
  - `get_available_timeframes(data_dir=None, data_source='tradingview') -> List[str]`

## Примеры

Загрузка из файла и базовая информация:
```python
from bquant.data.loader import load_ohlcv_data, get_data_info

df = load_ohlcv_data('data/XAUUSD_1h.csv', symbol='XAUUSD', timeframe='1h')
print(get_data_info(df))
```

Загрузка по символу/таймфрейму:
```python
from bquant.data.loader import load_symbol_data

df = load_symbol_data('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')
```

Загрузка всех файлов:
```python
from bquant.data.loader import load_all_data_files

datasets = load_all_data_files()
print(list(datasets.keys()))
```

## Логирование {#logging}

Модуль использует контекстное логирование с детальными техническими сообщениями:

```python
# Пример вывода логгера
10:54:37 - bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Loading data from: /path/to/file.csv
10:54:37 - bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Detected encoding: ascii
10:54:39 - bquant.data.loader - INFO - [symbol=XAUUSD, timeframe=1h] Successfully loaded 21357 rows of data
```

**Управление уровнем логирования:**

```python
import logging

# Скрыть технические детали загрузчика
logging.getLogger('bquant.data.loader').setLevel(logging.WARNING)

# Или для всех data модулей
logging.getLogger('bquant.data').setLevel(logging.WARNING)
```

**См. подробности:** [Управление логированием](../core/logging.md#управление-логированием-в-многомодульных-проектах)

## Замечания

- При `validate_data=True` используются внутренние проверки структуры (OHLCV) и консистентности.
- Поддерживаются различные форматы дат; при невозможности — будет предупреждение.

