"""
MACD PRELOADED Indicator

Индикатор для работы с уже готовыми данными MACD.
Извлекает значения MACD, signal и histogram из данных,
которые уже были рассчитаны с параметрами:
- fast=12, slow=26, smoothing=9
- цена=close

Используется для sample-данных и предобработанных файлов,
где MACD уже вычислен и встроен в данные.
"""

from typing import List, Dict, Any, Optional
import pandas as pd

from ..base import PreloadedIndicator, IndicatorResult, IndicatorSource, IndicatorConfig


class MACDPreloadedIndicator(PreloadedIndicator):
    """
    PRELOADED индикатор MACD для работы с готовыми данными.
    
    Этот индикатор извлекает уже рассчитанные значения из данных,
    не выполняя повторных вычислений. Предназначен для работы с:
    - Sample-данными BQuant
    - Предобработанными файлами с встроенными индикаторами
    - Данными, где индикаторы уже были рассчитаны
    
    Параметры оригинального расчета MACD:
    - fast=12 (быстрая EMA)
    - slow=26 (медленная EMA) 
    - smoothing=9 (сглаживание signal)
    - цена=close
    
    Особенности:
    - Гибкая настройка колонок для извлечения
    - Автоматическая валидация данных
    - Анализ трендов и пересечений для любых колонок
    """
    
    def __init__(self, name: str = "macd_preloaded", required_columns: Optional[List[str]] = None):
        """
        Инициализация PRELOADED MACD индикатора.
        
        Args:
            name: Название индикатора
            required_columns: Список колонок для извлечения из данных.
                            По умолчанию ['macd', 'signal']
        """
        # Определяем колонки для извлечения
        if required_columns is None:
            required_columns = self.get_default_columns()
        
        # Валидируем список колонок
        if not required_columns:
            raise ValueError("required_columns cannot be empty")
        
        # Проверяем, что все колонки являются строками
        if not all(isinstance(col, str) for col in required_columns):
            raise ValueError("All required_columns must be strings")
        
        # Сохраняем требуемые колонки ДО вызова super().__init__
        self._required_columns = required_columns.copy()
        
        config = IndicatorConfig(
            name=name,
            parameters={
                'fast': 12,
                'slow': 26, 
                'smoothing': 9,
                'price': 'close',
                'source': 'preloaded',
                'required_columns': required_columns
            },
            source=IndicatorSource.PRELOADED,
            columns=required_columns,
            description=f"MACD индикатор (PRELOADED) - fast=12, slow=26, smoothing=9, колонки: {required_columns}"
        )
        super().__init__(name, config)
    
    def get_output_columns(self) -> List[str]:
        """
        Возвращает выходные колонки индикатора.
        
        Returns:
            Список колонок, переданных при инициализации
        """
        return self._required_columns.copy()
    
    def get_required_columns(self) -> List[str]:
        """
        Возвращает колонки, которые должны быть в данных.
        
        Returns:
            Список требуемых колонок, переданных при инициализации
        """
        return self._required_columns.copy()
    
    @classmethod
    def get_required_columns(cls) -> List[str]:
        """
        Возвращает колонки по умолчанию для PRELOADED MACD индикатора.
        
        Returns:
            Список колонок по умолчанию: ['macd', 'signal']
        """
        return cls.get_default_columns()
    
    def get_min_records(self) -> int:
        """
        Минимальное количество записей для работы.
        
        Returns:
            Минимум 1 запись (данные уже готовы)
        """
        return 1
    
    @staticmethod
    def get_description() -> str:
        """
        Возвращает описание индикатора.
        
        Returns:
            Описание PRELOADED MACD индикатора
        """
        return (
            "MACD индикатор (PRELOADED) - извлекает уже рассчитанные значения "
            "MACD и signal из данных. Параметры оригинального расчета: "
            "fast=12, slow=26, smoothing=9, цена=close"
        )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """
        Возвращает колонки по умолчанию для PRELOADED MACD индикатора.
        
        Returns:
            Список колонок по умолчанию: ['macd', 'signal']
        """
        return ['macd', 'signal']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        Returns information about PRELOADED MACD indicator.
        
        Returns:
            Dictionary with indicator information
        """
        return {
            'name': 'MACDPreloadedIndicator',
            'type': 'PRELOADED',
            'description': 'MACD indicator for working with pre-calculated data',
            'default_columns': cls.get_default_columns(),
            'required_fields': {
                'macd': 'MACD line values (numeric)',
                'signal': 'Signal line values (numeric)'
            },
            'optional_fields': {
                'histogram': 'MACD histogram values (numeric)',
                'rsi': 'RSI values if available (numeric)'
            },
            'original_calculation_params': {
                'fast': 12,
                'slow': 26,
                'smoothing': 9,
                'price': 'close'
            },
            'usage_examples': {
                'basic': "MACDPreloadedIndicator()",
                'custom_columns': "MACDPreloadedIndicator(required_columns=['macd', 'signal'])",
                'single_column': "MACDPreloadedIndicator(required_columns=['macd'])"
            },
            'data_requirements': {
                'min_records': 1,
                'column_types': 'numeric',
                'source': 'preloaded_data'
            },
            'available_methods': [
                'calculate()',
                'validate_data()',
                'get_statistics()',
                'is_trending_up()',
                'is_trending_down()',
                'get_crossovers()'
            ]
        }
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Извлекает уже готовые значения MACD из данных.
        
        Args:
            data: DataFrame с данными, содержащий колонки 'macd' и 'signal'
            **kwargs: Дополнительные параметры (не используются для PRELOADED)
        
        Returns:
            IndicatorResult с данными MACD и signal
            
        Raises:
            ValueError: Если отсутствуют необходимые колонки
        """
        try:
            # Валидируем данные
            self.validate_data(data)
            
            # Получаем требуемые колонки
            required_cols = self.get_required_columns()
            missing_cols = [col for col in required_cols if col not in data.columns]
            
            if missing_cols:
                raise ValueError(
                    f"Missing required columns for MACD PRELOADED: {missing_cols}. "
                    f"Available columns: {list(data.columns)}"
                )
            
            # Извлекаем готовые значения MACD и signal
            result_data = data[required_cols].copy()
            
            # Проверяем на наличие NaN значений
            nan_counts = result_data.isnull().sum()
            if nan_counts.any():
                self.logger.warning(
                    f"Found NaN values in PRELOADED MACD data: {nan_counts.to_dict()}"
                )
            
            # Создаем результат
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'source': 'preloaded',
                    'calculation_method': 'extract_existing',
                    'original_params': {
                        'fast': 12,
                        'slow': 26,
                        'smoothing': 9,
                        'price': 'close'
                    },
                    'extracted_columns': self._required_columns,
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index(),
                    'total_records': len(result_data),
                    'nan_counts': nan_counts.to_dict() if nan_counts.any() else None
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to extract PRELOADED MACD data: {e}")
            raise
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Валидирует данные для PRELOADED MACD индикатора.
        
        Args:
            data: DataFrame для валидации
        
        Returns:
            True если данные валидны
            
        Raises:
            ValueError: Если данные невалидны
        """
        if data.empty:
            raise ValueError("Data is empty")
        
        # Проверяем наличие необходимых колонок
        required_cols = self.get_required_columns()
        missing_cols = [col for col in required_cols if col not in data.columns]
        
        if missing_cols:
            raise ValueError(
                f"Missing required columns for MACD PRELOADED: {missing_cols}"
            )
        
        # Проверяем минимальное количество записей
        if len(data) < self.get_min_records():
            raise ValueError(
                f"Insufficient data: {len(data)} records, minimum required: {self.get_min_records()}"
            )
        
        # Проверяем типы данных (должны быть числовыми)
        for col in required_cols:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise ValueError(
                    f"Column '{col}' must be numeric, got: {data[col].dtype}"
                )
        
        return True
    
    def get_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Возвращает статистику по PRELOADED MACD данным.
        
        Args:
            data: DataFrame с данными MACD
        
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
                column = self._required_columns[0]  # Используем первую колонку по умолчанию
            
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
                column = self._required_columns[0]  # Используем первую колонку по умолчанию
            
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
    
    def get_crossovers(self, data: pd.DataFrame, column1: str = None, column2: str = None) -> Dict[str, Any]:
        """
        Определяет пересечения между двумя колонками.
        
        Args:
            data: DataFrame с данными
            column1: Первая колонка для анализа пересечений. Если None, используется первая колонка
            column2: Вторая колонка для анализа пересечений. Если None, используется вторая колонка
        
        Returns:
            Словарь с информацией о пересечениях
        """
        try:
            result = self.calculate(data)
            result_data = result.data
            
            # Определяем колонки для анализа
            if column1 is None:
                column1 = self._required_columns[0] if len(self._required_columns) > 0 else None
            if column2 is None:
                column2 = self._required_columns[1] if len(self._required_columns) > 1 else None
            
            # Проверяем наличие колонок
            if column1 is None or column2 is None:
                self.logger.error(f"Need at least 2 columns for crossover analysis. Available: {list(result_data.columns)}")
                return {
                    'bullish_crossovers': 0,
                    'bearish_crossovers': 0,
                    'bullish_indices': [],
                    'bearish_indices': [],
                    'error': 'Insufficient columns for crossover analysis'
                }
            
            if column1 not in result_data.columns or column2 not in result_data.columns:
                self.logger.error(f"Columns '{column1}' or '{column2}' not found. Available: {list(result_data.columns)}")
                return {
                    'bullish_crossovers': 0,
                    'bearish_crossovers': 0,
                    'bullish_indices': [],
                    'bearish_indices': [],
                    'error': f'Columns {column1} or {column2} not found'
                }
            
            col1_values = result_data[column1]
            col2_values = result_data[column2]
            
            # Определяем пересечения
            crossover_up = (col1_values > col2_values) & (col1_values.shift(1) <= col2_values.shift(1))
            crossover_down = (col1_values < col2_values) & (col1_values.shift(1) >= col2_values.shift(1))
            
            return {
                'column1': column1,
                'column2': column2,
                'bullish_crossovers': crossover_up.sum(),  # col1 пересекает col2 снизу вверх
                'bearish_crossovers': crossover_down.sum(),  # col1 пересекает col2 сверху вниз
                'bullish_indices': crossover_up[crossover_up].index.tolist(),
                'bearish_indices': crossover_down[crossover_down].index.tolist()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to detect crossovers: {e}")
            return {
                'bullish_crossovers': 0,
                'bearish_crossovers': 0,
                'bullish_indices': [],
                'bearish_indices': [],
                'error': str(e)
            }
