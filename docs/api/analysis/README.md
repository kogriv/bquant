# Analysis — аналитические модули

Что лежит в `bquant.analysis` и как это связано между собой.

| Модуль | Предмет | Страница |
|---|---|---|
| `bquant.analysis.zones` | зоны: детекция, признаки, последовательности, пайплайн | [зоны](zones.md) · [пайплайн](pipeline.md) |
| `bquant.analysis.zones.strategies` | метрики зон пятью семействами | [стратегии](strategies.md) |
| `bquant.analysis.statistical` | гипотезы, распределения, регрессия | [статистика](statistical.md) |
| `bquant.analysis` | `BaseAnalyzer`, `AnalysisResult`, реестр видов анализа | [база](base.md) |
| `bquant.analysis.validation` | проверка устойчивости моделей | ниже |

## Зоны

Основной вход — `analyze_zones()`; полный справочник билдера в
[пайплайне](pipeline.md), практика — в [руководстве](../../user_guide/zone_analysis.md).

Живые компоненты, на которых пайплайн собран: `ZoneFeaturesAnalyzer` (признаки зоны) и
`ZoneSequenceAnalyzer` (переходы между зонами и кластеризация). Раньше оба были помечены
здесь как deprecated — это было неверно: пайплайн вызывает их напрямую, и они показаны в
актуальных примерах.

### Две модели зоны — разные предметы, а не версии

| | `ZoneInfo` | `PriceLevelZone` |
|---|---|---|
| что описывает | участок **времени**, где осциллятор в одном состоянии | полосу **цены**: поддержку, сопротивление |
| границы | в барах | в цене |
| покрытие | зоны идут встык, мощение полное | полосы могут перекрываться и покрывают не всю историю |
| вход | `analyze_zones()` | `find_support_resistance()`, `PriceLevelAnalyzer` |

Общего у них только слово «зона». Раньше оно стирало различие, и одна модель числилась
устаревшей версией другой — разбор в
`../../../devref/gaps/zone_types/g28_one_word_two_concepts_2026-08.md`.

### Глобальные свинги

- [Модели](zones/global_swings_models.md) — `SwingPoint`, `SwingContext`, поля `ZoneInfo`
- [Пайплайн](zones/global_swings_pipeline.md) — расчёт на всём кадре и нарезка по зонам
- [Стратегии](zones/global_swings_strategies.md) — контракт `calculate_global` / `aggregate_for_zone`

## Стратегии метрик

Пять семейств, семь зарегистрированных реализаций. Список берите у реестра, а не отсюда —
он не устаревает:

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

for family in ('swing', 'shape', 'divergence', 'volatility', 'volume'):
    lister = getattr(StrategyRegistry, f'list_{family}_strategies')
    print(f"{family}: {lister()}")
# swing: ['zigzag', 'find_peaks', 'pivot_points']
# shape: ['statistical']
# divergence: ['classic']
# volatility: ['combined']
# volume: ['standard']
```

Сколько метрик даёт каждое семейство — тоже вопрос к коду:

```python
import dataclasses

from bquant.analysis.zones.strategies import base

for name in ('SwingMetrics', 'ShapeMetrics', 'DivergenceMetrics',
             'VolatilityMetrics', 'VolumeMetrics'):
    fields = [f.name for f in dataclasses.fields(getattr(base, name))
              if f.name not in ('strategy_name', 'strategy_params')]
    print(f"{name}: {len(fields)}")
# SwingMetrics: 23
# ShapeMetrics: 3
# DivergenceMetrics: 4
# VolatilityMetrics: 10
# VolumeMetrics: 4
```

Инфраструктура вокруг них: `StrategyRegistry` — регистрация и поиск по имени, протоколы —
контракт, который обязана выполнить своя реализация, dataclass-ы — форма результата.
Как добавить свою — [Extension Guide](../extension_guide.md).

## Статистика

- `HypothesisTestSuite` — набор проверок гипотез о зонах; тест, которому не хватило
  данных или словаря типов, возвращает `error` **с причиной**, а не правдоподобное число;
- `ZoneRegressionAnalyzer` — OLS для длительности и доходности зоны, с диагностикой;
- `StatisticalAnalyzer` — общие статистики;
- `run_all_hypothesis_tests()` — прогнать всё разом.

Подробности и разбор отказов — [статистика](statistical.md).

## Валидация

`bquant.analysis.validation.ValidationSuite` — четыре метода проверки устойчивости:
`out_of_sample_test`, `walk_forward_test`, `sensitivity_analysis`, `monte_carlo_test`.
Включается через `.analyze(validation=True)` и требует больше 20 зон.

## Модули-заглушки — что это и как их отличить

Четыре подмодуля — `bquant.analysis.candlestick`, `.chart`, `.technical`,
`.timeseries` — сейчас **разметка под будущую работу**, а не рабочие анализаторы:
`CandlestickAnalyzer`, `ChartAnalyzer`, `TechnicalAnalyzer`, `TimeseriesAnalyzer`.

Они не притворяются: `analyze()` отрабатывает без ошибки и возвращает
`AnalysisResult`, в котором прямо сказано, что реализации нет.

```python
import pandas as pd
from bquant.analysis.candlestick import CandlestickAnalyzer

frame = pd.DataFrame({
    'open': [100.0, 101.0], 'high': [101.0, 102.0],
    'low': [99.0, 100.0], 'close': [100.5, 101.5],
})

result = CandlestickAnalyzer().analyze(frame)

print(CandlestickAnalyzer.is_stub)                      # True
print(result.metadata['implementation_status'])         # stub
print(result.results['status'])                         # stub_implementation
print(result.results['message'])
# Candlestick analysis module is not yet implemented
```

**Отличать их следует по `is_stub`, а не по названию модуля и не по словам в
описании.** Признак объявлен свойством класса (`BaseAnalyzer.is_stub`, по
умолчанию `False`), и на связь маркера с поведением стоит пин в обе стороны:
реализуют анализатор и забудут снять маркер — покраснеет; снимут маркер, не убрав
заглушку, — тоже.

Оттуда же берётся суффикс «(заглушка)» в перечнях `get_*_analyzers()`: он
**выводится** из маркера, а не вписан в строки описаний руками.

```python
from bquant.analysis.technical import get_technical_analyzers

print(get_technical_analyzers()['technical'])
# Технический анализ (заглушка)
```

Планы каждого модуля перечислены в `result.results['planned_features']` и в
докстроке модуля.

## Пример: анализ зон целиком

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .with_strategies(swing='zigzag', shape='statistical', volatility='combined')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(len(result.zones))
print(sorted(result.statistics))
print(len(result.hypothesis_tests.results['tests']))
# 32
# ['additional_metrics', 'duration_distribution', 'line_amplitude_distribution',
#  'oscillator_amplitude_distribution', 'return_distribution', 'total_statistics']
# 7
```

## Дальше

| | |
|---|---|
| [Пайплайн](pipeline.md) | справочник билдера |
| [Зоны](zones.md) | модели, словарь типов, стратегии детекции |
| [Стратегии](strategies.md) | метрики и их параметры |
| [Статистика](statistical.md) | гипотезы, регрессия, отказы |
| [Extension Guide](../extension_guide.md) | своя стратегия или индикатор |
