# Интеграция системы индикаторов BQuant с универсальным Zone Analyzer

**Дополнение к:** `zonan.md`  
**Дата:** 2025-10-17  
**Цель:** Показать как существующая инфраструктура индикаторов интегрируется с zone detection

---

## Существующая инфраструктура индикаторов BQuant

### Компоненты системы

```
bquant/indicators/
├── base.py                    # Базовая архитектура
│   ├── BaseIndicator          # Абстрактный базовый класс
│   ├── PreloadedIndicator     # Извлечение готовых данных
│   ├── CustomIndicator        # Встроенные алгоритмы
│   ├── LibraryIndicator       # Обертки над внешними библиотеками
│   ├── IndicatorFactory       # Фабрика создания индикаторов
│   ├── IndicatorResult        # Результат расчета
│   └── IndicatorConfig        # Конфигурация индикатора
│
├── custom/                    # Встроенные реализации
│   ├── sma.py                # SimpleMovingAverage
│   ├── ema.py                # ExponentialMovingAverage
│   ├── rsi.py                # RelativeStrengthIndex
│   ├── macd.py               # MACD
│   └── bollinger.py          # BollingerBands
│
├── library/                   # Внешние библиотеки
│   ├── manager.py            # LibraryManager
│   ├── pandas_ta.py          # PandasTALoader
│   └── talib.py              # TALibLoader
│
└── preloaded/                 # Готовые данные
    └── macd.py               # MACDPreloadedIndicator
```

### API создания индикаторов

```python
# 1. Через IndicatorFactory (основной способ)
from bquant.indicators import IndicatorFactory

# PRELOADED - извлечь готовые данные
indicator = IndicatorFactory.create('preloaded', 'macd')
result = indicator.calculate(df)  # Извлекает колонки 'macd', 'macd_signal', 'macd_hist'

# CUSTOM - встроенные алгоритмы
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26, signal=9)
result = indicator.calculate(df)  # Вычисляет MACD

# LIBRARY - внешние библиотеки
indicator = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
result = indicator.calculate(df)  # Использует pandas_ta.rsi()

# 2. Через LibraryManager (для библиотек)
from bquant.indicators import LibraryManager

indicator = LibraryManager.create_indicator('pandas_ta', 'zigzag', legs=10)
result = indicator.calculate(df)

# 3. Прямое создание класса
from bquant.indicators import MACD

indicator = MACD(fast=12, slow=26, signal=9)
result = indicator.calculate(df)
```

### IndicatorResult структура

```python
@dataclass
class IndicatorResult:
    name: str               # Название индикатора
    data: pd.DataFrame      # Результаты (одна или несколько колонок)
    config: IndicatorConfig # Конфигурация расчета
    metadata: Dict[str, Any] # Метаданные (source, method, etc.)
```

---

## Интеграция с Zone Detection архитектурой

### Проблема в текущем предложении

**В `zonan.md` я показал:**
```python
class MACDZoneAnalyzer:
    def calculate_indicator(self, df):
        # Ручной расчет MACD
        macd_data = calculate_macd(df, fast=..., slow=..., signal=...)
        # ... ручное добавление колонок
```

**Проблема:**
- ❌ Не использует `IndicatorFactory`
- ❌ Не использует систему PRELOADED/CUSTOM/LIBRARY
- ❌ Дублирует существующую инфраструктуру
- ❌ Игнорирует 3 способа получения индикаторов

### Правильная интеграция

#### Вариант 1: Через конфигурацию индикатора

