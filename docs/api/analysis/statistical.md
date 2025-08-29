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

## См. также

- [База анализа](base.md)
- [Анализ зон](zones.md)
