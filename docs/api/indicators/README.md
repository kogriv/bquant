# Indicators - Технические индикаторы BQuant

## 📚 Обзор

Indicators модули содержат технические индикаторы для анализа финансовых данных, включая MACD с анализом зон и расширяемую архитектуру для создания собственных индикаторов.

## 🗂️ Модули

### 🏗️ [bquant.indicators.base](base.md) - Базовые классы индикаторов
- **BaseIndicator** / **PreloadedIndicator** / **LibraryIndicator**
- **IndicatorResult** - результат расчёта индикатора
- **IndicatorConfig**/**IndicatorSource** - конфигурация/источник данных
- **IndicatorFactory** - фабрика индикаторов

### 📈 [bquant.indicators.macd](macd.md) - MACD индикатор и зоны
- **MACDZoneAnalyzer** - анализ зон MACD
- **ZoneInfo**/**ZoneAnalysisResult** - модели результатов
- Вспомогательные функции: `create_macd_analyzer()`, `analyze_macd_zones()`

### 🔄 [bquant.indicators.preloaded](preloaded.md) - PRELOADED индикаторы
- **MACDPreloadedIndicator** - извлечение готовых MACD значений
- Работа с предобработанными данными
- Анализ трендов и пересечений

### 🏭 [bquant.indicators.factory](factory.md) - Фабрика и библиотека индикаторов
- **IndicatorFactory**: `register_indicator()`, `register_library_function()`, `create_indicator()`, `list_indicators()`, `get_indicator_info()`
- Библиотека: `register_builtin_indicators()`, `get_builtin_indicators()`, `create_indicator()`

## 🔍 Быстрый поиск

### По функциональности

#### MACD анализ
- `MACDZoneAnalyzer.analyze_complete()` - Полный анализ MACD
- `calculate_macd()` - Расчет MACD значений
- `identify_zones()` - Идентификация зон
- `analyze_zone_features()` - Анализ характеристик зон

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
- `IndicatorFactory.create_indicator()` - Создание индикатора
- `IndicatorFactory.register_indicator()` - Регистрация индикатора
- `IndicatorFactory.list_indicators()` - Список индикаторов
- `IndicatorFactory.get_indicator_info()` - Информация об индикаторе

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

# Создание индикатора для всех доступных колонок
macd_full = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])

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

### MACD анализ с зонами

```python
from bquant.indicators import MACDZoneAnalyzer
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Создание анализатора MACD
analyzer = MACDZoneAnalyzer(
    macd_params={'fast': 12, 'slow': 26, 'signal': 9},
    zone_params={'min_duration': 2, 'min_amplitude': 0.001}
)

# Полный анализ
result = analyzer.analyze_complete(data)

# Анализ результатов
print(f"Найдено зон: {len(result.zones)}")
print(f"Статистика: {result.statistics}")

# Анализ отдельных зон
for zone in result.zones:
    print(f"Зона {zone.type}: {zone.start_time} - {zone.end_time}")
    print(f"  Длительность (bars): {zone.duration}")
    if zone.features:
        print(f"  MACD амплитуда: {zone.features['macd_amplitude']:.4f}")
```

### Создание собственного индикатора

```python
from bquant.indicators.base import BaseIndicator, IndicatorResult
import pandas as pd
import numpy as np

class SimpleMovingAverage(BaseIndicator):
    """Простая скользящая средняя"""
    
    def __init__(self, period=20):
        super().__init__('SMA', {'period': period})
    
    def calculate(self, data):
        """Расчет SMA"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for SMA calculation")
        
        period = self.params['period']
        sma = data['close'].rolling(window=period).mean()
        
        return IndicatorResult(
            indicator_name='SMA',
            values=sma,
            params=self.params,
            metadata={'period': period}
        )
    
    def validate_data(self, data):
        """Валидация данных"""
        required_columns = ['close']
        return all(col in data.columns for col in required_columns)

# Использование собственного индикатора
sma = SimpleMovingAverage(period=20)
result = sma.calculate(data)
print(f"SMA values: {result.values.tail()}")
```

### Работа с фабрикой индикаторов

```python
from bquant.indicators.factory import IndicatorFactory

# Создание фабрики
factory = IndicatorFactory()

# Регистрация индикатора
factory.register_indicator(SimpleMovingAverage)

# Создание индикатора через фабрику
sma = factory.create('SMA', period=20)

# Получение списка доступных индикаторов
indicators = factory.list_indicators()
print(f"Available indicators: {indicators}")

# Получение информации об индикаторе
info = factory.get_info('SMA')
print(f"SMA info: {info}")
```

