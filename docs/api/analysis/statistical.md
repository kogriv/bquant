# bquant.analysis.statistical — Статистический анализ

## Обзор

Инструменты описательной статистики, нормальности, корреляций и комплексного анализа данных. Дополнительно: модуль тестирования гипотез.

## Классы и функции

- `StatisticalAnalyzer(config=None)`
  - `descriptive_statistics(series, name='data') -> Dict`
  - `normality_test(series, alpha=None) -> Dict`
  - `correlation_analysis(x, y, methods=None) -> Dict`
  - `t_test(sample1, sample2=None, mu=0, alternative='two-sided') -> Dict`
  - `analyze(df) -> AnalysisResult` — комплексный анализ числовых колонок

- Утилиты:
  - `quick_stats(series) -> Dict`
  - `test_normality(series, alpha=0.05) -> bool`
  - `correlation_matrix(df, method='pearson') -> DataFrame`

- Тестирование гипотез (из `hypothesis_testing`):
  - `HypothesisTestResult`, `HypothesisTestSuite`
  - `run_all_hypothesis_tests(zones_features, alpha=0.05) -> Dict`
  - `test_single_hypothesis(zones_features, test_type, alpha=0.05) -> HypothesisTestResult`

## Примеры

Описательные статистики и нормальность:
```python
import pandas as pd
from bquant.analysis.statistical import StatisticalAnalyzer

sa = StatisticalAnalyzer({'alpha': 0.05})
series = pd.Series([1,2,3,4,5,6])
print(sa.descriptive_statistics(series))
print(sa.normality_test(series))
```

Корреляции и t-тест:
```python
import pandas as pd
from bquant.analysis.statistical import StatisticalAnalyzer

sa = StatisticalAnalyzer()
df = pd.DataFrame({'a':[1,2,3,4,5], 'b':[2,1,2,3,4]})
print(sa.correlation_analysis(df['a'], df['b']))
print(sa.t_test(df['a'], df['b']))
```

Гипотезы по зонам:
```python
from bquant.analysis.statistical import run_all_hypothesis_tests, test_single_hypothesis

zones_features = [
    {'type':'bull', 'duration':10, 'price_return':0.02, 'hist_slope':0.3},
    {'type':'bear', 'duration':8,  'price_return':-0.01, 'hist_slope':-0.1},
]

print(run_all_hypothesis_tests(zones_features, alpha=0.05))
print(test_single_hypothesis(zones_features, 'duration'))
```

---

## Hypothesis Testing (Extended)

> **API Stability:** 🟢 MOSTLY STABLE
> 
> **Note:** H4 test uses `correlation_price_hist` field which may be renamed to
> `correlation_price_indicator` during universalization refactoring. All other tests
> are fully stable.

### HypothesisTestSuite

Complete suite of statistical tests for zone analysis.

```python
from bquant.analysis.statistical import HypothesisTestSuite

test_suite = HypothesisTestSuite(alpha=0.05)
```

### Available Tests

#### H1: Zone Duration Hypothesis
Tests whether long zones end with stronger price moves than short zones.

```python
result = test_suite.test_zone_duration_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"Long zones avg return: {result.group1_mean:.3%}")
print(f"Short zones avg return: {result.group2_mean:.3%}")
```

#### H3: Bull-Bear Asymmetry Hypothesis
Tests whether bull and bear zones have different characteristics.

```python
result = test_suite.test_bull_bear_asymmetry_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"Bull duration: {result.group1_mean:.1f}")
print(f"Bear duration: {result.group2_mean:.1f}")
```

#### H4: Correlation-Drawdown Test (New in Phase 3.7)
Tests whether high price-indicator correlation leads to smaller drawdowns.

**Method:** `test_correlation_drawdown_hypothesis(zones_features, alpha=0.05)`

```python
result = test_suite.test_correlation_drawdown_hypothesis(zones_features)
print(f"Significant: {result.significant}")
print(f"High corr avg drawdown: {result.group1_mean:.3%}")
print(f"Low corr avg drawdown: {result.group2_mean:.3%}")
```

**Interpretation:**
- Significant result with group1_mean < group2_mean indicates that zones with high price-indicator correlation experience smaller drawdowns
- Uses t-test to compare drawdown magnitudes between high correlation (>0.7) and low correlation (<0.3) zones

#### ADF: Stationarity Test (New in Phase 3.7)
Tests whether zone durations are stationary over time using Augmented Dickey-Fuller test.

