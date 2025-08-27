"""
Исключения системы BQuant

Определение кастомных исключений для различных компонентов системы.
"""

from typing import Optional, Any, Dict


class BQuantError(Exception):
    """
    Базовое исключение BQuant
    
    Все исключения BQuant должны наследоваться от этого класса.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Args:
            message: Сообщение об ошибке
            details: Дополнительные детали ошибки
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} (Details: {details_str})"
        return self.message


class DataError(BQuantError):
    """
    Ошибка данных
    
    Возникает при проблемах с загрузкой, обработкой или валидацией данных.
    """
    pass


class DataValidationError(DataError):
    """
    Ошибка валидации данных
    
    Возникает когда данные не соответствуют ожидаемому формату или содержат ошибки.
    """
    pass


class DataLoadingError(DataError):
    """
    Ошибка загрузки данных
    
    Возникает при невозможности загрузить данные из источника.
    """
    pass


class DataProcessingError(DataError):
    """
    Ошибка обработки данных
    
    Возникает при ошибках во время обработки или трансформации данных.
    """
    pass


class ConfigurationError(BQuantError):
    """
    Ошибка конфигурации
    
    Возникает при проблемах с конфигурационными параметрами.
    """
    pass


class InvalidTimeframeError(ConfigurationError):
    """
    Ошибка неверного таймфрейма
    
    Возникает при использовании неподдерживаемого таймфрейма.
    """
    pass


class InvalidIndicatorParametersError(ConfigurationError):
    """
    Ошибка неверных параметров индикатора
    
    Возникает при передаче некорректных параметров для расчета индикатора.
    """
    pass


class AnalysisError(BQuantError):
    """
    Ошибка анализа
    
    Возникает при проблемах в аналитических модулях.
    """
    pass


class IndicatorCalculationError(AnalysisError):
    """
    Ошибка расчета индикатора
    
    Возникает при невозможности рассчитать технический индикатор.
    """
    pass


class ZoneAnalysisError(AnalysisError):
    """
    Ошибка анализа зон
    
    Возникает при проблемах в процессе анализа зон MACD или других индикаторов.
    """
    pass


class StatisticalAnalysisError(AnalysisError):
    """
    Ошибка статистического анализа
    
    Возникает при проблемах в статистических тестах или расчетах.
    """
    pass


class VisualizationError(BQuantError):
    """
    Ошибка визуализации
    
    Возникает при проблемах с созданием графиков или визуализаций.
    """
    pass


class MLError(BQuantError):
    """
    Ошибка машинного обучения
    
    Возникает при проблемах в ML модулях (пока в разработке).
    """
    pass


class FeatureExtractionError(MLError):
    """
    Ошибка извлечения признаков
    
    Возникает при проблемах с извлечением признаков для ML.
    """
    pass


class ModelTrainingError(MLError):
    """
    Ошибка обучения модели
    
    Возникает при проблемах в процессе обучения ML модели.
    """
    pass


class FileOperationError(BQuantError):
    """
    Ошибка файловых операций
    
    Возникает при проблемах с чтением/записью файлов.
    """
    pass


class NotImplementedError(BQuantError):
    """
    Ошибка незавершенной функциональности
    
    Возникает при обращении к функциональности, которая еще не реализована.
    """
    pass


# Вспомогательные функции для создания исключений

def create_data_validation_error(
    message: str,
    column: Optional[str] = None,
    expected_type: Optional[str] = None,
    actual_type: Optional[str] = None,
    expected_shape: Optional[tuple] = None,
    actual_shape: Optional[tuple] = None
) -> DataValidationError:
    """
    Создать исключение валидации данных с деталями
    """
    details = {}
    if column:
        details['column'] = column
    if expected_type:
        details['expected_type'] = expected_type
    if actual_type:
        details['actual_type'] = actual_type
    if expected_shape:
        details['expected_shape'] = expected_shape
    if actual_shape:
        details['actual_shape'] = actual_shape
    
    return DataValidationError(message, details)


def create_indicator_calculation_error(
    indicator_name: str,
    message: str,
    parameters: Optional[Dict[str, Any]] = None,
    data_shape: Optional[tuple] = None
) -> IndicatorCalculationError:
    """
    Создать исключение расчета индикатора с деталями
    """
    details = {'indicator': indicator_name}
    if parameters:
        details['parameters'] = parameters
    if data_shape:
        details['data_shape'] = data_shape
    
    return IndicatorCalculationError(message, details)


def create_configuration_error(
    parameter_name: str,
    message: str,
    expected_values: Optional[list] = None,
    actual_value: Optional[Any] = None
) -> ConfigurationError:
    """
    Создать исключение конфигурации с деталями
    """
    details = {'parameter': parameter_name}
    if expected_values:
        details['expected_values'] = expected_values
    if actual_value is not None:
        details['actual_value'] = actual_value
    
    return ConfigurationError(message, details)


# Контекстные менеджеры для обработки исключений

class BQuantErrorContext:
    """
    Контекстный менеджер для обработки исключений BQuant
    """
    
    def __init__(self, operation: str, logger=None):
        """
        Args:
            operation: Описание операции
            logger: Логгер для записи ошибок
        """
        self.operation = operation
        self.logger = logger
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.logger:
                self.logger.error(f"Ошибка в операции '{self.operation}': {exc_val}")
            
            # Если это не наше исключение, оборачиваем его
            if not isinstance(exc_val, BQuantError):
                if exc_type in (ValueError, TypeError):
                    # Конвертируем стандартные исключения в наши
                    raise ConfigurationError(
                        f"Ошибка в операции '{self.operation}': {exc_val}"
                    ) from exc_val
                else:
                    # Оборачиваем все остальные в базовое исключение
                    raise BQuantError(
                        f"Неожиданная ошибка в операции '{self.operation}': {exc_val}"
                    ) from exc_val
        
        return False  # Не подавляем исключение


# Валидаторы с исключениями

def validate_timeframe(timeframe: str, supported_timeframes: list):
    """
    Валидировать таймфрейм с выбросом исключения
    """
    if timeframe not in supported_timeframes:
        raise InvalidTimeframeError(
            f"Неподдерживаемый таймфрейм: {timeframe}",
            {
                'timeframe': timeframe,
                'supported_timeframes': supported_timeframes
            }
        )


def validate_indicator_parameters(indicator: str, parameters: Dict[str, Any], required_params: list):
    """
    Валидировать параметры индикатора с выбросом исключения
    """
    missing_params = [param for param in required_params if param not in parameters]
    if missing_params:
        raise InvalidIndicatorParametersError(
            f"Отсутствуют обязательные параметры для индикатора {indicator}: {missing_params}",
            {
                'indicator': indicator,
                'missing_parameters': missing_params,
                'provided_parameters': list(parameters.keys())
            }
        )


def validate_ohlcv_data(data, required_columns: list = None):
    """
    Валидировать OHLCV данные с выбросом исключения
    """
    import pandas as pd
    
    if not isinstance(data, pd.DataFrame):
        raise create_data_validation_error(
            "Данные должны быть pandas DataFrame",
            expected_type="pandas.DataFrame",
            actual_type=type(data).__name__
        )
    
    required_columns = required_columns or ['open', 'high', 'low', 'close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        raise create_data_validation_error(
            f"Отсутствуют обязательные колонки: {missing_columns}",
            expected_type="OHLCV columns",
            actual_type=list(data.columns)
        )
    
    if len(data) == 0:
        raise create_data_validation_error(
            "DataFrame не содержит данных",
            expected_shape="(n_rows > 0, n_cols)",
            actual_shape=data.shape
        )
