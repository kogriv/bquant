# bquant.core.performance — Производительность

## Обзор

Инструменты мониторинга и оптимизации: метрики, глобальный монитор, декораторы и контексты, набор оптимизированных индикаторов, бенчмарки.

## Сущности

- `PerformanceMetrics`: структура метрик (время, память, CPU, и т.д.)
- `PerformanceMonitor`:
  - `record(metrics)`, `get_stats(function_name=None)`, `clear_stats(function_name=None)`, `export_stats(file_path=None) -> DataFrame`
- `get_performance_monitor()`
- Декоратор: `@performance_monitor(enable_cpu=True, enable_memory=True)`
- Контекст: `performance_context(name)`
- `OptimizedIndicators`: `sma(prices, period)`, `ema(prices, period)`, `rsi(prices, period=14)`, `macd(prices, fast=12, slow=26, signal=9)`, `bollinger_bands(prices, period=20, std_dev=2)`
- Бенчмаркинг: `benchmark_function(func, *args, iterations=100, **kwargs)`, `compare_implementations(implementations, test_data, iterations=50) -> DataFrame`, `memory_usage_analysis(func, *args, **kwargs)`

## Примеры

Мониторинг функции:
```python
from bquant.core.performance import performance_monitor, get_performance_monitor

@performance_monitor()
def compute():
    import time; time.sleep(0.2)

compute()
print(get_performance_monitor().get_stats())
```

Контекст измерений:
```python
from bquant.core.performance import performance_context

with performance_context("data_processing"):
    process()
```

Оптимизированные индикаторы (NumPy):
```python
import numpy as np
from bquant.core.performance import OptimizedIndicators

prices = np.random.rand(1000)
sma = OptimizedIndicators.sma(prices, 20)
```

Бенчмарк реализаций:
```python
from bquant.core.performance import compare_implementations

impls = {
    'py_impl': lambda arr: sum(arr) / len(arr),
    'np_impl': lambda arr: arr.mean(),
}

import numpy as np
arr = np.random.rand(10_000)
print(compare_implementations(impls, arr, iterations=20))
```
