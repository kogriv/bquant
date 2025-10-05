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
  - Class methods: `get_info() -> Dict`, `get_default_columns() -> List[str]`
- `PreloadedIndicator(BaseIndicator)` — индикатор с реализацией внутри проекта
  - Работает с уже готовыми данными
  - Извлекает значения без пересчета
  - Поддерживает гибкую настройку колонок
- `LibraryIndicator(BaseIndicator)` — обёртка над функциями внешних библиотек (pandas-ta, TA-Lib и др.)
- `IndicatorFactory`
  - Регистрация: `register_indicator(name, cls)`, `register_library_function(name, func)`
  - Создание: `create(source, indicator, **params) -> BaseIndicator`
  - Совместимость: `create_indicator(name, **kwargs)` (устаревший интерфейс)
  - Справка: `list_indicators() -> Dict[str,str]`, `get_indicator_info(name) -> Optional[Dict]`

## Class Methods

### `get_info() -> Dict[str, Any]`
Возвращает информацию об индикаторе в виде словаря. Должен быть реализован в каждом классе индикатора.

**Возвращает:**
- `name`: название индикатора
- `type`: тип индикатора (PRELOADED, LIBRARY, CUSTOM)
- `description`: описание функциональности
- `default_columns`: колонки по умолчанию
- `required_fields`: описание обязательных полей
- `optional_fields`: описание опциональных полей
- `usage_examples`: примеры использования

### `get_default_columns() -> List[str]`
Возвращает список колонок по умолчанию для индикатора. Должен быть реализован в каждом классе индикатора.

## Пример: свой индикатор

```python
from bquant.indicators.base import BaseIndicator, IndicatorResult
import pandas as pd

class SMA(BaseIndicator):
    def __init__(self, period=20):
        super().__init__('sma', {'period': period})

    @classmethod
    def get_default_columns(cls) -> List[str]:
        return ['close']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        return {
            'name': 'SMA',
            'type': 'CUSTOM',
            'description': 'Simple Moving Average indicator',
            'default_columns': cls.get_default_columns(),
            'required_fields': {'close': 'Close price values'},
            'usage_examples': {'basic': 'SMA(period=20)'}
        }

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        period = kwargs.get('period', self.config['period'])
        values = data['close'].rolling(window=period).mean()
        return IndicatorResult('sma', values.to_frame(f'sma_{period}'), self.config)
```

## Пример: PRELOADED индикатор

```python
from bquant.indicators.base import PreloadedIndicator, IndicatorResult
import pandas as pd

class RSI(PreloadedIndicator):
    def __init__(self, required_columns=None):
        if required_columns is None:
            required_columns = self.get_default_columns()
        
        self._required_columns = required_columns.copy()
        super().__init__('rsi', {'required_columns': required_columns})
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        return ['rsi']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        return {
            'name': 'RSI',
            'type': 'PRELOADED',
            'description': 'Relative Strength Index from pre-calculated data',
            'default_columns': cls.get_default_columns(),
            'required_fields': {'rsi': 'RSI values (0-100)'}
        }
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        result_data = data[self._required_columns].copy()
        return IndicatorResult('rsi', result_data, self.config)
```

## Пример: фабрика

```python
from bquant.indicators.base import IndicatorFactory

# Регистрация пользовательского индикатора (при необходимости)
IndicatorFactory.register_indicator('custom_sma', SMA)

# Создание PRELOADED/CUSTOM индикаторов через современный интерфейс
sma = IndicatorFactory.create('custom', 'custom_sma', period=10)
result = sma.calculate(df)
```

## LibraryManager и динамические индикаторы

`LibraryIndicator` используется для обёрток внешних библиотек. После рефакторинга `LibraryManager`
обнаружение и регистрация индикаторов `pandas-ta` выполняются автоматически: достаточно вызвать загрузку библиотеки,
и все совместимые функции станут доступны через `IndicatorFactory.create()` и `LibraryManager.create_indicator()`.

```python
from bquant.indicators import LibraryManager, IndicatorFactory

# Загружаем все доступные библиотеки (pandas-ta, TA-Lib)
load_results = LibraryManager.load_all_libraries()
print(load_results['pandas_ta'])  # Количество зарегистрированных функций

# Создаём индикатор pandas-ta без ручной регистрации
macd = IndicatorFactory.create('pandas_ta', 'macd', fast=12, slow=26, signal=9)

# Альтернатива: «простой способ» напрямую через менеджер
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)

macd_result = macd.calculate(df)
rsi_result = rsi.calculate(df)
```

## См. также

- [MACD и зоны](macd.md)
- [PRELOADED индикаторы](preloaded.md)
- [Фабрика и библиотека](factory.md)
