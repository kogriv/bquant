# Руководство по стратегиям свингов BQuant

Это руководство описывает расчёт свингов в пайплайне анализа зон: чем отличаются
стратегии ZigZag, FindPeaks и PivotPoints, как выбирать их параметры через пресеты
и адаптивные пороги, и как читать полученные метрики.

Весь API ниже сверен с кодом (`bquant/analysis/zones/`).

## 🧭 Как выбрать стратегию

| Стратегия | Ключевая идея | Когда использовать | Параметры (значения по умолчанию) |
| --- | --- | --- | --- |
| `zigzag` | Фильтрация движений по процентному порогу отклонения | Тренды средней и большой длительности, волновые паттерны | `legs=10`, `deviation=0.05` |
| `find_peaks` | Поиск локальных экстремумов по проминенции | Резкие импульсы, волатильные активы, все локальные экстремумы | `prominence` (авто, если `None`), `distance=5`, `min_amplitude_pct` |
| `pivot_points` | Классический N-барный пивот (high/low среди N баров слева/справа) | Классический технический анализ, подтверждённые уровни | `left_bars=2`, `right_bars=2`, `min_amplitude_pct` |

> 💡 **Совет:** начните с `zigzag`. Глобальный режим (`swing_scope='global'`) включён
> **по умолчанию** — свинги считаются один раз по всему датасету и агрегируются в каждую
> зону. Для подробного разбора покрытия стратегий см.
> [сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md).

## ⚙️ Базовая конфигурация

Стратегия выбирается методом `.with_strategies(swing=...)` fluent-билдера:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data("tv_xauusd_1h").set_index("time")

result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_col="macd_hist")
    .with_strategies(swing="zigzag")
    .analyze(clustering=False)
    .build()
)
```

Свинг-метрики зоны доступны в `zone.features["metadata"]["swing_metrics"]`:

```python
bull_zones = [zone for zone in result.zones if zone.type == "bull"]
print(bull_zones[0].features["metadata"]["swing_metrics"])
```

Сами точки свингов зоны возвращает `zone.get_zone_swings()` (без аргументов — точки
берутся из привязанного к зоне `SwingContext`; при отсутствии контекста вернётся `[]`):

```python
for zone in result.zones:
    swings = zone.get_zone_swings()
    print(zone.zone_id, len(swings))
```

## 🎚️ Пресеты параметров

`bquant.core.config.SWING_PRESETS` содержит согласованные наборы параметров сразу для
всех трёх стратегий. Применить пресет ко всему пайплайну — `.with_swing_preset(name)`.
Доступные пресеты: **`default`** и **`narrow_zone`**.

```python
result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_col="macd_hist")
    .with_strategies(swing="zigzag")
    .with_swing_preset("narrow_zone")
    .analyze(clustering=False)
    .build()
)
```

Пресет `narrow_zone` ужимает ZigZag (`legs=3`, `deviation=0.008`) и сопутствующие пороги,
чтобы узкие диапазоны регистрировали пивоты; `default` — базовый набор (`legs=10`,
`deviation=0.05`).

## 📐 Адаптивные пороги

Для инструментов с широким ценовым диапазоном включите адаптивные пороги — они
пересчитывают `deviation`/`prominence` на основе диапазона зоны. Fluent-билдер
предоставляет `.with_auto_swing_thresholds(True)`; низкоуровневый флаг конструктора
`ZoneAnalysisPipeline` — `strategy_auto_thresholds`.

```python
result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_col="macd_hist")
    .with_strategies(swing="zigzag")
    .with_auto_swing_thresholds(True)
    .build()
)
```

Или напрямую через `ZoneAnalysisPipeline`:

```python
from bquant.analysis.zones.pipeline import ZoneAnalysisConfig, ZoneAnalysisPipeline

pipeline = ZoneAnalysisPipeline(
    config=my_config,
    enable_cache=False,
    strategy_auto_thresholds=True,
    auto_threshold_base_deviation=0.01,
)
pipeline.with_swing_preset("default")  # опциональная база
result = pipeline.run(df)
```

Адаптивный режим откатывается к параметрам пресета, когда вычисленный диапазон меньше
`auto_threshold_base_deviation`, что обеспечивает стабильность на тонких зонах.

## 🔀 Режим расчёта (scope)

`.with_swing_scope(scope)` управляет тем, как считаются свинги:

- `'global'` (по умолчанию) — один проход по всему датасету, затем агрегация в зоны;
- `'per_zone'` — локальный расчёт внутри каждой зоны (режим совместимости).

```python
.with_strategies(swing="zigzag").with_swing_scope("global")
```

> 📖 Внутренняя механика глобального режима (`_calculate_global_swings`,
> `_inject_swing_context`, фолбэки) — в
> [API: глобальные свинги — пайплайн](../api/analysis/zones/global_swings_pipeline.md).

## 🧪 Контроль качества

- Запускайте smoke-тест пайплайна `tests/integration/test_pipeline_global_swings.py`,
  если меняете параметры по умолчанию.
- Сравнивайте количество свингов и амплитуды между стратегиями на одной зоне.
- Фиксируйте выбранный пресет/параметры рядом с результатами, чтобы прогоны были
  воспроизводимы.

## См. также

- [API: Strategy Pattern](../api/analysis/strategies.md) — протоколы стратегий и полный список метрик `SwingMetrics`.
- [API: глобальные свинги — стратегии](../api/analysis/zones/global_swings_strategies.md) — контракт `calculate_global`/`aggregate_for_zone`.
- [Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md) — покрытие zigzag/find_peaks/pivot_points.
