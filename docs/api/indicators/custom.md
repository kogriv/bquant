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

| Класс | Параметры по умолчанию | Идентичность | Колонки | Роли | Минимум записей |
|---|---|---|---|---|---|
| `SimpleMovingAverage` | `period=20` | `custom.sma_20` | `sma_20` | `value` | 20 |
| `ExponentialMovingAverage` | `period=20` | `custom.ema_20` | `ema_20` | `value` | 20 |
| `RelativeStrengthIndex` | `period=14` | `custom.rsi_14` | `rsi_14` | `value` | 15 |
| `MACD` | `fast_period=12, slow_period=26, signal_period=9` | `custom.macd_12_26_9` | `macd_12_26_9__line`, `…__signal`, `…__hist` | `line`, `signal`, `hist` | 35 |
| `BollingerBands` | `period=20, std_dev=2.0` | `custom.bbands_20_2` | `bbands_20_2__upper`, `…__middle`, `…__lower`, `…__width`, `…__percent` | `upper`, `middle`, `lower`, `width`, `percent` | 20 |

Имена колонок **зависят от параметров вызова**: `BollingerBands(period=50)` даст
`bbands_50_2__upper`, а не `bbands_20_2__upper`. Поэтому адресоваться к результату
надёжнее по роли, а не по строке — см. пример ниже.

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
реализации**, и числа у них могут расходиться на малых окнах: встроенный расчёт
использует `ewm()` без `adjust=False`. Расхождение задокументировано
(`devref/gaps/issue_indicator_consistency.md`) и признано некритичным, потому что
в одном прогоне используется одна реализация — самосогласованность сохраняется.

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
