# Руководство по стратегиям свингов BQuant

Это руководство описывает расчёт свингов в пайплайне анализа зон: чем отличаются
стратегии ZigZag, FindPeaks и PivotPoints, как выбирать их параметры через пресеты
и адаптивные пороги, и как читать полученные метрики.

Весь API ниже сверен с кодом (`bquant/analysis/zones/`).

## Как выбрать стратегию

| Стратегия | Ключевая идея | Когда использовать | Параметры (значения по умолчанию) |
| --- | --- | --- | --- |
| `zigzag` | Фильтрация движений по процентному порогу отклонения | Тренды средней и большой длительности, волновые паттерны | `legs=10`, `deviation=0.05` |
| `find_peaks` | Поиск локальных экстремумов по проминенции | Резкие импульсы, волатильные активы, все локальные экстремумы | `prominence` (авто, если `None`), `distance=5`, `min_amplitude_pct`, `prominence_warmup=200` |
| `pivot_points` | Классический N-барный пивот (high/low среди N баров слева/справа) | Классический технический анализ, подтверждённые уровни | `left_bars=2`, `right_bars=2`, `min_amplitude_pct` |

> 💡 **Совет:** начните с `zigzag`. Глобальный режим (`swing_scope='global'`) включён
> **по умолчанию** — свинги считаются один раз по всему датасету и агрегируются в каждую
> зону. Для подробного разбора покрытия стратегий см.
> [сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md).

## Базовая конфигурация

Стратегия выбирается методом `.with_strategies(swing=...)` fluent-билдера:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data("tv_xauusd_1h")   # время в колонке; пайплайн перенесёт его на индекс сам

result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_role="hist")
    .with_strategies(swing="zigzag")
    .with_swing_preset("narrow_zone")
    .analyze(clustering=False)
    .build()
)

print(len(result.zones))   # 77
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

## Пресеты параметров

`bquant.analysis.zones.strategies.swing.SWING_PRESETS` содержит согласованные наборы параметров сразу для
всех трёх стратегий. Применить пресет ко всему пайплайну — `.with_swing_preset(name)`.
Доступные пресеты: **`narrow_zone`** (по умолчанию) и **`wide_zone`**.

Пресеты названы по ширине зоны, под которую откалиброваны. `narrow_zone` ужимает ZigZag
(`legs=3`, `deviation_pct=0.008`, `confirmation_retrace_pct=0.8`) и сопутствующие пороги,
чтобы узкие диапазоны регистрировали пивоты; `wide_zone` — крупные пороги (`legs=10`,
`deviation_pct=0.05`, `confirmation_retrace_pct=5.0`, `min_amplitude_pct=0.02`) для
инструментов и таймфреймов, где рядовое движение внутри зоны — проценты цены.

### Единицы ZigZag: `deviation_pct` и `confirmation_retrace_pct`

`deviation_pct` — **проценты, ровно так, как читает их pandas-ta**: `0.008` — это 0.008 %,
не 0.8 %. До 0.0.20 поле называлось `deviation` и описывалось как доля («0.05 = 5%»), тогда
как библиотека сравнивает `current_dev > 0.01 * deviation` и печатает единицу в имени
колонки, которую возвращает: `ZIGZAGs_0.008%_3`. Цифры пресетов при переименовании **не
менялись** — это то, что библиотека всегда читала, и именно этот объект измерен в G35/G38/
G48/G54. На значениях пресетов порог лежит ниже размаха одного бара часового золота, и
детектор сводится к экстремумам окна `legs`: рычаг, который решает, — `legs`.

```python
from bquant.analysis.zones.strategies.swing.zigzag import ZigZagSwingStrategy
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

shipped = ZigZagSwingStrategy(legs=3, deviation_pct=0.008, confirmation_retrace_pct=0.8)
print(len(shipped.calculate_global(data).swing_points))   # 402

honest = ZigZagSwingStrategy(legs=3, deviation_pct=0.8, confirmation_retrace_pct=0.8)
print(len(honest.calculate_global(data).swing_points))   # 132
```

«Честные» 0.8 % — не лучший объект, а другой: под `backtest=True` параметр не ограничивает
размер ноги (при 5.0 восемь ходов из десяти на сэмпле меньше 5 %), а больше половины
оставшихся точек становятся обновлениями того же экстремума (61.8 % при 0.8). Разбор —
`devref/gaps/swing/g86_…`.

