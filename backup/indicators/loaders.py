"""
Loaders for external indicator libraries in BQuant

This module provides functionality to load and integrate external technical indicator libraries.
"""

import importlib
from typing import Dict, Any, Optional, List, Callable, Tuple
import warnings

from .base import IndicatorFactory, LibraryIndicator
from ..core.logging_config import get_logger
from ..core.exceptions import IndicatorCalculationError

logger = get_logger(__name__)


class PandasTALoader:
    """
    Загрузчик индикаторов из библиотеки pandas-ta.
    """
    
    _loaded = False
    _ta = None
    
    @classmethod
    def load(cls) -> bool:
        """
        Загрузка библиотеки pandas-ta.
        
        Returns:
            True если загрузка успешна
        """
        if cls._loaded:
            return True
        
        try:
            import pandas_ta as ta
            cls._ta = ta
            cls._loaded = True
            logger.info("pandas-ta library loaded successfully")
            return True
        except ImportError:
            logger.warning("pandas-ta library not found. Install with: pip install pandas-ta")
            return False
    
    @classmethod
    def register_indicators(cls) -> int:
        """
        Регистрация всех доступных индикаторов из pandas-ta.
        
        Returns:
            Количество зарегистрированных индикаторов
        """
        if not cls.load():
            return 0
        
        registered_count = 0
        
        # Основные индикаторы pandas-ta
        indicators = {
            # Trend indicators
            'sma': cls._ta.sma,
            'ema': cls._ta.ema,
            'wma': cls._ta.wma,
            'macd': cls._ta.macd,
            'adx': cls._ta.adx,
            'aroon': cls._ta.aroon,
            'psar': cls._ta.psar,
            
            # Momentum indicators
            'rsi': cls._ta.rsi,
            'stoch': cls._ta.stoch,
            'cci': cls._ta.cci,
            'williams_r': cls._ta.willr,
            'roc': cls._ta.roc,
            'ppo': cls._ta.ppo,
            
            # Volatility indicators
            'bbands': cls._ta.bbands,
            'atr': cls._ta.atr,
            'natr': cls._ta.natr,
            'kc': cls._ta.kc,
            'donchian': cls._ta.donchian,
            
            # Volume indicators
            'ad': cls._ta.ad,
            'adosc': cls._ta.adosc,
            'cmf': cls._ta.cmf,
            'em': cls._ta.em,
            'mfi': cls._ta.mfi,
            'nvi': cls._ta.nvi,
            'obv': cls._ta.obv,
            'pvi': cls._ta.pvi,
            'pvol': cls._ta.pvol,
            'pvr': cls._ta.pvr,
            'pvt': cls._ta.pvt,
            'vp': cls._ta.vp,
        }
        
        for name, func in indicators.items():
            try:
                IndicatorFactory.register_library_function(name, func)
                registered_count += 1
            except Exception as e:
                logger.warning(f"Failed to register {name}: {e}")
        
        logger.info(f"Registered {registered_count} pandas-ta indicators")
        return registered_count
    
    @classmethod
    def get_indicator_list(cls) -> List[str]:
        """
        Получить список доступных индикаторов pandas-ta.
        
        Returns:
            Список названий индикаторов
        """
        if not cls.load():
            return []
        
        # Возвращаем список всех функций pandas-ta
        try:
            return [name for name in dir(cls._ta) if not name.startswith('_')]
        except Exception:
            return []


