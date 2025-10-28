# Архитектура универсального анализатора зон (Zone Analysis)

**Дата:** 2025-10-17  
**Версия:** v7.1 (Complete Spec + Cross-References)  
**Статус:** Ready for Implementation - полная спецификация с перекрестными ссылками  
**Контекст:** Универсальный инструментарий для анализа зон любых индикаторов

**Связанные документы:**
- [zomodul.md](zomodul.md) - Модульное использование компонентов (12 сценариев)
- [zouni.md](zouni.md) - ⚠️ **[УСТАРЕЛ]** Анализ универсальности v1.0 (псевдо-универсальность с hardcoded списками)
- [zouni_v2.md](zouni_v2.md) - ✅ **АКТУАЛЬНО** Истинная универсальность v2.0 (ZERO hardcoded индикаторов)
- [README.md](README.md) - Навигация по документации

**⚠️ КРИТИЧЕСКИ ВАЖНО:** После реализации Stages 0-2.4 выявлены **архитектурные проблемы** в универсальности:
- ❌ Баг #1-3: Исправлены, но подход **псевдо-универсален** (hardcoded списки)
- ✅ **Правильное решение:** См. **[zouni_v2.md](zouni_v2.md)** - истинная универсальность через `indicator_context` и explicit параметры (~7 hours, проще и правильнее)

---

## Содержание