**Method:** `test_zone_duration_stationarity(zones_features, alpha=0.05)`

```python
result = test_suite.test_zone_duration_stationarity(zones_features)
print(f"Stationary: {result.significant}")
print(f"ADF statistic: {result.statistic:.3f}")
print(f"P-value: {result.p_value:.4f}")
```

**Interpretation:**
- **Significant (p < 0.05):** Time series is stationary - no unit root, zone durations stable over time
- **Non-significant (p >= 0.05):** Time series has unit root - non-stationary, durations may drift

**Use cases:**
- Validate that trading strategy parameters are stable across time
- Check if zone duration patterns change over market regimes
- Prerequisite for time-series modeling

#### H5: Support/Resistance Levels Test (New in Phase 3.7)
Tests whether zones starting near support/resistance levels have different durations.

**Method:** `test_support_resistance_hypothesis(zones_features, price_levels=None, tolerance_pct=0.5, alpha=0.05)`

**Features:**
- **Auto-identification:** Automatically finds S/R levels by clustering zone start/end prices
- **Adaptive testing:** Chooses t-test or Mann-Whitney U based on data normality
- **Manual levels:** Can specify custom price levels

```python
# Auto-identification of S/R levels
result = test_suite.test_support_resistance_hypothesis(zones_features)

print(f"Levels identified: {len(result.metadata['price_levels'])}")
print(f"Levels: {result.metadata['price_levels']}")
print(f"Near levels mean: {result.group1_mean:.1f} bars")
print(f"Far from levels mean: {result.group2_mean:.1f} bars")
print(f"Test used: {result.metadata['test_used']}")

# With manual S/R levels
result = test_suite.test_support_resistance_hypothesis(
    zones_features,
    price_levels=[2000.0, 2050.0, 2100.0],
    tolerance_pct=0.5  # 0.5% tolerance
)
```

**Interpretation:**
- Significant result indicates S/R levels affect zone duration
- `group1_mean` vs `group2_mean` shows duration difference
- Can guide trading decisions (enter near S/R levels?)

### Running All Tests

```python
# Run all hypothesis tests at once
all_results = test_suite.run_all_tests(zones_features)

for test_name, result in all_results.items():
    print(f"{test_name}: {'Significant' if result['significant'] else 'Not significant'}")
```

### Running Single Test

```python
# Run specific test by name
result = test_single_hypothesis(zones_features, 'duration')  # or 'asymmetry', 'correlation', 'stationarity', 'support_resistance'
```

---

## Regression Analysis (New in Phase 3.8)

> **API Stability:** 🟢 STABLE - universally applicable

### ZoneRegressionAnalyzer

Predictive modeling for zone characteristics using OLS (Ordinary Least Squares) regression.

```python
from bquant.analysis.statistical import ZoneRegressionAnalyzer

regressor = ZoneRegressionAnalyzer()
```

### Methods

#### predict_zone_duration()

Predicts zone duration based on specified features.

**Parameters:**
- `zones_features`: List of ZoneFeatures or dicts with zone data
- `predictors`: List of feature names to use as predictors
  - Default: `['macd_amplitude', 'hist_amplitude', 'price_range_pct']`
  - Can use any numeric features
- `standardize`: Whether to standardize predictors (default: True)

**Returns:** `RegressionResult` with:
- `r_squared`: Model R² (coefficient of determination)
- `adjusted_r_squared`: Adjusted R² (accounts for number of predictors)
- `coefficients`: Dict mapping predictor names to coefficients
- `p_values`: Dict mapping predictor names to p-values
- `predictions`: Array of predicted values
- `residuals`: Array of residuals (actual - predicted)
- `diagnostics`: Dict with VIF, AIC, BIC, F-statistic, Durbin-Watson

**Example:**
```python
# Predict zone duration
duration_model = regressor.predict_zone_duration(
    zones_features,
    predictors=['macd_amplitude', 'hist_amplitude', 'price_range_pct']
)

print(f"Model R²: {duration_model.r_squared:.3f}")
print(f"Adjusted R²: {duration_model.adjusted_r_squared:.3f}")

# Check coefficients and significance
for predictor, coef in duration_model.coefficients.items():
    p_val = duration_model.p_values[predictor]
    sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
    print(f"  {predictor}: {coef:.4f} ({sig})")

# Check diagnostics
print(f"\nDiagnostics:")
print(f"  AIC: {duration_model.diagnostics['aic']:.1f}")
print(f"  BIC: {duration_model.diagnostics['bic']:.1f}")
print(f"  F-statistic: {duration_model.diagnostics['f_statistic']:.2f}")
print(f"  Durbin-Watson: {duration_model.diagnostics['durbin_watson']:.2f}")

# VIF for multicollinearity
for predictor, vif in duration_model.diagnostics['vif'].items():
    warning = " (HIGH!)" if vif > 10 else ""
    print(f"  VIF {predictor}: {vif:.2f}{warning}")
```

