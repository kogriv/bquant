# bquant.analysis.statistical — Статистический анализ

## Обзор

Модуль предоставляет инструменты описательной статистики, проверки нормальности,
корреляционного анализа, тестирования гипотез, регрессионного моделирования и валидации
для данных зон.

## Основные классы и функции

- `StatisticalAnalyzer(config=None)`
  - `descriptive_statistics(series, name='data') -> Dict`
  - `normality_test(series, alpha=None) -> Dict`
  - `correlation_analysis(x, y, methods=None) -> Dict`
  - `t_test(sample1, sample2=None, mu=0, alternative='two-sided') -> Dict`
  - `analyze(df) -> AnalysisResult`
- Утилиты:
  - `quick_stats(series) -> Dict`
  - `test_normality(series, alpha=0.05) -> bool`
  - `correlation_matrix(df, method='pearson') -> DataFrame`
- Тестирование гипотез (из `hypothesis_testing`):
  - `HypothesisTestResult`, `HypothesisTestSuite`
  - `run_all_hypothesis_tests(zones_features, alpha=0.05) -> Dict`
  - `run_single_hypothesis_test(zones_features, test_type, alpha=0.05) -> HypothesisTestResult`
- Регрессионный анализ:
  - `ZoneRegressionAnalyzer`
- Валидация моделей:
  - `ValidationSuite`

## Подготовка данных

Примеры ниже используют единый набор синтетических данных зон и цен.

```python
import numpy as np
import pandas as pd


def generate_sample_zones(seed: int = 42, count: int = 120):
    rng = np.random.default_rng(seed)
    base_price = 2050.0
    zones = []

    for idx in range(count):
        zone_type = 'bull' if idx % 2 == 0 else 'bear'
        duration = int(rng.integers(5, 45))
        price_return = float(rng.normal(0.018 if zone_type == 'bull' else -0.012, 0.015))
        hist_slope = float(rng.normal(0.35 if zone_type == 'bull' else -0.30, 0.10))
        macd_amplitude = float(rng.normal(1.20, 0.25))
        hist_amplitude = float(abs(rng.normal(0.90, 0.20)))
        price_range_pct = float(abs(rng.normal(0.025, 0.010)))
        num_peaks = int(rng.integers(1, 5))
        num_troughs = int(rng.integers(1, 5))
        num_swings = num_peaks + num_troughs
        hist_skewness = float(rng.normal(0.0, 0.4))
        volatility_score = float(rng.normal(0.6, 0.15))
        divergence_strength = float(rng.normal(0.5, 0.2))
        correlation_price_hist = float(rng.uniform(-0.2, 0.95))
        price_return_atr = float(abs(price_return) + rng.uniform(0.004, 0.020))
        atr = float(rng.uniform(0.3, 1.5))
        start_price = float(base_price + rng.normal(0, 45) + idx * rng.normal(0.5, 0.3))

        zone = {
            'zone_id': idx,
            'zone_type': zone_type,
            'duration': duration,
            'price_return': price_return,
            'hist_slope': hist_slope,
            'macd_amplitude': macd_amplitude,
            'hist_amplitude': hist_amplitude,
            'price_range_pct': price_range_pct,
            'num_peaks': num_peaks,
            'num_troughs': num_troughs,
            'num_swings': num_swings,
            'hist_skewness': hist_skewness,
            'volatility_score': volatility_score,
            'divergence_strength': divergence_strength,
            'correlation_price_hist': correlation_price_hist,
            'price_return_atr': price_return_atr,
            'atr': atr,
            'drawdown_from_peak': float(abs(rng.normal(0.03, 0.01))),
            'rally_from_trough': float(abs(rng.normal(0.035, 0.01))),
            'start_price': start_price,
        }

        zones.append(zone)

    return zones


def generate_market_data(seed: int = 7, periods: int = 360):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0008, 0.008, periods)
    close = 2000.0 * np.cumprod(1 + returns)
    open_ = np.concatenate(([close[0]], close[:-1]))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.0005, 0.01, periods))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.0005, 0.01, periods))
    volume = rng.integers(15_000, 45_000, periods)
    indicator = pd.Series(close).rolling(5).mean().fillna(method='bfill')
    duration_proxy = rng.integers(5, 30, periods)

    dates = pd.date_range('2024-01-01', periods=periods, freq='H')
    market_data = pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'indicator': indicator,
        'duration_proxy': duration_proxy,
    }, index=dates)

    return market_data


zones_features = generate_sample_zones()
market_data = generate_market_data()
```

