# `bquant.core.performance` — замер производительности

Замер времени, памяти и CPU: декоратор, контекстный менеджер, накопительный монитор и
бенчмарки. Плюс пять индикаторов на NumPy — для сравнения реализаций, а не для анализа.

## Декоратор

```python
from bquant.core.performance import get_performance_monitor, performance_monitor

@performance_monitor
def analyse(values):
    return sum(values)

@performance_monitor(enable_cpu=False, enable_memory=False)
def cheaper(values):
    return max(values)

print(analyse([1, 2, 3]), cheaper([1, 2, 3]))
print(analyse.__name__)
# 6 3
# analyse
```

Обе формы записи равноправны: `@performance_monitor` и `@performance_monitor(...)`.
Флаги передаются **только по имени** — позиционный аргумент может быть лишь
декорируемой функцией, иначе `TypeError` с объяснением.

До 2026-09-01 форма без скобок молча ломала функцию: декоратор получал её в аргумент
`enable_cpu`, и вызов декорированного имени возвращал внутренний `wrapper` вместо
результата. Ни исключения, ни предупреждения — возвращался объект правильного вида. Эта
же форма стояла в `AGENTS.md` как образец (`devref/gaps/core/g43_…`).

## Контекстный менеджер

```python
from bquant.core.performance import get_performance_monitor, performance_context

monitor = get_performance_monitor()
monitor.clear_stats()

with performance_context('загрузка'):
    sum(range(100_000))

print(sorted(monitor.get_stats()))
# ['загрузка']
```

Имя операции задаётся явно, поэтому контекст годится там, где функции нет — блок внутри
скрипта, участок цикла, шаг пайплайна.

## Монитор

```python
from bquant.core.performance import get_performance_monitor, performance_context

monitor = get_performance_monitor()
monitor.clear_stats()

with performance_context('шаг'):
    sum(range(10_000))

stats = monitor.get_stats('шаг')
print(sorted(stats))
print(stats['call_count'])
# ['avg_cpu_percent', 'avg_memory_delta', 'avg_time', 'call_count', 'function_name', 'last_call', 'max_cpu_percent', 'max_memory_delta', 'max_time', 'min_time', 'std_time', 'total_time']
# 1
```

| Метод | Что делает |
|---|---|
| `record(metrics)` | записать измерение вручную |
| `get_stats(function_name=None)` | сводка по одной операции или по всем |
| `clear_stats(function_name=None)` | сбросить |
| `export_stats(file_path=None)` | отдать `DataFrame`, при указанном пути — ещё и записать |

Монитор глобальный: `get_performance_monitor()` возвращает один и тот же экземпляр, и
декоратор с контекстом пишут в него же. Поэтому перед замером его обычно чистят.

## Бенчмарки

```python
import numpy as np

from bquant.core.performance import benchmark_function, compare_implementations

values = np.arange(10_000, dtype=float)

single = benchmark_function(lambda a: a.mean(), values, iterations=20)
print(sorted(single))
# ['avg_time', 'iterations', 'max_time', 'median_time', 'min_time', 'p95_time', 'p99_time', 'std_time', 'total_time']

table = compare_implementations(
    {'python': lambda a: sum(a) / len(a), 'numpy': lambda a: a.mean()},
    values,
    iterations=10,
)
print(list(table['implementation']))
print(bool(table.iloc[0]['speedup'] == 1.0))
# ['numpy', 'python']
# True
```

`compare_implementations()` сортирует по времени, поэтому первая строка — самая быстрая
реализация, и `speedup` в ней равен 1.0; у остальных это отношение к ней.
`memory_usage_analysis(func, *args)` меряет память одного вызова.

## Индикаторы на NumPy

```python
import numpy as np

from bquant.core.performance import OptimizedIndicators

prices = np.arange(100, 200, dtype=float)

sma = OptimizedIndicators.sma(prices, 20)
print(np.isnan(sma[:19]).all(), round(float(sma[-1]), 1))
print(round(float(OptimizedIndicators.rsi(prices, 14)[-1]), 1))
# True 189.5
# 100.0
```

| Метод | Возвращает |
|---|---|
| `sma(prices, period)` | массив; первые `period-1` значений — `NaN` |
| `ema(prices, period)` | массив; совпадает с `ewm(span=period, adjust=False)` |
| `rsi(prices, period=14)` | массив; первые `period` значений — `NaN` |
| `macd(prices, fast=12, slow=26, signal=9)` | кортеж `(line, signal, hist)` |
| `bollinger_bands(prices, period=20, std_dev=2.0)` | кортеж `(upper, middle, lower)` |

**Это не замена `bquant.indicators`.** Здесь пять функций над `np.ndarray` без ролей,
схемы колонок и связи с пайплайном зон; они существуют, чтобы было с чем сравнивать
скорость. Для анализа нужен [индикатор](../indicators/README.md), а не массив.

Три свойства, которые стоит знать:

* **Окно хвостовое.** Значение в точке `i` считается по `prices[i-period+1 : i+1]` и в
  будущее не заглядывает. До 2026-09-01 `sma` строилась через центрированную свёртку с
  дополнением нулями: индикатор смотрел вперёд, а последние `period//2` значений
  усреднялись с нулями и падали почти вдвое — 1597 на ряде около 2900
  (`devref/gaps/core/g44_…`). `bollinger_bands` брала оттуда среднюю линию.
* **Прогрев — это `NaN`, а не досчёт по неполному окну.**
* **У RSI края шкалы настоящие.** Ряд без падений даёт 100, ряд без ростов — 0, ряд без
  движения вовсе — `NaN`: величина не определена, и ноль здесь был бы выдумкой. Раньше
  все три случая давали 0, то есть отметку предельной перепроданности.

Результаты кэшируются на час (память и диск), и **версия пакета входит в ключ** — иначе
после обновления ещё час отдавались бы числа, посчитанные прежним кодом.

## Дальше

| | |
|---|---|
| [Логирование](logging.md) | `log_performance` — лёгкий замер без счётчиков |
| [Индикаторы](../indicators/README.md) | настоящие индикаторы, с ролями и схемой |
| [Кэширование](../../user_guide/caching.md) | кэш анализа зон |
