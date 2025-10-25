# Indicators - Технические индикаторы BQuant

## 📚 Обзор

Indicators модули содержат технические индикаторы для анализа финансовых данных с **Universal Architecture v2.1**. Система поддерживает все источники индикаторов (preloaded/custom/pandas_ta/talib) через `IndicatorFactory` и интегрируется с Universal Pipeline для анализа зон.

> **✅ v2.1 - Universal Indicator Support**
> 
> **IndicatorFactory Integration:** Все источники индикаторов поддерживаются универсально
> 
> **MACDZoneAnalyzer Status:** Deprecated wrapper с четким migration path
> 
> **Universal Pipeline:** Интеграция через `.with_indicator()` API

## 🗂️ Модули

### 🏗️ [bquant.indicators.base](base.md) - Базовые классы индикаторов
- **BaseIndicator** / **PreloadedIndicator** / **LibraryIndicator**
- **IndicatorResult** - результат расчёта индикатора
- **IndicatorConfig**/**IndicatorSource** - конфигурация/источник данных
- **IndicatorFactory** - единая фабрика индикаторов (`create()` для preloaded/custom/library)

### 📈 [bquant.indicators.macd](macd.md) - MACD индикатор и зоны (Deprecated)

⚠️ **DEPRECATED:** `MACDZoneAnalyzer` устарел в v2.1. Используйте Universal Pipeline.

**Legacy API (Deprecated):**
- **MACDZoneAnalyzer** - тонкий wrapper с @deprecated decorator
- **ZoneInfo**/**ZoneAnalysisResult** - модели результатов (перенесены в analysis.zones)
- Вспомогательные функции: `create_macd_analyzer()`, `analyze_macd_zones()`

**Migration Path:**
```python
# Старый способ (Deprecated)
from bquant.indicators.macd import MACDZoneAnalyzer
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# Новый способ (Universal Pipeline)
from bquant.analysis.zones import analyze_zones
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)
```

### 🔄 [bquant.indicators.preloaded](preloaded.md) - PRELOADED индикаторы
- **MACDPreloadedIndicator** - извлечение готовых MACD значений
- Работа с предобработанными данными
- Анализ трендов и пересечений

### 🏭 [bquant.indicators.factory](factory.md) - Universal Indicator Factory

**IndicatorFactory Integration:**
- **Universal Support:** все источники индикаторов (preloaded/custom/pandas_ta/talib)
- **Seamless Integration:** автоматическое использование в Universal Pipeline
- **No Hardcode:** ZERO hardcoded индикаторов, полная универсальность

**Core Methods:**
- **IndicatorFactory**: `register_indicator()`, `register_library_function()`, `create()`, `create_indicator()`, `list_indicators()`, `get_indicator_info()`
- **Universal Pipeline Integration:** автоматическое использование в `.with_indicator()`
- **Library Delegation:** делегирование в `LibraryManager` при работе с внешними библиотеками

### 🧭 [bquant.indicators.library_manager](library_manager.md) - Управление внешними библиотеками
- **LibraryManager**: `load_all_libraries()`, `get_library_info()`, `create_indicator()`
- Универсальный `pandas-ta` loader с автоматической регистрацией индикаторов
- Проверка доступности библиотек и логирование результата загрузки

## 🔍 Быстрый поиск

### По функциональности

#### Universal Pipeline Integration
- `analyze_zones().with_indicator()` - Универсальный анализ зон
- `IndicatorFactory.create()` - Создание индикаторов из всех источников
- `LibraryManager.create_indicator()` - Создание из внешних библиотек
- **Deprecated:** `MACDZoneAnalyzer.analyze_complete()` - используйте Universal Pipeline

#### PRELOADED индикаторы
- `MACDPreloadedIndicator.calculate()` - Извлечение готовых значений
- `MACDPreloadedIndicator.is_trending_up()` - Анализ восходящего тренда
- `MACDPreloadedIndicator.is_trending_down()` - Анализ нисходящего тренда
- `MACDPreloadedIndicator.get_crossovers()` - Определение пересечений
- `MACDPreloadedIndicator.get_statistics()` - Статистика по данным

