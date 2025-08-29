# bquant.indicators.base — База индикаторов

## Обзор

Архитектурные классы и типы для построения индикаторов.

## Классы

- `IndicatorSource`: перечисление источников данных индикатора (DataFrame, внешние либы и др.)
- `IndicatorConfig`: конфигурация индикатора (параметры, минимальные требования и т.п.)
- `IndicatorResult`
  - Поля: `name`, `data: DataFrame`, `config`, `metadata`
- `BaseIndicator`
  - Методы: `validate_data(data)`, `calculate(data, **kwargs) -> IndicatorResult`
- `PreloadedIndicator(BaseIndicator)` — индикатор с реализацией внутри проекта
- `LibraryIndicator(BaseIndicator)` — обёртка над функциями внешних библиотек
- `IndicatorFactory`
  - Регистрация: `register_indicator(name, cls)`, `register_library_function(name, func)`
  - Создание: `create_indicator(name, **kwargs) -> BaseIndicator`
  - Справка: `list_indicators() -> Dict[str,str]`, `get_indicator_info(name) -> Optional[Dict]`

## Пример: свой индикатор

```python
from bquant.indicators.base import BaseIndicator, IndicatorResult
import pandas as pd

class SMA(BaseIndicator):
    def __init__(self, period=20):
        super().__init__('sma', {'period': period})

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        period = kwargs.get('period', self.config['period'])
        values = data['close'].rolling(window=period).mean()
        return IndicatorResult('sma', values.to_frame(f'sma_{period}'), self.config)
```

## Пример: фабрика

```python
from bquant.indicators.base import IndicatorFactory

IndicatorFactory.register_indicator('SMA', SMA)
ind = IndicatorFactory.create_indicator('SMA', period=10)
res = ind.calculate(df)
```

## См. также

- [MACD и зоны](macd.md)
- [Фабрика и библиотека](factory.md)
