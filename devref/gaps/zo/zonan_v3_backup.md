# Архитектура универсального анализатора зон (Zone Analysis)

**Дата:** 2025-10-17  
**Статус:** Proposal v2 - интегрированы улучшения  
**Контекст:** Анализ текущей реализации MACDZoneAnalyzer и предложение универсального решения

---

## Содержание

1. [Проблема: MACDZoneAnalyzer как "толстый координатор"](#проблема)
2. [Решение: Трехслойная архитектура](#решение)
3. [Базовые структуры данных](#базовые-структуры)
4. [Слой 1: Zone Detection](#слой-1)
5. [Слой 2: Universal Zone Analyzer](#слой-2)
6. [Слой 3: Indicator Facades](#слой-3)
7. [Структура директорий](#структура)
8. [Примеры использования](#примеры)
9. [Преимущества архитектуры](#преимущества)
10. [План миграции](#план-миграции)
11. [Критерии успеха](#критерии)
12. [Сравнение: До и После](#сравнение)
13. [Заключение](#заключение)

---

<a name="проблема"></a>
## Проблема: MACDZoneAnalyzer как "толстый координатор"

### Текущее состояние (фактический анализ кода)

**Файл:** `bquant/indicators/macd.py` (564 строки)

**Структура класса:**
```python
class MACDZoneAnalyzer:
    def __init__(self, macd_params, zone_params):
        # Сохранение параметров
        ...
    
    def calculate_macd_with_atr(self, df):
        # 67 строк СВОЕЙ ЛОГИКИ
        # - Выбор алгоритма (NumPy vs standard)
        # - Расчет MACD через calculate_macd()
        # - Расчет ATR через calculate_derived_indicators()
        # - Объединение результатов
        ...
    
    def identify_zones(self, df):
        # 80 строк СВОЕЙ ЛОГИКИ (алгоритм сегментации!)
        # - Определение знака MACD: np.where(df['macd'] > 0, 1, -1)
        # - Поиск точек смены знака: diff().fillna(0)
        # - Создание объектов ZoneInfo с копией DataFrame
        # - Фильтрация по min_duration
        ...
    
    def _zone_to_dict(self, zone):
        # 20 строк адаптера (технический долг)
        ...
    
    def _features_to_dict(self, features):
        # 13 строк адаптера
        ...
    
    def _adapt_statistics_format(self, stats_data):
        # 45 строк ТЕХНИЧЕСКОГО ДОЛГА
        # - Маппинг 'total_statistics' → 'total_zones'
        # - Маппинг 'bull_zones_count' → 'bull_zones'
        # - Множество ручных преобразований
        ...
    
    def analyze_complete(self, df):
        # 3 строки - делегирует на analyze_complete_modular
        return self.analyze_complete_modular(df, ...)
    
    def analyze_complete_modular(self, df, perform_clustering, n_clusters):
        # 135 строк
        # ШАГ 1: СВОЯ ЛОГИКА
        df_with_indicators = self.calculate_macd_with_atr(df)
        zones = self.identify_zones(df_with_indicators)
        
        # ШАГ 2-7: Делегирование, но с ЦИКЛАМИ и АДАПТАЦИЕЙ
        features_analyzer = ZoneFeaturesAnalyzer(...)
        
        zones_features = []
        for zone in zones:  # ← ЦИКЛ в оркестраторе
            zone_dict = self._zone_to_dict(zone)  # ← АДАПТЕР
            zone_features = features_analyzer.extract_zone_features(zone_dict)
            zone.features = self._features_to_dict(zone_features)
            zones_features.append(zone_features)
        
        # Ручная подготовка данных
        features_dicts = []
        for f in zones_features:  # ← ЕЩЕ ОДИН ЦИКЛ
            f_dict = self._features_to_dict(f)
            if 'zone_type' in f_dict and 'type' not in f_dict:
                f_dict['type'] = f_dict['zone_type']  # ← РУЧНОЙ МАППИНГ
            features_dicts.append(f_dict)
        
        # Try-catch для каждого теста
        try:
            h1_result = test_suite.test_zone_duration_hypothesis(features_dicts)
            hypothesis_tests['zone_duration'] = h1_result.to_dict()
        except Exception as e:
            hypothesis_tests['zone_duration'] = {'error': str(e)}
        
        # ... еще вызовы с аналогичным try-catch
        ...
```

### Количественная оценка

| Категория | Строк кода | % от класса | Оценка |
|-----------|-----------|-------------|--------|
| **Своя бизнес-логика** | ~192 | 34% | ⚠️ МОНОЛИТ |
| └ MACD расчет | 67 | 12% | Алгоритмическая |
| └ Определение зон | 80 | 14% | Алгоритмическая |
| └ Адаптация форматов | 45 | 8% | Технический долг |
| **Делегирование** | ~135 | 24% | ✅ Оркестратор |
| └ Вызовы анализаторов | ~80 | 14% | Координация |
| └ Циклы обработки | ~30 | 5% | ⚠️ Сомнительно |
| └ Try-catch блоки | ~25 | 4% | Обработка ошибок |
| **Адаптеры** | ~78 | 14% | 🔧 Утилиты |
| **Конструктор + фабрики** | ~159 | 28% | 🔧 Инфраструктура |

**Вердикт:** Гибрид (40% монолит, 40% оркестратор, 20% адаптеры)

### Выявленные проблемы

1. **❌ Смешение ответственностей:**
   - Расчет индикатора (MACD-specific)
   - Определение зон (алгоритм сегментации)
   - Оркестрация анализа (координация)
   - Все в одном классе!

2. **❌ Жесткая привязка к MACD:**
   - Hardcoded: `if 'macd' not in df.columns`
   - Hardcoded: `df['macd_sign'] = np.where(df['macd'] > 0, 1, -1)`
   - Невозможно использовать для AO, Bollinger, RSI без копирования кода

3. **❌ Циклы обработки в оркестраторе:**
   ```python
   for zone in zones:
       zone_dict = self._zone_to_dict(zone)
       zone_features = features_analyzer.extract_zone_features(zone_dict)
   ```
   - Оркестратор содержит бизнес-логику (циклы обработки)
   - Должна быть чистая координация

4. **❌ Технический долг (45 строк адаптации):**
   ```python
   adapted['total_zones'] = total.get('total_zones', 0)
   adapted['bull_zones'] = total.get('bull_zones_count', 0)
   # ... еще 40 строк ручного маппинга
   ```
   - Несовместимость форматов между модулями
   - Ручной маппинг полей

5. **❌ Нет Dependency Injection:**
   ```python
   features_analyzer = ZoneFeaturesAnalyzer(...)  # создается внутри метода
   test_suite = HypothesisTestSuite(alpha=0.05)   # создается внутри метода
   ```
   - Невозможно подменить реализации для тестирования
   - Жесткая связанность

6. **❌ Фиксированные типы зон:**
   - Только 'bull' и 'bear'
   - Нет поддержки RSI-зон (overbought/neutral/oversold)

---

<a name="решение"></a>
## Решение: Трехслойная архитектура

### Ключевая идея

> **"Зоны - первичны."**  
> После идентификации зон мы передаем их в универсальный анализатор-оркестратор.

### Принцип разделения

```
┌────────────────────────────────────────────────────────────────┐
│ Слой 3: Indicator-specific Facades                            │
│ (MACDZoneAnalyzer, AOZoneAnalyzer, BollingerZoneAnalyzer)     │
│                                                                │
│ Ответственность: Расчет индикатора + координация             │
│ Размер: ~50-80 строк на фасад                                 │
└───────────────────┬────────────────────────────────────────────┘
                    │ передает zones: List[ZoneInfo]
                    ▼
┌────────────────────────────────────────────────────────────────┐
│ Слой 2: Universal Zone Analyzer                               │
│ (UniversalZoneAnalyzer)                                        │
│                                                                │
│ Ответственность: Анализ зон (агностичен к источнику!)         │
│ Размер: ~100-150 строк                                        │
└───────────────────┬────────────────────────────────────────────┘
                    │ использует
                    ▼
┌────────────────────────────────────────────────────────────────┐
│ Слой 1: Zone Detection Strategies                             │
│ (ZeroCrossing, LineCrossing, Threshold, Combined)             │
│                                                                │
│ Ответственность: Определение зон по правилам                  │
│ Размер: ~50-80 строк на стратегию                            │
└────────────────────────────────────────────────────────────────┘
```

---

<a name="интеграция-индикаторов"></a>
## Интеграция с существующей инфраструктурой индикаторов

### Обзор системы индикаторов BQuant

**BQuant уже имеет мощную инфраструктуру для работы с индикаторами:**

```
bquant/indicators/
├── base.py                     # Базовая архитектура
│   ├── IndicatorFactory        # ← Фабрика создания индикаторов
│   ├── BaseIndicator          # Абстрактный базовый класс
│   ├── PreloadedIndicator     # Извлечение готовых данных из DataFrame
│   ├── CustomIndicator        # Встроенные алгоритмы расчета
│   └── LibraryIndicator       # Обертки над pandas_ta, talib
│
├── custom/                     # Встроенные реализации (SMA, EMA, RSI, MACD, BB)
├── library/                    # Внешние библиотеки
│   └── manager.py (LibraryManager)  # Управление pandas_ta, talib
└── preloaded/                  # Извлечение готовых данных
```

### API создания индикаторов

**IndicatorFactory - единый интерфейс для всех источников:**

```python
from bquant.indicators import IndicatorFactory

# 1. PRELOADED - извлечь готовые данные
indicator = IndicatorFactory.create('preloaded', 'macd')
result = indicator.calculate(df)  # Извлекает 'macd', 'macd_signal', 'macd_hist'

# 2. CUSTOM - встроенный алгоритм
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26, signal=9)
result = indicator.calculate(df)  # Вычисляет MACD

# 3. LIBRARY - внешняя библиотека pandas_ta
indicator = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
result = indicator.calculate(df)  # Использует pandas_ta.rsi()

# 4. LIBRARY - TA-Lib
indicator = IndicatorFactory.create('talib', 'bbands', timeperiod=20)
result = indicator.calculate(df)  # Использует talib.BBANDS()
```

### Важность интеграции

**Zone Detection должен использовать IndicatorFactory вместо прямых вызовов:**

❌ **Неправильно** (дублирование):
```python
def calculate_indicator(self, df):
    macd_data = calculate_macd(df, fast=12, slow=26)  # Прямой вызов
    # ... ручное добавление колонок
```

✅ **Правильно** (использование инфраструктуры):
```python
def calculate_indicator(self, df):
    indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26)
    result = indicator.calculate(df)  # Через фабрику!
    # ... результат уже в стандартизированном формате
```

**Преимущества:**
- ✅ Поддержка всех 3 источников (preloaded/custom/library)
- ✅ Нет дублирования логики расчета
- ✅ Стандартизированный IndicatorResult
- ✅ Автоматическая регистрация и кэширование

---

<a name="базовые-структуры"></a>
## Базовые структуры данных

### Размещение моделей

**Проблема текущего размещения:**
- `ZoneInfo` и `ZoneAnalysisResult` находятся в `bquant/indicators/macd.py`
- Это MACD-специфичный модуль
- Модели используются универсально (в analysis, strategies, tests)
- Нарушает архитектурный принцип размещения

**Решение:** Переместить в `bquant/analysis/zones/models.py`

### ZoneInfo - универсальная модель зоны

```python
# bquant/analysis/zones/models.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd


@dataclass
class ZoneInfo:
    """
    Информация о зоне (универсальная структура).
    
    Используется для хранения данных зоны независимо от индикатора.
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        type: Тип зоны (любое значение: 'bull', 'bear', 'overbought', 'neutral', ...)
        start_idx: Начальный индекс в DataFrame (integer location)
        end_idx: Конечный индекс в DataFrame (integer location)
        start_time: Время начала зоны (index value, datetime)
        end_time: Время окончания зоны (index value, datetime)
        duration: Длительность в барах
        data: DataFrame с данными зоны (OHLCV + все индикаторы)
        features: Рассчитанные признаки зоны (заполняется после анализа)
    """
    zone_id: int
    type: str  # Может быть любое значение, не только 'bull'/'bear'
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None
    
    def to_analyzer_format(self) -> Dict[str, Any]:
        """
        Конвертация в формат для передачи в анализаторы.
        
        Инкапсулирует логику преобразования внутри модели.
        Убирает необходимость в адаптерах `_zone_to_dict()` в оркестраторах.
        
        Returns:
            Словарь с данными зоны для анализаторов
        """
        return {
            'zone_id': self.zone_id,
            'type': self.type,
            'duration': self.duration,
            'data': self.data,
            **(self.features or {})
        }


@dataclass
class ZoneAnalysisResult:
    """
    Результат анализа зон (универсальный).
    
    Attributes:
        zones: Список обнаруженных зон
        statistics: Статистики распределения зон
        hypothesis_tests: Результаты тестов гипотез
        clustering: Результаты кластеризации (опционально)
        sequence_analysis: Анализ последовательностей зон (опционально)
        regression_results: Результаты регрессионного анализа (опционально)
        validation_results: Результаты валидации (опционально)
        data: DataFrame с индикаторами (для визуализации)
        metadata: Метаданные анализа
    """
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    regression_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Ключевое улучшение:** Метод `to_analyzer_format()` инкапсулирует преобразование.

---

<a name="слой-1"></a>
## Слой 1: Zone Detection (Идентификация зон)

### Назначение

**Только определение зон по правилам.** Не знает ничего про анализ зон.

### Протокол и конфигурация

```python
# bquant/analysis/zones/detection/base.py

from typing import Protocol, List, Dict, Any, runtime_checkable
from dataclasses import dataclass, field
import pandas as pd
from ..models import ZoneInfo


@runtime_checkable
class ZoneDetectionStrategy(Protocol):
    """Стратегия определения зон."""
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: 'ZoneDetectionConfig') -> List[ZoneInfo]:
        """
        Определить зоны на основе данных и правил.
        
        Args:
            data: DataFrame с данными (OHLCV + индикаторы)
            config: Конфигурация правил определения зон
            
        Returns:
            Список объектов ZoneInfo
        """
        ...


@dataclass
class ZoneDetectionConfig:
    """Конфигурация правил определения зон."""
    
    # Основные параметры
    min_duration: int = 2
    zone_types: List[str] = None  # ['bull', 'bear'] или больше
    
    # Правила определения (различаются для разных стратегий)
    rules: Dict[str, Any] = field(default_factory=dict)
    
    # Метаданные
    strategy_name: str = None
    
    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = ['bull', 'bear']
```

### Реестр стратегий

```python
# bquant/analysis/zones/detection/registry.py

from typing import Dict, Type, List

class ZoneDetectionRegistry:
    """Реестр стратегий определения зон."""
    
    _strategies: Dict[str, Type[ZoneDetectionStrategy]] = {}
    
    @classmethod
    def register(cls, name: str):
        """Декоратор для регистрации стратегии."""
        def decorator(strategy_class):
            cls._strategies[name] = strategy_class
            return strategy_class
        return decorator
    
    @classmethod
    def get(cls, name: str, **params):
        """Получить стратегию по имени."""
        if name not in cls._strategies:
            raise ValueError(
                f"Unknown zone detection strategy: {name}. "
                f"Available: {list(cls._strategies.keys())}"
            )
        return cls._strategies[name](**params)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Список доступных стратегий."""
        return list(cls._strategies.keys())
```

**Доступные стратегии детекции зон:**

| Стратегия | Название | Применение | Типы зон |
|-----------|----------|------------|----------|
| `'zero_crossing'` | ZeroCrossingDetection | MACD, AO, CCI (осцилляторы) | 2 (bull/bear) |
| `'line_crossing'` | LineCrossingDetection | Bollinger, MA crosses | 2 (bull/bear) |
| `'threshold'` | ThresholdDetection | RSI, Stochastic (bounded) | 2-3+ (overbought/neutral/oversold) |
| `'preloaded'` | PreloadedZonesDetection | Импорт из внешних систем | Любое количество |
| `'combined'` | CombinedRulesDetection | Кастомные комбинации условий | 2+ |

---

### Реализация 1: Пересечение нулевой линии

**Для:** MACD, AO, CCI и других осцилляторов

```python
# bquant/analysis/zones/detection/zero_crossing.py

import numpy as np
import pandas as pd
from typing import List
from .base import ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo


@ZoneDetectionRegistry.register('zero_crossing')
class ZeroCrossingDetection:
    """Зоны по пересечению индикатором нулевой линии."""
    
    def detect_zones(self, 
                     data: pd.DataFrame, 
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Bull zone: indicator > 0
        Bear zone: indicator < 0
        """
        indicator_col = config.rules['indicator_col']  # 'macd', 'ao', 'cci', etc.
        
        # Определяем знак индикатора
        data = data.copy()
        data['zone_sign'] = np.where(data[indicator_col] > 0, 1, -1)
        
        # Находим точки смены знака
        sign_changes = data['zone_sign'].diff().fillna(0)
        change_points = data[sign_changes != 0].index.tolist()
        
        # Добавляем границы данных
        if data.index[0] not in change_points:
            change_points.insert(0, data.index[0])
        if data.index[-1] not in change_points:
            change_points.append(data.index[-1])
        
        # Создаем зоны между точками смены
        zones = []
        for i in range(len(change_points) - 1):
            start_time = change_points[i]
            end_time = change_points[i + 1]
            
            start_idx = data.index.get_loc(start_time)
            end_idx = data.index.get_loc(end_time)
            
            zone_data = data.iloc[start_idx:end_idx + 1]
            
            # Фильтрация по минимальной длительности
            if len(zone_data) < config.min_duration:
                continue
            
            # Определяем тип зоны
            zone_type = 'bull' if zone_data[indicator_col].iloc[0] > 0 else 'bear'
            
            zones.append(ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=start_time,
                end_time=end_time,
                duration=len(zone_data),
                data=zone_data
            ))
        
        return zones
```

### Реализация 2: Пересечение двух линий

**Для:** Bollinger (price vs middle), MA crosses (fast vs slow)

```python
# bquant/analysis/zones/detection/line_crossing.py

@ZoneDetectionRegistry.register('line_crossing')
class LineCrossingDetection:
    """Зоны по пересечению двух линий."""
    
    def detect_zones(self, 
                     data: pd.DataFrame, 
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Bull zone: line1 > line2
        Bear zone: line1 < line2
        
        Примеры:
        - Price crossing Bollinger Middle: line1='close', line2='bb_middle'
        - Fast MA crossing Slow MA: line1='fast_ma', line2='slow_ma'
        """
        line1 = config.rules['line1_col']
        line2 = config.rules['line2_col']
        
        # Определяем позицию
        data = data.copy()
        data['position'] = np.where(data[line1] > data[line2], 1, -1)
        
        # Находим пересечения
        position_changes = data['position'].diff().fillna(0)
        change_points = data[position_changes != 0].index.tolist()
        
        if data.index[0] not in change_points:
            change_points.insert(0, data.index[0])
        if data.index[-1] not in change_points:
            change_points.append(data.index[-1])
        
        # Создаем зоны
        zones = []
        for i in range(len(change_points) - 1):
            start_time = change_points[i]
            end_time = change_points[i + 1]
            
            start_idx = data.index.get_loc(start_time)
            end_idx = data.index.get_loc(end_time)
            
            zone_data = data.iloc[start_idx:end_idx + 1]
            
            if len(zone_data) < config.min_duration:
                continue
            
            zone_type = 'bull' if zone_data[line1].iloc[0] > zone_data[line2].iloc[0] else 'bear'
            
            zones.append(ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=start_time,
                end_time=end_time,
                duration=len(zone_data),
                data=zone_data
            ))
        
        return zones
```

### Реализация 3: Пороговые уровни

**Для:** RSI, Stochastic (поддержка > 2 типов зон!)

```python
# bquant/analysis/zones/detection/threshold.py

@ZoneDetectionRegistry.register('threshold')
class ThresholdDetection:
    """Зоны по превышению порогов."""
    
    def detect_zones(self, 
                     data: pd.DataFrame, 
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Определение 3-х типов зон:
        - Overbought zone: indicator > upper_threshold
        - Neutral zone: lower_threshold <= indicator <= upper_threshold
        - Oversold zone: indicator < lower_threshold
        
        Примеры:
        - RSI: upper=70, lower=30
        - Stochastic: upper=80, lower=20
        """
        indicator_col = config.rules['indicator_col']  # 'rsi', 'stoch_k'
        upper = config.rules.get('upper_threshold', 70)
        lower = config.rules.get('lower_threshold', 30)
        
        # Классификация значений
        def classify_zone(value):
            if value > upper:
                return 'overbought'
            elif value < lower:
                return 'oversold'
            else:
                return 'neutral'
        
        data = data.copy()
        data['zone_type'] = data[indicator_col].apply(classify_zone)
        
        # Находим смены типа зоны
        zone_changes = data['zone_type'].ne(data['zone_type'].shift())
        change_points = data[zone_changes].index.tolist()
        
        if data.index[0] not in change_points:
            change_points.insert(0, data.index[0])
        if data.index[-1] not in change_points:
            change_points.append(data.index[-1])
        
        # Создаем зоны (может быть 3 типа!)
        zones = []
        for i in range(len(change_points) - 1):
            start_time = change_points[i]
            end_time = change_points[i + 1]
            
            start_idx = data.index.get_loc(start_time)
            end_idx = data.index.get_loc(end_time)
            
            zone_data = data.iloc[start_idx:end_idx + 1]
            
            if len(zone_data) < config.min_duration:
                continue
            
            zone_type = zone_data['zone_type'].iloc[0]
            
            zones.append(ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=start_time,
                end_time=end_time,
                duration=len(zone_data),
                data=zone_data
            ))
        
        return zones
```

### Реализация 4: Комбинированные правила

**Для:** Кастомных сложных условий

```python
# bquant/analysis/zones/detection/combined.py

@ZoneDetectionRegistry.register('combined')
class CombinedRulesDetection:
    """Зоны по комбинации нескольких условий."""
    
    def detect_zones(self, 
                     data: pd.DataFrame, 
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Комбинация условий через AND / OR.
        
        Пример:
        Bull zone = (MACD > 0) AND (Price > MA50) AND (RSI > 50)
        
        config.rules = {
            'conditions': [
                lambda df: df['macd'] > 0,
                lambda df: df['close'] > df['ma_50'],
                lambda df: df['rsi'] > 50
            ],
            'logic': 'AND'  # or 'OR'
        }
        """
        conditions = config.rules['conditions']  # List[Callable]
        logic = config.rules.get('logic', 'AND')
        
        # Оценка каждого условия
        data = data.copy()
        conditions_met = pd.DataFrame({
            f'cond_{i}': cond(data) 
            for i, cond in enumerate(conditions)
        })
        
        # Логика комбинирования
        if logic == 'AND':
            data['zone_condition'] = conditions_met.all(axis=1)
        elif logic == 'OR':
            data['zone_condition'] = conditions_met.any(axis=1)
        else:
            raise ValueError(f"Unknown logic: {logic}. Use 'AND' or 'OR'")
        
        # Находим смены условия
        condition_changes = data['zone_condition'].ne(data['zone_condition'].shift())
        change_points = data[condition_changes].index.tolist()
        
        if data.index[0] not in change_points:
            change_points.insert(0, data.index[0])
        if data.index[-1] not in change_points:
            change_points.append(data.index[-1])
        
        # Создаем зоны
        zones = []
        for i in range(len(change_points) - 1):
            start_time = change_points[i]
            end_time = change_points[i + 1]
            
            start_idx = data.index.get_loc(start_time)
            end_idx = data.index.get_loc(end_time)
            
            zone_data = data.iloc[start_idx:end_idx + 1]
            
            if len(zone_data) < config.min_duration:
                continue
            
            zone_type = 'bull' if zone_data['zone_condition'].iloc[0] else 'bear'
            
            zones.append(ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=start_time,
                end_time=end_time,
                duration=len(zone_data),
                data=zone_data
            ))
        
        return zones
```

### Реализация 5: Загрузка готовых зон (Preloaded)

**Для:** Импорта зон из внешних систем, кэширования, ручной разметки

```python
# bquant/analysis/zones/detection/preloaded.py

import pandas as pd
from typing import List, Union
from pathlib import Path

from .base import ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from ...core.logging_config import get_logger

logger = get_logger(__name__)


@ZoneDetectionRegistry.register('preloaded')
class PreloadedZonesDetection:
    """
    Загрузка заранее рассчитанных зон из внешнего датасета.
    
    Применение:
    - Импорт зон из внешних систем (MT5, TradingView, custom scripts)
    - Кэширование результатов предыдущих расчетов
    - Ручная разметка зон экспертами
    - A/B тестирование различных алгоритмов детекции
    """
    
    def detect_zones(self, 
                     data: pd.DataFrame, 
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Загрузка зон из внешнего датасета и объединение с основными данными.
        
        Args:
            data: DataFrame с котировками (OHLCV + индикаторы)
            config: Конфигурация с источником зон
                rules = {
                    'zones_data': DataFrame или путь к CSV файлу,
                    'time_tolerance': '5min' (опционально),
                    'strict_matching': False (опционально)
                }
        
        Returns:
            Список объектов ZoneInfo с данными из основного DataFrame
        """
        # 1. Загружаем датасет зон
        zones_df = self._load_zones_data(config.rules)
        
        # 2. Валидация формата
        self._validate_zones_format(zones_df)
        
        # 3. Создаем ZoneInfo объекты с объединением данных
        zones = []
        tolerance = pd.Timedelta(config.rules.get('time_tolerance', '1min'))
        strict = config.rules.get('strict_matching', False)
        
        for idx, row in zones_df.iterrows():
            zone_id = int(row['zone_id'])
            zone_type = str(row['type'])
            start_time = pd.to_datetime(row['start_time'])
            end_time = pd.to_datetime(row['end_time'])
            
            # Находим данные в основном DataFrame по времени
            zone_data = self._extract_zone_data(
                data, start_time, end_time, tolerance
            )
            
            # Проверка наличия данных
            if zone_data is None or zone_data.empty:
                if strict:
                    raise ValueError(
                        f"No data found for zone {zone_id} "
                        f"({start_time} - {end_time})"
                    )
                logger.warning(f"Skipping zone {zone_id}: no matching data")
                continue
            
            # Фильтрация по минимальной длительности
            if len(zone_data) < config.min_duration:
                logger.debug(f"Skipping zone {zone_id}: duration {len(zone_data)} < {config.min_duration}")
                continue
            
            # Вычисляем индексы
            start_idx = data.index.get_loc(zone_data.index[0])
            end_idx = data.index.get_loc(zone_data.index[-1])
            
            # Создаем ZoneInfo
            zone_info = ZoneInfo(
                zone_id=zone_id,
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=zone_data.index[0],
                end_time=zone_data.index[-1],
                duration=len(zone_data),
                data=zone_data
            )
            
            # Добавляем опциональные метаданные из датасета
            optional_fields = [col for col in zones_df.columns 
                             if col not in ['zone_id', 'type', 'start_time', 'end_time']]
            if optional_fields:
                zone_info.features = {col: row[col] for col in optional_fields}
            
            zones.append(zone_info)
        
        logger.info(f"Loaded {len(zones)} preloaded zones from dataset")
        return zones
    
    def _load_zones_data(self, rules: dict) -> pd.DataFrame:
        """Загрузка датасета зон из файла или DataFrame."""
        zones_data = rules.get('zones_data')
        
        if zones_data is None:
            raise ValueError("zones_data must be provided in config.rules")
        
        # Если путь к файлу
        if isinstance(zones_data, (str, Path)):
            zones_df = pd.read_csv(zones_data)
            logger.info(f"Loaded zones from file: {zones_data}")
        # Если уже DataFrame
        elif isinstance(zones_data, pd.DataFrame):
            zones_df = zones_data.copy()
            logger.info(f"Loaded zones from DataFrame ({len(zones_df)} zones)")
        else:
            raise ValueError(
                f"zones_data must be DataFrame or file path, got {type(zones_data)}"
            )
        
        return zones_df
    
    def _validate_zones_format(self, zones_df: pd.DataFrame):
        """Валидация формата датасета зон."""
        required_columns = ['zone_id', 'type', 'start_time', 'end_time']
        missing = [col for col in required_columns if col not in zones_df.columns]
        
        if missing:
            raise ValueError(
                f"Missing required columns in zones dataset: {missing}. "
                f"Required: {required_columns}. "
                f"Available: {list(zones_df.columns)}"
            )
    
    def _extract_zone_data(self, 
                          data: pd.DataFrame, 
                          start_time: pd.Timestamp, 
                          end_time: pd.Timestamp,
                          tolerance: pd.Timedelta) -> pd.DataFrame:
        """Извлечение данных зоны из основного DataFrame по временным меткам."""
        try:
            # Прямой поиск в диапазоне
            mask = (data.index >= start_time) & (data.index <= end_time)
            zone_data = data[mask]
            
            if not zone_data.empty:
                return zone_data.copy()
            
            # Если точное совпадение не найдено - ищем с допуском
            start_nearest_mask = (data.index >= start_time - tolerance) & (data.index <= start_time + tolerance)
            end_nearest_mask = (data.index >= end_time - tolerance) & (data.index <= end_time + tolerance)
            
            start_candidates = data[start_nearest_mask]
            end_candidates = data[end_nearest_mask]
            
            if start_candidates.empty or end_candidates.empty:
                return None
            
            # Берем ближайшие точки
            start_nearest = start_candidates.index[0]
            end_nearest = end_candidates.index[-1]
            
            mask = (data.index >= start_nearest) & (data.index <= end_nearest)
            zone_data = data[mask]
            
            if not zone_data.empty:
                logger.debug(f"Found zone data with tolerance: {start_nearest} - {end_nearest}")
                return zone_data.copy()
            
            return None
            
        except (IndexError, KeyError) as e:
            logger.warning(f"Failed to extract zone data: {e}")
            return None


# Helper функция для быстрого использования
def load_preloaded_zones(df: pd.DataFrame, 
                        zones_source: Union[str, Path, pd.DataFrame],
                        min_duration: int = 2,
                        time_tolerance: str = '1min') -> List[ZoneInfo]:
    """
    Быстрая загрузка готовых зон из внешнего источника.
    
    Args:
        df: DataFrame с основными данными (OHLCV + индикаторы)
        zones_source: Путь к CSV файлу или DataFrame с зонами
        min_duration: Минимальная длительность зоны
        time_tolerance: Допуск при поиске данных по времени
    
    Returns:
        Список объектов ZoneInfo
    
    Example:
        zones = load_preloaded_zones(df, 'my_zones.csv')
        analyzer = UniversalZoneAnalyzer()
        result = analyzer.analyze_zones(zones, df)
    """
    detector = PreloadedZonesDetection()
    return detector.detect_zones(
        df,
        ZoneDetectionConfig(
            min_duration=min_duration,
            rules={
                'zones_data': zones_source,
                'time_tolerance': time_tolerance
            },
            strategy_name='preloaded'
        )
    )
```

**Формат датасета зон (CSV):**

**Минимальный формат (обязательные поля):**
```csv
zone_id,type,start_time,end_time
0,bull,2024-01-15 10:00:00,2024-01-15 15:30:00
1,bear,2024-01-15 15:30:00,2024-01-16 09:00:00
2,bull,2024-01-16 09:00:00,2024-01-16 14:00:00
3,bear,2024-01-16 14:00:00,2024-01-17 11:30:00
```

**Расширенный формат (с метаданными):**
```csv
zone_id,type,start_time,end_time,confidence,source,signal_strength
0,bull,2024-01-15 10:00:00,2024-01-15 15:30:00,0.95,MT5,strong
1,bear,2024-01-15 15:30:00,2024-01-16 09:00:00,0.87,manual,medium
2,bull,2024-01-16 09:00:00,2024-01-16 14:00:00,0.92,algo_v2,strong
```

**Примечания:**
- Временные метки в формате ISO 8601 или любом, распознаваемом `pd.to_datetime()`
- Дополнительные колонки автоматически добавляются в `ZoneInfo.features`
- `duration`, `start_idx`, `end_idx` вычисляются автоматически при merge с данными

---

<a name="слой-2"></a>
## Слой 2: Universal Zone Analyzer (Универсальный анализатор)

### Назначение

**Анализ уже идентифицированных зон.** Полностью агностичен к источнику зон.

### Реализация

```python
# bquant/analysis/zones/analyzer.py

from typing import List, Optional
import pandas as pd
from datetime import datetime

from ...core.logging_config import get_logger
from ...core.exceptions import AnalysisError
from .models import ZoneInfo, ZoneAnalysisResult
from .zone_features import ZoneFeaturesAnalyzer
from .sequence_analysis import ZoneSequenceAnalyzer
from ..statistical import HypothesisTestSuite, ZoneRegressionAnalyzer
from ..validation import ValidationSuite

logger = get_logger(__name__)


class UniversalZoneAnalyzer:
    """
    Универсальный оркестратор анализа зон.
    
    КЛЮЧЕВЫЕ ПРИНЦИПЫ:
    - НЕ ЗНАЕТ откуда зоны (MACD, AO, Bollinger, кастомные правила)
    - Работает ТОЛЬКО с ZoneInfo объектами
    - ЧИСТЫЙ оркестратор - только координация, нет своей логики
    - НЕТ циклов обработки - только вызовы делегатов
    - НЕТ адаптеров - использует ZoneInfo.to_analyzer_format()
    """
    
    def __init__(self,
                 # Dependency Injection всех компонентов
                 features_analyzer: Optional[ZoneFeaturesAnalyzer] = None,
                 hypothesis_suite: Optional[HypothesisTestSuite] = None,
                 sequence_analyzer: Optional[ZoneSequenceAnalyzer] = None,
                 regression_analyzer: Optional[ZoneRegressionAnalyzer] = None,
                 validation_suite: Optional[ValidationSuite] = None,
                 
                 # Стратегии метрик (опциональные, для features_analyzer)
                 swing_strategy=None,
                 shape_strategy=None,
                 divergence_strategy=None,
                 volatility_strategy=None,
                 volume_strategy=None):
        """
        Инициализация универсального анализатора.
        
        Args:
            features_analyzer: Анализатор признаков зон (DI)
            hypothesis_suite: Набор статистических тестов (DI)
            sequence_analyzer: Анализатор последовательностей (DI)
            regression_analyzer: Регрессионный анализатор (DI)
            validation_suite: Набор методов валидации (DI)
            
            swing_strategy: Стратегия расчета свингов
            shape_strategy: Стратегия расчета формы
            divergence_strategy: Стратегия дивергенций
            volatility_strategy: Стратегия волатильности
            volume_strategy: Стратегия объема
        
        Note:
            Если анализаторы не переданы, создаются из config по умолчанию.
        """
        # Создаем features_analyzer с переданными стратегиями
        if features_analyzer is None:
            features_analyzer = ZoneFeaturesAnalyzer(
                swing_strategy=swing_strategy,
                shape_strategy=shape_strategy,
                divergence_strategy=divergence_strategy,
                volatility_strategy=volatility_strategy,
                volume_strategy=volume_strategy
            )
        
        self.features = features_analyzer
        self.hypotheses = hypothesis_suite or HypothesisTestSuite()
        self.sequences = sequence_analyzer or ZoneSequenceAnalyzer()
        self.regression = regression_analyzer or ZoneRegressionAnalyzer()
        self.validation = validation_suite or ValidationSuite()
        
        logger.info("UniversalZoneAnalyzer initialized with DI components")
    
    def analyze_zones(self, 
                      zones: List[ZoneInfo],
                      data: pd.DataFrame,
                      perform_clustering: bool = True,
                      n_clusters: int = 3,
                      run_regression: bool = False,
                      run_validation: bool = False) -> ZoneAnalysisResult:
        """
        Полный анализ уже идентифицированных зон.
        
        ЧИСТАЯ КООРДИНАЦИЯ:
        - Нет циклов обработки
        - Нет своей бизнес-логики
        - Нет адаптеров (используется ZoneInfo.to_analyzer_format())
        - Только вызовы делегатов
        
        Args:
            zones: Список зон (откуда угодно!)
            data: Исходные данные для контекста
            perform_clustering: Выполнять кластеризацию
            n_clusters: Количество кластеров
            run_regression: Запустить регрессионный анализ
            run_validation: Запустить валидацию
            
        Returns:
            ZoneAnalysisResult с полным анализом
        """
        if not zones:
            logger.warning("No zones provided for analysis")
            return self._empty_result(data)
        
        logger.info(f"Analyzing {len(zones)} zones of types: {set(z.type for z in zones)}")
        
        try:
            # 1. Извлечение признаков (ДЕЛЕГИРОВАНИЕ - БЕЗ адаптеров!)
            # ZoneFeaturesAnalyzer.extract_all_zones_features() принимает List[ZoneInfo]
            zones_features = self.features.extract_all_zones_features(zones)
            
            # 2. Статистический анализ (ДЕЛЕГИРОВАНИЕ)
            statistics = self.features.analyze_zones_distribution(
                [f.to_dict() for f in zones_features]
            )
            
            # 3. Тестирование гипотез (ДЕЛЕГИРОВАНИЕ)
            hypothesis_tests = self.hypotheses.run_all_tests(
                [f.to_dict() for f in zones_features]
            )
            
            # 4. Анализ последовательностей (ДЕЛЕГИРОВАНИЕ)
            sequence_analysis = self.sequences.analyze_zone_transitions(
                zones_features
            )
            
            # 5. Кластеризация (ДЕЛЕГИРОВАНИЕ, опционально)
            clustering = None
            if perform_clustering and len(zones) >= n_clusters:
                clustering = self.sequences.cluster_zones(
                    zones_features, n_clusters=n_clusters
                )
            
            # 6. Регрессия (ДЕЛЕГИРОВАНИЕ, опционально)
            regression_results = None
            if run_regression and len(zones) > 10:
                regression_results = {
                    'duration': self.regression.predict_zone_duration(
                        [f.to_dict() for f in zones_features]
                    ),
                    'return': self.regression.predict_price_return(
                        [f.to_dict() for f in zones_features]
                    )
                }
            
            # 7. Валидация (ДЕЛЕГИРОВАНИЕ, опционально)
            validation_results = None
            if run_validation:
                # ValidationSuite API требует analyze_func + DataFrame
                # Для интеграции нужна отдельная обертка
                pass
            
            # 8. Формирование результата (ТОЛЬКО СБОРКА - нет логики!)
            return ZoneAnalysisResult(
                zones=zones,
                statistics=statistics.results if hasattr(statistics, 'results') else statistics,
                hypothesis_tests=hypothesis_tests,
                sequence_analysis=sequence_analysis.results if hasattr(sequence_analysis, 'results') else sequence_analysis,
                clustering=clustering.results if clustering and hasattr(clustering, 'results') else clustering,
                regression_results=regression_results,
                validation_results=validation_results,
                data=data,
                metadata={
                    'analysis_timestamp': datetime.now().isoformat(),
                    'total_zones': len(zones),
                    'zone_types': list(set(z.type for z in zones)),
                    'analyzer_version': 'universal_v1'
                }
            )
        
        except Exception as e:
            logger.error(f"Zone analysis failed: {e}", exc_info=True)
            raise AnalysisError(
                f"Failed to analyze zones: {e}",
                {'total_zones': len(zones)}
            )
    
    def _empty_result(self, data: pd.DataFrame) -> ZoneAnalysisResult:
        """Пустой результат для случая отсутствия зон."""
        return ZoneAnalysisResult(
            zones=[],
            statistics={},
            hypothesis_tests={},
            data=data,
            metadata={
                'warning': 'No zones identified',
                'analysis_timestamp': datetime.now().isoformat()
            }
        )
```

### Изменения в ZoneFeaturesAnalyzer

```python
# bquant/analysis/zones/zone_features.py

class ZoneFeaturesAnalyzer:
    # ... существующий код ...
    
    def extract_all_zones_features(self, 
                                   zones: List[ZoneInfo]) -> List[ZoneFeatures]:
        """
        Извлечь признаки для всех зон (пакетная обработка).
        
        Принимает ZoneInfo напрямую, использует метод to_analyzer_format()
        для преобразования. Инкапсуляция преобразования в модели!
        
        Args:
            zones: Список объектов ZoneInfo
            
        Returns:
            Список объектов ZoneFeatures
        """
        return [
            self.extract_zone_features(zone.to_analyzer_format())
            for zone in zones
        ]
    
    def extract_zone_features(self, 
                             zone_info: Dict[str, Any]) -> ZoneFeatures:
        """
        Извлечение признаков из информации о зоне.
        
        Args:
            zone_info: Словарь с информацией о зоне (из ZoneInfo.to_analyzer_format())
                - zone_id: ID зоны
                - type: Тип зоны
                - duration: Длительность
                - data: DataFrame с OHLCV + индикаторы
        
        Returns:
            ZoneFeatures с рассчитанными признаками
        """
        # ... существующая реализация ...
```

---

<a name="слой-3"></a>
## Слой 3: Indicator-specific Facades (Фасады для индикаторов)

### Назначение

**Координация расчета индикатора + определения зон + анализа** для конкретного индикатора.

### Базовый класс (опционально)

```python
# bquant/indicators/analyzers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

from bquant.analysis.zones.detection import ZoneDetectionConfig, ZoneDetectionRegistry
from bquant.analysis.zones import UniversalZoneAnalyzer
from bquant.analysis.zones.models import ZoneAnalysisResult


class BaseIndicatorZoneAnalyzer(ABC):
    """
    Базовый класс для анализаторов зон индикаторов.
    
    Подклассы должны реализовать:
    - calculate_indicator(df) -> df with indicator columns
    - get_default_zone_config() -> ZoneDetectionConfig
    """
    
    def __init__(self,
                 indicator_params: Dict[str, Any] = None,
                 zone_detection_config: Optional[ZoneDetectionConfig] = None,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            indicator_params: Параметры индикатора
            zone_detection_config: Конфигурация определения зон
            zone_analyzer: Универсальный анализатор (DI)
        """
        self.indicator_params = indicator_params or {}
        self.zone_config = zone_detection_config or self.get_default_zone_config()
        self.zone_detector = self._create_zone_detector()
        self.analyzer = zone_analyzer or UniversalZoneAnalyzer()
    
    @abstractmethod
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитать индикатор и добавить колонки.
        
        Единственная "своя" логика в фасаде!
        """
        pass
    
    @abstractmethod
    def get_default_zone_config(self) -> ZoneDetectionConfig:
        """Получить дефолтную конфигурацию определения зон."""
        pass
    
    def _create_zone_detector(self):
        """Создать детектор зон на основе конфигурации."""
        return ZoneDetectionRegistry.get(
            self.zone_config.strategy_name
        )
    
    def analyze(self, df: pd.DataFrame, **kwargs) -> ZoneAnalysisResult:
        """
        Полный анализ зон индикатора.
        
        ТОЛЬКО КООРДИНАЦИЯ - 3 чистых шага!
        """
        # 1. Расчет индикатора (СВОЕ - единственная логика)
        df_with_indicator = self.calculate_indicator(df)
        
        # 2. Определение зон (ДЕЛЕГИРОВАНИЕ)
        zones = self.zone_detector.detect_zones(
            df_with_indicator, 
            self.zone_config
        )
        
        # 3. Анализ зон (ДЕЛЕГИРОВАНИЕ)
        return self.analyzer.analyze_zones(
            zones=zones,
            data=df_with_indicator,
            **kwargs
        )
```

### Реализация: MACD Zone Analyzer

```python
# bquant/indicators/analyzers/macd.py

from typing import Dict, Any, Optional
import pandas as pd

from ...core.config import get_indicator_params
from ...core.logging_config import get_logger
from ...indicators.calculators import calculate_macd
from ...data.processor import calculate_derived_indicators
from ...analysis.zones.detection import ZoneDetectionConfig
from ...analysis.zones import UniversalZoneAnalyzer
from .base import BaseIndicatorZoneAnalyzer

logger = get_logger(__name__)


class MACDZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    """
    Фасад для MACD: расчет индикатора + определение зон + анализ.
    
    ТОНКИЙ класс (~50 строк) - только координация!
    """
    
    def __init__(self,
                 macd_params: Optional[Dict[str, Any]] = None,
                 zone_detection_config: Optional[ZoneDetectionConfig] = None,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            macd_params: Параметры MACD (fast, slow, signal)
            zone_detection_config: Конфигурация определения зон
            zone_analyzer: Универсальный анализатор (DI)
        """
        self.macd_params = macd_params or get_indicator_params('macd')
        super().__init__(
            indicator_params=self.macd_params,
            zone_detection_config=zone_detection_config,
            zone_analyzer=zone_analyzer
        )
        logger.info(f"MACDZoneAnalyzer initialized with params: {self.macd_params}")
    
    def get_default_zone_config(self) -> ZoneDetectionConfig:
        """Дефолтная конфигурация: пересечение нулевой линии MACD."""
        return ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет MACD и ATR.
        
        Единственная "своя" логика в этом фасаде!
        """
        logger.info("Calculating MACD and ATR indicators")
        
        df_with_indicators = df.copy()
        
        # Расчет MACD
        macd_data = calculate_macd(
            df, 
            fast=self.macd_params['fast'],
            slow=self.macd_params['slow'],
            signal=self.macd_params['signal']
        )
        
        for col in macd_data.columns:
            df_with_indicators[col] = macd_data[col]
        
        # Добавляем производные индикаторы (ATR и др.)
        derived_data = calculate_derived_indicators(df_with_indicators)
        for col in derived_data.columns:
            if col not in df_with_indicators.columns:
                df_with_indicators[col] = derived_data[col]
        
        logger.info(f"Indicators calculated. Shape: {df_with_indicators.shape}")
        return df_with_indicators


# Backward compatibility
def create_macd_analyzer(macd_params: Optional[Dict] = None,
                        zone_params: Optional[Dict] = None) -> MACDZoneAnalyzer:
    """
    Создать MACD анализатор (backward compatibility).
    
    Args:
        macd_params: Параметры MACD
        zone_params: Параметры зон (deprecated, используйте zone_detection_config)
    """
    zone_config = None
    if zone_params:
        zone_config = ZoneDetectionConfig(
            min_duration=zone_params.get('min_duration', 2),
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    
    return MACDZoneAnalyzer(
        macd_params=macd_params,
        zone_detection_config=zone_config
    )
```

### Реализация: AO Zone Analyzer

```python
# bquant/indicators/analyzers/ao.py

class AOZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    """Анализатор зон Awesome Oscillator."""
    
    def __init__(self,
                 ao_params: Optional[Dict[str, Any]] = None,
                 zone_detection_config: Optional[ZoneDetectionConfig] = None,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        self.ao_params = ao_params or {'fast': 5, 'slow': 34}
        super().__init__(
            indicator_params=self.ao_params,
            zone_detection_config=zone_detection_config,
            zone_analyzer=zone_analyzer
        )
    
    def get_default_zone_config(self) -> ZoneDetectionConfig:
        """AO использует пересечение нулевой линии (как MACD)."""
        return ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'ao'},
            strategy_name='zero_crossing'
        )
    
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет AO = SMA(median_price, fast) - SMA(median_price, slow)."""
        df = df.copy()
        
        median_price = (df['high'] + df['low']) / 2
        df['ao'] = (median_price.rolling(self.ao_params['fast']).mean() - 
                    median_price.rolling(self.ao_params['slow']).mean())
        
        # Добавляем ATR для нормализации
        from bquant.data.processor import calculate_derived_indicators
        derived = calculate_derived_indicators(df)
        if 'atr' in derived.columns:
            df['atr'] = derived['atr']
        
        return df
```

### Пример: Bollinger через custom

```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='custom',         # ← Встроенный алгоритм BollingerBands
        indicator_name='bbands',
        indicator_params={'length': 20, 'std': 2.0},
        zone_detection=ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={
                'line1_col': 'close',
                'line2_col': 'BBM_20_2.0'  # Bollinger Middle (custom naming)
            },
            strategy_name='line_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

### Пример: RSI через talib с 3 типами зон

```python
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='talib',          # ← TA-Lib
        indicator_name='rsi',
        indicator_params={'timeperiod': 14},
        zone_detection=ZoneDetectionConfig(
            min_duration=3,
            zone_types=['overbought', 'neutral', 'oversold'],  # 3 типа!
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

# Статистика по типам зон
print(f"Overbought zones: {sum(1 for z in result.zones if z.type == 'overbought')}")
print(f"Neutral zones: {sum(1 for z in result.zones if z.type == 'neutral')}")
print(f"Oversold zones: {sum(1 for z in result.zones if z.type == 'oversold')}")
```

---

<a name="структура"></a>
## Структура директорий

```
bquant/
├── analysis/
│   └── zones/
│       ├── __init__.py
│       │
│       ├── models.py               # НОВОЕ - ZoneInfo, ZoneAnalysisResult
│       │
│       ├── detection/              # НОВОЕ - Слой 1 (определение зон)
│       │   ├── __init__.py
│       │   ├── base.py            # ZoneDetectionStrategy, ZoneDetectionConfig
│       │   ├── registry.py         # ZoneDetectionRegistry
│       │   ├── zero_crossing.py    # ZeroCrossingDetection
│       │   ├── line_crossing.py    # LineCrossingDetection
│       │   ├── threshold.py        # ThresholdDetection
│       │   └── combined.py         # CombinedRulesDetection
│       │
│       ├── analyzer.py             # НОВОЕ - UniversalZoneAnalyzer (Слой 2)
│       │
│       ├── zone_features.py        # РЕФАКТОРИНГ - добавить extract_all_zones_features()
│       ├── sequence_analysis.py    # БЕЗ ИЗМЕНЕНИЙ
│       │
│       └── strategies/             # БЕЗ ИЗМЕНЕНИЙ (уже универсальны!)
│           ├── swing/
│           ├── shape/
│           ├── divergence/
│           ├── volatility/
│           └── volume/
│
├── indicators/
│   ├── analyzers/                  # НОВОЕ - Слой 3 (фасады индикаторов)
│   │   ├── __init__.py
│   │   ├── base.py                # BaseIndicatorZoneAnalyzer
│   │   ├── macd.py                # MACDZoneAnalyzer (рефакторинг)
│   │   ├── ao.py                  # AOZoneAnalyzer (новый)
│   │   └── bollinger.py           # BollingerZoneAnalyzer (новый)
│   │
│   └── macd.py                     # REFACTOR - переместить классы:
│                                   # - ZoneInfo → analysis/zones/models.py
│                                   # - ZoneAnalysisResult → analysis/zones/models.py
│                                   # - MACDZoneAnalyzer → indicators/analyzers/macd.py
│                                   # Оставить: helper functions (backward compat)
```

---

<a name="примеры"></a>
## Примеры использования

### Пример 1: MACD через PRELOADED (данные уже есть)

```python
from bquant.indicators.analyzers import MACDZoneAnalyzer

# df уже содержит колонки: 'macd', 'macd_signal', 'macd_hist'
analyzer = MACDZoneAnalyzer.from_preloaded()

result = analyzer.analyze(df)
print(f"Found {len(result.zones)} zones")
```

### Пример 2: MACD через CUSTOM (встроенный алгоритм)

```python
# MACD будет рассчитан автоматически
analyzer = MACDZoneAnalyzer.from_custom(fast=10, slow=24, signal=8)

result = analyzer.analyze(df)  # df содержит только OHLCV
print(f"Found {len(result.zones)} zones")
```

### Пример 3: MACD через pandas_ta

```python
# Использует pandas_ta.macd()
analyzer = MACDZoneAnalyzer.from_pandas_ta(fast=12, slow=26, signal=9)

result = analyzer.analyze(df)
print(f"Found {len(result.zones)} zones")
```

### Пример 4: Любой индикатор через UniversalIndicatorZoneAnalyzer

```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

# AO через pandas_ta
analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='pandas_ta',
        indicator_name='ao',
        indicator_params={},
        zone_detection=ZoneDetectionConfig(
            rules={'indicator_col': 'AO_5_34'},
            strategy_name='zero_crossing'
        )
    )
)

result = analyzer.analyze(df)
```

### Пример 5: Гибкий анализ с кастомными правилами (прямое использование слоев)

```python
from bquant.analysis.zones.detection import ZeroCrossingDetection, ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer

# Рассчитали индикатор (ваш код)
df['my_custom_indicator'] = (df['close'].rolling(10).mean() - 
                              df['close'].rolling(30).mean())

# Определили зоны с кастомными параметрами
detector = ZeroCrossingDetection()
zones = detector.detect_zones(
    df,
    ZoneDetectionConfig(
        min_duration=5,  # более длинные зоны
        zone_types=['bull', 'bear'],
        rules={'indicator_col': 'my_custom_indicator'},
        strategy_name='zero_crossing'
    )
)

print(f"Detected {len(zones)} zones")

# Проанализировали универсальным анализатором
analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df, perform_clustering=True)
```

### Пример 6: Кастомная стратегия определения зон

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer
from bquant.analysis.zones.models import ZoneInfo

@ZoneDetectionRegistry.register('volume_breakout')
class VolumeBreakoutDetection:
    """Зоны по volume spike + price breakout."""
    
    def detect_zones(self, data, config):
        zones = []
        
        # Ваша уникальная логика
        volume_threshold = config.rules.get('volume_multiplier', 2.0)
        volume_spike = data['volume'] > data['volume'].rolling(20).mean() * volume_threshold
        price_breakout = data['close'] > data['high'].rolling(20).max().shift(1)
        
        # Зоны где оба условия выполнены
        entries = volume_spike & price_breakout
        
        # ... создание ZoneInfo объектов ...
        
        return zones

# Использование
detector = VolumeBreakoutDetection()
zones = detector.detect_zones(
    df,
    ZoneDetectionConfig(
        min_duration=3,
        rules={'volume_multiplier': 2.5}
    )
)

analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df)
```

### Пример 7: RSI через talib с тремя типами зон

```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='talib',          # ← TA-Lib
        indicator_name='rsi',
        indicator_params={'timeperiod': 14},
        zone_detection=ZoneDetectionConfig(
            min_duration=3,
            zone_types=['overbought', 'neutral', 'oversold'],  # 3 типа!
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

# Статистика по типам зон
print(f"Overbought zones: {sum(1 for z in result.zones if z.type == 'overbought')}")
print(f"Neutral zones: {sum(1 for z in result.zones if z.type == 'neutral')}")
print(f"Oversold zones: {sum(1 for z in result.zones if z.type == 'oversold')}")
```

### Пример 8: Загрузка готовых зон (Preloaded)

```python
from bquant.analysis.zones.detection import load_preloaded_zones
from bquant.analysis.zones import UniversalZoneAnalyzer

# Быстрая загрузка через helper
zones = load_preloaded_zones(df, 'expert_zones.csv', min_duration=2)

analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df)

print(f"Loaded {len(zones)} zones from external dataset")

# Метаданные из датасета доступны
for zone in result.zones:
    if zone.features:
        print(f"Zone {zone.zone_id}: {zone.type}, "
              f"confidence={zone.features.get('confidence')}, "
              f"source={zone.features.get('source')}")
```

### Пример 9: PRELOADED индикатор + PRELOADED зоны (максимальная скорость)

```python
from bquant.indicators.analyzers import UniversalIndicatorZoneAnalyzer
from bquant.indicators.analyzers.base import IndicatorZoneConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

analyzer = UniversalIndicatorZoneAnalyzer(
    indicator_config=IndicatorZoneConfig(
        indicator_source='preloaded',      # индикатор уже в данных
        indicator_name='macd',
        zone_detection=ZoneDetectionConfig(
            strategy_name='preloaded',      # зоны из внешнего файла!
            rules={
                'zones_data': 'cached_zones.csv',
                'time_tolerance': '5min'
            }
        )
    )
)

# Оба компонента preloaded - нет расчетов, только merge и анализ
result = analyzer.analyze(df)

# Use case: кэширование результатов или A/B тестирование алгоритмов
```

---

<a name="преимущества"></a>
## Преимущества предложенной архитектуры

### 1. Разделение ответственностей (SRP)

| Слой | Ответственность | Размер | Независимость |
|------|-----------------|--------|---------------|
| **Zone Detection** | Как определять зоны | ~60 строк | Не знает про анализ |
| **Universal Analyzer** | Как анализировать зоны | ~120 строк | Не знает про индикаторы |
| **Indicator Facades** | Координация для индикатора | ~50 строк | Тонкий фасад |

### 2. Универсальность

- ✅ `UniversalZoneAnalyzer` не знает про MACD
- ✅ Работает с любыми зонами из любых источников
- ✅ Поддерживает > 2 типов зон
- ✅ Все стратегии метрик (swing, shape, divergence, volatility, volume) работают as-is

### 3. Расширяемость

- ✅ Новая стратегия зон = 1 класс + декоратор `@register`
- ✅ Новый индикатор = 1 фасад (20-50 строк)
- ✅ Все стратегии метрик переиспользуются автоматически
- ✅ Plugin-подобная архитектура

### 4. Dependency Injection

- ✅ Все компоненты инжектятся через конструктор
- ✅ Легко тестировать (mock любой компонент)
- ✅ Легко подменять реализации
- ✅ Конфигурируемость через DI

### 5. Чистый код

**MACDZoneAnalyzer** (после рефакторинга):
- ✅ ~60 строк (было 564) - **уменьшение на 89%**
- ✅ Только расчет индикатора + 3 строки координации
- ✅ Нет циклов обработки
- ✅ Нет адаптации форматов
- ✅ Чистый фасад

**UniversalZoneAnalyzer**:
- ✅ ~120 строк
- ✅ Только вызовы делегатов
- ✅ Нет своей логики анализа
- ✅ Чистый оркестратор

**PreloadedZonesDetection**:
- ✅ ~100 строк
- ✅ Простой merge по временным меткам
- ✅ Graceful handling (tolerance, skip missing)
- ✅ Автоматическая передача метаданных

### 6. Инкапсуляция преобразований

- ✅ Метод `ZoneInfo.to_analyzer_format()` инкапсулирует преобразование
- ✅ Нет адаптеров `_zone_to_dict()` в оркестраторах
- ✅ Единственный источник правды для формата

### 7. Поддержка внешних источников зон

**PreloadedZonesDetection как стратегия (не отдельный фасад):**
- ✅ Вписывается в единую архитектуру стратегий
- ✅ Используется через те же интерфейсы
- ✅ Комбинируется с любыми индикаторами
- ✅ Не усложняет API

**Практические применения:**
1. **Импорт из внешних систем:** MT5, TradingView, ProRealTime
2. **Кэширование результатов:** Сохранение зон для повторного анализа
3. **Ручная разметка:** Эксперты размечают зоны вручную
4. **A/B тестирование:** Сравнение алгоритмов детекции
5. **Бэктестинг стратегий:** Использование исторических зон
6. **Комбинирование источников:** Preloaded индикатор + preloaded зоны = max скорость

---

<a name="план-миграции"></a>
## План миграции

### Этап 0: Подготовка базовых моделей (1-2 дня)

**Цель:** Централизовать базовые структуры данных

**Задачи:**
1. [ ] Создать `bquant/analysis/zones/models.py`
   - Переместить `ZoneInfo` из `bquant/indicators/macd.py`
   - Переместить `ZoneAnalysisResult` из `bquant/indicators/macd.py`
   - Добавить метод `ZoneInfo.to_analyzer_format()`

2. [ ] Обновить импорты везде
   - `from bquant.analysis.zones.models import ZoneInfo, ZoneAnalysisResult`
   - В `macd.py`, `zone_features.py`, `sequence_analysis.py`
   - Во всех тестах

3. [ ] Проверить что все тесты проходят (507 тестов)

**Результат:** Базовые модели в правильном месте, нет зависимости от `indicators`

**Критерии готовности:**
- [ ] `ZoneInfo` доступен через `from bquant.analysis.zones.models import ZoneInfo`
- [ ] Метод `to_analyzer_format()` работает
- [ ] Все 507 тестов проходят

---

### Этап 1: Создание инфраструктуры детекции (3-5 дней)

**Цель:** Создать слои 1 и 2, не ломая текущий код

**Задачи:**

1. [ ] Создать `bquant/analysis/zones/detection/`
   - [ ] `base.py` - ZoneDetectionStrategy, ZoneDetectionConfig
   - [ ] `registry.py` - ZoneDetectionRegistry
   - [ ] `zero_crossing.py` - ZeroCrossingDetection
   - [ ] `line_crossing.py` - LineCrossingDetection
   - [ ] `threshold.py` - ThresholdDetection
   - [ ] `preloaded.py` - PreloadedZonesDetection + helper load_preloaded_zones()
   - [ ] `combined.py` - CombinedRulesDetection (опционально)

2. [ ] Создать `bquant/analysis/zones/analyzer.py`
   - [ ] `UniversalZoneAnalyzer` (чистый оркестратор БЕЗ адаптеров)

3. [ ] Обновить `ZoneFeaturesAnalyzer`
   - [ ] Добавить `extract_all_zones_features(zones: List[ZoneInfo])`
   - [ ] Обновить `extract_zone_features()` для поддержки Union[ZoneInfo, Dict]

4. [ ] Создать `bquant/indicators/analyzers/universal.py`
   - [ ] `UniversalIndicatorZoneAnalyzer` - работает с любым индикатором
   - [ ] Использует IndicatorFactory для всех источников

5. [ ] Unit-тесты для нового кода
   - [ ] `test_zone_detection_zero_crossing.py` (~10 тестов)
   - [ ] `test_zone_detection_line_crossing.py` (~10 тестов)  
   - [ ] `test_zone_detection_threshold.py` (~10 тестов)
   - [ ] `test_zone_detection_preloaded.py` (~12 тестов)
   - [ ] `test_universal_zone_analyzer.py` (~15 тестов)
   - [ ] `test_universal_indicator_zone_analyzer.py` (~15 тестов)
   - [ ] Интеграционные тесты с разными источниками (preloaded/custom/library)

**Результат:** Новая архитектура работает параллельно со старой + полная интеграция с IndicatorFactory

**Критерии готовности:**
- [ ] Все 5 стратегий детекции работают (zero_crossing, line_crossing, threshold, preloaded, combined)
- [ ] `UniversalZoneAnalyzer` работает с зонами от любой стратегии
- [ ] `PreloadedZonesDetection` корректно мерджит данные по времени
- [ ] +60 новых тестов, все проходят
- [ ] Старый `MACDZoneAnalyzer` продолжает работать

---

### Этап 2: Рефакторинг MACDZoneAnalyzer (3-5 дней)

**Цель:** Превратить MACD анализатор в тонкий фасад

**Задачи:**

1. [ ] Создать `bquant/indicators/analyzers/`
   - [ ] `base.py` - BaseIndicatorZoneAnalyzer
   - [ ] `macd.py` - новый MACDZoneAnalyzer (~50 строк)

2. [ ] Создать backward compatibility слой
   - [ ] Alias в старом `bquant/indicators/macd.py`
   - [ ] Deprecation warning
   - [ ] Redirect на новую реализацию

3. [ ] Обновить все импорты в проекте
   - [ ] В примерах (`examples/`)
   - [ ] В research notebooks
   - [ ] В документации

4. [ ] Обновить тесты
   - [ ] `test_macd_analyzer.py` - использовать новый API
   - [ ] Все 16 тестов должны проходить

**Результат:** MACD анализатор стал тонким фасадом (~50 строк)

**Критерии готовности:**
- [ ] `MACDZoneAnalyzer` < 100 строк
- [ ] Нет циклов обработки
- [ ] Нет адаптеров форматов
- [ ] Все тесты проходят

---

### Этап 3: Демонстрация универсальности (2-3 дня, опционально)

**Цель:** Показать универсальность на примерах других индикаторов

**Задачи:**

1. [ ] Создать `AOZoneAnalyzer` (~40 строк)
2. [ ] Создать `BollingerZoneAnalyzer` (~50 строк)
3. [ ] Создать `RSIZoneAnalyzer` (~40 строк) - с 3 типами зон
4. [ ] Создать примеры использования
5. [ ] Написать Extension Guide

**Результат:** Доказана универсальность архитектуры

---

### Этап 4: Очистка и документация (2-3 дня, опционально)

**Цель:** Финализировать миграцию

**Задачи:**

1. [ ] Убедиться что все работает
2. [ ] Удалить старый код из `bquant/indicators/macd.py`
3. [ ] Обновить API документацию
4. [ ] Обновить примеры
5. [ ] Написать Migration Guide

**Результат:** Чистая кодовая база с полной документацией

---

<a name="критерии"></a>
## Критерии успеха

### Технические критерии

1. ✅ `UniversalZoneAnalyzer` работает с зонами из любого источника
2. ✅ Добавление нового индикатора = 20-50 строк кода
3. ✅ Все существующие тесты проходят (507 тестов)
4. ✅ `MACDZoneAnalyzer` < 100 строк (чистый фасад)
5. ✅ Можно создавать кастомные стратегии зон без изменения ядра
6. ✅ API обратно совместим (старый код работает через deprecation)

### Архитектурные критерии

7. ✅ Нет адаптеров в оркестраторе (используется `ZoneInfo.to_analyzer_format()`)
8. ✅ Базовые модели в правильном месте (`bquant/analysis/zones/models.py`)
9. ✅ Нет циклов обработки в оркестраторе (только координация)
10. ✅ Dependency Injection работает (можно подменить любой компонент)
11. ✅ Расширяемость через регистрацию (декораторы `@register`)
12. ✅ Поддержка > 2 типов зон
13. ✅ **Интеграция с IndicatorFactory** (использует существующую инфраструктуру)
14. ✅ **Поддержка всех источников** индикаторов (preloaded/custom/library) (для RSI: overbought/neutral/oversold)

### Качественные критерии

13. ✅ Код читается как business-логика (не технические детали)
14. ✅ Каждый класс имеет одну ответственность (SRP)
15. ✅ Нет дублирования логики
16. ✅ Graceful degradation (работает с неполными данными)

---

<a name="сравнение"></a>
## Сравнение: До и После

### До (текущее состояние)

```python
# bquant/indicators/macd.py (564 строки)

@dataclass
class ZoneInfo:  # В неправильном месте!
    zone_id: int
    # ... поля ...

class MACDZoneAnalyzer:
    def calculate_macd_with_atr(self, df):      # 67 строк СВОЕЙ логики
        if len(df) > 1000:
            # NumPy версия
        else:
            # Стандартная версия
        # ... объединение результатов
    
    def identify_zones(self, df):               # 80 строк СВОЕЙ логики
        df['macd_sign'] = np.where(df['macd'] > 0, 1, -1)
        # ... алгоритм сегментации
        # ... создание ZoneInfo
    
    def _adapt_statistics_format(self, data):   # 45 строк ТЕХНИЧЕСКОГО ДОЛГА
        adapted['total_zones'] = total.get('total_zones', 0)
        # ... ручной маппинг
    
    def _zone_to_dict(self, zone):              # 20 строк АДАПТЕРА
        return {'zone_id': zone.zone_id, ...}
    
    def analyze_complete_modular(self, df):     # 135 строк с ЦИКЛАМИ
        df_with_ind = self.calculate_macd_with_atr(df)
        zones = self.identify_zones(df_with_ind)
        
        zones_features = []
        for zone in zones:  # ← ЦИКЛ в оркестраторе
            zone_dict = self._zone_to_dict(zone)
            ...

# Проблемы:
# - 40% монолитной логики (192 строки)
# - Циклы обработки в оркестраторе
# - Адаптеры форматов (технический долг)
# - Жесткая привязка к MACD
```

### После (предложенная архитектура)

```python
# bquant/analysis/zones/models.py (30 строк)
@dataclass
class ZoneInfo:
    # ... поля ...
    def to_analyzer_format(self): ...  # ← Инкапсулировано!

# bquant/analysis/zones/detection/zero_crossing.py (60 строк)
@ZoneDetectionRegistry.register('zero_crossing')
class ZeroCrossingDetection:
    def detect_zones(self, data, config):
        # ТОЛЬКО логика детекции по правилам!
        ...
        return zones  # List[ZoneInfo]

# bquant/analysis/zones/analyzer.py (120 строк)
class UniversalZoneAnalyzer:
    def __init__(self, features_analyzer=None, ...):  # ← DI
        self.features = features_analyzer or ...
        # ... все через DI
    
    def analyze_zones(self, zones, data):
        # ТОЛЬКО координация - БЕЗ циклов, БЕЗ адаптеров!
        zones_features = self.features.extract_all_zones_features(zones)
        statistics = self.features.analyze_zones_distribution(...)
        hypothesis_tests = self.hypotheses.run_all_tests(...)
        # ... только вызовы делегатов
        return ZoneAnalysisResult(...)

# bquant/indicators/analyzers/macd.py (50 строк)
class MACDZoneAnalyzer(BaseIndicatorZoneAnalyzer):
    def get_default_zone_config(self):
        return ZoneDetectionConfig(
            rules={'indicator_col': 'macd'},
            strategy_name='zero_crossing'
        )
    
    def calculate_indicator(self, df):
        # ТОЛЬКО расчет MACD + ATR (своя логика)
        ...
        return df_with_indicators
    
    # analyze() наследуется от базового класса (3 строки):
    # 1. df_with_ind = self.calculate_indicator(df)
    # 2. zones = self.detector.detect_zones(df_with_ind, config)
    # 3. return self.analyzer.analyze_zones(zones, df_with_ind)

# Преимущества:
# ✅ 0% монолитной логики (всё модульное)
# ✅ Нет циклов в оркестраторе
# ✅ Нет адаптеров (инкапсулировано)
# ✅ Универсальность (любые зоны)
# ✅ Расширяемость (plugin-like)
```

### Метрики улучшения

| Метрика | До | После | Улучшение |
|---------|-----|--------|-----------|
| **Размер MACDZoneAnalyzer** | 564 строки | ~50 строк | **-91%** |
| **Монолитная логика** | 34% (192 строки) | 0% (0 строк) | **-100%** |
| **Адаптеры форматов** | 3 метода (78 строк) | 0 методов | **-100%** |
| **Циклы обработки** | 2 цикла | 0 циклов | **-100%** |
| **Технический долг** | 45 строк маппинга | 0 строк | **-100%** |
| **Зависимость от индикатора** | Жесткая (MACD only) | Нет (универсально) | ✅ |
| **Поддержка типов зон** | 2 (bull/bear) | Любое количество | ✅ |
| **Расширяемость** | Копирование кода | Регистрация | ✅ |
| **Тестируемость** | Сложно (нет DI) | Легко (DI) | ✅ |

---

<a name="заключение"></a>
## Заключение

### Решаемые проблемы

Предложенная архитектура решает все выявленные проблемы:

1. ✅ **Разделение ответственностей** - 3 четких слоя
2. ✅ **Универсальность** - работает с любыми зонами
3. ✅ **Расширяемость** - plugin-like архитектура
4. ✅ **Чистый код** - нет монолитов и технического долга
5. ✅ **Dependency Injection** - полная тестируемость
6. ✅ **Инкапсуляция** - нет адаптеров в оркестраторе
7. ✅ **Правильное размещение** - models в analysis, не в indicators

### Ключевые улучшения

1. **Метод `ZoneInfo.to_analyzer_format()`** - убирает все адаптеры
2. **Прямая работа с `List[ZoneInfo]`** - упрощает API
3. **Централизация моделей** в `models.py` - правильная архитектура
4. **Стратегии детекции** - расширяемость через регистрацию
5. **DI во все компоненты** - тестируемость и гибкость

### Количественные результаты

- **MACDZoneAnalyzer:** 564 строки → 50 строк (**-91%**)
- **Монолитная логика:** 192 строки → 0 строк (**-100%**)
- **Адаптеры:** 3 метода → 0 методов (**-100%**)
- **Универсальность:** MACD only → Любые индикаторы (**∞%**)

### Открытые вопросы для обсуждения

1. **Naming:** `UniversalZoneAnalyzer` vs `ZoneAnalyzer`?
   - Рекомендация: `ZoneAnalyzer` (короче, universal подразумевается)

2. **BaseIndicatorZoneAnalyzer:** Использовать базовый класс или паттерн без наследования?
   - Рекомендация: Использовать базовый класс (упрощает реализацию)

3. **ZoneFeatures рефакторинг:** `macd_amplitude` → `indicator_amplitude` сейчас или позже?
   - Рекомендация: Отложить на Этап 2+ (не блокирует основную работу)

4. **Validation API:** Как интегрировать `ValidationSuite`?
   - Рекомендация: Через параметр `run_validation=True`, требует обертки

5. **Backward compatibility:** Сохранить старый `MACDZoneAnalyzer` как deprecated?
   - Рекомендация: Да, с deprecation warning и редиректом

### Следующий шаг

**Утверждение архитектуры и начало реализации Этапа 0** (подготовка базовых моделей).

**Оценка трудозатрат:**
- Этап 0: 1-2 дня
- Этап 1: 3-5 дней
- Этап 2: 3-5 дней
- **Итого:** 1-2 недели для полного рефакторинга

---

## Приложение: Интеграция с IndicatorFactory

### Поток данных с IndicatorFactory

```
DataFrame (OHLCV)
    ↓
IndicatorFactory.create(source, indicator, **params)
    ├─ source='preloaded'  → PreloadedIndicator (извлекает колонки)
    ├─ source='custom'     → CustomIndicator (встроенный алгоритм)
    ├─ source='pandas_ta'  → LibraryIndicator (pandas_ta.indicator())
    └─ source='talib'      → LibraryIndicator (talib.INDICATOR())
    ↓
indicator.calculate(df)
    ↓
IndicatorResult {name, data: DataFrame, config, metadata}
    ↓
BaseIndicatorZoneAnalyzer.calculate_indicator()
    ↓ объединение с исходными данными
DataFrame (OHLCV + indicator columns + ATR)
    ↓
ZoneDetectionStrategy.detect_zones(df, config)
    ↓
List[ZoneInfo]
    ↓
UniversalZoneAnalyzer.analyze_zones(zones, df)
    ↓
ZoneAnalysisResult
```

### Поддерживаемые индикаторы и стратегии зон

**Все зарегистрированные индикаторы работают через `UniversalIndicatorZoneAnalyzer`:**

| Индикатор | Источники | Zone Strategies | Типы зон |
|-----------|-----------|-----------------|----------|
| MACD | preloaded/custom/pandas_ta/talib | zero_crossing / **preloaded** | bull/bear |
| AO | pandas_ta/custom | zero_crossing / **preloaded** | bull/bear |
| RSI | custom/pandas_ta/talib | threshold / **preloaded** | overbought/neutral/oversold |
| Bollinger | custom/pandas_ta/talib | line_crossing / **preloaded** | bull/bear |
| Stochastic | custom/pandas_ta/talib | threshold / **preloaded** | overbought/neutral/oversold |
| CCI | custom/pandas_ta/talib | zero_crossing / threshold / **preloaded** | bull/bear or 3-level |
| Custom | - | combined / **preloaded** | Любые |
| ... | ... | ... | Любые |

**Ключевое:** 
- Любой индикатор из `IndicatorFactory.list_indicators()` доступен для зонального анализа
- **Любые зоны** можно загрузить через `preloaded` стратегию, независимо от индикатора

### Сценарии использования PRELOADED зон

| Use Case | Описание | Преимущество |
|----------|----------|--------------|
| **Импорт из MT5/TradingView** | Зоны размечены в другой системе, экспортированы в CSV | Использование внешних инструментов |
| **Кэширование расчетов** | Зоны рассчитаны один раз, сохранены для повторного анализа | Экономия времени на больших данных |
| **Экспертная разметка** | Трейдеры вручную разметили качественные зоны | Обучение на экспертных знаниях |
| **A/B тестирование** | Сравнение разных алгоритмов детекции на одних данных | Выбор лучшего алгоритма |
| **Исторические зоны** | Использование зон из прошлых периодов для бэктестинга | Валидация стратегий |
| **Гибридный подход** | Комбинация автоматической детекции + экспертной коррекции | Лучшее качество разметки |

### Примеры интеграции

**Пример 1: Автоматический выбор источника**
```python
from bquant.indicators.analyzers import SmartIndicatorZoneAnalyzer

# Умный анализатор автоматически определит источник
analyzer = SmartIndicatorZoneAnalyzer(
    indicator_name='macd',
    indicator_params={'fast': 12, 'slow': 26},
    required_columns=['macd', 'macd_signal', 'macd_hist'],  # для preloaded
    zone_detection_config=ZoneDetectionConfig(
        rules={'indicator_col': 'macd'},
        strategy_name='zero_crossing'
    )
)

# Если df содержит MACD колонки → использует PRELOADED
# Если нет → вычисляет через CUSTOM
result = analyzer.analyze(df)
```

**Пример 2: Комбинация индикаторов из разных источников**
```python
# MACD через custom + RSI через talib
from bquant.indicators import IndicatorFactory

# Рассчитываем индикаторы
macd_indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26)
rsi_indicator = IndicatorFactory.create('talib', 'rsi', timeperiod=14)

df_with_macd = macd_indicator.calculate(df).data
df_with_rsi = rsi_indicator.calculate(df).data

# Объединяем
df_combined = df.copy()
for col in df_with_macd.columns:
    df_combined[col] = df_with_macd[col]
for col in df_with_rsi.columns:
    df_combined[col] = df_with_rsi[col]

# Комбинированные правила зон
from bquant.analysis.zones.detection import CombinedRulesDetection, ZoneDetectionConfig

detector = CombinedRulesDetection()
zones = detector.detect_zones(
    df_combined,
    ZoneDetectionConfig(
        min_duration=3,
        rules={
            'conditions': [
                lambda df: df['macd'] > 0,      # MACD бычий
                lambda df: df['RSI'] < 70       # RSI не перекуплен
            ],
            'logic': 'AND'
        },
        strategy_name='combined'
    )
)

# Анализ комбинированных зон
from bquant.analysis.zones import UniversalZoneAnalyzer
analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df_combined)
```

**Пример 3: Формат датасета PRELOADED зон**

**Минимальный CSV (обязательные поля):**
```csv
zone_id,type,start_time,end_time
0,bull,2024-01-15 10:00:00,2024-01-15 15:30:00
1,bear,2024-01-15 15:30:00,2024-01-16 09:00:00
2,bull,2024-01-16 09:00:00,2024-01-16 14:00:00
```

**Расширенный CSV (с метаданными):**
```csv
zone_id,type,start_time,end_time,confidence,source,signal_strength,expert_comment
0,bull,2024-01-15 10:00:00,2024-01-15 15:30:00,0.95,MT5,strong,confirmed_breakout
1,bear,2024-01-15 15:30:00,2024-01-16 09:00:00,0.87,manual,medium,reversal_pattern
2,bull,2024-01-16 09:00:00,2024-01-16 14:00:00,0.92,algo_v2,strong,divergence_entry
```

**Примечания:**
- Обязательные поля: `zone_id`, `type`, `start_time`, `end_time`
- Временные метки: ISO 8601 формат или любой, распознаваемый `pd.to_datetime()`
- Дополнительные колонки: автоматически добавляются в `ZoneInfo.features`
- `duration`, `start_idx`, `end_idx`: вычисляются автоматически при merge с данными

---

**Дата создания:** 2025-10-15  
**Последнее обновление:** 2025-10-17  
**Авторы:** AI Assistant (Claude Sonnet 4.5), Ivan  
**Версия:** v3  
**Статус документа:** Proposal - интегрированы:
- IndicatorFactory и система индикаторов BQuant
- PreloadedZonesDetection как стратегия Слоя 1
- Поддержка импорта зон из внешних систем

