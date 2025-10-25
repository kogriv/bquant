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

- `validate_statistical_properties(df) -> Dict`
  - базовая статистика, поиск выбросов, проверки асимметрии и эксцесса

## Примеры

```python
import numpy as np
import pandas as pd

from bquant.data.validator import (
    validate_ohlcv_data, validate_data_completeness,
    validate_price_consistency, validate_time_series_continuity,
    validate_statistical_properties,
)

index = pd.date_range("2024-01-01", periods=120, freq="1h", name="time")
base = np.linspace(100.0, 110.0, len(index))
noise = np.sin(np.linspace(0, 6 * np.pi, len(index)))

df = pd.DataFrame(
    {
        "open": base + noise,
        "high": base + noise + 0.5,
        "low": base + noise - 0.5,
        "close": base + noise * 0.5,
        "volume": np.linspace(500, 900, len(index)),
    },
    index=index,
)

overall = validate_ohlcv_data(df)
completeness = validate_data_completeness(df)
prices = validate_price_consistency(df)
ts = validate_time_series_continuity(df, expected_frequency='1h')
stats = validate_statistical_properties(df)
```

## Результаты и рекомендации

- Используйте `issues` и `warnings` для быстрых правок данных.
- `recommendations` подсказывает наиболее вероятные шаги по улучшению качества датасета.

