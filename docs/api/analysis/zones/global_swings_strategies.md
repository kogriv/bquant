# Глобальные свинги: протокол `SwingCalculationStrategy`

> **Узкий справочник.** Эта страница покрывает контракт свинг-стратегий в режиме
> **глобального расчёта** (`calculate_global`/`aggregate_for_zone`). Обзор всех метрик-стратегий
> (swing/shape/divergence/volatility/volume) — в [Strategy Pattern](../strategies.md).

Контракт `SwingCalculationStrategy` и три реализации: ZigZag, FindPeaks, PivotPoints.

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

- `calculate_global()` дважды вызывает `scipy.signal.find_peaks` — по ряду и по его отражению; отдельной `find_troughs` в scipy нет.
- `aggregate_for_zone()` применяет общую вспомогательную функцию `_aggregate_metrics()` для расчёта амплитуд и длительностей.
- Локальный метод `calculate()` продолжает работать для совместимости, но теперь реиспользует глобальную логику.

## PivotPointsSwingStrategy

Файл: `bquant/analysis/zones/strategies/swing/pivot_points.py`

- `calculate_global()` строит пивоты по методике классических pivot points и сохраняет результаты в `SwingContext`.
- `aggregate_for_zone()` повторно использует общую агрегацию, возвращая метрики, даже если в зоне нет внутренних пивотов (в таком случае срабатывает neighbor padding).
- Локальный `calculate()` остаётся в коде для совместимости с прежними пайплайнами.

## Общие рекомендации

- Для пользовательских стратегий реализуйте `calculate_global` и `aggregate_for_zone`, затем зарегистрируйте стратегию через `StrategyRegistry`.
- Если необходимо поддержать только локальный режим, явно документируйте это и бросайте
  `NotImplementedError` в `calculate_global` — пайплайн поймает исключение, запишет
  предупреждение и оставит зоны без глобального контекста.
- Проверьте, что `strategy_params` включают ключевые настройки — это повышает
  трассируемость. Параметры конструкторов, как они называются на самом деле:

  | Стратегия | Параметры |
  |---|---|
  | `ZigZagSwingStrategy` | `legs=10`, `deviation=0.05` |
  | `FindPeaksSwingStrategy` | `prominence=None`, `distance=5`, `min_amplitude_pct=0.02`, `prominence_warmup=200` |
  | `PivotPointsSwingStrategy` | `left_bars=2`, `right_bars=2`, `min_amplitude_pct=0.015` |

  У FindPeaks параметр называется `prominence`, а не `min_prominence`; `prominence=None`
  означает не «без порога», а порог, выводимый из данных и **замороженный** на первых
  `prominence_warmup` барах (G15).

  Обратите внимание: перечисленные значения — умолчания *конструкторов*. Пайплайн по
  умолчанию применяет пресет `narrow_zone`, поэтому в прогоне через `analyze_zones()`
  параметры будут другими — фактические лежат в `zone.swing_context.strategy_params`.

