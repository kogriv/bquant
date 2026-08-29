# bquant.core.config — Конфигурация и пути

## Обзор

Модуль содержит константы путей проекта, конфигурации таймфреймов и шаблоны имён файлов данных, а также вспомогательные функции для получения путей и параметров.

## Основные константы

- `PROJECT_ROOT`: корень проекта
- `DATA_DIR`, `ALLDATA_DIR`, `PROCESSED_DATA_DIR`: директории данных
- `SCRIPTS_DIR`, `NOTEBOOKS_DIR`, `RESULTS_DIR`: служебные директории
- `TIMEFRAME_MAPPING`: соответствия таймфреймов для источников данных (`tradingview`, `metatrader`)
- `DATA_FILE_PATTERNS`: шаблоны имён файлов для разных источников
- `SUPPORTED_TIMEFRAMES`: поддерживаемые таймфреймы
- `DATA_VALIDATION`: правила валидации данных
- `CACHE_CONFIG`: настройки кэширования
- `LOGGING`: базовые настройки логирования
- `DEFAULT_INDICATORS`: параметры индикаторов по умолчанию — источник, из которого
  читает `get_indicator_params()` (см. ниже)

## Ключевые функции

- `get_data_path(symbol, timeframe, data_source='tradingview', quote_provider='default') -> Path`
  - Возвращает путь к файлу данных по символу и таймфрейму с учётом источника/провайдера.

- `get_indicator_params(indicator, **overrides) -> Dict[str, Any]`
  - Параметры индикатора по умолчанию с возможностью переопределения.
  - Читает `DEFAULT_INDICATORS`; для незнакомого имени возвращает пустой словарь,
    а не ошибку.

```python
from bquant.core import DEFAULT_INDICATORS
from bquant.core.config import get_indicator_params

print(sorted(DEFAULT_INDICATORS))
# ['atr', 'bollinger_bands', 'ema', 'macd', 'rsi', 'sma', 'stochastic', 'williams_r']

print(get_indicator_params('macd'))                # {'fast': 12, 'slow': 26, 'signal': 9}
print(get_indicator_params('macd', fast=5))        # {'fast': 5, 'slow': 26, 'signal': 9}
print(get_indicator_params('несуществующий'))      # {}
```

Имена ключей здесь — **не** имена классов индикаторов, и параметры записаны в стиле
внешних библиотек (`fast`/`slow`/`signal`, `length`). Встроенные индикаторы
([custom.md](../indicators/custom.md)) принимают свои имена аргументов
(`fast_period`, `period`), так что словарь сюда не передаётся как есть.

- `get_analysis_params(analysis_type, **overrides) -> Dict[str, Any]`
  - Параметры анализа по умолчанию с возможностью переопределения.

- `validate_timeframe(timeframe) -> str`
  - Проверяет, что таймфрейм поддерживается; иначе ValueError.

- `get_results_path(experiment_name, file_type='csv') -> Path`
  - Возвращает путь для сохранения результатов экспериментов.

- `get_cache_config() -> Dict[str, Any]`
  - Копия конфигурации кэша.

## Управление директориями

Новые функции для динамического управления путями директорий:

### Getter функции
- `get_data_dir() -> Path` — Получить текущий путь к директории данных
- `get_results_dir() -> Path` — Получить путь к директории результатов  
- `get_notebooks_dir() -> Path` — Получить путь к директории ноутбуков
- `get_processed_data_dir() -> Path` — Получить путь к директории обработанных данных

### Setter функции
- `set_data_dir(path) -> None` — Установить новый путь к директории данных
- `set_results_dir(path) -> None` — Установить путь к директории результатов
- `set_notebooks_dir(path) -> None` — Установить путь к директории ноутбуков  
- `set_processed_data_dir(path) -> None` — Установить путь к директории обработанных данных

