# BQuant - Архитектура проекта

## 📋 Обзор проекта

**BQuant** - это универсальный инструментарий для количественного исследования финансовых рынков. Проект начинается с MACD анализа зон как первого кейса, но архитектура рассчитана на исследование различных аспектов: технических индикаторов, графических паттернов, свечных формаций, временных рядов и применения машинного обучения.

### Ключевые возможности
- 🔧 **Универсальная конфигурационная система** - поддержка множества источников данных и брокеров
- 📊 **Многоуровневый анализ** - технический, статистический, графический, свечной, временные ряды
- 🤖 **Готовность к ML** - структура для машинного обучения (заглушки)
- 📈 **Инструменты визуализации** - графики и отчеты
- 🧪 **Исследовательская среда** - ноутбуки и эксперименты
- 🚀 **Автоматизированные пайплайны** - готовые скрипты для анализа

### Философия проекта
- **Универсальность** - начинаем с MACD, развиваемся в сторону комплексного анализа всех аспектов рынка
- **Научная строгость** - статистическое тестирование гипотез, валидация результатов
- **Простота использования** - минимум кода для максимума функциональности  
- **Расширяемость** - легкое добавление новых индикаторов, паттернов, методов анализа

---

## 🏗️ Структура проекта

```
bquant/
├── setup.py                    # Конфигурация пакета
├── pyproject.toml              # Современная конфигурация Python
├── requirements.txt            # Зависимости проекта
├── README.md                   # Основная документация
│
├── bquant/                     # 📦 ОСНОВНОЙ ПАКЕТ
│   ├── __init__.py
│   ├── core/                   # 🎯 Ядро системы
│   ├── data/                   # 💾 Работа с данными  
│   ├── indicators/             # 📊 Технические индикаторы
│   ├── analysis/              # 🔬 Аналитические модули
│   ├── ml/                    # 🤖 Машинное обучение (заглушки)
│   └── visualization/         # 📈 Визуализация
│
├── research/                   # 🧪 ИССЛЕДОВАНИЯ
│   ├── notebooks/             # Jupyter ноутбуки
│   ├── experiments/           # ML эксперименты (заглушки)
│   ├── studies/               # Исследовательские скрипты
│   └── methodology/           # Документация методологии
│
├── scripts/                    # 🚀 АВТОМАТИЗАЦИЯ
│   ├── pipelines/             # Пайплайны обработки
│   ├── data_processing/       # Скрипты обработки данных
│   ├── analysis/              # Готовые анализы
│   └── deployment/            # Деплой и продакшен (заглушки)
│
├── data/                       # 💽 ДАННЫЕ
│   ├── raw/                   # Сырые данные
│   ├── processed/             # Обработанные данные
│   ├── features/              # Признаки для ML (заглушки)
│   └── models/                # Обученные модели (заглушки)
│
├── tests/                      # ✅ ТЕСТЫ (ВНЕ ПАКЕТА)
│   ├── unit/                  # Модульные тесты
│   ├── integration/           # Интеграционные тесты
│   └── fixtures/              # Тестовые данные
│
├── docs/                       # 📖 ДОКУМЕНТАЦИЯ
│   ├── api/                   # API документация
│   ├── tutorials/             # Туториалы
│   └── examples/              # Примеры использования
│
├── logs/                       # 📝 Логи
└── results/                    # 📋 Результаты анализа
```

---

## 📦 Детальная структура модулей

### 🎯 `bquant/core/` - Ядро системы

```python
bquant/core/
├── __init__.py                 # Экспорт основных компонентов
├── config.py                   # Универсальная конфигурация
├── utils.py                    # Общие утилиты
├── logging_config.py           # Настройка логгирования
├── exceptions.py               # Исключения системы
└── numpy_fix.py                # Исправления для numpy
```

#### `bquant/core/config.py`
**Источник:** Полностью переносим из `core/config.py`

**Что сохранить:**
- Все константы (`PROJECT_ROOT`, `DATA_DIR`, `TIMEFRAME_MAPPING`, `DATA_FILE_PATTERNS`)
- Все функции (`get_data_path()`, `get_indicator_params()`, `validate_timeframe()`)
- `DEFAULT_INDICATORS` - параметры индикаторов

