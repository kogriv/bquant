# bquant.core.utils — Утилиты

## Обзор

Вспомогательные функции: логгирование проекта, расчёт доходностей, нормализация данных, сохранение результатов, валидации, полезные утилиты.

## Функции

- `setup_project_logging(name='bquant', level=None, log_to_file=None, log_file=None) -> logging.Logger`
- `calculate_returns(prices, method='simple', periods=1) -> pd.Series`
- `normalize_data(data, method='zscore', columns=None) -> pd.DataFrame`
- `save_results(data, filepath, format='csv', **kwargs) -> bool`
- `validate_ohlcv_columns(data, strict=True) -> Dict[str, Any]`
- `create_timestamp(format='compact') -> str`
- `memory_usage_info(data) -> Dict[str, Any]`
- `ensure_directory(path) -> Path`

## Примеры

Доходности и нормализация:
```python
import pandas as pd
from bquant.core.utils import calculate_returns, normalize_data

prices = pd.Series([1, 1.1, 1.2])
r = calculate_returns(prices, method='simple')

df = pd.DataFrame({'a':[1,2,3], 'b':[10,20,30]})
norm = normalize_data(df, method='zscore')
```

Сохранение результатов:
```python
from bquant.core.utils import save_results
ok = save_results(df, 'results/out.csv', index=False)
```

Валидация колонок OHLCV:
```python
from bquant.core.utils import validate_ohlcv_columns
result = validate_ohlcv_columns(df)
print(result['is_valid'], result['messages'])
```

Прочие утилиты:
```python
from bquant.core.utils import create_timestamp, ensure_directory
ts = create_timestamp('readable')
ensure_directory('results/charts')
```
