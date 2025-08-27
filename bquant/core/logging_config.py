"""
Конфигурация логгирования для BQuant

Централизованная настройка логгирования для всех модулей системы.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

from .config import LOGGING, PROJECT_ROOT


class BQuantFormatter(logging.Formatter):
    """
    Кастомный форматтер для BQuant с цветовой поддержкой
    """
    
    # Цветовые коды ANSI
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, use_colors: bool = True, *args, **kwargs):
        """
        Args:
            use_colors: Использовать цветовое выделение для консоли
        """
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматировать запись лога"""
        # Добавляем информацию о модуле если не указана
        if not hasattr(record, 'module_name'):
            record.module_name = record.name.split('.')[-1] if '.' in record.name else record.name
        
        # Форматируем базовое сообщение
        formatted = super().format(record)
        
        # Добавляем цветовое выделение для консоли
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            reset = self.COLORS['RESET']
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


class ContextualLogger:
    """
    Логгер с контекстной информацией
    """
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Args:
            name: Имя логгера
            context: Контекстная информация (symbol, timeframe, etc.)
        """
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _format_message(self, message: str) -> str:
        """Добавить контекст к сообщению"""
        if self.context:
            context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
            return f"[{context_str}] {message}"
        return message
    
    def debug(self, message: str, **kwargs):
        """Debug сообщение с контекстом"""
        self.logger.debug(self._format_message(message), **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info сообщение с контекстом"""
        self.logger.info(self._format_message(message), **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning сообщение с контекстом"""
        self.logger.warning(self._format_message(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error сообщение с контекстом"""
        self.logger.error(self._format_message(message), **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical сообщение с контекстом"""
        self.logger.critical(self._format_message(message), **kwargs)


def setup_logging(
    level: str = None,
    log_to_file: bool = None,
    log_file: Union[str, Path] = None,
    use_colors: bool = True,
    reset_loggers: bool = False
) -> logging.Logger:
    """
    Настроить систему логгирования BQuant
    
    Args:
        level: Уровень логгирования
        log_to_file: Логгировать в файл
        log_file: Путь к файлу логов
        use_colors: Использовать цветовое выделение
        reset_loggers: Сбросить существующие логгеры
    
    Returns:
        Корневой логгер BQuant
    """
    # Получаем настройки из конфигурации
    level = level or LOGGING['level']
    log_to_file = log_to_file if log_to_file is not None else LOGGING['file_logging']
    log_file = log_file or LOGGING['log_file']
    
    # Сбрасываем существующие логгеры если нужно
    if reset_loggers:
        for logger_name in list(logging.getLogger().manager.loggerDict.keys()):
            if logger_name.startswith('bquant'):
                logger = logging.getLogger(logger_name)
                logger.handlers.clear()
                logger.propagate = True
    
    # Конфигурация логгирования
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'console': {
                '()': BQuantFormatter,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%H:%M:%S',
                'use_colors': use_colors
            },
            'file': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'console',
                'stream': sys.stdout
            }
        },
        'loggers': {
            'bquant': {
                'level': level,
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Добавляем файловый обработчик если нужно
    if log_to_file:
        # Создаем директорию для логов
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True, parents=True)
        
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': level,
            'formatter': 'file',
            'filename': str(log_file),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'encoding': 'utf-8'
        }
        
        # Добавляем файловый обработчик к логгеру
        config['loggers']['bquant']['handlers'].append('file')
    
    # Применяем конфигурацию
    logging.config.dictConfig(config)
    
    # Получаем корневой логгер
    logger = logging.getLogger('bquant')
    
    # Логгируем успешную инициализацию
    logger.info(f"Система логгирования BQuant инициализирована (уровень: {level})")
    if log_to_file:
        logger.info(f"Логи сохраняются в файл: {log_file}")
    
    return logger


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> Union[logging.Logger, ContextualLogger]:
    """
    Получить логгер для модуля
    
    Args:
        name: Имя логгера (обычно __name__)
        context: Контекстная информация
    
    Returns:
        Logger или ContextualLogger с контекстом
    """
    # Убеждаемся что система логгирования инициализирована
    if not logging.getLogger('bquant').handlers:
        setup_logging()
    
    # Формируем полное имя логгера
    if not name.startswith('bquant'):
        if name == '__main__':
            logger_name = 'bquant.main'
        else:
            logger_name = f'bquant.{name}'
    else:
        logger_name = name
    
    # Возвращаем контекстный логгер если есть контекст
    if context:
        return ContextualLogger(logger_name, context)
    
    return logging.getLogger(logger_name)


def log_function_call(func):
    """
    Декоратор для логгирования вызовов функций
    
    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            return result
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__ or 'unknown')
        
        # Логгируем вызов функции
        func_name = f"{func.__module__}.{func.__name__}" if func.__module__ else func.__name__
        logger.debug(f"Вызов функции: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Функция {func_name} выполнена успешно")
            return result
        except Exception as e:
            logger.error(f"Ошибка в функции {func_name}: {e}")
            raise
    
    return wrapper


def log_performance(func):
    """
    Декоратор для логгирования производительности функций
    
    Usage:
        @log_performance
        def slow_function():
            # some slow operation
            pass
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__ or 'unknown')
        
        func_name = f"{func.__module__}.{func.__name__}" if func.__module__ else func.__name__
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Логгируем только если выполнение > 1 секунды
                logger.info(f"Функция {func_name} выполнена за {execution_time:.2f} сек")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Функция {func_name} завершилась с ошибкой за {execution_time:.2f} сек: {e}")
            raise
    
    return wrapper


class LoggingContext:
    """
    Контекстный менеджер для логгирования операций
    
    Usage:
        with LoggingContext("загрузка данных", symbol="XAUUSD"):
            data = load_data()
    """
    
    def __init__(self, operation: str, logger_name: str = 'bquant', **context):
        """
        Args:
            operation: Описание операции
            logger_name: Имя логгера
            **context: Контекстная информация
        """
        self.operation = operation
        self.context = context
        self.logger = get_logger(logger_name, context)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Начало операции: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Операция '{self.operation}' завершена успешно за {duration.total_seconds():.2f} сек")
        else:
            self.logger.error(f"Операция '{self.operation}' завершилась с ошибкой за {duration.total_seconds():.2f} сек: {exc_val}")
        
        return False  # Не подавляем исключение


# Инициализируем логгирование при импорте модуля
_root_logger = None

def ensure_logging_initialized():
    """Убедиться что логгирование инициализировано"""
    global _root_logger
    if _root_logger is None:
        _root_logger = setup_logging()
    return _root_logger


# Экспортируемые функции для быстрого доступа
def debug(message: str, **context):
    """Быстрое debug сообщение"""
    logger = get_logger('bquant.quick', context if context else None)
    logger.debug(message)

def info(message: str, **context):
    """Быстрое info сообщение"""
    logger = get_logger('bquant.quick', context if context else None)
    logger.info(message)

def warning(message: str, **context):
    """Быстрое warning сообщение"""
    logger = get_logger('bquant.quick', context if context else None)
    logger.warning(message)

def error(message: str, **context):
    """Быстрое error сообщение"""
    logger = get_logger('bquant.quick', context if context else None)
    logger.error(message)

def critical(message: str, **context):
    """Быстрое critical сообщение"""
    logger = get_logger('bquant.quick', context if context else None)
    logger.critical(message)