class TALibLoader:
    """
    Загрузчик индикаторов из библиотеки TA-Lib.
    """
    
    _loaded = False
    _talib = None
    
    @classmethod
    def load(cls) -> bool:
        """
        Загрузка библиотеки TA-Lib.
        
        Returns:
            True если загрузка успешна
        """
        if cls._loaded:
            return True
        
        try:
            import talib
            cls._talib = talib
            cls._loaded = True
            logger.info("TA-Lib library loaded successfully")
            return True
        except ImportError:
            logger.warning("TA-Lib library not found. Install instructions: https://github.com/mrjbq7/ta-lib")
            return False
    
    @classmethod
    def register_indicators(cls) -> int:
        """
        Регистрация основных индикаторов из TA-Lib.
        
        Returns:
            Количество зарегистрированных индикаторов
        """
        if not cls.load():
            return 0
        
        registered_count = 0
        
        # Основные функции TA-Lib
        indicators = {
            # Moving Averages
            'ta_sma': cls._talib.SMA,
            'ta_ema': cls._talib.EMA,
            'ta_wma': cls._talib.WMA,
            'ta_dema': cls._talib.DEMA,
            'ta_tema': cls._talib.TEMA,
            'ta_trima': cls._talib.TRIMA,
            'ta_kama': cls._talib.KAMA,
            
            # Momentum Indicators
            'ta_macd': cls._talib.MACD,
            'ta_rsi': cls._talib.RSI,
            'ta_stoch': cls._talib.STOCH,
            'ta_stochf': cls._talib.STOCHF,
            'ta_roc': cls._talib.ROC,
            'ta_mom': cls._talib.MOM,
            'ta_cci': cls._talib.CCI,
            'ta_willr': cls._talib.WILLR,
            
            # Volatility Indicators
            'ta_bbands': cls._talib.BBANDS,
            'ta_atr': cls._talib.ATR,
            'ta_natr': cls._talib.NATR,
            'ta_trange': cls._talib.TRANGE,
            
            # Trend Indicators
            'ta_adx': cls._talib.ADX,
            'ta_adxr': cls._talib.ADXR,
            'ta_aroon': cls._talib.AROON,
            'ta_aroonosc': cls._talib.AROONOSC,
            'ta_sar': cls._talib.SAR,
            
            # Volume Indicators
            'ta_ad': cls._talib.AD,
            'ta_adosc': cls._talib.ADOSC,
            'ta_obv': cls._talib.OBV,
        }
        
        for name, func in indicators.items():
            try:
                # Создаем обертку для TA-Lib функций
                wrapper = cls._create_talib_wrapper(func, name)
                IndicatorFactory.register_library_function(name, wrapper)
                registered_count += 1
            except Exception as e:
                logger.warning(f"Failed to register {name}: {e}")
        
        logger.info(f"Registered {registered_count} TA-Lib indicators")
        return registered_count
    
    @classmethod
    def _create_talib_wrapper(cls, talib_func: Callable, name: str) -> Callable:
        """
        Создает обертку для функций TA-Lib для совместимости с BQuant.
        
        Args:
            talib_func: Функция TA-Lib
            name: Название индикатора
        
        Returns:
            Обернутая функция
        """
        def wrapper(data, **kwargs):
            """Обертка для функций TA-Lib."""
            import pandas as pd
            
            try:
                # Определяем входные данные в зависимости от функции
                if name.lower().startswith('ta_macd'):
                    result = talib_func(data['close'].values, **kwargs)
                    if isinstance(result, tuple):
                        # MACD возвращает кортеж (macd, signal, histogram)
                        return pd.DataFrame({
                            'macd': result[0],
                            'macd_signal': result[1],
                            'macd_hist': result[2]
                        }, index=data.index)
                    else:
                        return pd.Series(result, index=data.index, name=name)
                
                elif name.lower().startswith('ta_bbands'):
                    result = talib_func(data['close'].values, **kwargs)
                    # Bollinger Bands возвращает кортеж (upper, middle, lower)
                    return pd.DataFrame({
                        'bb_upper': result[0],
                        'bb_middle': result[1],
                        'bb_lower': result[2]
                    }, index=data.index)
                
                elif name.lower().startswith('ta_stoch'):
                    result = talib_func(
                        data['high'].values,
                        data['low'].values,
                        data['close'].values,
                        **kwargs
                    )
                    # Stochastic возвращает кортеж (%K, %D)
                    return pd.DataFrame({
                        'stoch_k': result[0],
                        'stoch_d': result[1]
                    }, index=data.index)
                
                elif 'atr' in name.lower() or 'adx' in name.lower():
                    # Индикаторы, требующие HLC
                    result = talib_func(
                        data['high'].values,
                        data['low'].values,
                        data['close'].values,
                        **kwargs
                    )
                    return pd.Series(result, index=data.index, name=name)
                
                else:
                    # Простые индикаторы (SMA, EMA, RSI и т.д.)
                    result = talib_func(data['close'].values, **kwargs)
                    return pd.Series(result, index=data.index, name=name)
                    
            except Exception as e:
                raise IndicatorCalculationError(
                    f"TA-Lib calculation failed for {name}: {e}",
                    {'indicator': name, 'function': str(talib_func)}
                )
        
        wrapper.__name__ = name
        wrapper.__doc__ = f"TA-Lib wrapper for {name}"
        return wrapper


class LibraryManager:
    """
    Менеджер для управления внешними библиотеками индикаторов.
    """
    
    _loaders = {
        'pandas_ta': PandasTALoader,
        'talib': TALibLoader,
    }
    
    @classmethod
    def load_all_libraries(cls) -> Dict[str, int]:
        """
        Загрузка всех доступных библиотек.
        
        Returns:
            Словарь {библиотека: количество_индикаторов}
        """
        results = {}
        
        for lib_name, loader_class in cls._loaders.items():
            try:
                count = loader_class.register_indicators()
                results[lib_name] = count
                logger.info(f"Loaded {count} indicators from {lib_name}")
            except Exception as e:
                logger.error(f"Failed to load {lib_name}: {e}")
                results[lib_name] = 0
        
        total = sum(results.values())
        logger.info(f"Total loaded indicators: {total}")
        
        return results
    
    @classmethod
    def load_library(cls, library_name: str) -> int:
        """
        Загрузка конкретной библиотеки.
        
        Args:
            library_name: Название библиотеки
        
        Returns:
            Количество загруженных индикаторов
        """
        if library_name not in cls._loaders:
            logger.error(f"Unknown library: {library_name}")
            return 0
        
        try:
            loader_class = cls._loaders[library_name]
            count = loader_class.register_indicators()
            logger.info(f"Loaded {count} indicators from {library_name}")
            return count
        except Exception as e:
            logger.error(f"Failed to load {library_name}: {e}")
            return 0
    
    @classmethod
    def get_available_libraries(cls) -> List[str]:
        """
        Получить список доступных библиотек.
        
        Returns:
            Список названий библиотек
        """
        return list(cls._loaders.keys())
    
    @classmethod
    def check_library_availability(cls, library_name: str) -> bool:
        """
        Проверить доступность библиотеки.
        
        Args:
            library_name: Название библиотеки
        
        Returns:
            True если библиотека доступна
        """
        if library_name not in cls._loaders:
            return False
        
        try:
            return cls._loaders[library_name].load()
        except Exception:
            return False


# Функции для удобного использования
def load_pandas_ta() -> int:
    """Загрузить индикаторы pandas-ta."""
    return LibraryManager.load_library('pandas_ta')


def load_talib() -> int:
    """Загрузить индикаторы TA-Lib."""
    return LibraryManager.load_library('talib')


def load_all_indicators() -> Dict[str, int]:
    """Загрузить все доступные индикаторы."""
    return LibraryManager.load_all_libraries()


# Экспорт
__all__ = [
    'PandasTALoader',
    'TALibLoader', 
    'LibraryManager',
    'load_pandas_ta',
    'load_talib',
    'load_all_indicators'
]