**Что изменить:**
- Название проекта в путях на `bquant`
- Добавить поддержку готовых индикаторов в данных

#### `bquant/core/utils.py` - Новый модуль
```python
"""
Общие утилиты BQuant
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

def setup_project_logging(level: str = 'INFO') -> logging.Logger:
    """Настроить логгирование для проекта"""
    # Реализация настройки логгирования
    pass

def calculate_returns(prices: pd.Series) -> pd.Series:
    """Рассчитать доходности"""
    return prices.pct_change()

def normalize_data(data: pd.DataFrame, method: str = 'zscore') -> pd.DataFrame:
    """Нормализовать данные"""
    # Простые методы нормализации
    pass

def save_results(data: Any, filepath: str, format: str = 'csv'):
    """Универсальное сохранение результатов"""
    # Сохранение в разных форматах
    pass
```

#### `bquant/core/exceptions.py`
**Источник:** Создать новый, базируясь на паттернах из старых тестов

```python
"""Исключения системы BQuant"""

class BQuantError(Exception):
    """Базовое исключение BQuant"""
    pass

class DataError(BQuantError):
    """Ошибка данных"""
    pass

class ConfigurationError(BQuantError):
    """Ошибка конфигурации"""  
    pass

class AnalysisError(BQuantError):
    """Ошибка анализа"""
    pass
```

#### `bquant/core/numpy_fix.py`
**Источник:** Переносим из `scripts/core/numpy_fix.py`

```python
"""
Исправления для совместимости numpy
ИСТОЧНИК: scripts/core/numpy_fix.py
"""
import numpy as np
import sys

# Добавляем псевдоним для обратной совместимости
if not hasattr(np, 'NaN'):
    np.NaN = np.nan

# Перезагружаем модуль numpy с исправлением
sys.modules['numpy'].NaN = np.nan
```

### 💾 `bquant/data/` - Работа с данными

```python
bquant/data/
├── __init__.py                 # Экспорт функций загрузки
├── loader.py                   # Загрузка данных
├── processor.py                # Обработка данных
├── validator.py                # Валидация данных
└── schemas.py                  # Схемы данных (заглушка)
```

**Источники:**
- `loader.py` - переносим из `data/data_loader.py` функции `load_symbol_data()`, `load_all_data_files()`
- `processor.py` - переносим из `data/data_processor.py` функции очистки и обработки
- `validator.py` - переносим из `data/data_validator.py` функции валидации

**Что убрать:** Избыточную обработку ошибок и fallback код

### 📊 `bquant/indicators/` - Технические индикаторы

```python
bquant/indicators/
├── __init__.py                 # Экспорт индикаторов
├── base.py                     # Базовые классы для индикаторов
├── loaders.py                  # Загрузка готовых индикаторов из данных
├── library.py                  # Использование pandas_ta, ta-lib
├── calculators.py              # Собственные реализации расчетов  
├── registry.py                 # Реестр индикаторов (заглушка)
└── macd.py                     # Специализированный MACD анализатор
```

#### Универсальный подход к индикаторам

BQuant поддерживает **три способа работы с индикаторами**:

1. **Готовые данные** - когда индикаторы уже рассчитаны и есть в файлах
2. **Библиотеки теханализа** - pandas-ta, ta-lib для стандартных индикаторов  
3. **Собственные реализации** - кастомные расчеты с полным контролем

