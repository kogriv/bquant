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
    LibraryIndicator,
    IndicatorFactory
)

# Built-in indicators
from .library import (
    SimpleMovingAverage,
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    MACD,
    BollingerBands,
    register_builtin_indicators,
    get_builtin_indicators,
    create_indicator
)

# External library loaders
from .loaders import (
    PandasTALoader,
    TALibLoader,
    LibraryManager,
    load_pandas_ta,
    load_talib,
    load_all_indicators
)

# High-level calculators
from .calculators import (
    IndicatorCalculator,
    BatchCalculator,
    calculate_indicator,
    calculate_macd,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_moving_averages,
    create_indicator_suite,
    get_available_indicators,
    validate_indicator_data
)

# MACD analyzer
from .macd import (
    ZoneInfo,
    ZoneAnalysisResult,
    MACDZoneAnalyzer,
    create_macd_analyzer,
    analyze_macd_zones
)

# Auto-register built-in indicators
try:
    register_builtin_indicators()
except Exception:
    pass  # Ignore errors during auto-registration

__all__ = [
    # Base classes
    "IndicatorSource",
    "IndicatorConfig", 
    "IndicatorResult",
    "BaseIndicator",
    "PreloadedIndicator",
    "LibraryIndicator",
    "IndicatorFactory",
    
    # Built-in indicators
    "SimpleMovingAverage",
    "ExponentialMovingAverage",
    "RelativeStrengthIndex",
    "MACD",
    "BollingerBands",
    "register_builtin_indicators",
    "get_builtin_indicators",
    "create_indicator",
    
    # Library loaders
    "PandasTALoader",
    "TALibLoader",
    "LibraryManager",
    "load_pandas_ta",
    "load_talib",
    "load_all_indicators",
    
    # Calculators
    "IndicatorCalculator",
    "BatchCalculator",
    "calculate_indicator",
    "calculate_macd",
    "calculate_rsi",
    "calculate_bollinger_bands",
    "calculate_moving_averages",
    "create_indicator_suite",
    "get_available_indicators",
    "validate_indicator_data",
    
    # MACD Zone Analyzer
    "ZoneInfo",
    "ZoneAnalysisResult",
    "MACDZoneAnalyzer",
    "create_macd_analyzer",
    "analyze_macd_zones"
]
