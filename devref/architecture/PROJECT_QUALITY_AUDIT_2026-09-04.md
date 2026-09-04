# Аудит качества проекта BQuant

**Дата аудита:** 2026-09-04  
**Версия проекта:** 0.0.10 + изменения раздела Unreleased  
**Тип аудита:** архитектура, связанность, корректность логики, качество кода,
дублирование, мёртвый код, тесты, документация и реестр гэпов  
**Режим:** read-only исследование; исправления продуктового кода в рамках аудита не
выполнялись  
**База:** `08a58b1` (утро 2026-09-04, до релиза 0.0.11). Влит из PR #117 в тот же день с
перенумерацией предлагаемых гэпов (§11.4) и отметкой AQ-008 как закрытого. Прочие
находки на момент вливания не перепроверялись целиком; ядро P0 (AQ-001–007, 009, 012,
026, 051) сверено с кодом на `f76d020` и подтверждено

---

## 1. Цель и область аудита

Цель аудита — определить, насколько текущая архитектура и реализация BQuant пригодны
для достоверных количественных исследований, а не только насколько успешно собирается
пакет или проходит существующий набор тестов.

Проверены:

1. пакет `bquant/` целиком;
2. Universal Zone Analysis Pipeline;
3. стратегии детекции и метрик;
4. расчёт индикаторов;
5. слой загрузки, обработки и валидации данных;
6. сериализация и кэширование;
7. статистический, регрессионный и validation-код;
8. visualization и CLI;
9. публичные фабрики, registries и re-export API;
10. `tests/`, примеры, research-скрипты и документация;
11. `devref/gaps/`, `CHANGELOG.md` и ежедневные trace logs;
12. зависимости и совместимость с разрешёнными версиями библиотек.

Аудит не ограничивался поиском `TODO` или чтением документации. Проверялись
контракты между слоями, пути деградации, cache keys, причинность swing-алгоритмов,
инварианты временных рядов, round-trip сериализации, соответствие тестов их
утверждениям и фактический статус ранее закрытых гэпов.

---

## 2. Методика

Работа выполнена четырьмя независимыми проходами:

1. архитектура и связанность модулей;
2. логическая корректность ключевых расчётов;
3. мёртвый код, дублирование и DRY;
4. сверка gap registry, changelog и тестов с текущим кодом.

Дополнительно выполнен ручной перекрёстный анализ наиболее рискованных мест:

- cache key до и после разрешения indicator roles;
- различия global и per-zone swing paths;
- фактическое поведение `validation=True`;
- типы объектов внутри `ZoneAnalysisResult`;
- сохранение реального, а не искусственного результата pipeline;
- размерности ATR-метрик;
- поведение схем на пустых данных;
- загрузка шестиколоночного MetaTrader CSV без заголовка;
- корректность статистической валидации на окнах разной длины;
- соответствие документации фактическим сигнатурам.

### 2.1. Динамическая проверка зависимостей

В изолированном аудиторском окружении разрешение зависимостей установило pandas
3.0.5, что допускается текущим ограничением `pandas>=2.3.0`. Полный прогон дал:

- 3108 passed;
- 57 failed;
- 33 errors.

Большая часть ошибок связана с несовместимостью pandas 3:

- удалённый `DataFrame.fillna(method=...)`;
- удалённые uppercase frequency aliases вроде `1H` и `H`.

Последний trace log проекта сообщает 3198 passed и 33 skipped. Оба результата могут
быть честными одновременно только для разных наборов зависимостей. Следовательно,
зелёный suite сейчас не является воспроизводимым свойством заявленного диапазона
зависимостей.

---

## 3. Итоговый вердикт

### 3.1. Общая оценка

BQuant имеет сильную центральную архитектуру, но не готов к production-использованию
как источник доверенных исследовательских выводов.

Основной MACD/global-swing сценарий защищён значительно лучше периферийных путей.
За его пределами публичный API допускает:

- возврат cached result для других входных данных;
- look-ahead в per-zone ZigZag;
- формально успешный запрос validation, который не выполняется;
- математически бессодержательные verdicts в `ValidationSuite`;
- потерю структурированных результатов при JSON/Parquet round-trip;
- смену алгоритма после исключения без отражения в metadata;
- расхождения между задокументированным и фактическим контрактом данных.

Статус **Beta** в `README.md` соответствует фактической зрелости. Формулировка
**Production Ready** в `tests/STATUS.md` — нет.

### 3.2. Оценка по направлениям

| Направление | Оценка | Вывод |
|---|---|---|
| Центральный zone pipeline | Сильная сторона | Хороший builder, DI, roles, vocabularies, registries |
| Причинность расчётов | Неоднородна | Global swings защищены, per-zone path — нет |
| Кэширование | Высокий риск | Ключ не покрывает все зависимости результата |
| Validation | Критический риск | Pipeline flag не работает; отдельная suite сравнивает несопоставимые величины |
| Persistence | Высокий риск | Форматы называются round-trip, но теряют структуру и контекст |
| Data layer | Средний/высокий риск | Несколько разных контрактов и дублирующихся формул |
| Архитектурные границы | Средний долг | `core → analysis`, `data → indicators`, `viz → computation` |
| DRY и модульность | Средний долг | Крупные файлы, повтор расчётов и registration paths |
| Тесты | Широкий охват, неодинаковая строгость | Новые invariant tests хороши; legacy tests часто поверхностны |
| Gap registry | Сильная методология, слабая гигиена статусов | Много полезных разборов, но inventory структурно устарел |

---

## 4. Сильные стороны, которые следует сохранить

### S1. Fluent pipeline

`analyze_zones()` задаёт понятную последовательность:

1. нормализация времени;
2. расчёт индикатора;
3. построение `ColumnSchema`;
4. вычисление global swings;
5. детекция зон;
6. извлечение признаков;
7. статистика, hypothesis tests, sequences, clustering и regression;
8. сборка `ZoneAnalysisResult`.

Builder отделяет пользовательский API от orchestration-класса и позволяет
конфигурировать pipeline без специализированных MACD-фасадов.

### S2. Indicator identity и output roles

`IndicatorId`, закрытый словарь roles и `ColumnSchema` устраняют зависимость
универсального кода от строк вроде `macd_hist`. Это правильное архитектурное
направление: identity и meaning больше не слиты в одном литерале.

### S3. Zone vocabulary

`ZoneType` и `ZoneVocabulary` позволяют downstream-слоям рассуждать о polarity,
counterpart и display label, не предполагая названия `bull` и `bear`. Это важная
универсализация для threshold и custom detectors.

### S4. Детекция и metric strategies через registries