#### predict_price_return()

Predicts price return based on specified features. Same signature as `predict_zone_duration()`.

**Example:**
```python
# Predict price return
return_model = regressor.predict_price_return(
    zones_features,
    predictors=['duration', 'macd_amplitude', 'num_peaks', 'volatility_score']
)

print(f"Return model R²: {return_model.r_squared:.3f}")
print(f"Coefficients: {return_model.coefficients}")
```

### Diagnostics Interpretation

#### R² (R-squared)
- **R² > 0.7:** Strong model
- **0.3 < R² < 0.7:** Moderate model
- **R² < 0.3:** Weak model

#### VIF (Variance Inflation Factor)
- **VIF < 5:** Low multicollinearity
- **5 < VIF < 10:** Moderate multicollinearity
- **VIF > 10:** High multicollinearity - consider removing predictor

#### Durbin-Watson
- **~2.0:** No autocorrelation (good)
- **<1.5 or >2.5:** Potential autocorrelation issue

#### AIC/BIC (Information Criteria)
- Lower is better
- Use for model comparison (lower AIC/BIC = better model)

### Custom Predictors

```python
# Use any available features as predictors
custom_model = regressor.predict_zone_duration(
    zones_features,
    predictors=[
        'duration',              # from base features
        'num_swings',            # from swing metrics
        'hist_skewness',         # from shape metrics
        'volatility_score',      # from volatility metrics
        'divergence_strength'    # from divergence metrics
    ]
)
```

---

## Model Validation (New in Phase 3.8)

> **API Stability:** 🟢 STABLE - universally applicable

### ValidationSuite

Comprehensive model validation tools for assessing robustness and stability.

```python
from bquant.analysis.validation import ValidationSuite

validator = ValidationSuite()
```

### Validation Methods

#### out_of_sample_test()

Traditional train/test split validation.

**Parameters:**
- `zones_features`: List of zone features
- `test_size`: Proportion of data for testing (default: 0.3)
- `metrics`: List of metrics to predict (default: ['duration', 'price_return'])
- `predictors`: List of features to use as predictors (auto-selected if None)

**Returns:** `ValidationResult` with:
- `success`: bool
- `metrics`: Dict with train_r2, test_r2, degradation_pct for each metric
- `metadata`: Additional info

**Example:**
```python
result = validator.out_of_sample_test(
    zones_features,
    test_size=0.3,
    metrics=['duration', 'price_return']
)

print(f"Duration:")
print(f"  Train R²: {result.metrics['duration_train_r2']:.3f}")
print(f"  Test R²: {result.metrics['duration_test_r2']:.3f}")
print(f"  Degradation: {result.metrics['duration_degradation_pct']:.1f}%")

print(f"\nPrice Return:")
print(f"  Train R²: {result.metrics['price_return_train_r2']:.3f}")
print(f"  Test R²: {result.metrics['price_return_test_r2']:.3f}")
```

**Interpretation:**
- **Degradation < 10%:** Model generalizes well
- **Degradation > 30%:** Overfitting likely

#### walk_forward_test()

Rolling window validation simulating real trading conditions.

**Parameters:**
- `zones_features`: List of zone features
- `window_size`: Size of training window (default: 50)
- `step_size`: Step size for rolling (default: 10)
- `metrics`: Metrics to predict (default: ['duration'])
- `predictors`: Predictors to use (auto-selected if None)

**Returns:** `ValidationResult` with mean_r2, std_r2, stability_score per metric

**Example:**
```python
result = validator.walk_forward_test(
    zones_features,
    window_size=50,
    step_size=10,
    metrics=['duration']
)

print(f"Walk-Forward Results:")
print(f"  Mean R²: {result.metrics['duration_mean_r2']:.3f}")
print(f"  Std R²: {result.metrics['duration_std_r2']:.3f}")
print(f"  Min R²: {result.metrics['duration_min_r2']:.3f}")
print(f"  Max R²: {result.metrics['duration_max_r2']:.3f}")
print(f"  Stability score: {result.metrics['duration_stability_score']:.3f}")
```

