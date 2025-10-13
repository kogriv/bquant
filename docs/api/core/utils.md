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

---

## Deprecation Tools (New in Phase 2)

> **API Stability:** 🟢 STABLE

### @deprecated decorator

Marks methods as deprecated with automatic warning generation.

**Purpose:** Gracefully deprecate methods while maintaining backward compatibility.

**Usage:**
```python
from bquant.core.utils import deprecated

@deprecated("Use new_method() instead")
def old_method():
    """This method is deprecated."""
    pass

# When called
old_method()
# DeprecationWarning: old_method is deprecated. Use new_method() instead
```

**Effect:**
- Generates `DeprecationWarning` on first call per session
- Logs warning message to bquant logger
- Method still works (backward compatibility maintained)
- Warning can be filtered if needed

**Parameters:**
- `message`: String describing what to use instead

**Best practices:**
1. Always provide clear alternative in message
2. Deprecate for 1-2 versions before removal
3. Document deprecation in changelog
4. Update all examples to not use deprecated methods
5. Consider adding migration guide

**Example from BQuant:**
```python
@deprecated("Use ZoneFeaturesAnalyzer.extract_zone_features() from bquant.analysis.zones instead")
def calculate_zone_features(self, zone):
    # Old implementation kept for compatibility
    pass
```

**See also:**
- Phase 4 migration: removed 5 deprecated methods
- `docs/api/indicators/macd.md` - migration notice
