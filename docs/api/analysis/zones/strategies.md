# bquant.analysis.zones.strategies — Стратегии свингов

Раздел описывает контракт `SwingCalculationStrategy` и обновлённые реализации ZigZag, FindPeaks и PivotPoints после перехода на глобальный расчёт свингов.

## Протокол `SwingCalculationStrategy`

Все стратегии должны соответствовать протоколу `SwingCalculationStrategy` (см. `bquant/analysis/zones/strategies/base.py`). Ключевые методы:

### `calculate_global(full_data: pd.DataFrame) -> SwingContext`

- Выполняет единичный проход по подготовленному датафрейму и возвращает `SwingContext`.
- Должен логировать основные параметры стратегии (делается внутри реализации стратегии).
- Используется пайплайном в режиме `swing_scope="global"`.

### `aggregate_for_zone(zone: ZoneInfo, context: SwingContext) -> SwingMetrics`

- Преобразует глобальные точки свинга в метрики конкретной зоны.
- Работает с neighbor-aware срезом из `SwingContext.slice()`, чтобы корректно оценивать амплитуды.
- Обязан возвращать `SwingMetrics` с заполненными метаданными (`strategy_name`, `strategy_params`).

### `calculate(zone_data: pd.DataFrame) -> SwingMetrics`

- Сохраняет совместимость со старым режимом `per_zone`.
- Может вызывать `aggregate_for_zone`, создавая временный `SwingContext` (как делает ZigZag/FindPeaks/PivotPoints).

### `get_metadata()` и `config_hash()`

- Методы остаются без изменений: используются пайплайном и кэшем.

## ZigZagSwingStrategy

Файл: `bquant/analysis/zones/strategies/swing/zigzag.py`

- `calculate_global()` запускает ZigZag на полном наборе данных, формирует список `SwingPoint` и собирает `SwingContext`.
- `aggregate_for_zone()` срезает точки через `context.slice()` и вычисляет метрики (количество свингов, амплитуды, симметрию и т.д.).
- При отсутствии глобального контекста `calculate()` переходит к локальному расчёту, сохраняя поведение прошлых версий.

## FindPeaksSwingStrategy

Файл: `bquant/analysis/zones/strategies/swing/find_peaks.py`

- `calculate_global()` использует `scipy.signal.find_peaks`/`find_troughs` и формирует `SwingContext`.
- `aggregate_for_zone()` применяет общую вспомогательную функцию `_aggregate_metrics()` для расчёта амплитуд и длительностей.
- Локальный метод `calculate()` продолжает работать для совместимости, но теперь реиспользует глобальную логику.

## PivotPointsSwingStrategy

Файл: `bquant/analysis/zones/strategies/swing/pivot_points.py`

- `calculate_global()` строит пивоты по методике классических pivot points и сохраняет результаты в `SwingContext`.
- `aggregate_for_zone()` повторно использует общую агрегацию, возвращая метрики, даже если в зоне нет внутренних пивотов (в таком случае срабатывает neighbor padding).
- Локальный `calculate()` остаётся в коде для совместимости с прежними пайплайнами.

## Общие рекомендации

- Для пользовательских стратегий реализуйте `calculate_global` и `aggregate_for_zone`, затем зарегистрируйте стратегию через `StrategyRegistry`.
- Если необходимо поддержать только локальный режим, явно документируйте это и бросайте `NotImplementedError` в `calculate_global` — пайплайн отработает фолбэком.
- Проверьте, что `strategy_params` включают ключевые настройки (например, `deviation` для ZigZag или `min_prominence` для FindPeaks) — это повышает трассируемость.

Такая унификация интерфейса упрощает расширение набора стратегий и делает результаты свингов сопоставимыми между зонами.
