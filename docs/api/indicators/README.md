# Индикаторы — `bquant.indicators`

Четыре источника индикаторов за одной фабрикой. Что бы вы ни выбрали, дальше это ведёт
себя одинаково: считает колонки, объявляет их роли и подходит пайплайну зон.

| Источник | Что это | Сколько |
|---|---|---|
| `custom` | реализации внутри пакета, без внешних зависимостей | 5 |
| `preloaded` | чтение уже посчитанных колонок из кадра | 1 |
| `pandas_ta` | всё из `pandas-ta` | 158 |
| `talib` | всё из TA-Lib, если библиотека установлена | 0, пока не установлена |

```python
from collections import Counter

from bquant.indicators import IndicatorFactory

catalogue = IndicatorFactory.list_indicators()

print(len(catalogue))
print(Counter(catalogue.values()))
# 164
# Counter({'library': 158, 'custom': 5, 'preloaded': 1})
```

## Страницы

| | |
|---|---|
| [Базовые классы](base.md) | `BaseIndicator`, `IndicatorResult`, `IndicatorConfig`, `IndicatorSource` |
| [Фабрика](factory.md) | `IndicatorFactory` — создание из любого источника |
| [Встроенные](custom.md) | SMA, EMA, RSI, MACD, Bollinger Bands |
| [Preloaded](preloaded.md) | индикатор поверх готовых колонок |
| [Внешние библиотеки](library_manager.md) | `LibraryManager`, pandas-ta, TA-Lib |
| [MACD](macd.md) | где искать MACD после удаления модуля |

Файлов `bquant/indicators/factory.py`, `library_manager.py` и `macd.py` не существует:
фабрика живёт в `base`, менеджер библиотек — в пакете `library`, MACD — в `custom` и
`preloaded`. Страницы названы по предмету, а не по файлу.

## Как создать индикатор

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory

data = get_sample_data('tv_xauusd_1h')

macd = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
result = macd.calculate(data)

print(result.data.columns.tolist())
# ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']
```

Имя колонки собирается из **фактических параметров вызова**, поэтому меняется вместе с
ними. Адресоваться к колонке именем стоит только там, где схемы нет; внутри пайплайна
есть роль — см. [Pipeline API](../analysis/pipeline.md).

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory

data = get_sample_data('tv_xauusd_1h')

fast = IndicatorFactory.create('custom', 'macd', fast_period=5, slow_period=26, signal_period=9)

print(fast.calculate(data).data.columns.tolist())
print(fast.get_output_roles())
# ['macd_5_26_9__line', 'macd_5_26_9__signal', 'macd_5_26_9__hist']
# {'line': 'macd_5_26_9__line', 'signal': 'macd_5_26_9__signal', 'hist': 'macd_5_26_9__hist'}
```

`get_output_roles()` возвращает **отображение** роли в имя колонки: имена меняются вместе
с параметрами, а роли — нет. На этом и держится адресация по роли.

## Внешние библиотеки

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

LibraryManager.load_all_libraries()
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)

print(rsi.calculate(data).data.columns.tolist())
print(sorted(LibraryManager.get_available_libraries()))
# ['RSI_14']
# ['pandas_ta', 'talib']
```

`talib` в списке стоит всегда — это перечень **известных** менеджеру библиотек, а не
установленных. Установлена ли она на самом деле, спрашивают отдельно:
`LibraryManager.check_library_availability('talib')`. TA-Lib требует системной библиотеки
и в зависимости пакета не входит, поэтому по умолчанию её индикаторов будет 0.

## Индикатор поверх готовых колонок

Когда значения пришли вместе с данными, считать заново незачем:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')
indicator = MACDPreloadedIndicator()

print(indicator.calculate(data).data.columns.tolist())
print(MACDPreloadedIndicator.get_default_columns())
# ['macd', 'signal']
# ['macd', 'signal']
```

Колонки не пересчитываются и не переименовываются — берутся как есть. Подробности —
[preloaded](preloaded.md).

## Свой индикатор

Достаточно унаследовать `BaseIndicator` и реализовать `calculate()`; регистрация в
фабрике делает его доступным наравне со встроенными. Пошагово — [базовые классы](base.md)
и [Extension Guide](../extension_guide.md).

## Где MACD

Модуль `bquant.indicators.macd` удалён в 0.0.5 вместе с `MACDZoneAnalyzer` — тонкой
обёрткой, делегировавшей в тот же пайплайн. Сам индикатор не тронут:

| Что нужно | Где взять |
|---|---|
| посчитать MACD | `IndicatorFactory.create('custom', 'macd', ...)` |
| прочитать готовый MACD из кадра | `MACDPreloadedIndicator` |
| проанализировать зоны MACD | `analyze_macd_zones(df)` или `analyze_zones(df).with_indicator('custom', 'macd', ...)` |
| функция расчёта без класса | `bquant.indicators.calculators.calculate_macd` |

Модели `ZoneInfo` и `ZoneAnalysisResult` больше не реэкспортируются отсюда — они живут в
`bquant.analysis.zones.models`.

## Дальше

| | |
|---|---|
| [Pipeline API](../analysis/pipeline.md) | как индикатор попадает в анализ зон |
| [Extension Guide](../extension_guide.md) | как добавить свой индикатор |
| [Данные](../data/README.md) | откуда брать кадр для расчёта |
