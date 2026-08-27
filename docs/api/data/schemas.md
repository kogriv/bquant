# bquant.data.schemas — Схемы данных

## Обзор

Схемы и модели для структурированной валидации данных (базовые заготовки).

## Модели и классы

- `OHLCVRecord` — запись OHLCV (timestamp, open, high, low, close, volume) с методом `validate()`
- `DataSourceConfig` — описание источника данных (паттерн файлов, маппинги таймфреймов, провайдеры котировок)
- `DataValidationResult` — результат валидации (is_valid, issues, warnings, stats, recommendations)
- `DataSchema` — базовый класс схем: поля, типы, правила, `validate_dataframe(df)`
- `OHLCVSchema(DataSchema)` — схема для OHLCV
- `IndicatorSchema(DataSchema)` — схема для индикаторов (`macd`, `rsi`, `bollinger_bands`).
  Обязательные поля **берутся у самого индикатора** (`get_output_columns()`), а не
  перечисляются в схеме: собственный список был третьим местом, где живут имена выходов,
  и он успел разойтись с реальностью — схема `rsi` требовала колонку `rsi`, которой
  индикатор не производит (он выдаёт `rsi_14`), а выглядело это верным лишь потому, что
  встроенный сэмпл несёт свою колонку `rsi` из выгрузки TradingView

## Предопределённые схемы

- `OHLCV_SCHEMA`, `MACD_SCHEMA`, `RSI_SCHEMA`
- `AVAILABLE_SCHEMAS = {'ohlcv', 'macd', 'rsi'}`

## Функции

- `get_schema(name) -> Optional[DataSchema]`
- `validate_with_schema(df, schema_name) -> DataValidationResult`

## Пример

```python
import pandas as pd
from bquant.data.schemas import validate_with_schema

df = pd.DataFrame({'open':[1,2], 'high':[2,3], 'low':[1,2], 'close':[1.5, 2.5]})
res = validate_with_schema(df, 'ohlcv')
print(res.is_valid, res.stats)
```

Примечание: текущая реализация — заготовка; детальная схемная валидация может быть расширена в будущем.

