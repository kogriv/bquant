# G56 — JSON/Parquet назывались round-trip и теряли структуру

**Заведён:** 2026-09-04, из аудита качества (AQ-010, AQ-011).
**Статус:** ✅ закрыт 2026-09-04 — JSON и Parquet возвращают результат пайплайна целиком; объект в структурном поле — отказ, не строка.

---

## 1. Что было — замер

Настоящий результат пайплайна (`tv_xauusd_1h`, MACD/hist, `zigzag` в `global`, кластеры,
валидация; 77 зон), сохранён и прочитан обоими форматами:

| Что | До сохранения | JSON | Parquet |
|---|---|---|---|
| `hypothesis_tests` | `AnalysisResult`, 7 тестов | **строка** `'AnalysisResult(hypothesis_testing, 77 points, …)'` | та же строка |
| `statistics[…]['significant_difference']` | `np.False_` | **`"False"`** — строка, **истинная** | `"False"` |
| `regression_results['duration']` | `RegressionResult` | строка `repr` | строка `repr` |
| `zone.get_zone_swings()` (зона 5) | 10 точек | **0** | **0** |
| `zone.data` (зона 5) | 27 баров | пусто | пусто |
| `result.data.index` (`include_data=True`) | `DatetimeIndex`, +07:00 | **`RangeIndex`** | `DatetimeIndex` |
| `zone.start_time` | `pd.Timestamp` | `datetime` | `datetime` |

Ни один из семи отказов не был виден: файл писался, читался, `len(result.zones)` сходился.
Хуже всего вторая строка: `default=str` превращает `np.False_` в строку `"False"`, а строка
непуста — то есть после загрузки *каждое* «различие незначимо» читалось как «значимо».

## 2. Почему это форма «проверка не видит проверяемого»

Все JSON-писатели стояли на `default=str`: всё, что JSON не знает, молча становилось
строкой. `hypothesis_tests` был единственным разделом, который анализатор клал в результат
объектом, а не `.results` (у `statistics`, `sequence_analysis`, `clustering` — словарь);
`regression_results` держал объекты `RegressionResult`. Аннотации полей говорили `Dict`,
код — нет, а `default=str` прятал разницу.

Проверка сериализации (`test_zone_models.py`) подавала рукописный `dict` с
`hypothesis_tests={'test1': {...}}` и `statistics={'bull_zones': 1}` — тип, с которым
ни один из семи отказов не происходит. Она утверждала `len(loaded.zones) == 2`.

## 3. Что сделано

- **Один контракт на разделы.** Анализатор кладёт `hypothesis_tests.results` (словарь
  `tests`/`summary`) и `RegressionResult.to_dict()` — как у остальных разделов. Поле
  честно `Dict[str, Any]`; читатели `.results` (три теста, шесть страниц доков, пример,
  два рисёрч-скрипта) переведены. Попутно: `examples/02a` и `03_analysis_new_features.py`
  итерировали `tests.results.items()` — то есть по ключам `tests` и `summary`, печатая
  «tests: p=N/A».
- **`_json_default` вместо `default=str`:** `np.bool_` → `bool`, `np.integer` → `int`,
  `np.floating` → `float`, `ndarray` → список, `Timestamp`/`datetime`/`Timedelta` →
  ISO; всё остальное — `TypeError` с именем типа. Сохранение, которое стрингифицирует
  структуру, — не сохранение.
- **Свинг-контекст пишется один раз на результат** (`swing_contexts`), зона хранит номер
  своего контекста (в `global` у всех зон один объект — и после загрузки тоже один).
  `SwingContext.from_dict` восстанавливает точки с `pd.Timestamp`.
- **`zone.data` восстанавливается из `result.data`** по `start_idx:end_idx + 1` — это
  и есть его определение (проверено на всех 77 зонах); без кадра остаётся пустым, и дока
  говорит именно это.
- **Кадр в JSON** уезжает с индексом (ISO-метки, смещение сохраняется) и dtypes, а не
  `to_dict('records')`. **Parquet** возвращал индекс как `pytz.FixedOffset(420)` вместо
  `datetime.timezone(+7h)` — те же мгновения, другой объект, `DataFrame.equals` — `False`;
  имя зоны пишется в `metadata.json` и возвращается через `tz_convert`.
- Метки времени зон — `pd.Timestamp`, как до сохранения. `CACHE_VERSION` 23 → 24.

## 4. Замер после

Тот же результат, оба формата: `hypothesis_tests`, `statistics`, `clustering`,
`sequence_analysis`, `regression_results`, `validation_results`, `metadata`,
`column_schema` — равны (по канонической JSON-форме: `np.float64` против `float` и
`NaN` против `NaN` — не различие); `significant_difference` — `bool`; свинги всех зон —
те же точки, контекст один; `result.data.equals(...)` — `True`, индекс равен; `zone.data`
всех зон равны исходным; `start_time` — `Timestamp`. Объект `AnalysisResult` в
структурном поле — `TypeError: AnalysisResult cannot be written to JSON …`.

## 5. Проверка

`tests/unit/test_persistence_keeps_what_the_result_holds.py` — восемь проверок на
настоящем результате, каждая в обоих форматах: словарь тестов, булевы остаются булевыми,
все разделы, свинги и общий контекст, кадр и срезы, без кадра — пусто, но свинги есть,
объект — отказ, артефакт JSON-нативен.

| Мутация | Краснеет |
|---|---|
| `default=str` возвращён в писатели | 7: словарь тестов, булевы, разделы — оба формата; артефакт содержит `"False"` |
| `swing_contexts` не пишутся | загрузка падает (`IndexError` на номере контекста): 10 ошибок фикстуры + 1 |
| `zone.data` не восстанавливается | 2 (оба формата) |
| кадр как `records` (индекс на полу) | 1 (JSON) |
| анализатор оставляет объект `AnalysisResult` | сохранение отказывает `TypeError`: 10 ошибок фикстуры + 2 |

## 6. Цена

- `result.hypothesis_tests` — словарь; `.results['tests']` → `['tests']`.
- `result.regression_results[key]` — словарь `to_dict()`; `.r_squared` → `['r_squared']`.
- Артефакты JSON/Parquet прежней формы читаются, но `hypothesis_tests` в них — строка,
  которой уже нет чем помочь; кэш v23 не читается.

## 7. Чего не сделано

- Уровни персистентности (summary / analytical / full) из предложения аудита не введены:
  разница между уровнями сегодня — один флаг `include_data`, и он назван.
- Строгая JSON-схема артефакта не написана; контракт — «`from_dict(to_dict())` равен
  исходнику», и он проверяется на настоящем результате.