#### `bquant/indicators/base.py`
```python
"""Базовые классы для индикаторов"""
from abc import ABC, abstractmethod
from enum import Enum
import pandas as pd

class IndicatorSource(Enum):
    """Источник данных индикатора"""
    PRELOADED = "preloaded"    # Готовые данные из файла
    LIBRARY = "library"        # Библиотеки (pandas_ta, ta-lib)
    CUSTOM = "custom"          # Собственная реализация

class BaseIndicator(ABC):
    def __init__(self, data: pd.DataFrame, source: IndicatorSource = IndicatorSource.LIBRARY):
        self.data = data
        self.source = source
        self.result = None
        self._config = {}
    
    @abstractmethod
    def calculate(self) -> pd.DataFrame:
        """Рассчитать индикатор согласно выбранному источнику"""
        pass
    
    def validate_data(self):
        required_cols = ['open', 'high', 'low', 'close']
        missing = [col for col in required_cols if col not in self.data.columns]
        if missing:
            raise ValueError(f"Отсутствуют колонки: {missing}")
    
    def get_result(self) -> pd.DataFrame:
        if self.result is None:
            self.result = self.calculate()
        return self.result

class IndicatorFactory:
    """Фабрика для создания индикаторов с автоопределением источника"""
    
    @staticmethod
    def create_indicator(indicator_name: str, data: pd.DataFrame, 
                        source: IndicatorSource = None, **params):
        """
        Создать индикатор с автоматическим выбором источника
        
        Args:
            indicator_name: Название индикатора (macd, rsi, etc.)
            data: Данные OHLCV
            source: Принудительный выбор источника (опционально)
            **params: Параметры индикатора
        """
        if source is None:
            source = IndicatorFactory._detect_best_source(indicator_name, data)
        
        indicator_class = IndicatorFactory._get_indicator_class(indicator_name)
        return indicator_class(data, source=source, **params)
    
    @staticmethod
    def _detect_best_source(indicator_name: str, data: pd.DataFrame) -> IndicatorSource:
        """Автоопределение лучшего источника для индикатора"""
        # Проверяем есть ли готовые данные
        expected_columns = IndicatorFactory._get_expected_columns(indicator_name)
        if all(col in data.columns for col in expected_columns):
            return IndicatorSource.PRELOADED
        
        # Проверяем доступность в библиотеках
        if IndicatorFactory._is_available_in_library(indicator_name):
            return IndicatorSource.LIBRARY
        
        # Используем собственную реализацию
        return IndicatorSource.CUSTOM
```

#### `bquant/indicators/loaders.py` - Готовые данные
```python
"""Загрузка готовых индикаторов из файлов данных"""
import pandas as pd
from .base import BaseIndicator, IndicatorSource

class PreloadedMACDIndicator(BaseIndicator):
    def __init__(self, data: pd.DataFrame, **params):
        super().__init__(data, source=IndicatorSource.PRELOADED)
        self.params = params
    
    def calculate(self) -> pd.DataFrame:
        """Использовать готовые данные MACD из файла"""
        result = self.data.copy()
        
        # Поиск колонок MACD в различных форматах
        macd_candidates = ['macd', 'MACD', 'Macd']
        signal_candidates = ['signal', 'Signal', 'SIGNAL', 'macd_signal']  
        hist_candidates = ['histogram', 'Histogram', 'macd_hist', 'hist']
        
        # Маппинг найденных колонок
        for candidates, target_name in [
            (macd_candidates, 'macd'),
            (signal_candidates, 'macd_signal'), 
            (hist_candidates, 'macd_hist')
        ]:
            found_col = next((col for col in candidates if col in self.data.columns), None)
            if found_col and found_col != target_name:
                result[target_name] = result[found_col]
        
        # Валидация наличия основных компонентов
        required_cols = ['macd', 'macd_signal', 'macd_hist']
        missing = [col for col in required_cols if col not in result.columns]
        if missing:
            raise ValueError(f"В готовых данных отсутствуют колонки MACD: {missing}")
        
        return result

def load_precomputed_indicators(data: pd.DataFrame) -> dict:
    """Обнаружить и загрузить все доступные готовые индикаторы"""
    indicators = {}
    
    # MACD
    macd_columns = ['macd', 'signal', 'histogram']
    if any(col.lower() in [c.lower() for c in data.columns] for col in macd_columns):
        indicators['macd'] = PreloadedMACDIndicator(data)
    
    # RSI  
    rsi_columns = ['rsi', 'RSI']
    if any(col in data.columns for col in rsi_columns):
        indicators['rsi'] = PreloadedRSIIndicator(data)
    
    # Можно добавить другие индикаторы...
    
    return indicators
```

