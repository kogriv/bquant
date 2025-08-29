# Core Modules - Базовые модули BQuant

## 📚 Обзор

Core модули содержат базовую функциональность BQuant: конфигурацию, исключения, логирование, производительность и утилиты.

## 🗂️ Модули

### 🔧 [bquant.core.config](config.md) - Конфигурация и настройки
- Константы путей и конфигураций (PROJECT_ROOT, DATA_DIR, RESULTS_DIR, LOGGING, и др.)
- Помощники: `get_data_path()`, `get_indicator_params()`, `get_analysis_params()`, `validate_timeframe()`, `get_results_path()`, `get_cache_config()`

### ⚠️ [bquant.core.exceptions](exceptions.md) - Исключения и ошибки
- **BQuantError** - Базовое исключение BQuant
- **DataError** - Ошибки данных
- **AnalysisError** - Ошибки анализа
- **VisualizationError** - Ошибки визуализации

### 📝 [bquant.core.logging_config](logging.md) - Настройка логирования
- `setup_logging()` — инициализация логирования
- `get_logger()` — получение логгера (с контекстом)
- Декораторы и контекст логирования

### ⚡ [bquant.core.performance](performance.md) - Производительность и профилирование
- Декоратор `@performance_monitor` и контекст `performance_context`
- Глобальный монитор `PerformanceMonitor`, сбор и экспорт метрик
- Оптимизированные индикаторы (NumPy): `sma`, `ema`, `rsi`, `macd`, `bollinger_bands`

### 🛠️ [bquant.core.utils](utils.md) - Утилиты и вспомогательные функции
- `setup_project_logging()`, `calculate_returns()`, `normalize_data()`
- `save_results()`, `validate_ohlcv_columns()`, `create_timestamp()`
- `memory_usage_info()`, `ensure_directory()`

## 🔍 Быстрый поиск

### По функциональности

#### Конфигурация
- `get_data_path()` - Получение пути к данным
- `validate_timeframe()` - Проверка таймфрейма
- `get_indicator_params()` - Параметры индикатора

#### Логирование
- `setup_logging()` - Настройка логирования
- `get_logger()` - Получение логгера
- `logger.info()` - Информационные сообщения

#### Производительность
- `@performance_monitor` - Декоратор профилирования
- `performance_context()` - Контекстный менеджер
- `get_performance_monitor().get_stats()` - Получение метрик

#### Утилиты
- `validate_ohlcv_columns()` - Проверка структуры данных
- `calculate_returns()` - Доходности (simple/log)
- `normalize_data()` - Нормализация данных

### По типу

#### 🏗️ Классы
- `BQuantError` - Базовое исключение
- `PerformanceMonitor` - Сбор метрик

#### 🔧 Функции
- `setup_logging()` - Настройка логирования
- `get_logger()` - Получение логгера
- `validate_ohlcv_columns()` - Валидация данных

#### 📋 Исключения
- `BQuantError` - Базовое исключение
- `DataError` - Ошибки данных
- `AnalysisError` - Ошибки анализа

## 💡 Примеры использования

### Конфигурация

```python
from bquant.core.config import get_data_path, validate_timeframe

# Проверка таймфрейма
validate_timeframe('1h')

# Путь к данным TradingView/OANDA для XAUUSD 1h
path = get_data_path('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')
```

### Логирование

```python
from bquant.core.logging_config import setup_logging, get_logger

# Настройка логирования
setup_logging(level='INFO', log_file='bquant.log')

# Получение логгера
logger = get_logger(__name__)

# Использование логгера
logger.info("Starting analysis...")
logger.debug("Processing data...")
logger.warning("Data validation failed")
logger.error("Analysis failed")
```

### Производительность

```python
from bquant.core.performance import performance_monitor, performance_context

# Декоратор для профилирования
@performance_monitor
def slow_function():
    """Функция с профилированием"""
    import time
    time.sleep(1)
    return "result"

# Контекстный менеджер
with performance_context("data_processing"):
    # Код для профилирования
    process_large_dataset()
```

### Обработка ошибок

```python
from bquant.core.exceptions import BQuantError, DataError, AnalysisError

try:
    # Попытка загрузки данных
    data = load_data('invalid_file.csv')
except DataError as e:
    logger.error(f"Data error: {e}")
    # Обработка ошибки данных
except BQuantError as e:
    logger.error(f"BQuant error: {e}")
    # Обработка общей ошибки
```

### Утилиты

```python
from bquant.core.utils import validate_ohlcv_columns, calculate_returns

check = validate_ohlcv_columns(df)
if not check['is_valid']:
    raise DataError('; '.join(check['messages']))

ret = calculate_returns(df['close'], method='log')
```

## 🔗 Связанные разделы

- **[Data Modules](../data/README.md)** - Модули для работы с данными
- **[Indicators](../indicators/README.md)** - Технические индикаторы
- **[Analysis](../analysis/README.md)** - Аналитические модули
- **[Visualization](../visualization/README.md)** - Модули визуализации

## 📖 Детальная документация

- **[Config Module](config.md)** - Подробная документация конфигурации
- **[Exceptions Module](exceptions.md)** - Документация исключений
- **[Logging Module](logging.md)** - Документация логирования
- **[Performance Module](performance.md)** - Документация производительности
- **[Utils Module](utils.md)** - Документация утилит

---

**Следующий раздел:** [Data Modules](../data/README.md) 📊
