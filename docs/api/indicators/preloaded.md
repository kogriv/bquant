# bquant.indicators.preloaded — PRELOADED индикаторы

## Обзор

PRELOADED индикаторы работают с уже готовыми данными, извлекая значения без пересчета. Предназначены для работы с предобработанными данными, где технические индикаторы уже были рассчитаны.

## Особенности

- **Извлечение готовых значений** - нет необходимости в пересчете
- **Гибкая настройка колонок** - можно указать, какие поля извлекать
- **Валидация данных** - проверка наличия необходимых колонок
- **Аналитические методы** - тренды, пересечения, статистика
- **Class methods** - информация о классе без создания объекта

## Классы

### `MACDPreloadedIndicator`

PRELOADED индикатор для работы с готовыми MACD данными.

#### Параметры инициализации

- `name: str = "macd_preloaded"` - название индикатора
- `required_columns: Optional[List[str]] = None` - список колонок для извлечения

#### Class Methods

##### `get_default_columns() -> List[str]`
Возвращает колонки по умолчанию: `['macd', 'signal']`

##### `get_info() -> Dict[str, Any]`
Возвращает подробную информацию об индикаторе:

```python
{
    'name': 'MACDPreloadedIndicator',
    'type': 'PRELOADED',
    'description': 'MACD indicator for working with pre-calculated data',
    'default_columns': ['macd', 'signal'],
    'required_fields': {
        'macd': 'MACD line values (numeric)',
        'signal': 'Signal line values (numeric)'
    },
    'optional_fields': {
        'histogram': 'MACD histogram values (numeric)',
        'rsi': 'RSI values if available (numeric)'
    },
    'original_calculation_params': {
        'fast': 12,
        'slow': 26,
        'smoothing': 9,
        'price': 'close'
    },
    'usage_examples': {
        'basic': "MACDPreloadedIndicator()",
        'custom_columns': "MACDPreloadedIndicator(required_columns=['macd', 'signal'])",
        'single_column': "MACDPreloadedIndicator(required_columns=['macd'])"
    },
    'data_requirements': {
        'min_records': 1,
        'column_types': 'numeric',
        'source': 'preloaded_data'
    },
    'available_methods': [
        'calculate()',
        'validate_data()',
        'get_statistics()',
        'is_trending_up()',
        'is_trending_down()',
        'get_crossovers()'
    ]
}
```

#### Instance Methods

##### `calculate(data: pd.DataFrame, **kwargs) -> IndicatorResult`
Извлекает готовые значения MACD из данных.

**Параметры:**
- `data`: DataFrame с данными, содержащий необходимые колонки
- `**kwargs`: дополнительные параметры (не используются)

**Возвращает:**
- `IndicatorResult` с данными MACD и метаданными

**Особенности:**
- Автоматическая валидация данных
- Проверка на NaN значения
- Детальные метаданные о процессе извлечения

##### `validate_data(data: pd.DataFrame) -> bool`
Валидирует данные для PRELOADED MACD индикатора.

**Проверки:**
- Наличие необходимых колонок
- Минимальное количество записей (1)
- Числовой тип данных для всех колонок

##### `get_statistics(data: pd.DataFrame) -> Dict[str, Any]`
Возвращает статистику по PRELOADED MACD данным.

**Статистика для каждой колонки:**
- `count`: количество значений
- `min`, `max`: минимальное и максимальное значения
- `mean`, `std`, `median`: среднее, стандартное отклонение, медиана
- `nan_count`: количество NaN значений

##### `is_trending_up(data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool`
Проверяет, растет ли указанная колонка (тренд вверх).

**Логика:**
1. Извлекает данные через `calculate()`
2. Берет последние 2 значения колонки
3. Сравнивает: последнее > предыдущее И последнее > threshold

**Параметры:**
- `column`: колонка для анализа (по умолчанию первая из required_columns)
- `threshold`: порог для определения роста (по умолчанию 0.0)

##### `is_trending_down(data: pd.DataFrame, column: str = None, threshold: float = 0.0) -> bool`
Проверяет, падает ли указанная колонка (тренд вниз).

**Логика:**
1. Извлекает данные через `calculate()`
2. Берет последние 2 значения колонки
3. Сравнивает: последнее < предыдущее И последнее < threshold

**Параметры:**
- `column`: колонка для анализа (по умолчанию первая из required_columns)
- `threshold`: порог для определения падения (по умолчанию 0.0)

##### `get_crossovers(data: pd.DataFrame, column1: str = None, column2: str = None) -> Dict[str, Any]`
Определяет пересечения между двумя колонками.

**Логика:**
1. Извлекает данные через `calculate()`
2. Определяет колонки для анализа (по умолчанию первые две из required_columns)
3. Выявляет моменты пересечения:
   - **Bullish**: col1 > col2 И col1_prev ≤ col2_prev
   - **Bearish**: col1 < col2 И col1_prev ≥ col2_prev

**Возвращает:**
```python
{
    'column1': 'название первой колонки',
    'column2': 'название второй колонки',
    'bullish_crossovers': количество бычьих пересечений,
    'bearish_crossovers': количество медвежьих пересечений,
    'bullish_indices': индексы бычьих пересечений,
    'bearish_indices': индексы медвежьих пересечений
}
```