#### `bquant/indicators/library.py` - Библиотеки теханализа
```python
"""Использование pandas_ta и ta-lib для расчета индикаторов"""
import pandas as pd
import pandas_ta as ta
from .base import BaseIndicator, IndicatorSource
from ..core.config import get_indicator_params

class LibraryMACDIndicator(BaseIndicator):
    def __init__(self, data: pd.DataFrame, **params):
        super().__init__(data, source=IndicatorSource.LIBRARY)
        self.params = get_indicator_params('macd', **params)
    
    def calculate(self) -> pd.DataFrame:
        """Рассчитать MACD через pandas_ta"""
        self.validate_data()
        
        result = self.data.copy()
        
        # Расчет через pandas_ta
        macd_result = ta.macd(
            result['close'], 
            fast=self.params['fast'],
            slow=self.params['slow'], 
            signal=self.params['signal']
        )
        
        if macd_result is not None and not macd_result.empty:
            # Стандартизация названий колонок
            for col in macd_result.columns:
                if col.startswith('MACD_'):
                    result['macd'] = macd_result[col]
                elif col.startswith('MACDs_'):
                    result['macd_signal'] = macd_result[col]
                elif col.startswith('MACDh_'):
                    result['macd_hist'] = macd_result[col]
        
        return result

class LibraryRSIIndicator(BaseIndicator):
    def __init__(self, data: pd.DataFrame, **params):
        super().__init__(data, source=IndicatorSource.LIBRARY)
        self.params = get_indicator_params('rsi', **params)
    
    def calculate(self) -> pd.DataFrame:
        """Рассчитать RSI через pandas_ta"""
        self.validate_data()
        
        result = self.data.copy()
        result['rsi'] = ta.rsi(result['close'], length=self.params['length'])
        return result

# Универсальная функция для библиотечных индикаторов
def calculate_library_indicator(indicator_name: str, data: pd.DataFrame, **params) -> pd.DataFrame:
    """Универсальный расчет индикатора через pandas_ta"""
    
    library_mapping = {
        'macd': lambda d, p: ta.macd(d['close'], **p),
        'rsi': lambda d, p: ta.rsi(d['close'], **p), 
        'bbands': lambda d, p: ta.bbands(d['close'], **p),
        'atr': lambda d, p: ta.atr(d['high'], d['low'], d['close'], **p),
        'sma': lambda d, p: ta.sma(d['close'], **p),
        'ema': lambda d, p: ta.ema(d['close'], **p)
    }
    
    if indicator_name not in library_mapping:
        raise ValueError(f"Индикатор {indicator_name} не поддерживается библиотекой")
    
    config_params = get_indicator_params(indicator_name, **params)
    result = data.copy()
    
    indicator_result = library_mapping[indicator_name](data, config_params)
    if indicator_result is not None:
        if isinstance(indicator_result, pd.Series):
            result[indicator_name] = indicator_result
        else:  # DataFrame
            for col in indicator_result.columns:
                result[col] = indicator_result[col]
    
    return result
```

#### `bquant/indicators/calculators.py` - Собственные реализации
**Источник:** Переносим из `research/macd_analysis.py` функцию `calculate_macd()`

**Что сохранить:**
- Собственную логику расчета MACD с конфигурацией
- Обработку ошибок и fallback логику
- Расчет ATR для нормализации

```python
"""Собственные реализации расчета индикаторов"""
import pandas as pd
import numpy as np
from .base import BaseIndicator, IndicatorSource
from ..core.config import get_indicator_params

class CustomMACDIndicator(BaseIndicator):
    def __init__(self, data: pd.DataFrame, **params):
        super().__init__(data, source=IndicatorSource.CUSTOM)
        self.params = get_indicator_params('macd', **params)
    
    def calculate(self) -> pd.DataFrame:
        """Собственная реализация расчета MACD"""
        # ПЕРЕНОСИМ из research/macd_analysis.py функцию calculate_macd()
        # Весь код остается как есть, с конфигурированием и обработкой ошибок
        pass

def calculate_custom_macd(data: pd.DataFrame, **overrides) -> pd.DataFrame:
    """
    ИСТОЧНИК: research/macd_analysis.py -> calculate_macd()
    
    Переносим полностью:
    - Получение параметров из конфигурации
    - Расчет EMA для быстрой и медленной линии  
    - Расчет сигнальной линии
    - Расчет гистограммы
    - Добавление ATR
    - Обработку ошибок
    """
    # Весь существующий код переносим сюда
    pass

def calculate_custom_rsi(data: pd.DataFrame, **overrides) -> pd.DataFrame:
    """Собственная реализация RSI"""
    params = get_indicator_params('rsi', **overrides)
    period = params['length']
    
    close = data['close']
    delta = close.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    result = data.copy()
    result['rsi'] = rsi
    return result
```

