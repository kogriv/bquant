# Core Modules - Базовые модули BQuant

## 📚 Обзор

Core модули содержат базовую функциональность BQuant: конфигурацию, исключения, логирование, производительность и утилиты.

## 🗂️ Модули

### 🔧 [bquant.core.config](config.md) - Конфигурация и настройки
- **ConfigManager** - Управление конфигурацией приложения
- **Settings** - Настройки по умолчанию
- **Environment** - Переменные окружения

### ⚠️ [bquant.core.exceptions](exceptions.md) - Исключения и ошибки
- **BQuantError** - Базовое исключение BQuant
- **DataError** - Ошибки данных
- **AnalysisError** - Ошибки анализа
- **VisualizationError** - Ошибки визуализации

### 📝 [bquant.core.logging_config](logging.md) - Настройка логирования
- **setup_logging()** - Настройка системы логирования
- **get_logger()** - Получение логгера
- **LogLevels** - Уровни логирования

### ⚡ [bquant.core.performance](performance.md) - Производительность и профилирование
- **performance_monitor** - Декоратор для профилирования
- **performance_context** - Контекстный менеджер
- **CacheManager** - Управление кэшем

### 🛠️ [bquant.core.utils](utils.md) - Утилиты и вспомогательные функции
- **data_utils** - Утилиты для работы с данными
- **math_utils** - Математические утилиты
- **validation_utils** - Утилиты валидации

## 🔍 Быстрый поиск

### По функциональности

#### Конфигурация
- `ConfigManager.get_setting()` - Получение настройки
- `ConfigManager.set_setting()` - Установка настройки
- `ConfigManager.load_config()` - Загрузка конфигурации

#### Логирование
- `setup_logging()` - Настройка логирования
- `get_logger()` - Получение логгера
- `logger.info()` - Информационные сообщения

#### Производительность
- `@performance_monitor` - Декоратор профилирования
- `performance_context()` - Контекстный менеджер
- `CacheManager.get()` - Получение из кэша

#### Утилиты
- `validate_dataframe()` - Валидация DataFrame
- `calculate_statistics()` - Расчет статистики
- `format_number()` - Форматирование чисел

### По типу

#### 🏗️ Классы
- `ConfigManager` - Управление конфигурацией
- `CacheManager` - Управление кэшем
- `BQuantError` - Базовое исключение

#### 🔧 Функции
- `setup_logging()` - Настройка логирования
- `get_logger()` - Получение логгера
- `validate_dataframe()` - Валидация данных

#### 📋 Исключения
- `BQuantError` - Базовое исключение
- `DataError` - Ошибки данных
- `AnalysisError` - Ошибки анализа

## 💡 Примеры использования

### Конфигурация

```python
from bquant.core.config import ConfigManager

# Создание менеджера конфигурации
config = ConfigManager()

# Получение настройки
cache_enabled = config.get_setting('cache.enabled', default=True)

# Установка настройки
config.set_setting('performance.timeout', 30)

# Загрузка конфигурации из файла
config.load_config('config.yaml')
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
from bquant.core.utils import validate_dataframe, calculate_statistics

# Валидация DataFrame
is_valid = validate_dataframe(df, required_columns=['open', 'high', 'low', 'close'])

if not is_valid:
    raise DataError("Invalid DataFrame format")

# Расчет статистики
stats = calculate_statistics(df['close'])
print(f"Mean: {stats['mean']:.2f}")
print(f"Std: {stats['std']:.2f}")
```

## 🔗 Связанные разделы

- **[Data Modules](../data/)** - Модули для работы с данными
- **[Indicators](../indicators/)** - Технические индикаторы
- **[Analysis](../analysis/)** - Аналитические модули
- **[Visualization](../visualization/)** - Модули визуализации

## 📖 Детальная документация

- **[Config Module](config.md)** - Подробная документация конфигурации
- **[Exceptions Module](exceptions.md)** - Документация исключений
- **[Logging Module](logging.md)** - Документация логирования
- **[Performance Module](performance.md)** - Документация производительности
- **[Utils Module](utils.md)** - Документация утилит

---

**Следующий раздел:** [Data Modules](../data/) 📊
