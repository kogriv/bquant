# bquant.analysis.statistical — Статистический анализ

## Обзор

Модуль предоставляет инструменты описательной статистики, проверки нормальности,
корреляционного анализа, тестирования гипотез, регрессионного моделирования и валидации
для данных зон.

## Основные классы и функции

- `StatisticalAnalyzer(config=None)`
  - `descriptive_statistics(series, name='data') -> Dict`
  - `normality_test(series, alpha=None) -> Dict` — `shapiro` (до 5000 точек), `lilliefors` (KS с поправкой на оценённые по выборке параметры), `anderson_darling` с критическим значением **для переданного `alpha`** (доступны 0.15, 0.10, 0.05, 0.025, 0.01; иное — `ValueError`). До 2026-09-05 здесь стоял KS без поправки, принимавший равномерную выборку, и Андерсон всегда по 5 % (G63)
  - `correlation_analysis(x, y, methods=None) -> Dict`
  - `t_test(sample1, sample2=None, mu=0, alternative='two-sided') -> Dict`
  - `analyze(df) -> AnalysisResult`
- Утилиты:
  - `quick_stats(series) -> Dict`
  - `lilliefors_normal(values, simulations=2000, seed=0) -> (statistic, p_value)` — KS-расстояние до нормали с параметрами выборки, p-value методом Монте-Карло (2000 выборок того же размера, сид фиксирован); своя реализация, потому что `statsmodels.stats.diagnostic.lilliefors` падает на scipy 1.18
  - `test_normality(series, alpha=0.05) -> bool` — `True`, если **каждый** выполнившийся тест принял гипотезу; до 2026-09-05 хватало одного из трёх
  - `correlation_matrix(df, method='pearson') -> DataFrame`
- Тестирование гипотез (из `hypothesis_testing`):
  - `HypothesisTestResult`, `HypothesisTestSuite`
  - `run_all_hypothesis_tests(zones_features, alpha=0.05, vocabulary=None) -> Dict`
  - `run_single_hypothesis_test(zones_features, test_type, alpha=0.05, price_levels=None, tolerance_pct=0.5, vocabulary=None) -> HypothesisTestResult`
- Регрессионный анализ:
  - `ZoneRegressionAnalyzer`