#### `bquant/indicators/macd.py` - Универсальный MACD анализатор
**Источник:** Полностью переносим из `research/macd_analysis.py`

**Что изменить:** Добавить поддержку всех трех источников данных

```python
"""
ИСТОЧНИК: research/macd_analysis.py
Специализированный MACD анализатор с поддержкой всех источников данных
"""

class MACDAnalyzer:
    def __init__(self, data: pd.DataFrame, source: IndicatorSource = None, **macd_params):
        self.data = data.copy()
        self.macd_params = macd_params
        self.source = source
        self._macd_data = None
        self._zones = None
    
    def calculate_macd(self) -> pd.DataFrame:
        """Рассчитать MACD используя оптимальный источник"""
        if self._macd_data is None:
            # Автоопределение или принудительный выбор источника
            if self.source is None:
                self.source = self._detect_optimal_source()
            
            if self.source == IndicatorSource.PRELOADED:
                indicator = PreloadedMACDIndicator(self.data, **self.macd_params)
            elif self.source == IndicatorSource.LIBRARY:
                indicator = LibraryMACDIndicator(self.data, **self.macd_params)  
            else:  # CUSTOM
                indicator = CustomMACDIndicator(self.data, **self.macd_params)
            
            self._macd_data = indicator.calculate()
        
        return self._macd_data
    
    def _detect_optimal_source(self) -> IndicatorSource:
        """Автоматически выбрать оптимальный источник"""
        # Логика выбора на основе доступных данных
        macd_cols = ['macd', 'signal', 'histogram']
        if any(col.lower() in [c.lower() for c in self.data.columns] for col in macd_cols):
            return IndicatorSource.PRELOADED
        
        # Проверяем доступность pandas_ta
        try:
            import pandas_ta as ta
            return IndicatorSource.LIBRARY
        except ImportError:
            return IndicatorSource.CUSTOM
    
    # ВСЕ ОСТАЛЬНЫЕ МЕТОДЫ ПЕРЕНОСИМ БЕЗ ИЗМЕНЕНИЙ:
    # - identify_zones()
    # - calculate_zone_features()  
    # - find_divergences()
    # - get_macd_statistics()
    # - cluster_zone_shapes()
```

#### Пример использования универсального подхода:

```python
from bquant.indicators import MACDAnalyzer, IndicatorSource
from bquant.indicators import IndicatorFactory

# Способ 1: Автоматический выбор источника
analyzer = MACDAnalyzer(data)  # Сам определит оптимальный источник

# Способ 2: Принудительный выбор источника
analyzer_preloaded = MACDAnalyzer(data, source=IndicatorSource.PRELOADED)
analyzer_library = MACDAnalyzer(data, source=IndicatorSource.LIBRARY) 
analyzer_custom = MACDAnalyzer(data, source=IndicatorSource.CUSTOM)

# Способ 3: Через фабрику
indicator = IndicatorFactory.create_indicator('macd', data, fast=8, slow=21)

# Все способы дают одинаковый интерфейс для дальнейшего анализа
zones = analyzer.identify_zones()
features = [analyzer.calculate_zone_features(zone) for zone in zones]
```

### 🔬 `bquant/analysis/` - Аналитические модули

```python
bquant/analysis/
├── __init__.py                 # Экспорт аналитических функций
├── technical/                  # Технический анализ индикаторов
│   ├── __init__.py
│   ├── trends.py              # Анализ трендов (заглушка)
│   ├── momentum.py            # Анализ моментума (заглушка)
│   └── oscillators.py         # Анализ осцилляторов (заглушка)
├── chart/                     # Графический анализ (заглушки)
│   ├── __init__.py
│   ├── patterns.py           # Графические паттерны
│   └── support_resistance.py # Уровни поддержки/сопротивления
├── candlestick/              # Свечной анализ (заглушки)
│   ├── __init__.py
│   └── patterns.py           # Свечные паттерны
├── timeseries/               # 🆕 Анализ временных рядов
│   ├── __init__.py
│   ├── stationarity.py       # Тесты стационарности (заглушка)
│   ├── seasonality.py        # Анализ сезонности (заглушка)
│   ├── autocorrelation.py    # Автокорреляция (заглушка)
│   └── decomposition.py      # Декомпозиция рядов (заглушка)
├── statistical/              # Статистический анализ
│   ├── __init__.py
│   ├── distributions.py      # Анализ распределений (заглушка)
│   ├── hypothesis_testing.py # Тестирование гипотез
│   └── correlations.py       # Корреляционный анализ (заглушка)
└── zones/                    # Анализ зон
    ├── __init__.py
    ├── zone_features.py      # Признаки зон
    └── sequence_analysis.py  # Анализ последовательностей
```