Регистрация стратегий делает расширение предсказуемым. Контракт неизвестных detection
rules теперь строгий: лишний параметр не проглатывается молча.

### S5. Global swing causality

`SwingPoint.confirmation_index`, replay-causal tests и отдельная работа по ZigZag,
find_peaks и pivot_points — сильная часть проекта. Проблема не в отсутствии
каузального дизайна, а в том, что он не доведён до per-zone пути.

### S6. `min_duration` как reporting filter

Перенос фильтра из detection в analysis устранил разрывы в tiling и сделал исключённые
зоны наблюдаемыми через metadata.

### S7. Install-safe state directories

Разделение `PROJECT_ROOT` и `STATE_ROOT`, отказ от записи в `site-packages` на import и
ленивое создание log-файла — корректные решения для устанавливаемого публичного
пакета.

### S8. Новые invariant-based tests

Тесты причинности, adjacency, role resolution, cache schema, документационных вызовов,
shadowed definitions и отсутствующих метрик проверяют смысловые инварианты, а не только
типы объектов. Этот стиль следует распространить на оставшийся legacy suite.

---

## 5. Реестр найденных проблем

Статусы:

- **Bug** — дефект следует непосредственно из кода или воспроизводимого поведения;
- **Risk** — реалистичный путь к неверному результату, требующий отдельного
  regression test;
- **Architecture** — структурная проблема, повышающая вероятность новых дефектов;
- **Dead/DRY** — мёртвый, дублирующий или вводящий в заблуждение код;
- **Test gap** — существующие проверки не способны увидеть заявленное свойство.

Приоритеты:

- **P0** — достоверность результата или поддерживаемость установки;
- **P1** — высокий риск неправильного поведения публичного API;
- **P2** — архитектура и maintainability;
- **P3** — гигиена и низкорисковый долг.

---

## 6. P0 — достоверность результатов

### AQ-001. Cache data hash не покрывает зависимости результата

**Тип:** Bug  
**Приоритет:** P0  
**Где:** `bquant/analysis/zones/cache.py::compute_data_hash`

Хэш строится только по `open`, `high`, `low`, `close`. Pandas включает index в
`hash_pandas_object()` по умолчанию, поэтому время не игнорируется полностью. Однако
из ключа исключены:

- `volume`;
- precomputed indicator columns;
- arbitrary columns, читаемые combined conditions;
- auxiliary data, используемые custom strategies.

Сценарии неверного cache hit:

1. одинаковые OHLC и разные значения `RSI_14`, detection по `indicator_col='RSI_14'`;
2. одинаковые OHLC и разный volume, включена volume strategy;
3. одинаковые OHLC и разные custom regime columns, combined detector читает эти
   колонки;
4. вызывающий исправил precomputed indicator, но получил cached zones до исправления.

Кэш включён по умолчанию, поэтому это не редкий opt-in path.

**Предложение:**

- каждая стратегия должна объявлять `data_dependencies`;
- cache layer должен хэшировать union обязательных колонок;
- combined callable без декларации зависимостей не должен кэшироваться;
- альтернативно — безопасный default: хэшировать весь DataFrame;
- добавить tests на изменение только volume, indicator и custom columns.

### AQ-002. Разрешение roles мутирует конфигурацию после построения cache key

**Тип:** Bug  
**Приоритет:** P0  
**Где:** `ZoneAnalysisPipeline._resolve_indicator_role`

Метод выполняет `rules.pop(role_key)` и добавляет `<name>_col`. Первый key строится с
`indicator_role`, последующий запуск того же объекта — уже с `indicator_col`.

Последствия:

- первый повторный запуск получает cache miss;
- `invalidate_cache()` после выполнения может вычислить другой key;
- builder/config перестают быть value objects;
- один config нельзя безопасно передавать нескольким pipeline instances.

**Предложение:**

- сделать `ZoneDetectionConfig` immutable;
- resolution выполнять в локальной копии;
- разделить user config и resolved execution plan;
- key строить только по нормализованному execution plan.

### AQ-003. Per-zone ZigZag использует repainting path

**Тип:** Bug, look-ahead  
**Приоритет:** P0  
**Где:** `ZigZagSwingStrategy.calculate`

`calculate_global()` создаёт pandas-ta ZigZag с `backtest=True`. `calculate()` этого
аргумента не передаёт и использует default library behavior. В результате причинный
контракт зависит от `swing_scope`.

**Последствия:**

- per-zone метрики могут использовать будущие наблюдения;
- `global` и `per_zone` сравнивают не только области, но и разные алгоритмы;
- исследователь может получить завышенный результат из-за leakage;
- `confirmation_index` не защищает этот путь.

**Предложение:**

- сделать `backtest=True` обязательным для обоих путей;
- либо удалить per-zone ZigZag как непричинный;
- перенести truncation oracle из global tests на `calculate()`;
- документировать causal contract на уровне protocol.

### AQ-004. Global swing failure переключает pipeline на другой алгоритм

**Тип:** Bug/Risk  
**Приоритет:** P0  
**Где:** `ZoneAnalysisPipeline._run_without_cache`

Любое исключение при global swing calculation перехватывается общим
`except Exception`, после чего pipeline продолжает с per-zone metrics.

Пользователь запросил `global`, но получает:

- другой scope;
- для ZigZag — другое causal behavior;
- отсутствие `SwingContext`;
- отсутствие structured warning в result;
- возможность сохранения результата под global cache key.

**Предложение:**

- по умолчанию fail closed;
- fallback разрешать только явным `fallback='per_zone'`;
- записывать `requested_scope`, `effective_scope`, `fallback_reason`;
- не сохранять fallback-result под key исходного алгоритма.

### AQ-005. Validation сравнивает абсолютные counts на окнах разной длины

**Тип:** Bug, ошибка методологии  
**Приоритет:** P0  
**Где:** `ValidationSuite.out_of_sample_test`,
`ValidationSuite.walk_forward_test`

Default metric — `total_zones`. Для split 70/30 одинаковая частота зон закономерно
даёт меньшее абсолютное число в test. Это будет названо деградацией.

Walk-forward defaults ещё несопоставимее: 1000 train bars против 200 test bars.

**Предложение:**

- убрать `total_zones` как default validation metric;
- counts нормализовать на число баров или время;
- metric specification должна содержать denominator;
- сравнивать confidence intervals/rates, а не сырые counts;
- tests должны использовать stationary synthetic process.

### AQ-006. `ValidationSuite` не знает направления качества метрики

**Тип:** Bug, ошибка абстракции  
**Приоритет:** P0

Один generic numeric key недостаточен для validation verdict:

- рост может быть улучшением или ухудшением;
- снижение может быть улучшением или ухудшением;
- стабильность не всегда означает качество.

Код использует `abs(degradation)`, поэтому сильное улучшение также даёт
`success=False`.

Если train metric равна нулю, `_calculate_degradation()` возвращает `0.0` независимо
от test metric — ложная стабильность.

**Предложение:**

Ввести `MetricSpec`:

```text
name
direction: higher_is_better | lower_is_better | target
normalization: per_bar | per_time | none
comparison: relative | absolute | statistical
threshold
zero_baseline_policy
```

### AQ-007. Monte Carlo metadata называет значением то, что объявлено percentile

**Тип:** Bug  
**Приоритет:** P0

Код сначала получает долю simulated values ниже real value, затем передаёт эту долю в
`np.percentile()` и сохраняет полученное **значение метрики** под ключом
`percentile_real`.

Это не percentile rank. Кроме того, success предполагает, что большее значение всегда
лучше, что для generic metric неверно.

**Предложение:**

- `percentile_rank = 100 * mean(sim < real)`;
- отдельно хранить `p95_value`;
- направление сравнения брать из `MetricSpec`;
- добавить lower-is-better regression case.

### AQ-008. pandas 3 разрешён metadata, но не поддерживается

**Тип:** Bug, packaging  
**Приоритет:** P0

`pandas>=2.3.0` разрешает pandas 3, но production и test code используют удалённые API:

- `fillna(method='ffill')`;
- `fillna(method='bfill')`;
- uppercase frequency aliases.

**Предложение:**

Вариант A:

- временно ограничить `pandas>=2.3,<3`;
- явно записать ограничение в changelog.

Вариант B, предпочтительный:

- заменить на `.ffill()`/`.bfill()`;
- нормализовать aliases на lowercase;
- CI matrix: minimum supported + latest pandas;
- отдельный dependency-resolution smoke test без lock.

---

## 7. P1 — честность и корректность публичного API

### AQ-009. `validation=True` принимается, но ничего не выполняет

**Тип:** Bug  
**Приоритет:** P1  
**Где:** `UniversalZoneAnalyzer.analyze_zones`

Флаг проходит builder, presets и config, но analysis branch только пишет:
`Validation requested but not executed`. `validation_results` остаётся `None`.

**Предложение:**

- либо реализовать validation callback/factory;
- либо немедленно бросать `NotImplementedError`;
- до реализации убрать параметр из presets и документации;
- `metadata` должна различать `not_requested`, `executed`, `failed`,
  `not_supported`.

### AQ-010. Реальный `hypothesis_tests` теряется в JSON и Parquet

**Тип:** Bug, data loss  
**Приоритет:** P1

Analyzer кладёт в `ZoneAnalysisResult.hypothesis_tests` объект `AnalysisResult`, хотя
поле аннотировано как dict. JSON/Parquet metadata используют `default=str`, поэтому
объект превращается в строковое представление.

Существующий serialization test передаёт искусственный dict и не воспроизводит
реальный pipeline result.

**Предложение:**

- нормализовать `.results` при сборке результата;
- определить строгую JSON schema;
- запретить `default=str` для структурных полей;
- round-trip test должен начинаться с настоящего `analyze_zones(...).build()`.

### AQ-011. JSON/Parquet не являются полным round-trip результата

**Тип:** Bug/contract gap  
**Приоритет:** P1

Теряются:

- `ZoneInfo.swing_context`;
- `ZoneInfo.data`;
- DataFrame index в JSON `include_data=True`;
- типизированные объекты, не поддержанные JSON напрямую.

После загрузки `zone.get_zone_swings()` возвращает пустой список, даже если исходный
анализ был global.

**Предложение:**

- определить уровни persistence: summary, analytical, full;
- сохранять time index явно;
- сериализовать `SwingContext`;
- либо честно переименовать JSON export в summary export;
- добавить equality contract по каждому уровню.

### AQ-012. ATR enrichment в pipeline недостижим

**Тип:** Bug, dead branch  
**Приоритет:** P1

Pipeline вызывает `calculate_derived_indicators()`, ожидая колонку `atr`. Эта функция
ATR не создаёт. Ветка `if 'atr' in derived.columns` всегда ложна, если ATR не пришёл во
входном кадре.

**Предложение:**

- реализовать true range и rolling ATR в одном каноническом месте;
- назвать период ATR в config и cache key;
- либо удалить обещание автоматического ATR;
- test должен проверять наличие ATR в `result.data`.

### AQ-013. `atr_normalized_return` имеет неверную размерность

**Тип:** Bug  
**Приоритет:** P1

Сейчас:

```text
price_return / ATR
```

где `price_return` безразмерен, а ATR измеряется в единицах цены.

Корректные эквивалентные формы:

```text
(end_price - start_price) / ATR
price_return / (ATR / start_price)
```

**Предложение:**

- исправить формулу;
- переименовать поле при необходимости;
- добавить dimensional invariant test;
- bump cache schema.

### AQ-014. Пустой DataFrame с правильными колонками проходит schema validation

**Тип:** Bug  
**Приоритет:** P1

`DataSchema.validate_dataframe()` проверяет наличие колонок, dtype и rules. Если
колонки есть, но строк нет, rules дают warnings и `issues` остаётся пустым.

Это противоречит заявлению G42, что пустые кадры отвергаются.

**Предложение:**

- `df.empty` должен быть issue;
- минимальное число строк должно быть свойством schema;
- добавить exact regression test с пустыми OHLC-колонками.

### AQ-015. `OHLCVSchema` не проверяет OHLC relations

**Тип:** Bug/contract gap  
**Приоритет:** P1

`OHLCVRecord.validate()` проверяет:

- high не ниже low;
- high не ниже open/close;
- low не выше open/close.

`OHLCVSchema.validate_dataframe()` через declared rules проверяет только
положительность отдельных колонок.

Один и тот же контракт имеет две разные строгости.

**Предложение:**

- добавить dataframe-level cross-column rules;
- вынести общие OHLC invariants в один helper;
- использовать его loader, schema и validator слоями.

### AQ-016. `validate_data_completeness()` делит на ноль

**Тип:** Bug  
**Приоритет:** P1

Пустой DataFrame с объявленными колонками проходит в цикл missing ratios, где число
NaN делится на `len(df) == 0`.

**Предложение:**

- ранний empty verdict;
- единый `DataValidationResult` вместо нескольких несовместимых dict schemas;
- regression test на empty-with-columns.

### AQ-017. Шестиколоночный MetaTrader CSV без заголовка читается неверно

