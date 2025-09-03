"""
Library Manager for BQuant

This module provides centralized management of external indicator libraries.
"""

import importlib
from typing import Dict, Any, Optional, List, Callable
import warnings

from ..base import IndicatorFactory, LibraryIndicator
from ...core.logging_config import get_logger
from ...core.exceptions import IndicatorCalculationError

logger = get_logger(__name__)


class LibraryManager:
    """
    Менеджер для управления внешними библиотеками индикаторов.
    """
    
    _loaders = {
        'pandas_ta': None,  # Будет импортирован динамически
        'talib': None,      # Будет импортирован динамически
    }
    
    @classmethod
    def _get_loader(cls, library_name: str):
        """
        Получить загрузчик для библиотеки.
        
        Args:
            library_name: Название библиотеки
        
        Returns:
            Класс загрузчика
        """
        if cls._loaders[library_name] is None:
            try:
                if library_name == 'pandas_ta':
                    from .pandas_ta import PandasTALoader
                    cls._loaders[library_name] = PandasTALoader
                elif library_name == 'talib':
                    from .talib import TALibLoader
                    cls._loaders[library_name] = TALibLoader
            except ImportError as e:
                logger.warning(f"Failed to import {library_name} loader: {e}")
                return None
        
        return cls._loaders[library_name]
    
    @classmethod
    def load_all_libraries(cls) -> Dict[str, int]:
        """
        Загрузка всех доступных библиотек.
        
        Returns:
            Словарь {библиотека: количество_индикаторов}
        """
        results = {}
        
        for lib_name in cls._loaders.keys():
            try:
                count = cls.load_library(lib_name)
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
            loader_class = cls._get_loader(library_name)
            if loader_class is None:
                logger.warning(f"Loader for {library_name} not available")
                return 0
            
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
            loader_class = cls._get_loader(library_name)
            if loader_class is None:
                return False
            return loader_class.is_available()
        except Exception:
            return False
    
    @classmethod
    def create_indicator(cls, library_name: str, indicator_name: str, **kwargs):
        """
        Создать индикатор из внешней библиотеки.
        
        Args:
            library_name: Название библиотеки
            indicator_name: Название индикатора
            **kwargs: Параметры индикатора
        
        Returns:
            Экземпляр индикатора
        """
        try:
            # Проверяем доступность библиотеки
            if not cls.check_library_availability(library_name):
                raise ValueError(f"Library {library_name} is not available")
            
            # Получаем загрузчик
            loader_class = cls._get_loader(library_name)
            if loader_class is None:
                raise ValueError(f"Loader for {library_name} not found")
            
            # Создаем индикатор через IndicatorFactory
            full_name = f"{library_name}_{indicator_name}"
            return IndicatorFactory.create_indicator(full_name, **kwargs)
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to create indicator {indicator_name} from {library_name}: {e}",
                {'library': library_name, 'indicator': indicator_name}
            )
    
    @classmethod
    def get_library_info(cls, library_name: str) -> Dict[str, Any]:
        """
        Получить информацию о библиотеке.
        
        Args:
            library_name: Название библиотеки
        
        Returns:
            Словарь с информацией о библиотеке
        """
        if library_name not in cls._loaders:
            return {'available': False, 'error': 'Unknown library'}
        
        try:
            loader_class = cls._get_loader(library_name)
            if loader_class is None:
                return {'available': False, 'error': 'Loader not available'}
            
            is_available = loader_class.is_available()
            if is_available:
                indicators = loader_class.get_available_indicators()
                return {
                    'available': True,
                    'indicators_count': len(indicators),
                    'indicators': indicators
                }
            else:
                return {'available': False, 'error': 'Library not installed'}
                
        except Exception as e:
            return {'available': False, 'error': str(e)}


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


def create_library_indicator(library_name: str, indicator_name: str, **kwargs):
    """
    Создать индикатор из внешней библиотеки.
    
    Args:
        library_name: Название библиотеки
        indicator_name: Название индикатора
        **kwargs: Параметры индикатора
    
    Returns:
        Экземпляр индикатора
    """
    return LibraryManager.create_indicator(library_name, indicator_name, **kwargs)