#### `bquant/analysis/statistical/hypothesis_testing.py`
**Источник:** Полностью переносим из `research/hypothesis_testing.py`

**Что сохранить:** Все функции тестирования гипотез без изменений

#### `bquant/analysis/zones/zone_features.py`
**Источник:** Переносим из `research/macd_analysis.py` функции:
- `analyze_zones_distribution()`
- `create_zone_sequence_analysis()`

### 🤖 `bquant/ml/` - Машинное обучение (заглушки)

```python
bquant/ml/
├── __init__.py                 # Экспорт ML компонентов (заглушки)
├── features/                   # Работа с признаками (заглушки)
│   └── __init__.py
├── models/                     # ML модели (заглушки)
│   └── __init__.py
├── training/                   # Обучение моделей (заглушки)  
│   └── __init__.py
└── evaluation/                 # Оценка моделей (заглушки)
    └── __init__.py
```

#### Интеграция с основным пакетом
```python
# bquant/ml/__init__.py
"""
ML модуль BQuant - в разработке

Планируемая функциональность:
- Извлечение признаков из зон
- Классификация и предсказание зон
- Бэктестинг стратегий
"""

def extract_zone_features(zones):
    """Заглушка для извлечения ML признаков"""
    raise NotImplementedError("ML модуль в разработке")

def classify_zones(features):
    """Заглушка для классификации зон"""
    raise NotImplementedError("ML модуль в разработке")
```

### 📈 `bquant/visualization/` - Визуализация

```python
bquant/visualization/
├── __init__.py                 # Экспорт функций визуализации
├── charts.py                   # Основные графики
├── zones.py                    # Визуализация зон
├── statistical.py              # Статистические графики (заглушка)
└── themes.py                   # Темы и стили (заглушка)
```

#### `bquant/visualization/charts.py`
**Новый модуль** - создать класс `FinancialCharts` с методами:
```python
class FinancialCharts:
    def __init__(self, style='seaborn', figsize=(12, 8)):
        self.setup_style()
    
    def plot_ohlcv(self, data, title=None, show_volume=True):
        """OHLCV график"""
        pass
    
    def plot_macd_with_zones(self, data, zones, title=None):
        """MACD с зонами"""  
        pass
    
    def plot_zone_features_distribution(self, features):
        """Распределения признаков зон"""
        pass
```

---

## 🧪 Исследовательская структура

### `research/notebooks/`
```python
research/notebooks/
├── 01_data_exploration.ipynb      # Исследование данных
├── 02_macd_zones_analysis.ipynb   # Анализ зон MACD  
├── 03_hypothesis_testing.ipynb    # Тестирование гипотез
├── 04_pattern_recognition.ipynb   # Распознавание паттернов (заглушка)
└── 05_timeseries_analysis.ipynb   # Анализ временных рядов (заглушка)
```

### `research/methodology/`
**Источник:** Переносим `research/macd_research.md` без изменений

---

## 🚀 Скрипты автоматизации

### `scripts/analysis/`
```python
scripts/analysis/
├── run_macd_analysis.py     # Полный MACD анализ инструмента
├── test_hypotheses.py      # Запуск тестов гипотез
├── batch_analysis.py       # Анализ множества инструментов  
└── generate_report.py      # Генерация отчета (заглушка)
```