- Валидация моделей: `ValidationSuite` — она живёт в соседнем модуле
  `bquant.analysis.validation`, а не здесь

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
        oscillator_slope = float(rng.normal(0.35 if zone_type == 'bull' else -0.30, 0.10))
        line_amplitude = float(rng.normal(1.20, 0.25))
        oscillator_amplitude = float(abs(rng.normal(0.90, 0.20)))
        price_range_pct = float(abs(rng.normal(0.025, 0.010)))
        num_peaks = int(rng.integers(1, 5))
        num_troughs = int(rng.integers(1, 5))
        num_swings = num_peaks + num_troughs
        hist_skewness = float(rng.normal(0.0, 0.4))
        volatility_score = float(rng.normal(0.6, 0.15))
        divergence_strength = float(rng.normal(0.5, 0.2))
        correlation_price_oscillator = float(rng.uniform(-0.2, 0.95))
        price_return_atr = float(abs(price_return) + rng.uniform(0.004, 0.020))
        atr = float(rng.uniform(0.3, 1.5))
        start_price = float(base_price + rng.normal(0, 45) + idx * rng.normal(0.5, 0.3))

        zone = {
            'zone_id': idx,
            'zone_type': zone_type,
            'duration': duration,
            'price_return': price_return,
            'oscillator_slope': oscillator_slope,
            'line_amplitude': line_amplitude,
            'oscillator_amplitude': oscillator_amplitude,
            'price_range_pct': price_range_pct,
            'num_peaks': num_peaks,
            'num_troughs': num_troughs,
            'num_swings': num_swings,
            'hist_skewness': hist_skewness,
            'volatility_score': volatility_score,
            'divergence_strength': divergence_strength,
            'correlation_price_oscillator': correlation_price_oscillator,
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
    indicator = pd.Series(close).rolling(5).mean().bfill()
    duration_proxy = rng.integers(5, 30, periods)

    dates = pd.date_range('2024-01-01', periods=periods, freq='h')
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

> **Три теста требуют объявленного словаря типов зон** (с 2026-08-24):
> `contrast_asymmetry`, `sequence_patterns` и `correlation_drawdown`. Им нужны не
> имена типов, а свойства — **полярность** и **контрастная пара**, — и вывести их
> из имён нельзя: именно это и было дефектом (`test_bull_bear_asymmetry` сравнивал
> `zone_type == 'bull'` с `== 'bear'`, поэтому на любом другом словаре обе выборки
> оказывались пустыми, а сообщение винило объём данных).
>
> Через пайплайн словарь резолвится автоматически — из стратегии детекции, имя
> которой зоны несут в `indicator_context`. При прямом вызове по словарям признаков
> его нужно передать явно; без него эти три теста **откажутся считать** и назовут
> причину — отсутствие объявления, а не нехватку данных. Отказ намеренный: угадать
> полярность по имени значило бы вернуть снятый хардкод.

Словарь получают из зон — а если зон под рукой нет, из имени стратегии детекции:

```python
from bquant.analysis.zones.detection import resolve_vocabulary


class ZoneLike:
    """Минимум, который нужен резолверу: имя стратегии в контексте зоны."""
    indicator_context = {'detection_strategy': 'zero_crossing'}


vocabulary = resolve_vocabulary([ZoneLike()])

print(vocabulary.names())            # ['bull', 'bear']
print(vocabulary.contrast_pairs())   # [('bear', 'bull')]
print(vocabulary.polarity_of('bull'))  # 1
```

В обычном коде вместо `ZoneLike` стоят настоящие зоны: `resolve_vocabulary(result.zones)`.
Дальше `vocabulary` передаётся в тесты, которым он нужен.

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

#### H3: Гипотеза асимметрии контрастной пары

Сравнивает зоны двух **противоположных** типов — тех, которые объявила стратегия
детекции (`bull`/`bear` у MACD, `overbought`/`oversold` у порогового). Если
объявленных пар несколько, тестируется каждая, а в результат идёт наиболее
значимая; полный список — в `metadata['pairs_tested']`.

```python
result = test_suite.test_contrast_asymmetry_hypothesis(
    zones_features, vocabulary=vocabulary
)
first, second = result.metadata['pair_tested']
print(f"Pair tested: {first} vs {second}, significant: {result.significant}")
print(f"{first} duration: {result.metadata['duration_test'][f'{first}_mean']:.1f}")
print(f"{second} duration: {result.metadata['duration_test'][f'{second}_mean']:.1f}")
```

#### H4: Корреляция и величина экскурсии цены

Какая из двух экскурсий содержательна для зоны, решает её **объявленная
полярность**: у приподнятой — просадка от максимума, у подавленной — отскок от
минимума. Сколько зон каждого типа вошло в выборку, видно в
`metadata['zones_used_by_type']`.

```python
result = test_suite.test_correlation_drawdown_hypothesis(
    zones_features, vocabulary=vocabulary
)
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
full_suite = test_suite.run_all_tests(zones_features, vocabulary=vocabulary)
summary = full_suite.results['summary']
print(f"{summary['tests_executed']} of {summary['total_tests']} tests ran; "
      f"significance rate {summary['significance_rate']:.2f}")
for name, message in summary['failed_tests'].items():
    print(f"  {name} did not run: {message}")
```

Сводка отделяет **выполненные** тесты от **не выполнившихся**:
`significance_rate` считается по знаменателю `tests_executed`, а не `total_tests`.
Тест, который не выполнился, — не незначимый результат, а отсутствие результата;
раньше такие тесты попадали в знаменатель наравне с остальными и разбавляли долю,
ничего не сообщая о пробеле.

## Регрессионный анализ (фаза 3.8)

```python
from bquant.analysis.statistical import ZoneRegressionAnalyzer

regressor = ZoneRegressionAnalyzer()
```

**Регрессия объясняющая, не прогнозная.** Предикторы измерены по всей завершённой зоне —
длительность, просадка от пика (содержит цену конца), число пиков, наклон осциллятора, — а
цель — доходность или длительность той же зоны. R² здесь описывает связь постфактум и не
является свидетельством предсказательной силы; в `metadata` это записано
(`kind: 'in_sample_explanatory'`, `feature_availability: 'ex_post'`), `durbin_watson` считается
явно. До 2026-09-05 методы назывались `predict_*` (G62).

Объясняющая регрессия длительности зоны по умолчанию:

```python
duration_model = regressor.explain_zone_duration(zones_features)
print(f"Model R²: {duration_model.r_squared:.3f}")
print(f"Adjusted R²: {duration_model.adjusted_r_squared:.3f}")
```

Кастомные предикторы длительности:

```python
custom_model = regressor.explain_zone_duration(
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

Объясняющая регрессия доходности зоны:

```python
return_model = regressor.explain_price_return(
    zones_features,
    predictors=['duration', 'line_amplitude', 'correlation_price_oscillator', 'oscillator_slope', 'num_peaks']
)
print(f"Return model R²: {return_model.r_squared:.3f}")
print(f"Coefficients: {return_model.coefficients}")
```

## Валидация моделей (ValidationSuite)

`ValidationSuite` сравнивает **одну метрику** между окнами или с распределением симуляций.
Какую и как — говорит `MetricSpec`:

| Поле | Что задаёт |
|---|---|
| `key` | имя метрики в том, что вернула `analyze_func` (`dict` или `AnalysisResult.results`) |
| `direction` | `'higher_is_better'` — падение на тесте есть деградация, рост нет; `'lower_is_better'` — зеркально; `'stable'` — сдвиг в любую сторону за порог есть провал |
| `per_bar` | делить значение на число баров окна. **Обязательно для счётчиков**: окна 70 % и 30 % содержат разное число чего угодно, и сырой счётчик на них ничего не говорит о процессе |

Умолчания нет: набор не может знать, какое из ваших чисел — качество и в какую сторону.
До 2026-09-04 умолчанием был `total_zones` как есть, и стационарный процесс на разбиении
70/30 читался как «деградация 57 %» (G55).

`degradation_pct` — насколько тест **хуже** обучения в процентах от обучения, в
направлении метрики: положительное — хуже, отрицательное — лучше. Для `'stable'` знак лишь
говорит, куда сдвинулось (положительное — на тесте ниже), вердикт смотрит на модуль.
Нулевое значение на обучении при ненулевом на тесте — отказ (`AnalysisError`): процента
от нуля не существует, а «0 %» здесь означало бы «стабильно» при любом тесте.

```python
import numpy as np
import pandas as pd

from bquant.analysis import AnalysisResult
from bquant.analysis.validation import MetricSpec, ValidationSuite

rng = np.random.default_rng(7)
periods = 720
close = 2000 + np.cumsum(rng.normal(0, 3, periods))
market_data = pd.DataFrame({'close': close},
                           index=pd.date_range('2024-01-01', periods=periods, freq='h'))


def analyze_for_validation(data, min_amplitude: float = 0.0015):
    returns = data['close'].pct_change().dropna()
    events = int((returns.abs() > min_amplitude).sum())
    return AnalysisResult(
        analysis_type='statistical_validation',
        results={
            'events': float(events),
            'avg_abs_return': float(returns.abs().mean()),
        },
        data_size=len(data),
    )


validator = ValidationSuite(degradation_threshold=0.25)
event_rate = MetricSpec('events', direction='stable', per_bar=True)

oos = validator.out_of_sample_test(
    analyze_for_validation, market_data, event_rate, train_ratio=0.7
)
print(oos.metadata['train_size'], oos.metadata['test_size'])
print(round(oos.metadata['train_value'], 3), round(oos.metadata['test_value'], 3))
print(round(oos.degradation_pct, 1), oos.success)
# 503 217
# 0.342 0.318
# 7.0 True
```

Сырые значения метрики лежат в `train_metrics`/`test_metrics` как их вернула функция;
то, что сравнивалось (после нормировки), — в `metadata['train_value']`/`['test_value']`
вместе с самим `metadata['metric']`.

### Walk-forward

Окна `train_window`/`test_window` разной длины — счётчику нужен `per_bar`.

```python
wf = validator.walk_forward_test(
    analyze_for_validation,
    market_data,
    event_rate,
    train_window=240,
    test_window=120,
    step_size=120,
)
print(wf.metadata['iterations_count'])
print(round(wf.metadata['train_value'], 3), round(wf.metadata['test_value'], 3))
print(round(wf.degradation_pct, 1), wf.success)
# 4
# 0.34 0.35
# -3.1 True
```

### Sensitivity analysis

`direction` решает, какая комбинация «лучшая»; для `'stable'` лучшей и худшей нет
(`best_params`/`worst_params` — `None`), только разброс. `stability_score` — единица минус
коэффициент вариации; успех при > 0.8.

```python
sensitivity = validator.sensitivity_analysis(
    analyze_for_validation,
    market_data,
    param_ranges={'min_amplitude': [0.001, 0.0015, 0.002]},
    metric=MetricSpec('events', direction='higher_is_better'),
)
print(round(sensitivity.metadata['stability_score'], 2), sensitivity.success)
print(sensitivity.metadata['best_params'], sensitivity.metadata['worst_params'])
# 0.62 False
# {'min_amplitude': 0.001} {'min_amplitude': 0.002}
```

Число событий закономерно зависит от порога — и набор так и говорит: разброс между
комбинациями велик, стабильности нет.

### Monte Carlo

Где должно оказаться реальное значение относительно симуляций, тоже решает `direction`:
`'higher_is_better'` — выше p95, `'lower_is_better'` — ниже p05, `'stable'` — вне
центральных 95 % (вопрос тогда только «отличимо ли от случайного»). `percentile_rank` — ранг
реального значения в распределении симуляций, 0–100 (средний ранг при совпадениях).

```python
monte_carlo = validator.monte_carlo_test(
    analyze_for_validation,
    market_data,
    MetricSpec('avg_abs_return', direction='higher_is_better'),
    n_simulations=40,
    shuffle_method='returns',
)
print(round(monte_carlo.metadata['real_value'], 5), round(monte_carlo.metadata['sim_mean'], 5))
print(round(monte_carlo.metadata['percentile_rank'], 1), monte_carlo.metadata['success_rule'])
print(monte_carlo.success)
# 0.0012 0.0012
# 47.5 real > p95 of simulations
# False
```

Здесь отказ — правильный ответ: `shuffle_method='returns'` переставляет доходности, а
средний модуль доходности от перестановки не меняется. Метрика, которую симуляция не может
сдвинуть, ничего и не проверяет — выбирайте ту, что зависит от порядка баров.

### В пайплайне

`.analyze(validation=True)` у `analyze_zones(...)` запускает out-of-sample проверку
настроенной детекции: кадр делится 70/30, детекция прогоняется на каждой части, и частота зон
на бар (`MetricSpec('total_zones', 'stable', per_bar=True)`) обязана удержаться в пороге
набора. Итог — в `result.validation_results['out_of_sample']` и
`result.metadata['validation']`; см. [пайплайн](pipeline.md#analyzeclustering-true-n_clusters-3-regression-false-validation-false-min_duration-1).
Свой порог — через `UniversalZoneAnalyzer(validation_suite=ValidationSuite(0.1))`; свою
метрику или другой метод — вызовом набора вручную, как выше.

---

## См. также

- [База анализа](base.md)
- [Анализ зон](zones.md)
- [Регрессионный анализ](#регрессионный-анализ-фаза-38)
