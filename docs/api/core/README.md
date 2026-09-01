# Ядро — `bquant.core`

Шесть модулей, на которых стоит всё остальное: пути и параметры, исключения,
логирование, замер производительности, утилиты и сценарии в стиле ноутбука.

| Модуль | Отвечает за | Страница |
|---|---|---|
| `config` | пути проекта, таймфреймы, параметры по умолчанию, фабрики стратегий | [Конфигурация](config.md) |
| `exceptions` | иерархия ошибок, фабрики сообщений, контекст | [Исключения](exceptions.md) |
| `logging_config` | профили, модульные уровни, контекстные логгеры | [Логирование](logging.md) |
| `performance` | декоратор и контекст замера, монитор, бенчмарки | [Производительность](performance.md) |
| `utils` | доходности, нормировка, сохранение, проверки | [Утилиты](utils.md) |
| `nb` | `NotebookSimulator` — пошаговые research-скрипты | [Notebook-скрипты](nb.md) |

Сорок одно имя поднято в `bquant.core` напрямую — исключения, `get_logger`,
`setup_logging`, `NotebookSimulator`, константы путей и утилиты; спрашивать у
`bquant.core.__all__`, а не переписывать список сюда.

## Конфигурация

```python
from bquant.core.config import get_indicator_params, validate_timeframe

print(validate_timeframe('1h'))
print(get_indicator_params('macd'))
print(get_indicator_params('macd', fast=5))
# 1h
# {'fast': 12, 'slow': 26, 'signal': 9}
# {'fast': 5, 'slow': 26, 'signal': 9}
```

Имена параметров здесь — в стиле внешних библиотек (`fast`/`slow`/`signal`), а
встроенные индикаторы принимают свои (`fast_period`). Словарь сюда не передаётся как
есть; подробности — [конфигурация](config.md).

## Исключения

```python
from bquant.core.exceptions import BQuantError, DataError, create_data_validation_error

try:
    raise create_data_validation_error("нужен DataFrame", expected_type="DataFrame",
                                       actual_type="dict")
except DataError as error:
    print(type(error).__name__, isinstance(error, BQuantError))
    print(error.details)
# DataValidationError True
# {'expected_type': 'DataFrame', 'actual_type': 'dict'}
```

Всё семейство наследует `BQuantError`, поэтому одна ветка `except` ловит любую ошибку
пакета и не ловит чужие. Разбор — [исключения](exceptions.md).

## Логирование

```python
import logging

from bquant.core.logging_config import LOGGING_PROFILES, get_logger, setup_logging

print(sorted(LOGGING_PROFILES))
# ['audit', 'clean', 'critical', 'debug', 'focused', 'research', 'verbose']

setup_logging(profile='research')
logger = get_logger(__name__, context={'symbol': 'XAUUSD'})
logger.info('готово')
```

Семь профилей — от `research` (технические детали в файл, не в консоль) до `debug`.
Профиль применяется ко всему дереву `bquant.*`; отдельные модули настраиваются через
`modules_config` и `exceptions`. Подробности — [логирование](logging.md).

## Замер производительности

```python
from bquant.core.performance import get_performance_monitor, performance_monitor

@performance_monitor
def analyse(values):
    return sum(values)

analyse([1, 2, 3])

print('analyse' in ' '.join(get_performance_monitor().get_stats()))
# True
```

Декоратор пишется **и без скобок, и со скобками** — обе формы равноправны. До
2026-09-01 работала только форма со скобками, а без них декоратор молча подменял
функцию: вызов возвращал внутренний объект вместо результата
(`devref/gaps/core/g43_…`). Подробности и монитор — [производительность](performance.md).

## Утилиты

```python
from bquant.core.utils import calculate_returns, validate_ohlcv_columns
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
check = validate_ohlcv_columns(data)

print(check['is_valid'], check['missing_required'])
print(round(float(calculate_returns(data['close'], method='log').iloc[1]), 6))
# True []
# 0.00229
```

## Notebook-скрипты

```python
from bquant.core.nb import NotebookSimulator

nb = NotebookSimulator("Пример анализа")

nb.step("Загрузка данных")
nb.success("Данные загружены")
nb.wait()

nb.finish()
```

Полный справочник — [notebook-скрипты](nb.md).

## Совместимость с numpy

`bquant.core` поднимает три функции из `bquant.core.numpy_fix` и константу `NaN`.
**Вызывать их вручную не нужно** — `apply_numpy_fixes()` выполняется при импорте, до
того как пакетом начнут пользоваться. Экспортированы они, чтобы состояние совместимости
можно было *спросить*, а не чтобы им управлять.

* `apply_numpy_fixes()` — восстанавливает `np.NaN`, убранный в numpy 2.x, от которого
  зависят некоторые сторонние библиотеки. Идемпотентна.
* `ensure_numpy_compatibility()` — то же, но сперва проверяет, нужно ли.
* `check_numpy_compatibility() -> dict` — отчёт, ничего не меняет.

```python
from bquant.core import check_numpy_compatibility

info = check_numpy_compatibility()
print(sorted(info))
# ['fixes_applied', 'has_NaN', 'has_nan', 'issues', 'numpy_version']
```

`fixes_applied` отвечает на вопрос «понадобилось ли чинить», а не «вызывали ли
функцию»: на numpy, где `NaN` на месте, там будет `False`.

## Дальше

| | |
|---|---|
| [Данные](../data/README.md) | загрузка, обработка, валидация |
| [Индикаторы](../indicators/README.md) | что считать |
| [Анализ](../analysis/README.md) | зоны, статистика, стратегии |
| [Визуализация](../visualization/README.md) | графики |
