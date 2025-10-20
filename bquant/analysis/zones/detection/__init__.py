"""
Zone Detection Strategies

Этот модуль содержит стратегии для автоматического определения зон
на основе различных правил и индикаторов.

Доступные стратегии:
- zero_crossing: Пересечение нулевой линии (MACD, AO, CCI)
- threshold: Пересечение порогов (RSI, Stochastic)
- line_crossing: Пересечение линий (MA crosses, Price vs MA)
- preloaded: Импорт готовых зон (CSV, DataFrame)
- combined: Комбинация условий (AND/OR логика)

Example:
    from bquant.analysis.zones.detection import (
        ZoneDetectionRegistry,
        ZoneDetectionConfig,
        ZeroCrossingDetection
    )
    
    # Get strategy by name
    strategy = ZoneDetectionRegistry.get('zero_crossing')
    
    # Configure detection
    config = ZoneDetectionConfig(
        min_duration=2,
        zone_types=['bull', 'bear'],
        rules={'indicator_col': 'macd_histogram'}
    )
    
    # Detect zones
    zones = strategy.detect_zones(data, config)
    
    # List all available strategies
    strategies = ZoneDetectionRegistry.list_strategies()
    print(f"Available: {strategies}")
"""

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry

# Import all strategies to trigger registration
from .zero_crossing import ZeroCrossingDetection
from .threshold import ThresholdDetection
from .line_crossing import LineCrossingDetection
from .preloaded import PreloadedZonesDetection, load_preloaded_zones
from .combined import CombinedRulesDetection


# Экспорт
__all__ = [
    # Base
    'ZoneDetectionStrategy',
    'ZoneDetectionConfig',
    'ZoneDetectionRegistry',
    
    # Strategies
    'ZeroCrossingDetection',
    'ThresholdDetection',
    'LineCrossingDetection',
    'PreloadedZonesDetection',
    'CombinedRulesDetection',
    
    # Helper
    'load_preloaded_zones'
]

