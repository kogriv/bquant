# G64 — Слои перепутаны: основание знает анализ, данные знают индикаторы, визуализация считает

**Заведён:** 2026-09-05 (реестр; находки AQ-033…039 аудита качества 2026-09-04, этап 4, P2).
**Статус:** ✅ закрыт 2026-09-06 по шести находкам из семи (AQ-033–038); AQ-039 — записанное решение, см. §6.

---

## 1. Как нашли

Аудит назвал семь находок одной формы: знание лежит не в том слое, который им владеет.
Перед правкой картина снята с графа codemap, пересобранного из `977f915` инструментом
0.0.12 (`--deep --repeat 3`): ребро `core → analysis` — одно против сорока обратных,
`data → indicators` — одно, `visualization → indicators` — три, из них одно —
расчёт ZigZag через `LibraryManager`; контракт `[architecture]` в `codemap.toml` пуст.

## 2. Замер до правки

| Находка | Что было | Замер |
|---|---|---|
| AQ-033 | `core/config.py` держал пять фабрик `create_*_strategy` и пресеты свингов, лениво импортируя `analysis.zones.strategies.registry` | 5 ленивых импортов наверх; `config.py` 887 строк |
| AQ-034 | `data/schemas.py::IndicatorSchema` создавала индикатор через `IndicatorFactory` | импорт `bquant.data` тянул слой индикаторов при первом `IndicatorSchema('macd')`; константы `MACD_SCHEMA`/`RSI_SCHEMA` делали это на импорте модуля |
| AQ-035 | `plot_zigzag_verification(price_data, legs, deviation, …)` считала ZigZag сама через `LibraryManager.create_indicator('pandas_ta', 'zigzag')` | точки на графике и точки в метриках зон — два разных расчёта; параметр `full_data_for_calculation` появился, чтобы их сблизить |
| AQ-036 | `pipeline.py` импортировал `_AdaptiveSwingStrategy` | 1 приватное имя через границу модуля |
| AQ-037 | встроенные индикаторы регистрировались в **четырёх** местах (`custom/__init__`, `preloaded/__init__`, `register_builtin_indicators`, `_register_all_indicators`); `LibraryManager.load_all_libraries()` шёл при импорте | `import bquant.analysis.zones` — **2.55 с** локально (0.43 + 1.16 индикаторы + 0.96 зоны) на тёплом кэше numba, **30 с** в чистом venv с холодным кэшем numba (лог установочной проверки 0.0.13: 09:53:59 → 09:54:29); `pandas_ta` в `sys.modules` после импорта пайплайна |
| AQ-038 | `MemoryCache` без замка; `get_cache_manager()` без замка; контракт потоков нигде не записан | 8 потоков × 3000 операций на кэше из 40 записей: **7–8 исключений за прогон** (`list.remove(x): x not in list`), словарь 40 / список порядка 41 — состояние рассогласовано в 5 прогонах из 5 |
| AQ-039 | `visualization/zones.py` ≈3500 строк, `ZoneVisualizer` 35 методов / CC 443; две предметные области в `analysis.zones` | по графу: god-классы и `complex_functions` — см. §6 |

Побочная находка ленивой загрузки: **тринадцать тестовых файлов** ставили
`os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")` на весь процесс. Это работало
только потому, что библиотека грузилась при импорте `bquant.indicators` — раньше, чем
собирались эти модули. С загрузкой по запросу флаг стал действовать, и пять тестов
`zigzag`/библиотечных колонок покраснели в батче, оставаясь зелёными поодиночке —
ровно та «order-dependent tests», которую аудит назвал последствием AQ-037.

## 3. Почему это форма «проверка не видит проверяемого»

Слой, который импортирует наверх, проверить нельзя отдельно от того, что выше него:
`import bquant.core.config` тянет реестр стратегий, `IndicatorSchema('macd')` в слое
данных — фабрику и с ней pandas-ta. Замка в кэше не было, а тесты, которые могли это
показать, шли в один поток. Контракт «слои смотрят вниз» существовал в голове и ни в
одном сторожe — так и получилось одно ребро против сорока.

## 4. Что сделано

* **AQ-033** — фабрики → `analysis/zones/strategies/factory.py`, пресеты →
  `strategies/swing/presets.py`; экспорт из `bquant.analysis.zones.strategies` и `.swing`;
  `core/config.py` 887 → 618 строк, `ANALYSIS_CONFIG` остался как умолчания.
