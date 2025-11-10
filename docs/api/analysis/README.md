# Analysis - Аналитические модули BQuant

## 📚 Обзор

Analysis модули содержат инструменты для статистического анализа, анализа зон и других аналитических методов для исследования финансовых данных.

## 🎉 New in Phase 3-4

### Major Extensions
- ✨ **Strategy Pattern** for extensible metrics (8 strategies implemented)
- ✨ **67 total metrics** (was: 12 base metrics)
- ✨ **Regression analysis** for predictive modeling
- ✨ **Validation suite** for model robustness testing
- ✨ **Extended hypothesis tests** (H4, ADF, H5)

### API Stability Categories
- 🟢 **Stable APIs** - Strategy Pattern, Regression, Validation (documented fully)
- 🟡 **Evolving APIs** - Some zone features may be renamed during universalization

## 🗂️ Модули

### 🔬 [bquant.analysis.statistical](statistical.md) - Статистический анализ

**Базовый анализ:**
- **StatisticalAnalyzer** - Статистический анализатор
- **run_all_hypothesis_tests()** - Запуск всех статистических тестов
- **HypothesisTestSuite** - Набор статистических тестов
- **HypothesisTestResult** - Результат тестирования гипотезы

**New in Phase 3.7-3.8 (🟢 Stable):**
- **HypothesisTestSuite** - Extended with H4, ADF, H5 tests
- **ZoneRegressionAnalyzer** - OLS regression for duration and return prediction
- **RegressionResult** - Regression model results with diagnostics
- **ValidationSuite** - 4 validation methods (out-of-sample, walk-forward, sensitivity, monte-carlo)
- **ValidationResult** - Validation test results

### 📊 [bquant.analysis.zones](zones.md) - Universal Zone Analysis Pipeline v2.1

> **✅ v2.1 - Truly Universal Architecture**

**Universal Pipeline API:**
- **analyze_zones()** - Entry point для Universal Pipeline
- **ZoneAnalysisBuilder** - Fluent interface для настройки анализа
- **ZoneAnalysisResult** - Результат анализа с полным набором данных
- **ZoneInfo** - Модель зоны с полным контекстом

**Legacy API (Deprecated):**
- **ZoneFeaturesAnalyzer** - Анализ характеристик зон (deprecated)
- **ZoneSequenceAnalyzer** - Анализ последовательностей зон (deprecated)
- **Zone** class → **ZoneInfo** dataclass
- **find_support_resistance()** → Universal detection strategies

**New in v2.1:**
- **Universal Pipeline** - работает с ЛЮБЫМ индикатором
- **indicator_context** - зоны сами описывают стратегию детекции
- **115 тестов, 100% pass rate** - доказательство универсальности

**Документация по глобальным свингам:**
- [Модели](zones/models.md) — `SwingPoint`, `SwingContext`, расширения `ZoneInfo`
- [Пайплайн](zones/pipeline.md) — `_calculate_global_swings`, `_inject_swing_context`, `with_swing_scope()`
- [Стратегии](zones/strategies.md) — протокол `SwingCalculationStrategy`, ZigZag/FindPeaks/PivotPoints

### 🎨 [bquant.analysis.zones.strategies](strategies.md) - Strategy Pattern (New)

> **API Stability:** 🟢 STABLE - won't change

**8 implemented strategies:**
- **Swing strategies** (3): ZigZag, FindPeaks, PivotPoints → 23 metrics
- **Shape strategies** (1): StatisticalShape → 3 metrics
- **Divergence strategies** (1): ClassicDivergence → 4 metrics
- **Volatility strategies** (1): CombinedVolatility → 10 metrics
- **Volume strategies** (1): StandardVolume → 4 metrics

**Infrastructure:**
- **StrategyRegistry** - Centralized strategy registration
- **Protocols** - Type-safe strategy contracts
- **Dataclasses** - Structured metric results
- **Factory functions** - Strategy creation from config

### 🏗️ [bquant.analysis (base)](base.md) - Базовые классы анализа
- **BaseAnalyzer** - Базовый класс анализатора (из bquant.analysis)
- **AnalysisResult** - Результат анализа (из bquant.analysis)
- **AnalysisParams** - Параметры анализа (из bquant.analysis)
- **AnalysisRegistry** - Реестр анализаторов (из bquant.analysis)

## 🔍 Быстрый поиск

### По функциональности

#### Статистический анализ
- `run_all_hypothesis_tests()` - Все статистические тесты
- `HypothesisTestSuite` - Набор статистических тестов
- `StatisticalAnalyzer` - Статистический анализатор
- `calculate_correlation()` - Расчет корреляции
- `perform_t_test()` - T-тест

#### Анализ зон
- `ZoneFeaturesAnalyzer.analyze()` - Анализ характеристик зон
- `ZoneSequenceAnalyzer.analyze()` - Анализ последовательностей
- `extract_zone_features()` - Извлечение характеристик зон
- `analyze_transitions()` - Анализ переходов между зонами

