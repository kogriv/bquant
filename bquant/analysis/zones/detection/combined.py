"""
Combined Rules Detection Strategy

Стратегия детекции зон по комбинации условий с AND/OR логикой.

Применение:
- Кастомные торговые правила
- Комбинация нескольких индикаторов
- Сложная логика определения зон
"""

import pandas as pd
import numpy as np
from typing import List, Callable, Literal

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'combined',
    description='Detect zones by combining multiple conditions with AND/OR logic',
    supported_zones=['custom'],
    required_rules=['conditions']
)
class CombinedRulesDetection:
    """
    Стратегия: детекция зон по комбинации условий.
    
    Применение:
        - Кастомные торговые правила
        - Комбинация нескольких индикаторов
        - Сложная логика определения зон
        
    Правила (config.rules):
        - conditions: List[Callable] (обязательно) - список функций-условий
        - logic: 'AND' | 'OR' (опционально, default='AND')
        - zone_type_map: Dict[bool, str] (опционально) - маппинг результата на тип зоны
        
    Example:
        # AND logic - все условия должны быть True
        conditions = [
            lambda df: df['macd'] > 0,
            lambda df: df['rsi'] < 70,
            lambda df: df['close'] > df['sma_50']
        ]
        config = ZoneDetectionConfig(
            min_duration=3,
            zone_types=['bull_confirmed'],
            rules={
                'conditions': conditions,
                'logic': 'AND',
                'zone_type_map': {True: 'bull_confirmed', False: 'other'}
            }
        )
        
        # OR logic - хотя бы одно условие True
        conditions = [
            lambda df: df['rsi'] > 70,
            lambda df: df['stoch'] > 80
        ]
        config = ZoneDetectionConfig(
            rules={
                'conditions': conditions,
                'logic': 'OR',
                'zone_type_map': {True: 'overbought', False: 'neutral'}
            }
        )
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по комбинированным правилам."""
        config.validate(required_rules=['conditions'])
        
        conditions = config.rules['conditions']
        logic = config.rules.get('logic', 'AND').upper()
        zone_type_map = config.rules.get('zone_type_map', {True: 'active', False: 'inactive'})
        
        if logic not in ['AND', 'OR']:
            raise ValueError(f"logic must be 'AND' or 'OR', got '{logic}'")
        
        df = data.copy()
        
        # Вычислить все условия
        condition_results = []
        for i, cond in enumerate(conditions):
            try:
                result = cond(df)
                if not isinstance(result, (pd.Series, np.ndarray)):
                    raise TypeError(f"Condition {i} must return pd.Series or np.ndarray")
                condition_results.append(result)
            except Exception as e:
                raise ValueError(f"Error evaluating condition {i}: {e}")
        
        # Комбинировать условия
        if logic == 'AND':
            combined = np.logical_and.reduce(condition_results)
        else:  # OR
            combined = np.logical_or.reduce(condition_results)
        
        # Найти границы зон
        changes = np.where(
            np.concatenate([[True], combined[1:] != combined[:-1]])
        )[0]
        boundaries = np.concatenate([changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            if duration < config.min_duration:
                continue
            
            zone_active = combined[start_idx]
            zone_type = zone_type_map.get(zone_active, f'zone_{zone_active}')
            
            if zone_type not in config.zone_types:
                continue
            
            zone_data = df.iloc[start_idx:end_idx + 1].copy()
            
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data,
                indicator_context={
                    'detection_strategy': 'combined',
                    'detection_indicator': 'combined',
                    'signal_line': None,
                    'logic': logic,
                    'num_conditions': len(conditions),
                    'detection_rules': {k: v for k, v in config.rules.items() if k != 'conditions'}
                }
            )
            zones.append(zone)
        
        self.logger.info(f"Detected {len(zones)} zones from combined rules ({logic})")
        
        return zones


# Экспорт
__all__ = [
    'CombinedRulesDetection'
]

