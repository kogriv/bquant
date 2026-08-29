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

### 📓 [bquant.core.nb](nb.md) - Notebook-Style Scripts API
- **NotebookSimulator** - Класс для управления пошаговым выполнением скриптов
- Утилиты логирования: `log()`, `success()`, `error()`, `warning()`, `info()`
- Интерактивное управление: `step()`, `wait()`, `substep()`
- Настройка окружения: `setup_logging()`, `set_trap_mode()`

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
- `@performance_monitor()` - Декоратор профилирования
- `performance_context()` - Контекстный менеджер
- `get_performance_monitor().get_stats()` - Получение метрик

#### Утилиты
- `validate_ohlcv_columns()` - Проверка структуры данных
- `calculate_returns()` - Доходности (simple/log)
- `normalize_data()` - Нормализация данных

#### Notebook-style скрипты
- `NotebookSimulator()` - Создание runner для скрипта
- `step()` / `wait()` - Пошаговое выполнение
- `success()` / `error()` - Логирование с эмодзи

### По типу

#### 🏗️ Классы
- `BQuantError` - Базовое исключение
- `PerformanceMonitor` - Сбор метрик
- `NotebookSimulator` - Управление notebook-style скриптами

#### 🔧 Функции
- `setup_logging()` - Настройка логирования
- `get_logger()` - Получение логгера
- `validate_ohlcv_columns()` - Валидация данных

#### 📋 Исключения
- `BQuantError` - Базовое исключение
- `DataError` - Ошибки данных
- `AnalysisError` - Ошибки анализа

### 🧩 Совместимость с numpy

`bquant.core` поднимает три функции из `bquant.core.numpy_fix` и константу `NaN`.
**Вызывать функции вручную не нужно** — `apply_numpy_fixes()` выполняется сам при
импорте модуля, до того как пакетом начнут пользоваться. Экспортированы они, чтобы
состояние совместимости можно было *спросить*, а не чтобы им управлять.

- `apply_numpy_fixes()` — восстанавливает `np.NaN`, убранный в numpy 2.x, от
  которого зависят некоторые сторонние библиотеки. Идемпотентна: если атрибут уже
  есть, ничего не делает.
- `ensure_numpy_compatibility()` — то же самое, но сперва проверяет, нужно ли.
  Пригодна как явный вызов перед импортом библиотеки, ломающейся о numpy 2.x.
- `check_numpy_compatibility() -> dict` — отчёт, ничего не меняет. Ключи:
  `numpy_version`, `has_nan`, `has_NaN`, `fixes_applied`, `issues`.

```python
from bquant.core import check_numpy_compatibility

info = check_numpy_compatibility()
print(sorted(info))
# ['fixes_applied', 'has_NaN', 'has_nan', 'issues', 'numpy_version']
```

`fixes_applied` отвечает на вопрос «понадобилось ли чинить», а не «вызывали ли
функцию»: на numpy, где `NaN` на месте, там будет `False`.

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
@performance_monitor()
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

### Notebook-style скрипты

```python
from bquant.core.nb import NotebookSimulator

# Создание и настройка runner
runner = NotebookSimulator("Data Analysis Script", auto_setup=False)
runner.setup_logging('analysis.log')

# Пошаговое выполнение
runner.step("Loading Data")
# код загрузки данных
runner.success("Data loaded successfully")
runner.wait()

runner.step("Processing Data")
# код обработки
runner.success("Processing completed")
runner.wait()

runner.finish()
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
- **[Notebook-Style API](nb.md)** - Документация notebook-style скриптов

---

**Следующий раздел:** [Data Modules](../data/README.md) 📊
