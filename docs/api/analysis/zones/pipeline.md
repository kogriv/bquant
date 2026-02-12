# bquant.analysis.zones.pipeline — Пайплайн анализа зон v2.1

Этот документ фиксирует ключевые изменения API, связанные с глобальным расчётом свингов. Все описания приведены на русском языке в соответствии с требованиями плана 6.2.2.

## Обзор рабочего процесса

1. `ZoneAnalysisPipeline._prepare_data()` — подготовка данных и вычисление индикаторов.
2. `ZoneAnalysisPipeline._calculate_global_swings()` — (новый шаг) глобальный расчёт свингов, если `swing_scope="global"`.
3. `ZoneAnalysisPipeline._detect_zones()` — детекция зон выбранной стратегией.
4. `ZoneAnalysisPipeline._inject_swing_context()` — (новый шаг) инъекция глобального контекста в каждую зону.
5. `ZoneAnalysisPipeline._analyze_zones()` — извлечение признаков, включая `ZoneFeaturesAnalyzer`.

Диаграмма последовательности:

```
prepare_dataframe() ──▶ _calculate_global_swings()
         │                    │
         │                    └──► SwingContext (глобальные точки)
         ▼
 detect_zones() ──▶ _inject_swing_context(zones, context)
         │
         ▼
 analyze_zones() ──▶ ZoneAnalysisResult (zones + features + metadata)
```

## `_calculate_global_swings(data: pd.DataFrame) -> SwingContext`

- Вызывается при `config.swing_scope == "global"` (значение по умолчанию).
- Получает подготовленный датафрейм (с индикаторами, ATR и т.п.).
- Находит активную стратегию свингов через `_get_active_swing_strategy()`.
- Требует, чтобы стратегия реализовала метод `calculate_global()` и вернула `SwingContext`.
- Логирует количество найденных точек, что важно для диагностики.
- При любой ошибке выбрасывает исключение, которое перехватывается на уровне `_run_without_cache()` и приводит к фолбэку в `per_zone`.

### Минимальный пример

```python
pipeline = ZoneAnalysisPipeline(config.with_swing_scope("global"), analyzer)
context = pipeline._calculate_global_swings(prepared_df)
print(len(context.swing_points))
```

## `_inject_swing_context(zones: List[ZoneInfo], swing_context: SwingContext)`

- Присваивает ссылку на глобальный контекст каждому `ZoneInfo`.
- Не изменяет порядок и не фильтрует зоны.
- Логирует количество обработанных зон (уровень DEBUG).
- После вызова метод `ZoneInfo.get_zone_swings()` возвращает глобальные точки без повторного расчёта.

### Контрольный сценарий

```python
zones = pipeline._detect_zones(prepared_df)
pipeline._inject_swing_context(zones, context)
assert all(zone.swing_context is context for zone in zones)
```

## `ZoneAnalysisBuilder.with_swing_scope(scope: Literal["per_zone", "global"])`

- Fluent-метод билдера, который управляет режимом расчёта свингов.
- Допустимые значения: `"global"` (по умолчанию) и `"per_zone"`.
- Хранит выбранное значение в `ZoneAnalysisConfig`, которое затем читает пайплайн.
- Если метод не вызвать, используется `global` (по умолчанию).

### Пример использования билдера

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_swing_scope("global")
    .with_strategies(swing="zigzag")
    .analyze()
    .build()
)
```

## Обработка ошибок и фолбэки

- Если стратегия не поддерживает `calculate_global`, пайплайн логирует предупреждение и переключается на `per_zone`.
- При неуспешном глобальном расчёте (исключение в стратегии) `_run_without_cache()` оставляет зоны без контекста; анализатор признаков автоматически использует локальные данные.
- В трассировке `ZoneAnalysisResult.metadata['swing_calculation_mode']` фиксируется фактический режим (глобальный или локальный).

Эти изменения делают работу пайплайна предсказуемой и прозрачной, а также упрощают диагностику при интеграции глобальных свингов в пользовательские сценарии.
