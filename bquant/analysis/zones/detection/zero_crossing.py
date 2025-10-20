"""
Zero Crossing Detection Strategy

Стратегия детекции зон по пересечению индикатором нулевой линии.

Применение:
- MACD histogram
- Awesome Oscillator (AO)
- CCI (Commodity Channel Index)
- Любой осциллятор с нулевой линией
"""

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'zero_crossing',
    description='Detect bull/bear zones by indicator crossing zero line',
    supported_zones=['bull', 'bear'],
    required_rules=['indicator_col']
)
class ZeroCrossingDetection:
    """
    Стратегия: детекция зон по пересечению нулевой линии.
    
    Применение:
        - MACD histogram
        - Awesome Oscillator (AO)
        - CCI (Commodity Channel Index)
        - любой осциллятор с нулевой линией
        
    Правила (config.rules):
        - indicator_col: str (обязательно) - название колонки индикатора
        - smooth_window: int (опционально) - сглаживание перед детекцией
        
    Типы зон:
        - 'bull': индикатор > 0
        - 'bear': индикатор < 0
    
    Example:
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd_histogram'}
        )
        zones = strategy.detect_zones(data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Обнаружить зоны по пересечению нуля.
        
        Алгоритм:
        1. Извлечь колонку индикатора
        2. Опционально сгладить
        3. Найти знаковые переходы (+ -> -, - -> +)
        4. Создать ZoneInfo для каждой зоны
        5. Отфильтровать по min_duration
        
        Args:
            data: DataFrame с OHLCV + индикаторами
            config: Конфигурация правил детекции
            
        Returns:
            List[ZoneInfo] - список обнаруженных зон
        """
        # Валидация
        config.validate(required_rules=['indicator_col'])
        
        indicator_col = config.rules['indicator_col']
        if indicator_col not in data.columns:
            raise ValueError(
                f"Indicator column '{indicator_col}' not found in data. "
                f"Available: {list(data.columns)}"
            )
        
        df = data.copy()
        indicator_values = df[indicator_col].values
        
        # Опциональное сглаживание
        smooth_window = config.rules.get('smooth_window')
        if smooth_window and smooth_window > 1:
            indicator_values = pd.Series(indicator_values).rolling(
                window=smooth_window, 
                center=False
            ).mean().values
            self.logger.debug(f"Applied smoothing: window={smooth_window}")
        
        # Найти смены знака
        signs = np.sign(indicator_values)
        signs[signs == 0] = 1  # 0 считаем как положительное
        
        sign_changes = np.where(np.diff(signs) != 0)[0] + 1
        
        if len(sign_changes) == 0:
            self.logger.warning("No zero crossings found")
            return []
        
        # Добавить начало и конец
        boundaries = np.concatenate([[0], sign_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            # Фильтр по минимальной длительности
            if duration < config.min_duration:
                continue
            
            # Определить тип зоны
            zone_mean_value = indicator_values[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_value > 0 else 'bear'
            
            # Фильтр по типам зон
            if zone_type not in config.zone_types:
                continue
            
            # Создать ZoneInfo
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
                    'detection_strategy': 'zero_crossing',
                    'detection_indicator': indicator_col,
                    'signal_line': None,
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)
        
        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"{sum(1 for z in zones if z.type == 'bull')} bull, "
            f"{sum(1 for z in zones if z.type == 'bear')} bear"
        )
        
        return zones


# Экспорт
__all__ = [
    'ZeroCrossingDetection'
]

