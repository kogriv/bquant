# bquant.data.loader — Загрузка данных

## Обзор

Функции для загрузки OHLCV‑данных из CSV и по символу/таймфрейму на основе конфигурации. Включает нормализацию колонок, разбор дат, валидацию структуры.

## Основные функции

- `load_ohlcv_data(file_path, symbol=None, timeframe=None, validate_data=True) -> DataFrame`
  - Загружает CSV, нормализует имена колонок (`open/high/low/close/volume`), пытается распарсить дату, опционально валидирует структуру.

- `load_symbol_data(symbol, timeframe, data_source='tradingview', quote_provider='default', validate_data=True) -> DataFrame`
  - Находит путь с помощью `config.get_data_path()` и загружает файл.

- `load_xauusd_data(timeframe='1H', data_source='tradingview', quote_provider='oanda') -> DataFrame`
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

df = load_ohlcv_data('data/XAUUSD_1H.csv', symbol='XAUUSD', timeframe='1H')
print(get_data_info(df))
```

Загрузка по символу/таймфрейму:
```python
from bquant.data.loader import load_symbol_data

df = load_symbol_data('XAUUSD', '1H', data_source='tradingview', quote_provider='oanda')
```

Загрузка всех файлов:
```python
from bquant.data.loader import load_all_data_files

datasets = load_all_data_files()
print(list(datasets.keys()))
```

## Замечания

- При `validate_data=True` используются внутренние проверки структуры (OHLCV) и консистентности.
- Поддерживаются различные форматы дат; при невозможности — будет предупреждение.

