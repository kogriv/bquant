"""
Base classes for BQuant indicators - Updated version with new IndicatorFactory

This module contains the base classes for all indicators in BQuant.
"""

import pandas as pd
import numpy as np
import inspect
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass
from enum import Enum

from bquant.core.logging_config import get_logger
from bquant.core.exceptions import IndicatorCalculationError, DataValidationError
from .schema import IndicatorId

logger = get_logger(__name__)


class IndicatorSource(Enum):
    """Источники индикаторов."""
    PRELOADED = "preloaded"  # Готовые данные
    CUSTOM = "custom"         # Собственная реализация
    LIBRARY = "library"       # Внешняя библиотека


@dataclass
class IndicatorConfig:
    """Конфигурация индикатора."""
    name: str
    parameters: Dict[str, Any]
    source: IndicatorSource
    columns: List[str]
    description: str


@dataclass
class IndicatorResult:
    """Результат расчета индикатора."""
    name: str
    data: pd.DataFrame
    config: IndicatorConfig
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseIndicator(ABC):
    """
    Базовый абстрактный класс для всех индикаторов.
    """
    
    def __init__(self, name: str, config: IndicatorConfig):
        """
        Инициализация базового индикатора.
        
        Args:
            name: Название индикатора
            config: Конфигурация индикатора
        """
        self.name = name
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        pass
    
    def validate_data(self, data: pd.DataFrame, **params) -> bool:
        """Проверить кадр перед расчётом — и **отказать**, если он не годится.

        Возвращает ``True`` или поднимает :class:`DataValidationError`. До G58
        метод возвращал ``False`` и писал ошибку в лог, а ни один из пяти custom-
        индикаторов и оба базовых пути (preloaded, library) возвращённое значение
        не читали: расчёт шёл дальше и отдавал кадр из ``NaN`` той же длины, что
        неотличимо от «прогрев». Лог — не поток управления.

        Проверяется: обязательные колонки; число строк против
        :meth:`get_min_records` **по параметрам этого вызова** (``calculate(data,
        period=100)`` требует сто баров, а не двадцать из конструктора); числовой
        dtype обязательных колонок; отсутствие бесконечностей (``NaN`` — пропуск,
        это другая находка и дело чистки данных).

        Args:
            data: DataFrame с данными
            **params: параметры вызова, если они меняют требования к данным

        Returns:
            ``True``

        Raises:
            DataValidationError: с причиной по имени.
        """
        required_columns = self.get_required_columns() or []
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise DataValidationError(
                f"{self.name}: missing required columns {missing_columns}; "
                f"present: {list(data.columns)}"
            )

        min_records = self.get_min_records(**params)
        if min_records and len(data) < min_records:
            raise DataValidationError(
                f"{self.name}: {len(data)} rows, but at least {min_records} are needed "
                f"for these parameters. A shorter frame would yield nothing but NaN."
            )

        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise DataValidationError(
                    f"{self.name}: column '{col}' has dtype {data[col].dtype}, not a number. "
                    "Convert it before calculating."
                )
            values = data[col].to_numpy(dtype=float, na_value=np.nan)
            infinite = int(np.isinf(values).sum())
            if infinite:
                raise DataValidationError(
                    f"{self.name}: column '{col}' holds {infinite} infinite value(s); "
                    "an indicator over them is not a number either."
                )

        return True
    
    def get_required_columns(self) -> List[str]:
        """
        Получить список необходимых колонок.
        
        Returns:
            Список названий колонок
        """
        return []
    
    def get_min_records(self, **params) -> int:
        """
        Получить минимальное количество записей.

        Args:
            **params: параметры вызова, переопределяющие параметры конструктора
                (``calculate(data, period=100)``). Реализация обязана считать
                минимум по ним, а не по тому, с чем её создали.

        Returns:
            Минимальное количество записей
        """
        return 0
    
    def get_output_roles(self) -> Dict[str, str]:
        """Map each declared output **role** to the column this instance emits.

        The point of the map is that a consumer asks for a *role* — "the
        histogram" — instead of guessing the string ``'macd_hist'``. Until now
        the two were fused in one literal and the mapping lived nowhere, so every
        producer invented a name and every consumer guessed one
        (``devref/gaps/columns/``).

        The default covers the single-output case, which is unambiguous. An
        indicator with several outputs must override this; returning ``{}`` is
        honest — it says the roles are not declared — and a consumer will then
        report role addressing as unavailable rather than guess.
        """
        columns = self.get_output_columns()
        if len(columns) == 1:
            return {"value": columns[0]}
        return {}

    def get_indicator_id(self, **parameter_overrides: Any) -> IndicatorId:
        """Identity of this instance: name plus normalized parameters.

        Parameter order is taken from the constructor signature, i.e. **fixed by
        the declaration** rather than by the order a caller happened to pass
        keywords in — otherwise the same indicator would slug two ways.

        ``parameter_overrides`` exists because ``calculate(data, **kwargs)`` may
        be called with different periods than the instance was built with. The
        emitted column names have to describe **the series actually computed**;
        naming it after the instance would put the wrong parameters on the
        column, which is defect D3 of this gap (library outputs labelled with
        the parameters of registration rather than of the call).
        """
        try:
            signature = inspect.signature(type(self).__init__)
            order = tuple(
                name for name in signature.parameters
                if name not in ("self", "args", "kwargs")
            )
        except (TypeError, ValueError):  # pragma: no cover - exotic callables
            order = ()

        source = getattr(self.config, "source", None)
        source_name = getattr(source, "value", None) or str(source or "custom")

        parameters = dict(getattr(self.config, "parameters", {}) or {})
        parameters.update(parameter_overrides)

        return IndicatorId(
            source=source_name,
            name=self.name,
            parameters=parameters,
            parameter_order=order,
        )

    def get_output_columns(self) -> List[str]:
        """
        Получить список выходных колонок.
        
        Returns:
            Список названий колонок
        """
        return self.config.columns
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """
        Получить список колонок по умолчанию.
        
        Returns:
            Список названий колонок
        """
        raise NotImplementedError("Subclasses must implement get_default_columns")
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        Получить информацию о классе.
        
        Returns:
            Словарь с информацией о классе
        """
        raise NotImplementedError("Subclasses must implement get_info")


class PreloadedIndicator(BaseIndicator):
    """
    Базовый класс для PRELOADED индикаторов.
    
    Эти индикаторы извлекают готовые значения из данных,
    которые уже были рассчитаны ранее.
    """
    
    def __init__(self, name: str, config: IndicatorConfig):
        """
        Инициализация PRELOADED индикатора.
        
        Args:
            name: Название индикатора
            config: Конфигурация индикатора
        """
        super().__init__(name, config)
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Извлечение готовых значений из данных.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с извлеченными значениями
        """
        try:
            self.validate_data(data)
            
            # Извлекаем необходимые колонки
            required_columns = self.get_required_columns()
            if not required_columns:
                raise ValueError("No required columns specified")
            
            # Проверяем наличие колонок в данных
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"Missing columns in data: {missing_columns}")
            
            # Извлекаем данные
            result_data = data[required_columns].copy()
            
            # Переименовываем колонки если нужно
            output_columns = self.get_output_columns()
            if len(output_columns) == len(required_columns):
                result_data.columns = output_columns
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'extracted_columns': required_columns,
                    'source': 'preloaded',
                    'calculation_method': 'extraction'
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(f"Failed to extract PRELOADED data: {e}")
    
    def get_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Получить статистику по данным индикатора.
        
        Args:
            data: DataFrame с данными
        
        Returns:
            Словарь со статистикой
        """
        try:
            result = self.calculate(data)
            result_data = result.data
            
            stats = {}
            for col in result_data.columns:
                col_data = result_data[col].dropna()
                if len(col_data) > 0:
                    stats[col] = {
                        'count': len(col_data),
                        'min': float(col_data.min()),
                        'max': float(col_data.max()),
                        'mean': float(col_data.mean()),
                        'std': float(col_data.std()),
                        'median': float(col_data.median()),
                        'nan_count': result_data[col].isnull().sum()
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {e}")
            return {}
    
    def is_trending_up(self, data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool:
        """
        Проверяет, растет ли указанная колонка (тренд вверх).
        
        Args:
            data: DataFrame с данными
            column: Колонка для анализа тренда. Если None, используется первая колонка
            threshold: Порог для определения роста (по умолчанию 0.0)
        
        Returns:
            True если колонка растет выше порога
        """
        try:
            result = self.calculate(data)
            
            # Определяем колонку для анализа
            if column is None:
                column = result.data.columns[0]  # Используем первую колонку по умолчанию
            
            if column not in result.data.columns:
                self.logger.error(f"Column '{column}' not found in data. Available: {list(result.data.columns)}")
                return False
            
            values = result.data[column].dropna()
            
            if len(values) < 2:
                return False
            
            # Проверяем последние значения
            recent_values = values.tail(2)
            return recent_values.iloc[-1] > recent_values.iloc[-2] and recent_values.iloc[-1] > threshold
            
        except Exception as e:
            self.logger.error(f"Failed to check trend for column '{column}': {e}")
            return False
    
    def is_trending_down(self, data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool:
        """
        Проверяет, падает ли указанная колонка (тренд вниз).
        
        Args:
            data: DataFrame с данными
            column: Колонка для анализа тренда. Если None, используется первая колонка
            threshold: Порог для определения падения (по умолчанию 0.0)
        
        Returns:
            True если колонка падает ниже порога
        """
        try:
            result = self.calculate(data)
            
            # Определяем колонку для анализа
            if column is None:
                column = result.data.columns[0]  # Используем первую колонку по умолчанию
            
            if column not in result.data.columns:
                self.logger.error(f"Column '{column}' not found in data. Available: {list(result.data.columns)}")
                return False
            
            values = result.data[column].dropna()
            
            if len(values) < 2:
                return False
            
            # Проверяем последние значения
            recent_values = values.tail(2)
            return recent_values.iloc[-1] < recent_values.iloc[-2] and recent_values.iloc[-1] < threshold
            
        except Exception as e:
            self.logger.error(f"Failed to check trend for column '{column}': {e}")
            return False
    
    def get_crossovers(self, data: pd.DataFrame, column1: str = None, column2: str = None, 
                       lookback: int = 5) -> Dict[str, List[int]]:
        """
        Определяет пересечения между двумя колонками.
        
        Args:
            data: DataFrame с данными
            column1: Первая колонка для анализа
            column2: Вторая колонка для анализа
            lookback: Количество периодов для анализа
        
        Returns:
            Словарь с индексами пересечений
        """
        try:
            result = self.calculate(data)
            
            # Определяем колонки для анализа
            if column1 is None:
                column1 = result.data.columns[0]
            if column2 is None and len(result.data.columns) > 1:
                column2 = result.data.columns[1]
            else:
                column2 = column1
            
            if column1 not in result.data.columns or column2 not in result.data.columns:
                self.logger.error(f"Columns not found: {column1}, {column2}")
                return {'bullish': [], 'bearish': []}
            
            # Получаем данные
            series1 = result.data[column1].dropna()
            series2 = result.data[column2].dropna()
            
            if len(series1) < lookback or len(series2) < lookback:
                return {'bullish': [], 'bearish': []}
            
            # Анализируем пересечения
            bullish_crosses = []
            bearish_crosses = []
            
            for i in range(lookback, len(series1)):
                # Бычье пересечение: series1 пересекает series2 снизу вверх
                if (series1.iloc[i-1] <= series2.iloc[i-1] and 
                    series1.iloc[i] > series2.iloc[i]):
                    bullish_crosses.append(i)
                
                # Медвежье пересечение: series1 пересекает series2 сверху вниз
                elif (series1.iloc[i-1] >= series2.iloc[i-1] and 
                      series1.iloc[i] < series2.iloc[i]):
                    bearish_crosses.append(i)
            
            return {
                'bullish': bullish_crosses,
                'bearish': bearish_crosses
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate crossovers: {e}")
            return {'bullish': [], 'bearish': []}


class CustomIndicator(BaseIndicator):
    """
    Базовый класс для пользовательских и встроенных индикаторов BQuant.
    
    Этот класс предназначен для индикаторов, которые реализуют собственную логику расчета,
    а не просто извлекают готовые данные или используют внешние библиотеки.
    """
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """
        Инициализация пользовательского индикатора.
        
        Args:
            name: Название индикатора
            parameters: Параметры индикатора
        """
        config = IndicatorConfig(
            name=name,
            parameters=parameters or {},
            source=IndicatorSource.CUSTOM,
            columns=[],
            description=self.get_description()
        )
        super().__init__(name, config)
        # Колонки заполняются ПОСЛЕ того, как конфиг привязан к экземпляру.
        # Раньше `get_output_columns()` звался до `super().__init__`, то есть до
        # существования `self.config` — пока колонки были голым литералом, это
        # сходило с рук. Как только они выводятся из объявления ролей (а роль на
        # этапе C2b будет спрашивать имя у `get_indicator_id()`, а тот — у
        # конфига), тот же вызов упирался бы в AttributeError. Порядок починен
        # здесь, отдельно от переименования, чтобы C2b не начинался с красного.
        self.config.columns = self.get_output_columns()
    
    @abstractmethod
    def get_output_columns(self) -> List[str]:
        """Возвращает список выходных колонок индикатора."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Возвращает описание индикатора."""
        pass
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        pass
    
    def get_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Возвращает статистику по данным индикатора.
        
        Args:
            data: DataFrame с данными
        
        Returns:
            Словарь со статистикой
        """
        try:
            result = self.calculate(data)
            result_data = result.data
            
            stats = {}
            for col in result_data.columns:
                col_data = result_data[col].dropna()
                if len(col_data) > 0:
                    stats[col] = {
                        'count': len(col_data),
                        'min': float(col_data.min()),
                        'max': float(col_data.max()),
                        'mean': float(col_data.mean()),
                        'std': float(col_data.std()),
                        'median': float(col_data.median()),
                        'nan_count': result_data[col].isnull().sum()
                    }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {e}")
            return {}
    
    def is_trending_up(self, data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool:
        """
        Проверяет, растет ли указанная колонка (тренд вверх).
        
        Args:
            data: DataFrame с данными
            column: Колонка для анализа тренда. Если None, используется первая колонка
            threshold: Порог для определения роста (по умолчанию 0.0)
        
        Returns:
            True если колонка растет выше порога
        """
        try:
            result = self.calculate(data)
            
            # Определяем колонку для анализа
            if column is None:
                column = result.data.columns[0]  # Используем первую колонку по умолчанию
            
            if column not in result.data.columns:
                self.logger.error(f"Column '{column}' not found in data. Available: {list(result.data.columns)}")
                return False
            
            values = result.data[column].dropna()
            
            if len(values) < 2:
                return False
            
            # Проверяем последние значения
            recent_values = values.tail(2)
            return recent_values.iloc[-1] > recent_values.iloc[-2] and recent_values.iloc[-1] > threshold
            
        except Exception as e:
            self.logger.error(f"Failed to check trend for column '{column}': {e}")
            return False
    
    def is_trending_down(self, data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool:
        """
        Проверяет, падает ли указанная колонка (тренд вниз).
        
        Args:
            data: DataFrame с данными
            column: Колонка для анализа тренда. Если None, используется первая колонка
            threshold: Порог для определения падения (по умолчанию 0.0)
        
        Returns:
            True если колонка падает ниже порога
        """
        try:
            result = self.calculate(data)
            
            # Определяем колонку для анализа
            if column is None:
                column = result.data.columns[0]  # Используем первую колонку по умолчанию
            
            if column not in result.data.columns:
                self.logger.error(f"Column '{column}' not found in data. Available: {list(result.data.columns)}")
                return False
            
            values = result.data[column].dropna()
            
            if len(values) < 2:
                return False
            
            # Проверяем последние значения
            recent_values = values.tail(2)
            return recent_values.iloc[-1] < recent_values.iloc[-2] and recent_values.iloc[-1] < threshold
            
        except Exception as e:
            self.logger.error(f"Failed to check trend for column '{column}': {e}")
            return False
    
    def calculate_with_cache(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора с поддержкой кэширования.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        # Для CustomIndicator просто вызываем calculate, кэширование не реализовано
        return self.calculate(data, **kwargs)


class LibraryIndicator(BaseIndicator):
    """
    Базовый класс для индикаторов из внешних библиотек.
    
    Этот класс оборачивает функции из внешних библиотек (TA-Lib, pandas-ta)
    и предоставляет единый интерфейс для их использования.
    """
    
    def __init__(self, name: str, library_func: Callable, parameters: Dict[str, Any] = None):
        """
        Инициализация библиотечного индикатора.
        
        Args:
            name: Название индикатора
            library_func: Функция из внешней библиотеки
            parameters: Параметры индикатора
        """
        config = IndicatorConfig(
            name=name,
            parameters=parameters or {},
            source=IndicatorSource.LIBRARY,
            columns=[f"{name}_value"],
            description=f"Library indicator: {name}"
        )
        super().__init__(name, config)
        self.library_func = library_func
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Вычисление индикатора через внешнюю библиотеку.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            IndicatorResult с результатами
        """
        try:
            self.validate_data(data)
            
            # Объединяем параметры
            all_params = {**self.config.parameters, **kwargs}
            
            # Вызываем функцию библиотеки
            result = self.library_func(data, **all_params)
            
            # Обрабатываем результат
            if isinstance(result, pd.DataFrame):
                result_data = result
            elif isinstance(result, pd.Series):
                result_data = pd.DataFrame({f"{self.name}_value": result})
            else:
                # Для других типов результатов создаем DataFrame
                result_data = pd.DataFrame({f"{self.name}_value": result})
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'library_function': str(self.library_func),
                    'source': 'library',
                    'calculation_method': 'external_library'
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(f"Failed to calculate library indicator: {e}")
    
    @property
    def native_indicator(self):
        """
        Доступ к исходной функции библиотеки.
        
        Returns:
            Исходная функция из внешней библиотеки
        """
        return self.library_func


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
        # Снижаем уровень шума при массовой регистрации
        logger.debug(f"Registered indicator: {name}")
    
    @classmethod
    def register_library_function(cls, name: str, func: Callable):
        """
        Регистрация функции из библиотеки.
        
        Args:
            name: Название индикатора
            func: Функция из библиотеки
        """
        cls._library_functions[name.lower()] = func
        # Снижаем уровень шума при массовой регистрации
        logger.debug(f"Registered library function: {name}")
    
    @classmethod
    def create(cls, source: str, indicator: str, **params) -> BaseIndicator:
        """
        Единый метод создания индикаторов.
        
        Args:
            source: Источник индикатора ('preloaded', 'custom', 'talib', 'pandas_ta')
            indicator: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            Экземпляр индикатора
        
        Raises:
            ValueError: Если указан неизвестный источник
            KeyError: Если индикатор не найден
        """
        source_lower = source.lower()
        
        try:
            if source_lower == 'preloaded':
                return cls._create_preloaded(indicator, **params)
            elif source_lower == 'custom':
                return cls._create_custom(indicator, **params)
            elif source_lower in ['talib', 'pandas_ta']:
                return cls._create_library(source_lower, indicator, **params)
            else:
                raise ValueError(f"Unknown source: {source}. Available sources: preloaded, custom, talib, pandas_ta")
        except Exception as e:
            logger.error(f"Failed to create indicator {indicator} from {source}: {e}")
            raise
    
    @classmethod
    def _create_preloaded(cls, indicator: str, **params) -> BaseIndicator:
        """
        Создание PRELOADED индикатора.
        
        Args:
            indicator: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            Экземпляр PRELOADED индикатора
        """
        indicator_lower = indicator.lower()
        
        # Ищем в зарегистрированных индикаторах
        if indicator_lower in cls._registry:
            indicator_class = cls._registry[indicator_lower]
            # Проверяем, что это PRELOADED индикатор
            if issubclass(indicator_class, PreloadedIndicator):
                return indicator_class(**params)
            else:
                logger.warning(f"Indicator {indicator} is not PRELOADED type")
        
        # Если не найден, пробуем создать по шаблону
        if indicator_lower == 'macd':
            from .preloaded.macd import MACDPreloadedIndicator
            return MACDPreloadedIndicator(**params)
        
        raise KeyError(f"PRELOADED indicator '{indicator}' not found")
    
    @classmethod
    def _create_custom(cls, indicator: str, **params) -> BaseIndicator:
        """
        Создание CUSTOM индикатора.
        
        Args:
            indicator: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            Экземпляр CUSTOM индикатора
        """
        indicator_lower = indicator.lower()
        
        # Ищем в зарегистрированных индикаторах
        if indicator_lower in cls._registry:
            indicator_class = cls._registry[indicator_lower]
            # Проверяем, что это CUSTOM индикатор
            if issubclass(indicator_class, CustomIndicator):
                return indicator_class(**params)
            else:
                logger.warning(f"Indicator {indicator} is not CUSTOM type")
        
        # Если не найден, пробуем создать по шаблону
        if indicator_lower == 'sma':
            from .custom.sma import SimpleMovingAverage
            return SimpleMovingAverage(**params)
        elif indicator_lower == 'ema':
            from .custom.ema import ExponentialMovingAverage
            return ExponentialMovingAverage(**params)
        elif indicator_lower == 'rsi':
            from .custom.rsi import RelativeStrengthIndex
            return RelativeStrengthIndex(**params)
        elif indicator_lower == 'macd':
            from .custom.macd import MACD
            return MACD(**params)
        elif indicator_lower == 'bbands':
            from .custom.bollinger import BollingerBands
            return BollingerBands(**params)
        
        raise KeyError(f"CUSTOM indicator '{indicator}' not found")
    
    @classmethod
    def _create_library(cls, source: str, indicator: str, **params) -> BaseIndicator:
        """
        Создание LIBRARY индикатора.
        
        Args:
            source: Источник библиотеки ('talib', 'pandas_ta')
            indicator: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            Экземпляр LIBRARY индикатора
        """
        indicator_lower = indicator.lower()
        
        # Ищем в зарегистрированных индикаторах с учетом источника
        registry_key = f"{source}_{indicator_lower}"
        if registry_key in cls._registry:
            indicator_class = cls._registry[registry_key]
            if issubclass(indicator_class, LibraryIndicator):
                return indicator_class(**params)
            logger.warning(f"Indicator {indicator} is not LIBRARY type")

        # Library indicators exist only through their loader: it registers them when
        # the library imports. An unregistered name therefore means the library is
        # not installed or has not been loaded — say that, not the name of a class.
        # (A "template" fallback used to live here and imported TALibSMA/TALibRSI/…
        # from library.talib — classes that module never defined, so the error for a
        # missing TA-Lib read "cannot import name 'TALibRSI'".)
        raise KeyError(
            f"LIBRARY indicator '{indicator}' from '{source}' is not registered: "
            f"the library is not installed or its loader has not run "
            f"(LibraryManager.load_all_libraries())"
        )
    
    @classmethod
    def create_indicator(cls, name: str, data: pd.DataFrame = None, **kwargs) -> BaseIndicator:
        """
        Создание индикатора по имени (устаревший метод, используйте create()).
        
        Args:
            name: Название индикатора
            data: DataFrame с данными (для проверки)
            **kwargs: Параметры индикатора
        
        Returns:
            Экземпляр индикатора
        """
        logger.warning("create_indicator() is deprecated, use create() instead")
        # Пытаемся определить тип индикатора автоматически
        name_lower = name.lower()
        
        # Проверяем, есть ли индикатор в реестре
        if name_lower in cls._registry:
            indicator_class = cls._registry[name_lower]
            if issubclass(indicator_class, PreloadedIndicator):
                return cls._create_preloaded(name, **kwargs)
            elif issubclass(indicator_class, CustomIndicator):
                return cls._create_custom(name, **kwargs)
            elif issubclass(indicator_class, LibraryIndicator):
                return indicator_class(**kwargs)
        
        # Если не найден в реестре, пробуем создать как CUSTOM
        try:
            return cls._create_custom(name, **kwargs)
        except KeyError:
            # Если не получилось как CUSTOM, пробуем как PRELOADED
            try:
                return cls._create_preloaded(name, **kwargs)
            except KeyError:
                raise KeyError(f"Indicator '{name}' not found in any source")
    
    @classmethod
    def list_indicators(cls) -> Dict[str, str]:
        """
        Получить список доступных индикаторов.
        
        Returns:
            Словарь {название: источник}
        """
        indicators = {}
        
        # Добавляем PRELOADED индикаторы
        for name in cls._registry:
            indicator_class = cls._registry[name]
            if issubclass(indicator_class, PreloadedIndicator):
                indicators[name] = "preloaded"
            elif issubclass(indicator_class, CustomIndicator):
                indicators[name] = "custom"
            elif issubclass(indicator_class, LibraryIndicator):
                indicators[name] = "library"
            else:
                indicators[name] = "unknown"
        
        # Добавляем библиотечные функции
        for name in cls._library_functions:
            indicators.setdefault(name, "library_function")

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
            
            # Определяем тип индикатора
            if issubclass(indicator_class, PreloadedIndicator):
                source = "preloaded"
            elif issubclass(indicator_class, CustomIndicator):
                source = "custom"
            elif issubclass(indicator_class, LibraryIndicator):
                source = "library"
            else:
                source = "unknown"
            
            # Создаем экземпляр для получения описания
            try:
                # Пытаемся создать экземпляр с параметрами по умолчанию
                instance = indicator_class()
                description = instance.get_description()
            except Exception:
                description = 'No description'
            
            return {
                'name': name,
                'source': source,
                'class': indicator_class.__name__,
                'description': description
            }
        
        if name_lower in cls._library_functions:
            func = cls._library_functions[name_lower]
            return {
                'name': name,
                'source': 'library_function',
                'function': str(func),
                'description': getattr(func, '__doc__', 'No description')
            }
        
        return None
    
    @classmethod
    def get_indicators_by_source(cls, source: str) -> List[str]:
        """
        Получить список индикаторов по источнику.
        
        Args:
            source: Источник индикаторов ('preloaded', 'custom', 'library')
        
        Returns:
            Список названий индикаторов
        """
        source_lower = source.lower()
        indicators = []
        
        for name, indicator_class in cls._registry.items():
            if source_lower == 'preloaded' and issubclass(indicator_class, PreloadedIndicator):
                indicators.append(name)
            elif source_lower == 'custom' and issubclass(indicator_class, CustomIndicator):
                indicators.append(name)
            elif source_lower == 'library' and issubclass(indicator_class, LibraryIndicator):
                indicators.append(name)
        
        return indicators


class _StubIndicator(BaseIndicator):
    """
    Заглушка для неизвестных индикаторов.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, IndicatorConfig(
            name=name,
            parameters=kwargs,
            source=IndicatorSource.CUSTOM,
            columns=[f"{name}_value"],
            description=f"Stub indicator: {name}"
        ))
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
    'CustomIndicator',
    'LibraryIndicator',
    'IndicatorFactory'
]
