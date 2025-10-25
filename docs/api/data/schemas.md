# bquant.data.schemas — Схемы данных

## Обзор

Схемы и модели для структурированной валидации данных (базовые заготовки).

## Модели и классы

- `OHLCVRecord` — запись OHLCV (timestamp, open, high, low, close, volume) с методом `validate()`
- `DataSourceConfig` — описание источника данных (паттерн файлов, маппинги таймфреймов, провайдеры котировок)
- `ValidationResult` — результат валидации (is_valid, issues, warnings, stats, recommendations)
- `DataSchema` — базовый класс схем: поля, типы, правила, `validate_dataframe(df)`
- `OHLCVSchema(DataSchema)` — схема для OHLCV
- `IndicatorSchema(DataSchema)` — схема для индикаторов (поддерживаются варианты `macd`, `rsi`)

## Предопределённые схемы

- `OHLCV_SCHEMA`, `MACD_SCHEMA`, `RSI_SCHEMA`
- `AVAILABLE_SCHEMAS = {'ohlcv', 'macd', 'rsi'}`

## Функции

- `get_schema(name) -> Optional[DataSchema]`
- `validate_with_schema(df, schema_name) -> ValidationResult`

## Пример

```python
import pandas as pd
from bquant.data.schemas import validate_with_schema

df = pd.DataFrame({'open':[1,2], 'high':[2,3], 'low':[1,2], 'close':[1.5, 2.5]})
res = validate_with_schema(df, 'ohlcv')
print(res.is_valid, res.stats)
```

Примечание: текущая реализация — заготовка; детальная схемная валидация может быть расширена в будущем.