```python
# bquant/indicators/analyzers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

from bquant.indicators import IndicatorFactory, IndicatorResult
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer


@dataclass
class IndicatorZoneConfig:
    """Конфигурация индикатора для зонального анализа."""
    
    # Конфигурация расчета индикатора
    indicator_source: str          # 'preloaded', 'custom', 'pandas_ta', 'talib'
    indicator_name: str            # 'macd', 'ao', 'rsi', 'bbands', ...
    indicator_params: Dict[str, Any] = field(default_factory=dict)
    
    # Конфигурация определения зон
    zone_detection: ZoneDetectionConfig = None


class BaseIndicatorZoneAnalyzer(ABC):
    """
    Базовый класс для анализаторов зон индикаторов.
    
    ИНТЕГРАЦИЯ с IndicatorFactory!
    """
    
    def __init__(self,
                 indicator_config: IndicatorZoneConfig,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            indicator_config: Конфигурация индикатора и зон
            zone_analyzer: Универсальный анализатор (DI)
        """
        self.indicator_config = indicator_config
        self.zone_config = indicator_config.zone_detection
        
        # Создаем индикатор через IndicatorFactory!
        self.indicator = IndicatorFactory.create(
            source=indicator_config.indicator_source,
            indicator=indicator_config.indicator_name,
            **indicator_config.indicator_params
        )
        
        # Создаем детектор зон
        from bquant.analysis.zones.detection import ZoneDetectionRegistry
        self.zone_detector = ZoneDetectionRegistry.get(
            self.zone_config.strategy_name
        )
        
        # Универсальный анализатор
        self.analyzer = zone_analyzer or UniversalZoneAnalyzer()
    
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет индикатора через IndicatorFactory.
        
        ИСПОЛЬЗУЕТ существующую инфраструктуру!
        """
        # Вычисляем через фабрику
        result: IndicatorResult = self.indicator.calculate(df)
        
        # Объединяем исходные данные с результатами индикатора
        df_with_indicator = df.copy()
        for col in result.data.columns:
            df_with_indicator[col] = result.data[col]
        
        # Добавляем дополнительные индикаторы (ATR для нормализации)
        if 'atr' not in df_with_indicator.columns:
            from bquant.data.processor import calculate_derived_indicators
            derived = calculate_derived_indicators(df_with_indicator)
            if 'atr' in derived.columns:
                df_with_indicator['atr'] = derived['atr']
        
        return df_with_indicator
    
    def analyze(self, df: pd.DataFrame, **kwargs):
        """
        Полный анализ зон индикатора.
        
        3 шага: calculate_indicator → detect_zones → analyze_zones
        """
        # 1. Расчет индикатора (через IndicatorFactory!)
        df_with_indicator = self.calculate_indicator(df)
        
        # 2. Определение зон (делегирование)
        zones = self.zone_detector.detect_zones(
            df_with_indicator, 
            self.zone_config
        )
        
        # 3. Анализ зон (делегирование)
        return self.analyzer.analyze_zones(
            zones=zones,
            data=df_with_indicator,
            **kwargs
        )
```

#### Примеры использования

**MACD через PRELOADED:**
```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='preloaded',      # ← Используем готовые данные!
        indicator_name='macd',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(
            min_duration=2,
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)  # df уже содержит 'macd', 'macd_signal', 'macd_hist'
```

**MACD через CUSTOM:**
```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='custom',         # ← Вычисляем через встроенный алгоритм
        indicator_name='macd',
        indicator_params={'fast': 12, 'slow': 26, 'signal': 9},
        zone_detection=ZoneDetectionConfig(
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)  # df с OHLCV, MACD будет рассчитан автоматически
```

**AO через LIBRARY (pandas_ta):**
```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='pandas_ta',      # ← Используем внешнюю библиотеку!
        indicator_name='ao',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(
            rules={'indicator_col': 'AO_5_34'},  # pandas_ta использует такое имя
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

**RSI через LIBRARY с 3 типами зон:**
```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='talib',          # ← Используем TA-Lib
        indicator_name='rsi',
        indicator_params={'length': 14},
        zone_detection=ZoneDetectionConfig(
            min_duration=3,
            zone_types=['overbought', 'neutral', 'oversold'],
            rules={
                'indicator_col': 'RSI_14',
                'upper_threshold': 70,
                'lower_threshold': 30
            },
            strategy_name='threshold'
        )
    )
)

result = analyzer.analyze(df)
print(f"Overbought zones: {sum(1 for z in result.zones if z.type == 'overbought')}")
```

---

## Специализированные фасады с поддержкой всех источников

### MACD Zone Analyzer (полная версия)

```python
# bquant/indicators/analyzers/macd.py

from typing import Dict, Any, Optional, Literal
import pandas as pd

from ...core.config import get_indicator_params
from ...core.logging_config import get_logger
from ...indicators import IndicatorFactory
from ...analysis.zones.detection import ZoneDetectionConfig
from ...analysis.zones import UniversalZoneAnalyzer
from .base import IndicatorZoneConfig, BaseIndicatorZoneAnalyzer

