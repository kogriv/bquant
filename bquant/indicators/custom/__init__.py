"""
BQuant Custom Indicators Module

This module contains custom and built-in technical indicators implemented specifically for BQuant.
These indicators inherit from CustomIndicator and provide their own calculation logic.
"""

# Built-in indicators (moved from library.py)
from .sma import SimpleMovingAverage
from .ema import ExponentialMovingAverage
from .rsi import RelativeStrengthIndex
from .macd import MACD
from .bollinger import BollingerBands

# Custom indicators
# Users can create their own indicators inheriting from CustomIndicator

__all__ = [
    # Built-in indicators
    "SimpleMovingAverage",
    "ExponentialMovingAverage", 
    "RelativeStrengthIndex",
    "MACD",
    "BollingerBands",
    
    # Custom indicators (to be added by users)
]

# Auto-register built-in indicators
try:
    from ..base import IndicatorFactory
    
    # Регистрируем BUILTIN индикаторы
    IndicatorFactory.register_indicator("sma", SimpleMovingAverage)
    IndicatorFactory.register_indicator("ema", ExponentialMovingAverage)
    IndicatorFactory.register_indicator("rsi", RelativeStrengthIndex)
    IndicatorFactory.register_indicator("macd", MACD)
    IndicatorFactory.register_indicator("bbands", BollingerBands)
    
    print(f"✅ Registered {len(__all__)} BUILTIN indicators in custom module")
    
except Exception as e:
    print(f"⚠️ Warning: Failed to auto-register BUILTIN indicators: {e}")
    pass  # Ignore errors during auto-registration
