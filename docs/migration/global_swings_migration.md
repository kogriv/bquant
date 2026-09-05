# Глобальный расчёт свингов — что изменилось и как жить с этим

С 0.0.6 свинги считаются **один раз на всём кадре** и нарезаются по зонам (`global`); режим
`per_zone` — внутри каждой зоны отдельно — остался по явному запросу. Страница для тех, чей
код писался под `per_zone`.

## Почему `global` — умолчание

Замер 2026-09-04 на `tv_xauusd_1h`, пресет `narrow_zone`, 39 бычьих зон
([полный отчёт](../analytics/zones/swing_strategy_comparison_case_study.md)):

| Стратегия | `per_zone` | `global` |
|---|---|---|
| `find_peaks` | 15.4 % зон со свингами | 35.9 % |
| `pivot_points` | 7.7 % | 51.3 % |
| `zigzag` | 56.4 % | 92.3 % |

Пивот, стоящий за границей зоны, в `per_zone` невидим; `global` видит его и потому
находит свинги там, где локальный расчёт не находил ничего. Про **время** режимы ничего
не обещают: два прогона одного дня дали `zigzag` противоположный порядок, разброс между
прогонами больше разницы между режимами.

С G54 (2026-09-04) оба режима считаются **одним детектором**: раньше `per_zone` у `zigzag`
брал перерисовывающий вариант, и сравнение режимов сравнивало алгоритмы. Отказ
глобального расчёта больше не переключает прогон на `per_zone` молча — это `RuntimeError`.

## Что делать

**Ничего**, если код не звал `with_swing_scope`: умолчание уже `global`.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .build()
)

zone = result.zones[5]
print(result.metadata['swing_coverage'])
print(len(zone.get_zone_swings()), zone.features['metadata']['swing_calculation_mode'])
# {'strategy': 'ZigZagSwingStrategy', 'zones': 77, 'zones_with_swings': 70}
# 10 global
```

`zone.get_zone_swings()` отдаёт точки `SwingPoint` внутри зоны **плюс по одной соседней с
каждой стороны** — чтобы амплитуда и длительность крайних движений были настоящими, а не
обрезанными границей. С 0.0.12 контекст свингов переживает `result.save()` в JSON и
Parquet.

Вернуть локальный расчёт — явно:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .with_swing_scope('per_zone')
    .build()
)

print(result.metadata['swing_coverage']['zones_with_swings'], result.zones[5].get_zone_swings())
# 44 []
```

В `per_zone` у зон нет `swing_context`, и `get_zone_swings()` пуст — метрики свингов лежат
в `zone.features['metadata']['swing_metrics']` в обоих режимах.

## Своя свинг-стратегия

`global` требует `calculate_global(full_data)` **и** `aggregate_for_zone(zone, context)`;
стратегия только с `calculate()` работает в `per_zone`. Стратегия с одной половиной
глобального контракта отвергается при сборке (G68). Шаблон —
[руководство по расширению](../api/extension_guide.md).

## Кэш

Кэш зон лежит в `~/.cache/bquant/*.pkl` и версионируется `ZoneAnalysisCache.CACHE_VERSION`:
запись прежней версии не читается, пересчёт происходит сам; чистить руками нужно только
ради места. Ключ включает режим свингов, поэтому `global` и `per_zone` не делят записи.

## Что здесь раньше было и снято

Раздел «Производительность» обещал «≤1.5× времени per_zone на 100k баров» и «≈264 байта на
точку». Первое не измерялось этим репозиторием; второе держит только тест
`tests/unit/test_swing_context_memory.py` — в границах 40–450 байт на точку, а не числом.
Совет «на ≲10 зон локальный режим быстрее» тоже не измерялся.

## См. также

- [Модели свингов](../api/analysis/zones/global_swings_models.md) — `SwingPoint`,
  `SwingContext`, `confirmation_index`
- [Пайплайн глобальных свингов](../api/analysis/zones/global_swings_pipeline.md)
- `examples/zone_analysis_global_swings.py`
