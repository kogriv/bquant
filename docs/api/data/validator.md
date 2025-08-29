# bquant.data.validator — Валидация данных

## Обзор

Комплексная проверка качества, структуры и непрерывности OHLCV‑данных.

## Функции

- `validate_ohlcv_data(df, strict=True) -> Dict` — общая валидация:
  - базовая структура, качество данных, логика OHLC, временной ряд, объём
  - возвращает: `{'is_valid', 'issues', 'warnings', 'stats', 'recommendations'}`

- `validate_data_completeness(df, required_columns=None, min_rows=None) -> Dict`
  - проверка обязательных колонок, минимального числа строк и доли пропусков по колонкам

- `validate_price_consistency(df) -> Dict`
  - логические проверки цен: high>=low, high>=open/close, low<=open/close; неотрицательные значения; экстремальные изменения

- `validate_time_series_continuity(df, expected_frequency=None) -> Dict`
  - проверка непрерывности временного ряда: частота, дубликаты, пробелы

## Примеры

```python
from bquant.data.validator import (
    validate_ohlcv_data, validate_data_completeness,
    validate_price_consistency, validate_time_series_continuity
)

overall = validate_ohlcv_data(df)
completeness = validate_data_completeness(df)
prices = validate_price_consistency(df)
ts = validate_time_series_continuity(df, expected_frequency='1H')
```

## Результаты и рекомендации

- Используйте `issues` и `warnings` для быстрых правок данных.
- `recommendations` подсказывает наиболее вероятные шаги по улучшению качества датасета.