#### Пример `scripts/analysis/run_macd_analysis.py`
```python
#!/usr/bin/env python3
"""
Полный анализ MACD зон для инструмента
"""
import sys
sys.path.append('.')

from bquant.data import load_symbol_data
from bquant.indicators import MACDAnalyzer  
from bquant.analysis.statistical import run_all_hypothesis_tests
from bquant.visualization import FinancialCharts

def main(symbol='XAUUSD', timeframe='1h'):
    print(f"🔍 Анализ {symbol} {timeframe}")
    
    # Загрузка данных
    data = load_symbol_data(symbol, timeframe)
    print(f"📊 Загружено {len(data)} записей")
    
    # MACD анализ
    analyzer = MACDAnalyzer(data, fast=8, slow=21)
    zones = analyzer.identify_zones()
    features = [analyzer.calculate_zone_features(zone) for zone in zones]
    
    print(f"🎯 Найдено {len(zones)} зон")
    
    # Статистические тесты
    hypothesis_results = run_all_hypothesis_tests(features)
    significant = hypothesis_results['summary']['significant_tests']
    print(f"📈 Значимых тестов: {significant}")
    
    # Визуализация
    charts = FinancialCharts()
    fig = charts.plot_macd_with_zones(analyzer.calculate_macd(), zones)
    fig.savefig(f'results/{symbol}_{timeframe}_analysis.png')
    print(f"💾 График сохранен")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
```

---

## ⚙️ Конфигурация проекта

### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bquant"
version = "0.0.0"
description = "Quantitative research toolkit"
authors = [{name = "kogriv", email = "kogriv@gmail.com"}]
readme = "README.md"
requires-python = ">=3.13"
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Financial and Insurance Industry",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "pandas==2.3.1",
    "numpy==2.3.2",
    "matplotlib==3.10.5",
    "seaborn==0.13.2",
    "pandas-ta==0.3.14b0",
    "statsmodels==0.14.5",
    "scipy==1.16.1",
    "scikit-learn==1.7.1",
    "plotly==6.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "jupyter==1.1.1",
]
notebooks = [
    "jupyter==1.1.1",
    "plotly==6.3.0",
]

[project.scripts]
bquant-analyze = "scripts.analysis.run_macd_analysis:main"
bquant-batch = "scripts.analysis.batch_analysis:main"

[tool.setuptools.packages.find]
where = ["."]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.black]
line-length = 88
target-version = ['py313']
```

---

## 🎯 Архитектурные принципы

### 1. **Конфигурация как код**
Все настройки в `bquant/core/config.py` с возможностью переопределения

### 2. **Простота импортов**
```python
# Простая установка
pip install -e .

# Простые импорты
from bquant.data import load_symbol_data
from bquant.indicators import MACDAnalyzer
from bquant.analysis.statistical import run_all_hypothesis_tests
```

### 3. **Использование готовых решений**
- **Индикаторы:** pandas_ta, ta-lib или готовые данные
- **ML:** scikit-learn как основа для будущего развития
- **Визуализация:** matplotlib + seaborn + plotly

### 4. **Поэтапное развитие**
- **Этап 1:** Основная функциональность (данные, MACD анализ как первый кейс, статистика)
- **Этап 2:** Расширенная визуализация, временные ряды, другие индикаторы
- **Этап 3:** Полноценное ML, графические паттерны, автоматизация

---

## 🏛️ Архитектурные паттерны

BQuant построен на основе проверенных архитектурных паттернов, обеспечивающих гибкость, расширяемость и maintainability кода.

### 1. **Паттерн "Конфигурация как код" (Configuration as Code)**

Центральное место всех настроек в `bquant/core/config.py`:

```python
# Единый источник конфигурации
DEFAULT_INDICATORS = {
    'macd': {'fast': 12, 'slow': 26, 'signal': 9},
    'rsi': {'length': 14}
}

# Переопределение параметров
def get_indicator_params(indicator: str, **overrides) -> Dict[str, Any]:
    params = DEFAULT_INDICATORS[indicator].copy()
    params.update(overrides)  # Позволяет кастомизировать
    return params

# Использование
macd_params = get_indicator_params('macd', fast=8, slow=21)  # Кастомные параметры
```

**Преимущества:**
- Единое место для всех настроек
- Легкое переопределение параметров
- Версионирование конфигураций
- Валидация параметров

### 2. **Паттерн "Стратегия" (Strategy Pattern)**

Взаимозаменяемые алгоритмы анализа через базовые классы:

```python
# Базовый интерфейс
class BaseIndicator(ABC):
    @abstractmethod
    def calculate(self) -> pd.DataFrame:
        pass

# Конкретные реализации
class MACDIndicator(BaseIndicator):
    def calculate(self) -> pd.DataFrame:
        return ta.macd(self.data['close'], **self.params)

