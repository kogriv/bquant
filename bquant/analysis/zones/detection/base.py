"""
Zone Detection - Base Protocol and Configuration

Этот модуль определяет базовый интерфейс для стратегий детекции зон:
- ZoneDetectionStrategy: Protocol для всех стратегий
- ZoneDetectionConfig: Универсальная конфигурация правил
"""

from typing import Protocol, runtime_checkable, List, Dict, Any
from dataclasses import dataclass, field
import pandas as pd

from ..models import ZoneInfo


@runtime_checkable
class ZoneDetectionStrategy(Protocol):
    """
    Протокол для стратегий определения зон.
    
    Все стратегии детекции должны реализовать метод detect_zones().
    
    Example:
        class MyDetectionStrategy:
            def detect_zones(self, data: pd.DataFrame, 
                           config: ZoneDetectionConfig) -> List[ZoneInfo]:
                # your logic here
                return zones
    """
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: 'ZoneDetectionConfig') -> List[ZoneInfo]:
        """
        Определить зоны на основе данных и правил.
        
        Args:
            data: DataFrame с OHLCV + индикаторами
            config: Конфигурация правил детекции
            
        Returns:
            List[ZoneInfo] - список обнаруженных зон
            
        Raises:
            ValueError: Если конфигурация некорректна
        """
        ...


@dataclass
class ZoneDetectionConfig:
    """
    Универсальная конфигурация правил определения зон.
    
    Attributes:
        min_duration: Минимальная длительность зоны в барах
        zone_types: Типы зон для поиска (None = все возможные для стратегии)
        rules: Специфичные правила для стратегии (Dict[str, Any])
        strategy_name: Имя стратегии для registry
        metadata: Дополнительная информация (для логирования, отладки)
    
    Example:
        # MACD zero crossing
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd_histogram'},
            strategy_name='zero_crossing'
        )
        
        # RSI thresholds
        config = ZoneDetectionConfig(
            min_duration=3,
            zone_types=['overbought', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            },
            strategy_name='threshold'
        )
    """
    min_duration: int = 2
    zone_types: List[str] = None
    rules: Dict[str, Any] = field(default_factory=dict)
    strategy_name: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = ['bull', 'bear']
    
    def validate(self, required_rules: List[str]) -> None:
        """
        Валидация наличия обязательных правил.
        
        Args:
            required_rules: Список обязательных ключей в self.rules
            
        Raises:
            ValueError: Если отсутствуют обязательные правила
        """
        missing = [r for r in required_rules if r not in self.rules]
        if missing:
            raise ValueError(
                f"Missing required rules for {self.strategy_name}: {missing}"
            )


# Экспорт
__all__ = [
    'ZoneDetectionStrategy',
    'ZoneDetectionConfig'
]


