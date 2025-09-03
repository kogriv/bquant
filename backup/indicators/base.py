"""
Base classes and architecture for BQuant indicators

This module provides the foundation for all technical indicators in BQuant.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Type, Callable
from dataclasses import dataclass
from datetime import datetime

from ..core.exceptions import IndicatorCalculationError
from ..core.logging_config import get_logger
from ..core.cache import cached, get_cache_manager

# Получаем логгер для модуля
logger = get_logger(__name__)


class IndicatorSource(Enum):
    """
    Источники индикаторов для BQuant.
    
    PRELOADED - предзагруженные индикаторы (встроенные в BQuant)
    LIBRARY - индикаторы из внешних библиотек (pandas-ta, talib)
    CUSTOM - пользовательские индикаторы
    """
    PRELOADED = "preloaded"
    LIBRARY = "library"
    CUSTOM = "custom"


@dataclass
class IndicatorConfig:
    """
    Конфигурация для индикаторов.
    
    Attributes:
        name: Название индикатора
        parameters: Параметры индикатора
        source: Источник индикатора
        columns: Ожидаемые колонки результата
        description: Описание индикатора
    """
    name: str
    parameters: Dict[str, Any]
    source: IndicatorSource
    columns: List[str]
    description: str = ""


@dataclass
class IndicatorResult:
    """
    Результат вычисления индикатора.
    
    Attributes:
        name: Название индикатора
        data: DataFrame с результатами
        config: Конфигурация индикатора
        metadata: Дополнительная информация
    """
    name: str
    data: pd.DataFrame
    config: IndicatorConfig
    metadata: Dict[str, Any]


class BaseIndicator(ABC):
    """
    Базовый класс для всех индикаторов BQuant.
    
    Этот класс определяет общий интерфейс для всех технических индикаторов.
    """
    
    def __init__(self, name: str, config: Optional[IndicatorConfig] = None):
        """
        Инициализация базового индикатора.
        
        Args:
            name: Название индикатора
            config: Конфигурация индикатора
        """
        self.name = name
        self.config = config or IndicatorConfig(
            name=name,
            parameters={},
            source=IndicatorSource.CUSTOM,
            columns=[],
            description=""
        )
        self.logger = get_logger(f"{__name__}.{name}")
        
        # Кэширование результатов
        self._cache = {}
        self._cache_enabled = True
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Абстрактный метод для вычисления индикатора.
        
        Args:
            data: DataFrame с ценовыми данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами вычисления
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Валидация входных данных.
        
        Args:
            data: DataFrame для валидации
        
        Returns:
            True если данные корректны
            
        Raises:
            IndicatorCalculationError: Если данные некорректны
        """
        if data.empty:
            raise IndicatorCalculationError(
                f"Empty DataFrame provided for indicator {self.name}",
                {'indicator': self.name}
            )
        
        # Проверка минимального количества записей
        min_records = self.get_min_records()
        if len(data) < min_records:
            raise IndicatorCalculationError(
                f"Insufficient data for {self.name}: {len(data)} < {min_records}",
                {'indicator': self.name, 'records': len(data), 'required': min_records}
            )
        
        # Проверка обязательных колонок
        required_columns = self.get_required_columns()
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise IndicatorCalculationError(
                f"Missing required columns for {self.name}: {missing_columns}",
                {'indicator': self.name, 'missing_columns': missing_columns}
            )
        
        return True
    
    def get_min_records(self) -> int:
        """
        Минимальное количество записей для вычисления индикатора.
        
        Returns:
            Минимальное количество записей
        """
        return 1
    
    def get_required_columns(self) -> List[str]:
        """
        Обязательные колонки для вычисления индикатора.
        
        Returns:
            Список обязательных колонок
        """
        return ['close']
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """
        Возвращает колонки по умолчанию для индикатора.
        
        Returns:
            Список колонок по умолчанию
        """
        raise NotImplementedError
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        Возвращает информацию об индикаторе.
        
        Returns:
            Словарь с информацией об индикаторе
        """
        raise NotImplementedError
    
    def enable_cache(self, enabled: bool = True):
        """Включить/выключить кэширование результатов."""
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()
    
    def clear_cache(self):
        """Очистить кэш результатов."""
        self._cache.clear()
    
    def _get_cache_key(self, data: pd.DataFrame, **kwargs) -> str:
        """Генерация ключа для кэширования."""
        data_hash = pd.util.hash_pandas_object(data).sum()
        params_str = str(sorted(kwargs.items()))
        return f"{self.name}_{data_hash}_{hash(params_str)}"
    
    def calculate_with_cache(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора с кэшированием.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        # Используем новую систему кэширования
        cache_manager = get_cache_manager()
        
        # Генерируем ключ кэша
        func_name = f"{self.__class__.__name__}.calculate"
        cache_key = cache_manager.memory_cache._generate_key(func_name, (data,), kwargs)
        
        # Проверяем кэш
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.debug(f"Cache hit for {self.name}")
            return cached_result
        
        # Вычисляем результат
        self.logger.debug(f"Cache miss for {self.name}, calculating...")
        result = self.calculate(data, **kwargs)
        
        # Сохраняем в кэш (время жизни 1 час)
        cache_manager.put(cache_key, result, ttl=3600, disk=True)
        
        return result


class PreloadedIndicator(BaseIndicator):
    """
    Базовый класс для предзагруженных (встроенных) индикаторов BQuant.
    """
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """
        Инициализация предзагруженного индикатора.
        
        Args:
            name: Название индикатора
            parameters: Параметры индикатора
        """
        config = IndicatorConfig(
            name=name,
            parameters=parameters or {},
            source=IndicatorSource.PRELOADED,
            columns=self.get_output_columns(),
            description=self.get_description()
        )
        super().__init__(name, config)
    
    @abstractmethod
    def get_output_columns(self) -> List[str]:
        """Возвращает список выходных колонок индикатора."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Возвращает описание индикатора."""
        pass