## Примеры использования

### Базовое использование

```python
from bquant.indicators.preloaded import MACDPreloadedIndicator
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Создание индикатора с колонками по умолчанию
macd_indicator = MACDPreloadedIndicator()

# Получение информации о классе
info = MACDPreloadedIndicator.get_info()
print(f"Type: {info['type']}")
print(f"Required fields: {info['required_fields']}")

# Извлечение данных
result = macd_indicator.calculate(data)
print(f"Extracted columns: {list(result.data.columns)}")
```

### Кастомные колонки

```python
# Создание индикатора только для MACD линии
macd_only = MACDPreloadedIndicator(required_columns=['macd'])

# Создание индикатора для всех доступных колонок
macd_full = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])

# Валидация данных
try:
    is_valid = macd_full.validate_data(data)
    print("Validation passed")
except ValueError as e:
    print(f"Validation failed: {e}")
```

### Анализ трендов

```python
# Анализ тренда MACD линии
trending_up = macd_indicator.is_trending_up(data, column='macd')
trending_down = macd_indicator.is_trending_down(data, column='macd')

print(f"MACD trending up: {trending_up}")
print(f"MACD trending down: {trending_down}")

# Анализ с кастомным порогом
trending_up_strong = macd_indicator.is_trending_up(data, column='macd', threshold=0.5)
print(f"MACD strongly trending up: {trending_up_strong}")
```

### Анализ пересечений

```python
# Анализ пересечений MACD и signal
crossovers = macd_indicator.get_crossovers(data)

print(f"Bullish crossovers: {crossovers['bullish_crossovers']}")
print(f"Bearish crossovers: {crossovers['bearish_crossovers']}")

# Анализ пересечений с кастомными колонками
custom_crossovers = macd_indicator.get_crossovers(
    data, 
    column1='macd', 
    column2='signal'
)
```

### Статистика

```python
# Получение статистики по всем колонкам
stats = macd_indicator.get_statistics(data)

for col, col_stats in stats.items():
    print(f"{col}:")
    print(f"  Min: {col_stats['min']:.4f}")
    print(f"  Max: {col_stats['max']:.4f}")
    print(f"  Mean: {col_stats['mean']:.4f}")
    print(f"  NaN count: {col_stats['nan_count']}")
```

### Комбинированный анализ

```python
# Полный анализ PRELOADED MACD
def analyze_macd_data(data, indicator):
    """Комплексный анализ MACD данных"""
    
    # Валидация
    if not indicator.validate_data(data):
        return None
    
    # Извлечение данных
    result = indicator.calculate(data)
    
    # Анализ трендов
    trends = {
        'macd_up': indicator.is_trending_up(data, 'macd'),
        'macd_down': indicator.is_trending_down(data, 'macd'),
        'signal_up': indicator.is_trending_up(data, 'signal'),
        'signal_down': indicator.is_trending_down(data, 'signal')
    }
    
    # Анализ пересечений
    crossovers = indicator.get_crossovers(data)
    
    # Статистика
    stats = indicator.get_statistics(data)
    
    return {
        'data_columns': list(result.data.columns),
        'total_records': len(result.data),
        'trends': trends,
        'crossovers': crossovers,
        'statistics': stats,
        'metadata': result.metadata
    }

# Использование
analysis = analyze_macd_data(data, macd_indicator)
if analysis:
    print(f"Total records: {analysis['total_records']}")
    print(f"Trends: {analysis['trends']}")
    print(f"Crossovers: {analysis['crossovers']}")
```

## Создание собственного PRELOADED индикатора

```python
from bquant.indicators.base import PreloadedIndicator, IndicatorResult
import pandas as pd
from typing import List, Dict, Any, Optional

class RSI(PreloadedIndicator):
    """PRELOADED RSI индикатор"""
    
    def __init__(self, required_columns: Optional[List[str]] = None):
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
            'required_fields': {'rsi': 'RSI values (0-100)'},
            'usage_examples': {'basic': 'RSI()'}
        }
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        result_data = data[self._required_columns].copy()
        
        return IndicatorResult(
            name=self.name,
            data=result_data,
            config=self.config,
            metadata={
                'source': 'preloaded',
                'extracted_columns': self._required_columns,
                'total_records': len(result_data)
            }
        )
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        if data.empty:
            raise ValueError("Data is empty")
        
        missing_cols = [col for col in self._required_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        return True
```

## Лучшие практики

1. **Реализуйте class methods** - `get_info()` и `get_default_columns()` для всех PRELOADED индикаторов
2. **Валидируйте данные** - всегда проверяйте наличие необходимых колонок
3. **Обрабатывайте ошибки** - предоставляйте понятные сообщения об ошибках
4. **Документируйте параметры** - четко описывайте, какие поля требуются
5. **Тестируйте гибкость** - проверяйте работу с различными наборами колонок

## См. также

- [База индикаторов](base.md) - базовые классы и интерфейсы
- [MACD и зоны](macd.md) - MACD анализ с зонами
- [Фабрика и библиотека](factory.md) - создание и управление индикаторами
