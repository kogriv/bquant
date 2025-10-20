"""
Line Crossing Detection Strategy

Стратегия детекции зон по пересечению двух линий.

Применение:
- MA crosses (fast MA vs slow MA)
- Price vs MA
- Bollinger Bands (price vs upper/lower band)
"""

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'line_crossing',
    description='Detect zones by two lines crossing each other',
    supported_zones=['bull', 'bear'],
    required_rules=['line1_col', 'line2_col']
)
class LineCrossingDetection:
    """
    Стратегия: детекция зон по пересечению двух линий.
    
    Применение:
        - MA crosses (fast MA vs slow MA)
        - Price vs MA
        - Bollinger Bands (price vs upper/lower band)
        
    Правила (config.rules):
        - line1_col: str (обязательно) - первая линия (обычно быстрая)
        - line2_col: str (обязательно) - вторая линия (обычно медленная)
        
    Типы зон:
        - 'bull': line1 > line2
        - 'bear': line1 < line2
    
    Example:
        strategy = LineCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={
                'line1_col': 'close',
                'line2_col': 'sma_20'
            }
        )
        zones = strategy.detect_zones(data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по пересечению линий."""
        config.validate(required_rules=['line1_col', 'line2_col'])
        
        line1_col = config.rules['line1_col']
        line2_col = config.rules['line2_col']
        
        for col in [line1_col, line2_col]:
            if col not in data.columns:
                raise ValueError(f"Column '{col}' not found in data")
        
        df = data.copy()
        
        # Разница между линиями
        diff = df[line1_col].values - df[line2_col].values
        
        # Знак разницы
        signs = np.sign(diff)
        signs[signs == 0] = 1
        
        # Найти пересечения
        sign_changes = np.where(np.diff(signs) != 0)[0] + 1
        
        if len(sign_changes) == 0:
            self.logger.warning("No line crossings found")
            return []
        
        boundaries = np.concatenate([[0], sign_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            if duration < config.min_duration:
                continue
            
            zone_mean_diff = diff[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_diff > 0 else 'bear'
            
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
                    'detection_strategy': 'line_crossing',
                    'detection_indicator': line1_col,
                    'signal_line': line2_col,
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)
        
        self.logger.info(f"Detected {len(zones)} zones from line crossing")
        
        return zones


# Экспорт
__all__ = [
    'LineCrossingDetection'
]