class LibraryIndicator(BaseIndicator):
    """
    Базовый класс для индикаторов из внешних библиотек.
    """
    
    def __init__(self, name: str, library_func: Callable, parameters: Dict[str, Any] = None):
        """
        Инициализация индикатора из библиотеки.
        
        Args:
            name: Название индикатора
            library_func: Функция из библиотеки
            parameters: Параметры для функции
        """
        self.library_func = library_func
        
        config = IndicatorConfig(
            name=name,
            parameters=parameters or {},
            source=IndicatorSource.LIBRARY,
            columns=[],  # Будет определено динамически
            description=f"Library indicator: {name}"
        )
        super().__init__(name, config)
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора через библиотечную функцию.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        try:
            self.validate_data(data)
            
            # Объединяем параметры из конфига и kwargs
            params = {**self.config.parameters, **kwargs}
            
            self.logger.info(f"Calculating {self.name} using library function")
            
            # Вызываем библиотечную функцию
            result_data = self.library_func(data, **params)
            
            # Убеждаемся, что результат - DataFrame
            if not isinstance(result_data, pd.DataFrame):
                if isinstance(result_data, pd.Series):
                    result_data = result_data.to_frame(name=self.name)
                else:
                    raise IndicatorCalculationError(
                        f"Library function returned unexpected type: {type(result_data)}",
                        {'indicator': self.name}
                    )
            
            # Обновляем конфигурацию с фактическими колонками
            self.config.columns = list(result_data.columns)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'library_function': str(self.library_func),
                    'calculation_time': datetime.now(),
                    'data_shape': result_data.shape
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate {self.name}: {e}",
                {'indicator': self.name, 'error': str(e)}
            )


class IndicatorFactory:
    """
    Фабрика для создания индикаторов.
    
    Предоставляет единый интерфейс для создания различных типов индикаторов.
    """
    
    _registry = {}
    _library_functions = {}
    
    @classmethod
    def register_indicator(cls, name: str, indicator_class: Type[BaseIndicator]):
        """
        Регистрация индикатора в фабрике.
        
        Args:
            name: Название индикатора
            indicator_class: Класс индикатора
        """
        cls._registry[name.lower()] = indicator_class
        logger.info(f"Registered indicator: {name}")
    
    @classmethod
    def register_library_function(cls, name: str, func: Callable):
        """
        Регистрация функции из библиотеки.
        
        Args:
            name: Название индикатора
            func: Функция из библиотеки
        """
        cls._library_functions[name.lower()] = func
        logger.info(f"Registered library function: {name}")
    
    @classmethod
    def create_indicator(cls, name: str, data: pd.DataFrame = None, **kwargs) -> BaseIndicator:
        """
        Создание индикатора по имени.
        
        Args:
            name: Название индикатора
            data: DataFrame с данными (для проверки)
            **kwargs: Параметры индикатора
        
        Returns:
            Экземпляр индикатора
        """
        name_lower = name.lower()
        
        # Сначала ищем в зарегистрированных индикаторах
        if name_lower in cls._registry:
            return cls._registry[name_lower](**kwargs)
        
        # Затем ищем в библиотечных функциях
        if name_lower in cls._library_functions:
            return LibraryIndicator(
                name=name,
                library_func=cls._library_functions[name_lower],
                parameters=kwargs
            )
        
        # Если не найден, возвращаем заглушку
        logger.warning(f"Indicator {name} not found, creating stub")
        return _StubIndicator(name, **kwargs)
    
    @classmethod
    def list_indicators(cls) -> Dict[str, str]:
        """
        Получить список доступных индикаторов.
        
        Returns:
            Словарь {название: источник}
        """
        indicators = {}
        
        for name in cls._registry:
            indicators[name] = "preloaded"
        
        for name in cls._library_functions:
            indicators[name] = "library"
        
        return indicators
    
    @classmethod
    def get_indicator_info(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию об индикаторе.
        
        Args:
            name: Название индикатора
        
        Returns:
            Информация об индикаторе или None
        """
        name_lower = name.lower()
        
        if name_lower in cls._registry:
            indicator_class = cls._registry[name_lower]
            return {
                'name': name,
                'source': 'preloaded',
                'class': indicator_class.__name__,
                'description': getattr(indicator_class, 'get_description', lambda: 'No description')()
            }
        
        if name_lower in cls._library_functions:
            func = cls._library_functions[name_lower]
            return {
                'name': name,
                'source': 'library',
                'function': str(func),
                'description': getattr(func, '__doc__', 'No description')
            }
        
        return None


class _StubIndicator(BaseIndicator):
    """
    Заглушка для неизвестных индикаторов.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name)
        self.parameters = kwargs
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Возвращает заглушку результата.
        """
        self.logger.warning(f"Using stub for indicator {self.name}")
        
        # Создаем DataFrame с NaN значениями
        result_data = pd.DataFrame(
            index=data.index,
            data={f"{self.name}_value": np.nan}
        )
        
        return IndicatorResult(
            name=self.name,
            data=result_data,
            config=self.config,
            metadata={'stub': True, 'parameters': self.parameters}
        )


# Экспорт основных классов
__all__ = [
    'IndicatorSource',
    'IndicatorConfig',
    'IndicatorResult',
    'BaseIndicator',
    'PreloadedIndicator',
    'LibraryIndicator',
    'IndicatorFactory'
]
