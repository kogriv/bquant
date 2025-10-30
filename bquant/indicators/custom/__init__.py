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
    
    # Registration function
    "register_builtin_indicators",
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
    
    # Тихая регистрация: используем DEBUG через логгер фабрики на этапе register
    # (здесь избегаем print, чтобы не шуметь в консоли)
    
except Exception as e:
    print(f"[WARNING] Failed to auto-register BUILTIN indicators: {e}")
    pass  # Ignore errors during auto-registration


def register_builtin_indicators():
    """
    Регистрация всех встроенных индикаторов в фабрике.
    
    Returns:
        int: Количество зарегистрированных индикаторов
    """
    from ..base import IndicatorFactory
    
    registered_count = 0
    
    try:
        IndicatorFactory.register_indicator("sma", SimpleMovingAverage)
        registered_count += 1
        IndicatorFactory.register_indicator("ema", ExponentialMovingAverage)
        registered_count += 1
        IndicatorFactory.register_indicator("rsi", RelativeStrengthIndex)
        registered_count += 1
        IndicatorFactory.register_indicator("macd", MACD)
        registered_count += 1
        IndicatorFactory.register_indicator("bbands", BollingerBands)
        registered_count += 1
        
        # Тихая регистрация: не печатаем в консоль, полагаться на логи фабрики
        return registered_count
        
    except Exception as e:
        # Ошибки будут отражены уровнем ERROR из фабрики/вызовов выше
        return registered_count