## Примеры статистического анализатора

Описательные статистики и проверка нормальности:

```python
import pandas as pd
from bquant.analysis.statistical import StatisticalAnalyzer

sa = StatisticalAnalyzer({'alpha': 0.05})
series = pd.Series([1, 2, 3, 4, 5, 6], dtype=float)
print(sa.descriptive_statistics(series))
print(sa.normality_test(series))
```

Корреляции и t-тест с уменьшенным порогом выборки:

```python
import pandas as pd
from bquant.analysis.statistical import StatisticalAnalyzer

df = pd.DataFrame({
    'a': [1, 2, 3, 4, 5],
    'b': [2, 1, 2, 3, 4]
})

sa_small = StatisticalAnalyzer({'min_sample_size': 5})
print(sa_small.correlation_analysis(df['a'], df['b']))
print(sa_small.t_test(df['a'], df['b']))
```

## Тестирование гипотез

Полный запуск тестов и одиночный вызов:

```python
from bquant.analysis.statistical import (
    run_all_hypothesis_tests,
    run_single_hypothesis_test
)

all_tests = run_all_hypothesis_tests(zones_features, alpha=0.05)
print(all_tests['summary'])

support_resistance = run_single_hypothesis_test(
    zones_features,
    'support_resistance',
    price_levels=[1950.0, 2050.0, 2150.0]
)
print(support_resistance.metadata['price_levels'])
```

### HypothesisTestSuite

```python
from bquant.analysis.statistical import HypothesisTestSuite

test_suite = HypothesisTestSuite(alpha=0.05)
```

#### H1: Гипотеза длительности зон

```python
result = test_suite.test_zone_duration_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"Long zones avg return: {result.metadata['long_zones_mean_return']:.3%}")
print(f"Short zones avg return: {result.metadata['short_zones_mean_return']:.3%}")
```

#### H3: Гипотеза асимметрии bull/bear

```python
result = test_suite.test_bull_bear_asymmetry_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"Bull duration: {result.metadata['duration_test']['bull_mean']:.1f}")
print(f"Bear duration: {result.metadata['duration_test']['bear_mean']:.1f}")
```

#### H4: Корреляция и просадка

```python
result = test_suite.test_correlation_drawdown_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"High corr avg drawdown: {result.metadata['high_corr_mean_drawdown']:.3%}")
print(f"Low corr avg drawdown: {result.metadata['low_corr_mean_drawdown']:.3%}")
```

#### ADF: Стационарность длительности

```python
result = test_suite.test_zone_duration_stationarity(zones_features)
print(f"Stationary: {result.significant}")
print(f"ADF statistic: {result.statistic:.3f}")
print(f"P-value: {result.p_value:.4f}")
```

#### H5: Поддержка/сопротивление

```python
# Автоопределение уровней
auto_result = test_suite.test_support_resistance_hypothesis(zones_features)
print(f"Levels identified: {auto_result.metadata['price_levels_count']}")
print(f"Test used: {auto_result.metadata['test_used']}")

# Пользовательские уровни
manual_result = test_suite.test_support_resistance_hypothesis(
    zones_features,
    price_levels=[1950.0, 2050.0, 2150.0],
    tolerance_pct=0.5
)
print(f"Near level mean: {manual_result.metadata['near_level_mean_duration']:.1f}")
```