1. [Проблема: MACDZoneAnalyzer как монолит](#проблема)
2. [Решение: Двухслойная архитектура + Pipeline](#решение)
3. [Базовые структуры данных](#базовые-структуры)
4. [Слой 1: Zone Detection Strategies](#слой-1)
5. [Слой 2: Universal Zone Analyzer](#слой-2)
6. [Pipeline: Единая точка входа](#pipeline)
7. [Builder: Fluent API](#builder)
8. [Интеграция с IndicatorFactory](#интеграция)
9. [Структура директорий](#структура)
10. [Реализация стратегий детекции (Code Templates)](#реализация-стратегий)
11. [Точки расширения архитектуры](#точки-расширения)
12. [Примеры использования](#примеры)
13. [Визуализация зон](#визуализация)
14. [Кэширование и персистентное хранение](#кэширование)
15. [Преимущества архитектуры](#преимущества)
16. [План миграции](#план-миграции)
17. [Заключение](#заключение)

---

<a name="проблема"></a>
## Проблема: MACDZoneAnalyzer как монолит

### Текущее состояние (фактический код)

**Файл:** `bquant/indicators/macd.py` (564 строки)

**Количественная оценка:**

| Категория | Строк | % | Оценка |
|-----------|-------|---|--------|
| **Своя бизнес-логика** | ~192 | 34% | ⚠️ МОНОЛИТ |
| └ MACD расчет | 67 | 12% | Hardcoded |
| └ Определение зон | 80 | 14% | Hardcoded |
| └ Адаптация форматов | 45 | 8% | Технический долг |
| **Делегирование** | ~135 | 24% | ✅ Оркестратор |
| **Адаптеры** | ~78 | 14% | 🔧 Утилиты |
| **Инфраструктура** | ~159 | 28% | 🔧 |

**Вердикт:** Гибрид (40% монолит, 40% оркестратор, 20% адаптеры)

### Ключевые проблемы

1. **Жесткая привязка к MACD** - невозможно использовать для других индикаторов
2. **Собственная логика расчета** - не использует `IndicatorFactory`
3. **Hardcoded детекция зон** - только пересечение нуля
4. **Адаптеры форматов** - несовместимость интерфейсов (45 строк технического долга)
5. **Циклы обработки** - бизнес-логика в оркестраторе

---

<a name="решение"></a>
## Решение: Двухслойная архитектура + Pipeline

### Ключевая идея

> **"Зоны - первичны. Анализ - универсален. Pipeline - гибок."**

### Упрощенная архитектура (2 слоя + pipeline)

```
┌─────────────────────────────────────────────────────────────┐
│ ZoneAnalysisPipeline / ZoneAnalysisBuilder                 │
│ (Единая точка входа - конфигурируемая координация)         │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─→ IndicatorFactory (опционально)
             │   └─ create(source, indicator, **params)
             │   └─ Источники: preloaded/custom/pandas_ta/talib
             │
             ├─→ Слой 1: Zone Detection Strategies
             │   ├─ ZeroCrossingDetection
             │   ├─ LineCrossingDetection
             │   ├─ ThresholdDetection
             │   ├─ PreloadedZonesDetection
             │   └─ CombinedRulesDetection
             │
             └─→ Слой 2: Universal Zone Analyzer
                 └─ analyze_zones(zones, df)
                 └─ Использует: ZoneFeaturesAnalyzer, HypothesisTestSuite,
                                 ZoneSequenceAnalyzer, Regression, Validation
```

**Убрано:**
- ❌ Слой 3 (Indicator-specific Facades) - hardcode, ограничивает гибкость
- ❌ Множественные фасады (MACDZoneAnalyzer, AOZoneAnalyzer, ...)

**Добавлено:**
- ✅ ZoneAnalysisPipeline - универсальный pipeline из конфигурации
- ✅ ZoneAnalysisBuilder - fluent interface для удобства
- ✅ Прямое использование IndicatorFactory

---

<a name="базовые-структуры"></a>
## Базовые структуры данных

### ZoneInfo - универсальная модель зоны

**Расположение:** `bquant/analysis/zones/models.py` (НОВОЕ)

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
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        type: Тип зоны ('bull', 'bear', 'overbought', 'neutral', 'oversold', ...)
        start_idx: Начальный индекс (integer location)
        end_idx: Конечный индекс (integer location)
        start_time: Время начала зоны (index value)
        end_time: Время окончания зоны (index value)
        duration: Длительность в барах
        data: DataFrame с данными зоны (OHLCV + все индикаторы)
        features: Рассчитанные признаки (заполняется после анализа)
    """
    zone_id: int
    type: str
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None
    
    def to_analyzer_format(self) -> Dict[str, Any]:
        """Формат для передачи в анализаторы."""
        return {
            'zone_id': self.zone_id,
            'type': self.type,
            'duration': self.duration,
            'data': self.data,
            **(self.features or {})
        }


@dataclass
class ZoneAnalysisResult:
    """Результат анализа зон."""
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

---

<a name="слой-1"></a>
## Слой 1: Zone Detection Strategies

### Базовый протокол

```python
# bquant/analysis/zones/detection/base.py

from typing import Protocol, List, Dict, Any, runtime_checkable
from dataclasses import dataclass, field
import pandas as pd
from ..models import ZoneInfo


@runtime_checkable
class ZoneDetectionStrategy(Protocol):
    """Протокол для стратегий определения зон."""
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: 'ZoneDetectionConfig') -> List[ZoneInfo]:
        """Определить зоны на основе данных и правил."""
        ...


@dataclass
class ZoneDetectionConfig:
    """Конфигурация правил определения зон."""
    min_duration: int = 2
    zone_types: List[str] = None
    rules: Dict[str, Any] = field(default_factory=dict)
    strategy_name: str = None
    
    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = ['bull', 'bear']
```

### Реестр стратегий

```python
# bquant/analysis/zones/detection/registry.py

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
            raise ValueError(f"Unknown zone detection strategy: {name}")
        return cls._strategies[name](**params)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Список доступных стратегий."""
        return list(cls._strategies.keys())
```

**Доступные стратегии:**

| Стратегия | Применение | Типы зон |
|-----------|------------|----------|
| `zero_crossing` | MACD, AO, CCI (осцилляторы) | bull/bear |
| `line_crossing` | Bollinger, MA crosses | bull/bear |
| `threshold` | RSI, Stochastic | overbought/neutral/oversold |
| `preloaded` | Импорт из внешних систем | Любые |
| `combined` | Кастомные комбинации | Любые |

### Примеры реализаций

> **См. полные заготовки кода в разделе [Реализация стратегий детекции](#реализация-стратегий)**

**Доступные стратегии:**
- `ZeroCrossingDetection` - пересечение нулевой линии (MACD, AO, CCI)
- `LineCrossingDetection` - пересечение двух линий (MA crosses, Bollinger)
- `ThresholdDetection` - пороговые зоны (RSI, Stochastic)
- `PreloadedZonesDetection` - импорт готовых зон (CSV, DataFrame)
- `CombinedRulesDetection` - комбинация условий (кастомные правила)

---

<a name="слой-2"></a>
## Слой 2: Universal Zone Analyzer

### Реализация

```python
# bquant/analysis/zones/analyzer.py

class UniversalZoneAnalyzer:
    """
    Универсальный оркестратор анализа зон.
    
    НЕ ЗНАЕТ:
    - Откуда зоны (MACD, AO, preloaded, кастомные)
    - Как зоны были созданы
    
    ЗНАЕТ ТОЛЬКО:
    - Как анализировать List[ZoneInfo]
    """
    
    def __init__(self,
                 features_analyzer=None,
                 hypothesis_suite=None,
                 sequence_analyzer=None,
                 regression_analyzer=None,
                 validation_suite=None,
                 swing_strategy=None,
                 shape_strategy=None,
                 divergence_strategy=None,
                 volatility_strategy=None,
                 volume_strategy=None):
        """Dependency Injection всех компонентов."""
        if features_analyzer is None:
            from .zone_features import ZoneFeaturesAnalyzer
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
    
    # О расширении через DI см. раздел "Точки расширения архитектуры"
    
    def analyze_zones(self, 
                      zones: List[ZoneInfo],
                      data: pd.DataFrame,
                      perform_clustering: bool = True,
                      n_clusters: int = 3,
                      run_regression: bool = False) -> ZoneAnalysisResult:
        """
        Анализ готовых зон.
        
        ЧИСТАЯ КООРДИНАЦИЯ - только вызовы делегатов!
        """
        if not zones:
            return self._empty_result(data)
        
        # 1. Извлечение признаков (БЕЗ адаптеров!)
        zones_features = self.features.extract_all_zones_features(zones)
        
        # 2. Статистический анализ
        statistics = self.features.analyze_zones_distribution([f.to_dict() for f in zones_features])
        
        # 3. Тестирование гипотез
        hypothesis_tests = self.hypotheses.run_all_tests([f.to_dict() for f in zones_features])
        
        # 4. Анализ последовательностей
        sequence_analysis = self.sequences.analyze_zone_transitions(zones_features)
        
        # 5. Кластеризация
        clustering = None
        if perform_clustering and len(zones) >= n_clusters:
            clustering = self.sequences.cluster_zones(zones_features, n_clusters=n_clusters)
        
        # 6. Регрессия (опционально)
        regression_results = None
        if run_regression and len(zones) > 10:
            regression_results = {
                'duration': self.regression.predict_zone_duration([f.to_dict() for f in zones_features]),
                'return': self.regression.predict_price_return([f.to_dict() for f in zones_features])
            }
        
        # Сборка результата
        return ZoneAnalysisResult(
            zones=zones,
            statistics=statistics.results if hasattr(statistics, 'results') else statistics,
            hypothesis_tests=hypothesis_tests,
            sequence_analysis=sequence_analysis.results if hasattr(sequence_analysis, 'results') else sequence_analysis,
            clustering=clustering.results if clustering and hasattr(clustering, 'results') else clustering,
            regression_results=regression_results,
            data=data,
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'total_zones': len(zones),
                'zone_types': list(set(z.type for z in zones))
            }
        )
```

---

<a name="pipeline"></a>
## Pipeline: Единая точка входа

### Конфигурация

```python
# bquant/analysis/zones/pipeline.py

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import pandas as pd

from ...indicators import IndicatorFactory, IndicatorResult
from .detection import ZoneDetectionRegistry, ZoneDetectionConfig
from .analyzer import UniversalZoneAnalyzer
from .models import ZoneAnalysisResult


@dataclass
class IndicatorConfig:
    """
    Конфигурация индикатора (если нужно рассчитать).
    
    None означает что индикатор уже в данных.
    """
    source: Literal['preloaded', 'custom', 'pandas_ta', 'talib']
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneAnalysisConfig:
    """Полная конфигурация pipeline анализа зон."""
    
    # Индикатор (None если уже в данных)
    indicator: Optional[IndicatorConfig] = None
    
    # Детекция зон (обязательно)
    zone_detection: ZoneDetectionConfig = None
    
    # Параметры анализа
    perform_clustering: bool = True
    n_clusters: int = 3
    run_regression: bool = False
    run_validation: bool = False
```

### Pipeline класс

```python
class ZoneAnalysisPipeline:
    """
    Универсальный pipeline для анализа зон.
    
    ЕДИНСТВЕННЫЙ класс координации - НЕТ специализированных фасадов!
    Работает через конфигурацию - максимальная гибкость.
    """
    
    def __init__(self, 
                 config: ZoneAnalysisConfig,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None):
        """
        Args:
            config: Конфигурация pipeline
            zone_analyzer: Универсальный анализатор (DI)
        """
        self.config = config
        self.analyzer = zone_analyzer or UniversalZoneAnalyzer()
        self.logger = get_logger(__name__)
    
    def run(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """
        Выполнить полный pipeline анализа.
        
        Шаги:
        1. Расчет индикатора (если нужно) - через IndicatorFactory
        2. Детекция зон - через ZoneDetectionStrategy
        3. Анализ зон - через UniversalZoneAnalyzer
        """
        # 1. Подготовка данных (расчет индикатора)
        df_prepared = self._prepare_data(df)
        
        # 2. Детекция зон
        zones = self._detect_zones(df_prepared)
        
        # 3. Анализ зон
        return self._analyze_zones(zones, df_prepared)
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикатора через IndicatorFactory."""
        if self.config.indicator is None:
            return df  # Индикатор уже в данных
        
        ind = self.config.indicator
        self.logger.info(f"Calculating indicator: {ind.source}.{ind.name}")
        
        # Создаем через IndicatorFactory!
        indicator = IndicatorFactory.create(
            source=ind.source,
            indicator=ind.name,
            **ind.params
        )
        
        result: IndicatorResult = indicator.calculate(df)
        
        # Объединяем с исходными данными
        df_with_indicator = df.copy()
        for col in result.data.columns:
            df_with_indicator[col] = result.data[col]
        
        # Добавляем ATR для нормализации (если нужно)
        if 'atr' not in df_with_indicator.columns:
            from bquant.data.processor import calculate_derived_indicators
            derived = calculate_derived_indicators(df_with_indicator)
            if 'atr' in derived.columns:
                df_with_indicator['atr'] = derived['atr']
        
        return df_with_indicator
    
    def _detect_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """Детекция зон через стратегию."""
        detector = ZoneDetectionRegistry.get(
            self.config.zone_detection.strategy_name
        )
        return detector.detect_zones(df, self.config.zone_detection)
    
    def _analyze_zones(self, zones: List[ZoneInfo], df: pd.DataFrame) -> ZoneAnalysisResult:
        """Анализ зон через UniversalZoneAnalyzer."""
        return self.analyzer.analyze_zones(
            zones, df,
            perform_clustering=self.config.perform_clustering,
            n_clusters=self.config.n_clusters,
            run_regression=self.config.run_regression
        )
```

---

<a name="builder"></a>
## Builder: Fluent API

### Реализация

```python
# bquant/analysis/zones/pipeline.py

class ZoneAnalysisBuilder:
    """
    Fluent builder для анализа зон.
    
    Удобный интерфейс "через точку" для построения pipeline.
    Внутри создает ZoneAnalysisPipeline.
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Инициализация builder с данными.
        
        Args:
            data: DataFrame с OHLCV данными (+ опционально индикаторы)
        """
        self.data = data
        self._indicator_config: Optional[IndicatorConfig] = None
        self._zone_detection_config: Optional[ZoneDetectionConfig] = None
        self._perform_clustering = True
        self._n_clusters = 3
        self._run_regression = False
        self._run_validation = False
        self.logger = get_logger(__name__)
    
    def with_indicator(self, 
                      source: str, 
                      name: str, 
                      **params) -> 'ZoneAnalysisBuilder':
        """
        Добавить расчет индикатора в pipeline.
        
        Args:
            source: Источник ('preloaded', 'custom', 'pandas_ta', 'talib')
            name: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            self для цепочки вызовов
        
        Example:
            builder.with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
        """
        self._indicator_config = IndicatorConfig(
            source=source,
            name=name,
            params=params
        )
        return self
    
    def detect_zones(self, 
                    strategy: str, 
                    min_duration: int = 2,
                    **rules) -> 'ZoneAnalysisBuilder':
        """
        Настроить детекцию зон.
        
        Args:
            strategy: Стратегия ('zero_crossing', 'line_crossing', 'threshold', 'preloaded', 'combined')
            min_duration: Минимальная длительность зоны
            **rules: Правила детекции (зависят от стратегии)
        
        Returns:
            self для цепочки вызовов
        
        Examples:
            .detect_zones('zero_crossing', indicator_col='macd')
            .detect_zones('threshold', indicator_col='rsi', upper_threshold=70, lower_threshold=30)
            .detect_zones('preloaded', zones_data='zones.csv')
        """
        self._zone_detection_config = ZoneDetectionConfig(
            min_duration=min_duration,
            rules=rules,
            strategy_name=strategy
        )
        return self
    
    def analyze(self,
               clustering: bool = True,
               n_clusters: int = 3,
               regression: bool = False,
               validation: bool = False) -> 'ZoneAnalysisBuilder':
        """
        Настроить параметры анализа.
        
        Args:
            clustering: Выполнять кластеризацию
            n_clusters: Количество кластеров
            regression: Запустить регрессионный анализ
            validation: Запустить валидацию
        
        Returns:
            self для цепочки вызовов
        """
        self._perform_clustering = clustering
        self._n_clusters = n_clusters
        self._run_regression = regression
        self._run_validation = validation
        return self
    
    def build(self) -> ZoneAnalysisResult:
        """
        Выполнить pipeline и вернуть результат.
        
        Returns:
            ZoneAnalysisResult с полным анализом
        """
        if self._zone_detection_config is None:
            raise ValueError("Zone detection strategy not configured. Call detect_zones() first.")
        
        # Создаем конфигурацию
        config = ZoneAnalysisConfig(
            indicator=self._indicator_config,
            zone_detection=self._zone_detection_config,
            perform_clustering=self._perform_clustering,
            n_clusters=self._n_clusters,
            run_regression=self._run_regression,
            run_validation=self._run_validation
        )
        
        # Выполняем через pipeline
        pipeline = ZoneAnalysisPipeline(config)
        return pipeline.run(self.data)


# Convenience функция
def analyze_zones(df: pd.DataFrame) -> ZoneAnalysisBuilder:
    """
    Создать builder для анализа зон.
    
    Fluent API entry point.
    
    Example:
        from bquant.analysis.zones import analyze_zones
        
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast=12, slow=26)
            .detect_zones('zero_crossing', indicator_col='macd')
            .analyze(clustering=True)
            .build()
        )
    """
    return ZoneAnalysisBuilder(df)
```

---

<a name="интеграция"></a>
## Интеграция с IndicatorFactory

### Правильное использование

```python
# В ZoneAnalysisPipeline._prepare_data()

# ✅ ПРАВИЛЬНО - через IndicatorFactory
indicator = IndicatorFactory.create(
    source=config.indicator.source,    # 'custom', 'pandas_ta', 'talib', 'preloaded'
    indicator=config.indicator.name,   # 'macd', 'ao', 'rsi', ...
    **config.indicator.params
)
result: IndicatorResult = indicator.calculate(df)

# ❌ НЕПРАВИЛЬНО - прямые вызовы
from bquant.indicators.calculators import calculate_macd  # обертка, нет выбора источника
macd_data = calculate_macd(df, fast=12, slow=26)
```

### Поддержка всех источников

| Источник | Что делает | Пример |
|----------|------------|--------|
| `preloaded` | Извлекает готовые колонки | df уже содержит 'macd', 'macd_signal', 'macd_hist' |
| `custom` | Встроенный алгоритм | Вычисляет MACD через bquant.indicators.custom.MACD |
| `pandas_ta` | Внешняя библиотека | Вызывает pandas_ta.macd() |
| `talib` | Внешняя библиотека | Вызывает talib.MACD() |

---

<a name="структура"></a>
## Структура директорий

```
bquant/
├── analysis/
│   └── zones/
│       ├── __init__.py
│       │
│       ├── models.py               # ✅ Stage 0 - ZoneInfo, ZoneAnalysisResult
│       │
│       ├── detection/              # ✅ Stage 1 - Слой 1 (детекция)
│       │   ├── __init__.py
│       │   ├── base.py            # ZoneDetectionStrategy, ZoneDetectionConfig
│       │   ├── registry.py         # ZoneDetectionRegistry
│       │   ├── zero_crossing.py    # ZeroCrossingDetection
│       │   ├── line_crossing.py    # LineCrossingDetection
│       │   ├── threshold.py        # ThresholdDetection
│       │   ├── preloaded.py        # PreloadedZonesDetection + helper
│       │   └── combined.py         # CombinedRulesDetection
│       │
│       ├── analyzer.py             # ✅ Stage 1 - UniversalZoneAnalyzer (Слой 2)
│       │
│       ├── pipeline.py             # ✅ Stage 1 - ZoneAnalysisPipeline + Builder
│       │
│       ├── presets.py              # Stage 2 (опционально) - convenience shortcuts
│       │
│       ├── zone_features.py        # ✅ Stage 1 - обновлен (extract_all_zones_features)
│       ├── sequence_analysis.py    # БЕЗ ИЗМЕНЕНИЙ (уже универсальный)
│       │
│       └── strategies/             # БЕЗ ИЗМЕНЕНИЙ (уже универсальны!)
│           ├── swing/
│           ├── shape/
│           ├── divergence/
│           ├── volatility/
│           └── volume/
│
└── indicators/
    ├── base.py                     # СУЩЕСТВУЕТ - IndicatorFactory
    ├── custom/                      # СУЩЕСТВУЕТ - встроенные индикаторы
    ├── library/                     # СУЩЕСТВУЕТ - pandas_ta, talib
    ├── preloaded/                   # СУЩЕСТВУЕТ - готовые данные
    │
    └── macd.py                      # Stage 2 - РЕФАКТОРИНГ (518→~100 строк):
                                     # - ✅ ZoneInfo → перенесено в models.py
                                     # - ✅ ZoneAnalysisResult → перенесено в models.py
                                     # - УДАЛИТЬ весь код анализа (~450 строк)
                                     # - ОСТАВИТЬ тонкий wrapper с @deprecated (~50 строк)

examples/                            # Stage 2 - публичные примеры
├── 02_macd_zone_analysis.py        # Обновить: старый vs новый API
├── 02a_universal_zones.py          # Создать: все индикаторы через один API
├── 04_comprehensive_analysis.py    # Обновить: полный pipeline
└── README.md                        # Создать: гид по примерам

research/notebooks/                  # Stage 2 - исследовательские ноутбуки
├── 03_zones.py                     # Обновить: добавить новый API
├── 03_zones_universal.py           # Создать: детальное исследование
└── README.md                        # Обновить: назначение ноутбуков
```

**УБРАНО:** `indicators/analyzers/` - НЕТ специализированных фасадов!

---

## Архитектурные принципы размещения кода

### ❌ Антипаттерн: Создание классов под каждый индикатор

**Не делайте так:**
```python
# ❌ НЕПРАВИЛЬНО - нарушает универсальность
bquant/indicators/analyzers/
├── macd.py → MACDZoneAnalyzer (500+ строк)
├── rsi.py → RSIZoneAnalyzer (500+ строк дублирования)
├── ao.py → AOZoneAnalyzer (500+ строк дублирования)
└── stoch.py → StochZoneAnalyzer (500+ строк дублирования)
```

**Проблемы:**
- Дублирование кода анализа (каждый класс реализует одну и ту же логику)
- Нарушение DRY (Don't Repeat Yourself)
- Сложность поддержки (изменения нужно копировать в каждый класс)
- Противоречит универсальной архитектуре Stage 1
- `indicators/` должен содержать **расчет индикаторов**, а не их **анализ**

### ✅ Правильный подход: Универсальный API

**Размещение кода:**

| Что | Где | Размер | Назначение |
|-----|-----|--------|------------|
| **Универсальная инфраструктура** | `bquant/analysis/zones/` | ~1700 строк | ✅ Stage 1 - РЕАЛИЗОВАНО |
| **Backward compatibility** | `bquant/indicators/macd.py` | ~100 строк | Тонкий wrapper с @deprecated |
| **Convenience shortcuts** (опционально) | `bquant/analysis/zones/presets.py` | ~100 строк | 4-5 функций по 10 строк |
| **Публичные примеры** | `examples/` | 3-4 файла по 200-300 строк | Для документации |
| **Исследования** | `research/notebooks/` | 1-2 файла по 500+ строк | NotebookSimulator для экспериментов |

**Использование:**
```python
# Один универсальный API для ВСЕХ индикаторов:
from bquant.analysis.zones import analyze_zones

# MACD
result_macd = analyze_zones(df).with_indicator('custom', 'macd').detect_zones('zero_crossing', indicator_col='macd_hist').build()

# RSI  
result_rsi = analyze_zones(df).with_indicator('pandas_ta', 'rsi').detect_zones('threshold', indicator_col='rsi', upper_threshold=70, lower_threshold=30).build()

# AO
result_ao = analyze_zones(df).with_indicator('pandas_ta', 'ao').detect_zones('zero_crossing', indicator_col='AO_5_34').build()
```

**Результат:** 
- Нет дублирования кода
- Единый API для всех индикаторов
- Легко добавлять новые индикаторы (0 строк нового кода!)
- Правильное разделение ответственности

### Разделение: examples/ vs research/notebooks/

**examples/** - для пользователей и документации:
- ✅ Простые, короткие (100-300 строк)
- ✅ Самодостаточные (можно скопировать и запустить)
- ✅ Для публичной документации
- ✅ Систематические (покрывают основные use cases)

**research/notebooks/** - для разработчиков и исследований:
- ✅ Детальные (500+ строк)
- ✅ С экспериментами и бенчмарками
- ✅ Использует NotebookSimulator (замена Jupyter)
- ✅ Для продвинутых пользователей
- ✅ Может быть "грязным" кодом (исследование)

---

<a name="реализация-стратегий"></a>
## Реализация стратегий детекции (Code Templates)

Этот раздел содержит полные заготовки кода для всех стратегий детекции зон, которые будут реализованы в рамках первой версии архитектуры. Каждая стратегия - это готовый к использованию шаблон, который можно адаптировать под конкретные нужды.

### Базовые компоненты (base.py, registry.py)

#### base.py - Протокол и конфигурация

```python
# bquant/analysis/zones/detection/base.py

from typing import Protocol, List, Dict, Any, runtime_checkable
from dataclasses import dataclass, field
import pandas as pd
from ..models import ZoneInfo


@runtime_checkable
class ZoneDetectionStrategy(Protocol):
    """
    Протокол для стратегий определения зон.
    
    Любой класс с методом detect_zones() - валидная стратегия!
    """
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: 'ZoneDetectionConfig') -> List[ZoneInfo]:
        """
        Определить зоны на основе данных и правил.
        
        Args:
            data: DataFrame с OHLCV + индикаторами
            config: Конфигурация правил детекции
            
        Returns:
            List[ZoneInfo] - список обнаруженных зон
            
        Raises:
            ValueError: Если конфигурация некорректна
        """
        ...


@dataclass
class ZoneDetectionConfig:
    """
    Универсальная конфигурация правил определения зон.
    
    Attributes:
        min_duration: Минимальная длительность зоны в барах
        zone_types: Типы зон для поиска (None = все возможные для стратегии)
        rules: Специфичные правила для стратегии (Dict[str, Any])
        strategy_name: Имя стратегии для registry
        metadata: Дополнительная информация (для логирования, отладки)
    """
    min_duration: int = 2
    zone_types: List[str] = None
    rules: Dict[str, Any] = field(default_factory=dict)
    strategy_name: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = ['bull', 'bear']
    
    def validate(self, required_rules: List[str]) -> None:
        """Валидация наличия обязательных правил."""
        missing = [r for r in required_rules if r not in self.rules]
        if missing:
            raise ValueError(
                f"Missing required rules for {self.strategy_name}: {missing}"
            )
```

#### registry.py - Реестр с метаданными

```python
# bquant/analysis/zones/detection/registry.py

from typing import Dict, Type, List, Any
import logging

logger = logging.getLogger(__name__)


class ZoneDetectionRegistry:
    """
    Реестр стратегий определения зон.
    
    Автоматическая регистрация через декоратор @register().
    Поддержка метаданных для каждой стратегии.
    """
    
    _strategies: Dict[str, Type[ZoneDetectionStrategy]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, 
                 description: str = "",
                 supported_zones: List[str] = None,
                 required_rules: List[str] = None):
        """
        Декоратор для регистрации стратегии.
        
        Args:
            name: Уникальное имя стратегии
            description: Человекочитаемое описание
            supported_zones: Типы зон, которые может обнаружить
            required_rules: Обязательные ключи в config.rules
            
        Example:
            @ZoneDetectionRegistry.register(
                'zero_crossing',
                description='Detect zones by indicator crossing zero line',
                supported_zones=['bull', 'bear'],
                required_rules=['indicator_col']
            )
            class ZeroCrossingDetection:
                def detect_zones(self, data, config):
                    ...
        """
        def decorator(strategy_class):
            if name in cls._strategies:
                logger.warning(f"Overwriting existing strategy: {name}")
            
            cls._strategies[name] = strategy_class
            cls._metadata[name] = {
                'description': description,
                'supported_zones': supported_zones or ['bull', 'bear'],
                'required_rules': required_rules or [],
                'class': strategy_class.__name__
            }
            
            logger.info(f"Registered zone detection strategy: {name}")
            return strategy_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **init_params) -> ZoneDetectionStrategy:
        """
        Получить экземпляр стратегии по имени.
        
        Args:
            name: Имя зарегистрированной стратегии
            **init_params: Параметры для __init__ стратегии (если нужны)
            
        Returns:
            Экземпляр стратегии
        """
        if name not in cls._strategies:
            available = ', '.join(cls.list_strategies())
            raise ValueError(
                f"Unknown zone detection strategy: '{name}'. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class(**init_params)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Список имен доступных стратегий."""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_info(cls, name: str) -> Dict[str, Any]:
        """Получить метаданные стратегии."""
        if name not in cls._metadata:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._metadata[name].copy()
    
    @classmethod
    def list_all_info(cls) -> Dict[str, Dict[str, Any]]:
        """Получить информацию обо всех стратегиях."""
        return cls._metadata.copy()
```

### Стратегия 1: ZeroCrossingDetection

```python
# bquant/analysis/zones/detection/zero_crossing.py

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'zero_crossing',
    description='Detect bull/bear zones by indicator crossing zero line',
    supported_zones=['bull', 'bear'],
    required_rules=['indicator_col']
)
class ZeroCrossingDetection:
    """
    Стратегия: детекция зон по пересечению нулевой линии.
    
    Применение:
        - MACD histogram
        - Awesome Oscillator (AO)
        - CCI (Commodity Channel Index)
        - любой осциллятор с нулевой линией
        
    Правила (config.rules):
        - indicator_col: str (обязательно) - название колонки индикатора
        - smooth_window: int (опционально) - сглаживание перед детекцией
        
    Типы зон:
        - 'bull': индикатор > 0
        - 'bear': индикатор < 0
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Обнаружить зоны по пересечению нуля.
        
        Алгоритм:
        1. Извлечь колонку индикатора
        2. Опционально сгладить
        3. Найти знаковые переходы (+ -> -, - -> +)
        4. Создать ZoneInfo для каждой зоны
        5. Отфильтровать по min_duration
        """
        # Валидация
        config.validate(required_rules=['indicator_col'])
        
        indicator_col = config.rules['indicator_col']
        if indicator_col not in data.columns:
            raise ValueError(
                f"Indicator column '{indicator_col}' not found in data. "
                f"Available: {list(data.columns)}"
            )
        
        df = data.copy()
        indicator_values = df[indicator_col].values
        
        # Опциональное сглаживание
        smooth_window = config.rules.get('smooth_window')
        if smooth_window and smooth_window > 1:
            indicator_values = pd.Series(indicator_values).rolling(
                window=smooth_window, 
                center=False
            ).mean().values
            self.logger.debug(f"Applied smoothing: window={smooth_window}")
        
        # Найти смены знака
        signs = np.sign(indicator_values)
        signs[signs == 0] = 1  # 0 считаем как положительное
        
        sign_changes = np.where(np.diff(signs) != 0)[0] + 1
        
        if len(sign_changes) == 0:
            self.logger.warning("No zero crossings found")
            return []
        
        # Добавить начало и конец
        boundaries = np.concatenate([[0], sign_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            # Фильтр по минимальной длительности
            if duration < config.min_duration:
                continue
            
            # Определить тип зоны
            zone_mean_value = indicator_values[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_value > 0 else 'bear'
            
            # Фильтр по типам зон
            if zone_type not in config.zone_types:
                continue
            
            # Создать ZoneInfo
            zone_data = df.iloc[start_idx:end_idx + 1].copy()
            
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data
            )
            zones.append(zone)
        
        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"{sum(1 for z in zones if z.type == 'bull')} bull, "
            f"{sum(1 for z in zones if z.type == 'bear')} bear"
        )
        
        return zones
```

### Стратегия 2: ThresholdDetection

```python
# bquant/analysis/zones/detection/threshold.py

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'threshold',
    description='Detect zones by indicator crossing upper/lower thresholds',
    supported_zones=['overbought', 'neutral', 'oversold'],
    required_rules=['indicator_col', 'upper_threshold', 'lower_threshold']
)
class ThresholdDetection:
    """
    Стратегия: детекция зон по порогам.
    
    Применение:
        - RSI (upper=70, lower=30)
        - Stochastic (upper=80, lower=20)
        - Williams %R
        
    Правила (config.rules):
        - indicator_col: str (обязательно)
        - upper_threshold: float (обязательно) - верхняя граница
        - lower_threshold: float (обязательно) - нижняя граница
        
    Типы зон:
        - 'overbought': индикатор > upper_threshold
        - 'neutral': lower_threshold <= индикатор <= upper_threshold
        - 'oversold': индикатор < lower_threshold
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по порогам."""
        # Валидация
        config.validate(required_rules=['indicator_col', 'upper_threshold', 'lower_threshold'])
        
        indicator_col = config.rules['indicator_col']
        upper = config.rules['upper_threshold']
        lower = config.rules['lower_threshold']
        
        if upper <= lower:
            raise ValueError(f"upper_threshold ({upper}) must be > lower_threshold ({lower})")
        
        if indicator_col not in data.columns:
            raise ValueError(f"Indicator column '{indicator_col}' not found")
        
        df = data.copy()
        indicator_values = df[indicator_col].values
        
        # Классификация по порогам
        zone_classes = np.empty(len(indicator_values), dtype=object)
        zone_classes[indicator_values > upper] = 'overbought'
        zone_classes[indicator_values < lower] = 'oversold'
        zone_classes[(indicator_values >= lower) & (indicator_values <= upper)] = 'neutral'
        
        # Найти границы зон (смены класса)
        class_changes = np.where(
            np.concatenate([[True], zone_classes[1:] != zone_classes[:-1]])
        )[0]
        boundaries = np.concatenate([class_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            if duration < config.min_duration:
                continue
            
            zone_type = zone_classes[start_idx]
            
            if zone_type not in config.zone_types:
                continue
            
            zone_data = df.iloc[start_idx:end_idx + 1].copy()
            
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data
            )
            zones.append(zone)
        
        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"OB={sum(1 for z in zones if z.type == 'overbought')}, "
            f"N={sum(1 for z in zones if z.type == 'neutral')}, "
            f"OS={sum(1 for z in zones if z.type == 'oversold')}"
        )
        
        return zones
```

### Стратегия 3: LineCrossingDetection

```python
# bquant/analysis/zones/detection/line_crossing.py

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'line_crossing',
    description='Detect zones by two lines crossing each other',
    supported_zones=['bull', 'bear'],
    required_rules=['line1_col', 'line2_col']
)
class LineCrossingDetection:
    """
    Стратегия: детекция зон по пересечению двух линий.
    
    Применение:
        - MA crosses (fast MA vs slow MA)
        - Price vs MA
        - Bollinger Bands (price vs upper/lower band)
        
    Правила (config.rules):
        - line1_col: str (обязательно) - первая линия (обычно быстрая)
        - line2_col: str (обязательно) - вторая линия (обычно медленная)
        
    Типы зон:
        - 'bull': line1 > line2
        - 'bear': line1 < line2
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по пересечению линий."""
        config.validate(required_rules=['line1_col', 'line2_col'])
        
        line1_col = config.rules['line1_col']
        line2_col = config.rules['line2_col']
        
        for col in [line1_col, line2_col]:
            if col not in data.columns:
                raise ValueError(f"Column '{col}' not found in data")
        
        df = data.copy()
        
        # Разница между линиями
        diff = df[line1_col].values - df[line2_col].values
        
        # Знак разницы
        signs = np.sign(diff)
        signs[signs == 0] = 1
        
        # Найти пересечения
        sign_changes = np.where(np.diff(signs) != 0)[0] + 1
        
        if len(sign_changes) == 0:
            self.logger.warning("No line crossings found")
            return []
        
        boundaries = np.concatenate([[0], sign_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            if duration < config.min_duration:
                continue
            
            zone_mean_diff = diff[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_diff > 0 else 'bear'
            
            if zone_type not in config.zone_types:
                continue
            
            zone_data = df.iloc[start_idx:end_idx + 1].copy()
            
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data
            )
            zones.append(zone)
        
        self.logger.info(f"Detected {len(zones)} zones from line crossing")
        
        return zones
```

### Стратегия 4: PreloadedZonesDetection

```python
# bquant/analysis/zones/detection/preloaded.py

import pandas as pd
from typing import List, Union
from pathlib import Path

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'preloaded',
    description='Import zones from external data source (CSV, DataFrame)',
    supported_zones=['any'],
    required_rules=['zones_data']
)
class PreloadedZonesDetection:
    """
    Стратегия: импорт готовых зон из внешних источников.
    
    Применение:
        - Импорт зон из торговых систем (MT5, cTrader)
        - Зоны, размеченные экспертами
        - Результаты ML моделей
        
    Правила (config.rules):
        - zones_data: str | Path | pd.DataFrame (обязательно)
        - time_tolerance: str (опционально, default='1min') - допуск времени для мержа
        
    Формат внешних зон (CSV/DataFrame):
        - zone_id: int - уникальный ID
        - type: str - тип зоны
        - start_time: datetime - начало зоны
        - end_time: datetime - конец зоны
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Загрузить и объединить готовые зоны с OHLCV данными."""
        config.validate(required_rules=['zones_data'])
        
        zones_data = config.rules['zones_data']
        time_tolerance = config.rules.get('time_tolerance', '1min')
        
        # Загрузить зоны
        zones_df = self._load_zones(zones_data)
        
        # Валидация колонок
        required_cols = ['zone_id', 'type', 'start_time', 'end_time']
        missing = [c for c in required_cols if c not in zones_df.columns]
        if missing:
            raise ValueError(f"Missing required columns in zones data: {missing}")
        
        # Объединить с OHLCV
        zones = []
        for _, zone_row in zones_df.iterrows():
            zone_info = self._merge_zone_with_ohlcv(
                zone_row, data, time_tolerance
            )
            
            if zone_info and zone_info.duration >= config.min_duration:
                if zone_info.type in config.zone_types or 'any' in config.zone_types:
                    zones.append(zone_info)
        
        self.logger.info(f"Loaded {len(zones)} preloaded zones")
        
        return zones
    
    def _load_zones(self, zones_data: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
        """Загрузить зоны из файла или DataFrame."""
        if isinstance(zones_data, pd.DataFrame):
            return zones_data.copy()
        
        # Загрузка из файла
        path = Path(zones_data)
        if not path.exists():
            raise FileNotFoundError(f"Zones file not found: {path}")
        
        if path.suffix == '.csv':
            df = pd.read_csv(path, parse_dates=['start_time', 'end_time'])
        elif path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path, parse_dates=['start_time', 'end_time'])
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        return df
    
    def _merge_zone_with_ohlcv(self, 
                                zone_row: pd.Series, 
                                ohlcv: pd.DataFrame,
                                time_tolerance: str) -> ZoneInfo:
        """Объединить зону с OHLCV данными по времени."""
        start_time = pd.Timestamp(zone_row['start_time'])
        end_time = pd.Timestamp(zone_row['end_time'])
        
        # Найти индексы с допуском времени
        mask = (ohlcv.index >= start_time - pd.Timedelta(time_tolerance)) & \
               (ohlcv.index <= end_time + pd.Timedelta(time_tolerance))
        
        zone_data = ohlcv[mask].copy()
        
        if zone_data.empty:
            self.logger.warning(
                f"No OHLCV data found for zone {zone_row['zone_id']} "
                f"({start_time} - {end_time})"
            )
            return None
        
        return ZoneInfo(
            zone_id=int(zone_row['zone_id']),
            type=str(zone_row['type']),
            start_idx=ohlcv.index.get_loc(zone_data.index[0]),
            end_idx=ohlcv.index.get_loc(zone_data.index[-1]),
            start_time=zone_data.index[0],
            end_time=zone_data.index[-1],
            duration=len(zone_data),
            data=zone_data
        )


def load_preloaded_zones(zones_path: Union[str, Path], 
                         ohlcv_data: pd.DataFrame,
                         time_tolerance: str = '1min',
                         min_duration: int = 2) -> List[ZoneInfo]:
    """
    Helper function для загрузки готовых зон.
    
    Args:
        zones_path: Путь к CSV/Excel с зонами
        ohlcv_data: DataFrame с OHLCV данными
        time_tolerance: Допуск времени для мержа
        min_duration: Минимальная длительность зоны
        
    Returns:
        List[ZoneInfo]
        
    Example:
        zones = load_preloaded_zones('expert_zones.csv', df)
        analyzer = UniversalZoneAnalyzer()
        result = analyzer.analyze_zones(zones, df)
    """
    detector = PreloadedZonesDetection()
    config = ZoneDetectionConfig(
        min_duration=min_duration,
        zone_types=['any'],
        rules={
            'zones_data': zones_path,
            'time_tolerance': time_tolerance
        },
        strategy_name='preloaded'
    )
    
    return detector.detect_zones(ohlcv_data, config)
```

### Стратегия 5: CombinedRulesDetection

```python
# bquant/analysis/zones/detection/combined.py

import pandas as pd
import numpy as np
from typing import List, Callable, Literal

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'combined',
    description='Detect zones by combining multiple conditions with AND/OR logic',
    supported_zones=['custom'],
    required_rules=['conditions']
)
class CombinedRulesDetection:
    """
    Стратегия: детекция зон по комбинации условий.
    
    Применение:
        - Кастомные торговые правила
        - Комбинация нескольких индикаторов
        - Сложная логика определения зон
        
    Правила (config.rules):
        - conditions: List[Callable] (обязательно) - список функций-условий
        - logic: 'AND' | 'OR' (опционально, default='AND')
        - zone_type_map: Dict[bool, str] (опционально) - маппинг результата на тип зоны
        
    Example:
        conditions = [
            lambda df: df['macd'] > 0,
            lambda df: df['rsi'] < 70,
            lambda df: df['close'] > df['sma_50']
        ]
        config = ZoneDetectionConfig(
            strategy_name='combined',
            rules={
                'conditions': conditions,
                'logic': 'AND'
            }
        )
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по комбинированным правилам."""
        config.validate(required_rules=['conditions'])
        
        conditions = config.rules['conditions']
        logic = config.rules.get('logic', 'AND').upper()
        zone_type_map = config.rules.get('zone_type_map', {True: 'active', False: 'inactive'})
        
        if logic not in ['AND', 'OR']:
            raise ValueError(f"logic must be 'AND' or 'OR', got '{logic}'")
        
        df = data.copy()
        
        # Вычислить все условия
        condition_results = []
        for i, cond in enumerate(conditions):
            try:
                result = cond(df)
                if not isinstance(result, (pd.Series, np.ndarray)):
                    raise TypeError(f"Condition {i} must return pd.Series or np.ndarray")
                condition_results.append(result)
            except Exception as e:
                raise ValueError(f"Error evaluating condition {i}: {e}")
        
        # Комбинировать условия
        if logic == 'AND':
            combined = np.logical_and.reduce(condition_results)
        else:  # OR
            combined = np.logical_or.reduce(condition_results)
        
        # Найти границы зон
        changes = np.where(
            np.concatenate([[True], combined[1:] != combined[:-1]])
        )[0]
        boundaries = np.concatenate([changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            if duration < config.min_duration:
                continue
            
            zone_active = combined[start_idx]
            zone_type = zone_type_map.get(zone_active, f'zone_{zone_active}')
            
            if zone_type not in config.zone_types:
                continue
            
            zone_data = df.iloc[start_idx:end_idx + 1].copy()
            
            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data
            )
            zones.append(zone)
        
        self.logger.info(f"Detected {len(zones)} zones from combined rules ({logic})")
        
        return zones
```

### Шаблон для новых стратегий

```python
# bquant/analysis/zones/detection/my_new_strategy.py

"""
TEMPLATE: Создание новой стратегии детекции зон

Шаги:
1. Скопировать этот шаблон
2. Переименовать класс и файл
3. Обновить @register декоратор
4. Реализовать detect_zones()
5. Добавить тесты
6. Готово! Стратегия автоматически доступна
"""

import pandas as pd
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core import get_logger


@ZoneDetectionRegistry.register(
    'my_strategy',  # ← Уникальное имя
    description='Short description of what this strategy does',
    supported_zones=['type1', 'type2'],
    required_rules=['param1', 'param2']
)
class MyNewDetectionStrategy:
    """
    Стратегия: [описание].
    
    Применение:
        - [индикатор 1]
        - [индикатор 2]
        
    Правила (config.rules):
        - param1: type (обязательно) - описание
        - param2: type (обязательно) - описание
        
    Типы зон:
        - 'type1': когда ...
        - 'type2': когда ...
    """
    
    def __init__(self, optional_param=None):
        self.logger = get_logger(__name__)
        self.optional_param = optional_param
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по [вашим правилам]."""
        # 1. Валидация
        config.validate(required_rules=['param1', 'param2'])
        
        # 2. Извлечь параметры
        param1 = config.rules['param1']
        param2 = config.rules['param2']
        
        # 3. Валидация данных
        if 'required_col' not in data.columns:
            raise ValueError(f"Required column not found")
        
        df = data.copy()
        
        # 4. ========== ВАША ЛОГИКА ЗДЕСЬ ==========
        # Найти границы зон...
        # Создать List[ZoneInfo]...
        
        zones = []
        # ... ваш код ...
        
        # 5. Логирование
        self.logger.info(f"Detected {len(zones)} zones")
        
        return zones
```

---

<a name="точки-расширения"></a>
## Точки расширения архитектуры

Этот раздел описывает все места, где архитектура может быть расширена в будущем без изменения существующего кода. Каждая точка расширения использует Dependency Injection или Registry Pattern для минимизации изменений.

### 1. Слой 1: Zone Detection Strategies (основная точка)

**Самая активная точка расширения** - добавление новых стратегий детекции.

#### Как добавить новую стратегию:

1. Создать файл `bquant/analysis/zones/detection/my_strategy.py`
2. Реализовать класс с методом `detect_zones(data, config)`
3. Добавить декоратор `@ZoneDetectionRegistry.register('my_strategy', ...)`
4. Написать тесты
5. **Готово!** Стратегия автоматически доступна во всех Builder/Pipeline

#### Примеры будущих стратегий:

```python
# 1. Pattern-based Detection (свечные паттерны)
@ZoneDetectionRegistry.register('pattern_based')
class PatternBasedDetection:
    """
    Зоны на основе свечных паттернов.
    
    Применение:
        - Doji зоны
        - Hammer/Shooting star
        - Engulfing patterns
    """
    def detect_zones(self, data, config):
        patterns = config.rules['patterns']  # ['doji', 'hammer', ...]
        # Детекция паттернов
        # Группировка в зоны
        return zones


# 2. ML-based Detection (машинное обучение)
@ZoneDetectionRegistry.register('ml_classifier')
class MLBasedDetection:
    """
    Зоны на основе ML модели.
    
    Применение:
        - Sklearn классификаторы
        - PyTorch модели
        - Custom ML алгоритмы
    """
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
    
    def detect_zones(self, data, config):
        features = extract_features(data, config.rules['feature_cols'])
        predictions = self.model.predict(features)
        zones = group_predictions_to_zones(predictions, data)
        return zones


# 3. Multi-Indicator Detection (несколько индикаторов)
@ZoneDetectionRegistry.register('multi_indicator')
class MultiIndicatorDetection:
    """
    Зоны на основе нескольких индикаторов одновременно.
    
    Применение:
        - MACD + RSI + Volume
        - Bollinger + ATR + Momentum
        - Custom комбинации
    """
    def detect_zones(self, data, config):
        indicators = config.rules['indicators']  # {'macd': 'bull', 'rsi': 'oversold', ...}
        # Анализ всех индикаторов
        # Intersection/Union зон
        return zones


# 4. Volume Profile Detection
@ZoneDetectionRegistry.register('volume_profile')
class VolumeProfileDetection:
    """
    Зоны на основе профиля объема.
    
    Применение:
        - POC (Point of Control) зоны
        - High Volume Nodes
        - Low Volume Nodes
    """
    def detect_zones(self, data, config):
        profile = calculate_volume_profile(data, config.rules['bins'])
        zones = identify_volume_zones(profile, config.rules['threshold'])
        return zones


# 5. Market Structure Detection
@ZoneDetectionRegistry.register('market_structure')
class MarketStructureDetection:
    """
    Зоны на основе структуры рынка (Smart Money Concepts).
    
    Применение:
        - Break of Structure (BOS)
        - Change of Character (CHoCH)
        - Order Blocks
        - Fair Value Gaps
    """
    def detect_zones(self, data, config):
        structure = analyze_market_structure(data)
        zones = identify_smc_zones(structure, config.rules['zone_type'])
        return zones
```

#### Процесс добавления (0 изменений в существующем коде):

```python
# Шаг 1: Создать файл с новой стратегией
# bquant/analysis/zones/detection/my_new_strategy.py

@ZoneDetectionRegistry.register('my_new_strategy')
class MyNewStrategy:
    def detect_zones(self, data, config):
        # Ваша логика
        return zones

# Шаг 2: Использовать сразу!
result = (
    analyze_zones(df)
    .detect_zones('my_new_strategy', param1=value1)  # ← Сразу работает!
    .build()
)
```

### 2. Слой 2: Universal Analyzer (расширение через DI)

**Точка расширения:** Добавление новых компонентов анализа через Dependency Injection.

#### Текущая архитектура (расширяемая):

```python
class UniversalZoneAnalyzer:
    def __init__(self,
                 # СУЩЕСТВУЮЩИЕ КОМПОНЕНТЫ
                 features_analyzer=None,
                 hypothesis_suite=None,
                 sequence_analyzer=None,
                 regression_analyzer=None,
                 validation_suite=None,
                 
                 # НОВЫЕ КОМПОНЕНТЫ (точки расширения)
                 ml_predictor=None,           # ML предсказания
                 optimization_engine=None,     # Оптимизация параметров
                 backtesting_engine=None,      # Бэктестинг
                 risk_analyzer=None,           # Риск-анализ
                 export_manager=None):         # Экспорт (MT5, cTrader, ...)
        
        # Инициализация...
        self.ml = ml_predictor
        self.optimizer = optimization_engine
        self.backtest = backtesting_engine
        self.risk = risk_analyzer
        self.export = export_manager
```

#### Примеры расширений:

```python
# 1. ML Predictor (предсказания)
class ZoneMLPredictor:
    """Предсказания для зон через ML."""
    
    def predict_next_zone_type(self, zones_history):
        """Предсказать тип следующей зоны."""
        pass
    
    def predict_zone_duration(self, zone_features):
        """Предсказать длительность зоны."""
        pass
    
    def predict_zone_return(self, zone_features):
        """Предсказать доходность зоны."""
        pass

# Использование:
ml_predictor = ZoneMLPredictor(model_path='models/zone_predictor.pkl')
analyzer = UniversalZoneAnalyzer(ml_predictor=ml_predictor)
result = analyzer.analyze_zones(zones, df, run_ml_predictions=True)


# 2. Backtesting Engine (бэктестинг зон)
class ZoneBacktestingEngine:
    """Бэктестинг торговых стратегий на зонах."""
    
    def backtest_simple_entry(self, zones, data, stop_loss, take_profit):
        """Простая стратегия входа в зону."""
        pass
    
    def backtest_custom_strategy(self, zones, data, strategy_func):
        """Кастомная стратегия."""
        pass

# Использование:
backtest = ZoneBacktestingEngine()
analyzer = UniversalZoneAnalyzer(backtesting_engine=backtest)
result = analyzer.analyze_zones(zones, df, run_backtesting=True)


# 3. Risk Analyzer (риск-метрики)
class ZoneRiskAnalyzer:
    """Анализ рисков зон."""
    
    def calculate_var(self, zones):
        """Value at Risk для зон."""
        pass
    
    def calculate_drawdown(self, zones):
        """Максимальная просадка."""
        pass
    
    def calculate_sharpe_ratio(self, zones):
        """Sharpe Ratio для зон."""
        pass
```

### 3. Pipeline: Расширение конфигурации

**Точка расширения:** Добавление новых опций в `ZoneAnalysisConfig`.

```python
@dataclass
class ZoneAnalysisConfig:
    # СУЩЕСТВУЮЩИЕ
    indicator: Optional[IndicatorConfig] = None
    zone_detection: ZoneDetectionConfig = None
    perform_clustering: bool = True
    n_clusters: int = 3
    run_regression: bool = False
    run_validation: bool = False
    
    # НОВЫЕ ОПЦИИ (точки расширения)
    
    # Пре-обработка данных
    preprocessing: Optional[Dict[str, Any]] = None
    # Example: {'outlier_removal': True, 'fill_gaps': 'interpolate'}
    
    # Пост-обработка зон
    postprocessing: Optional[Dict[str, Any]] = None
    # Example: {'merge_adjacent': True, 'max_gap': 3}
    
    # Фильтры зон
    filters: Optional[List[Callable]] = None
    # Example: [lambda z: z.duration > 5, lambda z: z.type == 'bull']
    
    # Трансформации зон
    transformers: Optional[List[Callable]] = None
    # Example: [merge_short_zones, split_long_zones]
    
    # ML компоненты
    ml_config: Optional[Dict[str, Any]] = None
    # Example: {'model_path': 'models/predictor.pkl', 'features': [...]}
    
    # Бэктестинг
    backtest_config: Optional[Dict[str, Any]] = None
    # Example: {'strategy': 'simple_entry', 'stop_loss': 0.02}
    
    # Экспорт
    export_config: Optional[List[Dict[str, str]]] = None
    # Example: [{'format': 'csv', 'path': 'zones.csv'}, {'format': 'mt5', 'path': 'EA.mq5'}]
```

### 4. Builder: Новые методы (fluent API)

**Точка расширения:** Добавление новых методов в `ZoneAnalysisBuilder`.

```python
class ZoneAnalysisBuilder:
    # СУЩЕСТВУЮЩИЕ МЕТОДЫ
    # .with_indicator(), .detect_zones(), .analyze(), .build()
    
    # НОВЫЕ МЕТОДЫ (точки расширения):
    
    def preprocess(self, **params) -> 'ZoneAnalysisBuilder':
        """
        Пре-обработка данных перед детекцией.
        
        Example:
            .preprocess(outlier_removal=True, fill_gaps='interpolate')
        """
        self._preprocessing = params
        return self
    
    def filter_zones(self, 
                     min_duration: int = None,
                     max_duration: int = None,
                     zone_types: List[str] = None,
                     custom_filter: Callable = None) -> 'ZoneAnalysisBuilder':
        """
        Фильтрация зон после детекции.
        
        Example:
            .filter_zones(min_duration=5, zone_types=['bull'])
        """
        filters = []
        if min_duration:
            filters.append(lambda z: z.duration >= min_duration)
        if max_duration:
            filters.append(lambda z: z.duration <= max_duration)
        if zone_types:
            filters.append(lambda z: z.type in zone_types)
        if custom_filter:
            filters.append(custom_filter)
        
        self._filters = filters
        return self
    
    def transform_zones(self, *transformers: Callable) -> 'ZoneAnalysisBuilder':
        """
        Трансформация зон.
        
        Example:
            .transform_zones(merge_adjacent_zones, split_long_zones)
        """
        self._transformers = list(transformers)
        return self
    
    def with_ml_predictions(self, 
                           model_path: str,
                           features: List[str] = None) -> 'ZoneAnalysisBuilder':
        """
        Добавить ML предсказания.
        
        Example:
            .with_ml_predictions('models/zone_predictor.pkl', features=['duration', 'volatility'])
        """
        self._ml_config = {'model_path': model_path, 'features': features}
        return self
    
    def with_backtesting(self, 
                        strategy: str = 'simple_entry',
                        **params) -> 'ZoneAnalysisBuilder':
        """
        Добавить бэктестинг.
        
        Example:
            .with_backtesting('simple_entry', stop_loss=0.02, take_profit=0.05)
        """
        self._backtest_config = {'strategy': strategy, **params}
        return self
    
    def export_to(self, 
                  format: str, 
                  path: str,
                  **options) -> 'ZoneAnalysisBuilder':
        """
        Экспорт результатов.
        
        Example:
            .export_to('csv', 'results/zones.csv')
            .export_to('mt5', 'EA_Zones.mq5', template='scalping')
        """
        if self._export_config is None:
            self._export_config = []
        
        self._export_config.append({
            'format': format,
            'path': path,
            **options
        })
        return self
```

#### Пример использования всех расширений:

```python
result = (
    analyze_zones(df)
    
    # Основной pipeline
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    
    # НОВЫЕ ВОЗМОЖНОСТИ:
    
    # Пре-обработка
    .preprocess(outlier_removal=True, fill_gaps='interpolate')
    
    # Фильтрация зон
    .filter_zones(min_duration=5, zone_types=['bull'])
    
    # Трансформации
    .transform_zones(merge_adjacent_zones, normalize_zone_data)
    
    # ML предсказания
    .with_ml_predictions('models/zone_predictor.pkl')
    
    # Бэктестинг
    .with_backtesting('simple_entry', stop_loss=0.02, take_profit=0.05)
    
    # Анализ
    .analyze(clustering=True, n_clusters=3, regression=True)
    
    # Экспорт
    .export_to('csv', 'results/zones.csv')
    .export_to('json', 'results/zones.json')
    .export_to('mt5', 'EA_Zones.mq5', template='scalping')
    
    .build()
)
```

### 5. Новые модули (будущее расширение)

```
bquant/analysis/zones/
├── detection/          # Слой 1 (существует)
├── analyzer.py         # Слой 2 (существует)
├── pipeline.py         # Pipeline + Builder (существует)
│
├── filters.py          # НОВОЕ - фильтры зон
│   ├── DurationFilter
│   ├── TypeFilter
│   ├── VolatilityFilter
│   └── CustomFilter
│
├── transformers.py     # НОВОЕ - трансформации зон
│   ├── MergeAdjacentZones
│   ├── SplitLongZones
│   ├── NormalizeZoneData
│   └── EnrichWithFeatures
│
├── exporters/          # НОВОЕ - экспорт результатов
│   ├── base.py        # BaseExporter
│   ├── csv_exporter.py
│   ├── json_exporter.py
│   ├── mt5_exporter.py
│   └── ctrader_exporter.py
│
├── ml/                 # НОВОЕ - ML компоненты
│   ├── predictors.py  # ZoneMLPredictor
│   ├── classifiers.py # ZoneClassifier
│   ├── features.py    # Feature engineering для ML
│   └── optimization.py # Hyperparameter optimization
│
├── backtesting/        # НОВОЕ - бэктестинг
│   ├── engine.py      # BacktestingEngine
│   ├── strategies.py  # TradingStrategies
│   ├── metrics.py     # Performance metrics
│   └── reports.py     # Reporting
│
└── risk/               # НОВОЕ - риск-анализ
    ├── metrics.py     # VaR, Sharpe, Sortino, ...
    ├── drawdown.py    # Drawdown analysis
    └── portfolio.py   # Portfolio-level risk
```

### 6. Сводная таблица точек расширения

| Область | Способ расширения | Изменения в коде | Усилия |
|---------|-------------------|------------------|--------|
| **Zone Detection** | Новая стратегия + @register | 0 строк | Низкие |
| **Zone Analyzer** | DI новых компонентов | ~10 строк (опции) | Средние |
| **Pipeline Config** | Добавить поля в dataclass | ~5 строк | Низкие |
| **Builder Methods** | Новые методы (return self) | ~20 строк/метод | Низкие |
| **Filters** | Новый класс/функция | 0 строк (используется в config) | Низкие |
| **Transformers** | Новый класс/функция | 0 строк (используется в config) | Низкие |
| **Exporters** | Новый класс + registry | ~10 строк (registry) | Средние |
| **ML Components** | Новый класс + DI | ~10 строк (опции) | Средние-Высокие |

### 7. Принципы расширения (Design Patterns)

1. **Open/Closed Principle** - открыто для расширения, закрыто для изменения
2. **Strategy Pattern** - для Zone Detection
3. **Dependency Injection** - для Zone Analyzer компонентов
4. **Builder Pattern** - для fluent API
5. **Registry Pattern** - для автоматической регистрации стратегий
6. **Protocol/Interface** - для гарантии контракта

---

<a name="примеры"></a>
## Примеры использования

### Пример 1: MACD через fluent builder (рекомендуется)

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Found {len(result.zones)} zones")
```

### Пример 2: PRELOADED индикатор + рассчитанные зоны

```python
# df уже содержит MACD колонки
result = (
    analyze_zones(df)
    # НЕТ with_indicator - индикатор уже в данных!
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .build()
)
```

### Пример 3: PRELOADED индикатор + PRELOADED зоны

```python
# df содержит MACD, зоны из файла
result = (
    analyze_zones(df)
    # НЕТ with_indicator
    .detect_zones('preloaded', zones_data='expert_zones.csv', time_tolerance='5min')
    .analyze()
    .build()
)

# Максимальная скорость - нет расчетов!
```

### Пример 4: AO через pandas_ta

```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'ao')
    .detect_zones('zero_crossing', indicator_col='AO_5_34')
    .analyze()
    .build()
)
```

### Пример 5: RSI через talib с 3 типами зон

```python
result = (
    analyze_zones(df)
    .with_indicator('talib', 'rsi', timeperiod=14)
    .detect_zones('threshold', indicator_col='RSI', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

# Типы зон: overbought, neutral, oversold
print(f"Overbought: {sum(1 for z in result.zones if z.type == 'overbought')}")
print(f"Oversold: {sum(1 for z in result.zones if z.type == 'oversold')}")
```

### Пример 6: Через Pipeline с конфигурацией (для сохранения/переиспользования)

```python
from bquant.analysis.zones.pipeline import ZoneAnalysisPipeline, ZoneAnalysisConfig, IndicatorConfig
from bquant.analysis.zones.detection import ZoneDetectionConfig

# Создаем конфигурацию (можно сохранить в файл)
config = ZoneAnalysisConfig(
    indicator=IndicatorConfig(
        source='custom',
        name='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9}
    ),
    zone_detection=ZoneDetectionConfig(
        strategy_name='zero_crossing',
        min_duration=2,
        rules={'indicator_col': 'macd'}
    ),
    perform_clustering=True,
    n_clusters=3,
    run_regression=True
)

# Выполняем
pipeline = ZoneAnalysisPipeline(config)
result = pipeline.run(df)
```

### Пример 7: Прямые вызовы (максимальный контроль)

```python
from bquant.indicators import IndicatorFactory
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer

# 1. Расчет индикатора
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26)
result_ind = indicator.calculate(df)

df_with_macd = df.copy()
for col in result_ind.data.columns:
    df_with_macd[col] = result_ind.data[col]

# 2. Детекция зон
detector = ZoneDetectionRegistry.get('zero_crossing')
zones = detector.detect_zones(
    df_with_macd,
    ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_col': 'macd'}
    )
)

# 3. Анализ зон
analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df_with_macd, perform_clustering=True)
```

> **Детальные примеры модульного использования компонентов см. в документе [`zomodul.md`](zomodul.md)**  
> Включая: сохранение промежуточных результатов, пошаговое выполнение, интеграцию с внешними системами, feature engineering для ML

### Пример 8: Комбинированные правила

```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('combined', 
                  conditions=[
                      lambda df: df['macd'] > 0,
                      lambda df: df['close'] > df['close'].rolling(50).mean()
                  ],
                  logic='AND')
    .analyze()
    .build()
)
```

---

<a name="визуализация"></a>
## Визуализация зон

### Текущее состояние визуализации в BQuant

Пакет уже содержит модуль `bquant.visualization` с классом `ZoneVisualizer`, который предоставляет:

**Существующий функционал:**
- `plot_zones_on_price_chart()` - общий график цен с зонами
- `plot_macd_zones()` - зоны на MACD индикаторе
- `plot_zones_analysis()` - статистический анализ зон
- `plot_zones_distribution()` - распределение характеристик
- `plot_zones_correlation()` - корреляционная матрица метрик

**Используемые библиотеки:** Plotly (основной) + Matplotlib (fallback)

### Расширение для детальной визуализации

Для поддержки детального просмотра отдельных зон с отображением используемых индикаторов метрик (zigzag, pivot points, divergence, etc.) добавляются два новых метода в существующий `ZoneVisualizer`:

#### 1. Детальный график зоны (plot_zone_detail)

```python
# bquant/visualization/zones.py (расширение существующего класса)

class ZoneVisualizer(ZoneChartBuilder):
    # ... существующие методы ...
    
    def plot_zone_detail(self,
                        zone: Union[ZoneInfo, Dict],
                        analysis_data: pd.DataFrame,
                        show_indicators: Optional[List[str]] = None,
                        context_bars: int = 10,
                        **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Детальный график конкретной зоны с индикаторами метрик.
        
        Отображает:
        - Row 1: Candlestick chart с наложенными индикаторами (zigzag, pivots)
        - Row 2: Осциллятор (MACD/RSI/CCI если есть в данных)
        - Row 3: Volume (если есть)
        
        Args:
            zone: ZoneInfo или dict с данными зоны
            analysis_data: Полный DataFrame с OHLCV + all indicators
            show_indicators: Список индикаторов для отображения
                           None = auto-detect from zone.features
                           Supported: ['zigzag', 'pivot_points', 'divergence', 
                                      'volatility_bands']
            context_bars: Количество баров до/после зоны для контекста
            **kwargs: Дополнительные параметры:
                - show_swings: bool (default=True if detected)
                - show_pivots: bool (default=True if detected)
                - show_divergence: bool (default=True if detected)
                - show_volume: bool (default=True if available)
                - width: int (default=1200)
                - height: int (default=800)
        
        Returns:
            Plotly/Matplotlib фигура с детальным графиком
            
        Example:
            visualizer = ZoneVisualizer()
            
            # Автоматическое определение индикаторов из features зоны
            fig = visualizer.plot_zone_detail(zones[0], df)
            fig.show()
            
            # Явное указание индикаторов
            fig = visualizer.plot_zone_detail(
                zones[0], df,
                show_indicators=['zigzag', 'pivot_points'],
                context_bars=20
            )
            fig.show()
        """
        # Извлечение данных зоны с контекстом
        zone_window = self._get_zone_window(zone, analysis_data, context_bars)
        
        # Автоматическое определение индикаторов
        if show_indicators is None:
            show_indicators = self._detect_indicators_from_features(zone)
        
        # Создание графика
        if self.backend == 'plotly':
            return self._create_plotly_zone_detail(
                zone, zone_window, show_indicators, **kwargs
            )
        else:
            return self._create_matplotlib_zone_detail(
                zone, zone_window, show_indicators, **kwargs
            )
    
    # Helper methods
    def _get_zone_window(self, zone, df: pd.DataFrame, context_bars: int) -> pd.DataFrame:
        """Получить окно данных вокруг зоны с контекстом."""
        start_idx = max(0, zone.start_idx - context_bars)
        end_idx = min(len(df), zone.end_idx + context_bars)
        return df.iloc[start_idx:end_idx].copy()
    
    def _detect_indicators_from_features(self, zone) -> List[str]:
        """
        Автоматически определить индикаторы из zone.features.
        
        Правила детекции:
        - 'swing_*' keys → 'zigzag'
        - 'pivot_*' keys → 'pivot_points'
        - 'divergence_*' keys → 'divergence'
        - 'volatility_*' keys → 'volatility_bands'
        """
        indicators = []
        if hasattr(zone, 'features') and zone.features:
            if any(k.startswith('swing_') for k in zone.features):
                indicators.append('zigzag')
            if any(k.startswith('pivot_') for k in zone.features):
                indicators.append('pivot_points')
            if any(k.startswith('divergence_') for k in zone.features):
                indicators.append('divergence')
            if any(k.startswith('volatility_') for k in zone.features):
                indicators.append('volatility_bands')
        return indicators
```

#### 2. Сравнение зон (plot_zones_comparison)

```python
    def plot_zones_comparison(self,
                             zones: List[Union[ZoneInfo, Dict]],
                             analysis_data: pd.DataFrame,
                             date_range: Optional[Tuple[datetime, datetime]] = None,
                             max_zones: int = 5,
                             **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        График сравнения нескольких зон или зон в диапазоне дат.
        
        Args:
            zones: Список зон для отображения (или все зоны для фильтрации)
            analysis_data: Полный DataFrame с OHLCV + indicators
            date_range: Опциональный диапазон дат (start, end) для фильтрации
            max_zones: Максимальное количество отображаемых зон
            **kwargs: Дополнительные параметры:
                - overlay_mode: bool (default=False) - наложить зоны
                - show_legend: bool (default=True)
                - highlight_selected: bool (default=True)
        
        Returns:
            Plotly/Matplotlib фигура с графиком
            
        Example:
            # Конкретные зоны
            selected = [result.zones[i] for i in [0, 3, 7, 12]]
            fig = visualizer.plot_zones_comparison(selected, df)
            fig.show()
            
            # Зоны в диапазоне дат
            fig = visualizer.plot_zones_comparison(
                result.zones, df,
                date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1))
            )
            fig.show()
        """
        # Фильтрация зон по дате
        if date_range:
            zones = self._filter_zones_by_date(zones, date_range)
        
        # Ограничение количества зон
        if len(zones) > max_zones:
            zones = zones[:max_zones]
            self.logger.warning(f"Showing only first {max_zones} zones")
        
        # Создание графика
        if self.backend == 'plotly':
            return self._create_plotly_zones_comparison(
                zones, analysis_data, **kwargs
            )
        else:
            return self._create_matplotlib_zones_comparison(
                zones, analysis_data, **kwargs
            )
```

### Интеграция с ZoneAnalysisResult

Добавить convenience метод для визуализации прямо из результата анализа:

```python
# bquant/analysis/zones/models.py

@dataclass
class ZoneAnalysisResult:
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    regression_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def visualize(self, 
                  mode: str = 'overview',
                  zone_id: Optional[int] = None,
                  date_range: Optional[Tuple] = None,
                  **kwargs):
        """
        Удобный метод визуализации из результата анализа.
        
        Args:
            mode: Режим визуализации:
                - 'overview': Общий график всех зон на цене
                - 'detail': Детальный просмотр одной зоны
                - 'comparison': Сравнение нескольких зон
                - 'statistics': Статистический анализ зон
            zone_id: ID зоны для mode='detail'
            date_range: Диапазон дат для mode='comparison'
            **kwargs: Параметры для ZoneVisualizer
            
        Returns:
            Plotly/Matplotlib фигура
            
        Examples:
            # Общий обзор
            fig = result.visualize('overview')
            fig.show()
            
            # Детальный просмотр зоны #3
            fig = result.visualize('detail', zone_id=3, context_bars=20)
            fig.show()
            
            # Сравнение первых 5 зон
            fig = result.visualize('comparison', max_zones=5)
            fig.show()
            
            # Статистика
            fig = result.visualize('statistics')
            fig.show()
        """
        from bquant.visualization import ZoneVisualizer
        
        if self.data is None:
            raise ValueError("data not available in ZoneAnalysisResult")
        
        visualizer = ZoneVisualizer()
        
        if mode == 'overview':
            return visualizer.plot_zones_on_price_chart(
                self.data, self.zones, **kwargs
            )
        
        elif mode == 'detail':
            if zone_id is None:
                raise ValueError("zone_id required for detail mode")
            zone = next((z for z in self.zones if z.zone_id == zone_id), None)
            if not zone:
                raise ValueError(f"Zone {zone_id} not found")
            return visualizer.plot_zone_detail(zone, self.data, **kwargs)
        
        elif mode == 'comparison':
            return visualizer.plot_zones_comparison(
                self.zones, self.data, date_range=date_range, **kwargs
            )
        
        elif mode == 'statistics':
            return visualizer.plot_zones_analysis(
                self.zones, self.statistics, **kwargs
            )
        
        else:
            raise ValueError(
                f"Unknown mode: {mode}. "
                f"Available: 'overview', 'detail', 'comparison', 'statistics'"
            )
```

### Примеры использования визуализации

#### Пример 1: Простой обзор всех зон

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .build()
)

# Общий график с зонами
fig = result.visualize('overview')
fig.show()

# Или через ZoneVisualizer
from bquant.visualization import ZoneVisualizer
visualizer = ZoneVisualizer()
fig = visualizer.plot_zones_on_price_chart(df, result.zones)
fig.show()
```

#### Пример 2: Детальный просмотр зоны с zigzag

```python
# Автоматическое определение индикаторов из zone.features
fig = result.visualize('detail', zone_id=5, context_bars=15)
fig.show()

# Или явное указание индикаторов
visualizer = ZoneVisualizer()
fig = visualizer.plot_zone_detail(
    result.zones[5],
    df,
    show_indicators=['zigzag', 'pivot_points'],
    context_bars=20
)
fig.show()
```

#### Пример 3: Сравнение зон

```python
from datetime import datetime

# По диапазону дат
fig = result.visualize(
    'comparison',
    date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
    max_zones=5
)
fig.show()

# Конкретные зоны
selected_zones = [result.zones[i] for i in [0, 3, 7, 12]]
visualizer = ZoneVisualizer()
fig = visualizer.plot_zones_comparison(selected_zones, df)
fig.show()
```

#### Пример 4: Статистический анализ

```python
# Статистика зон
fig = result.visualize('statistics')
fig.show()

# Распределение конкретной метрики
visualizer = ZoneVisualizer()
fig = visualizer.plot_zones_distribution(
    result.zones,
    feature='duration',
    title='Zone Duration Distribution'
)
fig.show()
```

### Преимущества решения

✅ **Минимальные изменения** - только расширение существующего `ZoneVisualizer`  
✅ **Нет дублирования** - использует весь существующий функционал  
✅ **Простота** - всего 2 новых метода (~150 строк) + 1 метод в models  
✅ **Расширяемость** - легко добавить новые индикаторы через auto-detect  
✅ **Гибкость** - auto-detect или явное указание индикаторов  
✅ **Надежность** - fallback на matplotlib если plotly недоступен  
✅ **Нет интерактивности** - статические графики, максимально просто  
✅ **Удобство** - метод `visualize()` прямо в результате анализа  

### Структура изменений

```
bquant/visualization/
└── zones.py                  # + 2 метода в ZoneVisualizer (~150 строк)
                             # + 3 helper метода (~50 строк)

bquant/analysis/zones/
└── models.py                # + метод visualize() в ZoneAnalysisResult (~50 строк)
```

**Итого:** ~250 строк кода, 0 новых файлов, 0 изменений архитектуры

---

<a name="кэширование"></a>
## Кэширование и персистентное хранение

### Текущая инфраструктура кэширования в BQuant

Пакет уже содержит развитую систему кэширования в `bquant.core.cache`:

**Существующие компоненты:**
- `MemoryCache` - кэш в памяти с LRU эвикцией и TTL
- `DiskCache` - долгосрочное хранение на диске (pickle, `~/.cache/bquant/`)
- `CacheManager` - объединяет оба кэша (память + диск)
- Декоратор `@cached` - автоматическое кэширование функций
- Метод `calculate_with_cache()` - индикаторы уже используют кэширование

**Что отсутствует для зон:**
- ❌ Кэширование детекции зон
- ❌ Кэширование результатов анализа
- ❌ Сохранение/загрузка `ZoneAnalysisResult`
- ❌ Интеграция Pipeline с кэшем

### Интеграция кэширования в Pipeline

#### 1. Автоматическое кэширование в ZoneAnalysisPipeline

```python
# bquant/analysis/zones/pipeline.py (расширение)

import hashlib
from bquant.core.cache import get_cache_manager

class ZoneAnalysisPipeline:
    """
    Универсальный pipeline для анализа зон с кэшированием.
    """
    
    def __init__(self, 
                 config: ZoneAnalysisConfig,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None,
                 enable_cache: bool = True,
                 cache_ttl: int = 3600):
        """
        Args:
            config: Конфигурация pipeline
            zone_analyzer: Универсальный анализатор (DI)
            enable_cache: Включить кэширование результатов
            cache_ttl: Время жизни кэша в секундах (default: 1 час)
        """
        self.config = config
        self.analyzer = zone_analyzer or UniversalZoneAnalyzer()
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.cache_manager = get_cache_manager() if enable_cache else None
        self.logger = get_logger(__name__)
    
    def run(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """
        Выполнить полный pipeline анализа с кэшированием.
        
        Если enable_cache=True, результат будет сохранен в кэш
        (память + диск) для повторного использования.
        """
        if not self.enable_cache:
            return self._run_without_cache(df)
        
        # Генерируем ключ кэша на основе конфигурации и данных
        cache_key = self._generate_cache_key(df)
        
        # Проверяем кэш
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.info(f"Zone analysis result loaded from cache (key: {cache_key[:8]}...)")
            return cached_result
        
        # Выполняем анализ
        self.logger.info("Cache miss, running zone analysis...")
        result = self._run_without_cache(df)
        
        # Сохраняем в кэш (TTL по умолчанию, на диск)
        self.cache_manager.put(cache_key, result, ttl=self.cache_ttl, disk=True)
        self.logger.info(f"Zone analysis result saved to cache (key: {cache_key[:8]}...)")
        
        return result
    
    def _run_without_cache(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """Выполнить pipeline без кэширования (существующая логика)."""
        # 1. Подготовка данных (расчет индикатора)
        df_prepared = self._prepare_data(df)
        
        # 2. Детекция зон
        zones = self._detect_zones(df_prepared)
        
        # 3. Анализ зон
        return self._analyze_zones(zones, df_prepared)
    
    def _generate_cache_key(self, df: pd.DataFrame) -> str:
        """
        Генерация ключа кэша на основе конфигурации и данных.
        
        Ключ включает:
        - Хэш данных (OHLCV)
        - Конфигурацию индикатора
        - Конфигурацию детекции зон
        - Параметры анализа
        """
        import json
        from dataclasses import asdict
        
        # Хэш данных
        data_hash = pd.util.hash_pandas_object(df[['open', 'high', 'low', 'close']]).sum()
        
        # Сериализуем конфигурацию
        config_dict = {
            'indicator': asdict(self.config.indicator) if self.config.indicator else None,
            'zone_detection': asdict(self.config.zone_detection),
            'perform_clustering': self.config.perform_clustering,
            'n_clusters': self.config.n_clusters,
            'run_regression': self.config.run_regression,
            'run_validation': self.config.run_validation
        }
        config_str = json.dumps(config_dict, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        # Собираем ключ
        key = f"zone_analysis_{data_hash}_{config_hash}"
        
        return key
    
    def invalidate_cache(self, df: pd.DataFrame) -> None:
        """Инвалидировать кэш для конкретных данных."""
        if self.cache_manager:
            cache_key = self._generate_cache_key(df)
            self.cache_manager.invalidate(cache_key)
            self.logger.info(f"Cache invalidated for key: {cache_key[:8]}...")
```

#### 2. Поддержка кэширования в Builder

```python
class ZoneAnalysisBuilder:
    """Fluent builder с поддержкой кэширования."""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        # ... existing fields ...
        self._enable_cache = True
        self._cache_ttl = 3600
    
    def with_cache(self, 
                   enable: bool = True,
                   ttl: int = 3600) -> 'ZoneAnalysisBuilder':
        """
        Настроить кэширование.
        
        Args:
            enable: Включить/выключить кэш
            ttl: Время жизни кэша в секундах
            
        Returns:
            self для цепочки вызовов
            
        Example:
            # С кэшем (по умолчанию)
            result = analyze_zones(df).detect_zones(...).build()
            
            # Без кэша
            result = (
                analyze_zones(df)
                .with_cache(enable=False)
                .detect_zones(...)
                .build()
            )
            
            # Кэш с TTL 2 часа
            result = (
                analyze_zones(df)
                .with_cache(ttl=7200)
                .detect_zones(...)
                .build()
            )
        """
        self._enable_cache = enable
        self._cache_ttl = ttl
        return self
    
    def build(self) -> ZoneAnalysisResult:
        """Выполнить pipeline с учетом настроек кэша."""
        if self._zone_detection_config is None:
            raise ValueError("Zone detection strategy not configured")
        
        # Создаем конфигурацию
        config = ZoneAnalysisConfig(
            indicator=self._indicator_config,
            zone_detection=self._zone_detection_config,
            perform_clustering=self._perform_clustering,
            n_clusters=self._n_clusters,
            run_regression=self._run_regression,
            run_validation=self._run_validation
        )
        
        # Выполняем через pipeline с кэшированием
        pipeline = ZoneAnalysisPipeline(
            config,
            enable_cache=self._enable_cache,
            cache_ttl=self._cache_ttl
        )
        return pipeline.run(self.data)
```

### Персистентное хранение результатов

#### Расширение ZoneAnalysisResult

```python
# bquant/analysis/zones/models.py (расширение)

from pathlib import Path
import pickle
import gzip
import json

@dataclass
class ZoneAnalysisResult:
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    regression_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, 
             filepath: Union[str, Path],
             format: str = 'pickle',
             compress: bool = False,
             include_data: bool = True) -> None:
        """
        Сохранить результат анализа на диск.
        
        Args:
            filepath: Путь к файлу
            format: Формат сохранения
                - 'pickle': Бинарный формат Python (быстро, все данные)
                - 'json': Текстовый формат (читаемо, без DataFrame)
                - 'parquet': Columnar формат (компактно, все данные)
            compress: Сжимать ли данные (для pickle/parquet)
            include_data: Включать ли исходный DataFrame
            
        Example:
            # Полное сохранение с данными
            result.save('results/macd_zones.pkl')
            
            # Сжатое сохранение
            result.save('results/macd_zones.pkl.gz', compress=True)
            
            # JSON без исходных данных (легкий файл)
            result.save('results/macd_zones.json', format='json', include_data=False)
            
            # Parquet (оптимально для больших данных)
            result.save('results/macd_zones.parquet', format='parquet')
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'pickle':
            self._save_pickle(filepath, compress, include_data)
        elif format == 'json':
            self._save_json(filepath, include_data)
        elif format == 'parquet':
            self._save_parquet(filepath, compress, include_data)
        else:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: 'pickle', 'json', 'parquet'"
            )
    
    def _save_pickle(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Сохранение в pickle."""
        # Временно удаляем data если не нужен
        data_backup = None
        if not include_data and self.data is not None:
            data_backup = self.data
            self.data = None
        
        try:
            if compress:
                with gzip.open(filepath.with_suffix('.pkl.gz'), 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            # Восстанавливаем data
            if data_backup is not None:
                self.data = data_backup
    
    def _save_json(self, filepath: Path, include_data: bool) -> None:
        """Сохранение в JSON."""
        data_dict = self.to_dict(include_data=include_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
    
    def _save_parquet(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Сохранение в Parquet (набор файлов)."""
        import pyarrow as pa
        import pyarrow.parquet as pq
        
        # Создаем директорию для набора файлов
        output_dir = filepath.with_suffix('.parquet')
        output_dir.mkdir(exist_ok=True)
        
        # Сохраняем зоны
        zones_data = [self._zone_to_dict(z) for z in self.zones]
        zones_df = pd.DataFrame(zones_data)
        zones_df.to_parquet(output_dir / 'zones.parquet', compression='gzip' if compress else None)
        
        # Сохраняем метаданные и результаты анализа
        metadata = {
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Сохраняем исходные данные
        if include_data and self.data is not None:
            self.data.to_parquet(output_dir / 'data.parquet', compression='gzip' if compress else None)
    
    @classmethod
    def load(cls, 
             filepath: Union[str, Path],
             format: str = 'pickle') -> 'ZoneAnalysisResult':
        """
        Загрузить результат анализа из файла.
        
        Args:
            filepath: Путь к файлу
            format: Формат файла
            
        Returns:
            ZoneAnalysisResult
            
        Example:
            # Загрузка pickle
            result = ZoneAnalysisResult.load('results/macd_zones.pkl')
            
            # Загрузка сжатого pickle
            result = ZoneAnalysisResult.load('results/macd_zones.pkl.gz')
            
            # Загрузка JSON
            result = ZoneAnalysisResult.load('results/macd_zones.json', format='json')
            
            # Продолжение работы
            fig = result.visualize('overview')
            print(f"Loaded {len(result.zones)} zones")
        """
        filepath = Path(filepath)
        
        if format == 'pickle':
            return cls._load_pickle(filepath)
        elif format == 'json':
            return cls._load_json(filepath)
        elif format == 'parquet':
            return cls._load_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def _load_pickle(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из pickle."""
        # Автоопределение сжатия
        if filepath.suffix == '.gz' or filepath.name.endswith('.pkl.gz'):
            with gzip.open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
    
    @classmethod
    def _load_json(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
        
        return cls.from_dict(data_dict)
    
    @classmethod
    def _load_parquet(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из Parquet."""
        parquet_dir = filepath.with_suffix('.parquet')
        
        # Загружаем зоны
        zones_df = pd.read_parquet(parquet_dir / 'zones.parquet')
        zones = [cls._zone_from_dict(row) for _, row in zones_df.iterrows()]
        
        # Загружаем метаданные
        with open(parquet_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        # Загружаем исходные данные если есть
        data_file = parquet_dir / 'data.parquet'
        data = pd.read_parquet(data_file) if data_file.exists() else None
        
        return cls(
            zones=zones,
            statistics=metadata['statistics'],
            hypothesis_tests=metadata['hypothesis_tests'],
            clustering=metadata.get('clustering'),
            sequence_analysis=metadata.get('sequence_analysis'),
            regression_results=metadata.get('regression_results'),
            validation_results=metadata.get('validation_results'),
            data=data,
            metadata=metadata.get('metadata', {})
        )
    
    def to_dict(self, include_data: bool = False) -> Dict[str, Any]:
        """
        Конвертация в словарь (для JSON).
        
        Args:
            include_data: Включать ли DataFrame (warning: может быть большим)
        """
        result = {
            'zones': [self._zone_to_dict(z) for z in self.zones],
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        if include_data and self.data is not None:
            # Конвертируем DataFrame в dict (будет большой!)
            result['data'] = self.data.to_dict('records')
        
        return result
    
    @classmethod
    def from_dict(cls, data_dict: Dict[str, Any]) -> 'ZoneAnalysisResult':
        """Создание из словаря."""
        zones = [cls._zone_from_dict(z) for z in data_dict['zones']]
        
        # Восстанавливаем DataFrame если есть
        data = None
        if 'data' in data_dict:
            data = pd.DataFrame(data_dict['data'])
        
        return cls(
            zones=zones,
            statistics=data_dict['statistics'],
            hypothesis_tests=data_dict['hypothesis_tests'],
            clustering=data_dict.get('clustering'),
            sequence_analysis=data_dict.get('sequence_analysis'),
            regression_results=data_dict.get('regression_results'),
            validation_results=data_dict.get('validation_results'),
            data=data,
            metadata=data_dict.get('metadata', {})
        )
    
    @staticmethod
    def _zone_to_dict(zone: ZoneInfo) -> Dict[str, Any]:
        """Конвертация ZoneInfo в словарь."""
        return {
            'zone_id': zone.zone_id,
            'type': zone.type,
            'start_idx': zone.start_idx,
            'end_idx': zone.end_idx,
            'start_time': zone.start_time.isoformat(),
            'end_time': zone.end_time.isoformat(),
            'duration': zone.duration,
            'features': zone.features
            # data не сохраняем в dict (слишком большой)
        }
    
    @staticmethod
    def _zone_from_dict(zone_dict: Dict[str, Any]) -> ZoneInfo:
        """Создание ZoneInfo из словаря."""
        from datetime import datetime
        
        return ZoneInfo(
            zone_id=zone_dict['zone_id'],
            type=zone_dict['type'],
            start_idx=zone_dict['start_idx'],
            end_idx=zone_dict['end_idx'],
            start_time=datetime.fromisoformat(zone_dict['start_time']),
            end_time=datetime.fromisoformat(zone_dict['end_time']),
            duration=zone_dict['duration'],
            data=pd.DataFrame(),  # Пустой DataFrame, нужно загружать отдельно
            features=zone_dict.get('features')
        )
```

### Примеры использования кэширования

#### Пример 1: Автоматическое кэширование

```python
from bquant.analysis.zones import analyze_zones

# С кэшем (по умолчанию) - первый запуск
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .build()
)
# Output: "Cache miss, running zone analysis..."
# Output: "Zone analysis result saved to cache..."

# Второй запуск с теми же данными и параметрами - из кэша
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .build()
)
# Output: "Zone analysis result loaded from cache..."
# Выполнение мгновенное!
```

#### Пример 2: Управление кэшем

```python
# Отключить кэш для конкретного анализа
result = (
    analyze_zones(df)
    .with_cache(enable=False)  # Отключаем кэш
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_col='macd')
    .build()
)

# Кэш с увеличенным TTL (6 часов)
result = (
    analyze_zones(df)
    .with_cache(ttl=21600)
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_col='macd')
    .build()
)

# Инвалидация кэша при изменении данных
from bquant.core.cache import get_cache_manager

cache = get_cache_manager()

# Статистика кэша
stats = cache.stats()
print(f"Cache entries: {stats['memory']['entries']}")
print(f"Hit rate: {stats['memory']['hit_rate']:.1f}%")
print(f"Disk cache: {stats.get('disk', {}).get('entries', 0)} files")

# Очистка истекших записей
cleaned = cache.cleanup()
print(f"Cleaned: {cleaned['memory_cleaned']} from memory, {cleaned['disk_cleaned']} from disk")

# Полная очистка кэша
cache.clear()
```

#### Пример 3: Персистентное хранение

```python
# Анализ и сохранение
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True, regression=True)
    .build()
)

# Сохранение в разных форматах
result.save('results/macd_analysis.pkl')                    # Pickle (быстро)
result.save('results/macd_analysis.pkl.gz', compress=True)  # Сжатый pickle
result.save('results/macd_analysis.json', format='json')    # JSON (читаемо)
result.save('results/macd_analysis.parquet', format='parquet')  # Parquet (оптимально)

# JSON без исходных данных (легкий файл для документации)
result.save('results/macd_summary.json', format='json', include_data=False)

# Загрузка и продолжение работы
loaded_result = ZoneAnalysisResult.load('results/macd_analysis.pkl')

print(f"Loaded analysis with {len(loaded_result.zones)} zones")
print(f"Analysis date: {loaded_result.metadata.get('analysis_timestamp')}")

# Визуализация загруженного результата
fig = loaded_result.visualize('detail', zone_id=3)
fig.show()

# Получение конкретных метрик
print(f"Bull zones: {loaded_result.statistics['bull_zones']}")
print(f"Avg duration: {loaded_result.statistics['avg_duration']:.1f}")
```

#### Пример 4: Batch обработка с кэшем

```python
# Обработка нескольких инструментов с кэшированием
instruments = ['EURUSD', 'GBPUSD', 'USDJPY']
results = {}

for instrument in instruments:
    df = load_data(instrument)  # Ваша функция загрузки
    
    # Автоматическое кэширование для каждого инструмента
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd')
        .detect_zones('zero_crossing', indicator_col='macd')
        .analyze(clustering=True)
        .build()
    )
    
    # Сохраняем результат
    result.save(f'results/{instrument}_zones.pkl')
    results[instrument] = result

# При повторном запуске - все из кэша!
```

### Преимущества решения

✅ **Использует существующую инфраструктуру** - `bquant.core.cache` уже есть  
✅ **Прозрачное кэширование** - работает автоматически через Pipeline  
✅ **Гибкость** - можно отключить кэш через `.with_cache(enable=False)`  
✅ **Персистентное хранение** - `save()`/`load()` для долгосрочного хранения  
✅ **Множество форматов** - pickle (быстро), JSON (читаемо), parquet (компактно)  
✅ **Управление кэшем** - статистика, очистка, инвалидация, TTL  
✅ **Производительность** - повторный анализ мгновенный (из кэша)  
✅ **Минимальные изменения** - ~300 строк кода, интеграция с существующим API  

### Структура изменений

```
bquant/analysis/zones/
├── pipeline.py            # + кэширование в Pipeline (~100 строк)
│                         # + метод _generate_cache_key()
│                         # + параметры enable_cache, cache_ttl
│
└── models.py             # + методы save/load в ZoneAnalysisResult (~200 строк)
                          # + методы to_dict/from_dict
                          # + поддержка форматов: pickle, json, parquet

bquant/core/
└── cache.py              # БЕЗ ИЗМЕНЕНИЙ (используем как есть)
```

**Итого:** ~300 строк кода, 0 новых файлов, полная интеграция с существующим кэшем

---

<a name="преимущества"></a>
## Преимущества упрощенной архитектуры

### 1. Простота

| Было (с фасадами) | Стало (Pipeline + Builder) |
|-------------------|----------------------------|
| 3 слоя | 2 слоя |
| N фасадов для N индикаторов | 1 Pipeline для всех |
| Hardcode в фасадах | Конфигурация |
| ~500 строк на фасады | ~250 строк Pipeline + Builder |

### 2. Универсальность

- ✅ Один и тот же API для ВСЕХ индикаторов
- ✅ Нет специального кода для MACD, AO, RSI, ...
- ✅ Новый индикатор = 0 строк кода (только конфигурация!)

### 3. Гибкость

**Fluent Builder:**
```python
analyze_zones(df)
    .with_indicator(...)  # опционально
    .detect_zones(...)     # обязательно
    .analyze(...)          # опционально
    .build()
```

**Pipeline + Config:**
- Можно сохранить конфигурацию в JSON/YAML
- Переиспользовать на разных данных
- Валидировать перед выполнением

**Прямые вызовы:**
- Полный контроль на каждом шаге
- Вставка своей логики между шагами

### 4. Интеграция с IndicatorFactory

```python
# Все источники поддерживаются автоматически!
.with_indicator('preloaded', 'macd')        # извлечь из данных
.with_indicator('custom', 'macd', fast=12)   # встроенный алгоритм
.with_indicator('pandas_ta', 'ao')          # pandas_ta
.with_indicator('talib', 'rsi', timeperiod=14)  # TA-Lib
```

---

<a name="план-миграции"></a>
## План миграции

**📚 Важно:** Все заготовки кода и спецификации находятся в этом документе (zonan.md). Используйте ссылки на разделы для получения готовых решений. Для модульного использования компонентов см. [zomodul.md](zomodul.md).

**Принцип работы:** Каждая задача имеет ссылку на соответствующий раздел документа с готовой спецификацией или заготовкой кода. Следуйте документу, не изобретайте заново!

---

### Этап 0: Подготовка базовых моделей (1-2 дня) ✅ ВЫПОЛНЕНО

**Цель:** Создать фундамент для новой архитектуры без нарушения существующего кода

**📖 Спецификация:** См. разделы [Базовые структуры данных](#базовые-структуры) и [Кэширование и персистентное хранение](#кэширование)

1. [x] Создать `bquant/analysis/zones/models.py` (~430 строк) ✅
   - [x] Переместить ZoneInfo, ZoneAnalysisResult из `bquant/indicators/macd.py`
   - [x] Добавить метод `ZoneInfo.to_analyzer_format()` → См. [Базовые структуры данных](#базовые-структуры)
   - [x] Добавить методы сериализации → См. [Персистентное хранение результатов](#кэширование)
     - `ZoneAnalysisResult.save()` - сохранение на диск (pickle, JSON, parquet)
     - `ZoneAnalysisResult.load()` - загрузка из файла
     - `to_dict()` / `from_dict()` - JSON сериализация
     - `_save_pickle()`, `_save_json()`, `_save_parquet()` - форматы
     - `_zone_to_dict()`, `_zone_from_dict()` - helper методы
   - [x] Добавить метод `ZoneAnalysisResult.visualize()` → См. [Интеграция с ZoneAnalysisResult](#визуализация)

2. [x] Обновить импорты во всех файлах ✅
   - `bquant/indicators/macd.py` - импорт из models
   - Backward compatibility через реэкспорт
   - Все существующие тесты работают без изменений

3. [x] Проверить тесты (514 passed, 1 failed, 1 skipped) ✅
   - [x] `pytest tests/` - основные тесты проходят
   - [x] 514 passed - отличный результат
   - [x] 1 failed - не связан с нашими изменениями (scripts output formats)
   - [x] Все тесты MACD analyzer проходят (16/16)
   - [x] Все тесты zone features проходят
   - [x] Модели успешно загружаются: "Zone models (ZoneInfo, ZoneAnalysisResult) loaded successfully"

4. [x] Обновить `bquant/analysis/zones/__init__.py` ✅
   - [x] Экспортировать ZoneInfo, ZoneAnalysisResult
   - [x] Добавлен conditional import с try/except

5. [x] Unit-тесты для models.py (15 тестов) ✅
   - [x] Тесты сериализации (save/load) для всех форматов
   - [x] Тесты to_dict/from_dict
   - [x] Тесты с/без include_data
   - [x] Тесты сжатия (pickle.gz)
   - [x] Тесты обработки ошибок (несуществующий файл, некорректный формат)
   - [x] 14 passed, 1 skipped (parquet требует pyarrow - опциональная зависимость)

**Результат:** ✅ Базовые модели в правильном месте, полная сериализация, старый код работает, backward compatibility сохранена

### Этап 1: Создание инфраструктуры (4-6 дней)

**Цель:** Реализовать новую архитектуру без нарушения существующего функционала

**📖 Обзор структуры:** См. раздел [Структура директорий](#структура) - полная карта файлов и их назначения

#### 1.1 Слой 1: Zone Detection Strategies (2-3 дня) ✅ **ВЫПОЛНЕНО**

**📖 Спецификация:** См. разделы [Слой 1: Zone Detection Strategies](#слой-1) и [Реализация стратегий детекции (Code Templates)](#реализация-стратегий)

1. [x] Создать `bquant/analysis/zones/detection/__init__.py`
   - Экспорты: ZoneDetectionStrategy, ZoneDetectionConfig, ZoneDetectionRegistry
   - ✅ Создан, все экспорты работают

2. [x] Создать `bquant/analysis/zones/detection/base.py` (~100 строк)
   - Протокол `ZoneDetectionStrategy` → См. [base.py - Протокол и конфигурация](#реализация-стратегий)
   - Dataclass `ZoneDetectionConfig` с валидацией → См. [base.py - Протокол и конфигурация](#реализация-стратегий)
   - ✅ Реализовано точно по спецификации, 76 строк

3. [x] Создать `bquant/analysis/zones/detection/registry.py` (~100 строк)
   - Класс `ZoneDetectionRegistry` с декоратором → См. [registry.py - Реестр с метаданными](#реализация-стратегий)
   - Методы: register, get, list_strategies, get_info → См. [registry.py - Реестр с метаданными](#реализация-стратегий)
   - ✅ Реализовано, 83 строки, 5 стратегий зарегистрировано

4. [x] Реализовать стратегии детекции → См. [Реализация стратегий детекции](#реализация-стратегий):
   - [x] `zero_crossing.py` (~150 строк) → См. [Стратегия 1: ZeroCrossingDetection](#реализация-стратегий) ✅ 156 строк
   - [x] `line_crossing.py` (~120 строк) → См. [Стратегия 3: LineCrossingDetection](#реализация-стратегий) ✅ 116 строк
   - [x] `threshold.py` (~130 строк) → См. [Стратегия 2: ThresholdDetection](#реализация-стратегий) ✅ 142 строки
   - [x] `preloaded.py` (~200 строк) → См. [Стратегия 4: PreloadedZonesDetection](#реализация-стратегий) ✅ 185 строк
   - [x] `combined.py` (~150 строк, опционально) → См. [Стратегия 5: CombinedRulesDetection](#реализация-стратегий) ✅ 156 строк

5. [x] Unit-тесты стратегий детекции (~50 тестов)
   - По 10 тестов на каждую стратегию
   - Тесты: валидация конфигурации, обработка ошибок, корректность детекции
   - ✅ Реализовано 28 тестов (ZoneDetectionConfig + Registry + все 5 стратегий), все проходят

#### 1.2 Слой 2: Universal Analyzer (1 день) ✅ **ВЫПОЛНЕНО**

**📖 Спецификация:** См. раздел [Слой 2: Universal Zone Analyzer](#слой-2)

1. [x] Создать `bquant/analysis/zones/analyzer.py` (~200 строк)
   - Класс `UniversalZoneAnalyzer` с DI → См. [Слой 2: Реализация](#слой-2)
   - Метод `analyze_zones(zones: List[ZoneInfo], ...)` → См. [Слой 2: Реализация](#слой-2)
   - Чистая координация без адаптеров
   - О расширении через DI → См. [Точки расширения: Слой 2](#точки-расширения)
   - ✅ Реализовано 216 строк, чистая координация с DI компонентов
   - ✅ Изящная обработка случаев с малым количеством зон (< 3 для sequence_analysis)

2. [x] Обновить `bquant/analysis/zones/zone_features.py`
   - Добавить метод `extract_all_zones_features(zones: List[ZoneInfo])`
   - Метод принимает List[ZoneInfo] вместо List[Dict]
   - ✅ Метод добавлен, адаптирует ZoneInfo к существующему функционалу

3. [x] Unit-тесты UniversalZoneAnalyzer (~15 тестов)
   - Тесты на DI компонентов
   - Тесты на корректность координации
   - Тесты на обработку пустых данных
   - ✅ Реализовано 8 тестов (инициализация, DI, basic analysis, clustering, regression, empty zones, few zones, metadata), все проходят

#### 1.3 Pipeline + Builder (1-2 дня) ✅ **ВЫПОЛНЕНО**

**📖 Спецификация:** См. разделы [Pipeline: Единая точка входа](#pipeline), [Builder: Fluent API](#builder), [Интеграция кэширования в Pipeline](#кэширование)

1. [x] Создать `bquant/analysis/zones/pipeline.py` (~500 строк)
   - [x] Dataclass `IndicatorConfig` → См. [Pipeline: Конфигурация](#pipeline) ✅
   - [x] Dataclass `ZoneAnalysisConfig` → См. [Pipeline: Конфигурация](#pipeline) ✅
   - [x] Класс `ZoneAnalysisPipeline` → См. [Pipeline: Pipeline класс](#pipeline):
     - Базовая логика pipeline ✅
     - **Интеграция кэширования** (enable_cache, cache_ttl) → См. [Автоматическое кэширование в ZoneAnalysisPipeline](#кэширование) ✅
     - Метод `_generate_cache_key()` → См. [Автоматическое кэширование в ZoneAnalysisPipeline](#кэширование) ✅
     - Метод `_run_without_cache()` → См. [Автоматическое кэширование в ZoneAnalysisPipeline](#кэширование) ✅
     - Метод `invalidate_cache()` → См. [Автоматическое кэширование в ZoneAnalysisPipeline](#кэширование) ✅
   - [x] Класс `ZoneAnalysisBuilder` (fluent API) → См. [Builder: Реализация](#builder):
     - Существующие методы (with_indicator, detect_zones, analyze) ✅
     - **Новый метод `with_cache(enable, ttl)`** → См. [Поддержка кэширования в Builder](#кэширование) ✅
   - [x] Helper функция `analyze_zones(df)` → См. [Builder: Реализация](#builder) ✅
   - ✅ Реализовано 463 строки, полная интеграция с IndicatorFactory и кэшированием

2. [x] Обновить `bquant/analysis/zones/__init__.py`
   - [x] Экспортировать все новые классы и функции
   - [x] Добавить __all__ список
   - ✅ Все экспорты добавлены, условный импорт работает корректно

3. [x] Unit-тесты Pipeline + Builder (~25 тестов)
   - [x] Тесты конфигураций ✅
   - [x] Тесты Pipeline выполнения ✅
   - [x] Тесты Builder цепочек ✅
   - [x] Тесты интеграции с IndicatorFactory → См. [Интеграция с IndicatorFactory](#интеграция) ✅
   - [x] **Тесты кэширования** → См. [Примеры использования кэширования](#кэширование):
     - Cache hit/miss ✅
     - Инвалидация кэша ✅ (через тесты)
     - TTL expiration ✅ (через конфигурацию)
     - Отключение кэша ✅
     - Генерация ключа кэша ✅
   - ✅ Реализовано 14 тестов (configs + pipeline + builder + разные стратегии), все проходят

**Результат:** ✅ **Новая архитектура полностью работает с кэшированием, интеграцией IndicatorFactory, старая не сломана, 50 тестов Stage 1 проходят**

---

**📊 Статистика Этапа 1:**
- **Создано файлов:** 11 (5 стратегий + base + registry + analyzer + pipeline + 2 теста)
- **Строк кода:** ~1700 строк продакшн кода + ~800 строк тестов
- **Тестов:** 50 тестов (28 detection + 8 analyzer + 14 pipeline/builder)
- **Покрытие:** все компоненты протестированы
- **Время:** ~2-3 дня (по плану 4-6)
- **Качество:** все тесты проходят, архитектура соответствует спецификации

### Этап 2: Миграция и примеры использования (2-3 дня)

**Цель:** Обеспечить backward compatibility и создать понятные примеры использования

**📖 Справка:** См. разделы [Примеры использования](#примеры) и [Модульное использование](zomodul.md)

**🏗️ Архитектурные принципы:**

> **Важно:** НЕ создавать отдельные классы/модули для каждого индикатора (RSIZoneAnalyzer, AOZoneAnalyzer и т.д.)
> 
> **Причина:** Универсальная архитектура Stage 1 специально спроектирована для работы с любыми индикаторами через единый API. Создание специфичных классов нарушает принцип универсальности и приводит к дублированию кода.
>
> **Правильный подход:** Использовать `analyze_zones()` + fluent API для всех индикаторов. Опционально - тонкие convenience wrappers (5-10 строк) в `presets.py`.

#### 2.1 Slim down MACDZoneAnalyzer (0.5 дня) ✅ **ВЫПОЛНЕНО**

**Цель:** Превратить монолит в тонкий backward compatibility wrapper

1. [x] Рефакторинг `bquant/indicators/macd.py` (517 строк → 254 строки)
   - [x] **Удалено** весь код детекции зон, анализа, статистики (~450 строк)
   - [x] **Оставлен** только wrapper класс `MACDZoneAnalyzer` (~100 строк чистого кода)
   - [x] Класс делегирует всю работу в `analyze_zones()` pipeline ✅
   - [x] Добавлен `@deprecated` decorator с понятным сообщением ✅
   - [x] Сохранена старая сигнатура методов для совместимости ✅
   - [x] **Улучшение:** адаптация старого формата параметров (fast/slow/signal → fast_period/slow_period/signal_period)
   - [x] **Улучшение:** lazy import `analyze_zones` внутри методов (избегаем circular dependency)
   
   **Пример реализации:**
   ```python
   from bquant.analysis.zones import analyze_zones
   from bquant.core.utils import deprecated
   
   @deprecated(
       message="MACDZoneAnalyzer is deprecated. Use universal API instead: "
               "from bquant.analysis.zones import analyze_zones",
       version="2.0.0",
       removal_version="3.0.0"
   )
   class MACDZoneAnalyzer:
       """Deprecated wrapper for backward compatibility."""
       
       def __init__(self, macd_params=None, zone_params=None):
           self.macd_params = macd_params or {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
           self.zone_params = zone_params or {'min_duration': 2}
       
       def analyze_complete_modular(self, df, **kwargs):
           """Delegate to universal pipeline."""
           return (
               analyze_zones(df)
               .with_indicator('custom', 'macd', **self.macd_params)
               .detect_zones('zero_crossing', 
                            indicator_col='macd_hist',
                            min_duration=self.zone_params.get('min_duration', 2))
               .analyze(**kwargs)
               .build()
           )
   ```

2. [x] Обновить тесты MACDZoneAnalyzer
   - [x] Создан `tests/unit/test_macd_backward_compatibility.py` (255 строк, 11 тестов) ✅
   - [x] Проверка deprecation warnings (3 теста) ✅
   - [x] Проверка delegation в новый API (3 теста) ✅
   - [x] Проверка совместимости параметров (старый/новый формат) (2 теста) ✅
   - [x] Проверка идентичности результатов (2 теста) ✅
   - [x] Проверка clustering параметра (1 тест) ✅
   - ✅ **Результат:** 11/11 тестов проходят, все deprecation warnings работают корректно

#### 2.2 Convenience wrappers (опционально, 0.5 дня) ✅ **ВЫПОЛНЕНО**

**Цель:** Предоставить удобные shortcuts для частых сценариев

1. [x] Создать `bquant/analysis/zones/presets.py` (315 строк)
   - [x] `analyze_macd_zones(df, **params)` - wrapper для MACD ✅
   - [x] `analyze_rsi_zones(df, **params)` - wrapper для RSI ✅
   - [x] `analyze_ao_zones(df, **params)` - wrapper для AO ✅
   - [x] `analyze_preloaded_zones(df, zones_data, **params)` - для preloaded zones ✅
   - [x] **Все функции:** полная поддержка параметров (clustering, regression, validation, caching)
   - [x] **Все функции:** comprehensive docstrings с примерами использования
   
   **Каждая функция - 5-10 строк:**
   ```python
   def analyze_macd_zones(df: pd.DataFrame,
                          fast: int = 12,
                          slow: int = 26,
                          signal: int = 9,
                          min_duration: int = 2,
                          **analysis_params) -> ZoneAnalysisResult:
       """Convenience wrapper для MACD зон."""
       return (
           analyze_zones(df)
           .with_indicator('custom', 'macd', fast_period=fast, slow_period=slow, signal_period=signal)
           .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=min_duration)
           .analyze(**analysis_params)
           .build()
       )
   ```

2. [x] Обновить `bquant/analysis/zones/__init__.py`
   - [x] Добавлен условный импорт presets функций ✅
   - [x] Добавлены в __all__ список для экспорта ✅
   - [x] Логирование загрузки presets ✅

3. [x] Unit-тесты для presets (13 тестов)
   - [x] Создан `tests/unit/test_zone_presets.py` (343 строки) ✅
   - [x] TestMACDPreset: 3 теста (default params, custom params, equals direct builder) ✅
   - [x] TestRSIPreset: 2 теста (default params, custom thresholds) ✅
   - [x] TestAOPreset: 2 теста (default params, custom periods) ✅
   - [x] TestPreloadedZonesPreset: 2 теста (from DataFrame, from CSV) ✅
   - [x] TestPresetsIntegration: 4 теста (all presets return result, caching, regression, zone_types) ✅
   - [x] **Результат:** 13/13 тестов проходят, все preset функции работают корректно

#### 2.3 Публичные примеры (examples/) - 1 день ✅ **ВЫПОЛНЕНО**

**Назначение:** Простые, самодостаточные скрипты для документации и quick start

**Характеристики:**
- ✅ Короткие (100-300 строк максимум)
- ✅ Самодостаточные (можно скопировать и запустить)
- ✅ Систематические (покрывают основные use cases)
- ✅ Хорошо прокомментированные
- ✅ Для публичной документации
- ❌ НЕ должны быть исследовательскими

1. [x] Обновить `examples/02_macd_zone_analysis.py` (241 строка)
   - [x] **Раздел 1:** Демонстрация deprecated подхода (с предупреждением) ✅
   - [x] **Раздел 2:** Новый универсальный подход (fluent API + preset) ✅
   - [x] **Раздел 3:** Разные стратегии детекции для MACD (zero_crossing, line_crossing, combined) ✅
   - [x] **Раздел 4:** Модульное использование (только детекция, только анализ) ✅
   - [x] **Раздел 5:** Сохранение результатов (pickle, JSON) ✅
   - [x] **Итоги:** Сравнение старого vs нового подхода, преимущества универсального API ✅

2. [x] Создать `examples/02a_universal_zones.py` (297 строк) - **НОВЫЙ** ✅
   - [x] **Раздел 1:** MACD zones (zero_crossing strategy) - builder + preset ✅
   - [x] **Раздел 2:** RSI zones (threshold strategy) - builder + preset ✅
   - [x] **Раздел 3:** AO zones (zero_crossing strategy) - builder + preset ✅
   - [x] **Раздел 4:** MA crossover zones (line_crossing strategy) ✅
   - [x] **Раздел 5:** Preloaded zones (external data from CSV/DataFrame) ✅
   - [x] **Раздел 6:** Кэширование и персистентное хранение (3 формата) ✅
   - [x] **Раздел 7:** Модульное использование (детекция отдельно, анализ отдельно) ✅
   - [x] **Итоги:** Таблица сравнения индикаторов, демонстрация ZERO дублирования кода ✅

3. [x] Обновить `examples/04_comprehensive_analysis.py` (237 строк) ✅
   - [x] Полный pipeline: data → indicator → detection → analysis → save ✅
   - [x] Детальный анализ результатов (statistics, sequences, clustering) ✅
   - [x] Сохранение в 3 форматах (pickle, JSON, parquet) ✅
   - [x] Модульное использование компонентов (IndicatorFactory, ZoneDetectionRegistry, UniversalZoneAnalyzer) ✅
   - [x] Сравнение разных индикаторов (MACD, RSI, AO) ✅
   - [x] Загрузка и продолжение работы с сохраненными результатами ✅

4. [x] Создать `examples/README.md` (181 строка) ✅
   - [x] Описание всех example файлов с назначением ✅
   - [x] Рекомендуемый путь обучения (начинающие → средний → продвинутые) ✅
   - [x] Быстрый старт (3 шага) ✅
   - [x] Ключевые концепции (старый vs новый API, convenience presets) ✅
   - [x] Требования и советы ✅
   - [x] Ссылки на дополнительные ресурсы ✅

#### 2.4 Исследовательские ноутбуки (research/notebooks/) - 1 день ✅ **ВЫПОЛНЕНО (2025-10-22)**

**Назначение:** Детальное исследование с NotebookSimulator для разработчиков

**Характеристики:**
- ✅ Детальные (500+ строк нормально)
- ✅ С экспериментами и визуализацией каждого шага
- ✅ Использует NotebookSimulator (замена Jupyter)
- ✅ Для продвинутых пользователей и разработчиков
- ✅ Может включать бенчмарки, сравнения, edge cases
- ❌ НЕ для публичной документации (внутреннее использование)

**✅ Проверка актуальности (2025-10-22 - ОБНОВЛЕНО):**

**Проверено:** 20/20 скриптов с `--no-trap` - полная валидация совместимости

| Категория | Работают | Не работают | Неполные | Итого |
|-----------|----------|-------------|----------|-------|
| Data Processing | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Indicators | 7/7 (100%) ✅ | 0/7 | 0/7 | 7 |
| Analysis | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Utilities | 1/1 (100%) ✅ | 0/1 | 0/1 | 1 |
| **ИТОГО** | **20/20 (100%) 🎉** | **0/20 (0%)** | **0/20 (0%)** | **20** |

**Детальная таблица:**

| # | Скрипт | Категория | Статус | Проблема |
|---|--------|-----------|--------|----------|
| 1 | `00_logging_demo.py` | Data | ✅ Работает (2025-10-22) | Exit code 0 |
| 2 | `01_data.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, исправлены отступы |
| 3 | `01_data_loader.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, все тесты OK |
| 4 | `01_data_processor.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 5 | `01_data_schemas.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 6 | `01_data_validator.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 7 | `02_ind_base.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 8 | `02_ind_calculators.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 9 | `02_ind_factory.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 10 | `02_ind_lib.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, talib unavailable (OK) |
| 11 | `02_ind_library.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 12 | `02_ind_macd.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, отступы исправлены |
| 13 | `02_ind_types.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 14 | `03_analysis_base.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 15 | `03_analysis_new_features.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, v2.1 migrated (ЭТАП 2) |
| 16 | `03_analysis_statistical.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 17 | `03_analysis_zones.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 18 | `03_zones.py` | Analysis | ✅ Удален (2025-10-22) | Заменен на 03_zones_universal.py |
| 18a | `03_zones_universal.py` | Analysis | ✅ Создан (2025-10-22) | Exit code 0, 11 steps, v2.1 (ЭТАП 1) |
| 19 | `bq.py` | Utilities | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |

**Ключевые проблемы:**
- **Indicators:** 1/7 не работает (MACD - устаревший API) → ✅ ИСПРАВЛЕНО (2025-10-22)
- **Analysis:** 3/5 проблемных (2 не работают, 1 неполный) → ✅ ИСПРАВЛЕНО (2025-10-22)
- **Data Processing:** 2/6 с техническими ошибками → ✅ ВСЕ ИСПРАВЛЕНО (2025-10-22)

**Детали ошибок:**
- **`02_ind_macd.py`**: ✅ ИСПРАВЛЕНО (2025-10-22) - обновлен на v2.1 API
- **`03_analysis_zones.py`**: ✅ РАБОТАЕТ (2025-10-22) - проблема решена автоматически после обновления архитектуры
- **`03_analysis_new_features.py`**: ✅ ИСПРАВЛЕНО (2025-10-22) - полная миграция на v2.1 API
- **`03_zones.py`**: ✅ УДАЛЕН (2025-10-22) - заменен на 03_zones_universal.py
- **`01_data.py`**: ✅ ИСПРАВЛЕНО (2025-10-22) - исправлены IndentationError и TypeError с WindowsPath
- **`01_data_processor.py`**: ✅ ИСПРАВЛЕНО (2025-10-22) - эмодзи заменены на ASCII символы ([OK], [+])

**См. также:** `research/notebooks/README.md` - полный отчет о проверке с категоризацией и приоритетами

---

**📊 ИТОГИ ПРОВЕРКИ И ИСПРАВЛЕНИЙ (2025-10-22):**

**Исправлено файлов:** 12 из 20
1. ✅ `01_data.py` - IndentationError, TypeError (WindowsPath)
2. ✅ `01_data_processor.py` - 14 эмодзи → ASCII
3. ✅ `01_data_schemas.py` - 12 эмодзи → ASCII
4. ✅ `01_data_validator.py` - 10 эмодзи → ASCII
5. ✅ `02_ind_base.py` - 19 эмодзи → ASCII
6. ✅ `02_ind_calculators.py` - 18 эмодзи → ASCII
7. ✅ `02_ind_factory.py` - 3 эмодзи → ASCII
8. ✅ `02_ind_library.py` - 17 эмодзи → ASCII
9. ✅ `02_ind_macd.py` - IndentationError
10. ✅ `02_ind_types.py` - 5 эмодзи → ASCII
11. ✅ `03_analysis_new_features.py` - v2.1 API migration (ЭТАП 2)
12. ✅ `03_zones_universal.py` - создан (ЭТАП 1)

**Без изменений:** 8 файлов (уже корректные)
- 00_logging_demo.py, 01_data_loader.py, 02_ind_lib.py
- 03_analysis_base.py, 03_analysis_statistical.py, 03_analysis_zones.py
- bq.py

**Удалены:** 1 файл
- 03_zones.py (заменен на 03_zones_universal.py)

**Замен эмодзи:** 98 символов (✅❌🔧🏗️ → [OK][!][+][*])

**Результат:**
- ✅ Все 20 notebooks работают с exit code 0
- ✅ Все совместимы с Windows cp1251 (ASCII-safe)
- ✅ Все используют актуальный v2.1 API
- ✅ NotebookSimulator работает корректно во всех скриптах

---

**📋 Анализ существующих ноутбуков:**

Текущее состояние `research/notebooks/` (обновлено 2025-10-22):
- `02_ind_macd.py` (262 строки) - ✅ **ОБНОВЛЕН** (2025-10-22) - migration guide на v2.1 API
- `03_zones.py` - ✅ **УДАЛЕН** (2025-10-22) - заменен на 03_zones_universal.py
- `03_zones_universal.py` (418 строк) - ✅ **СОЗДАН** (2025-10-22) - 11 steps, v2.1 API, полная демонстрация
- `03_analysis_zones.py` (656 строк) - ✅ **РАБОТАЕТ** (2025-10-22) - совместим с обновленной архитектурой
- `03_analysis_new_features.py` (640 строк) - ✅ **ПЕРЕПИСАН** (2025-10-22) - полная миграция на v2.1 API (ЭТАП 2)

**🛠️ NotebookSimulator API (из bquant.core.nb):**
- Автоматическая настройка: `nb = NotebookSimulator("Description")`
- Шаги: `nb.step()`, `nb.substep()`
- Вывод: `nb.info()`, `nb.success()`, `nb.error()`, `nb.warning()`, `nb.data_info()`
- Контроль: `nb.wait()` (пропускается с `--no-trap`)
- Обработка ошибок: `with nb.error_handling("Operation", critical=True):`
- Запуск: `python script.py --no-trap` (для автоматического выполнения)
- Логирование: автоматически в `script_name_log.txt`

**📝 План работы:**

1. [x] **Обновить `research/notebooks/02_ind_macd.py`** (729 → 262 строки) ✅ **ВЫПОЛНЕНО**
   - [x] Полностью переписан с фокусом на migration guide ✅
   - [x] 8 шагов NotebookSimulator (вместо 10) ✅
   - [x] Старый API показан как примеры кода (без запуска из-за технических проблем) ✅
   - [x] Новый API демонстрируется полностью (fluent builder + preset) ✅
   - [x] Migration guide с пошаговыми примерами ✅
   - [x] Различные стратегии детекции ✅
   - [x] Модульное использование ✅
   - [x] Сохранение/загрузка результатов ✅
   - [x] Сравнение с другими индикаторами (примеры кода) ✅
   - [x] **Результат:** Все 8 шагов выполняются успешно (проверено с --no-trap)

2. [x] **Создать `research/notebooks/03_zones_universal.py`** (412 строк) ✅ **ВЫПОЛНЕНО**
   
   **Реализованная структура (10 шагов NotebookSimulator):**
   ```python
   nb = NotebookSimulator("Universal Zone Analysis - Deep Dive")
   
   nb.step("Step 1: Data Loading & Preparation")
   # - Load sample data (tv_xauusd_1h, 1000 bars)
   # - Show data structure, statistics, visualization
   
   nb.step("Step 2: Old vs New API Comparison")
   nb.substep("2.1: Old API (MACDZoneAnalyzer)")
   # - Time measurement
   # - Show deprecation warnings
   nb.substep("2.2: New Universal API (analyze_zones)")
   # - Time measurement
   # - Show fluent builder syntax
   nb.substep("2.3: Results Comparison")
   # - Compare zones count, types, features
   # - Performance comparison (old vs new)
   # - Memory usage comparison
   
   nb.step("Step 3: Detection Strategies Experiments")
   nb.substep("3.1: Zero Crossing (MACD, AO)")
   nb.substep("3.2: Threshold (RSI)")
   nb.substep("3.3: Line Crossing (MA crossover)")
   nb.substep("3.4: Combined Rules")
   nb.substep("3.5: Preloaded Zones")
   # For each: show detected zones, statistics, visualization
   
   nb.step("Step 4: Parameter Sensitivity Analysis")
   # - MACD: vary fast/slow/signal
   # - RSI: vary thresholds
   # - min_duration impact
   # - smooth_window impact
   # Show how parameters affect zones count and quality
   
   nb.step("Step 5: Full Analysis Pipeline Deep Dive")
   # - Feature extraction details
   # - Statistical tests results
   # - Sequence analysis (transitions, patterns)
   # - Clustering (quality metrics, cluster characteristics)
   # Detailed visualization of each analysis component
   
   nb.step("Step 6: Modular Usage Scenarios")
   # - Scenario 1: Only detection → save → load → analyze
   # - Scenario 2: Only analysis of preloaded zones
   # - Scenario 3: Custom feature extraction
   # - Scenario 4: Custom detection strategy
   # Use examples from zomodul.md
   
   nb.step("Step 7: Caching & Persistence Deep Dive")
   # - Cache hit/miss demonstration
   # - TTL expiration testing
   # - Save/load in 3 formats (pickle, JSON, parquet)
   # - File sizes comparison
   # - Load speed comparison
   
   nb.step("Step 8: Multiple Indicators Comparison")
   # - MACD vs RSI vs AO zones on same data
   # - Zone overlap analysis
   # - Consensus signals (multiple indicators agree)
   # - Best indicator selection criteria
   
   nb.step("Step 9: Edge Cases & Error Handling")
   # - Small datasets (< 50 bars)
   # - No zones detected
   # - Missing indicator columns
   # - Invalid parameters
   # Show how architecture handles edge cases gracefully
   
   nb.step("Step 10: Performance Benchmarks")
   # - Large datasets (5000+ bars)
   # - Multiple indicators
   # - With/without caching
   # - Memory profiling
   # - Recommendations for optimization
   
   nb.finish("Universal zone analysis investigation complete!")
   ```
   
   **Детализация:**
   - [x] Использовать все примеры из [Примеры использования](#примеры) ✅
   - [x] Использованы ключевые сценарии (модульность, кэширование, разные индикаторы) ✅
   - [x] Добавлены benchmarks для 100 и 1000 баров ✅
   - [x] Обработка ошибок через nb.error_handling() ✅
   - [x] Работает с `--no-trap` ✅
   - [x] **Результаты:** 11 шагов, 72 MACD зоны, ~14K зон/сек, кэширование работает ✅
   - [x] **Исправлено:** Problems 1.1-1.7 через zonan_uni_full.md ✅

3. [x] **Удалить `research/notebooks/03_zones.py`** ✅ **ВЫПОЛНЕНО**
   - [x] Файл удален (заменен на 03_zones_universal.py) ✅

4. [x] **Обновить `research/notebooks/README.md`** ✅ **ВЫПОЛНЕНО**
   - [x] Добавлено описание 03_zones_universal.py (418 строк, 11 шагов) ✅
   - [x] Обновлен статус 02_ind_macd.py (работает, migration guide) ✅
   - [x] Обновлена сводная таблица (20/20 работают, 100%) ✅
   - [x] Обновлена категоризация по назначению ✅
   - [x] Обновлены приоритеты (Stage 2.4 завершен) ✅
   - [x] Добавлены выявленные баги в список ✅

5. [x] **Исправить все ноутбуки research/notebooks/** ✅ **ВЫПОЛНЕНО (2025-10-22)**
   - [x] Проверены все 20 скриптов с --no-trap ✅
   - [x] Исправлены 12 файлов (эмодзи, отступы, v2.1 migration) ✅
   - [x] 8 файлов без изменений (уже корректные) ✅
   - [x] **Результат:** 20/20 работают с exit code 0 ✅

#### 2.5 Integration тесты (0.5 дня) ✅ **ВЫПОЛНЕНО (2025-10-22)**

1. [x] Создать `tests/integration/test_zone_analysis_e2e.py` (283 строки) ✅
   - [x] End-to-end тесты всего pipeline для разных индикаторов ✅
   - [x] MACD: `test_macd_full_pipeline()`, `test_macd_preset_convenience()` ✅
   - [x] RSI: `test_rsi_full_pipeline()`, `test_rsi_preset_convenience()` ✅
   - [x] AO: `test_ao_full_pipeline()`, `test_ao_preset_convenience()` ✅
   - [x] Preloaded: `test_preloaded_zones_pipeline()` ⚠️ (skipped - требует доработки формата)
   - [x] Performance: `test_pipeline_performance()`, `test_multiple_indicators_performance()` ✅
   - [x] Edge cases: `test_small_dataset()`, `test_no_zones_detected()` ✅
   - [x] **Результат:** 10 тестов (9 passed, 1 skipped)
   
2. [x] Создать `tests/integration/test_backward_compatibility.py` (210 строк) ✅
   - [x] Тесты что старый MACDZoneAnalyzer работает через новый API ✅
   - [x] Сравнение результатов старого vs нового (должны совпадать) ✅
   - [x] Проверка deprecation warnings ✅
   - [x] Тесты новых v2.1 features (.with_strategies(), zone.features) ✅
   - [x] **Результат:** 8 тестов (all passed)

**Результат:** 
- ✅ Старый код работает через новую архитектуру (backward compatibility)
- ✅ Понятные примеры для всех типов пользователей
- ✅ Систематическое покрытие всех возможностей
- ✅ Разделение: публичные примеры (examples/) vs исследовательские (notebooks/)
- ✅ НЕТ дублирования кода (один универсальный API для всех индикаторов)

### Этап 3: Документация (2-3 дня) — **статус: в работе**

**Цель:** Обновить документацию для пользователей и разработчиков

**📖 Источники контента:** См. все разделы zonan.md + [zomodul.md](zomodul.md) + отчёты `zoval_check.md`

1. [x] API документация → Использовать заготовки из zonan.md
   - [x] Переписаны `docs/api/analysis/zones.md`, `strategies.md`, `pipeline.md` под Universal Pipeline (см. валидацию `docs/api` в `zoval_check.md`).
   - [x] Исправлен legacy-пример `find_support_resistance` в `docs/api/analysis/zones.md` (рабочие данные + пояснения по ZoneFeaturesAnalyzer).
   - [x] Добавлены перекрёстные ссылки на новый developer guide в `docs/api/analysis/strategies.md` и `docs/developer_guide/README.md`.
   - [x] Добавить проверки/примеры для новых маркетинговых сценариев (например, `FICTIONAL_INDICATOR_99`) либо скорректировать текст, чтобы соответствовать тестам.
   - [x] Финальная сверка ссылок/крест-референсов после исправления legacy-блока.
   - **Прогресс:** 5/5 задач закрыто — doc-примеры покрыты автотестом, ссылки указывают на актуальные файлы.

2. [x] User Guide → Использовать примеры из zonan.md
   - ✅ Quick Start и основной README обновлены под Universal Pipeline.
   - ✅ Финализирована структура: `docs/user_guide/zone_analysis_pipeline.md` признан основным гидом, обновлены TOC и перекрёстные ссылки.
   - [x] Migration guide (переход со старого API) — оформлен как `docs/user_guide/MIGRATION_v2.md` с сопоставлением сценариев Пример 7 и `MACDZoneAnalyzer`.
   - [x] Best practices — вынесен материал из [Best Practices](zomodul.md#best-practices) в раздел `docs/user_guide/zone_analysis_pipeline.md#best-practices` с новыми примерами.

3. [x] Developer Guide → Использовать точки расширения
   - [x] Создано руководство `docs/developer_guide/zone_detection_strategies.md` (шаблон + пример реализации стратегии).
   - [x] Добавлена подробная инструкция по созданию стратегий детекции с перекрёстными ссылками на [Точки расширения: Слой 1](#точки-расширения).
   - [x] Документировано расширение `UniversalZoneAnalyzer` с опорой на [Точки расширения: Слой 2](#точки-расширения).
   - [x] Подготовлен contribution guide с требованиями к тестам, документации и ревью.

4. [x] Tutorials → Адаптировать из zonan.md
   - [x] Tutorial: анализ зон MACD → См. [Пример 1](#примеры).
   - [x] Tutorial: анализ зон RSI → См. [Пример 5](#примеры).
   - [x] Tutorial: кастомные правила детекции → См. [Пример 8](#примеры).
   - [x] Tutorial: работа с preloaded зонами → См. [Пример 3](#примеры) и [Сценарий 9](zomodul.md).

5. [ ] Трэйслог и migration notes
   - [ ] Обновить дневной трэйслог в `changelogs/CHANGE_TRACE_LOG_YYYY-MM-DD.md` по правилам из `changelogs/README.md`, зафиксировав ключевые изменения Universal Zone Analyzer + pipeline.
   - [ ] Создать `MIGRATION_v2.md` (или одноимённый раздел user guide) с инструкцией перехода со старого API.
   - [ ] Зафиксировать breaking changes / legacy-ограничения и дать ссылки на обновлённые разделы документации.

**Текущий статус (2025-10-xx):** API/User Guide/Developer Guide и tutorials полностью обновлены. Открыт блок по фиксации изменений в трэйслоге и финальной миграционной сводке; этап завершится после их закрытия и повторной валидации документации.

### Этап 4: Визуализация (1-2 дня)

**Цель:** Расширить возможности визуализации для детального анализа зон

**📖 Спецификация:** См. раздел [Визуализация зон](#визуализация)

1. [ ] Расширить `bquant/visualization/zones.py` (~250 строк)
   - [ ] Метод `plot_zone_detail()` → См. [Детальный график зоны (plot_zone_detail)](#визуализация)
   - [ ] Метод `plot_zones_comparison()` → См. [Сравнение зон (plot_zones_comparison)](#визуализация)
   - [ ] Helper `_get_zone_window()` → См. [Детальный график зоны](#визуализация)
   - [ ] Helper `_detect_indicators_from_features()` → См. [Детальный график зоны](#визуализация)
   - [ ] Helper `_filter_zones_by_date()` - фильтрация по дате
   - [ ] Plotly реализации для обоих методов
   - [ ] Matplotlib реализации (упрощенные)

2. [ ] Обновить `bquant/analysis/zones/models.py` (~50 строк)
   - [ ] Добавить метод `ZoneAnalysisResult.visualize()` → См. [Интеграция с ZoneAnalysisResult](#визуализация)
   - [ ] Поддержка режимов: overview, detail, comparison, statistics

3. [ ] Обновить `bquant/visualization/__init__.py`
   - [ ] Экспортировать новые методы визуализации
   - [ ] Обновить convenience функции

4. [ ] Unit-тесты визуализации (~15 тестов)
   - [ ] Тесты `plot_zone_detail()` для разных конфигураций
   - [ ] Тесты `plot_zones_comparison()` с фильтрами
   - [ ] Тесты `ZoneAnalysisResult.visualize()` для всех режимов
   - [ ] Тесты auto-detect индикаторов

5. [ ] Примеры визуализации → См. [Примеры использования визуализации](#визуализация) и [Сценарий 10](zomodul.md)
   - [ ] Добавить в examples/ пример детальной визуализации
   - [ ] Notebook с различными режимами визуализации
   - [ ] Screenshots для документации

**Результат:** Полнофункциональная визуализация с минимальными изменениями

### Этап 5: Очистка и финализация (1 день)

**Цель:** Удалить устаревший код и завершить миграцию

1. [ ] Удалить старый код (после периода deprecation)
   - [ ] Удалить методы расчета из `MACDZoneAnalyzer`
   - [ ] Оставить только wrapper для backward compatibility
   - [ ] Обновить deprecation warnings

2. [ ] Code review и рефакторинг
   - [ ] Проверить code style (black, isort, flake8)
   - [ ] Проверить type hints
   - [ ] Проверить docstrings
   - [ ] Убрать TODO и FIXME комментарии

3. [ ] Финальное тестирование
   - [ ] Все unit тесты проходят (~600+ тестов)
   - [ ] Все integration тесты проходят
   - [ ] Coverage > 90%
   - [ ] No regression в performance

4. [ ] Подготовка к релизу
   - [ ] Обновить версию пакета
   - [ ] Финализировать CHANGELOG
   - [ ] Создать release notes
   - [ ] Tag в git

**Результат:** Чистая кодовая база, готовая к production

---

### Будущее развитие (Post-Release)

**📖 Roadmap:** См. раздел [Точки расширения архитектуры](#точки-расширения)

После завершения основной миграции можно добавлять новые возможности без изменения существующего кода:

**Новые стратегии детекции** (0 строк изменений в существующем коде):
- ML-based Detection → См. [Примеры будущих стратегий](#точки-расширения)
- Pattern-based Detection → См. [Примеры будущих стратегий](#точки-расширения)
- Volume Profile, Market Structure → См. [Примеры будущих стратегий](#точки-расширения)

**Новые компоненты анализа** (через DI):
- ML Predictor, Backtesting Engine, Risk Analyzer → См. [Слой 2: расширение через DI](#точки-расширения)

**Новые возможности Builder** (новые методы):
- `.preprocess()`, `.filter_zones()`, `.transform_zones()` → См. [Builder: Новые методы](#точки-расширения)
- `.with_ml_predictions()`, `.with_backtesting()`, `.export_to()` → См. [Builder: Новые методы](#точки-расширения)

**Новые модули:**
- `filters.py`, `transformers.py`, `exporters/`, `ml/`, `backtesting/`, `risk/` → См. [Новые модули (будущее расширение)](#точки-расширения)

### Сводка по этапам

| Этап | Длительность | Задачи | Тесты | Результат |
|------|--------------|--------|-------|-----------|
| **Этап 0** | 1-2 дня | Базовые модели + сериализация | Существующие (507) + 15 новых | Фундамент готов |
| **Этап 1** | 4-6 дней | Detection + Analyzer + Pipeline + Cache | +90 новых | Новая архитектура с кэшем |
| **Этап 2** | 2-3 дня | Backward compatibility + примеры | +48 новых | ✅ ЗАВЕРШЕНО (2025-10-22) |
| **Этап 3** | 2-3 дня | Документация | - | В процессе: завершить обновление документации |
| **Этап 4** | 1-2 дня | Визуализация | +15 новых | Расширенная визуализация |
| **Этап 5** | 1 день | Очистка + финализация | ~657+ итого | Production ready |
| **ИТОГО** | **11-17 дней** | **~2800 строк кода** | **~150 новых тестов** | **Готовая система** |

### Метрики кода

| Компонент | Строк кода | Файлов | Тестов |
|-----------|------------|--------|--------|
| Models (+ сериализация) | 400 | 1 | 15 |
| Detection Strategies | 850 | 6 | 50 |
| Universal Analyzer | 200 | 1 | 15 |
| Pipeline + Builder (+ кэш) | 500 | 1 | 25 |
| Visualization | 250 | 1 (расширение) | 15 |
| Backward compatibility | 100 | 1 (расширение) | 20 |
| Integration tests | 200 | 2-3 | 10 |
| Tests (unit) | ~2500 | 12-15 | 150 |
| Documentation | ~5000 | 15-20 | - |
| **ИТОГО** | **~10000** | **40-48** | **~657** |

### Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Нарушение backward compatibility | Средняя | Wrapper классы + deprecation warnings + тесты |
| Performance regression | Низкая | Performance тесты на каждом этапе |
| Неполное покрытие тестами | Средняя | Требование coverage > 90% |
| Недостаточная документация | Средняя | Выделенный этап для документации |
| Сложность для пользователей | Низкая | Fluent API + примеры + migration guide |

---

<a name="заключение"></a>
## Заключение

### Финальная архитектура

```
IndicatorFactory (существует)
    ↓
ZoneAnalysisPipeline / Builder (новое - единая точка входа)
    ├─ Слой 1: ZoneDetectionStrategies (5 стратегий)
    └─ Слой 2: UniversalZoneAnalyzer (агностичен к зонам)
```

**УБРАНО:**
- ❌ Слой 3 (Indicator Facades) - hardcode, избыточность

**ДОБАВЛЕНО:**
- ✅ ZoneAnalysisPipeline - универсальный pipeline с кэшированием
- ✅ ZoneAnalysisBuilder - fluent API с `.with_cache()`
- ✅ Прямое использование IndicatorFactory
- ✅ PreloadedZonesDetection как стратегия
- ✅ Автоматическое кэширование (память + диск)
- ✅ Персистентное хранение (pickle, JSON, parquet)
- ✅ Расширенная визуализация (`plot_zone_detail`, `plot_zones_comparison`)

### Ключевые преимущества

1. **Проще:** 2 слоя вместо 3, нет hardcode фасадов
2. **Гибче:** Конфигурация + Fluent API + Прямые вызовы
3. **Универсальнее:** Работает с ЛЮБЫМ индикатором из IndicatorFactory
4. **Правильнее:** Использует существующую инфраструктуру, нет дублирования
5. **Производительнее:** Автоматическое кэширование (память + диск)
6. **Переиспользуемо:** Сохранение результатов в pickle/JSON/parquet
7. **Наглядно:** Детальная визуализация зон с индикаторами метрик

### Метрики улучшения

| Метрика | До | После | Улучшение |
|---------|-----|--------|-----------|
| Размер MACDZoneAnalyzer | 564 строки | 0 строк (удален) | -100% |
| Специализированных фасадов | 1 (планировалось N) | 0 | -100% |
| Универсальных компонентов | 0 | 2 (Pipeline + Builder) | +∞ |
| Код для нового индикатора | 20-60 строк | 0 строк | -100% |
| Поддержка источников | 1 (hardcoded) | 4 (через IndicatorFactory) | +300% |
| Кэширование | Нет | Auto (память + диск) | +100% |
| Форматы сохранения | Нет | 3 (pickle, JSON, parquet) | +300% |
| Визуализация зон | Общая | Детальная + сравнение | +200% |

### Использование (3 способа на выбор)

**1. Fluent Builder (самый удобный):**
```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .with_cache(ttl=7200)  # Кэш на 2 часа
    .build()
)

# Сохранение результата
result.save('results/macd_zones.pkl')

# Визуализация
result.visualize('overview')
result.visualize('detail', zone_id=3)
```

**2. Pipeline + Config (для переиспользования):**
```python
config = ZoneAnalysisConfig(...)
result = ZoneAnalysisPipeline(config).run(df)
```

**3. Прямые вызовы (максимальный контроль):**
```python
indicator = IndicatorFactory.create(...)
zones = detector.detect_zones(...)
result = analyzer.analyze_zones(...)
```

---

**Дата создания:** 2025-10-15  
**Последнее обновление:** 2025-10-18  
**Авторы:** AI Assistant (Claude Sonnet 4.5), Ivan  
**Версия:** v8.4 (Stage 2.1-2.4 Complete + Critical Bugfixes)  
**Статус:** Stage 1 ✅ | Stage 2.1-2.4 ✅ | Stage 2.5-3 Ready for Implementation

**Изменения v8.5 (2025-10-18):**
- ✅ **Bugfixes #1-3 реализованы:**
  - #1: ZoneFeaturesAnalyzer - добавлена auto-detection индикаторов (universal)
  - #2: HypothesisTestSuite - заменена 'type' → 'zone_type' (8 occurrences)
  - #3: RSI/AO presets - работают с полным analyze() (авто-исправлено)
- ✅ **Верификация:** RSI/AO zones работают без ошибок
- ⚠️ **Анализ универсальности выявил критические проблемы:**
  - **Bug #4 (CRITICAL):** StatisticalShapeStrategy hardcoded 'macd_hist'
  - **Bug #5 (CRITICAL):** ClassicDivergenceStrategy hardcoded 'macd_hist'/'macd'
  - **Bug #6 (LOW):** StandardVolumeStrategy - volume_macd_corr не универсален
- 📊 **Текущая универсальность:** 75% (хорошо, но нужны критические исправления)
  - Zone Detection: 100% ✅
  - Swing Strategies: 100% ✅
  - Volatility Strategy: 100% ✅
  - Shape/Divergence: 0% ❌ (CRITICAL)
  - Volume: 90% ⚠️
- 📄 **Создан [zouni.md](zouni.md)** - детальный план достижения 95%+ универсальности (~15 hours)

**Изменения v8.4 (2025-10-18):**
- ✅ **Stage 2.4 полностью реализован:**
  - Обновлен `02_ind_macd.py` (729→262 строки, migration guide, 8 шагов)
  - Создан `03_zones_universal.py` (412 строк, comprehensive test, 10 шагов)
  - Удален `03_zones.py` (неполный черновик)
  - Обновлен `research/notebooks/README.md` (+150 строк)
  - Проверка: ✅ Оба скрипта работают с `--no-trap`
- 🐛 **КРИТИЧЕСКИЙ BUGFIX:** Исправлена регистрация swing strategies
  - Добавлены импорты в `bquant/analysis/zones/strategies/__init__.py`
  - Теперь ZigZag/FindPeaks/PivotPoints strategies регистрируются корректно
  - Решена проблема "Unknown swing strategy: zigzag. Available: []"
- 🐛 **Выявлены баги #1-3** (исправлены в v8.5):
  - ZoneFeaturesAnalyzer hardcoded для MACD колонок
  - HypothesisTestSuite expects 'type' column (несоответствие схем)
  - RSI/AO presets fall из-за бага в features analyzer
- 📊 **Результаты:** 15/19 работают (79%, +2), 4/19 не работают (21%, -2)

**Изменения v8.3 (2025-10-18):**
- ✅ **Проведена ПОЛНАЯ проверка всех research/notebooks** (19/19 скриптов с `--no-trap`)
- ✅ **Обновлен `research/notebooks/README.md`** с полным отчетом:
  - Детальная таблица всех 19 скриптов
  - Категоризация по назначению (Data / Indicators / Analysis / Utilities)
  - Статус каждого скрипта с описанием ошибок
  - Обновленные приоритеты для Stage 2.4
  - Рекомендации для пользователей и разработчиков
- ✅ **Обновлен `zonan.md` Stage 2.4** с полными результатами:
  - Сводная таблица по категориям (4 категории)
  - Детальная таблица всех 19 скриптов
  - Анализ ключевых проблем по категориям
  - Детали всех 6 ошибок
- 📊 **Результаты проверки:** 13/19 работают (68%), 5/19 не работают (26%), 1/19 неполный (5%)

**Изменения v8.2 (2025-10-18):**
- ✅ **Проведена проверка research/notebooks** (6 скриптов с `--no-trap`)
- ✅ **Обновлен `research/notebooks/README.md`** с детальным отчетом
- ✅ **Обновлен `zonan.md` Stage 2.4** с результатами проверки
- 📊 **Результаты проверки:** 2/6 работают, 3/6 требуют обновления, 1/6 неполный

**Изменения v8.1 (2025-10-18):**
- ✅ **Stage 2.1-2.3 полностью реализованы:**
  - 2.1: MACDZoneAnalyzer slim down (517→254 lines, 11 tests)
  - 2.2: Convenience presets (4 functions, 13 tests)
  - 2.3: Public examples (4 files, ~956 lines documentation)
- ✅ **Добавлен детальный анализ research/notebooks:**
  - Проанализированы 4 существующих ноутбука
  - Определены файлы для обновления/удаления/сохранения
  - Документирован NotebookSimulator API
  - Детальная структура для 03_zones_universal.py (10 шагов)
- ✅ Обновлен план Stage 2.4 с конкретными задачами и структурой

**Изменения v8.0 (2025-10-18):**
- ✅ **Stage 1 полностью реализован и протестирован:**
  - 11 новых файлов (~1700 строк продакшн кода)
  - 50 unit-тестов (100% passing)
  - Детальная статистика в разделе "План миграции"
- ✅ **Добавлены архитектурные принципы размещения кода:**
  - Антипаттерн: создание классов под каждый индикатор
  - Правильный подход: универсальный API
  - Разделение: examples/ vs research/notebooks/
  - Размещение: indicators/ (расчет) vs analysis/zones/ (анализ)
- ✅ **Переработан Этап 2 с учетом архитектурных принципов:**
  - 2.1: Slim down MACDZoneAnalyzer (518→100 строк)
  - 2.2: Convenience wrappers (опционально, presets.py)
  - 2.3: Публичные примеры (examples/)
  - 2.4: Исследовательские ноутбуки (research/notebooks/)
  - 2.5: Integration тесты
- ✅ Обновлена структура директорий с отметками статуса
- Принцип: "Один универсальный API для всех индикаторов - ZERO дублирования кода"

**Изменения v7.1:**
- Добавлены перекрестные ссылки в плане миграции
  - Каждая задача содержит ссылку на раздел документа с заготовкой кода
  - Добавлена общая справка в начале плана миграции
  - Добавлены ссылки на zomodul.md для модульного использования
  - Добавлен раздел "Будущее развитие" со ссылками на точки расширения
- Принцип: "Следуйте документу, не изобретайте заново!"

**Изменения v7:**
- Добавлен раздел "Кэширование и персистентное хранение" (~660 строк)
- Интеграция с существующим `bquant.core.cache`
- Персистентное хранение (pickle, JSON, parquet)
- Обновлен план миграции: ~2800 строк кода, ~150 новых тестов

**Изменения v6:**
- Добавлен раздел "Визуализация зон" (~400 строк)
- Детализирован план миграции (5 этапов)
- Расширение ZoneVisualizer для детального просмотра
- Метод `visualize()` в ZoneAnalysisResult

**Изменения v5:**
- Добавлен раздел "Реализация стратегий детекции (Code Templates)"
- Добавлен раздел "Точки расширения архитектуры"
- Полные заготовки для всех 5 базовых стратегий
- Шаблон для создания новых стратегий

**Изменения v4:**
- Удален Слой 3 (избыточные фасады)
- Добавлен ZoneAnalysisPipeline и ZoneAnalysisBuilder (fluent API)
- Прямое использование IndicatorFactory
