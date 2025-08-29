# bquant.core.logging_config — Логирование

## Обзор

Централизованная настройка логгирования: форматтер, инициализация, контекстный логгер, декораторы и контексты для измерений/сообщений.

## Ключевые сущности

- `setup_logging(level=None, log_to_file=None, log_file=None, use_colors=True, reset_loggers=False) -> logging.Logger`
- `get_logger(name, context=None) -> logging.Logger | ContextualLogger`
- `BQuantFormatter`: цветной форматтер для консоли
- `ContextualLogger`: логгер, добавляющий контекст `symbol=..., timeframe=...`
- Декораторы: `@log_function_call`, `@log_performance`
- Контекст: `LoggingContext(operation, logger_name='bquant', **context)`
- Быстрые шорткаты: `debug/info/warning/error/critical(message, **context)`

## Примеры

Базовая инициализация и запись в файл:
```python
from bquant.core.logging_config import setup_logging, get_logger

setup_logging(level='INFO', log_to_file=True)
logger = get_logger(__name__)
logger.info("Запуск анализа")
```

Контекстный логгер:
```python
from bquant.core.logging_config import get_logger
logger = get_logger(__name__, context=dict(symbol='XAUUSD', timeframe='1h'))
logger.info("Загрузка данных")
```

Декораторы:
```python
from bquant.core.logging_config import log_function_call, log_performance

@log_function_call
def foo():
    return 42

@log_performance
def slow():
    import time; time.sleep(1.5)
```

Контекст операций:
```python
from bquant.core.logging_config import LoggingContext

with LoggingContext("загрузка данных", symbol="XAUUSD"):
    load_data()
```
