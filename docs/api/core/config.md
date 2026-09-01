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

path = get_data_path('XAUUSD', '1h', data_source='tradingview', quote_provider='oanda')
print(path.name)
# OANDA_XAUUSD, 60.csv
```

Функция **собирает путь, а не проверяет файл**: она отвечает на вопрос «как назывался бы
файл», и вернёт имя даже для символа, которого нет. Существование проверяет загрузчик.

Проверка таймфрейма:
```python
from bquant.core.config import SUPPORTED_TIMEFRAMES, validate_timeframe

print(validate_timeframe('1h'), len(SUPPORTED_TIMEFRAMES))
try:
    validate_timeframe('2D')
except ValueError as error:
    print(str(error)[:37])
# 1h 27
# Unsupported timeframe: 2D. Supported:
```

Поддерживаются 27 обозначений, и регистр в них значим по-разному: `1d` и `1D` — оба
приняты, `2D` — нет, потому что двухдневного таймфрейма в списке нет вовсе. Здесь
поднимается обычный `ValueError`; одноимённая
[`exceptions.validate_timeframe(timeframe, supported)`](exceptions.md) принимает список
аргументом и поднимает `InvalidTimeframeError` — это разные функции.

Параметры индикатора:
```python
from bquant.core.config import get_indicator_params

macd_params = get_indicator_params('macd', fast=8)
```

Путь для результатов:
```python
from bquant.core.config import get_results_path

path = get_results_path('zone_analysis', file_type='csv')
print(path.name, path.suffix)
# zone_analysis.csv .csv
```

---

## Фабрики стратегий (новое в фазе 3)

> **Стабильность API:** 🟢 В ОСНОВНОМ СТАБИЛЕН
>
> **Примечание:** Сигнатуры функций стабильны. Внутренняя реализация может
> изменяться в процессе унификации (например, обработка имён столбцов).

Фабричные функции создают экземпляры стратегий на основе конфигурации.

Каждая принимает имя, словарь `{'type': ..., 'params': {...}}` или готовый экземпляр и
возвращает **экземпляр**, а не класс.

```python
from bquant.core.config import (
    create_divergence_strategy, create_shape_strategy, create_swing_strategy,
    create_volatility_strategy, create_volume_strategy,
)

print(create_swing_strategy())
print(create_swing_strategy('find_peaks'))
print(create_swing_strategy({'type': 'zigzag', 'params': {'legs': 15, 'deviation': 0.03}}))
# ZigZagSwingStrategy(legs=10, deviation=0.05)
# FindPeaksSwingStrategy(prominence=None, distance=5, min_amplitude_pct=0.02, prominence_warmup=200)
# ZigZagSwingStrategy(legs=15, deviation=0.03)

print(create_shape_strategy('statistical'))
print(create_divergence_strategy('classic'))
print(create_volatility_strategy({'type': 'combined', 'params': {'bb_length': 20}}))
print(create_volume_strategy('standard'))
# StatisticalShapeStrategy(calculate_smoothness=True, bias_correction=True)
# ClassicDivergenceStrategy(min_peak_distance=5, min_divergence_strength=0.01)
# CombinedVolatilityStrategy(bb_length=20, bb_std=2.0, touch_threshold=0.01)
# StandardVolumeStrategy(baseline_window=50, correlation_min_periods=3)
```

Значения без аргументов — **конструкторские**, а не те, с которыми стратегия
поедет в анализ: для свингов их перекрывает пресет, и именно пресет определяет, найдётся
ли хоть что-нибудь. См. [свинг-стратегии](../../user_guide/swing_strategies.md).

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
import tempfile

from bquant.core.config import (
    get_data_dir, get_directory_status, reset_directories_to_defaults, set_data_dir
)

status = get_directory_status()
print(sorted(status))
print(sorted(status['data_dir']))
# ['data_dir', 'notebooks_dir', 'processed_data_dir', 'results_dir']
# ['current', 'default', 'exists', 'is_custom']

set_data_dir(tempfile.mkdtemp())
print(get_directory_status()['data_dir']['is_custom'])
# True

reset_directories_to_defaults()
print(get_directory_status()['data_dir']['is_custom'])
# False
```

`is_custom` отвечает на вопрос «переставляли ли путь», а не «существует ли он» — на это
есть отдельный ключ `exists`. Установка пути каталог не создаёт.
