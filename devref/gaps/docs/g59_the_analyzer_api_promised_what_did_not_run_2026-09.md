# G59 — Публичный API анализаторов обещал то, что не исполнялось

**Заведён:** 2026-09-04, из аудита качества (AQ-031, AQ-032).
**Статус:** ✅ закрыт 2026-09-05 — фабрика собирает настоящие классы; каталог — только исполняемое; заглушки отказывают, а не возвращают успех.

---

## 1. Что было — замер

| Вход | Ответ было | Ответ стало |
|---|---|---|
| `create_analyzer(name)` для каждого из шести имён каталога | `BaseAnalyzer` с проставленным именем; `analyze()` → `NotImplementedError` — **все шесть** | `'statistical'` → `StatisticalAnalyzer`, `'price_levels'` → `PriceLevelAnalyzer`, оба исполняются |
| `create_analyzer('statistical').analyze(frame)` | `NotImplementedError: analyze method must be implemented in subclass` | `AnalysisResult('statistical', …)` с описательной статистикой |
| `CandlestickAnalyzer().analyze(frame)` | **успешный** `AnalysisResult`, `results` из трёх ключей, `status: 'stub_implementation'` внутри | `NotImplementedError: CandlestickAnalyzer is a stub: … Planned: …` |
| `create_analyzer('candlestick')` | `BaseAnalyzer` | `NotImplementedError: 'candlestick' is planned, not implemented` |
| `create_analyzer('zones')` | `BaseAnalyzer` | `ValueError` с указанием на `analyze_zones()` |

## 2. Почему это форма «проверка не видит проверяемого»

G32 сверил каталог с фабрикой: каждое имя каталога фабрика принимала. Сверка была
честной и недостаточной — фабрика принимала имя и возвращала объект, который не умеет
ничего; «принимает» и «собирает» — разные утверждения, и пин стоял на первом. G31 сделал
заглушки различимыми программой (`is_stub`) и оставил им успешный результат со словом
«stub» внутри: честно для того, кто заглянет в `results`, и успех для всех остальных —
та же форма, что у нуля вместо метрики.

## 3. Что сделано

- **`SUPPORTED_ANALYSIS_TYPES`** — только исполняемое: `statistical`, `price_levels`;
  каждое имя отображено на класс в `_EXECUTABLE_ANALYZERS`, и на это стоит пин.
  `'zones'` из каталога убран намеренно: анализ зон — `analyze_zones()`, не
  `BaseAnalyzer`; `PriceLevelAnalyzer` (уровни поддержки/сопротивления) — другая
  возможность и назван своим именем.
- **`PLANNED_ANALYSIS_TYPES` / `get_planned_analyzers()`** — четыре направления с
  модулем-заглушкой. Отдельный перечень, потому что «что запустить» и «что
  запланировано» — разные вопросы, и смешение их в одном словаре было дефектом.
- **`create_analyzer()`** строит класс с `kwargs` как `config`; запланированное имя —
  `NotImplementedError`, неизвестное — `ValueError` с обоими перечнями.
- **Заглушки** (`technical`, `chart`, `candlestick`, `timeseries`): `analyze()` поднимает
  `NotImplementedError`, перечисляя `PLANNED_FEATURES` — программный кортеж класса,
  читаемый без вызова. `is_stub` и суффикс «(заглушка)» в модульных перечнях остались.
  Модули не переносились (`analysis.stubs` из предложения аудита): путь — не обещание,
  обещание — успешный результат, и его больше нет.

## 4. Проверка

`tests/unit/test_the_factory_builds_what_it_lists.py` — 9 проверок: каждое имя каталога
собирается своим классом и исполняется; исполняемый и запланированный перечни не
пересекаются, второй — только `is_stub`; запланированное имя отказывает как
запланированное, `'zones'` — как неизвестное с подсказкой; каждая заглушка отказывает и
называет план; `BaseAnalyzer` абстрактен. `test_a_stub_says_so.py` перепинен с
«результат помечен stub» на «`analyze()` отказывает», в обе стороны;
`test_analysis_structure.py` — каталог из двух имён, фабрика даёт не `BaseAnalyzer`.

| Мутация | Краснеет |
|---|---|
| фабрика снова возвращает `BaseAnalyzer` | 1 |
| заглушка в исполняемом каталоге | 2 |
| запланированное имя как неизвестное | 1 |
| заглушка снова возвращает результат | 2 (сторож и пин маркера) |

## 5. Цена

- `create_analyzer('zones' | 'technical' | …)` — отказ вместо бесполезного объекта.
- `<Stub>Analyzer().analyze()` — `NotImplementedError` вместо `AnalysisResult`.
- `SUPPORTED_ANALYSIS_TYPES` — два имени вместо шести; `'price_levels'` — новое.

## 6. Чего не сделано

- `tests/STATUS.md` («Production Ready, 670 passed») — переписан 2026-09-04, до этой
  записи; в реестре упомянут под G59 как часть той же находки.
- Перенос заглушек в `analysis.stubs` — не сделан (см. §3).
