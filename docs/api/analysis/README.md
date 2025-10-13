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
- **test_single_hypothesis()** - Тестирование отдельной гипотезы
- **HypothesisTestResult** - Результат тестирования гипотезы

**New in Phase 3.7-3.8 (🟢 Stable):**
- **HypothesisTestSuite** - Extended with H4, ADF, H5 tests
- **ZoneRegressionAnalyzer** - OLS regression for duration and return prediction
- **RegressionResult** - Regression model results with diagnostics
- **ValidationSuite** - 4 validation methods (out-of-sample, walk-forward, sensitivity, monte-carlo)
- **ValidationResult** - Validation test results

### 📊 [bquant.analysis.zones](zones.md) - Анализ зон

> **Note:** 🟡 Some APIs may evolve during universalization (field names)

**Analyzers:**
- **ZoneFeaturesAnalyzer** - Анализ характеристик зон (with Strategy Pattern support)
- **ZoneSequenceAnalyzer** - Анализ последовательностей зон
- **ZoneFeatures** - Характеристики зоны (18 base fields + metadata)
- **TransitionAnalysis** - Анализ переходов

**New in Phase 3 (🟢 Strategies are stable):**
- See [strategies.md](strategies.md) for full Strategy Pattern documentation

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
- **BaseAnalyzer** - Базовый класс анализатора
- **AnalysisResult** - Результат анализа
- **AnalysisParams** - Параметры анализа
- **AnalysisRegistry** - Реестр анализаторов

## 🔍 Быстрый поиск

### По функциональности

#### Статистический анализ
- `run_all_hypothesis_tests()` - Все статистические тесты
- `test_single_hypothesis()` - Один статистический тест
- `calculate_correlation()` - Расчет корреляции
- `perform_t_test()` - T-тест
- `perform_chi_square_test()` - Chi-square тест

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
- `test_single_hypothesis()` - Тестирование гипотезы
- `extract_zone_features()` - Извлечение характеристик зон
- `analyze_transitions()` - Анализ переходов

#### 📋 Типы данных
- `HypothesisTestResult` - Результат тестирования гипотезы
- `ZoneFeatures` - Характеристики зоны
- `TransitionAnalysis` - Анализ переходов
- `AnalysisResult` - Результат анализа

## 💡 Примеры использования

### Статистический анализ

```python
from bquant.analysis.statistical import run_all_hypothesis_tests, test_single_hypothesis
from bquant.indicators import MACDZoneAnalyzer
from bquant.data.samples import get_sample_data

# Загрузка данных и анализ MACD
data = get_sample_data('tv_xauusd_1h')
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# Подготовка данных для статистического анализа
zones_info = {
    'zones_features': [zone.features for zone in result.zones if zone.features],
    'zones': result.zones,
    'statistics': result.statistics
}

# Запуск всех статистических тестов
hypothesis_results = run_all_hypothesis_tests(zones_info)

# Анализ результатов
for test_name, test_result in hypothesis_results.items():
    print(f"{test_name}:")
    print(f"  p-value: {test_result.p_value:.4f}")
    print(f"  Significant: {test_result.is_significant}")
    print(f"  Effect size: {test_result.effect_size:.4f}")
```

### Тестирование отдельной гипотезы

```python
from bquant.analysis.statistical import test_single_hypothesis

# Тестирование гипотезы о различии волатильности между bull и bear зонами
bull_volatility = [zone.features.avg_volatility for zone in result.zones 
                   if zone.zone_type == 'bull' and zone.features]
bear_volatility = [zone.features.avg_volatility for zone in result.zones 
                   if zone.zone_type == 'bear' and zone.features]

# T-тест
t_test_result = test_single_hypothesis(
    't_test',
    data1=bull_volatility,
    data2=bear_volatility,
    alpha=0.05
)

print(f"T-test result:")
print(f"  p-value: {t_test_result.p_value:.4f}")
print(f"  Significant: {t_test_result.is_significant}")
print(f"  Effect size: {t_test_result.effect_size:.4f}")
```

### Анализ характеристик зон

```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

# Создание анализатора характеристик зон
features_analyzer = ZoneFeaturesAnalyzer()

# Анализ характеристик зон
features_analysis = features_analyzer.analyze(result.zones)

# Анализ результатов
print(f"Zone features analysis:")
print(f"  Total zones analyzed: {features_analysis.total_zones}")
print(f"  Average volatility: {features_analysis.avg_volatility:.4f}")
print(f"  Average amplitude: {features_analysis.avg_amplitude:.4f}")
print(f"  Peak distribution: {features_analysis.peak_distribution}")
```