**Тип:** Bug  
**Приоритет:** P1

Первая попытка читает CSV с `index_col=0`. После этого у стандартного шестиколоночного
файла остаётся пять колонок, а `_is_mt_format_without_headers()` требует минимум шесть
и возвращает `False`.

Проверка первой колонки `isinstance(str(value), str)` всегда истинна и ничего не
проверяет.

**Предложение:**

- format sniffing выполнять по raw sample до `index_col`;
- проверять datetime pattern первой колонки;
- проверять numeric OHLCV columns;
- покрыть 6- и 7-column fixtures без headers.

### AQ-018. Частично невалидная time column превращается в index с `NaT`

**Тип:** Risk  
**Приоритет:** P1

`resolve_time_index()` отказывается от колонки только если не распарсилось ни одного
значения. Если распарсилась одна строка, а остальные стали `NaT`, такой index
принимается.

**Последствия:** неверная сортировка, ambiguous zone boundaries, ошибки visualization и
cache identity.

**Предложение:**

- configurable threshold допустимых parse failures;
- по умолчанию любое `NaT` в time index считать validation error;
- сообщать count и исходные значения.

### AQ-019. Preloaded zones не валидируют порядок, пересечения и duplicate timestamps

**Тип:** Bug/Risk  
**Приоритет:** P1

Проблемы:

- входные зоны не сортируются;
- overlapping zones разрешены;
- `time_tolerance` расширяет declared interval;
- `get_loc()` на duplicate index возвращает slice или mask;
- DataFrame со строковыми датами отвергается, хотя пример в docstring показывает
  строки;
- timezone compatibility проверяется поздно и неполно.

**Предложение:**

- нормализовать datetime columns внутри `_load_zones`;
- сортировать по start/end;
- явная overlap policy: reject, merge или event-mode;
- использовать positional indices через `np.flatnonzero(mask)`;
- требовать unique monotonic OHLCV index;
- tolerance применять к matching, но хранить declared и matched boundaries отдельно.

### AQ-020. Sequence adjacency считает пересекающиеся зоны соседними

**Тип:** Bug  
**Приоритет:** P1

Условие `start[i] <= end[i-1] + 1` принимает:

- корректно примыкающую зону;
- overlap;
- зону, начинающуюся раньше предыдущей.

Для tiling adjacency должна быть `==`. Для event zones нужен отдельный relation model.

**Предложение:**

- strict equality для temporal tiling;
- overlap и reverse order — explicit error;
- отдельный analyzer для event/price-level zones;
- tests на overlap и unsorted input.

### AQ-021. Результат `validate_data()` индикатора игнорируется

**Тип:** Bug  
**Приоритет:** P1

Custom и preloaded indicators вызывают `self.validate_data(data)`, но не проверяют
возвращённый bool. Недостаток строк логируется как error, после чего calculation
продолжается.

**Предложение:**

- validation должна бросать typed exception либо её bool обязан проверяться;
- не объединять logging и control flow;
- min records вычислять по фактическим call overrides;
- invalid dtype и non-finite values проверять до pandas calculation.

### AQ-022. Optimized EMA теряет дробную часть на integer input

**Тип:** Bug  
**Приоритет:** P1

`np.zeros_like(prices)` наследует integer dtype. EMA assignments обрезаются до целых.
Этот EMA используется optimized RSI и MACD.

**Предложение:**

- `np.asarray(prices, dtype=float)`;
- output всегда float;
- tests на integer и float inputs должны совпадать.

### AQ-023. Optimized MACD нарушает единый warm-up contract

**Тип:** Bug  
**Приоритет:** P1

Custom MACD маскирует:

- line до `slow - 1`;
- signal и histogram до `slow + signal - 2`.

Optimized MACD публикует значения с первого бара. Периоды `<=0` также не валидируются.

**Предложение:**

- единый parameter/warm-up helper для всех implementations;
- parity tests custom, optimized и pandas-ta;
- validation `fast > 0`, `slow > fast`, `signal > 0`.

### AQ-024. Constant-price dataset полностью удаляется outlier filter

**Тип:** Bug  
**Приоритет:** P1

При standard deviation, равном нулю:

```text
(x - mean) / std = NaN
NaN <= threshold = False
```

Все строки удаляются как выбросы.

**Предложение:**

- zero-variance column не создаёт outliers;
- mask должен начинаться с all-True;
- считать mask по исходному frame, а не последовательно изменять distribution;
- tests на constant и near-constant series.

### AQ-025. `detect_market_sessions()` оставляет NaN вместо False

**Тип:** Bug  
**Приоритет:** P1

Присваивание `True` только overlap-строкам создаёт NaN в остальных. Последующий
`DataFrame.get()` не заполняет их, потому что колонка уже существует.

**Предложение:**

- инициализировать колонку `False`;
- затем присвоить `True` по mask;
- assert boolean dtype и отсутствие null.

### AQ-026. Две функции считают разные величины под именем `true_range`

**Тип:** Bug/DRY  
**Приоритет:** P1

`calculate_derived_indicators()`:

```text
high - low
```

`add_technical_features()`:

```text
max(high-low, abs(high-prev_close), abs(low-prev_close))
```

Вторая формула является True Range, первая — только intrabar range.

**Предложение:**

- единый `calculate_true_range`;
- первой величине дать имя `intrabar_range`;
- ATR строить только из канонического True Range.

### AQ-027. Fallback oscillator выбирается как первая подходящая numeric column

**Тип:** Risk  
**Приоритет:** P1

Если `indicator_context` отсутствует, `_find_any_oscillator()` берёт первую numeric
колонку, не входящую в короткий exclude list. Это может быть spread, derived feature,
позиционный id или чужая метрика.

Pipeline продолжит расчёт и выдаст правдоподобные, но относящиеся к другому ряду
amplitude/correlation.

**Предложение:**

- отказаться от угадывания по умолчанию;
- требовать explicit indicator column или schema;
- degraded guess разрешать только opt-in и отражать в metadata.

### AQ-028. `IndicatorId` не является immutable и теряет source в `ColumnSchema`

**Тип:** Bug  
**Приоритет:** P1

Frozen dataclass хранит mutable dict `parameters`. После помещения object в dict/set
параметры можно изменить, вместе с ними изменятся slug и hash.

`ColumnSchema` индексирует entries только по `(slug, role)`, хотя identity включает
source. Custom и library indicator с одинаковыми slug могут затереть друг друга.

**Предложение:**

- `MappingProxyType` или tuple нормализованных pairs;
- schema key: полный `IndicatorId` либо `(source, slug, role)`;
- tests на direct mutation и same-slug/different-source.

