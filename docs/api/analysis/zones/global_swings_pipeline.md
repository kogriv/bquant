# Глобальные свинги: внутренняя механика пайплайна

> **Узкий справочник.** Эта страница покрывает только шаги `ZoneAnalysisPipeline`,
> относящиеся к **глобальному расчёту свингов** (`swing_scope="global"`). Полный справочник
> публичного builder-API — в [Universal Pipeline](../pipeline.md).

Всё перечисленное ниже — **внутренние** методы пайплайна. Снаружи режим включается
одной строкой билдера, `with_swing_scope`; знать эти шаги нужно при отладке и при
написании своей свинг-стратегии.

## Обзор рабочего процесса

1. `ZoneAnalysisPipeline._prepare_data()` — подготовка данных и вычисление индикаторов.
2. `ZoneAnalysisPipeline._calculate_global_swings()` — (новый шаг) глобальный расчёт свингов, если `swing_scope="global"`.
3. `ZoneAnalysisPipeline._detect_zones()` — детекция зон выбранной стратегией.
4. `ZoneAnalysisPipeline._inject_swing_context()` — (новый шаг) инъекция глобального контекста в каждую зону.
5. `ZoneAnalysisPipeline._analyze_zones()` — извлечение признаков, включая `ZoneFeaturesAnalyzer`.

Диаграмма последовательности:

```
_prepare_data()  ────▶ _calculate_global_swings()
         │                    │
         │                    └──► SwingContext (глобальные точки)
         ▼
 _detect_zones() ──▶ _inject_swing_context(zones, context)
         │
         ▼
 _analyze_zones() ──▶ ZoneAnalysisResult (zones + features + metadata)
```

## `_calculate_global_swings(data: pd.DataFrame) -> SwingContext`

- Вызывается при `config.swing_scope == "global"` (значение по умолчанию).
- Получает подготовленный датафрейм (с индикаторами, ATR и т.п.).
- Находит активную стратегию свингов через `_get_active_swing_strategy()`.
- Требует, чтобы стратегия реализовала метод `calculate_global()` и вернула `SwingContext`.
- Логирует количество найденных точек, что важно для диагностики.
- При любой ошибке выбрасывает исключение, которое перехватывается на уровне `_run_without_cache()` и приводит к фолбэку в `per_zone`.

### Минимальный пример

Режим задаётся билдеру, а не конфигурации: у `ZoneAnalysisConfig` метода
`with_swing_scope` нет — это метод `ZoneAnalysisBuilder`. Готовый контекст доступен
из любой зоны, обращаться к приватному методу для этого не нужно:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .with_swing_scope('global')
    .analyze(clustering=False)
    .build()
)

context = result.zones[0].swing_context
print(len(context.swing_points))
# 402
```

## `_inject_swing_context(zones: List[ZoneInfo], swing_context: SwingContext)`

- Присваивает ссылку на глобальный контекст каждому `ZoneInfo`.
- Не изменяет порядок и не фильтрует зоны.
- Логирует количество обработанных зон (уровень DEBUG).
- После вызова метод `ZoneInfo.get_zone_swings()` возвращает глобальные точки без повторного расчёта.

### Контрольный сценарий

Контекст один на прогон, и все зоны ссылаются на **один и тот же** объект — это и есть
смысл режима: свинги считаются однажды.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .analyze(clustering=False)
    .build()
)

context = result.zones[0].swing_context
print(all(zone.swing_context is context for zone in result.zones))
# True
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

- Если стратегия не поддерживает `calculate_global` или глобальный расчёт падает, пайплайн
  **останавливается** с `RuntimeError`, называющей причину. До 2026-09-04 он логировал
  предупреждение и молча продолжал в `per_zone` — вызывающий просил одну область, получал
  другую, и результат ложился в кэш под ключом глобальной (G54). Нужен `per_zone` —
  просите его явно: `.with_swing_scope('per_zone')`.
- При неуспешном глобальном расчёте (исключение в стратегии) `_run_without_cache()` оставляет зоны без контекста; анализатор признаков автоматически использует локальные данные.
- Фактический режим фиксируется **у каждой зоны**, а не у результата:
  `zone.features['metadata']['swing_calculation_mode']` даёт `'global'` или `'per_zone'`.
  В `ZoneAnalysisResult.metadata` этого ключа нет — там лежат `swing_coverage`,
  `duration_filter`, `zone_types` и прочая сводка по прогону.

