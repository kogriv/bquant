# `bquant.indicators.base` — база индикаторов

Классы, на которых стоят все индикаторы пакета, и фабрика, которая их создаёт.

## Что здесь есть

| Имя | Что это |
|---|---|
| `BaseIndicator` | базовый класс: `calculate()`, `validate_data()`, описание входов и выходов |
| `PreloadedIndicator` | база для индикаторов, читающих уже посчитанные колонки |
| `LibraryIndicator` | обёртка над функцией внешней библиотеки |
| `IndicatorResult` | результат расчёта: `name`, `data`, `config`, `metadata` |
| `IndicatorConfig` | описание посчитанного индикатора: `name`, `parameters`, `source`, `columns`, `description` |
| `IndicatorSource` | перечисление: `PRELOADED`, `CUSTOM`, `LIBRARY` |
| `IndicatorFactory` | единая фабрика — [отдельная страница](factory.md) |

`IndicatorConfig` **не путать** с `IndicatorSpec` из `bquant.analysis.zones`: первый
описывает *посчитанный* индикатор, второй — заявку на расчёт. До 2026-08-24 оба звались
одинаково.

## Методы `BaseIndicator`

```python
from bquant.indicators.base import BaseIndicator

print(sorted(m for m in dir(BaseIndicator) if not m.startswith('_')))
# ['calculate', 'get_default_columns', 'get_indicator_id', 'get_info', 'get_min_records',
#  'get_output_columns', 'get_output_roles', 'get_required_columns', 'validate_data']
```

| Метод | Отвечает на вопрос |
|---|---|
| `calculate(data, **kwargs)` | посчитать; возвращает `IndicatorResult` |
| `validate_data(data, **params)` | годится ли кадр: колонки, строки **по параметрам вызова**, числовой dtype, нет бесконечностей. Возвращает `True` или поднимает `DataValidationError` — до 2026-09-05 возвращал `False`, которого никто не читал, и расчёт шёл дальше (G58) |
| `get_required_columns()` | что нужно на входе |
| `get_output_columns()` | какие колонки появятся |
| `get_output_roles()` | **роль → имя колонки**; роли не меняются от параметров, имена меняются |
| `get_min_records(**params)` | сколько баров нужно минимум — для параметров вызова (`period=100` → сто), не конструктора |
| `get_indicator_id()` | идентичность: источник, имя, параметры |
| `get_info()` | описание класса словарём (`name`, `type`, `description`, …) |
| `get_default_columns()` | колонки по умолчанию |

## Свой индикатор

Достаточно унаследовать `BaseIndicator` и реализовать `calculate()`:

```python
from typing import List

import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.indicators.base import BaseIndicator, IndicatorResult


class SimpleMA(BaseIndicator):
    def __init__(self, period: int = 20):
        super().__init__('simple_ma', {'period': period})

    @classmethod
    def get_default_columns(cls) -> List[str]:
        return ['close']

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        period = kwargs.get('period', self.config['period'])
        values = data['close'].rolling(window=period).mean()
        return IndicatorResult('simple_ma', values.to_frame(f'simple_ma_{period}'), self.config)


result = SimpleMA(period=10).calculate(get_sample_data('tv_xauusd_1h'))

print(result.data.columns.tolist())
print(round(result.data.iloc[-1, 0], 2))
# ['simple_ma_10']
# 3350.49
```

Конструктор принимает и обычный словарь параметров, и `IndicatorConfig` — в примере выше
словарь, поэтому `self.config['period']` читается как из словаря.

## Индикатор поверх готовых колонок

`PreloadedIndicator` не считает, а извлекает: проверяет, что нужные колонки есть, и
отдаёт их как есть.

```python
from typing import List

import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.indicators.base import IndicatorResult, PreloadedIndicator


class PreloadedRSI(PreloadedIndicator):
    def __init__(self, required_columns=None):
        required_columns = list(required_columns or self.get_default_columns())
        self._required_columns = required_columns
        super().__init__('preloaded_rsi', {'required_columns': required_columns})

    @classmethod
    def get_default_columns(cls) -> List[str]:
        return ['rsi']

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        return IndicatorResult('preloaded_rsi', data[self._required_columns].copy(), self.config)


data = get_sample_data('tv_xauusd_1h')
extracted = PreloadedRSI().calculate(data)

print(extracted.data.columns.tolist())
print(round(extracted.data['rsi'].iloc[-1], 2))
# ['rsi']
# 42.9
```

Во встроенном наборе колонка `rsi` уже есть — она пришла из источника данных, а не из
нашего расчёта. Готовый такой индикатор для MACD — [preloaded](preloaded.md).

## Регистрация в фабрике

Чтобы имя принимала фабрика, наследовать нужно **`CustomIndicator`**, а не
`BaseIndicator`: `create('custom', ...)` проверяет именно это. Контракт у него шире —
обязательны `get_description()`, `get_output_columns()` и `get_default_columns()`, а
параметры лежат в `self.config.parameters`.

```python
from typing import List

import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.indicators.base import CustomIndicator, IndicatorFactory, IndicatorResult


class RangeIndicator(CustomIndicator):
    def __init__(self, period: int = 14):
        super().__init__('range', {'period': period})

    @classmethod
    def get_default_columns(cls) -> List[str]:
        return ['high', 'low']

    @classmethod
    def get_description(cls) -> str:
        return 'Average high-low range'

    def get_output_columns(self) -> List[str]:
        return ['range']

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        period = kwargs.get('period', self.config.parameters['period'])
        values = (data['high'] - data['low']).rolling(window=period).mean()
        return IndicatorResult('range', values.to_frame('range'), self.config)


IndicatorFactory.register_indicator('range', RangeIndicator)

indicator = IndicatorFactory.create('custom', 'range', period=10)

print(round(indicator.calculate(get_sample_data('tv_xauusd_1h')).data.iloc[-1, 0], 3))
print(IndicatorFactory.list_indicators()['range'])
# 6.892
# custom
```

После регистрации имя доступно так же, как встроенные: его видит
`IndicatorFactory.list_indicators()` и принимает `.with_indicator('custom', 'range')` в
пайплайне зон.

Наследование `BaseIndicator` — как в примере выше — годится для собственного кода, но в
фабрику такой класс не пройдёт: она отвергнет его и сообщит, что индикатор не CUSTOM.

## Внешние библиотеки

Регистрировать функции `pandas-ta` вручную не нужно — загрузка делает это сама:

```python
from bquant.indicators import IndicatorFactory, LibraryManager

print(LibraryManager.load_all_libraries())
# {'pandas_ta': 158, 'talib': 0}

macd = IndicatorFactory.create('pandas_ta', 'macd', fast=12, slow=26, signal=9)
print(type(macd).__name__)
# PandasTAMacd
```

Ноль у `talib` означает, что библиотека не установлена: она требует системной части и в
зависимости пакета не входит.

## Дальше

| | |
|---|---|
| [Фабрика](factory.md) | все способы создать индикатор |
| [Встроенные](custom.md) | как устроены SMA, EMA, RSI, MACD, Bollinger |
| [Preloaded](preloaded.md) | индикатор поверх готовых колонок |
| [Extension Guide](../extension_guide.md) | свой индикатор целиком, с ролями и схемой |
