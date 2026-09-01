# `bquant.core.exceptions` — исключения

Одно дерево ошибок на весь пакет: любая ошибка bquant наследует `BQuantError`, поэтому
одна ветка `except` ловит их все и не ловит чужие.

## Дерево

```
BQuantError
├── DataError
│   ├── DataValidationError
│   ├── DataLoadingError
│   └── DataProcessingError
├── ConfigurationError
│   ├── InvalidTimeframeError
│   └── InvalidIndicatorParametersError
├── AnalysisError
│   ├── IndicatorCalculationError
│   ├── ZoneAnalysisError
│   └── StatisticalAnalysisError
├── VisualizationError
├── MLError
│   ├── FeatureExtractionError
│   └── ModelTrainingError
├── FileOperationError
└── NotImplementedError
```

```python
from bquant.core.exceptions import BQuantError, DataError, DataValidationError

print(issubclass(DataValidationError, DataError), issubclass(DataError, BQuantError))
print(issubclass(DataValidationError, Exception))
# True True
# True
```

**`NotImplementedError` здесь перекрывает встроенное имя.** Это класс пакета, не
`builtins.NotImplementedError`, и ни одна строка пакета его не поднимает. Импортировать
его в модуль, где ловят обычный `NotImplementedError`, — верный способ получить
`except`, который не сработает. Имя оставлено ради обратной совместимости; при импорте
из этого модуля стоит переименовывать: `from bquant.core.exceptions import
NotImplementedError as BQuantNotImplementedError`.

## Что несёт исключение

```python
from bquant.core.exceptions import BQuantError

error = BQuantError("что-то пошло не так", details={'symbol': 'XAUUSD'})

print(str(error))
print(error.message, error.details)
# что-то пошло не так (Details: symbol=XAUUSD)
# что-то пошло не так {'symbol': 'XAUUSD'}
```

Детали идут отдельным словарём и попадают в текст — значит их видно и в логе, и в
трассировке, и программно.

## Фабрики

Три функции собирают исключение с уже разложенными деталями, чтобы каждое место не
придумывало свой формат:

```python
from bquant.core.exceptions import (
    create_configuration_error,
    create_data_validation_error,
    create_indicator_calculation_error,
)

print(create_data_validation_error("нужен DataFrame", expected_type="DataFrame",
                                   actual_type="dict").details)
print(create_indicator_calculation_error("macd", "не хватает баров",
                                         parameters={'fast': 12}).details)
print(create_configuration_error("timeframe", "не поддерживается",
                                 expected_values=['1h', '4h'], actual_value='2D').details)
# {'expected_type': 'DataFrame', 'actual_type': 'dict'}
# {'indicator': 'macd', 'parameters': {'fast': 12}}
# {'parameter': 'timeframe', 'expected_values': ['1h', '4h'], 'actual_value': '2D'}
```

Каждая принимает необязательные поля и кладёт в `details` только те, что переданы —
пустые ключи не выдумываются.

## Валидаторы

```python
import pandas as pd

from bquant.core.exceptions import InvalidTimeframeError, validate_timeframe

try:
    validate_timeframe('2D', ['1h', '4h', '1d'])
except InvalidTimeframeError as error:
    print(error.details)
# {'timeframe': '2D', 'supported_timeframes': ['1h', '4h', '1d']}
```

| Функция | Проверяет |
|---|---|
| `validate_timeframe(timeframe, supported_timeframes)` | таймфрейм в списке поддерживаемых |
| `validate_indicator_parameters(indicator, parameters, required_params)` | все обязательные параметры переданы |
| `validate_ohlcv_data(data, required_columns=None)` | кадр не пуст и содержит нужные колонки |

Список поддерживаемых таймфреймов здесь передаётся **аргументом** — модуль исключений
ничего не знает о конфигурации. Одноимённая
[`config.validate_timeframe(timeframe)`](config.md) берёт список сама и поднимает
обычный `ValueError`; это разные функции с одинаковыми именами, и путать их не стоит.

## Контекст операции

```python
from bquant.core.exceptions import BQuantError, BQuantErrorContext

try:
    with BQuantErrorContext("загрузка данных"):
        1 / 0
except BQuantError as error:
    print(type(error).__name__)
    print(error.details['operation'], error.details['original_error'])
# BQuantError
# загрузка данных ZeroDivisionError
```

Менеджер логирует ошибку и **оборачивает чужое исключение**, сохраняя имя операции и
тип исходной ошибки в `details`. `ValueError` и `TypeError` становятся
`ConfigurationError`, всё прочее — `BQuantError`. Исключения самого пакета проходят как
есть, со своими деталями: оборачивать их незачем.

До 2026-09-01 имя операции попадало только в текст сообщения, и достать его можно было
разбором строки. Тот же принцип, что в G31: свойство, а не проза.

## Как это ловить

```python
from bquant.core.exceptions import AnalysisError, BQuantError, DataError

try:
    ...  # работа с пакетом
except DataError:
    ...  # проблема во входных данных
except AnalysisError:
    ...  # проблема в расчёте
except BQuantError:
    ...  # всё остальное из пакета
```

Порядок веток — от частного к общему; последняя гарантированно ловит любую ошибку
пакета и **не** ловит ошибки чужого кода, что и позволяет отличить своё от постороннего.

## Дальше

| | |
|---|---|
| [Конфигурация](config.md) | вторая `validate_timeframe`, с которой не надо путать |
| [Валидация данных](../data/validator.md) | проверки, возвращающие отчёт, а не бросающие |
| [Логирование](logging.md) | куда уходит запись об ошибке |
