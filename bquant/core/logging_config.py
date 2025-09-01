"""
Конфигурация логгирования для BQuant

Централизованная настройка логгирования для всех модулей системы.
"""

import logging
import logging.config
import logging.handlers
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
    console_level: str = None,
    file_level: str = None,
    log_to_file: bool = None,
    log_file: Union[str, Path] = None,
    use_colors: bool = True,
    console_enabled: bool = True,
    reset_loggers: bool = False,
    # Новые параметры для модульного контроля
    modules_config: Optional[Dict[str, Dict[str, str]]] = None,
    profile: Optional[str] = None,
    exceptions: Optional[Dict[str, str]] = None
) -> logging.Logger:
    """
    Настроить систему логгирования BQuant
    
    Args:
        level: Общий уровень логгирования (если не указаны отдельные)
        console_level: Уровень для консольного вывода (INFO, WARNING, ERROR, etc.)
        file_level: Уровень для файлового логгирования
        log_to_file: Логгировать в файл
        log_file: Путь к файлу логов
        use_colors: Использовать цветовое выделение в консоли
        console_enabled: Включить консольный вывод
        reset_loggers: Сбросить существующие логгеры
        modules_config: Модульная настройка логгирования
            {'bquant.data': {'console': 'WARNING', 'file': 'INFO'}}
        profile: Предустановленный профиль ('research', 'debug', etc.)
        exceptions: Исключения для конкретных логгеров
            {'bquant.data.loader': 'ERROR'}
    
    Returns:
        Корневой логгер BQuant
    """
    # Получаем настройки из конфигурации
    level = level or LOGGING['level']
    console_level = console_level or level
    file_level = file_level or level
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
        'handlers': {},
        'loggers': {
            'bquant': {
                'level': 'DEBUG',  # Общий уровень - самый низкий, обработчики фильтруют
                'handlers': [],
                'propagate': False
            }
        }
    }
    
    # Добавляем консольный обработчик если включен
    if console_enabled:
        config['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'level': console_level,
            'formatter': 'console',
            'stream': sys.stdout
        }
        config['loggers']['bquant']['handlers'].append('console')
    
    # Добавляем файловый обработчик если нужно
    if log_to_file:
        # Создаем директорию для логов
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True, parents=True)
        
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': file_level,
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
    
    # Применяем модульные настройки если указаны
    if modules_config or profile or exceptions:
        _apply_modular_config(modules_config, profile, exceptions, console_level, file_level)
    
    # Логгируем успешную инициализацию
    if console_enabled:
        logger.info(f"Система логгирования BQuant инициализирована (консоль: {console_level})")
    if log_to_file:
        logger.info(f"Логи сохраняются в файл: {log_file} (уровень: {file_level})")
    
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


# ============================================================================
# АРХИТЕКТУРНЫЙ РЕФАКТОРИНГ: УДАЛЕНЫ ИЗБЫТОЧНЫЕ ФУНКЦИИ
# ============================================================================
#
# УСТАРЕЛИ (удалены для чистоты архитектуры):
# - setup_notebook_logging() 
# - setup_development_logging()
# - setup_production_logging()  
# - setup_quiet_logging()
#
# НОВЫЙ ЕДИНЫЙ API:
# setup_logging(profile='research')      # для notebook сценариев
# setup_logging(profile='verbose')       # для development
# setup_logging(profile='critical')      # для production
# setup_logging(profile='clean')         # для quiet сценариев
#
# ПРИЧИНА УДАЛЕНИЯ:
# - 4 функции делали одно и то же с разными дефолтами
# - Нарушение принципа DRY и архитектурное засорение
# - Усложнение поддержки (изменения в 4 местах)
# - Профили в data лучше чем функции в code
#


# =============================================================================
# МОДУЛЬНАЯ НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================

