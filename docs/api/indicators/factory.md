# Фабрика и библиотека индикаторов

## IndicatorFactory (bquant.indicators.base)

Методы (классовые):
- `register_indicator(name, indicator_class)` — регистрирует класс индикатора
- `register_library_function(name, func)` — регистрирует функцию из внешней библиотеки
- `create_indicator(name, **kwargs) -> BaseIndicator` — создаёт индикатор
- `list_indicators() -> Dict[str, str]` — список доступных индикаторов (preloaded|library)
- `get_indicator_info(name) -> Optional[Dict]` — информация об индикаторе

Пример:
```python
from bquant.indicators.base import IndicatorFactory

IndicatorFactory.register_indicator('SMA', SimpleMovingAverage)
ind = IndicatorFactory.create_indicator('SMA', period=10)
res = ind.calculate(df)
```

## Библиотека встроенных индикаторов (bquant.indicators.library)

Экспортируемые:
- `SimpleMovingAverage`, `ExponentialMovingAverage`, `RelativeStrengthIndex`, `MACD`, `BollingerBands`
- Регистрация/получение: `register_builtin_indicators()`, `get_builtin_indicators()`, `create_indicator(name, **params)`

Пример:
```python
from bquant.indicators.library import register_builtin_indicators, create_indicator

register_builtin_indicators()
sma = create_indicator('sma', period=20)
res = sma.calculate(df)
```

## Утилиты расчёта (bquant.indicators.calculators)

- `calculate_indicator(name, df, **kwargs)`
- `calculate_macd(df, fast=12, slow=26, signal=9)`
- `calculate_rsi(df, period=14)`
- `calculate_bollinger_bands(df, period=20, std_dev=2)`
- `calculate_moving_averages(df, periods=(20,50,200))`
- `create_indicator_suite(df, indicators: Dict[str, Dict])`
- `get_available_indicators()`
- `validate_indicator_data(df)`

## Загрузчики внешних библиотек (bquant.indicators.loaders)

- `load_pandas_ta()`, `load_talib()` — загрузка библиотек
- `PandasTALoader`, `TALibLoader`, `LibraryManager`
- `load_all_indicators()` — регистрация доступных функций в фабрике

