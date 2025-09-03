"""
Pandas-TA Loader for BQuant

This module provides integration with pandas-ta library for technical indicators.
"""

import pandas as pd
from typing import Dict, Any, List, Optional, Callable
import warnings

from ..base import IndicatorFactory, LibraryIndicator, IndicatorConfig, IndicatorSource
from ...core.logging_config import get_logger
from ...core.exceptions import IndicatorCalculationError

logger = get_logger(__name__)


class PandasTALoader:
    """
    Загрузчик индикаторов из библиотеки pandas-ta.
    """
    
    _indicators_registered = False
    _available_indicators = []
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Проверить доступность pandas-ta.
        
        Returns:
            True если pandas-ta доступна
        """
        try:
            import pandas_ta
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
        Обнаружить доступные индикаторы pandas-ta.
        """
        try:
            import pandas_ta as ta
            
            # Основные категории индикаторов
            categories = [
                'trend', 'momentum', 'volatility', 'volume', 'overlap'
            ]
            
            indicators = []
            for category in categories:
                try:
                    # Получаем методы категории
                    category_methods = getattr(ta, category)
                    if hasattr(category_methods, '__dict__'):
                        for method_name in dir(category_methods):
                            if not method_name.startswith('_'):
                                indicators.append(f"{category}_{method_name}")
                except Exception as e:
                    logger.debug(f"Failed to discover {category} indicators: {e}")
            
            # Добавляем основные индикаторы
            basic_indicators = [
                'sma', 'ema', 'rsi', 'macd', 'bbands', 'stoch', 'adx'
            ]
            
            for indicator in basic_indicators:
                if hasattr(ta, indicator):
                    indicators.append(indicator)
            
            cls._available_indicators = sorted(list(set(indicators)))
            logger.info(f"Discovered {len(cls._available_indicators)} pandas-ta indicators")
            
        except Exception as e:
            logger.error(f"Failed to discover pandas-ta indicators: {e}")
            cls._available_indicators = []
    
    @classmethod
    def register_indicators(cls) -> int:
        """
        Зарегистрировать индикаторы pandas-ta в IndicatorFactory.
        
        Returns:
            Количество зарегистрированных индикаторов
        """
        if cls._indicators_registered:
            return len(cls._available_indicators)
        
        if not cls.is_available():
            logger.warning("pandas-ta is not available")
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
            logger.info(f"Registered {registered_count} pandas-ta indicators")
            
            return registered_count
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta indicators: {e}")
            return 0
    
    @classmethod
    def _register_sma(cls) -> bool:
        """Зарегистрировать SMA индикатор."""
        try:
            class PandasTASMA(LibraryIndicator):
                """Simple Moving Average из pandas-ta."""
                
                def __init__(self, length: int = 20):
                    config = IndicatorConfig(
                        name='pandas_ta_sma',
                        parameters={'length': length},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'sma_{length}'],
                        description=f'Pandas-TA SMA with length {length}'
                    )
                    super().__init__('pandas_ta_sma', config)
                    self.length = length
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить SMA используя pandas-ta."""
                    try:
                        import pandas_ta as ta
                        
                        length = kwargs.get('length', self.length)
                        
                        # Вычисляем SMA
                        sma = ta.sma(data['close'], length=length)
                        
                        result = pd.DataFrame({
                            f'sma_{length}': sma
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate pandas-ta SMA: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту pandas-ta."""
                    import pandas_ta as ta
                    return ta.sma
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('pandas_ta_sma', PandasTASMA)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta SMA: {e}")
            return False
    
    @classmethod
    def _register_ema(cls) -> bool:
        """Зарегистрировать EMA индикатор."""
        try:
            class PandasTAEMA(LibraryIndicator):
                """Exponential Moving Average из pandas-ta."""
                
                def __init__(self, length: int = 20):
                    config = IndicatorConfig(
                        name='pandas_ta_ema',
                        parameters={'length': length},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'ema_{length}'],
                        description=f'Pandas-TA EMA with length {length}'
                    )
                    super().__init__('pandas_ta_ema', config)
                    self.length = length
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить EMA используя pandas-ta."""
                    try:
                        import pandas_ta as ta
                        
                        length = kwargs.get('length', self.length)
                        
                        # Вычисляем EMA
                        ema = ta.ema(data['close'], length=length)
                        
                        result = pd.DataFrame({
                            f'ema_{length}': ema
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate pandas-ta EMA: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту pandas-ta."""
                    import pandas_ta as ta
                    return ta.ema
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('pandas_ta_ema', PandasTAEMA)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta EMA: {e}")
            return False
    
    @classmethod
    def _register_rsi(cls) -> bool:
        """Зарегистрировать RSI индикатор."""
        try:
            class PandasTARSI(LibraryIndicator):
                """Relative Strength Index из pandas-ta."""
                
                def __init__(self, length: int = 14):
                    config = IndicatorConfig(
                        name='pandas_ta_rsi',
                        parameters={'length': length},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'rsi_{length}'],
                        description=f'Pandas-TA RSI with length {length}'
                    )
                    super().__init__('pandas_ta_rsi', config)
                    self.length = length
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить RSI используя pandas-ta."""
                    try:
                        import pandas_ta as ta
                        
                        length = kwargs.get('length', self.length)
                        
                        # Вычисляем RSI
                        rsi = ta.rsi(data['close'], length=length)
                        
                        result = pd.DataFrame({
                            f'rsi_{length}': rsi
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate pandas-ta RSI: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту pandas-ta."""
                    import pandas_ta as ta
                    return ta.rsi
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('pandas_ta_rsi', PandasTARSI)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta RSI: {e}")
            return False
    
    @classmethod
    def _register_macd(cls) -> bool:
        """Зарегистрировать MACD индикатор."""
        try:
            class PandasTAMACD(LibraryIndicator):
                """MACD из pandas-ta."""
                
                def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
                    config = IndicatorConfig(
                        name='pandas_ta_macd',
                        parameters={'fast': fast, 'slow': slow, 'signal': signal},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'macd_{fast}_{slow}_{signal}', f'macds_{fast}_{slow}_{signal}', f'macdh_{fast}_{slow}_{signal}'],
                        description=f'Pandas-TA MACD with fast={fast}, slow={slow}, signal={signal}'
                    )
                    super().__init__('pandas_ta_macd', config)
                    self.fast = fast
                    self.slow = slow
                    self.signal = signal
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить MACD используя pandas-ta."""
                    try:
                        import pandas_ta as ta
                        
                        fast = kwargs.get('fast', self.fast)
                        slow = kwargs.get('slow', self.slow)
                        signal = kwargs.get('signal', self.signal)
                        
                        # Вычисляем MACD
                        macd_result = ta.macd(data['close'], fast=fast, slow=slow, signal=signal)
                        
                        # pandas-ta возвращает DataFrame с колонками MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9
                        result = pd.DataFrame({
                            f'macd_{fast}_{slow}_{signal}': macd_result[f'MACD_{fast}_{slow}_{signal}'],
                            f'macds_{fast}_{slow}_{signal}': macd_result[f'MACDs_{fast}_{slow}_{signal}'],
                            f'macdh_{fast}_{slow}_{signal}': macd_result[f'MACDh_{fast}_{slow}_{signal}']
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate pandas-ta MACD: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту pandas-ta."""
                    import pandas_ta as ta
                    return ta.macd
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('pandas_ta_macd', PandasTAMACD)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta MACD: {e}")
            return False
    
    @classmethod
    def _register_bbands(cls) -> bool:
        """Зарегистрировать Bollinger Bands индикатор."""
        try:
            class PandasTABBands(LibraryIndicator):
                """Bollinger Bands из pandas-ta."""
                
                def __init__(self, length: int = 20, std: float = 2.0):
                    config = IndicatorConfig(
                        name='pandas_ta_bbands',
                        parameters={'length': length, 'std': std},
                        source=IndicatorSource.LIBRARY,
                        columns=[f'bbands_upper_{length}_{std}', f'bbands_middle_{length}_{std}', f'bbands_lower_{length}_{std}'],
                        description=f'Pandas-TA Bollinger Bands with length={length}, std={std}'
                    )
                    super().__init__('pandas_ta_bbands', config)
                    self.length = length
                    self.std = std
                
                def calculate(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
                    """Вычислить Bollinger Bands используя pandas-ta."""
                    try:
                        import pandas_ta as ta
                        
                        length = kwargs.get('length', self.length)
                        std = kwargs.get('std', self.std)
                        
                        # Вычисляем Bollinger Bands
                        bb_result = ta.bbands(data['close'], length=length, std=std)
                        
                        # pandas-ta возвращает DataFrame с колонками BBU_20_2.0, BBM_20_2.0, BBL_20_2.0
                        result = pd.DataFrame({
                            f'bbands_upper_{length}_{std}': bb_result[f'BBU_{length}_{std}'],
                            f'bbands_middle_{length}_{std}': bb_result[f'BBM_{length}_{std}'],
                            f'bbands_lower_{length}_{std}': bb_result[f'BBL_{length}_{std}']
                        }, index=data.index)
                        
                        return result
                        
                    except Exception as e:
                        raise IndicatorCalculationError(f"Failed to calculate pandas-ta Bollinger Bands: {e}")
                
                @property
                def native_indicator(self):
                    """Доступ к нативному объекту pandas-ta."""
                    import pandas_ta as ta
                    return ta.bbands
            
            # Регистрируем в фабрике
            IndicatorFactory.register_indicator('pandas_ta_bbands', PandasTABBands)
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pandas-ta Bollinger Bands: {e}")
            return False
