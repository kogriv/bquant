# LibraryManager — управление внешними индикаторами

`LibraryManager` централизует работу с внешними библиотеками индикаторов (например, `pandas-ta` и `TA-Lib`).
Он отвечает за загрузку, регистрацию динамических обёрток и предоставление «простого способа» создавать
индикаторы без ручного кода.

## Основные задачи

- Загрузка всех поддерживаемых библиотек одной командой.
- Динамическая регистрация индикаторов в `IndicatorFactory`.
- Предоставление информации о доступности библиотек и количестве индикаторов.
- Создание индикаторов по названию библиотеки и функции без знания внутренних префиксов.

## Публичные методы

| Метод | Описание |
|-------|----------|
| `load_all_libraries() -> Dict[str, int]` | Загружает все поддерживаемые библиотеки и возвращает количество зарегистрированных индикаторов для каждой. |
| `load_library(name: str) -> int` | Загружает конкретную библиотеку (`pandas_ta`, `talib`). |
| `get_available_libraries() -> List[str]` | Возвращает список поддерживаемых библиотек. |
| `check_library_availability(name: str) -> bool` | Проверяет, установлена ли библиотека и доступен ли загрузчик. |
| `get_library_info(name: str) -> Dict[str, Any]` | Возвращает структуру с признаками доступности, количеством и списком индикаторов или сообщением об ошибке. |
| `create_indicator(library: str, indicator: str, **params)` | Создаёт индикатор библиотеки, автоматически загружая соответствующую обёртку из `IndicatorFactory`. |

Дополнительные функции-алиасы: `load_pandas_ta()`, `load_talib()`, `load_all_indicators()`.

## Быстрый старт: «простой способ» получить индикатор из pandas-ta

```python
from bquant.indicators import LibraryManager

# 1. Загрузить все доступные библиотеки
LibraryManager.load_all_libraries()

# 2. Создать индикатор pandas-ta без ручной регистрации
macd = LibraryManager.create_indicator('pandas_ta', 'macd', fast=12, slow=26, signal=9)
result = macd.calculate(data)
```

`LibraryManager.create_indicator()` скрывает детали префиксов (`pandas_ta_macd`) и использует
`IndicatorFactory` для создания корректного экземпляра.

## Получение информации о библиотеках

```python
from bquant.indicators import LibraryManager

info = LibraryManager.get_library_info('pandas_ta')
if info['available']:
    print(f"Всего индикаторов: {info['indicators_count']}")
    print(f"Примеры: {info['indicators'][:5]}")
else:
    print(f"Библиотека недоступна: {info['error']}")
```

Информация полезна для отображения в интерфейсе или логировании. Список индикаторов (`info['indicators']`) отражает
все функции, обнаруженные динамическим загрузчиком `PandasTALoader`.

## Интеграция с IndicatorFactory

При вызове `load_all_libraries()` менеджер:

1. Импортирует соответствующие загрузчики (`PandasTALoader`, `TALibLoader`).
2. Запускает `register_indicators()` на каждом загрузчике. В случае pandas-ta создаются классы-наследники
   `LibraryIndicator` для каждой доступной функции.
3. Регистрирует новые классы в `IndicatorFactory` под ключами вида `pandas_ta_<имя>`.

После этого индикаторы доступны как через `LibraryManager.create_indicator()`, так и напрямую через
`IndicatorFactory.create('pandas_ta', '<имя>', **params)`.

## Обработка ошибок и логирование

- Недоступные библиотеки логируются с уровнем `warning`, а метод возвращает `0` индикаторов.
- При попытке создать индикатор из отсутствующей библиотеки выбрасывается `IndicatorCalculationError` с контекстом.
- `LibraryManager.load_all_libraries()` агрегирует результаты и сообщает общее количество зарегистрированных индикаторов.

## См. также

- [IndicatorFactory — фабрика индикаторов](factory.md)
- [PandasTALoader — динамический загрузчик pandas-ta](../indicators/README.md)
