# bquant.indicators.custom — встроенные индикаторы

Пять индикаторов, реализованных в самом пакете, без внешних библиотек. Все они
наследуют `CustomIndicator` из [base.md](base.md): объявляют **роли** выходных
колонок, а сами имена колонок выводят из своей идентичности, а не из строкового
литерала.

```python
from bquant.indicators import BollingerBands, ExponentialMovingAverage, RelativeStrengthIndex
from bquant.indicators.custom import SimpleMovingAverage, MACD
```

Первые три доступны и напрямую из `bquant.indicators`, остальные — из
`bquant.indicators.custom`.

## Состав

| Класс | Параметры по умолчанию | Идентичность | Колонки | Роли | Минимум записей | Прогрев |
|---|---|---|---|---|---|---|
| `SimpleMovingAverage` | `period=20` | `custom.sma_20` | `sma_20` | `value` | 20 | 19 |
| `ExponentialMovingAverage` | `period=20` | `custom.ema_20` | `ema_20` | `value` | 20 | 19 |
| `RelativeStrengthIndex` | `period=14` | `custom.rsi_14` | `rsi_14` | `value` | 15 | 1 |
| `MACD` | `fast_period=12, slow_period=26, signal_period=9` | `custom.macd_12_26_9` | `macd_12_26_9__line`, `…__signal`, `…__hist` | `line`, `signal`, `hist` | 35 | 25 / 33 / 33 |
| `BollingerBands` | `period=20, std_dev=2.0` | `custom.bbands_20_2` | `bbands_20_2__upper`, `…__middle`, `…__lower`, `…__width`, `…__percent` | `upper`, `middle`, `lower`, `width`, `percent` | 20 | 19 |

Имена колонок **зависят от параметров вызова**: `BollingerBands(period=50)` даст
`bbands_50_2__upper`, а не `bbands_20_2__upper`. Поэтому адресоваться к результату
надёжнее по роли, а не по строке — см. пример ниже.

## Прогрев

Последний столбец — сколько значений в **голове** ряда индикатор не публикует. Пока
наблюдений меньше, чем требует окно, среднего за период не существует, и вместо числа
стоит `NaN`. Длины считаются от параметров вызова: `ExponentialMovingAverage(period=50)`
закрывает 49 значений, `MACD(slow_period=10, signal_period=3)` — 9 у линии и 11 у
сигнала с гистограммой.

```python
from bquant.data.samples import get_sample_data
from bquant.indicators.custom import MACD

data = get_sample_data('tv_xauusd_1h')
frame = MACD().calculate(data).data

print({column: int(frame[column].isna().sum()) for column in frame.columns})
# {'macd_12_26_9__line': 25, 'macd_12_26_9__signal': 33, 'macd_12_26_9__hist': 33}
```

Это важно не само по себе, а ниже по течению: зона детектируется по смене знака
гистограммы, и до сентября 2026 непрогретая голова MACD давала на встроенном сэмпле
**шесть зон из восьмидесяти трёх**, ничем не отличимых от настоящих. Подробности —
`devref/gaps/core/g45_indicators_publish_an_unfilled_window_2026-09.md`.

Длины совпадают с pandas-ta по всем пяти индикаторам, так что смена источника голову
ряда не сдвигает.

## Расчёт

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import RelativeStrengthIndex

data = get_sample_data('tv_xauusd_1h')

rsi = RelativeStrengthIndex(period=14)
result = rsi.calculate(data)

print(result.data.columns.tolist())   # ['rsi_14']
print(rsi.get_indicator_id())         # custom.rsi_14
```

`calculate()` возвращает `IndicatorResult`; сам кадр — в `result.data`.

`get_indicator_id()` отдаёт не строку, а объект `IndicatorId`: он печатается как
`custom.rsi_14`, но в f-строку с форматом (`f"{ident:20}"`) не встанет — для этого
нужен явный `str()`. Имя колонки по роли берётся у него методом `.column('line')`.

### Адресация по роли, а не по имени колонки

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import BollingerBands

data = get_sample_data('tv_xauusd_1h')

bb = BollingerBands(period=50, std_dev=2.5)
result = bb.calculate(data)

roles = bb.get_output_roles()          # {'upper': 'bbands_50_2.5__upper', ...}
upper = result.data[roles['upper']]

print(len(upper))
```

Так код переживает смену параметров: меняется имя колонки, роль остаётся.

## Кэширование

У каждого индикатора есть `calculate_with_cache()` с той же сигнатурой, что и
`calculate()`. Про уровни кэша и его инвалидацию — [caching.md](../../user_guide/caching.md).

## Регистрация в фабрике

```python
from bquant.indicators.custom import register_builtin_indicators

count = register_builtin_indicators()
print(count)   # 5
```

Регистрирует все пять в `IndicatorFactory` и возвращает их число. **Вызывать
вручную обычно не нужно:** пакет делает это сам при импорте `bquant.indicators`,
и после этого работает обращение по имени через фабрику:

```python
from bquant.indicators import IndicatorFactory
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
indicator = IndicatorFactory.create('custom', 'rsi', period=21)
print(indicator.calculate(data).data.columns.tolist())   # ['rsi_21']
```

Функция пригождается, если фабрику чистили или собирали заново в своём процессе.

## Отличие от одноимённых индикаторов внешних библиотек

`pandas-ta` и TA-Lib предоставляют индикаторы с теми же названиями. Это **разные
реализации**, и это by design: источник `custom` существует именно ради собственных
формул.

Расходятся они не «на малых окнах», а **в голове ряда**, и по конкретной причине:
`MACD` и `RelativeStrengthIndex` сглаживают через `ewm()` с дефолтным `adjust=True`,
тогда как pandas-ta берёт рекурсивную форму. Замер на `tv_xauusd_1h`: у RSI расхождение
доходит до 54 пунктов на втором баре, к сотому падает до 0.05, к двухсотому — до нуля.
После прогрева реализации совпадают.

Решение оставить `adjust=True` принято владельцем и задокументировано
(`devref/gaps/issue_indicator_consistency.md`); внутри одного прогона используется одна
реализация, поэтому статистика по зонам самосогласована.

Одна оговорка к слову «самосогласована», чтобы она не читалась шире, чем верна:
`ExponentialMovingAverage` сглаживает с `adjust=False`, а `MACD` внутри себя — с
`adjust=True`. Значит `EMA(12) − EMA(26)`, посчитанные этим пакетом, **не равны** его же
линии MACD: на сэмпле расхождение доходит до 6.3 в голове и сходится к нулю примерно к
сотому бару. Считать одно через другое нельзя; каждый индикатор согласован сам с собой.

Выбор источника — параметр фабрики:

```python
from bquant.indicators import IndicatorFactory

builtin = IndicatorFactory.create('custom', 'rsi', period=14)
external = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
```

## См. также

- [base.md](base.md) — базовые классы, роли, контракт имён колонок
- [factory.md](factory.md) — `IndicatorFactory` и источники индикаторов
- [library_manager.md](library_manager.md) — индикаторы из `pandas-ta` и TA-Lib
- [preloaded.md](preloaded.md) — индикаторы поверх уже посчитанных колонок
