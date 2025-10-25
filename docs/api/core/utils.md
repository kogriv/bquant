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

df = pd.DataFrame({
    'open': [100, 102, 105],
    'high': [101, 103, 106],
    'low': [99, 101, 104],
    'close': [100.5, 102.5, 105.5],
    'volume': [1200, 1350, 1280],
})
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

## Инструменты устаревания (новое во второй фазе)

> **Стабильность API:** 🟢 СТАБИЛЬНО

### @deprecated decorator

Помечает методы как устаревшие и автоматически формирует предупреждение.

**Назначение:** Аккуратно отмечать методы как устаревшие, сохраняя обратную совместимость.

**Использование:**
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

**Эффект:**
- Генерирует `DeprecationWarning` при первом вызове в рамках сессии
- Записывает предупреждение в логгер bquant
- Метод продолжает работать (обратная совместимость сохраняется)
- При необходимости предупреждение можно отфильтровать

**Параметры:**
- `message`: строка с описанием альтернативы

**Рекомендации:**
1. Всегда указывайте понятную альтернативу в сообщении
2. Поддерживайте устаревший метод 1–2 версии до удаления
3. Документируйте факт устаревания в changelog
4. Обновляйте примеры, чтобы они не использовали устаревшие методы
5. При необходимости добавляйте миграционное руководство

**Пример из BQuant:**
```python
@deprecated("Use ZoneFeaturesAnalyzer.extract_zone_features() from bquant.analysis.zones instead")
def calculate_zone_features(self, zone):
    # Old implementation kept for compatibility
    pass
```

**См. также:**
- Миграция фазы 4: удалены 5 устаревших методов
- `docs/api/indicators/macd.md` — уведомление о миграции