### Запуск полного набора

```python
full_suite = test_suite.run_all_tests(zones_features)
print(full_suite.results['summary'])
```

## Регрессионный анализ (фаза 3.8)

```python
from bquant.analysis.statistical import ZoneRegressionAnalyzer

regressor = ZoneRegressionAnalyzer()
```

Прогноз длительности зоны по умолчанию:

```python
duration_model = regressor.predict_zone_duration(zones_features)
print(f"Model R²: {duration_model.r_squared:.3f}")
print(f"Adjusted R²: {duration_model.adjusted_r_squared:.3f}")
```

Кастомные предикторы длительности:

```python
custom_model = regressor.predict_zone_duration(
    zones_features,
    predictors=[
        'num_swings',
        'hist_skewness',
        'volatility_score',
        'divergence_strength',
        'price_return_atr'
    ]
)
print(custom_model.coefficients)
```

Прогноз доходности зоны:

```python
return_model = regressor.predict_price_return(
    zones_features,
    predictors=['duration', 'macd_amplitude', 'correlation_price_hist', 'hist_slope', 'num_peaks']
)
print(f"Return model R²: {return_model.r_squared:.3f}")
print(f"Coefficients: {return_model.coefficients}")
```

## Валидация моделей (ValidationSuite)

```python
from bquant.analysis import AnalysisResult
from bquant.analysis.statistical import StatisticalAnalyzer
from bquant.analysis.validation import ValidationSuite

validator = ValidationSuite(degradation_threshold=0.25)


def analyze_for_validation(data, min_duration: int = 6, min_amplitude: float = 0.004):
    analyzer = StatisticalAnalyzer({'alpha': 0.05, 'min_sample_size': 5})
    analyzer.analyze(data[['close', 'indicator']])
    returns = data['close'].pct_change().dropna()
    event_count = int((returns.abs() > min_amplitude).sum())
    total_zones = max(event_count // max(min_duration, 1), 1)

    return AnalysisResult(
        analysis_type='statistical_validation',
        results={
            'total_zones': float(total_zones),
            'avg_return': float(returns.mean()),
            'volatility': float(returns.std()),
        },
        data_size=len(data),
        metadata={
            'min_duration': min_duration,
            'min_amplitude': min_amplitude,
            'event_count': event_count,
        }
    )
```

### Out-of-sample

```python
oos = validator.out_of_sample_test(
    analyze_for_validation,
    market_data,
    train_ratio=0.7,
    metric_key='total_zones'
)
print(oos.metadata['split_index'])
print(oos.train_metrics['total_zones'], oos.test_metrics['total_zones'])
```

### Walk-forward

```python
wf = validator.walk_forward_test(
    analyze_for_validation,
    market_data,
    train_window=120,
    test_window=60,
    step_size=60,
    metric_key='total_zones'
)
print(wf.metadata['iterations_count'])
print(wf.metadata['avg_train_metric'], wf.metadata['avg_test_metric'])
```

### Sensitivity analysis

```python
sensitivity = validator.sensitivity_analysis(
    analyze_for_validation,
    market_data,
    param_ranges={
        'min_duration': [4, 6, 8],
        'min_amplitude': [0.003, 0.004, 0.005]
    },
    metric_key='total_zones'
)
print(sensitivity.metadata['stability_score'])
print(sensitivity.metadata['best_params'])
```

### Monte Carlo

```python
monte_carlo = validator.monte_carlo_test(
    analyze_for_validation,
    market_data,
    n_simulations=32,
    metric_key='total_zones',
    shuffle_method='prices'
)
print(monte_carlo.metadata['real_metric_value'])
print(monte_carlo.metadata['p95_threshold'])
```

---

## См. также

- [База анализа](base.md)
- [Анализ зон](zones.md)
- [Регрессионный анализ](#регрессионный-анализ-фаза-38)