`confirmation_retrace_pct` — откат от цены пивота, в процентах, после которого пивот
считается причинно подтверждённым (`SwingPoint.confirmation_index`). Это отдельная
величина по необходимости: следующий пивот и есть первый бар, где откат превысил порог
обнаружения, поэтому подтверждение, определённое тем же числом, попадало бы на следующий
пивот по построению (99.2 % пар) и не несло бы информации. Значения пресетов — та доля, за
которую старый код принимал `deviation`; на них проверен причинный контракт (#110, G54).

Что считается ногой: движение строится из **каждой** пары соседних точек, поэтому
обновление (две вершины подряд, вторая выше) — тоже движение. Обновления никогда не
противоречат своему типу; на значениях пресетов их 11–14 % пар.

**Выбор пресета влияет сильнее выбора стратегии.** Доля зон, у которых нашёлся хотя бы
один свинг — 30 зон MACD по линии на `tv_xauusd_1h`, замер прогоном:

| Стратегия | `wide_zone`, `per_zone` | `wide_zone`, `global` | `narrow_zone`, `per_zone` | `narrow_zone`, `global` |
|---|---|---|---|---|
| `zigzag` | 12/30 | 26/30 | 23/30 | **29/30** |
| `find_peaks` | 0/30 | 0/30 | 14/30 | 19/30 |
| `pivot_points` | 0/30 | 2/30 | 10/30 | 23/30 |

Нули в колонках `wide_zone` — не свойство рынка, а свойство порога: `min_amplitude_pct`
там равен 2% цены, тогда как медианный размах зоны на этих данных — 1.2%. Мерка крупнее
измеряемого, и пройти её свинг внутри зоны не может.

**До 0.0.10 этот пресет был умолчанием и назывался `default`** — то есть по умолчанию две
стратегии из трёх не находили ничего. Умолчанием стал `narrow_zone`, а имя `default`
исчезло: оно называло не свойство набора порогов, а его положение в списке, и когда
положение изменилось, имя стало бы враньём.

**Ноль при этом всё равно не сообщал бы о себе сам:** `swing_metrics` с `num_swings: 0`
выглядит ровно так же, как честно измеренное отсутствие движения. Поэтому результат
несёт `metadata['swing_coverage']`, а пустой улов у всех зон пишет предупреждение в лог.
Разбор: `devref/gaps/swing/g35_default_preset_measures_nothing_and_says_nothing_2026-08.md`.

## Авто-проминенция `find_peaks` и прогрев

Если `prominence=None` (по умолчанию), порог выводится из ценового диапазона —
но **только по первым `prominence_warmup` барам** (по умолчанию 200), и дальше
не пересчитывается.

Так сделано ради причинной честности. Раньше порог считался по всему наблюдённому
диапазону, а `high.max()` может только расти и `low.min()` только падать — значит
порог всё время рос. Экстремум, прошедший ранний меньший порог и объявленный
подтверждённым, позже проваливал больший и **исчезал из результата**. Замороженный
порог этого не допускает: усечение серии не меняет первые `N` баров.

Что это означает на практике:

- **Пока баров меньше `prominence_warmup`, `confirmation_index` не выставляется**
  ни у одного свинга — порог ещё не окончателен, обещать доступность нечестно.
  Стратегия пишет об этом предупреждение в лог. Сами свинги при этом детектируются.
- Замороженный порог ниже того, до которого дорастал прежний, поэтому засчитывается
  **немного больше** мелких экстремумов. Пропасть уже найденное он не может.
- **С явным `prominence` прогрев не действует вовсе** — константа не нуждается в
  оценке, и подтверждения не задерживаются.

Настраивайте `prominence_warmup` под длину истории: чем он больше, тем
представительнее оценка волатильности, но тем длиннее «слепое окно» в начале.

```python
from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy

# короткая история — уменьшить прогрев, иначе подтверждений не будет вовсе
strategy = FindPeaksSwingStrategy(distance=3, prominence_warmup=50)

# либо задать порог явно — тогда прогрев не нужен
strategy = FindPeaksSwingStrategy(distance=3, prominence=0.5)
```

## Адаптивные пороги

Адаптивный режим выводит порог из данных у `find_peaks` и `pivot_points` (с G48, 2026-09-06):
`min_amplitude_pct` от **масштаба зоны** — `max(медианный размах бара, медианный размах
зоны × k)`, k = 0.3 и 0.25. В `global` масштаб — все найденные зоны (пайплайн детектирует
их до свингов), в `per_zone` — сама зона. Пол — размах бара, не константа: движение меньше
типичного бара движением не считается.

**С ZigZag режим отказывает.** До 0.0.20 слой «адаптировал» его `deviation` от размаха
кадра — величину, которую pandas-ta читал как проценты ниже размаха одного бара; измерено:
193 свинга без слоя, 192 со слоем (G86). Переключатель, который принимается и ничего не
меняет, — дефект той же породы, что G85, поэтому `with_auto_swing_thresholds(True)` при
активном `zigzag` поднимает `ValueError` и называет, что слой адаптирует на самом деле.
Пороги ZigZag задаются пресетом или руками: `deviation_pct`, `confirmation_retrace_pct`.

Fluent-билдер предоставляет `.with_auto_swing_thresholds(True)` — под ним пайплайн оборачивает
базовую стратегию в `AdaptiveSwingStrategy` (`bquant.analysis.zones.strategies.swing`; до G64
имя было приватным); низкоуровневый флаг
конструктора `ZoneAnalysisPipeline` — `strategy_auto_thresholds`.

На часовом сэмпле режим поднимает `find_peaks` с 28 до 65 зон из 77 и `pivot_points` с 38 до
63; на 15-минутном — с 3 до 67 и 72 из 91, потому что константа пресета 0.006 стоит там выше
размаха типичной зоны (0.0028). Что это доказывает и чего нет — в
[исследовании G48](../analytics/zones/swing_zone_scale_threshold_study.md): пивоты те же
самые (366 = 366), ZigZag подтверждает их на 99–100 %, метрики не вырождаются; полезность
движений в 0.2–0.6 % — свойство задачи, не порога.

> ⚠️ Проминенцию `find_peaks` этот режим **намеренно не трогает**. Она задаётся в единицах
> цены, а не долей, и подстановка сюда относительной величины раньше её обнуляла — фильтр
> переставал фильтровать, и адаптивный режим давал *больше* свингов, чем обычный (G16).
> У `find_peaks` есть собственный адаптивный к диапазону порог — см. раздел про прогрев выше;
> он и работает.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data("tv_xauusd_1h")

result = (
    analyze_zones(df)
    .with_cache(enable=False)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_role="line")
    .with_strategies(swing="find_peaks")
    .with_auto_swing_thresholds(True)
    .analyze()
    .build()
)

