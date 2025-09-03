"""
BQuant Indicators Module

Technical indicators calculation and analysis.
"""

# Base classes and architecture
from .base import (
    IndicatorSource,
    IndicatorConfig,
    IndicatorResult,
    BaseIndicator,
    PreloadedIndicator,
    CustomIndicator,
    LibraryIndicator,
    IndicatorFactory
)

# Built-in indicators (мигрированы в custom/ на Этапе 4)
from .custom import (
    SimpleMovingAverage,
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    MACD,
    BollingerBands
)

# External library loaders (moved from loaders.py)
from .library import (
    PandasTALoader,
    TALibLoader,
    LibraryManager,
    load_pandas_ta,
    load_talib,
    load_all_indicators
)

# High-level calculators (временно закомментировано до Этапа 4)
# from .calculators import (
#     IndicatorCalculator,
#     BatchCalculator,
#     calculate_indicator,
#     calculate_macd,
#     calculate_rsi,
#     calculate_bollinger_bands,
#     calculate_moving_averages,
#     create_indicator_suite,
#     get_available_indicators,
#     validate_indicator_data
# )

# MACD analyzer
from .macd import (
    ZoneInfo,
    ZoneAnalysisResult,
    MACDZoneAnalyzer,
    create_macd_analyzer,
    analyze_macd_zones
)

# PRELOADED indicators
from .preloaded import (
    MACDPreloadedIndicator
)

# Auto-register all indicators
def _register_all_indicators():
    """Регистрирует все доступные индикаторы в IndicatorFactory."""
    try:
        # Регистрируем PRELOADED индикаторы
        IndicatorFactory.register_indicator('macd_preloaded', MACDPreloadedIndicator)
        
        # Регистрируем CUSTOM индикаторы
        IndicatorFactory.register_indicator('sma', SimpleMovingAverage)
        IndicatorFactory.register_indicator('ema', ExponentialMovingAverage)
        IndicatorFactory.register_indicator('rsi', RelativeStrengthIndex)
        IndicatorFactory.register_indicator('macd', MACD)
        IndicatorFactory.register_indicator('bbands', BollingerBands)
        
        # LIBRARY индикаторы регистрируются автоматически при загрузке
        # через соответствующие загрузчики
        
    except Exception as e:
        # Игнорируем ошибки при авторегистрации
        pass

# Выполняем авторегистрацию при импорте модуля
_register_all_indicators()

__all__ = [
    # Base classes
    "BaseIndicator",
    "PreloadedIndicator", 
    "LibraryIndicator",
    "CustomIndicator",
    "IndicatorResult",
    "IndicatorConfig",
    "IndicatorSource",
    "IndicatorFactory",
    
    # PRELOADED indicators
    "MACDPreloadedIndicator",
    
    # Built-in indicators (мигрированы в custom/ на Этапе 4)
    "SimpleMovingAverage",
    "ExponentialMovingAverage",
    "RelativeStrengthIndex",
    "MACD",
    "BollingerBands",
    
    # External library loaders (мигрированы в library/ на Этапе 5)
    "PandasTALoader",
    "TALibLoader",
    "LibraryManager",
    "load_pandas_ta",
    "load_talib",
    "load_all_indicators",
    
    # MACD analyzer
    "ZoneInfo",
    "ZoneAnalysisResult", 
    "MACDZoneAnalyzer",
    "create_macd_analyzer",
    "analyze_macd_zones",
]
