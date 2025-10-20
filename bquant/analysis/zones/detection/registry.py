"""
Zone Detection Registry - реестр стратегий детекции зон.

Обеспечивает:
- Автоматическую регистрацию стратегий через декоратор
- Хранение метаданных (описание, поддерживаемые зоны, обязательные параметры)
- Получение стратегий по имени
"""

from typing import Dict, Type, List, Any

from bquant.core.logging_config import get_logger

logger = get_logger(__name__)


class ZoneDetectionRegistry:
    """
    Реестр стратегий определения зон.
    
    Автоматическая регистрация через декоратор @register().
    Поддержка метаданных для каждой стратегии.
    
    Example:
        @ZoneDetectionRegistry.register(
            'zero_crossing',
            description='Detect zones by zero line crossing',
            supported_zones=['bull', 'bear'],
            required_rules=['indicator_col']
        )
        class ZeroCrossingDetection:
            def detect_zones(self, data, config):
                ...
    """
    
    _strategies: Dict[str, Type] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, 
                 description: str = "",
                 supported_zones: List[str] = None,
                 required_rules: List[str] = None):
        """
        Декоратор для регистрации стратегии.
        
        Args:
            name: Уникальное имя стратегии
            description: Человекочитаемое описание
            supported_zones: Типы зон, которые может обнаружить
            required_rules: Обязательные ключи в config.rules
            
        Example:
            @ZoneDetectionRegistry.register(
                'zero_crossing',
                description='Detect zones by indicator crossing zero line',
                supported_zones=['bull', 'bear'],
                required_rules=['indicator_col']
            )
            class ZeroCrossingDetection:
                def detect_zones(self, data, config):
                    ...
        """
        def decorator(strategy_class):
            if name in cls._strategies:
                logger.warning(f"Overwriting existing strategy: {name}")
            
            cls._strategies[name] = strategy_class
            cls._metadata[name] = {
                'description': description,
                'supported_zones': supported_zones or ['bull', 'bear'],
                'required_rules': required_rules or [],
                'class': strategy_class.__name__
            }
            
            logger.info(f"Registered zone detection strategy: {name}")
            return strategy_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **init_params):
        """
        Получить экземпляр стратегии по имени.
        
        Args:
            name: Имя зарегистрированной стратегии
            **init_params: Параметры для __init__ стратегии (если нужны)
            
        Returns:
            Экземпляр стратегии
            
        Raises:
            ValueError: Если стратегия не найдена
        """
        if name not in cls._strategies:
            available = ', '.join(cls.list_strategies())
            raise ValueError(
                f"Unknown zone detection strategy: '{name}'. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class(**init_params)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Список имен доступных стратегий."""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_info(cls, name: str) -> Dict[str, Any]:
        """
        Получить метаданные стратегии.
        
        Args:
            name: Имя стратегии
            
        Returns:
            Словарь с метаданными
            
        Raises:
            ValueError: Если стратегия не найдена
        """
        if name not in cls._metadata:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._metadata[name].copy()
    
    @classmethod
    def list_all_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Получить информацию обо всех стратегиях.
        
        Returns:
            Словарь {имя_стратегии: метаданные}
        """
        return cls._metadata.copy()


# Экспорт
__all__ = [
    'ZoneDetectionRegistry'
]