### Комбинированный анализ

```python
from bquant.indicators import MACDZoneAnalyzer
from bquant.indicators.preloaded import MACDPreloadedIndicator
from bquant.indicators.factory import IndicatorFactory

# Создание нескольких индикаторов
factory = IndicatorFactory()
factory.register_indicator(SimpleMovingAverage)

# PRELOADED MACD анализ
macd_preloaded = MACDPreloadedIndicator()
macd_result = macd_preloaded.calculate(data)

# MACD зоны анализ
macd_analyzer = MACDZoneAnalyzer()
macd_zones_result = macd_analyzer.analyze_complete(data)

# SMA анализ
sma = factory.create('SMA', period=20)
sma_result = sma.calculate(data)

# Комбинированный анализ
combined_analysis = {
    'preloaded_macd_columns': list(macd_result.data.columns),
    'macd_zones': len(macd_zones_result.zones),
    'macd_statistics': macd_zones_result.statistics,
    'sma_current': sma_result.values.iloc[-1],
    'sma_trend': 'up' if sma_result.values.iloc[-1] > sma_result.values.iloc[-2] else 'down'
}

print(f"Combined analysis: {combined_analysis}")
```

### Анализ характеристик зон

```python
from bquant.indicators import MACDZoneAnalyzer

# Создание анализатора
analyzer = MACDZoneAnalyzer()

# Полный анализ с характеристиками зон
result = analyzer.analyze_complete(data)

# Анализ характеристик зон
for zone in result.zones:
    if zone.features:
        features = zone.features
        print(f"Зона {zone.zone_type}:")
        print(f"  Средняя волатильность: {features.avg_volatility:.4f}")
        print(f"  Максимальная амплитуда: {features.max_amplitude:.4f}")
        print(f"  Количество пиков: {features.peak_count}")
        print(f"  Тренд: {features.trend}")
```

### Настройка параметров индикаторов

```python
from bquant.indicators import MACDZoneAnalyzer

# Создание анализатора с кастомными параметрами
analyzer = MACDZoneAnalyzer(
    macd_params={
        'fast': 8,      # Быстрая EMA
        'slow': 21,     # Медленная EMA
        'signal': 5     # Сигнальная линия
    },
    zone_params={
        'min_duration': 3,      # Минимальная длительность зоны
        'min_amplitude': 0.002, # Минимальная амплитуда
        'smooth_factor': 0.1    # Фактор сглаживания
    }
)

# Анализ с кастомными параметрами
result = analyzer.analyze_complete(data)

# Сравнение с дефолтными параметрами
default_analyzer = MACDZoneAnalyzer()
default_result = default_analyzer.analyze_complete(data)

print(f"Custom parameters zones: {len(result.zones)}")
print(f"Default parameters zones: {len(default_result.zones)}")
```

### Экспорт результатов анализа

```python
import json
from bquant.indicators import MACDZoneAnalyzer

# Анализ
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# Подготовка данных для экспорта
export_data = {
    'analysis_date': str(pd.Timestamp.now()),
    'data_info': {
        'symbol': 'XAUUSD',
        'timeframe': '1H',
        'records_count': len(data)
    },
    'macd_analysis': {
        'zones_count': len(result.zones),
        'statistics': result.statistics,
        'zones': [
            {
                'type': zone.zone_type,
                'start': str(zone.start_date),
                'end': str(zone.end_date),
                'duration': zone.duration,
                'amplitude': zone.amplitude
            }
            for zone in result.zones
        ]
    }
}

# Экспорт в JSON
with open('macd_analysis.json', 'w') as f:
    json.dump(export_data, f, indent=2, default=str)

print("Analysis exported to macd_analysis.json")
```

## 🔗 Связанные разделы

- **[Core Modules](../core/README.md)** - Базовые модули
- **[Data Modules](../data/README.md)** - Модули данных
- **[Analysis](../analysis/README.md)** - Аналитические модули
- **[Visualization](../visualization/README.md)** - Модули визуализации

## 📖 Детальная документация

- **[Base Module](base.md)** - Подробная документация базовых классов
- **[MACD Module](macd.md)** - Документация MACD индикатора
- **[PRELOADED Module](preloaded.md)** - Документация PRELOADED индикаторов
- **[Factory Module](factory.md)** - Документация фабрики индикаторов

## 🚀 Руководство по расширению

### Создание нового индикатора

1. **Наследование от BaseIndicator**
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