* **AQ-034** — `IndicatorSchema`, `MACD_SCHEMA`, `RSI_SCHEMA` → `indicators/output_schema.py`,
  экспорт из `bquant.indicators`; `data.schemas` знает только `ohlcv`,
  `validate_with_schema(df, name_or_schema)` принимает экземпляр; имя `'macd'` — отказ с
  адресом, а не тихий `None`.
* **AQ-035** — `plot_zigzag_verification(price_data, swing_context, *, …)`: рисует точки
  готового контекста, ничего не считает; без контекста — `ValueError`; срез кадра показывает
  точки контекста в срезе (81 из 402 на первых 200 барах). `LibraryManager` из
  визуализации ушёл.
* **AQ-036** — `AdaptiveSwingStrategy` публичное, экспорт из `strategies.swing`.
* **AQ-037** — один бутстрап `_bootstrap_registry()` в `indicators/__init__` (preloaded +
  `register_builtin_indicators()`); `custom/__init__` и `preloaded/__init__` при импорте не
  регистрируют; `LibraryManager.ensure_loaded()` — один раз за процесс, под замком, зовётся
  фабрикой при первом `create('pandas_ta', …)` / `list_indicators()` / `get_indicator_info()`
  / `get_indicators_by_source()`. `import bquant.analysis.zones` — **1.37 с**, `pandas_ta` не
  импортирован; первый `create('pandas_ta', 'rsi')` — 0.90 с.
* **AQ-038** — `MemoryCache` под `RLock` (get/put/invalidate/clear/cleanup/stats),
  `get_cache_manager()` — двойная проверка под замком; контракт записан таблицей в
  `docs/user_guide/caching.md` §9: что потокобезопасно, что процесс-глобально, что не
  координируется между процессами.
* Тесты: 13 файлов перестали писать `BQUANT_SKIP_*` в окружение процесса.

## 5. Сторожа

* `tests/unit/test_layers_point_one_way.py` — импорты вниз по стеку (включая тела функций),
  ни одного приватного имени через границу модуля, регистрация/загрузка не на уровне
  модуля (кроме одного бутстрапа), `import bquant.analysis.zones|indicators|data` в
  подпроцессе не подгружает `pandas_ta`/`talib`.
* `tests/unit/test_global_state_has_a_contract.py` — 8 потоков на кэше без исключений и с
  согласованным состоянием; один менеджер на 8 потоков через барьер; `ensure_loaded()`
  грузит один раз.
* `codemap.toml` `[architecture]` — тот же порядок слоёв, запреты рёбер, `exhaustive`;
  проверяется `codemap check --graph … --require-contract` по свежему графу. `no_cycles`
  выключено: инструмент считает импорт под `if TYPE_CHECKING:` (`cache.py → pipeline`)
  eager-ребром и называет цикл там, где его нет при исполнении — заведено как
  [codemap#18](https://github.com/kogriv/codemap/issues/18); включить после починки.

Мутации: замок снят — 1 тест красный (исключения под потоками); флаг `_loaded` игнорируется
— 1; ленивый импорт наверх добавлен в `core/config.py` — 1; приватное имя импортировано в
`pipeline.py` — 1; регистрация возвращена в `preloaded/__init__` — 1 (нашлась самим
сторожем при первом прогоне); загрузка библиотек возвращена в импорт — 1.

## 6. Что не сделано и почему (AQ-039)

Разделение `analysis.zones` на `oscillator_zones/` и `price_levels/` — это переименование
флагманского пути `bquant.analysis.zones.analyze_zones`, который пинит внешний
потребитель по коммиту; G28 уже развёл словарь двух областей. Нарезка
`visualization/zones.py` (3500 строк, `ZoneVisualizer` CC 443) и `indicators/base.py` —
механическая, но без сторожа, который бы покраснел от их обратного срастания, она не
закрывает находку, а прячет. Оба решения — за владельцем; запись остаётся открытой как
**G64-остаток (AQ-039)** в реестре.

## 7. Ломает

`bquant.core.config` больше не экспортирует `create_*_strategy`, `SWING_PRESETS`,
`DEFAULT_SWING_PRESET`, `SwingPreset`; `bquant.data.schemas` — `IndicatorSchema`,
`MACD_SCHEMA`, `RSI_SCHEMA` (и `get_schema('macd')` → `None`, `validate_with_schema(df, 'macd')`
→ отказ); `plot_zigzag_verification` — новая сигнатура; `_AdaptiveSwingStrategy` →
`AdaptiveSwingStrategy`; `IndicatorFactory.list_indicators()` при первом вызове грузит
библиотеки (раньше это делал импорт); `BQUANT_SKIP_*` читается при первой загрузке, а не
при импорте.