#### Базовый анализ
- `BaseAnalyzer.analyze()` - Базовый анализ
- `BaseAnalyzer.validate_data()` - Валидация данных
- `BaseAnalyzer.get_params()` - Получение параметров
- `BaseAnalyzer.set_params()` - Установка параметров

### По типу

#### 🏗️ Классы
- `BaseAnalyzer` - Базовый класс анализатора
- `StatisticalAnalyzer` - Статистический анализатор
- `ZoneFeaturesAnalyzer` - Анализатор характеристик зон
- `ZoneSequenceAnalyzer` - Анализатор последовательностей зон

#### 🔧 Функции
- `run_all_hypothesis_tests()` - Статистические тесты
- `HypothesisTestSuite` - Набор статистических тестов
- `extract_zone_features()` - Извлечение характеристик зон
- `analyze_transitions()` - Анализ переходов

#### 📋 Типы данных
- `HypothesisTestResult` - Результат тестирования гипотезы
- `ZoneFeatures` - Характеристики зоны
- `TransitionAnalysis` - Анализ переходов
- `AnalysisResult` - Результат анализа

## 💡 Примеры использования

### Universal Pipeline v2.1

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Universal Pipeline с автоматическими hypothesis tests
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', divergence='classic')
    .analyze(clustering=True)  # Автоматически включает hypothesis tests
    .build()
)

# Анализ результатов
print(f"Найдено зон: {len(result.zones)}")
if result.hypothesis_tests:
    for test_name, test_result in result.hypothesis_tests.results.items():
        print(f"{test_name}:")
        # Проверяем структуру результата
        if hasattr(test_result, 'p_value'):
            print(f"  p-value: {test_result.p_value:.4f}")
            print(f"  Significant: {test_result.is_significant}")
        elif isinstance(test_result, dict) and 'p_value' in test_result:
            print(f"  p-value: {test_result['p_value']:.4f}")
            print(f"  Significant: {test_result['is_significant']}")
        else:
            print(f"  Result: {test_result}")
```

### Тестирование отдельной гипотезы

```python
from bquant.analysis.statistical import run_all_hypothesis_tests
import numpy as np
from scipy import stats

# Тестирование гипотезы о различии волатильности между bull и bear зонами
bull_volatility = [zone.features.get('avg_volatility', 0) for zone in result.zones 
                   if zone.type == 'bull' and zone.features]
bear_volatility = [zone.features.get('avg_volatility', 0) for zone in result.zones 
                   if zone.type == 'bear' and zone.features]

if len(bull_volatility) > 0 and len(bear_volatility) > 0:
    # T-тест
    t_stat, p_value = stats.ttest_ind(bull_volatility, bear_volatility)
    
    print(f"T-test result:")
    print(f"  p-value: {p_value:.4f}")
    print(f"  Significant: {p_value < 0.05}")
    print(f"  t-statistic: {t_stat:.4f}")
```

### Анализ характеристик зон (Universal Pipeline)

```python
# Universal Pipeline автоматически извлекает характеристики
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', volatility='combined')
    .analyze(clustering=True)
    .build()
)

# Анализ результатов
print(f"Zone features analysis:")
print(f"  Total zones analyzed: {len(result.zones)}")
for i, zone in enumerate(result.zones[:3]):
    if zone.features:
        print(f"  Zone {i}: volatility={zone.features.get('volatility_regime', 'unknown')}")
        print(f"    Swings: {zone.features.get('num_swings', 0)}")
        print(f"    Duration: {zone.features.get('duration', 0):.2f}")
```

### Анализ последовательностей зон (Universal Pipeline)

```python
# Universal Pipeline с sequence analysis
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)  # sequence analysis включен автоматически
    .build()
)

# Анализ переходов между зонами
if result.sequence_analysis:
    print(f"Transition analysis:")
    print(f"  Bull to Bear transitions: {result.sequence_analysis.get('bull_to_bear', 0)}")
    print(f"  Bear to Bull transitions: {result.sequence_analysis.get('bear_to_bull', 0)}")

# Кластерный анализ зон
if result.clustering:
    print(f"Cluster analysis:")
    print(f"  Number of clusters: {result.clustering.get('n_clusters', 0)}")
    print(f"  Cluster labels: {result.clustering.get('cluster_labels', [])[:5]}...")
```

### Комбинированный статистический анализ

```python
import numpy as np
from bquant.analysis.statistical import StatisticalAnalyzer

# Создание статистического анализатора
stat_analyzer = StatisticalAnalyzer()

# Подготовка данных для анализа
bull_zones = [zone for zone in result.zones if zone.type == 'bull']
bear_zones = [zone for zone in result.zones if zone.type == 'bear']