class RSIIndicator(BaseIndicator):
    def calculate(self) -> pd.DataFrame:
        return ta.rsi(self.data['close'], **self.params)

# Клиентский код не зависит от конкретной реализации
def analyze_indicator(indicator: BaseIndicator):
    return indicator.calculate()
```

**Преимущества:**
- Легкое добавление новых индикаторов
- Единообразный интерфейс
- Тестируемость каждой стратегии отдельно

### 3. **Паттерн "Фабрика" (Factory Pattern)**

Создание объектов через фабричные функции с автоматической конфигурацией:

```python
def create_macd_analyzer(data: pd.DataFrame, **custom_params) -> MACDAnalyzer:
    """Фабрика для создания MACD анализатора"""
    # Автоматически применяем конфигурацию
    config_params = get_indicator_params('macd', **custom_params)
    return MACDAnalyzer(data, **config_params)

# Использование
analyzer = create_macd_analyzer(data, fast=8)  # Просто и понятно
```

**Преимущества:**
- Инкапсуляция логики создания
- Автоматическое применение конфигурации
- Упрощение клиентского кода

### 4. **Паттерн "Адаптер" (Adapter Pattern)**

Унификация работы с разными источниками данных:

```python
class DataSourceAdapter(ABC):
    @abstractmethod
    def load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        pass

class TradingViewAdapter(DataSourceAdapter):
    def load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        # Специфическая логика для TradingView
        file_pattern = "OANDA_{symbol}, {timeframe}.csv"
        return self._load_csv(file_pattern.format(symbol=symbol, timeframe=timeframe))

class MetaTraderAdapter(DataSourceAdapter):
    def load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        # Специфическая логика для MetaTrader
        file_pattern = "{symbol}{timeframe}.csv"
        return self._load_csv(file_pattern.format(symbol=symbol, timeframe=timeframe))

# Единый интерфейс загрузки
def load_symbol_data(symbol: str, timeframe: str, source: str = 'tradingview'):
    adapter = get_adapter(source)  # Фабрика адаптеров
    return adapter.load_data(symbol, timeframe)
```

**Преимущества:**
- Единый интерфейс для разных источников
- Легкое добавление новых источников данных
- Изоляция специфической логики

---

## 🔧 Возможности расширения

### 1. **Новые источники данных**
```python
# В bquant/core/config.py добавить:
DATA_FILE_PATTERNS['new_source'] = {
    'default': '{symbol}_{timeframe}.csv'
}
```

### 2. **Новые индикаторы**
```python
# В bquant/indicators/calculators.py добавить:
def calculate_custom_indicator(data, **params):
    return ta.custom_indicator(data['close'], **params)
```

### 3. **ML модули (будущее)**
Заглушки готовы для развития в:
- Классификация зон
- Предсказание движений
- Автоматические стратегии

---

## 📚 Примеры использования

### Базовый анализ
```python
from bquant.data import load_symbol_data
from bquant.indicators import MACDAnalyzer

# Загрузка и анализ
data = load_symbol_data('XAUUSD', '1h')
analyzer = MACDAnalyzer(data, fast=8, slow=21)
zones = analyzer.identify_zones()

print(f"Найдено {len(zones)} зон")
```

### Исследование в ноутбуке
```python
# В Jupyter ноутбуке
from bquant.visualization import FinancialCharts
from bquant.analysis.statistical import run_all_hypothesis_tests

# Визуализация
charts = FinancialCharts()
fig = charts.plot_macd_with_zones(analyzer.calculate_macd(), zones)

# Статистические тесты
features = [analyzer.calculate_zone_features(zone) for zone in zones]
hypothesis_results = run_all_hypothesis_tests(features)
```

### Командная строка
```bash
# Установка в режиме разработки
pip install -e .

# Установка с дополнительными зависимостями
pip install -e .[dev,notebooks]

# Анализ инструмента
bquant-analyze EURUSD

# Пакетный анализ
bquant-batch XAUUSD EURUSD GBPUSD
```

---

**BQuant** - это практичный, расширяемый инструментарий для количественного исследования финансовых рынков. Начинаем с MACD анализа как первого применения, но архитектура рассчитана на комплексное исследование всех аспектов рыночного поведения - от технических индикаторов до сложных паттернов и машинного обучения.