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

Дополнительные функции-алиасы: `load_pandas_ta()`, `load_talib()`, `load_all_indicators()` — все три экспортируются из `bquant.indicators`.

## Быстрый старт: «простой способ» получить индикатор из pandas-ta

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

LibraryManager.load_all_libraries()
macd = LibraryManager.create_indicator('pandas_ta', 'macd', fast=12, slow=26, signal=9)

print(macd.calculate(data).data.columns.tolist())
# ['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']
```

`LibraryManager.create_indicator()` скрывает детали префиксов (`pandas_ta_macd`) и использует
`IndicatorFactory` для создания корректного экземпляра.

### Как называются выходные колонки

Имена колонок задаёт **сама библиотека**, и они включают параметры расчёта:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

print(LibraryManager.create_indicator('pandas_ta', 'rsi', length=14).calculate(data).data.columns.tolist())
print(LibraryManager.create_indicator('pandas_ta', 'rsi', length=50).calculate(data).data.columns.tolist())
# ['RSI_14']
# ['RSI_50']   <- имя следует за параметром
```

Практическое следствие: **не задавайте имя колонки константой, если меняете параметры.**
Узнать его заранее можно у самого индикатора:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=50)
print(rsi.get_output_columns())
# ['RSI_50']

result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=50)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze()
    .build()
)

print(len(result.zones))
# 4
```

Внутри пайплайна имя колонки не нужно вовсе: роль `value` разрешается по схеме, которую
пайплайн строит сам. `get_output_columns()` пригодится там, где кадр обрабатывают руками.

> **`zone_types` передавать не нужно** — с 0.0.6 умолчание `None` означает «не
> фильтровать», и пороговый детектор возвращает свои `overbought` / `neutral` /
> `oversold`. Раньше умолчанием было `['bull', 'bear']` — словарь MACD-подобных
> стратегий, — и на пороговом детекторе **все зоны отфильтровывались, а результат
> оказывался пуст**. Это был G19, он исправлен.

> **Изменение в 0.0.6 (G18).** Раньше имя выводилось один раз при регистрации индикатора,
> на дефолтных параметрах, и подставлялось всегда: `rsi(length=50)` считался верно, но
> колонка называлась `RSI_14`. Теперь имя соответствует фактическим параметрам. Вызовы
> **без параметров** не затронуты.

## Получение информации о библиотеках

```python
from bquant.indicators import LibraryManager

info = LibraryManager.get_library_info('pandas_ta')

print(info['available'], info['indicators_count'])
print(info['indicators'][:5])
# True 158
# ['aberration', 'accbands', 'ad', 'adosc', 'adx']
```

У недоступной библиотеки `available` будет `False`, а причина — в `info['error']`.

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
