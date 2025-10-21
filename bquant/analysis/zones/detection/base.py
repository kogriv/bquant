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
    
    CONTRACT (v2.1 - REQUIRED):
        All detection strategies MUST populate indicator_context in each ZoneInfo.
        
        REQUIRED fields in indicator_context:
        - 'detection_strategy': str - name of this strategy
        - 'detection_indicator': str - primary indicator column name
        
        OPTIONAL fields:
        - 'signal_line': Optional[str] - secondary indicator (if 2-line strategy)
        - 'detection_rules': dict - full rules dict (for reference)
        - Any other strategy-specific metadata
        
        Strategy is RESPONSIBLE for deciding:
        - Which of its parameters is the "primary indicator"
        - Which (if any) is the "signal line"
        - What metadata to include
        
        This enables:
        - Self-description (strategies interpret their own rules)
        - Agnosticism (Pipeline doesn't need to know parameter names)
        - Extensibility (new strategies can use ANY parameters)
    
    Example:
        class MyCustomDetection:
            def detect_zones(self, data: pd.DataFrame, 
                           config: ZoneDetectionConfig) -> List[ZoneInfo]:
                # Interpret your rules (strategy decides semantics)
                my_indicator = config.rules['my_custom_param']
                
                # Your detection logic
                # ...
                
                # Create ZoneInfo with indicator_context (REQUIRED!)
                zone = ZoneInfo(
                    zone_id=0,
                    type='bull',
                    start_idx=0,
                    end_idx=10,
                    start_time=data.index[0],
                    end_time=data.index[10],
                    duration=11,
                    data=data.iloc[0:11],
                    indicator_context={
                        'detection_strategy': 'my_custom',      # REQUIRED
                        'detection_indicator': my_indicator,    # REQUIRED
                        'signal_line': None,                    # OPTIONAL
                        'detection_rules': config.rules         # OPTIONAL
                    }
                )
                return [zone]
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
            List[ZoneInfo] - список обнаруженных зон с заполненным indicator_context
            
        Raises:
            ValueError: Если конфигурация некорректна
            
        Note:
            Implementation MUST populate indicator_context in each ZoneInfo
            according to v2.1 contract (see class docstring).
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


