"""
Дизайн расширенного API для модульной настройки логирования BQuant.

Этот файл содержит проектные решения для доработки всех setup_*_logging функций
с поддержкой гранулярного контроля на уровне модулей.
"""

from typing import Dict, Union, Optional, Literal
from pathlib import Path

# Типы для API
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ModuleConfig = Dict[str, Dict[str, LogLevel]]  # {'bquant.data': {'console': 'WARNING', 'file': 'INFO'}}
ProfileName = Literal["research", "debug", "clean", "verbose", "focused", "critical", "audit"]


# =============================================================================
# 1. РАСШИРЕННЫЕ ФУНКЦИИ С МОДУЛЬНОЙ ПОДДЕРЖКОЙ
# =============================================================================

def setup_notebook_logging(
    console_level: LogLevel = "WARNING",
    file_level: LogLevel = "INFO", 
    log_file: Optional[Union[str, Path]] = None,
    # ↓ НОВЫЕ ПАРАМЕТРЫ
    modules_config: Optional[ModuleConfig] = None,
    profile: Optional[ProfileName] = None,
    exceptions: Optional[Dict[str, LogLevel]] = None,
    reset_loggers: bool = True
):
    """
    Настройка логгирования для Jupyter ноутбуков с модульным контролем.
    
    Args:
        console_level: Уровень по умолчанию для консоли
        file_level: Уровень по умолчанию для файла
        log_file: Путь к файлу логов
        modules_config: Детальная настройка модулей
            {'bquant.data': {'console': 'WARNING', 'file': 'INFO'}}
        profile: Предустановленный профиль ('research', 'debug', 'clean')
        exceptions: Исключения для конкретных логгеров
            {'bquant.data.loader': 'ERROR'}
        reset_loggers: Сбросить существующие логгеры
    
    Examples:
        # Базовое использование (без изменений)
        setup_notebook_logging()
        
        # Модульная настройка
        setup_notebook_logging(
            modules_config={
                'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
                'bquant.indicators': {'console': 'ERROR', 'file': 'INFO'}
            }
        )
        
        # Профиль + исключения
        setup_notebook_logging(
            profile='research',
            exceptions={'bquant.data.loader': 'ERROR'}
        )
    """
    pass  # Реализация будет в следующем шаге


def setup_development_logging(
    console_level: LogLevel = "DEBUG",
    file_level: LogLevel = "DEBUG",
    log_file: Optional[Union[str, Path]] = None,
    # ↓ НОВЫЕ ПАРАМЕТРЫ  
    modules_config: Optional[ModuleConfig] = None,
    profile: Optional[ProfileName] = None,
    exceptions: Optional[Dict[str, LogLevel]] = None,
    reset_loggers: bool = True
):
    """
    Настройка логгирования для разработки с модульным контролем.
    
    Examples:
        # Focused debugging - только core модули детально
        setup_development_logging(
            profile='focused',
            modules_config={
                'bquant.core': {'console': 'DEBUG', 'file': 'DEBUG'},
                'bquant.data': {'console': 'INFO', 'file': 'DEBUG'}
            }
        )
    """
    pass


def setup_production_logging(
    log_file: Optional[Union[str, Path]] = None,
    file_level: LogLevel = "INFO",
    # ↓ НОВЫЕ ПАРАМЕТРЫ
    modules_config: Optional[ModuleConfig] = None, 
    profile: Optional[ProfileName] = None,
    exceptions: Optional[Dict[str, LogLevel]] = None,
    reset_loggers: bool = True
):
    """
    Настройка логгирования для продакшена с модульным контролем.
    
    Examples:
        # Критические модули - более детально
        setup_production_logging(
            profile='critical',
            modules_config={
                'bquant.data.loader': {'file': 'DEBUG'},  # Важные данные
                'bquant.indicators': {'file': 'INFO'},    # Стандартно
            }
        )
    """
    pass


