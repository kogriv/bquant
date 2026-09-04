# `bquant.data.processor` — обработка данных

Чистка, ресемплинг, производные величины и признаки. Всё принимает `DataFrame` и
возвращает `DataFrame`; исходный кадр не меняется.

## Функции

| Сигнатура | Что делает |
|---|---|
| `resolve_time_index(df)` | переносит время из колонки в `DatetimeIndex` |
| `clean_ohlcv_data(df, fill_method='forward', remove_outliers=True, outlier_threshold=3.0)` | заполняет пропуски, снимает выбросы |
| `remove_price_outliers(df, columns=None, threshold=3.0, method='z_score')` | только выбросы; `method` — `'z_score'` или `'iqr'` |
| `calculate_derived_indicators(df)` | десять величин из самих цен |
| `resample_ohlcv(df, target_timeframe, method='standard')` | меняет таймфрейм |
| `normalize_prices(df, base_column='close', method='first_value')` | нормирует цены |
| `detect_market_sessions(df, timezone='UTC')` | размечает торговые сессии |
| `add_technical_features(df)` | семнадцать технических признаков |
| `create_lagged_features(df, columns, lags)` | лаги указанных колонок |
| `prepare_data_for_analysis(df, target_column='close', …)` | всё вместе, одним вызовом |

## Кому нужен `DatetimeIndex`

Три функции — `resample_ohlcv()`, `detect_market_sessions()` и (через них)
`prepare_data_for_analysis()` с сессиями — работают по времени и требуют
`DatetimeIndex`. Sample-данные отдают время колонкой, поэтому им нужен
`resolve_time_index()`:

```python
from bquant.data.processor import resample_ohlcv, resolve_time_index
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
indexed = resolve_time_index(data)

print(type(data.index).__name__, '→', type(indexed.index).__name__)
print(resample_ohlcv(indexed, '4h').shape, resample_ohlcv(indexed, '1d').shape)
# RangeIndex → DatetimeIndex
# (262, 5) (53, 5)
```

Без переноса `resample_ohlcv()` поднимет `DataProcessingError` и назовёт причину —
`RangeIndex` вместо временного. Кадр из `load_ohlcv_data()` в переносе не нуждается:
загрузчик ставит время в индекс сам.

Таймфрейм задаётся в соглашении проекта — `'5m'`, `'1h'`, `'1d'`, `'1w'`, `'1M'` — и
переводится в pandas-алиас с тем же смыслом (`pandas_offset_alias` из `bquant.core.config`);
собственные алиасы pandas (`'5min'`, `'D'`, `'ME'`) принимаются как есть. До 2026-09-04
строка уходила в pandas без перевода, а pandas читает `m` как конец месяца: `'5m'` давал
пятимесячные бары и сообщал об успехе.

Ресемплинг оставляет пять колонок — OHLCV. Всё остальное (индикаторы источника,
маркеры) агрегировать нечем, и оно отбрасывается.

## Чистка

```python
from bquant.data.processor import clean_ohlcv_data
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
clean = clean_ohlcv_data(data, fill_method='forward', remove_outliers=True)

print(data.shape, '→', clean.shape)
# (1000, 15) → (1000, 15)
```

На встроенных данных чистка ничего не удаляет: пропусков в ценах нет, выбросов за три
сигмы тоже. Это ожидаемо для аккуратной выгрузки и не означает, что вызов лишний.

## Производные величины

```python
from bquant.data.processor import calculate_derived_indicators
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
derived = calculate_derived_indicators(data)

print([c for c in derived.columns if c not in data.columns])
# ['hl_avg', 'ohlc_avg', 'typical_price', 'true_range', 'price_change', 'price_change_pct', 'gap', 'gap_pct', 'volume_sma_20', 'volume_ratio']
```

Ничего внешнего здесь не считается — только арифметика по OHLCV. Индикаторы живут в
[`bquant.indicators`](../indicators/README.md).

## Признаки

```python
from bquant.data.processor import add_technical_features, create_lagged_features
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')
featured = add_technical_features(data)
lagged = create_lagged_features(data, ['close'], [1, 3])

print(len(featured.columns) - len(data.columns), 'новых признаков')
print([c for c in lagged.columns if c not in data.columns])
# 17 новых признаков
# ['close_lag_1', 'close_lag_3']
```

## Подготовка одним вызовом

```python
from bquant.data.processor import clean_ohlcv_data, prepare_data_for_analysis
from bquant.data.samples import get_sample_data

clean = clean_ohlcv_data(get_sample_data('tv_xauusd_1h'))
prepared = prepare_data_for_analysis(clean, add_tech_features=True, normalize=True)

print(prepared.shape)
print(prepared.index[0], prepared.index[-1])
# (951, 36)
# 49 999
```

`prepare_data_for_analysis()` последовательно чистит, добавляет признаки, при
`create_lags=True` — лаги, нормирует и снимает строки с пропусками. Отсев идёт **только
по цели и признакам**, и снимаются ровно строки прогрева самого длинного окна: `price_ma_50`
требует 50 баров, поэтому результат начинается с индекса 49.

Три свойства, за которые стоит держаться:

* **Колонка, пустая во всех строках, признаком не считается** и строк не отсеивает; её
  имя уходит в лог уровня WARNING.
* **Пустой результат не возвращается.** Если после отсева не осталось ничего, функция
  поднимает `DataProcessingError` и объясняет, сколько строк было и по скольким колонкам
  шёл отсев.
* Отсев не трогает колонки, к анализу отношения не имеющие.

До 2026-09-01 всё было наоборот: `dropna()` шёл по всему кадру, четыре пустые колонки
маркеров дивергенций TradingView уносили выборку целиком, и функция возвращала
`(0, 36)` — тридцать шесть колонок и ни одной строки — как успех
(`devref/gaps/data/g41_…`).

## Нормировка и сессии

```python
from bquant.data.processor import detect_market_sessions, normalize_prices, resolve_time_index
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

normalized = normalize_prices(data, base_column='close', method='first_value')
sessions = detect_market_sessions(resolve_time_index(data), timezone='UTC')

print([c for c in normalized.columns if c.endswith('_normalized')])
print([c for c in sessions.columns if c not in data.columns])
# ['open_normalized', 'high_normalized', 'low_normalized', 'close_normalized']
# ['session', 'london_ny_overlap']
```

`normalize_prices()` добавляет колонки, а не заменяет исходные. `method` принимает
`'first_value'`, `'min_max'` и `'z_score'`.

## Дальше

| | |
|---|---|
| [Валидация](validator.md) | что проверить до обработки |
| [Схемы](schemas.md) | как описать требования к кадру |
| [Индикаторы](../indicators/README.md) | что считать поверх |
| [Анализ зон](../analysis/README.md) | куда это идёт |
