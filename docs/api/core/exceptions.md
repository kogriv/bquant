# bquant.core.exceptions — Исключения

## Обзор

Кастомные исключения BQuant для однородной обработки ошибок в данных, анализе, визуализации и конфигурации.

## Классы

- `BQuantError(Exception)`: базовый класс всех исключений BQuant.
- `DataError(BQuantError)`: общие ошибки данных.
  - `DataValidationError`, `DataLoadingError`, `DataProcessingError`.
- `ConfigurationError(BQuantError)`: ошибки конфигурации.
  - `InvalidTimeframeError`, `InvalidIndicatorParametersError`.
- `AnalysisError(BQuantError)`: ошибки анализа.
  - `IndicatorCalculationError`, `ZoneAnalysisError`, `StatisticalAnalysisError`.
- `VisualizationError(BQuantError)`: ошибки визуализации.
- `MLError(BQuantError)`: ошибки ML (будущие модули).
  - `FeatureExtractionError`, `ModelTrainingError`.

## Фабрики ошибок

- `create_data_validation_error(message, column=None, expected_type=None, actual_type=None, expected_shape=None, actual_shape=None) -> DataValidationError`
- `create_indicator_calculation_error(indicator_name, message, parameters=None, data_shape=None) -> IndicatorCalculationError`
- `create_configuration_error(parameter_name, message, expected_values=None, actual_value=None) -> ConfigurationError`

## Контекст и валидаторы

- `BQuantErrorContext(operation, logger=None)`: контекстный менеджер обработки исключений (логирует и оборачивает чужие исключения в семейство BQuant).
- `validate_timeframe(timeframe, supported_timeframes)`: валидирует таймфрейм, бросает `InvalidTimeframeError`.
- `validate_indicator_parameters(indicator, parameters, required_params)`: проверяет обязательные параметры индикатора.
- `validate_ohlcv_data(data, required_columns=None)`: валидирует структуру OHLCV DataFrame.

## Примеры

Использование фабрики и перехват ошибок:
```python
from bquant.core.exceptions import (
    create_data_validation_error,
    DataValidationError,
    BQuantErrorContext,
)

try:
    raise create_data_validation_error("Неверный формат", expected_type="DataFrame", actual_type="dict")
except DataValidationError as e:
    print(e)

from bquant.core.logging_config import get_logger
logger = get_logger(__name__)

with BQuantErrorContext("load data", logger=logger):
    # Любая ошибка внутри будет обернута в BQuantError/ConfigurationError
    1 / 0
```