# Извлечение характеристик
bull_durations = [zone.duration for zone in bull_zones]
bear_durations = [zone.duration for zone in bear_zones]
bull_amplitudes = [zone.amplitude for zone in bull_zones]
bear_amplitudes = [zone.amplitude for zone in bear_zones]

# Комплексный статистический анализ
from scipy import stats

# T-тест для сравнения групп
duration_t_stat, duration_p_value = stats.ttest_ind(bull_durations, bear_durations)
amplitude_t_stat, amplitude_p_value = stats.ttest_ind(bull_amplitudes, bear_amplitudes)

# Описательная статистика
bull_duration_stats = {
    'mean': np.mean(bull_durations),
    'std': np.std(bull_durations),
    'min': np.min(bull_durations),
    'max': np.max(bull_durations)
}

bear_duration_stats = {
    'mean': np.mean(bear_durations),
    'std': np.std(bear_durations),
    'min': np.min(bear_durations),
    'max': np.max(bear_durations)
}

# Вывод результатов
print(f"\nDuration comparison:")
print(f"  p-value: {duration_p_value:.4f}")
print(f"  Significant: {duration_p_value < 0.05}")

print(f"\nBull duration stats:")
print(f"  Mean: {bull_duration_stats['mean']:.4f}")
print(f"  Std: {bull_duration_stats['std']:.4f}")
print(f"  Min: {bull_duration_stats['min']:.4f}")
print(f"  Max: {bull_duration_stats['max']:.4f}")
```

### Создание собственного анализатора

```python
from bquant.analysis import BaseAnalyzer, AnalysisResult
import numpy as np

class VolatilityAnalyzer(BaseAnalyzer):
    """Анализатор волатильности"""
    
    def __init__(self, window_size=20):
        super().__init__('VolatilityAnalyzer')
        self.window_size = window_size
    
    def analyze(self, data):
        """Анализ волатильности"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for volatility analysis")
        
        # Расчет волатильности
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=self.window_size).std()
        
        # Статистики волатильности
        volatility_stats = {
            'mean': volatility.mean(),
            'std': volatility.std(),
            'min': volatility.min(),
            'max': volatility.max(),
            'current': volatility.iloc[-1]
        }
        
        return AnalysisResult(
            analysis_type='VolatilityAnalyzer',
            results=volatility_stats,
            data_size=len(volatility),
            metadata={'window_size': self.window_size}
        )
    
    def validate_data(self, data):
        """Валидация данных"""
        required_columns = ['close']
        return all(col in data.columns for col in required_columns)

# Использование собственного анализатора
volatility_analyzer = VolatilityAnalyzer(window_size=20)
volatility_result = volatility_analyzer.analyze(data)

print(f"Volatility analysis:")
print(f"  Mean volatility: {volatility_result.results['mean']:.4f}")
print(f"  Current volatility: {volatility_result.results['current']:.4f}")
```

### Экспорт результатов анализа

```python
import json
import pandas as pd
from bquant.analysis.statistical import run_all_hypothesis_tests

# Выполнение анализа
hypothesis_results = run_all_hypothesis_tests(zones_info)

# Подготовка данных для экспорта
export_data = {
    'analysis_date': str(pd.Timestamp.now()),
    'data_info': {
        'symbol': 'XAUUSD',
        'timeframe': '1H',
        'zones_count': len(result.zones)
    },
    'hypothesis_tests': {
        test_name: {
            'p_value': float(test_result.p_value),
            'is_significant': test_result.is_significant,
            'effect_size': float(test_result.effect_size),
            'test_statistic': float(test_result.test_statistic),
            'alpha': float(test_result.alpha)
        }
        for test_name, test_result in hypothesis_results.items()
    }
}

# Экспорт в JSON
with open('statistical_analysis.json', 'w') as f:
    json.dump(export_data, f, indent=2)

print("Statistical analysis exported to statistical_analysis.json")
```

## 🔗 Связанные разделы

- **[Core Modules](../core/README.md)** - Базовые модули
- **[Data Modules](../data/README.md)** - Модули данных
- **[Indicators](../indicators/README.md)** - Технические индикаторы
- **[Visualization](../visualization/README.md)** - Модули визуализации

## 📖 Детальная документация

- **[Universal Pipeline](pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zone Detection Strategies](strategies.md)** - Детальное описание 5 стратегий детекции
- **[Statistical Module](statistical.md)** - Подробная документация статистического анализа
- **[Zones Module](zones.md)** - Universal API для анализа зон
- **[Base Module](base.md)** - Документация базовых классов анализа

## 🚀 Руководство по расширению

### Создание нового анализатора

1. **Наследование от BaseAnalyzer**
2. **Реализация метода analyze()**
3. **Валидация данных**
4. **Возврат AnalysisResult**

### Лучшие практики

- Используйте научно обоснованные статистические методы
- Валидируйте входные данные
- Документируйте статистические тесты и их интерпретацию
- Учитывайте множественные сравнения

---

**Следующий раздел:** [Visualization](../visualization/README.md) 📊
