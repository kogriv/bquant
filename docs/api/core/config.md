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
