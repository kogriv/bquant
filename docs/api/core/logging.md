# bquant.core.logging_config — Логирование

## Обзор

Централизованная настройка логгирования с гибкой конфигурацией для разных обработчиков, preset'ами для типовых сценариев, контекстными логгерами и декораторами.

## Основные функции

### Гибкая настройка
- `setup_logging(level=None, console_level=None, file_level=None, log_to_file=None, log_file=None, use_colors=True, console_enabled=True, reset_loggers=False) -> logging.Logger`
- `get_logger(name, context=None) -> logging.Logger | ContextualLogger`

### Preset конфигурации
- `setup_notebook_logging(console_level="WARNING", file_level="INFO", log_file=None) -> logging.Logger` - для Jupyter ноутбуков
- `setup_development_logging() -> logging.Logger` - для разработки (DEBUG везде)
- `setup_production_logging(log_file=None) -> logging.Logger` - для продакшена (только файл)
- `setup_quiet_logging() -> logging.Logger` - тихий режим (ERROR→консоль, INFO→файл)

## Ключевые классы

- `BQuantFormatter`: цветной форматтер для консоли с поддержкой ANSI кодов
- `ContextualLogger`: логгер, добавляющий контекст `[symbol=XAUUSD, timeframe=1h] сообщение`
- `LoggingContext`: контекстный менеджер для операций с замером времени

## Декораторы и утилиты

- Декораторы: `@log_function_call`, `@log_performance`
- Контекст: `LoggingContext(operation, logger_name='bquant', **context)`
- Быстрые шорткаты: `debug/info/warning/error/critical(message, **context)`

## Примеры

### Быстрая настройка для ноутбуков
```python
from bquant.core.logging_config import setup_notebook_logging

# WARNING+ в консоль, INFO+ в файл - одна строка!
setup_notebook_logging()

# Кастомные уровни
setup_notebook_logging(console_level="ERROR", file_level="DEBUG")
```

### Preset конфигурации
```python
from bquant.core.logging_config import (
    setup_development_logging,
    setup_production_logging,
    setup_quiet_logging
)

# Для разработки - DEBUG везде
setup_development_logging()

# Для продакшена - только файл
setup_production_logging()

# Тихий режим
setup_quiet_logging()
```

### Гибкая настройка
```python
from bquant.core.logging_config import setup_logging

# Разные уровни для консоли и файла
setup_logging(
    console_level="WARNING",
    file_level="INFO",
    log_to_file=True,
    use_colors=False
)

# Только файловое логирование
setup_logging(
    console_enabled=False,
    file_level="DEBUG",
    log_to_file=True
)
```

### Контекстный логгер
```python
from bquant.core.logging_config import get_logger

logger = get_logger(__name__, context={'symbol': 'XAUUSD', 'timeframe': '1h'})
logger.info("Загрузка данных")  # [symbol=XAUUSD, timeframe=1h] Загрузка данных
```

### Декораторы
```python
from bquant.core.logging_config import log_function_call, log_performance

@log_function_call
def load_data():
    return data

@log_performance  # Логирует время выполнения если > 1 сек
def slow_operation():
    # медленная операция
    pass
```

### Контекст операций
```python
from bquant.core.logging_config import LoggingContext

with LoggingContext("загрузка данных XAUUSD", symbol="XAUUSD", timeframe="1h"):
    data = load_data()
    # Автоматически логирует начало, конец и время выполнения
```

### Быстрые сообщения
```python
from bquant.core.logging_config import info, warning, error

info("Процесс запущен", symbol="XAUUSD")
warning("Найдены пропуски в данных", count=5)
error("Ошибка соединения", url="http://api.example.com")
```
