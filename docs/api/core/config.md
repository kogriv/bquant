# bquant.core.config — Конфигурация и пути

## Обзор

Модуль содержит константы путей проекта, конфигурации таймфреймов и шаблоны имён файлов данных, а также вспомогательные функции для получения путей и параметров.

## Основные константы

- `PROJECT_ROOT`: корень проекта
- `DATA_DIR`, `ALLDATA_DIR`, `PROCESSED_DATA_DIR`: директории данных
- `SCRIPTS_DIR`, `NOTEBOOKS_DIR`, `RESULTS_DIR`: служебные директории
- `TIMEFRAME_MAPPING`: соответствия таймфреймов для источников данных (`tradingview`, `metatrader`)
- `DATA_FILE_PATTERNS`: шаблоны имён файлов для разных источников
- `SUPPORTED_TIMEFRAMES`: поддерживаемые таймфреймы
- `DATA_VALIDATION`: правила валидации данных
- `CACHE_CONFIG`: настройки кэширования
- `LOGGING`: базовые настройки логирования

## Ключевые функции

- `get_data_path(symbol, timeframe, data_source='tradingview', quote_provider='default') -> Path`
  - Возвращает путь к файлу данных по символу и таймфрейму с учётом источника/провайдера.

- `get_indicator_params(indicator, **overrides) -> Dict[str, Any]`
  - Параметры индикатора по умолчанию с возможностью переопределения.

- `get_analysis_params(analysis_type, **overrides) -> Dict[str, Any]`
  - Параметры анализа по умолчанию с возможностью переопределения.

- `validate_timeframe(timeframe) -> str`
  - Проверяет, что таймфрейм поддерживается; иначе ValueError.

- `get_results_path(experiment_name, file_type='csv') -> Path`
  - Возвращает путь для сохранения результатов экспериментов.

- `get_cache_config() -> Dict[str, Any]`
  - Копия конфигурации кэша.

## Управление директориями

Новые функции для динамического управления путями директорий:

### Getter функции
- `get_data_dir() -> Path` — Получить текущий путь к директории данных
- `get_results_dir() -> Path` — Получить путь к директории результатов  
- `get_notebooks_dir() -> Path` — Получить путь к директории ноутбуков
- `get_processed_data_dir() -> Path` — Получить путь к директории обработанных данных

### Setter функции
- `set_data_dir(path) -> None` — Установить новый путь к директории данных
- `set_results_dir(path) -> None` — Установить путь к директории результатов
- `set_notebooks_dir(path) -> None` — Установить путь к директории ноутбуков  
- `set_processed_data_dir(path) -> None` — Установить путь к директории обработанных данных

### Утилиты
- `reset_directories_to_defaults() -> None` — Сбросить все пути к значениям по умолчанию
- `get_directory_status() -> Dict[str, Any]` — Получить информацию о текущих путях

## Примеры

Получение пути к данным TradingView:
```python
from bquant.core.config import get_data_path

# OANDA XAUUSD, TradingView 1h
path = get_data_path('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')
print(path)
```

Проверка таймфрейма:
```python
from bquant.core.config import validate_timeframe

validate_timeframe('1h')   # '1h'
validate_timeframe('2D')   # ValueError
```

Параметры индикатора:
```python
from bquant.core.config import get_indicator_params

macd_params = get_indicator_params('macd', fast=8)
```

Путь для результатов:
```python
from bquant.core.config import get_results_path

csv_path = get_results_path('zone_analysis_2025-08-29', file_type='csv')
```

Управление директориями:
```python
from bquant.core.config import (
    get_data_dir, set_data_dir, get_directory_status, reset_directories_to_defaults
)

# Получить текущий путь к данным
current_data_dir = get_data_dir()

# Установить кастомный путь
set_data_dir('/custom/data/path')

# Проверить статус всех директорий
status = get_directory_status()
print(status['data_dir']['is_custom'])  # True

# Сбросить к умолчаниям
reset_directories_to_defaults()
```