### AQ-029. Regression API называется prediction, но использует ex-post features

**Тип:** Risk/semantic bug  
**Приоритет:** P1

Price-return regression использует:

- duration всей завершённой зоны;
- drawdown from peak, содержащий end price;
- число peaks за всю зону;
- oscillator slope всей зоны.

Target — return той же завершённой зоны. Это explanatory in-sample regression, а не
forecast. Высокий R² не является predictive evidence.

Также `durbin_watson` читается как attribute fitted model, которого обычно нет, и
metadata получает `None`.

**Предложение:**

- переименовать в `explain_*` или сформировать features на decision time;
- отделить in-sample diagnostics от out-of-sample prediction;
- вычислять Durbin-Watson явной функцией;
- metadata должна содержать feature availability time.

### AQ-030. StatisticalAnalyzer смешивает tests с разными semantics

**Тип:** Risk, statistical methodology  
**Приоритет:** P1

Проблемы:

- KS normality test использует mean/std, оценённые на той же выборке; стандартный KS
  p-value в таком случае некорректен без Lilliefors correction;
- Anderson-Darling всегда берёт critical value index для 5%, игнорируя переданный
  `alpha`;
- helper `test_normality()` возвращает True, если хотя бы один из нескольких tests
  принял normality, без multiple-testing policy;
- descriptive `count` использует длину series вместе с NaN, тогда как остальные
  метрики NaN пропускают.

**Предложение:**

- использовать `statsmodels.stats.diagnostic.lilliefors`;
- выбирать Anderson critical level по alpha;
- определить aggregation policy;
- count сделать non-null count.

---

## 8. P2 — архитектура и связанность

### AQ-031. `create_analyzer()` — публичная неработающая фабрика

**Тип:** Architecture/Bug  
**Приоритет:** P2

Фабрика рекламирует шесть analysis types, но всегда возвращает `BaseAnalyzer`.
`BaseAnalyzer.analyze()` бросает `NotImplementedError`. Даже `statistical` не
связан с существующим `StatisticalAnalyzer`.

**Предложение:**

- wire real classes;
- либо удалить factory;
- либо переименовать в `create_analysis_config_holder`, если именно это её назначение;
- каталог должен включать только executable capabilities.

### AQ-032. Intentional stub modules расширяют ложную API surface

**Тип:** Architecture  
**Приоритет:** P2

`technical`, `chart`, `candlestick`, `timeseries` помечены `is_stub=True`, что честнее
прежнего поведения, но всё ещё экспортируются рядом с рабочими анализаторами.

**Предложение:**

- перенести в `analysis.experimental` или `analysis.stubs`;
- не включать в supported executable analyzers;
- не возвращать успешный `AnalysisResult` для несуществующей функции.

### AQ-033. `core` зависит от analysis strategies

**Тип:** Architecture  
**Приоритет:** P2

`core/config.py` содержит `create_swing_strategy`, `create_shape_strategy`,
`create_divergence_strategy`, `create_volume_strategy`,
`create_volatility_strategy` и лениво импортирует analysis registry.

Это обратное направление зависимости: foundation layer знает domain implementation.

**Предложение:**

- перенести factories в `analysis/zones/strategies/factory.py`;
- swing presets — в `analysis/zones/strategies/swing/presets.py`;
- `core/config.py` оставить для paths и generic configuration.

### AQ-034. Data schema зависит от IndicatorFactory

**Тип:** Architecture  
**Приоритет:** P2

`data/schemas.py::IndicatorSchema` импортирует indicators и создаёт indicator для
получения output columns.

**Предложение:**

- перенести `IndicatorSchema` в indicators package;
- либо inject output contract;
- data layer не должен загружать external indicator libraries для validation schema.

### AQ-035. Visualization выполняет analysis и зависит от detection

**Тип:** Architecture  
**Приоритет:** P2

Visualization:

- вычисляет ZigZag через `LibraryManager`;
- обращается к detection registry для vocabulary;
- тем самым смешивает presentation и computation.

**Предложение:**

- visualization принимает готовые `SwingContext`, `ZoneVocabulary` и display model;
- вычисления остаются в analysis;
- `ZoneAnalysisResult` должен нести всё необходимое для rendering.

### AQ-036. Pipeline импортирует private `_AdaptiveSwingStrategy`

**Тип:** Architecture  
**Приоритет:** P2

Приватное имя используется за пределами собственного модуля и фактически является
частью внутреннего API.

**Предложение:**

- публичный `AdaptiveSwingStrategy`;
- либо factory `create_adaptive_swing_strategy`;
- запрет imports private symbols между subpackages.

### AQ-037. Import-time registration и тройная регистрация indicators

**Тип:** Architecture/DRY  
**Приоритет:** P2

Built-ins регистрируются:

1. при import `indicators.custom`;
2. через `register_builtin_indicators()`;
3. в `indicators._register_all_indicators()`.

Корневой import также вызывает `LibraryManager.load_all_libraries()`.

**Последствия:** global side effects, медленный import, order-dependent tests,
сложность parallel execution.

**Предложение:**

- один idempotent bootstrap;
- lazy registration на первом create/list;
- explicit reset fixture для tests;
- library discovery не выполнять при обычном import.

### AQ-038. Global mutable state не имеет thread-safety contract

**Тип:** Architecture/Risk  
**Приоритет:** P2

Глобальны:

- cache manager;
- indicator/detection/strategy registries;
- runtime directory overrides;
- extra output roles;
- library availability flags.

Memory cache также не защищён lock.

**Предложение:**

- dependency injection для cache/config/registries;
- singleton оставить только convenience default;
- context-local directory overrides;
- задокументировать thread/process safety.

### AQ-039. God modules и две zone domain models

**Тип:** Architecture  
**Приоритет:** P2

Крупнейшие файлы:

- `visualization/zones.py` — около 3500 строк;
- `indicators/base.py` — больше 1000 строк;
- `analysis/zones/pipeline.py` — около 1000 строк;
- `analysis/zones/zone_features.py` — около 1000 строк.

В `analysis.zones` по-прежнему живут две разные предметные области:

- temporal oscillator zones;
- support/resistance price-level zones.

Переименование G28 улучшило терминологию, но не разделило packages.

**Предложение:**

- `analysis/oscillator_zones/`;
- `analysis/price_levels/`;
- visualization разбить на overview/detail/metrics/swings;
- indicator base разбить на contracts/factory/helpers.

### AQ-040. Indicator helper methods скопированы трижды

**Тип:** Dead/DRY  
**Приоритет:** P2

`get_statistics`, `is_trending_up`, `is_trending_down`, `get_crossovers` повторяются
между:

- `PreloadedIndicator`;
- `CustomIndicator`;
- `MACDPreloadedIndicator`.

Уже наблюдается функциональный дрейф: CustomIndicator не имеет общего crossover
метода, хотя `MACD.get_info()` рекламирует `get_crossovers()`.

**Предложение:**

- stateless module helpers или `IndicatorAnalyticsMixin`;
- методы должны работать по `IndicatorResult` и output roles;
- `available_methods` генерировать introspection, а не литералом.

### AQ-041. Calculator layer повторно реализует indicators

**Тип:** DRY/Bug  
**Приоритет:** P2

`calculate_moving_averages()` использует factory только для первого периода, затем
считает остальные SMA/EMA вручную. `create_indicator_suite()` снова вручную считает
дополнительные periods.

Ручные EMA обходят warm-up contract и могут использовать другую настройку `adjust`.

**Предложение:**

- все calculations только через indicator objects;
- batch calculator хранит result по `(name, normalized params)`, а не только name;
- удалить duplicate formulas.

### AQ-042. Presets повторяют builder tail и хардкодят library column names

**Тип:** DRY/Architecture  
**Приоритет:** P2

RSI preset строит `RSI_{period}`, AO — `AO_{fast}_{slow}`, хотя role/schema
архитектура создана именно для отказа от library naming conventions.

Четыре presets также повторяют analysis/cache arguments.

**Предложение:**

- использовать `indicator_role='value'`;
- общий internal `_build_preset`;
- публичные функции сохранить как стабильные wrappers.

### AQ-043. StrategyRegistry повторяет один механизм пять раз

**Тип:** DRY  
**Приоритет:** P2

Register/get/list logic повторяется для swing, shape, divergence, volatility, volume.

**Предложение:**

- generic typed registry bucket;
- family enum;
- единый conflict/validation policy.

### AQ-044. Generic cache key нестабилен между процессами

**Тип:** Risk/Performance  
**Приоритет:** P2

`MemoryCache._generate_key()` использует Python `hash(str(value))` и `hash(bytes)`.
Python hash salted per process, поэтому persistent disk cache для таких аргументов не
имеет стабильного key между запусками.

Также загрузка disk entry в memory создаёт новый default TTL и может продлить жизнь
почти истёкшей записи.

**Предложение:**

- canonical serialization + SHA-256;
- сохранять и переносить абсолютный expiry;
- тест key stability в subprocess.

### AQ-045. Model invariants не проверяются

**Тип:** Architecture/Risk  
**Приоритет:** P2

`ZoneInfo` не проверяет:

- `start_idx <= end_idx`;
- `duration == end_idx - start_idx + 1`;
- соответствие `len(data)` duration;
- порядок времени.

`SwingContext` проверяет длины arrays, но не sortedness `indices`, хотя `bisect`
требует сортировку.

**Предложение:**

- строгие `__post_init__` invariants;
- отдельный unsafe/legacy loader при необходимости;
- property-based tests.

### AQ-046. Optional dependency model противоречив

**Тип:** Packaging/Architecture  
**Приоритет:** P2

Base dependencies включают visualization, notebook и export packages, хотя код и
документация называют их optional.

Сообщение `ZoneAnalysisResult.visualize()` предлагает установить `bquant[viz]`, но
extra `viz` в `pyproject.toml` не существует.

Extras `notebooks` и `full` повторяют уже обязательные dependencies.

**Предложение:**

- минимальное ядро: numpy, pandas, scipy;
- extras: `viz`, `stats`, `notebooks`, `research`, `full`;
- сообщения об установке генерировать из реальных extras;
- тест установки каждого extra в clean environment.

### AQ-047. Публичные типы результата не согласованы

**Тип:** API quality  
**Приоритет:** P2

`ZoneAnalysisResult.hypothesis_tests` аннотирован как dict, но runtime возвращает
`AnalysisResult`. Документация вынуждена писать «dict или object with `.results`».

Документация также приводит `ColumnSchema.column(indicator, role)`, тогда как реальная
сигнатура — `column(role, indicator=None)`.

**Предложение:**

- нормализовать result fields к JSON-compatible dataclasses/dicts;
- генерировать signature sections из introspection;
- type-checking в CI.

---

## 9. P3 — мёртвый код и repository hygiene

### AQ-048. Подтверждённый внутренний dead code

**Тип:** Dead  
**Приоритет:** P3

Кандидаты:

- `_StubIndicator` — не используется и не экспортируется;
- `bquant.core.exceptions.NotImplementedError` — production-кодом не используется и
  затеняет builtin;
- `ensure_logging_initialized()` — нет callers;
- пустой try/pass block в `indicators/library/__init__.py`;
- второй logging setup в `core/utils.py`, почти не используемый.

**Предложение:**

- удалить внутренние symbols;
- для public symbols сначала deprecation release;
- оставить один logging bootstrap.

### AQ-049. Экспортированные symbols без внутренних consumers

**Тип:** Dead/API uncertainty  
**Приоритет:** P3

Найдены:

- `plot_macd_zones_chart`;
- `analyze_zones_visually`;
- `DistributionPlotter`;
- `load_pandas_ta`;
- `load_talib`;
- `load_all_indicators`.

Отсутствие внутренних callers не доказывает отсутствие внешних пользователей.

**Предложение:**

- отметить experimental/deprecated;
- собрать usage telemetry невозможно для public package, поэтому удалять только через
  documented breaking release;
- либо добавить examples/tests, подтверждающие назначение.

### AQ-050. `get_zone_features_summary()` — неиспользуемая и устаревшая логика

**Тип:** Dead/Bug  
**Приоритет:** P3

Метод не имеет callers и продолжает hardcode `bull`/`bear`, хотя основной pipeline
перешёл на `ZoneVocabulary`.

**Предложение:**

- удалить;
- либо переписать на generic `zones_by_type` и покрыть tests.

### AQ-051. `FindPeaksSwingStrategy.config_hash()` не включает warm-up

**Тип:** Bug/Risk  
**Приоритет:** P2

`_build_strategy_params()` правильно добавляет `prominence_warmup` на auto path и
прямо комментирует, что параметр меняет swings и обязан попасть в cache key.

`config_hash()` возвращает только:

- prominence;
- distance;
- min_amplitude_pct.

Два auto-prominence strategies с разным warm-up могут разделить cache entry.

**Предложение:**

- `config_hash()` должен использовать `_build_strategy_params()`;
- cache-key test для warm-up 100 против 200;
- bump cache schema после исправления.

### AQ-052. Stale research/doctest artifacts ссылаются на удалённый API