#### Базовые индикаторы
- `BaseIndicator.calculate()` - Расчет индикатора
- `BaseIndicator.validate_data()` - Валидация данных
- `BaseIndicator.get_params()` - Получение параметров
- `BaseIndicator.set_params()` - Установка параметров
- `BaseIndicator.get_info()` - Информация об индикаторе (class method)
- `BaseIndicator.get_default_columns()` - Колонки по умолчанию (class method)

#### Фабрика индикаторов
- `IndicatorFactory.create()` - Создание индикатора с указанием источника (`preloaded`, `custom`, `pandas_ta`, `talib`)
- `IndicatorFactory.create_indicator()` - Устаревшая оболочка для совместимости
- `IndicatorFactory.register_indicator()` - Регистрация индикатора (preloaded/custom/library)
- `IndicatorFactory.list_indicators()` - Список индикаторов
- `IndicatorFactory.get_indicator_info()` - Информация об индикаторе

#### LibraryManager и внешние библиотеки
- `LibraryManager.load_all_libraries()` - Централизованная загрузка внешних библиотек
- `LibraryManager.get_library_info()` - Детальная информация о доступных индикаторах
- `LibraryManager.create_indicator()` - «Простой способ» получить индикатор из `pandas-ta` или `TA-Lib`

### По типу

#### 🏗️ Классы
- `BaseIndicator` - Базовый класс индикатора
- `PreloadedIndicator` - Базовый класс для PRELOADED индикаторов
- `MACDPreloadedIndicator` - PRELOADED MACD индикатор
- `MACDZoneAnalyzer` - Анализатор MACD
- `IndicatorFactory` - Фабрика индикаторов
- `IndicatorRegistry` - Реестр индикаторов

#### 🔧 Функции
- `calculate_macd()` - Расчет MACD
- `identify_zones()` - Идентификация зон
- `register_indicator()` - Регистрация индикатора
- `create_indicator()` - Создание индикатора

#### 📋 Типы данных
- `IndicatorResult` - Результат индикатора
- `IndicatorConfig` - Конфигурация индикатора
- `ZoneAnalysisResult` - Результат анализа зон
- `ZoneInfo` - Информация о зоне

## 💡 Примеры использования

### PRELOADED MACD индикатор

```python
from bquant.indicators.preloaded import MACDPreloadedIndicator
from bquant.data.samples import get_sample_data

# Загрузка данных с готовыми MACD значениями
data = get_sample_data('tv_xauusd_1h')

# Создание PRELOADED индикатора
macd_indicator = MACDPreloadedIndicator()

# Получение информации о классе
info = MACDPreloadedIndicator.get_info()
default_cols = MACDPreloadedIndicator.get_default_columns()

print(f"Indicator type: {info['type']}")
print(f"Default columns: {default_cols}")
print(f"Required fields: {info['required_fields']}")

# Извлечение данных
result = macd_indicator.calculate(data)
print(f"Extracted columns: {list(result.data.columns)}")

# Анализ трендов
trending_up = macd_indicator.is_trending_up(data, column='macd')
trending_down = macd_indicator.is_trending_down(data, column='macd')
print(f"MACD trending up: {trending_up}")
print(f"MACD trending down: {trending_down}")

# Анализ пересечений
crossovers = macd_indicator.get_crossovers(data)
print(f"Bullish crossovers: {crossovers['bullish_crossovers']}")
print(f"Bearish crossovers: {crossovers['bearish_crossovers']}")

# Статистика
stats = macd_indicator.get_statistics(data)
for col, col_stats in stats.items():
    print(f"{col}: min={col_stats['min']:.4f}, max={col_stats['max']:.4f}")
```

### PRELOADED индикатор с кастомными колонками

