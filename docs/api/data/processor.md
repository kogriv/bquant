# bquant.data.processor — Обработка данных

## Обзор

Предобработка OHLCV‑данных: очистка, удаление выбросов, ресемплинг, расчёт производных индикаторов и признаков.

## Функции

- `clean_ohlcv_data(df, fill_method='forward', remove_outliers=True, outlier_threshold=3.0) -> DataFrame`
- `remove_price_outliers(df, columns=None, threshold=3.0, method='z_score'|'iqr') -> DataFrame`
- `calculate_derived_indicators(df) -> DataFrame` — `hl_avg`, `ohlc_avg`, `typical_price`, `true_range`, `price_change`, `price_change_pct`, `gap/gap_pct`, volume‑метрики
- `resample_ohlcv(df, target_timeframe, method='standard') -> DataFrame`
- Дополнительно: `normalize_prices`, `detect_market_sessions`, `add_technical_features`, `create_lagged_features`, `prepare_data_for_analysis` (если присутствуют в версии модуля)

## Примеры

Очистка + подготовка:
```python
from bquant.data.processor import clean_ohlcv_data, prepare_data_for_analysis

clean = clean_ohlcv_data(df, fill_method='forward', remove_outliers=True)
prep = prepare_data_for_analysis(clean, add_tech_features=True, normalize=True)
```

Ресемплинг:
```python
from bquant.data.processor import resample_ohlcv
hourly = resample_ohlcv(df, '1H')
daily = resample_ohlcv(df, '1D')
```

Производные индикаторы:
```python
from bquant.data.processor import calculate_derived_indicators
features = calculate_derived_indicators(df)
```

## Советы

- Перед ресемплингом убедитесь, что индекс — DatetimeIndex.
- Для удаления выбросов выбирайте метод, подходящий под ваш рынок (z_score или IQR).