**Тип:** Repository hygiene  
**Приоритет:** P3

В `devref/gaps/zo/zodoctest/` остаются старые imports `MACDZoneAnalyzer` и другие
исторические примеры. Они не входят в основной pytest suite, поэтому могут выглядеть
как рабочая validation infrastructure.

**Предложение:**

- либо мигрировать и включить в tests;
- либо перенести в archive;
- файлы, которые заведомо не исполняются, не называть tests.

### AQ-053. Generated sample metadata дублирует registry и остаётся повреждённым

**Тип:** Existing gap G40 remainder  
**Приоритет:** P2

`embedded/mt_xauusd_m15.py::DATASET_INFO` содержит:

- columns, взятые из первой строки старого CSV;
- `period_start=None`;
- `period_end=None`.

Публичный registry исправлен, но generator output и registry остаются двумя sources of
truth.

**Предложение:**

- generator должен распознавать no-header MT CSV;
- registry генерировать из embedded metadata;
- regeneration обязана fail, если period не определён;
- test parity embedded metadata ↔ registry.

### AQ-054. `calculate_with_cache()` называется кэшем, но кэша не имеет

**Тип:** API quality/Dead abstraction  
**Приоритет:** P3

`CustomIndicator.calculate_with_cache()` просто вызывает `calculate()`.
`IndicatorCalculator` использует именно этот метод, создавая ложное впечатление, что
calculations cached.

**Предложение:**

- реализовать cache;
- либо удалить метод и вызывать `calculate`;
- `IndicatorCalculator.results` назвать local result store, не cache.

### AQ-055. MACD metadata рекламирует отсутствующий `get_crossovers()`

**Тип:** Bug/Documentation  
**Приоритет:** P3

`MACD.get_info()['available_methods']` содержит `get_crossovers()`, но
`CustomIndicator` такого метода не определяет.

Research examples также вызывают trend/crossover helpers на классах, где они
доступны неодинаково.

**Предложение:**

- генерировать capability list через protocols/introspection;
- общий analytics mixin;
- executable tests для каждого advertised method.

---

## 10. Аудит тестов

### 10.1. Сильные тестовые практики

Следует сохранить и расширить:

- replay-causal truncation tests;
- tiling и adjacency invariants;
- role/schema round-trip;
- cache behavior по strategy configuration;
- docs import and call signature parity;
- mutation tests, показывающие, что regression guard действительно краснеет;
- repository-wide shadowed-definition scan.

### 10.2. Слабые и ложноположительные tests

#### T1. Тест min duration ничего не меняет

Создаются две одинаковые detection configs без параметра duration, затем проверяется:

```text
len(zones2) <= len(zones1)
```

При равенстве assertion всегда проходит. Название теста обещает проверку поведения,
которого в нём нет.

#### T2. Условные assertions дают vacuous pass

Несколько tests выполняют проверки только внутри:

```python
if zones:
    ...
```

Если zones не найдено, тест проходит, не проверив контракт.

#### T3. Слишком много shape-only assertions

Legacy tests часто проверяют только:

- `isinstance`;
- наличие ключа;
- `is not None`;
- отсутствие exception.

Именно этот стиль ранее пропустил validation, themes, parquet и duplicate methods.

#### T4. Unseeded random data

`test_zone_detection_strategies.py` массово использует global `np.random` без seed.
Большинство assertions широкие, но изменение случайной выборки может создавать flaky
или vacuous cases.

#### T5. Persistence tests не используют production-shaped result

Fixture вручную кладёт dict в `hypothesis_tests`. Реальный pipeline кладёт
`AnalysisResult`. Поэтому test подтверждает искусственный schema, а не runtime schema.

#### T6. G42 test narrative шире test implementation

Описание говорит, что пустой DataFrame должен быть отвергнут, но empty-with-columns
case отсутствует.

#### T7. Нет теста working validation flag

Suite проверяет `ValidationSuite` отдельно, но не утверждает, что
`.analyze(validation=True)` формирует `validation_results`.

#### T8. Нет cache dependency matrix

Не проверяются изменения только:

- volume;
- precomputed indicator;
- custom combined input;
- datetime column/index representation;
- `prominence_warmup`.

#### T9. Causality проверена только для global path

Per-zone `calculate()` не проходит тот же oracle.

#### T10. `tests/STATUS.md` не отражает suite

Документ продолжает сообщать 670 passed и Production Ready. Trace log сообщает 3198
passed, а разрешённая pandas 3 даёт другой результат.

### 10.3. Предлагаемая test matrix

Минимальная обязательная матрица:

1. Python 3.12 + minimum dependencies;
2. Python 3.12 + latest dependencies;
3. Python 3.13 + minimum dependencies;
4. Python 3.13 + latest dependencies;
5. package installed read-only;
6. package without visualization extras;
7. all extras;
8. cache disabled и enabled;
9. global и per-zone swing scope;
10. JSON, Parquet и pickle real-pipeline round-trip.

---

## 11. Сверка существующего gap registry

### 11.1. Действительно открытые записи

#### G48

Zone-scale thresholds измерены и дают большее swing coverage, но не доказано, что
добавленные swings являются сигналом, а не шумом. Оставить открытым — правильное
решение.

До внедрения необходимы:

- независимая мера качества;
- второй dataset;
- объяснение потолка coverage;
- проверка downstream metric stability;
- causal tests.

#### G40 §5

Публичный registry исправлен, generated `DATASET_INFO` — нет. Это открытый остаток, а
не полностью закрытый gap.

#### G47 product remainder

Explicit theme работает. Применять ли тему по умолчанию — product choice, не
correctness defect. Следует хранить отдельно от defect registry.

### 11.2. Частично закрытые

#### G32

Catalog и factory согласованы по допустимым строкам, но factory по-прежнему возвращает
нерабочий `BaseAnalyzer`. Исправлена согласованность перечней, не функциональность.

#### G17

Silent overwrite заменён warning. Overwrite остаётся намеренным поведением. Нужно
формально закрыть gap как design decision либо реализовать collision policy.

### 11.3. Устаревшие статусы

Проблемы registry hygiene:

- раздел «Открыто» содержит множество строк со статусом «исправлено»;
- G38 одновременно открыт в ограничениях 0.0.10 и исправлен в Unreleased;
- G16 описывает fields, удалённые G38;
- headers G8, G24 и G27 не синхронизированы с inventory;
- `gloswing.md` частично описывает старое поведение.

### 11.4. Предлагаемые новые gap IDs

