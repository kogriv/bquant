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

def register_builtin_indicators():
    """
    Регистрация всех встроенных индикаторов в фабрике.
    
    Returns:
        int: Количество зарегистрированных индикаторов
    """
    from ..base import IndicatorFactory

    # Идемпотентно: повторная регистрация того же класса под тем же именем ничего
    # не меняет. До G64 этот же список регистрировался ещё дважды — при импорте
    # этого пакета и в ``bquant.indicators._register_all_indicators``.
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
