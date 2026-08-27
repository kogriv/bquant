"""
Threshold Detection Strategy

Стратегия детекции зон по пересечению порогов индикатора.

Применение:
- RSI (upper=70, lower=30)
- Stochastic (upper=80, lower=20)
- Williams %R
"""

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo, ZoneType
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'threshold',
    description='Detect zones by indicator crossing upper/lower thresholds',
    supported_zones=[
        # Три полосы осциллятора. Нейтральная объявлена наравне с сигнальными:
        # без неё зоны покрывают лишь часть таймлайна и соседние зоны перестают
        # примыкать, а анализ последовательностей читает соседние элементы как
        # переход (замер: devref/gaps/detection/g19_*.md).
        ZoneType('overbought', polarity=+1, counterpart='oversold', label='Overbought'),
        ZoneType('neutral', polarity=0, label='Neutral'),
        ZoneType('oversold', polarity=-1, counterpart='overbought', label='Oversold'),
    ],
    required_rules=['indicator_col', 'upper_threshold', 'lower_threshold']
)
class ThresholdDetection:
    """
    Стратегия: детекция зон по порогам.
    
    Применение:
        - RSI (upper=70, lower=30)
        - Stochastic (upper=80, lower=20)
        - Williams %R
        
    Правила (config.rules):
        - indicator_col: str (обязательно)
        - upper_threshold: float (обязательно) - верхняя граница
        - lower_threshold: float (обязательно) - нижняя граница
        
    Типы зон:
        - 'overbought': индикатор > upper_threshold
        - 'neutral': lower_threshold <= индикатор <= upper_threshold
        - 'oversold': индикатор < lower_threshold
    
    Example:
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            zone_types=['overbought', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            }
        )
        zones = strategy.detect_zones(data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по порогам."""
        # Валидация
        config.validate(required_rules=['indicator_col', 'upper_threshold', 'lower_threshold'])
        
        indicator_col = config.rules['indicator_col']
        upper = config.rules['upper_threshold']
        lower = config.rules['lower_threshold']
        
        if upper <= lower:
            raise ValueError(f"upper_threshold ({upper}) must be > lower_threshold ({lower})")
        
        if indicator_col not in data.columns:
            raise ValueError(f"Indicator column '{indicator_col}' not found")
        
        df = data.copy()
        indicator_values = df[indicator_col].values
        
        # Классификация по порогам
        zone_classes = np.empty(len(indicator_values), dtype=object)
        zone_classes[indicator_values > upper] = 'overbought'
        zone_classes[indicator_values < lower] = 'oversold'
        zone_classes[(indicator_values >= lower) & (indicator_values <= upper)] = 'neutral'
        
        # Найти границы зон (смены класса)
        class_changes = np.where(
            np.concatenate([[True], zone_classes[1:] != zone_classes[:-1]])
        )[0]
        boundaries = np.concatenate([class_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            zone_type = zone_classes[start_idx]

            # `np.empty(dtype=object)` заполняется None, и позиции, где у
            # индикатора нет значения, ни одному из трёх сравнений не
            # удовлетворяют — там так и остаётся None. Это не четвёртый тип
            # зоны, а отсутствие зоны: бар разогрева не «нейтрален», индикатора
            # на нём просто нет. Пока порог длительности стоял в детекции,
            # короткий разогрев отсеивался и типа-None никто не видел.
            if zone_type is None:
                continue

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
                    'detection_strategy': 'threshold',
                    'detection_indicator': indicator_col,
                    'signal_line': None,
                    'thresholds': {
                        'upper': upper,
                        'lower': lower
                    },
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)
        
        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"OB={sum(1 for z in zones if z.type == 'overbought')}, "
            f"N={sum(1 for z in zones if z.type == 'neutral')}, "
            f"OS={sum(1 for z in zones if z.type == 'oversold')}"
        )
        
        return zones


# Экспорт
__all__ = [
    'ThresholdDetection'
]