```python
from bquant.indicators.preloaded import MACDPreloadedIndicator

# Создание индикатора только для MACD линии
macd_only = MACDPreloadedIndicator(required_columns=['macd'])

# Создание индикатора для ключевых колонок
macd_full = MACDPreloadedIndicator(required_columns=['macd', 'signal'])

# Валидация данных
try:
    is_valid = macd_full.validate_data(data)
    print("Data validation passed")
except ValueError as e:
    print(f"Validation failed: {e}")

# Работа с доступными колонками
if macd_only.validate_data(data):
    result = macd_only.calculate(data)
    print(f"Single column result: {list(result.data.columns)}")
```

### Universal Pipeline с любыми индикаторами

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')
data['macd_hist'] = data['macd'] - data['signal']

# Universal Pipeline - MACD
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', divergence='classic')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

# Анализ результатов
print(f"Найдено зон: {len(result.zones)}")
print(f"Статистика: {result.statistics}")

# Анализ отдельных зон
for zone in result.zones:
    print(f"Зона {zone.type}: {zone.start_time} - {zone.end_time}")
    if zone.features:
        print(f"  Swings: {zone.features.get('num_swings', 0)}")
        print(f"  Divergence: {zone.features.get('has_classic_divergence', False)}")
```

### Universal Pipeline - RSI

```python
# RSI анализ с threshold detection
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .with_strategies(swing='pivot_points', volatility='combined')
    .analyze(clustering=True)
    .build()
)
```

### Universal Pipeline - Custom Indicator

```python
# Создаем собственный индикатор
data['MY_OSC'] = data['close'].diff(5) / data['close'].rolling(20).std()

# Universal Pipeline работает с любым индикатором
result = (
    analyze_zones(data)
    .detect_zones('zero_crossing', indicator_col='MY_OSC')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True)
    .build()
)
```

### Создание собственного индикатора

```python
from bquant.indicators.base import CustomIndicator, IndicatorResult
import pandas as pd


class SimpleMovingAverage(CustomIndicator):
    """Простая скользящая средняя"""

    def __init__(self, period=20):
        self.period = period
        super().__init__('sma_custom', {'period': period})

    def get_output_columns(self):
        return [f'sma_{self.period}']

    def get_description(self):
        return f"Simple Moving Average (period={self.period})"

    def calculate(self, data, **kwargs):
        if not self.validate_data(data):
            raise ValueError("Invalid data for SMA calculation")

        period = kwargs.get('period', self.period)
        sma = data['close'].rolling(window=period).mean()
        result_data = pd.DataFrame({f'sma_{period}': sma}, index=data.index)

        return IndicatorResult(
            name='sma_custom',
            data=result_data,
            config=self.config,
            metadata={'period': period}
        )

    def get_required_columns(self):
        return ['close']


# Использование собственного индикатора
sma = SimpleMovingAverage(period=20)
result = sma.calculate(data)
print(f"SMA values: {result.data.tail()}")
```

### Работа с фабрикой индикаторов

```python
from bquant.indicators.base import IndicatorFactory

# Регистрация индикатора (используем уникальное имя)
IndicatorFactory.register_indicator('sma_custom', SimpleMovingAverage)

# Создание индикатора через фабрику
sma = IndicatorFactory.create('custom', 'sma_custom', period=20)

# Получение списка доступных индикаторов
indicators = IndicatorFactory.list_indicators()
print(f"Available indicators: {indicators}")

# Получение информации об индикаторе
info = IndicatorFactory.get_indicator_info('sma_custom')
print(f"SMA info: {info}")
```

### Комбинированный анализ с Universal Pipeline

```python
from bquant.analysis.zones import analyze_zones
from bquant.indicators.preloaded import MACDPreloadedIndicator
from bquant.indicators.base import IndicatorFactory

# Регистрация пользовательского SMA
IndicatorFactory.register_indicator('sma_custom', SimpleMovingAverage)

# PRELOADED MACD анализ
macd_preloaded = MACDPreloadedIndicator()
macd_result = macd_preloaded.calculate(data)

