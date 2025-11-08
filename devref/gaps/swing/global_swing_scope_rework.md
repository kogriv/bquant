# Глобальный расчёт свингов и последующее сопоставление с зонами

## Краткое описание проблемы

Сейчас пайплайн `ZoneAnalysisPipeline` рассчитывает свинговые метрики отдельно для каждой зоны, передавая стратегиям (Find Peaks, Pivot Points, ZigZag) локальные фреймы `zone.data`. Такой подход приводит к искажению анализа: если границы зоны разрезают более крупный трендовый ход, локальные алгоритмы не видят свинги целиком и возвращают неполные либо пустые метрики. В сравнении с глобальным ZigZag, построенным на всём ряде котировок, результат получается беднее и менее надёжен.

## Архитектурный разбор текущего решения

### 1. Пайплайн анализа зон
```
ZoneAnalysisPipeline.build()
  ├─> _run_without_cache()
  │     ├─> prepare_dataframe()
  │     ├─> detect_zones()
  │     │      └─> ZoneDetector.detect()  # выделение зон на всём диапазоне данных
  │     └─> UniversalZoneAnalyzer(...)
  │             └─> ZoneFeaturesAnalyzer.extract_all_zones_features(zones)
  │                    └─> swing_strategy.calculate(zone.data)
```
* Детектор зон работает на глобальном DataFrame, но на этапе упаковки результатов каждая зона получает собственный срез `df.iloc[start_idx:end_idx+1]`, который складывается в `ZoneInfo.data`.
* `UniversalZoneAnalyzer`/`ZoneFeaturesAnalyzer` видят только локальные данные зоны, потому что `zone.data` передаётся напрямую в свинговую стратегию.

### 2. Стратегии свингов
```
class ZigZagSwingStrategy:
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        pivot_series = ta.zigzag(..., zone_data)
        pivots = _collect_pivots(pivot_series)
        return _calculate_swing_metrics(pivots)
```
* Стратегия полностью изолирована: она строит индикатор, извлекает пивоты и агрегирует метрики, не зная о глобальном контексте.
* Аналогичный паттерн повторяется в `FindPeaksSwingStrategy` и `PivotPointsSwingStrategy`.

### 3. Побочные эффекты
* Зоны, начинающиеся/заканчивающиеся внутри большого движения, теряют внешние пивоты и часто дают `num_swings = 0`.
* Отчёты (например, `research/notebooks/05_case_study_zone_consistency.py`) показывают сильный разброс в покрытии свингами.
* Порог «auto» (`with_auto_swing_thresholds(True)`) пересчитывается на локальном срезе, из-за чего итог ещё больше зависит от ширины зоны.

## Предлагаемое решение: глобальный расчёт и нарезка на зоны

### Общая идея
* Один раз посчитать свинговые пивоты на глобальном DataFrame, затем для каждой зоны извлекать соответствующие точки и агрегировать метрики.
* Сохранить опцию текущего поведения («per-zone»), добавив переключатель конфигурации.

### 1. Предлагаемое расширение конфигурации

В `ZoneAnalysisConfig` добавить поле:
```python
@dataclass
class ZoneAnalysisConfig:
    ...
    swing_scope: Literal["per_zone", "global"] = "per_zone"
```
* Значение участвует в сериализации и кэш-ключах.
* Builder (`ZoneAnalysisPipelineBuilder`) получает метод `.with_swing_scope("global")`.
* Настройки свингов (включая адаптивные пороги) остаются в прежних структурах, чтобы переключение режима не ломало существующие конфигурации.

### 2. Расчёт глобального контекста свингов

В `_run_without_cache` после `prepare_dataframe()` и перед `detect_zones()`:
```python
global_swing_context = None
if config.swing_scope == "global":
    global_swing_context = swing_strategy.build_global(df_prepared)
```
* Новый метод `build_global` должен использовать текущие параметры стратегии (включая авто-порог).
* Контекст строится тем же классом стратегии, который задействован в анализаторе, чтобы исключить дублирование логики.
* Возвращаемая структура (`GlobalSwingContext`) содержит:
  * исходные параметры;
  * список пивотов `(index, price, direction)`;
  * быстрые индексы для поиска пивотов по диапазону индексов/дат.

### 3. Преобразование стратегий

* В каждой стратегии выделяем чистую функцию, которая из последовательности пивотов строит `SwingMetrics`. Для ZigZag в основу можно взять существующий приватный метод `_calculate_swing_metrics`, сделав его статическим или вынеся в утиль.
* Стратегия должна уметь возвращать сами пивоты (индексы и цены), чтобы ими мог делиться глобальный контекст.
* При отсутствии глобального контекста стратегия продолжает работать в пер-зонном режиме без изменений.

### 4. Интеграция с анализатором зон

* Передача контекста: либо расширить `ZoneInfo` полем `global_swing_context`, либо изменить сигнатуру `extract_all_zones_features`:
```python
def extract_all_zones_features(self, zones: list[ZoneInfo], *, global_swing_context=None):
    for zone in zones:
        if global_swing_context:
            metrics = swing_strategy.calculate_from_pivots(
                global_swing_context.slice(zone.start_idx, zone.end_idx)
            )
        else:
            metrics = swing_strategy.calculate(zone.data)
        zone.metadata["swing_metrics"] = metrics
```
* Метод `slice(start_idx, end_idx)` возвращает пивоты внутри диапазона, захватывая ближайшие точки за границами зоны (см. ниже).

