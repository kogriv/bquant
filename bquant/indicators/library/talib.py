"""
TA-Lib Loader for BQuant

This module provides integration with TA-Lib library for technical indicators.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable
import warnings

from ..base import IndicatorFactory, LibraryIndicator, IndicatorConfig, IndicatorSource
from ...core.logging_config import get_logger
from ...core.exceptions import IndicatorCalculationError

logger = get_logger(__name__)


class TALibLoader:
    """
    Загрузчик индикаторов из библиотеки TA-Lib.
    """
    
    _indicators_registered = False
    _available_indicators = []
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Проверить доступность TA-Lib.
        
        Returns:
            True если TA-Lib доступна
        """
        try:
            import talib
            return True
        except ImportError:
            return False
    
    @classmethod
    def get_available_indicators(cls) -> List[str]:
        """
        Получить список доступных индикаторов.
        
        Returns:
            Список названий индикаторов
        """
        if not cls.is_available():
            return []
        
        if not cls._indicators_registered:
            cls._discover_indicators()
        
        return cls._available_indicators.copy()
    
    @classmethod
    def _discover_indicators(cls):
        """
        Обнаружить доступные индикаторы TA-Lib.
        """
        try:
            import talib
            
            # Основные категории индикаторов TA-Lib
            categories = [
                'overlap_studies', 'momentum_indicators', 'volume_indicators',
                'volatility_indicators', 'price_transform', 'cycle_indicators',
                'pattern_recognition', 'statistic_functions', 'math_transform',
                'math_operators'
            ]
            
            indicators = []
            for category in categories:
                try:
                    # Получаем функции категории
                    category_funcs = getattr(talib, category)
                    if hasattr(category_funcs, '__dict__'):
                        for func_name in dir(category_funcs):
                            if not func_name.startswith('_'):
                                indicators.append(f"{category}_{func_name}")
                except Exception as e:
                    logger.debug(f"Failed to discover {category} indicators: {e}")
            
            # Добавляем основные индикаторы
            basic_indicators = [
                'SMA', 'EMA', 'RSI', 'MACD', 'BBANDS', 'STOCH', 'ADX',
                'ATR', 'CCI', 'WILLR', 'ROC', 'PPO', 'AROON', 'PSAR'
            ]
            
            for indicator in basic_indicators:
                if hasattr(talib, indicator):
                    indicators.append(indicator)
            
            cls._available_indicators = sorted(list(set(indicators)))
            logger.info(f"Discovered {len(cls._available_indicators)} TA-Lib indicators")
            
        except Exception as e:
            logger.error(f"Failed to discover TA-Lib indicators: {e}")
            cls._available_indicators = []
    
    @classmethod
    def register_indicators(cls) -> int:
        """
        Зарегистрировать индикаторы TA-Lib в IndicatorFactory.
        
        Returns:
            Количество зарегистрированных индикаторов
        """
        if cls._indicators_registered:
            return len(cls._available_indicators)
        
        if not cls.is_available():
            logger.warning("TA-Lib is not available")
            return 0
        
        try:
            # Обнаруживаем индикаторы если еще не сделано
            if not cls._available_indicators:
                cls._discover_indicators()
            
            # Регистрируем основные индикаторы
            registered_count = 0
            
            # SMA
            if cls._register_sma():
                registered_count += 1
            
            # EMA
            if cls._register_ema():
                registered_count += 1
            
            # RSI
            if cls._register_rsi():
                registered_count += 1
            
            # MACD
            if cls._register_macd():
                registered_count += 1
            
            # Bollinger Bands
            if cls._register_bbands():
                registered_count += 1
            
            cls._indicators_registered = True
            logger.info(f"Registered {registered_count} TA-Lib indicators")
            
            return registered_count
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib indicators: {e}")
            return 0
    
    @classmethod
    def _register_sma(cls) -> bool:
        """Зарегистрировать SMA индикатор."""
        try:
            class TALibSMA(LibraryIndicator):
                """Simple Moving Average из TA-Lib."""
                
                def __init__(self, timeperiod: int = 30):
                    config = IndicatorConfig(
                        name='talib_sma',
                        parameters={'timeperiod': timeperiod},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'sma_{timeperiod}'],
                        description=f'TA-Lib SMA with timeperiod {timeperiod}'
                    )
                    super().__init__('talib_sma', config)
                    self.timeperiod = timeperiod
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить SMA используя TA-Lib."""
                    try:
                        import talib
                        
                        timeperiod = kwargs.get('timeperiod', self.timeperiod)
                        
                        # Получаем данные
                        close_prices = data['close'].values.astype(float)
                        
                        # Вычисляем SMA
                        sma = talib.SMA(close_prices, timeperiod=timeperiod)
                        
                        result = pd.DataFrame({
                            f'sma_{timeperiod}': sma
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate TA-Lib SMA: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту TA-Lib."""
                    import talib
                    return talib.SMA
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('talib_sma', TALibSMA)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib SMA: {e}")
            return False
    
    @classmethod
    def _register_ema(cls) -> bool:
        """Зарегистрировать EMA индикатор."""
        try:
            class TALibEMA(LibraryIndicator):
                """Exponential Moving Average из TA-Lib."""
                
                def __init__(self, timeperiod: int = 30):
                    config = IndicatorConfig(
                        name='talib_ema',
                        parameters={'timeperiod': timeperiod},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'ema_{timeperiod}'],
                        description=f'TA-Lib EMA with timeperiod {timeperiod}'
                    )
                    super().__init__('talib_ema', config)
                    self.timeperiod = timeperiod
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить EMA используя TA-Lib."""
                    try:
                        import talib
                        
                        timeperiod = kwargs.get('timeperiod', self.timeperiod)
                        
                        # Получаем данные
                        close_prices = data['close'].values.astype(float)
                        
                        # Вычисляем EMA
                        ema = talib.EMA(close_prices, timeperiod=timeperiod)
                        
                        result = pd.DataFrame({
                            f'ema_{timeperiod}': ema
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate TA-Lib EMA: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту TA-Lib."""
                    import talib
                    return talib.EMA
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('talib_ema', TALibEMA)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib EMA: {e}")
            return False
    
    @classmethod
    def _register_rsi(cls) -> bool:
        """Зарегистрировать RSI индикатор."""
        try:
            class TALibRSI(LibraryIndicator):
                """Relative Strength Index из TA-Lib."""
                
                def __init__(self, timeperiod: int = 14):
                    config = IndicatorConfig(
                        name='talib_rsi',
                        parameters={'timeperiod': timeperiod},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'rsi_{timeperiod}'],
                        description=f'TA-Lib RSI with timeperiod {timeperiod}'
                    )
                    super().__init__('talib_rsi', config)
                    self.timeperiod = timeperiod
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить RSI используя TA-Lib."""
                    try:
                        import talib
                        
                        timeperiod = kwargs.get('timeperiod', self.timeperiod)
                        
                        # Получаем данные
                        close_prices = data['close'].values.astype(float)
                        
                        # Вычисляем RSI
                        rsi = talib.RSI(close_prices, timeperiod=timeperiod)
                        
                        result = pd.DataFrame({
                            f'rsi_{timeperiod}': rsi
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate TA-Lib RSI: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту TA-Lib."""
                    import talib
                    return talib.RSI
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('talib_rsi', TALibRSI)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib RSI: {e}")
            return False
    
    @classmethod
    def _register_macd(cls) -> bool:
        """Зарегистрировать MACD индикатор."""
        try:
            class TALibMACD(LibraryIndicator):
                """MACD из TA-Lib."""
                
                def __init__(self, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9):
                    config = IndicatorConfig(
                        name='talib_macd',
                        parameters={'fastperiod': fastperiod, 'slowperiod': slowperiod, 'signalperiod': signalperiod},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'macd_{fastperiod}_{slowperiod}_{signalperiod}', f'macdsignal_{fastperiod}_{slowperiod}_{signalperiod}', f'macdhist_{fastperiod}_{slowperiod}_{signalperiod}'],
                        description=f'TA-Lib MACD with fastperiod={fastperiod}, slowperiod={slowperiod}, signalperiod={signalperiod}'
                    )
                    super().__init__('talib_macd', config)
                    self.fastperiod = fastperiod
                    self.slowperiod = slowperiod
                    self.signalperiod = signalperiod
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить MACD используя TA-Lib."""
                    try:
                        import talib
                        
                        fastperiod = kwargs.get('fastperiod', self.fastperiod)
                        slowperiod = kwargs.get('slowperiod', self.slowperiod)
                        signalperiod = kwargs.get('signalperiod', self.signalperiod)
                        
                        # Получаем данные
                        close_prices = data['close'].values.astype(float)
                        
                        # Вычисляем MACD
                        macd, macdsignal, macdhist = talib.MACD(
                            close_prices, 
                            fastperiod=fastperiod, 
                            slowperiod=slowperiod, 
                            signalperiod=signalperiod
                        )
                        
                        result = pd.DataFrame({
                            f'macd_{fastperiod}_{slowperiod}_{signalperiod}': macd,
                            f'macdsignal_{fastperiod}_{slowperiod}_{signalperiod}': macdsignal,
                            f'macdhist_{fastperiod}_{slowperiod}_{signalperiod}': macdhist
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate TA-Lib MACD: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту TA-Lib."""
                    import talib
                    return talib.MACD
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('talib_macd', TALibMACD)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib MACD: {e}")
            return False
    
    @classmethod
    def _register_bbands(cls) -> bool:
        """Зарегистрировать Bollinger Bands индикатор."""
        try:
            class TALibBBands(LibraryIndicator):
                """Bollinger Bands из TA-Lib."""
                
                def __init__(self, timeperiod: int = 5, nbdevup: float = 2.0, nbdevdn: float = 2.0, matype: int = 0):
                    config = IndicatorConfig(
                        name='talib_bbands',
                        parameters={'timeperiod': timeperiod, 'nbdevup': nbdevup, 'nbdevdn': nbdevdn, 'matype': matype},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'bbands_upper_{timeperiod}_{nbdevup}_{nbdevdn}', f'bbands_middle_{timeperiod}_{nbdevup}_{nbdevdn}', f'bbands_lower_{timeperiod}_{nbdevup}_{nbdevdn}'],
                        description=f'TA-Lib Bollinger Bands with timeperiod={timeperiod}, nbdevup={nbdevup}, nbdevdn={nbdevdn}, matype={matype}'
                    )
                    super().__init__('talib_bbands', config)
                    self.timeperiod = timeperiod
                    self.nbdevup = nbdevup
                    self.nbdevdn = nbdevdn
                    self.matype = matype
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить Bollinger Bands используя TA-Lib."""
                    try:
                        import talib
                        
                        timeperiod = kwargs.get('timeperiod', self.timeperiod)
                        nbdevup = kwargs.get('nbdevup', self.nbdevup)
                        nbdevdn = kwargs.get('nbdevdn', self.nbdevdn)
                        matype = kwargs.get('matype', self.matype)
                        
                        # Получаем данные
                        close_prices = data['close'].values.astype(float)
                        
                        # Вычисляем Bollinger Bands
                        upperband, middleband, lowerband = talib.BBANDS(
                            close_prices,
                            timeperiod=timeperiod,
                            nbdevup=nbdevup,
                            nbdevdn=nbdevdn,
                            matype=matype
                        )
                        
                        result = pd.DataFrame({
                            f'bbands_upper_{timeperiod}_{nbdevup}_{nbdevdn}': upperband,
                            f'bbands_middle_{timeperiod}_{nbdevup}_{nbdevdn}': middleband,
                            f'bbands_lower_{timeperiod}_{nbdevup}_{nbdevdn}': lowerband
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate TA-Lib Bollinger Bands: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту TA-Lib."""
                    import talib
                    return talib.BBANDS
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('talib_bbands', TALibBBands)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register TA-Lib Bollinger Bands: {e}")
            return False