params = next(z.features["metadata"]["swing_metrics"]["strategy_params"]
              for z in result.zones
              if z.features["metadata"].get("swing_metrics", {}).get("strategy_params"))
print(sorted(params))   # ['distance', 'min_amplitude_pct', 'prominence']
print(round(params['min_amplitude_pct'], 5))   # 0.00373
```

Порог выведен из данных: пресет `narrow_zone` просит `min_amplitude_pct=0.006`, масштаб зон
на этом кадре дал `0.00373` — ниже пресета, и движения между пивотами, которые пресет
отбрасывал, проходят.

> **В 0.0.10 и раньше этот режим обнулял `find_peaks` и `pivot_points`** — во всех зонах, в обоих
> режимах области. Он поднимал их `min_amplitude_pct` до `0.01` (пол `base_deviation`),
> тогда как пресет `narrow_zone` просит `0.006`, а медианная зона проходит `0.0075`: порог
> стоял выше движения, которое обязан был пропускать. Замер на 77 зонах MACD по
> гистограмме, пресет `narrow_zone`:
>
> | Стратегия | режим выключен | было (0.0.10) | стало (исправлено 2026-09-03, не отгружено) |
> |---|---|---|---|
> | `zigzag` | 90.9 % | 90.9 % | 90.9 % |
> | `find_peaks` | 36.4 % | **0 %** | 36.4 % |
> | `pivot_points` | 49.4 % | **0 %** | 49.4 % |
>
> Слой перестал выставлять `min_amplitude_pct`, и обе стратегии вернулись ровно туда, где
> они с выключенным режимом. Ноль свингов при этом ничем не отличался от «рынок стоял»,
> поэтому опубликованный отчёт девять месяцев читал это как свойство стратегий.
>
> Строка `zigzag` в этой таблице — 90.9 % во всех трёх столбцах — и была уликой G86: слой
> менял его `deviation` с `0.05` на `0.031`, и это не меняло ничего, потому что оба числа
> библиотека читала как сотые доли процента. Два месяца одинаковые числа читались как
> «не задет», а не как «рычаг мёртв». Разбор:
> `devref/gaps/swing/g38_adaptive_thresholds_restore_the_threshold_g35_removed_2026-08.md`,
> `devref/gaps/swing/g86_…`.

Низкоуровневый флаг конструктора `ZoneAnalysisPipeline` — `strategy_auto_thresholds`; база
отката `auto_threshold_base_deviation` удалена в 0.0.20 вместе с адаптивной половиной
ZigZag, которую одну она и питала.

## Режим расчёта (scope)

`.with_swing_scope(scope)` управляет тем, как считаются свинги:

- `'global'` (по умолчанию) — один проход по всему датасету, затем агрегация в зоны;
- `'per_zone'` — локальный расчёт внутри каждой зоны (режим совместимости).

```text
.with_strategies(swing="zigzag").with_swing_scope("global")
```

> 📖 Внутренняя механика глобального режима (`_calculate_global_swings`,
> `_inject_swing_context`, фолбэки) — в
> [API: глобальные свинги — пайплайн](../api/analysis/zones/global_swings_pipeline.md).

## Контроль качества

- Запускайте smoke-тест пайплайна `tests/integration/test_pipeline_global_swings.py`,
  если меняете параметры по умолчанию.
- Сравнивайте количество свингов и амплитуды между стратегиями на одной зоне.
- Фиксируйте выбранный пресет/параметры рядом с результатами, чтобы прогоны были
  воспроизводимы.

## См. также

- [API: Strategy Pattern](../api/analysis/strategies.md) — протоколы стратегий и полный список метрик `SwingMetrics`.
- [API: глобальные свинги — стратегии](../api/analysis/zones/global_swings_strategies.md) — контракт `calculate_global`/`aggregate_for_zone`.
- [Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md) — покрытие zigzag/find_peaks/pivot_points.
