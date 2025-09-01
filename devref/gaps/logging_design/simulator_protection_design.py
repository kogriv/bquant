"""
NotebookSimulator Protection Mechanism Design

Хотя NotebookSimulator технически независим от Python logging,
добавляем концептуальную "защиту" для документированного API.
"""

from typing import Optional, Dict, Any
import logging


def apply_simulator_protection(config: Dict[str, Any], enabled: bool = True):
    """
    Применить защиту NotebookSimulator к конфигурации логирования.
    
    Args:
        config: Конфигурация логирования
        enabled: Включить защиту (по умолчанию True)
        
    Note:
        Технически NotebookSimulator независим от Python logging,
        поэтому эта функция больше концептуальная/документационная.
        
        В будущем может быть расширена если появятся интеграции.
    """
    if not enabled:
        return config
    
    # Концептуальная защита - убеждаемся что любые логгеры
    # связанные с notebook/simulator не затрагиваются
    
    protected_patterns = [
        'notebook',
        'simulator', 
        'nb_',
        'script_'
    ]
    
    # В modules_config исключаем protected паттерны
    if 'modules_config' in config:
        modules_to_remove = []
        for module_name in config['modules_config']:
            if any(pattern in module_name.lower() for pattern in protected_patterns):
                modules_to_remove.append(module_name)
        
        for module_name in modules_to_remove:
            del config['modules_config'][module_name]
            print(f"🛡️ Protected module '{module_name}' from logging configuration")
    
    # Добавляем метаданные о защите
    config['_simulator_protection'] = {
        'enabled': True,
        'protected_patterns': protected_patterns,
        'note': 'NotebookSimulator uses independent logging (print + file)'
    }
    
    return config


def check_simulator_compatibility(logger_name: str) -> bool:
    """
    Проверить совместимость логгера с NotebookSimulator.
    
    Args:
        logger_name: Имя логгера для проверки
        
    Returns:
        True если логгер безопасен для настройки
        
    Note:
        Все BQuant логгеры ('bquant.*') безопасны для настройки,
        так как NotebookSimulator использует независимую систему.
    """
    # NotebookSimulator не использует Python logging
    # Все bquant.* логгеры безопасны для настройки
    
    if logger_name.startswith('bquant.'):
        return True
    
    # Гипотетические небезопасные паттерны (на будущее)
    unsafe_patterns = [
        'notebook_simulator',
        'nb_internal',
        'script_runner'
    ]
    
    for pattern in unsafe_patterns:
        if pattern in logger_name.lower():
            return False
    
    return True


def validate_logging_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидировать конфигурацию логирования на совместимость.
    
    Args:
        config: Конфигурация для валидации
        
    Returns:
        Валидированная и исправленная конфигурация
    """
    validated_config = config.copy()
    
    # Проверяем modules_config
    if 'modules_config' in validated_config:
        safe_modules = {}
        
        for module_name, module_config in validated_config['modules_config'].items():
            if check_simulator_compatibility(module_name):
                safe_modules[module_name] = module_config
            else:
                print(f"⚠️ Skipping potentially incompatible module: {module_name}")
        
        validated_config['modules_config'] = safe_modules
    
    # Проверяем exceptions
    if 'exceptions' in validated_config:
        safe_exceptions = {}
        
        for logger_name, level in validated_config['exceptions'].items():
            if check_simulator_compatibility(logger_name):
                safe_exceptions[logger_name] = level
            else:
                print(f"⚠️ Skipping potentially incompatible exception: {logger_name}")
        
        validated_config['exceptions'] = safe_exceptions
    
    return validated_config


# =============================================================================
# ИНТЕГРАЦИЯ В ОСНОВНЫЕ ФУНКЦИИ
# =============================================================================

def enhanced_setup_logging_with_protection(
    modules_config: Optional[Dict] = None,
    simulator_protection: bool = True,
    **kwargs
):
    """
    Пример интеграции защиты в основную функцию.
    """
    config = {
        'modules_config': modules_config or {},
        **kwargs
    }
    
    # Применяем защиту
    if simulator_protection:
        config = apply_simulator_protection(config, enabled=True)
        config = validate_logging_config(config)
    
    # Здесь была бы основная логика setup_logging
    print("🔧 Applying enhanced logging configuration with protection")
    return config


# =============================================================================
# ДОКУМЕНТАЦИЯ И ПРИМЕРЫ
# =============================================================================

"""
ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:

# 1. Автоматическая защита (по умолчанию)
setup_notebook_logging(
    modules_config={
        'bquant.data': {'console': 'WARNING'},
        'notebook_simulator': {'console': 'DEBUG'}  # <- Будет исключен автоматически
    }
)

# 2. Отключение защиты (если точно знаете что делаете)  
setup_notebook_logging(
    modules_config={...},
    simulator_protection=False  # Отключить все проверки
)

# 3. Fluent API с защитой
LoggingConfigurator()
    .preset('notebook') 
    .module('bquant.data').console('WARNING')
    .simulator_protection(True)  # Включена по умолчанию
    .apply()

ТЕХНИЧЕСКАЯ ЗАМЕТКА:
Эта система защиты больше концептуальная, так как NotebookSimulator
технически независим. Но она полезна для:
- Документирования лучших практик
- Предотвращения случайных ошибок конфигурации  
- Возможных будущих интеграций
"""