### Утилиты
- `reset_directories_to_defaults() -> None` — Сбросить все пути к значениям по умолчанию
- `get_directory_status() -> Dict[str, Any]` — Получить информацию о текущих путях

## Примеры

Получение пути к данным TradingView:
```python
from bquant.core.config import get_data_path

# OANDA XAUUSD, TradingView 1h
path = get_data_path('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')
print(path)
```

Проверка таймфрейма:
```python
from bquant.core.config import validate_timeframe

validate_timeframe('1h')   # '1h'
validate_timeframe('2D')   # ValueError
```

Параметры индикатора:
```python
from bquant.core.config import get_indicator_params

macd_params = get_indicator_params('macd', fast=8)
```

Путь для результатов:
```python
from bquant.core.config import get_results_path

csv_path = get_results_path('zone_analysis_2025-08-29', file_type='csv')
```

---

## Фабрики стратегий (новое в фазе 3)

> **Стабильность API:** 🟢 В ОСНОВНОМ СТАБИЛЕН
>
> **Примечание:** Сигнатуры функций стабильны. Внутренняя реализация может
> изменяться в процессе унификации (например, обработка имён столбцов).

Фабричные функции создают экземпляры стратегий на основе конфигурации.

### create_swing_strategy()

Создание стратегии для определения свингов.

```python
from bquant.core.config import create_swing_strategy

strategy_default = create_swing_strategy()
strategy_by_name = create_swing_strategy('find_peaks')
strategy_custom = create_swing_strategy({
    'type': 'zigzag',
    'params': {'legs': 15, 'deviation': 0.03}
})
```

### create_shape_strategy()

```python
from bquant.core.config import create_shape_strategy

strategy = create_shape_strategy('statistical')
```

### create_divergence_strategy()

```python
from bquant.core.config import create_divergence_strategy

strategy = create_divergence_strategy('classic')
```

### create_volatility_strategy()

```python
from bquant.core.config import create_volatility_strategy

strategy = create_volatility_strategy({
    'type': 'combined',
    'params': {'bb_length': 20, 'bb_std': 2.0, 'touch_threshold': 0.02}
})
```

### create_volume_strategy()

```python
from bquant.core.config import create_volume_strategy

strategy = create_volume_strategy('standard')
```

### ANALYSIS_CONFIG

Конфигурация стратегий анализа:

```python
ANALYSIS_CONFIG = {
    # Секции 'zone_analysis' здесь нет, как нет и ключей 'min_duration' /
    # 'min_amplitude': их не читала ни одна строка пакета. Порог длительности
    # задаётся явно — `.analyze(min_duration=N)`.
    'zone_features': {
        'swing_strategy': {
            'type': 'zigzag',
            'params': {'legs': 10, 'deviation': 0.05},
        },
        'divergence_strategy': {
            'type': 'none',
            'params': {},
        },
        'shape_strategy': {
            'type': 'statistical',
            'params': {'calculate_smoothness': True, 'bias_correction': True},
        },
        'volume_strategy': {
            'type': 'none',
            'params': {},
        },
    },
    'pattern_analysis': {
        'min_pattern_length': 3,
        'max_pattern_length': 50,
        'similarity_threshold': 0.8,
    },
    'statistical_analysis': {
        'confidence_level': 0.95,
        'significance_level': 0.05,
        'bootstrap_samples': 1000,
        'random_state': 42,
    },
}
```

Подробную документацию по стратегиям см. в разделе [Analysis Strategies](../analysis/strategies.md).

---

Управление директориями:
```python
from bquant.core.config import (
    get_data_dir, set_data_dir, get_directory_status, reset_directories_to_defaults
)

# Получить текущий путь к данным
current_data_dir = get_data_dir()

# Установить кастомный путь
set_data_dir('/custom/data/path')

# Проверить статус всех директорий
status = get_directory_status()
print(status['data_dir']['is_custom'])  # True

# Сбросить к умолчаниям
reset_directories_to_defaults()
```