def setup_quiet_logging(
    console_level: LogLevel = "ERROR",
    file_level: LogLevel = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    # ↓ НОВЫЕ ПАРАМЕТРЫ
    modules_config: Optional[ModuleConfig] = None,
    profile: Optional[ProfileName] = None, 
    exceptions: Optional[Dict[str, LogLevel]] = None,
    reset_loggers: bool = True
):
    """
    Тихое логгирование с модульным контролем.
    """
    pass


def setup_logging(
    level: Optional[LogLevel] = None,
    console_level: Optional[LogLevel] = None,
    file_level: Optional[LogLevel] = None, 
    log_to_file: Optional[bool] = None,
    log_file: Optional[Union[str, Path]] = None,
    use_colors: bool = True,
    console_enabled: bool = True,
    reset_loggers: bool = False,
    # ↓ НОВЫЕ ПАРАМЕТРЫ
    modules_config: Optional[ModuleConfig] = None,
    profile: Optional[ProfileName] = None,
    exceptions: Optional[Dict[str, LogLevel]] = None
):
    """
    Базовая функция настройки логгирования с полным контролем.
    """
    pass


# =============================================================================
# 2. ПРЕДУСТАНОВЛЕННЫЕ ПРОФИЛИ
# =============================================================================

LOGGING_PROFILES = {
    # Профили для setup_notebook_logging()
    "research": {
        "description": "Для research скриптов - скрыть технические детали",
        "modules_config": {
            "bquant.data": {"console": "WARNING", "file": "INFO"},
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
    
    # Профили для setup_development_logging()
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
    
    # Профили для setup_production_logging()
    "critical": {
        "description": "Только критические события",
        "modules_config": {
            "bquant": {"file": "ERROR"}
        }
    },
    
    "audit": {
        "description": "Полный аудит в файл, минимум в консоль",
        "modules_config": {
            "bquant": {"console": "ERROR", "file": "INFO"}
        }
    }
}


# =============================================================================
# 3. FLUENT API (ОПЦИОНАЛЬНО)
# =============================================================================

class LoggingConfigurator:
    """
    Fluent API для сложной настройки логирования.
    
    Example:
        LoggingConfigurator()
            .preset('notebook')
            .module('bquant.data').console('WARNING').file('INFO')
            .module('bquant.indicators').console('ERROR')
            .simulator_protection(True)
            .apply()
    """
    
    def __init__(self):
        self.config = {
            'preset': None,
            'modules_config': {},
            'exceptions': {},
            'simulator_protection': True
        }
    
    def preset(self, preset_name: str):
        """Применить базовый preset."""
        self.config['preset'] = preset_name
        return self
    
    def module(self, module_name: str):
        """Начать настройку конкретного модуля."""
        self._current_module = module_name
        if module_name not in self.config['modules_config']:
            self.config['modules_config'][module_name] = {}
        return self
    
    def console(self, level: LogLevel):
        """Настроить уровень консоли для текущего модуля."""
        self.config['modules_config'][self._current_module]['console'] = level
        return self
    
    def file(self, level: LogLevel):
        """Настроить уровень файла для текущего модуля."""
        self.config['modules_config'][self._current_module]['file'] = level
        return self
    
    def simulator_protection(self, enabled: bool = True):
        """Включить защиту NotebookSimulator (всегда по умолчанию)."""
        self.config['simulator_protection'] = enabled
        return self
    
    def apply(self):
        """Применить настройки."""
        # Здесь будет логика применения конфигурации
        pass


# =============================================================================
# 4. ОБРАТНАЯ СОВМЕСТИМОСТЬ
# =============================================================================

# Все существующие вызовы должны работать без изменений:
# setup_notebook_logging()  -> работает как раньше
# setup_development_logging() -> работает как раньше  
# setup_production_logging() -> работает как раньше
# setup_quiet_logging() -> работает как раньше
# setup_logging() -> работает как раньше

# Новые возможности добавляются через опциональные параметры