logger = get_logger(__name__)


class MACDZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    """
    Фасад для MACD с поддержкой всех источников индикаторов.
    
    Поддерживает:
    - PRELOADED: Извлечение готовых MACD данных из DataFrame
    - CUSTOM: Встроенный алгоритм расчета MACD
    - LIBRARY: pandas_ta.macd(), talib.MACD()
    """
    
    def __init__(self,
                 macd_params: Optional[Dict[str, Any]] = None,
                 indicator_source: Literal['preloaded', 'custom', 'pandas_ta', 'talib'] = 'custom',
                 zone_detection_config: Optional[ZoneDetectionConfig] = None,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            macd_params: Параметры MACD (fast, slow, signal)
            indicator_source: Источник индикатора ('preloaded', 'custom', 'pandas_ta', 'talib')
            zone_detection_config: Конфигурация определения зон
            zone_analyzer: Универсальный анализатор (DI)
        """
        macd_params = macd_params or get_indicator_params('macd')
        zone_detection_config = zone_detection_config or self._get_default_zone_config()
        
        # Создаем конфигурацию индикатора
        indicator_config = IndicatorZoneConfig(
            indicator_source=indicator_source,
            indicator_name='macd',
            indicator_params=macd_params,
            zone_detection=zone_detection_config
        )
        
        super().__init__(
            indicator_config=indicator_config,
            zone_analyzer=zone_analyzer
        )
        
        logger.info(f"MACDZoneAnalyzer initialized with source={indicator_source}, params={macd_params}")
    
    @staticmethod
    def _get_default_zone_config() -> ZoneDetectionConfig:
        """Дефолтная конфигурация зон для MACD."""
        return ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    
    @classmethod
    def from_preloaded(cls, 
                       zone_detection_config: Optional[ZoneDetectionConfig] = None,
                       zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Создать анализатор для PRELOADED MACD данных.
        
        Использование:
            analyzer = MACDZoneAnalyzer.from_preloaded()
            result = analyzer.analyze(df)  # df уже содержит MACD колонки
        """
        return cls(
            macd_params={},
            indicator_source='preloaded',
            zone_detection_config=zone_detection_config,
            zone_analyzer=zone_analyzer
        )
    
    @classmethod
    def from_custom(cls,
                    fast: int = 12,
                    slow: int = 26,
                    signal: int = 9,
                    zone_detection_config: Optional[ZoneDetectionConfig] = None,
                    zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Создать анализатор с встроенным расчетом MACD.
        
        Использование:
            analyzer = MACDZoneAnalyzer.from_custom(fast=10, slow=24, signal=8)
            result = analyzer.analyze(df)  # MACD будет рассчитан автоматически
        """
        return cls(
            macd_params={'fast': fast, 'slow': slow, 'signal': signal},
            indicator_source='custom',
            zone_detection_config=zone_detection_config,
            zone_analyzer=zone_analyzer
        )
    
    @classmethod
    def from_pandas_ta(cls,
                      fast: int = 12,
                      slow: int = 26,
                      signal: int = 9,
                      zone_detection_config: Optional[ZoneDetectionConfig] = None,
                      zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Создать анализатор через pandas_ta.
        
        Использование:
            analyzer = MACDZoneAnalyzer.from_pandas_ta()
            result = analyzer.analyze(df)  # Использует pandas_ta.macd()
        """
        return cls(
            macd_params={'fast': fast, 'slow': slow, 'signal': signal},
            indicator_source='pandas_ta',
            zone_detection_config=zone_detection_config,
            zone_analyzer=zone_analyzer
        )


# Backward compatibility
def create_macd_analyzer(
    macd_params: Optional[Dict] = None,
    zone_params: Optional[Dict] = None,
    indicator_source: str = 'custom'
) -> MACDZoneAnalyzer:
    """Создать MACD анализатор (backward compatibility)."""
    zone_config = None
    if zone_params:
        zone_config = ZoneDetectionConfig(
            min_duration=zone_params.get('min_duration', 2),
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    
    return MACDZoneAnalyzer(
        macd_params=macd_params,
        indicator_source=indicator_source,
        zone_detection_config=zone_config
    )
```

---

## Универсальный анализатор для любого индикатора

### UniversalIndicatorZoneAnalyzer

```python
# bquant/indicators/analyzers/universal.py

class UniversalIndicatorZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    """
    Универсальный анализатор для ЛЮБОГО индикатора.
    
    Поддерживает все источники через IndicatorFactory.
    """
    
    def __init__(self, indicator_config: IndicatorZoneConfig,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            indicator_config: Полная конфигурация индикатора и зон
            zone_analyzer: Универсальный анализатор (DI)
        """
        super().__init__(
            indicator_config=indicator_config,
            zone_analyzer=zone_analyzer
        )
    
    # calculate_indicator() и analyze() наследуются от базового класса
```

### Примеры для разных индикаторов

#### Пример 1: AO через pandas_ta

```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='pandas_ta',      # ← Внешняя библиотека
        indicator_name='ao',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(
            rules={'indicator_col': 'AO_5_34'},  # pandas_ta column name
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

#### Пример 2: Bollinger через custom

```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='custom',         # ← Встроенный алгоритм
        indicator_name='bbands',
        indicator_params={'length': 20, 'std': 2.0},
        zone_detection=ZoneDetectionConfig(
            rules={
                'line1_col': 'close',
                'line2_col': 'BBM_20_2.0'  # Bollinger Middle
            },
            strategy_name='line_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

#### Пример 3: RSI через talib

```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='talib',          # ← TA-Lib
        indicator_name='rsi',
        indicator_params={'timeperiod': 14},
        zone_detection=ZoneDetectionConfig(
            zone_types=['overbought', 'neutral', 'oversold'],
            rules={
                'indicator_col': 'RSI',
                'upper_threshold': 70,
                'lower_threshold': 30
            },
            strategy_name='threshold'
        )
    )
)

result = analyzer.analyze(df)
```

#### Пример 4: Кастомный индикатор через callable

```python
# Сначала регистрируем свой индикатор
from bquant.indicators import IndicatorFactory, CustomIndicator

class MyCustomIndicator(CustomIndicator):
    def calculate(self, data, **kwargs):
        # Ваш алгоритм
        result_data = pd.DataFrame({
            'my_indicator': data['close'].rolling(10).mean() - data['close'].rolling(30).mean()
        })
        return IndicatorResult(
            name='my_custom',
            data=result_data,
            config=self.config
        )

IndicatorFactory.register_indicator('my_custom', MyCustomIndicator)

# Используем
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='custom',
        indicator_name='my_custom',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(
            rules={'indicator_col': 'my_indicator'},
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

---

## Поддержка PRELOADED данных

### Проблема

Когда данные уже содержат индикаторы (загружены из файла с MACD колонками), не нужно их пересчитывать.

### Решение

**1. Определение источника автоматически:**

```python
class SmartIndicatorZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    """Анализатор с автоопределением источника индикатора."""
    
    def __init__(self,
                 indicator_name: str,
                 indicator_params: Dict = None,
                 required_columns: List[str] = None,
                 zone_detection_config: ZoneDetectionConfig = None,
                 zone_analyzer: UniversalZoneAnalyzer = None):
        """
        Args:
            indicator_name: Название индикатора
            indicator_params: Параметры (для custom/library)
            required_columns: Колонки которые должны быть для PRELOADED
            zone_detection_config: Конфигурация зон
            zone_analyzer: Анализатор (DI)
        """
        self.indicator_name = indicator_name
        self.indicator_params = indicator_params or {}
        self.required_columns = required_columns or []
        
        # Создаем конфигурацию (источник определим позже)
        indicator_config = IndicatorZoneConfig(
            indicator_source='custom',  # по умолчанию
            indicator_name=indicator_name,
            indicator_params=self.indicator_params,
            zone_detection=zone_detection_config
        )
        
        super().__init__(indicator_config, zone_analyzer)
    
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Умный расчет индикатора.
        
        Автоматически определяет:
        - Если нужные колонки есть → PRELOADED
        - Если нет → CUSTOM или LIBRARY
        """
        # Проверяем наличие PRELOADED данных
        has_preloaded = all(col in df.columns for col in self.required_columns)
        
        if has_preloaded:
            logger.info(f"Using PRELOADED {self.indicator_name} data")
            # Создаем PRELOADED индикатор
            indicator = IndicatorFactory.create('preloaded', self.indicator_name)
            result = indicator.calculate(df)
        else:
            logger.info(f"Calculating {self.indicator_name} using {self.indicator_config.indicator_source}")
            # Используем заданный источник
            result = self.indicator.calculate(df)
        
        # Объединяем
        df_with_indicator = df.copy()
        for col in result.data.columns:
            df_with_indicator[col] = result.data[col]
        
        return df_with_indicator
```

**Использование:**
```python
analyzer = SmartIndicatorZoneAnalyzer(
    indicator_name='macd',
    indicator_params={'fast': 12, 'slow': 26, 'signal': 9},
    required_columns=['macd', 'macd_signal', 'macd_hist'],  # для PRELOADED
    zone_detection_config=ZoneDetectionConfig(
        rules={'indicator_col': 'macd'},
        strategy_name='zero_crossing'
    )
)

# Если df содержит MACD - использует PRELOADED
# Если нет - вычисляет через CUSTOM
result = analyzer.analyze(df)
```

---

## Обновленная архитектура (с учетом IndicatorFactory)

### Поток данных

```
1. RAW DATA (pd.DataFrame)
   ├─ OHLCV columns
   └─ Опционально: preloaded indicator columns

2. IndicatorFactory.create(source, indicator, **params)
   ↓
   BaseIndicator (PreloadedIndicator | CustomIndicator | LibraryIndicator)
   ↓
   indicator.calculate(df)
   ↓
   IndicatorResult
   ├─ name: 'macd'
   ├─ data: DataFrame with indicator columns
   ├─ config: IndicatorConfig
   └─ metadata: {'source': 'custom', ...}

3. BaseIndicatorZoneAnalyzer.calculate_indicator()
   ↓
   ENRICHED DATA (pd.DataFrame)
   ├─ OHLCV columns
   ├─ Indicator columns (macd, macd_signal, macd_hist)
   └─ atr (добавляется для нормализации)

4. ZoneDetectionStrategy.detect_zones(data, config)
   ↓
   List[ZoneInfo]

5. UniversalZoneAnalyzer.analyze_zones(zones, data)
   ↓
   ZoneAnalysisResult
```

### Обновленная структура директорий

```
bquant/
├── indicators/
│   ├── base.py                    # СУЩЕСТВУЕТ
│   │   ├── BaseIndicator
│   │   ├── PreloadedIndicator
│   │   ├── CustomIndicator
│   │   ├── LibraryIndicator
│   │   ├── IndicatorFactory       # ← ИСПОЛЬЗУЕМ!
│   │   └── IndicatorResult
│   │
│   ├── custom/                     # СУЩЕСТВУЕТ - встроенные индикаторы
│   ├── library/                    # СУЩЕСТВУЕТ - внешние библиотеки
│   │   └── manager.py (LibraryManager)  # ← ИСПОЛЬЗУЕМ!
│   ├── preloaded/                  # СУЩЕСТВУЕТ - готовые данные
│   │
│   └── analyzers/                  # НОВОЕ - фасады для zone analysis
│       ├── __init__.py
│       ├── base.py                # BaseIndicatorZoneAnalyzer + IndicatorZoneConfig
│       ├── universal.py           # UniversalIndicatorZoneAnalyzer
│       ├── macd.py                # MACDZoneAnalyzer (использует IndicatorFactory)
│       ├── ao.py                  # AOZoneAnalyzer (использует IndicatorFactory)
│       └── smart.py               # SmartIndicatorZoneAnalyzer (auto-detect)
│
└── analysis/
    └── zones/
        ├── models.py              # ZoneInfo, ZoneAnalysisResult
        ├── detection/             # Стратегии детекции зон
        ├── analyzer.py            # UniversalZoneAnalyzer
        ├── zone_features.py       # Извлечение признаков
        └── strategies/            # Стратегии метрик (swing, shape, etc.)
```

---

## Ключевые преимущества интеграции

### 1. Использование существующей инфраструктуры

- ✅ **IndicatorFactory** - единый интерфейс для всех источников
- ✅ **LibraryManager** - управление pandas_ta, talib
- ✅ **IndicatorResult** - стандартизированный результат
- ✅ Нет дублирования логики расчета индикаторов

### 2. Гибкость источников

```python
# Один и тот же фасад, разные источники:

# PRELOADED (данные уже есть)
analyzer = MACDZoneAnalyzer.from_preloaded()

# CUSTOM (встроенный алгоритм)
analyzer = MACDZoneAnalyzer.from_custom(fast=10, slow=24)

# LIBRARY (pandas_ta)
analyzer = MACDZoneAnalyzer.from_pandas_ta(fast=10, slow=24)

# Все работают одинаково!
result = analyzer.analyze(df)
```

### 3. Расширяемость

```python
# Новый индикатор = регистрация + фасад

# 1. Регистрируем индикатор (если еще не зарегистрирован)
IndicatorFactory.register_indicator('my_indicator', MyIndicatorClass)

# 2. Используем универсальный фасад
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='custom',
        indicator_name='my_indicator',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(...)
    )
)

# Готово!
result = analyzer.analyze(df)
```

### 4. Совместимость с текущим кодом

Текущий код в `MACDZoneAnalyzer.calculate_macd_with_atr()` использует:
```python
macd_data = calculate_macd(df, fast=..., slow=..., signal=...)
```

Новый код будет использовать:
```python
indicator = IndicatorFactory.create('custom', 'macd', fast=..., slow=..., signal=...)
result = indicator.calculate(df)
```

**Результат идентичен** - обе функции используют одну и ту же реализацию!

---

## Рекомендации по реализации

### Обновить `zonan.md`

1. **Добавить секцию "Интеграция с IndicatorFactory"** перед Слоем 3
2. **Обновить `BaseIndicatorZoneAnalyzer.calculate_indicator()`** для использования IndicatorFactory
3. **Добавить `IndicatorZoneConfig`** dataclass
4. **Показать примеры всех 3 источников** (preloaded/custom/library)

### Обновить план миграции

**Этап 0:** Добавить задачу:
```
[ ] Определить стратегию интеграции с IndicatorFactory
    - Использовать IndicatorFactory.create() вместо прямых вызовов
    - Поддержка всех источников (preloaded, custom, library)
```

### Создать фабричные методы

Для каждого фасада индикатора:
```python
class XXXZoneAnalyzer:
    @classmethod
    def from_preloaded(cls, ...): ...
    
    @classmethod
    def from_custom(cls, ...): ...
    
    @classmethod
    def from_library(cls, library='pandas_ta', ...): ...
```

---

## Заключение

### Что было упущено в zonan.md

1. ❌ Не использовалась `IndicatorFactory`
2. ❌ Не поддерживались 3 источника индикаторов
3. ❌ Игнорировался `LibraryManager`
4. ❌ Дублировалась логика расчета индикаторов

### Что нужно добавить

1. ✅ **IndicatorZoneConfig** - конфигурация с указанием источника
2. ✅ **BaseIndicatorZoneAnalyzer.calculate_indicator()** - через IndicatorFactory
3. ✅ **Фабричные методы** - from_preloaded(), from_custom(), from_library()
4. ✅ **Примеры для всех источников**

### Итоговая интеграция

```python
# Архитектура с полной интеграцией:

IndicatorFactory (существует)
    ├── PRELOADED (извлечение готовых данных)
    ├── CUSTOM (встроенные алгоритмы)
    └── LIBRARY (pandas_ta, talib)
         ↓ создает BaseIndicator
         ↓ calculate() → IndicatorResult
         ↓
BaseIndicatorZoneAnalyzer
    ├── calculate_indicator() - использует IndicatorFactory!
    ├── detect_zones() - делегирует ZoneDetectionStrategy
    └── analyze() - делегирует UniversalZoneAnalyzer
         ↓
UniversalZoneAnalyzer (универсальный оркестратор)
    └── analyze_zones() - агностичен к источнику индикатора!
```

**Результат:** Полная интеграция с существующей инфраструктурой, нет дублирования, максимальная гибкость.

---

**Дата:** 2025-10-17  
**Статус:** Дополнение к zonan.md - интеграция с IndicatorFactory  
**Действие:** Требуется обновить zonan.md с учетом этих данных

