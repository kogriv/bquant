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
                # 'source' deliberately absent: it duplicated
                # `IndicatorSource.PRELOADED` already carried by the config, and
                # a duplicated fact is a fact that can disagree with itself. It
                # also leaked into the identity slug, where it said nothing the
                # slug's own `source` field did not already say.
                'required_columns': required_columns
            },
            source=IndicatorSource.PRELOADED,
            columns=required_columns,
            description=f"MACD индикатор (PRELOADED) - fast=12, slow=26, smoothing=9, колонки: {required_columns}"
        )
        super().__init__(name, config)
    
    #: Роли выходов в том порядке, в каком класс их документирует
    #: (`get_info`: обязательные `macd`, `signal`, необязательный `histogram`).
    #: `required_columns` говорит, **в каких колонках кадра** они лежат, поэтому
    #: сопоставление позиционное — это и есть контракт класса, а не догадка по
    #: именам.
    _ROLE_ORDER = ("line", "signal", "hist")

    def get_output_columns(self) -> List[str]:
        """
        Возвращает выходные колонки индикатора.
        
        Returns:
            Список колонок, переданных при инициализации
        """
        return self._required_columns.copy()

    def get_output_roles(self) -> Dict[str, str]:
        """Роль → колонка, в которой лежит уже посчитанное значение.

        Имена здесь **чужие**: колонки пришли с данными (выгрузка TradingView
        зовёт их `macd` и `signal`), и переименовывать их нечего — индикатор
        ничего не вычисляет, он читает. Ровно этот случай и разделяет
        идентичность и роль: адресация по роли работает, а имена остаются теми,
        какими их дал источник.

        Если запрошено больше колонок, чем класс документирует ролей, честный
        ответ — пустой словарь: контракт исчерпан, и угадывать, чем является
        четвёртая колонка, значит вернуться к тому, из-за чего затевался G8.
        """
        if len(self._required_columns) > len(self._ROLE_ORDER):
            return {}
        return {
            role: column
            for role, column in zip(self._ROLE_ORDER, self._required_columns)
        }
    
    def get_required_columns(self) -> List[str]:
        """
        Возвращает колонки, которые должны быть в данных.

        Именно **запрошенные при создании**, а не умолчания класса. Ниже по коду
        этим списком и извлекают, и валидируют, поэтому подмена его умолчаниями
        означала, что параметр `required_columns` не действует ни там, ни там
        (G46). Раньше сразу за этим методом стоял его же одноимённый двойник с
        `@classmethod`, который молча выигрывал: Python оставляет последнее
        определение в теле класса и ни о чём не предупреждает.

        Returns:
            Список требуемых колонок, переданных при инициализации
        """
        return self._required_columns.copy()

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
            'available_methods': cls.available_methods()
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
                    # Всегда словарь: `None` не отличить от «не считали», а здесь
                    # считали всегда. Нули — такой же результат замера, как и всё
                    # остальное.
                    'nan_counts': nan_counts.to_dict()
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
    