# Universal Pipeline - MACD зоны анализ
macd_zones_result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# SMA анализ
sma = IndicatorFactory.create('custom', 'sma_custom', period=20)
sma_result = sma.calculate(data)

# Комбинированный анализ
combined_analysis = {
    'preloaded_macd_columns': list(macd_result.data.columns),
    'macd_zones': len(macd_zones_result.zones),
    'macd_statistics': macd_zones_result.statistics,
    'sma_current': float(sma_result.data.iloc[-1, 0]),
    'sma_trend': 'up' if sma_result.data.iloc[-1, 0] > sma_result.data.iloc[-2, 0] else 'down'
}

print(f"Combined analysis: {combined_analysis}")
```

### Анализ характеристик зон (Universal Pipeline)

```python
# Universal Pipeline с автоматическим извлечением характеристик
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', volatility='combined')
    .analyze(clustering=True)
    .build()
)

# Анализ характеристик зон
for zone in result.zones:
    if zone.features:
        features = zone.features
        print(f"Зона {zone.type}:")
        print(f"  Swings: {features.get('num_swings', 0)}")
        print(f"  Volatility regime: {features.get('volatility_regime', 'unknown')}")
        print(f"  Rally count: {features.get('rally_count', 0)}")
        print(f"  Drop count: {features.get('drop_count', 0)}")
```

### Настройка параметров индикаторов (Universal Pipeline)

```python
# Universal Pipeline с кастомными параметрами
result_custom = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=8, slow_period=21, signal_period=5)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

# Сравнение с дефолтными параметрами
result_default = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Custom parameters zones: {len(result_custom.zones)}")
print(f"Default parameters zones: {len(result_default.zones)}")
```

### Экспорт результатов анализа (Universal Pipeline)

```python
import json
from bquant.analysis.zones import analyze_zones

# Universal Pipeline анализ
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# Подготовка данных для экспорта
export_data = {
    'analysis_date': str(pd.Timestamp.now()),
    'data_info': {
        'symbol': 'XAUUSD',
        'timeframe': '1H',
        'records_count': len(data)
    },
    'universal_analysis': {
        'zones_count': len(result.zones),
        'statistics': result.statistics,
        'zones': [
            {
                'type': zone.type,
                'start': str(zone.start_time),
                'end': str(zone.end_time),
                'features': zone.features
            }
            for zone in result.zones
        ]
    }
}

# Экспорт в JSON
with open('universal_analysis.json', 'w') as f:
    json.dump(export_data, f, indent=2, default=str)

print("Universal analysis exported to universal_analysis.json")
```

## 🔗 Связанные разделы

- **[Core Modules](../core/README.md)** - Базовые модули
- **[Data Modules](../data/README.md)** - Модули данных
- **[Analysis](../analysis/README.md)** - Аналитические модули
- **[Visualization](../visualization/README.md)** - Модули визуализации

## 📖 Детальная документация

- **[Universal Pipeline](../analysis/pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Base Module](base.md)** - Подробная документация базовых классов
- **[MACD Module](macd.md)** - Документация MACD индикатора (Deprecated)
- **[PRELOADED Module](preloaded.md)** - Документация PRELOADED индикаторов
- **[Factory Module](factory.md)** - Документация Universal Indicator Factory

## 🚀 Руководство по расширению

### Создание нового индикатора

1. **Наследование от CustomIndicator**
2. **Реализация метода calculate()**
3. **Валидация данных**
4. **Регистрация в фабрике**

### Создание PRELOADED индикатора

1. **Наследование от PreloadedIndicator**
2. **Реализация get_default_columns() и get_info() class methods**
3. **Настройка гибких required_columns**
4. **Реализация аналитических методов (тренды, пересечения)**

### Лучшие практики

- Используйте NumPy для быстрых вычислений
- Валидируйте входные данные
- Документируйте параметры и результаты
- Тестируйте индикатор на различных данных
- Реализуйте class methods для информации и конфигурации по умолчанию

---

**Следующий раздел:** [Analysis](../analysis/README.md) 🔬