# Предустановленные профили логирования
LOGGING_PROFILES = {
    "research": {
        "description": "Для research скриптов - скрыть технические детали",
        "modules_config": {
            "bquant.data": {"console": "WARNING", "file": "INFO"},
            "bquant.data.loader": {"console": "WARNING", "file": "INFO"},
            "bquant.data.processor": {"console": "WARNING", "file": "INFO"},
            "bquant.data.validator": {"console": "WARNING", "file": "INFO"},
            "bquant.indicators": {"console": "WARNING", "file": "INFO"}, 
            "bquant.analysis": {"console": "INFO", "file": "INFO"}
        }
    },
    
    "clean": {
        "description": "Минимум шума - только ошибки в консоль",
        "modules_config": {
            "bquant.data": {"console": "ERROR", "file": "INFO"},
            "bquant.indicators": {"console": "ERROR", "file": "INFO"},
            "bquant.analysis": {"console": "ERROR", "file": "INFO"}
        }
    },
    
    "debug": {
        "description": "Все детали для отладки",
        "modules_config": {
            "bquant": {"console": "DEBUG", "file": "DEBUG"}
        }
    },
    
    "verbose": {
        "description": "Максимум информации везде",
        "modules_config": {
            "bquant": {"console": "DEBUG", "file": "DEBUG"}
        }
    },
    
    "focused": {
        "description": "Детали только для core, остальное - стандартно",
        "modules_config": {
            "bquant.core": {"console": "DEBUG", "file": "DEBUG"},
            "bquant.data": {"console": "INFO", "file": "DEBUG"},
            "bquant.indicators": {"console": "INFO", "file": "DEBUG"}
        }
    },
    
    "critical": {
        "description": "Только критические события",
        "modules_config": {
            "bquant": {"console": "ERROR", "file": "ERROR"}
        }
    },
    
    "audit": {
        "description": "Полный аудит в файл, минимум в консоль",
        "modules_config": {
            "bquant": {"console": "ERROR", "file": "INFO"}
        }
    }
}


def _apply_modular_config(
    modules_config: Optional[Dict[str, Dict[str, str]]] = None,
    profile: Optional[str] = None, 
    exceptions: Optional[Dict[str, str]] = None,
    default_console_level: str = "INFO",
    default_file_level: str = "INFO"
):
    """
    Применить модульную настройку логирования.
    
    Args:
        modules_config: Настройки модулей
        profile: Предустановленный профиль
        exceptions: Исключения для конкретных логгеров
        default_console_level: Уровень консоли по умолчанию
        default_file_level: Уровень файла по умолчанию
    """
    # Начинаем с профиля если указан
    final_config = {}
    if profile and profile in LOGGING_PROFILES:
        final_config = LOGGING_PROFILES[profile]["modules_config"].copy()
    
    # Добавляем/перезаписываем настройки модулей
    if modules_config:
        for module_name, module_settings in modules_config.items():
            if module_name not in final_config:
                final_config[module_name] = {}
            final_config[module_name].update(module_settings)
    
    # Применяем настройки к логгерам
    for module_name, settings in final_config.items():
        logger = logging.getLogger(module_name)
        
        # Настраиваем обработчики если они есть
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                # Console handler
                if "console" in settings:
                    handler.setLevel(getattr(logging, settings["console"].upper()))
            elif isinstance(handler, (logging.FileHandler, logging.handlers.RotatingFileHandler)):
                # File handler  
                if "file" in settings:
                    handler.setLevel(getattr(logging, settings["file"].upper()))
        
        # Если у логгера нет собственных обработчиков, он использует родительские
        # В этом случае настраиваем сам логгер
        if not logger.handlers:
            console_level = settings.get("console", default_console_level)
            # Устанавливаем уровень логгера на минимальный из console/file
            file_level = settings.get("file", default_file_level)
            min_level = min(
                getattr(logging, console_level.upper()),
                getattr(logging, file_level.upper())
            )
            logger.setLevel(min_level)
        
        # ДОПОЛНИТЕЛЬНО: Настраиваем все дочерние логгеры для этого модуля
        # Это важно для случаев когда логгер не имеет собственных обработчиков
        if "console" in settings:
            console_level = getattr(logging, settings["console"].upper())
            # Находим все дочерние логгеры и устанавливаем им уровень
            for logger_name in logging.getLogger().manager.loggerDict.keys():
                if logger_name.startswith(module_name + "."):
                    child_logger = logging.getLogger(logger_name)
                    # Устанавливаем уровень только если у дочернего логгера нет собственных обработчиков
                    if not child_logger.handlers:
                        child_logger.setLevel(console_level)
            
            # КРИТИЧНО: Настраиваем фильтры для корневого логгера bquant
            # чтобы он не пропускал сообщения от дочерних логгеров с низким уровнем
            root_logger = logging.getLogger('bquant')
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    # Создаем фильтр для скрытия сообщений от указанного модуля
                    class ModuleLevelFilter(logging.Filter):
                        def __init__(self, module_name, min_level):
                            self.module_name = module_name
                            self.min_level = min_level
                        
                        def filter(self, record):
                            # Если сообщение от указанного модуля, проверяем уровень
                            if record.name.startswith(self.module_name):
                                return record.levelno >= self.min_level
                            # Остальные сообщения пропускаем
                            return True
                    
                    # Добавляем фильтр к обработчику
                    handler.addFilter(ModuleLevelFilter(module_name, console_level))
    
    # Применяем исключения
    if exceptions:
        for logger_name, level in exceptions.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, level.upper()))