**Interpretation:**
- **Stability score > 0.8:** Very stable model
- **Stability score > 0.6:** Acceptably stable
- **Stability score < 0.4:** Unstable, sensitive to data window

#### sensitivity_analysis()

Tests model stability across different parameter combinations.

**Parameters:**
- `zones_features`: List of zone features
- `param_grid`: Dict of parameter lists to test
  - Example: `{'min_duration': [2, 5, 10], 'min_amplitude': [0.001, 0.005]}`
- `metric`: Metric to analyze (default: 'duration')
- `predictors`: Predictors to use (auto-selected if None)

**Returns:** `ValidationResult` with stability_score, best_params, param_importance

**Example:**
```python
result = validator.sensitivity_analysis(
    zones_features,
    param_grid={
        'min_duration': [2, 5, 10],
        'min_amplitude': [0.001, 0.005, 0.01]
    },
    metric='duration'
)

print(f"Stability score: {result.metrics['stability_score']:.3f}")
print(f"R² range: {result.metrics['r2_min']:.3f} to {result.metrics['r2_max']:.3f}")
print(f"Best params: {result.metadata['best_params']}")

# Parameter importance
for param, importance in result.metrics['param_importance'].items():
    print(f"  {param} impact: {importance:.3f}")
```

**Interpretation:**
- **Stability > 0.8:** Model robust to parameter changes
- **Stability < 0.5:** Model highly sensitive to parameters

#### monte_carlo_test()

Compares real data performance with synthetic (shuffled) data to detect overfitting.

**Parameters:**
- `zones_features`: List of zone features
- `n_simulations`: Number of synthetic datasets (default: 100)
- `shuffle_method`: Method to generate synthetic data (default: 'bootstrap')
  - 'bootstrap': Resample with replacement
  - 'permutation': Shuffle values
  - 'block': Block shuffling (preserves local structure)
- `metric`: Metric to test (default: 'duration')
- `predictors`: Predictors to use (auto-selected if None)

**Returns:** `ValidationResult` with real_mean, synthetic_mean, p_value

**Example:**
```python
result = validator.monte_carlo_test(
    zones_features,
    n_simulations=100,
    shuffle_method='bootstrap',
    metric='duration'
)

print(f"Real model R²: {result.metrics['real_mean']:.3f}")
print(f"Synthetic R² (mean): {result.metrics['synthetic_mean']:.3f}")
print(f"Synthetic R² (std): {result.metrics['synthetic_std']:.3f}")
print(f"P-value: {result.metrics['p_value']:.4f}")
print(f"Significant: {result.success}")
```

**Interpretation:**
- **Real > Synthetic + significant:** Model captures real patterns
- **Real ≈ Synthetic:** Model may be overfitted or capturing noise

### Complete Validation Example

```python
# Comprehensive validation workflow
from bquant.analysis.statistical import ZoneRegressionAnalyzer
from bquant.analysis.validation import ValidationSuite

regressor = ZoneRegressionAnalyzer()
validator = ValidationSuite()

# 1. Build model
model = regressor.predict_zone_duration(zones_features)
print(f"Initial R²: {model.r_squared:.3f}")

# 2. Out-of-sample validation
oos = validator.out_of_sample_test(zones_features)
print(f"OOS degradation: {oos.metrics['duration_degradation_pct']:.1f}%")

# 3. Walk-forward validation
wf = validator.walk_forward_test(zones_features, window_size=50)
print(f"WF stability: {wf.metrics['duration_stability_score']:.3f}")

# 4. Sensitivity check
sens = validator.sensitivity_analysis(
    zones_features,
    param_grid={'min_duration': [2, 5, 10]}
)
print(f"Parameter sensitivity: {sens.metrics['stability_score']:.3f}")

# 5. Monte Carlo check
mc = validator.monte_carlo_test(zones_features, n_simulations=100)
print(f"Real vs synthetic: {mc.metrics['p_value']:.4f}")

# Final assessment
if (oos.metrics['duration_degradation_pct'] < 20 and
    wf.metrics['duration_stability_score'] > 0.6 and
    sens.metrics['stability_score'] > 0.7 and
    mc.success):
    print("\n✅ Model is robust and production-ready")
else:
    print("\n⚠️ Model needs improvement")
```

---

## См. также

- [База анализа](base.md)
- [Анализ зон](zones.md)
- [Regression Analysis](#regression-analysis-new-in-phase-38) - see above