| ID | Название | Приоритет | Связанные находки |
|---|---|---:|---|
| — | pandas 3 compatibility и dependency matrix | P0 | AQ-008 — **закрыто в тот же день как G50** (`gaps/data/g50_…`): формы переведены, сьют зелёный на 3.0.5 и 2.3.3, верхняя граница не ставится |
| G53 | Cache dependency coverage и immutable execution config | P0 | AQ-001, AQ-002, AQ-051 |
| G54 | Causal parity global/per-zone swings | P0 | AQ-003, AQ-004 |
| G55 | Validation semantics и pipeline wiring | P0/P1 | AQ-005–AQ-007, AQ-009 |
| G56 | Lossless result persistence | P1 | AQ-010, AQ-011 |
| G57 | Data contracts и validation consistency | P1 | AQ-014–AQ-020, AQ-024–AQ-026 |
| G58 | Indicator implementation parity | P1 | AQ-021–AQ-023, AQ-028 |
| G59 | Public analyzer API honesty | P2 | AQ-031, AQ-032 |

> Номера при вливании (2026-09-04) сдвинуты: в оригинале PR #117 предлагались G49–G56, но
> G49–G52 к моменту вливания уже были заняты записями того же дня (G49 — единицы
> таймфрейма, G50 — pandas 3, G51 — фабрика TA-Lib, G52 — хелпер preloaded-зон).

---

## 12. План исправлений

### Этап 1. Остановить выдачу недостоверных результатов

1. Сделать cache dependency-aware.
2. Устранить config mutation при role resolution.
3. Сделать per-zone ZigZag replay-safe.
4. Запретить silent global fallback.
5. Исправить либо временно отключить `ValidationSuite` verdicts.
6. Ограничить pandas `<3` до полного compatibility fix.

**Критерий выхода:** ни один из этих путей не может молча вернуть результат другого
алгоритма, другого набора данных или несопоставимого окна.

### Этап 2. Сделать API честным

1. Реализовать или удалить `validation=True`.
2. Нормализовать типы полей `ZoneAnalysisResult`.
3. Определить persistence levels и round-trip contracts.
4. Исправить ATR generation и normalization.
5. Исправить schemas, MT loader и preloaded boundaries.
6. Исправить `create_analyzer`.

**Критерий выхода:** принятый параметр либо действует, либо немедленно отвергается.

### Этап 3. Унифицировать расчёты

1. Один True Range и ATR.
2. Один warm-up contract.
3. Один indicator calculation path.
4. Один набор indicator analytics helpers.
5. Один registration bootstrap.
6. Один structured validation result.

**Критерий выхода:** одна именованная величина не может иметь две формулы.

### Этап 4. Восстановить слои

1. Strategy factories из `core` перенести в analysis.
2. Indicator schema из data перенести в indicators.
3. Visualization лишить вычислительных обязанностей.
4. Разделить oscillator zones и price levels.
5. Разбить god modules.

### Этап 5. Усилить доказательства

1. CI matrix minimum/latest.
2. Real-result serialization tests.
3. Cache dependency tests.
4. Per-zone replay oracle.
5. Property-based model invariants.
6. Empty, duplicate, overlap, timezone and constant-series edge cases.
7. Убрать vacuous assertions.

### Этап 6. Очистить repository

1. Синхронизировать gap statuses.
2. Обновить `tests/STATUS.md` и `tests/SKIPPED_TESTS.md`.
3. Архивировать неисполняемые zodoctests.
4. Удалить internal dead code.
5. Для public dead candidates провести deprecation cycle.

---

## 13. Предлагаемая целевая архитектура

```text
bquant/
  core/
    paths
    logging
    generic cache primitives
    exceptions

  data/
    contracts
    loader
    processor
    validation
    samples

  indicators/
    contracts
    identity_and_roles
    factory
    custom
    adapters/
      pandas_ta
      talib

  analysis/
    oscillator_zones/
      pipeline
      detection
      metrics
      swings
      sequences
      persistence
    price_levels/
    statistical/
    validation/

  visualization/
    view_models
    oscillator_zones
    price_levels
    statistical

  cli.py
```

Правила зависимостей:

```text
core <- data
core <- indicators
data + indicators <- analysis
analysis models <- visualization
all public services <- CLI
```

Запрещённые направления:

```text
core -> analysis
data -> indicator implementations
visualization -> indicator calculation
visualization -> detection registry
```

---

## 14. Что не следует делать

1. Не закрывать G48 только по росту coverage.
2. Не лечить cache collision очередным глобальным `CACHE_VERSION` без исправления
   состава key.
3. Не оставлять `validation=True` как no-op с предупреждением.
4. Не заменять structured serialization на `default=str`.
5. Не считать большее число tests доказательством качества без проверки assertions.
6. Не удалять public dead candidates только потому, что callers не найдены внутри
   repository.
7. Не объединять temporal zones и price levels ради формального DRY — это разные
   domain models.
8. Не добавлять ещё одну формулу indicator/ATR в convenience layer.
9. Не скрывать dependency incompatibility lock-файлом: заявленный диапазон обязан
   проверяться отдельно.

---

## 15. Критерии production readiness

Проект можно повторно оценивать как production-ready, когда одновременно выполнены:

1. все P0 закрыты regression tests;
2. latest supported dependencies дают green suite;
3. cache dependency matrix зелёная;
4. global и per-zone causal contracts формально определены;
5. validation verdicts сравнивают нормализованные и направленные metrics;
6. `validation=True` либо работает, либо удалён;
7. JSON/Parquet contracts не обещают больше, чем сохраняют;
8. data schemas отвергают пустые и логически невозможные OHLC;
9. public factories создают executable objects;
10. `tests/STATUS.md`, gap inventory и changelog согласованы;
11. нет unconditional fallback, меняющего алгоритм без metadata;
12. каждый public parameter имеет test, который различает его включение и выключение.

---

## 16. Заключение

Главная проблема BQuant — не отсутствие архитектуры. Центральная архитектура хорошо
продумана и содержит несколько сильных контрактов: roles, vocabularies, registries,
causal swing context и reporting filter.

Главный риск — неоднородность строгости:

- основной happy path защищён инвариантами;
- соседние публичные пути сохраняют старые silent-degradation patterns;
- тесты иногда подтверждают форму объекта вместо смысла результата;
- gap registry тщательно объясняет прошлые дефекты, но не всегда отражает текущее
  состояние.

Следующий цикл работ должен начинаться не с рефакторинга крупных файлов, а с P0:
cache correctness, causal parity, validation semantics и dependency compatibility.
Архитектурная чистка имеет смысл после того, как система перестанет молча выдавать
результаты для другого набора данных или другого алгоритма.

До этого проект следует позиционировать как **Beta research toolkit**.
