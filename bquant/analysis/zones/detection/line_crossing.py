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

from .base import ZoneDetectionStrategy, ZoneDetectionConfig, defined_segments
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo, ZoneType
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'line_crossing',
    description='Detect zones by two lines crossing each other',
    supported_zones=[
        # Первая линия выше второй — приподнятое состояние, ниже — подавленное.
        ZoneType('bull', polarity=+1, counterpart='bear', label='Bullish'),
        ZoneType('bear', polarity=-1, counterpart='bull', label='Bearish'),
    ],
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
        
        # Мостится область, где определены **обе** линии: там, где одной из них
        # ещё нет, у их разницы нет знака, а не «отрицательный знак».
        segments = defined_segments(diff)
        if not segments:
            self.logger.warning(
                "Lines '%s' and '%s' never overlap; no zones", line1_col, line2_col
            )
            return []

        undefined_bars = len(df) - sum(stop - start for start, stop in segments)
        if undefined_bars:
            self.logger.info(
                "%d of %d bars have no value for both lines; they belong to no "
                "zone.", undefined_bars, len(df)
            )

        spans = []
        for seg_start, seg_stop in segments:
            signs = np.sign(diff[seg_start:seg_stop])
            signs[signs == 0] = 1
            changes = (np.where(np.diff(signs) != 0)[0] + 1 + seg_start).tolist()
            edges = [seg_start, *changes, seg_stop]
            spans.extend(zip(edges, edges[1:]))

        if len(spans) == 1:
            self.logger.warning("No line crossings found")

        zones = []
        for start_idx, stop_idx in spans:
            end_idx = stop_idx - 1
            duration = end_idx - start_idx + 1

            zone_mean_diff = diff[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_diff > 0 else 'bear'
            
            if not config.accepts(zone_type):
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

