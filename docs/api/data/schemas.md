# `bquant.data.schemas` — схемы данных

Схема отвечает на вопрос «каким кадр обязан быть»: какие поля обязательны, каких типов
и каким правилам подчиняются их значения. Проверка по схеме даёт вердикт с объяснением.

## Что здесь есть

| Имя | Что это |
|---|---|
| `DataSchema` | база: обязательные и опциональные поля, типы, правила, `validate_dataframe()` |
| `OHLCVSchema` | схема свечей: цены обязательны и положительны, объём опционален |
| `IndicatorSchema` | схема выходов индикатора; поля берутся у самого индикатора |
| `OHLCVRecord` | одна свеча как dataclass с `validate()` |
| `DataSourceConfig` | описание источника: шаблон имени файла, таймфреймы, провайдеры |
| `DataValidationResult` | результат: `is_valid`, `issues`, `warnings`, `stats`, `recommendations` |
| `OHLCV_SCHEMA`, `MACD_SCHEMA`, `RSI_SCHEMA` | готовые экземпляры |
| `get_schema(name)`, `validate_with_schema(df, name)` | доступ по имени |

## Проверка кадра

```python
from bquant.data.samples import get_sample_data
from bquant.data.schemas import validate_with_schema

data = get_sample_data('tv_xauusd_1h')
result = validate_with_schema(data, 'ohlcv')

print(result.is_valid, result.issues)
print(result.stats['checked_fields'], result.stats['absent_optional'])
# True []
# ['open', 'high', 'low', 'close', 'volume'] []
```

Отказ называет и то, чего не хватает, и то, что проверялось:

```python
from bquant.data.samples import get_sample_data
from bquant.data.schemas import validate_with_schema

result = validate_with_schema(get_sample_data('tv_xauusd_1h'), 'macd')

print(result.is_valid)
print(result.stats['missing_required'])
print(result.recommendations)
# False
# ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']
# ["Add the missing columns or pick another schema: ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']"]
```

Вердикт верен: в сэмпле есть колонки `macd` и `signal`, но это **выгрузка
TradingView**, а не выход индикатора пакета. Схема требует именно его выход.

До 2026-09-01 обе проверки печатали `True`: `validate_dataframe()` была заглушкой,
безусловно возвращавшей «валидно» на любом кадре, включая пустой. Признание «проверка не
реализована» лежало в `recommendations` — в поле, которое не читают, когда вердикт уже
получен (`devref/gaps/data/g42_…`).

## Что именно проверяется

| Что | Как отражается в результате |
|---|---|
| обязательное поле отсутствует | `issues`, `is_valid=False`, имена в `stats['missing_required']` |
| тип поля не числовой при объявленном `float` | `issues` с фактическим dtype |
| значения нарушают правило поля | `issues` + счётчик по колонкам в `stats['rule_violations']` |
| опциональное поле отсутствует | не отказ; отмечено в `stats['absent_optional']` |
| правило нечего применять (нет значений) | `warnings` — не молчание |

```python
import pandas as pd

from bquant.data.schemas import OHLCV_SCHEMA

frame = pd.DataFrame({
    'open': [1.0, -2.0], 'high': [2.0, 3.0],
    'low': [1.0, 2.0], 'close': [1.5, -2.5],
})
result = OHLCV_SCHEMA.validate_dataframe(frame)

print(result.is_valid, result.stats['rule_violations'])
print(result.stats['absent_optional'])
# False {'open': 1, 'close': 1}
# ['volume']
```

Правило «цена положительна» нарушено по одному разу в двух колонках; объём опционален,
и его отсутствие отказом не является.

## Схемы индикаторов

```python
from bquant.data.schemas import MACD_SCHEMA, RSI_SCHEMA

print(MACD_SCHEMA.required_fields)
print(RSI_SCHEMA.required_fields, len(RSI_SCHEMA.validation_rules))
# ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']
# ['rsi_14'] 1
```

Обязательные поля **спрашиваются у самого индикатора** (`get_output_columns()`), а не
перечисляются в схеме литералами. Собственный список был бы третьим местом, где живут
имена выходов, — и он успел разойтись с реальностью: схема `rsi` требовала колонку `rsi`,
которой индикатор не производит, а выглядело это верным только потому, что встроенный
сэмпл несёт свою колонку `rsi` из выгрузки TradingView.

Индикатор, для которого схема неизвестна, остаётся без ограничений — это не ошибка:

```python
from bquant.data.schemas import IndicatorSchema

schema = IndicatorSchema('stochastic')

print(schema.required_fields)
# []
```

## Одна свеча

```python
from datetime import datetime

from bquant.data.schemas import OHLCVRecord

good = OHLCVRecord(timestamp=datetime(2025, 1, 1), open=1.0, high=2.0, low=0.5,
                   close=1.5, volume=10.0)
bad = OHLCVRecord(timestamp=datetime(2025, 1, 1), open=1.0, high=0.4, low=0.5, close=1.5)

print(good.validate(), bad.validate())
# True False
```

`OHLCVRecord.validate()` возвращает голый `bool` без объяснения — это проверка одной
записи, а не отчёт. За объяснением — к схеме или к
[валидатору](validator.md).

## Неизвестное имя схемы

```python
import pandas as pd

from bquant.data.schemas import validate_with_schema

result = validate_with_schema(pd.DataFrame({'x': [1]}), 'нет_такой_схемы')

print(result.is_valid, result.issues)
print(result.recommendations)
# False ["Schema 'нет_такой_схемы' not found"]
# ["Available schemas: ['ohlcv', 'macd', 'rsi']"]
```

## Схема против валидатора

Обе стороны проверяют данные, но отвечают на разные вопросы:

| | схема | [валидатор](validator.md) |
|---|---|---|
| Вопрос | соответствует ли кадр **объявленным** требованиям | что с данными не так по существу |
| Знает заранее | перечень полей, типы, правила | ничего, кроме соглашения об OHLCV |
| Годится для | своих форматов и выходов индикаторов | сырых рыночных данных |

## Дальше

| | |
|---|---|
| [Валидация](validator.md) | проверки по существу данных |
| [Обработка](processor.md) | что делать с найденным |
| [Индикаторы](../indicators/README.md) | откуда берутся имена выходных колонок |