### 5. Нарезка пивотов на зоны

```
Global pivots: P0----P1----P2----P3----P4----P5
Zone A:        |------|          Zone B:          |------|
```
1. Для зоны берётся первый pivot внутри [start_idx, end_idx].
2. Чтобы не обрезать свинг, захватываем pivot слева (если его index < start_idx) и справа (если > end_idx) — так восстанавливается амплитуда.
3. Полученный список передаётся в `calculate_from_pivots`.

Псевдокод `slice`:
```python
def slice(self, start_idx: int, end_idx: int) -> list[Pivot]:
    left = bisect_left(self.indices, start_idx)
    right = bisect_right(self.indices, end_idx)
    pivots = self.pivots[max(0, left-1):min(len(self.pivots), right+1)]
    return pivots
```

Полученный список прокидывается в «агрегирующую» функцию стратегии. Если точек недостаточно, возвращаем пустой результат — поведение совпадает с текущим режимом.

#### Пример для ZigZag
```python
class ZigZagSwingStrategy:
    def build_global(self, df: pd.DataFrame) -> GlobalSwingContext:
        pivot_series = ta.zigzag(..., df)
        pivots = _collect_pivots(pivot_series)
        return GlobalSwingContext(pivots, df.index)

    def calculate_from_pivots(self, pivots: Sequence[Pivot]) -> SwingMetrics:
        return _calculate_swing_metrics(pivots)

    def calculate(self, zone_data: pd.DataFrame, *, scope: str, context: GlobalSwingContext | None = None) -> SwingMetrics:
        if scope == "global" and context:
            sliced = context.slice(zone_data.index[0], zone_data.index[-1])
            return self.calculate_from_pivots(sliced)
        return self.calculate_from_zone_data(zone_data)
```
* `_calculate_swing_metrics` становится статическим методом или функцией-утилитой, чтобы переиспользовать её и в глобальном, и в локальном режимах.
* FindPeaks и PivotPoints получают аналогичные `build_global`/`calculate_from_pivots` реализации, чтобы API стратегий было единообразным.

### 6. Работа с адаптивными порогами

* Обёртка `_AdaptiveSwingStrategy` при `scope="global"` должна вычислять пороги один раз на глобальном `df_prepared`.
* В глобальном контексте сохраняется применённый порог, чтобы повторно использовать его при нарезке.

### Схема нового воркфлоу
```
┌──────────────────────────────────────────────────────────┐
│           ZoneAnalysisPipeline._run_without_cache        │
├──────────────────────────────────────────────────────────┤
│ prepare_dataframe()                                     │
│ if swing_scope == "global":                             │
│     global_ctx = swing_strategy.build_global(df)        │
│ zones = detect_zones(df)                                │
│ for zone in zones:                                      │
│     if swing_scope == "global":                        │
│         pivots = global_ctx.slice(zone.range)           │
│         metrics = swing_strategy.calculate_from_pivots  │
│     else:                                               │
│         metrics = swing_strategy.calculate(zone.data)   │
│     zone.metadata['swing_metrics'] = metrics            │
└──────────────────────────────────────────────────────────┘
```

### 7. Совместимость, кэширование и fallback
* Значение по умолчанию (`"per_zone"`) сохраняет старое поведение.
* Кэширование (`ZoneAnalysisCache`) расширяется полем `swing_scope`, чтобы результаты разных режимов не смешивались.
* Старый API остаётся доступным: если глобальные пивоты построить не удалось (например, нет достаточного количества баров), стратегия автоматически откатывается к локальному расчёту.
* Для FindPeaks/PivotPoints реализуем аналогичные `build_global`/`calculate_from_pivots` методы, чтобы режимы переключались симметрично.

### 8. Тестирование и документация
* Юнит-тест: искусственный ряд, где глобальный ZigZag даёт ≥2 свинга, а локальное вычисление в узких зонах — 0. Проверяем, что новый режим возвращает непустые метрики.
* Интеграционный тест пайплайна — сравнение количества зон со свингами в разных режимах.
* Обновление документации (`docs/analytics/zones/...`) с описанием переключателя и сценариев.

### Риски и меры
* **Границы пивотов**: убедиться, что slicing корректно добавляет соседние pivots, иначе метрики исказятся. Тесты на пограничные случаи.
* **Производительность**: глобальный расчёт выполняется один раз; дополнительная стоимость — лишь фильтрация и агрегация. Для больших наборов стоит профилировать.
* **Расширяемость**: формальный контракт (`build_global` + `calculate_from_pivots`) упрощает добавление новых стратегий и гарантирует единый подход.

## Итог
Введя глобальный расчёт свингов и последующую нарезку пивотов на зоны, мы получим согласованный набор метрик, совпадающий с результатами «глобального» ZigZag, и сохраним возможность fallback-а на текущий режим. Это устраняет искажения анализа, повышает воспроизводимость и закладывает основу для дальнейшего развития свинговых стратегий.