# =============================================================================
# FLUENT API
# =============================================================================

class LoggingConfigurator:
    """
    Fluent API для сложной настройки логирования.
    
    Examples:
        # Базовая настройка с профилем
        LoggingConfigurator().preset('notebook').apply()
        
        # Сложная настройка
        LoggingConfigurator()
            .preset('research')
            .module('bquant.data').console('WARNING').file('INFO')
            .module('bquant.indicators').console('ERROR')
            .exception('bquant.data.loader', 'DEBUG')
            .apply()
    """
    
    def __init__(self):
        self.config = {
            'preset_type': 'notebook',  # По умолчанию
            'preset_profile': None,
            'modules_config': {},
            'exceptions': {},
            'custom_params': {}
        }
        self._current_module = None
    
    def preset(self, preset_type: str, profile: Optional[str] = None):
        """
        Установить базовый preset.
        
        Args:
            preset_type: Тип preset ('notebook', 'development', 'production', 'quiet')
            profile: Профиль для preset ('research', 'debug', etc.)
        
        Returns:
            self для chaining
        """
        valid_presets = ['notebook', 'development', 'production', 'quiet']
        if preset_type not in valid_presets:
            raise ValueError(f"Invalid preset type. Valid options: {valid_presets}")
        
        self.config['preset_type'] = preset_type
        self.config['preset_profile'] = profile
        return self
    
    def module(self, module_name: str):
        """
        Начать настройку конкретного модуля.
        
        Args:
            module_name: Имя модуля (например, 'bquant.data')
            
        Returns:
            self для chaining
        """
        self._current_module = module_name
        if module_name not in self.config['modules_config']:
            self.config['modules_config'][module_name] = {}
        return self
    
    def console(self, level: str):
        """
        Настроить уровень консоли для текущего модуля.
        
        Args:
            level: Уровень логирования ('DEBUG', 'INFO', 'WARNING', 'ERROR')
            
        Returns:
            self для chaining
        """
        if self._current_module is None:
            raise ValueError("Call module() first to specify which module to configure")
        
        self.config['modules_config'][self._current_module]['console'] = level.upper()
        return self
    
    def file(self, level: str):
        """
        Настроить уровень файла для текущего модуля.
        
        Args:
            level: Уровень логирования ('DEBUG', 'INFO', 'WARNING', 'ERROR')
            
        Returns:
            self для chaining  
        """
        if self._current_module is None:
            raise ValueError("Call module() first to specify which module to configure")
        
        self.config['modules_config'][self._current_module]['file'] = level.upper()
        return self
    
    def exception(self, logger_name: str, level: str):
        """
        Добавить исключение для конкретного логгера.
        
        Args:
            logger_name: Полное имя логгера (например, 'bquant.data.loader')
            level: Уровень логирования
            
        Returns:
            self для chaining
        """
        self.config['exceptions'][logger_name] = level.upper()
        return self
    
    def param(self, key: str, value: Any):
        """
        Добавить кастомный параметр.
        
        Args:
            key: Имя параметра
            value: Значение параметра
            
        Returns:
            self для chaining
        """
        self.config['custom_params'][key] = value
        return self
    
    def apply(self) -> logging.Logger:
        """
        Применить настройки логирования.
        
        Returns:
            Настроенный логгер
        """
        preset_type = self.config['preset_type']
        profile = self.config['preset_profile']
        modules_config = self.config['modules_config'] if self.config['modules_config'] else None
        exceptions = self.config['exceptions'] if self.config['exceptions'] else None
        custom_params = self.config['custom_params']
        
        # Используем единую функцию setup_logging() с соответствующими параметрами
        # preset_type определяет базовые настройки, которые применяются через profile
        if preset_type == 'notebook':
            # Для notebook сценариев используем research профиль по умолчанию
            if not profile:
                profile = 'research'
        elif preset_type == 'development':
            # Для development сценариев используем verbose профиль по умолчанию
            if not profile:
                profile = 'verbose'
        elif preset_type == 'production':
            # Для production сценариев используем critical профиль по умолчанию
            if not profile:
                profile = 'critical'
        elif preset_type == 'quiet':
            # Для quiet сценариев используем clean профиль по умолчанию
            if not profile:
                profile = 'clean'
        else:
            raise ValueError(f"Unknown preset type: {preset_type}")
        
        # Вызываем единую функцию setup_logging()
        return setup_logging(
            profile=profile,
            modules_config=modules_config,
            exceptions=exceptions,
            **custom_params
        )