### Анализ последовательностей зон

```python
from bquant.analysis.zones import ZoneSequenceAnalyzer

# Создание анализатора последовательностей
sequence_analyzer = ZoneSequenceAnalyzer()

# Анализ последовательностей зон
sequence_analysis = sequence_analyzer.analyze(result.zones)

# Анализ переходов между зонами
print(f"Transition analysis:")
print(f"  Bull to Bear transitions: {sequence_analysis.transitions.bull_to_bear}")
print(f"  Bear to Bull transitions: {sequence_analysis.transitions.bear_to_bull}")
print(f"  Average transition duration: {sequence_analysis.avg_transition_duration:.2f}")

# Кластерный анализ зон
print(f"Cluster analysis:")
print(f"  Number of clusters: {sequence_analysis.clusters.n_clusters}")
print(f"  Cluster sizes: {sequence_analysis.clusters.cluster_sizes}")
```

### Комбинированный статистический анализ

```python
import numpy as np
from bquant.analysis.statistical import StatisticalAnalyzer

# Создание статистического анализатора
stat_analyzer = StatisticalAnalyzer()

# Подготовка данных для анализа
bull_zones = [zone for zone in result.zones if zone.zone_type == 'bull']
bear_zones = [zone for zone in result.zones if zone.zone_type == 'bear']

# Извлечение характеристик
bull_durations = [zone.duration for zone in bull_zones]
bear_durations = [zone.duration for zone in bear_zones]
bull_amplitudes = [zone.amplitude for zone in bull_zones]
bear_amplitudes = [zone.amplitude for zone in bear_zones]

# Комплексный статистический анализ
analysis_results = {
    'duration_comparison': stat_analyzer.compare_groups(bull_durations, bear_durations),
    'amplitude_comparison': stat_analyzer.compare_groups(bull_amplitudes, bear_amplitudes),
    'bull_duration_stats': stat_analyzer.descriptive_statistics(bull_durations),
    'bear_duration_stats': stat_analyzer.descriptive_statistics(bear_durations)
}

# Вывод результатов
for analysis_name, result in analysis_results.items():
    print(f"\n{analysis_name}:")
    if hasattr(result, 'p_value'):
        print(f"  p-value: {result.p_value:.4f}")
        print(f"  Significant: {result.is_significant}")
    else:
        print(f"  Mean: {result.mean:.4f}")
        print(f"  Std: {result.std:.4f}")
        print(f"  Min: {result.min:.4f}")
        print(f"  Max: {result.max:.4f}")
```

### Создание собственного анализатора

```python
from bquant.analysis.base import BaseAnalyzer, AnalysisResult
import numpy as np

class VolatilityAnalyzer(BaseAnalyzer):
    """Анализатор волатильности"""
    
    def __init__(self, window_size=20):
        super().__init__('VolatilityAnalyzer', {'window_size': window_size})
    
    def analyze(self, data):
        """Анализ волатильности"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for volatility analysis")
        
        window_size = self.params['window_size']
        
        # Расчет волатильности
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=window_size).std()
        
        # Статистики волатильности
        volatility_stats = {
            'mean': volatility.mean(),
            'std': volatility.std(),
            'min': volatility.min(),
            'max': volatility.max(),
            'current': volatility.iloc[-1]
        }
        
        return AnalysisResult(
            analyzer_name='VolatilityAnalyzer',
            data=volatility,
            statistics=volatility_stats,
            params=self.params
        )
    
    def validate_data(self, data):
        """Валидация данных"""
        required_columns = ['close']
        return all(col in data.columns for col in required_columns)

# Использование собственного анализатора
volatility_analyzer = VolatilityAnalyzer(window_size=20)
volatility_result = volatility_analyzer.analyze(data)

print(f"Volatility analysis:")
print(f"  Mean volatility: {volatility_result.statistics['mean']:.4f}")
print(f"  Current volatility: {volatility_result.statistics['current']:.4f}")
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

- **[Statistical Module](statistical.md)** - Подробная документация статистического анализа
- **[Zones Module](zones.md)** - Документация анализа зон
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
