# BQuant `docs/` — структурный аудит (D0)

**Дата:** 2026-07-22
**Тип:** read-only карта + находки (исполнение — отдельными шагами, с согласия)
**Родитель:** `devref/cleanup/oss_readiness_plan_2026-07.md` (Батч D, шаг D0)
**Метод:** сверка `index.rst` toctree ↔ факт (детерминированно) + веерное чтение 4 кластеров.
**Важно:** это аудит *организации* контента (дубли / разнесение / сироты), НЕ аудит парити
(запускаются ли примеры — это D1). Ни один файл не изменён.

---

## 0. Карта источника (без `_build/`)

```
docs/
  index.rst            toctree (задуманная IA) + placeholder-ссылки your-username/bquant
  README.md            META: как собирать Sphinx (корректно вне toctree)
  BUILD_ISSUES.md      DEV-SCRATCH: лог сборки, внутренне противоречив (см. G)
  conf.py, Makefile
  api/            (~18 файлов, 8941 стр) — reference
  user_guide/     (9 файлов) — how-to/reference (RU+EN)
  tutorials/      (5 файлов) — сценарные прогоны
  developer_guide/(5 файлов) — dev + 1 методология
  analytics/zones/(6 файлов) — 1 usage-doc + 5 research
  migration/      (2 файла) — исторические
  examples/       README.md — каталог скриптов (дубль корневого examples/README.md)
  _build/         34M артефакт сборки В GIT → Батч A
```

Язык: **весь источник = RU-проза + EN-код** (mixed, RU-доминантный). Чистого EN нет,
кроме `analytics/zones/swing.md`. Это подтверждает locked-решение «англ. как цель,
инкрементально» — переводить придётся почти всё, но не сейчас.

---

## A. Сироты (детерминированно: в источнике есть, в toctree/сборке — нет)

| Файл | Что это | Действие |
|---|---|---|
| `analytics/zones/layerA_ii_representations_case_study.md` (68) | lab research (DTW/catch22/ARI) | → лаба |
| `analytics/zones/layerA_zone_structure_case_study.md` (73) | lab research (Layer A классы) | → лаба |
| `analytics/zones/s1_swing_anatomy_case_study.md` (127) | lab research (анатомия свингов) | → лаба |
| `user_guide/zone_analysis_result.md` (443) | **НЕ протухший** — глубже/актуальнее по result-объекту | → **подключить в toctree**, не удалять |

Первые три — «Отчёт по `research/notebooks/...`», ссылаются на приватную
`research/methodology/...`, тянут tslearn/pycatch22/pyts. Однозначно материал `bquearch`.

`zone_analysis_result.md` — важная тонкость: сирота ≠ протухший. Документирует
`to_dict()/save()/to_analyzer_format()/SwingPoint`, согласован с текущим API-инвариантом
(«у `ZoneInfo` нет `.metadata`, метаданные в `zone.features['metadata']`»). Это
**навигационный пробел**, лечится добавлением в toctree.

---

## B. Research/методология в доках пакета (MOVE-TO-LAB кандидаты)

Аналитика/альфа уехали в `bquearch` → эти доки в публичном пакете лишние:

| Файл | В toctree? | Природа |
|---|---|---|
| `analytics/zones/macd_zone_consistency_case_study.md` (64) | да | датированный отчёт H0/H1, p-values, «Переоценка 2026-07» |
| `analytics/zones/swing_strategy_comparison_case_study.md` (31) | да | датированный отчёт coverage/runtime |
| `analytics/zones/layerA_*`, `s1_swing_anatomy` (×3) | нет (сироты) | lab research (см. A) |
| `developer_guide/analytical_philosophy.md` (55) | **да** | философия «состоятельности зон» + карта идей исследований — материал лабы |
| `user_guide/swing_analysis_results.md` (341) | да | датированный (2025-10-28) отчёт по 1 прогону MACD+ZigZag + wishlist; тип не совпадает с соседями |

**Не двигать (keep):**
- `analytics/zones/swing.md` (64) — **мисфайл**: лежит в `analytics/`, но это usage-doc
  (пресеты + adaptive thresholds), чистый EN, с рабочим кодом. → перенести в `user_guide/`,
  НЕ в лабу.
- `developer_guide/statistical_analysis_workflow.md` (69) — пограничный, но оформлен как
  package how-to со ссылкой на публичный `api/analysis/statistical.md`. Слабый кандидат, keep.

**Побочка (C3 в лабе):** case studies + `developer_guide/zone_analyzer_deep_dive.md` +
`analytics/zones/swing.md` содержат ссылки в приватные `research/methodology/...` и
`research/notebooks/...` — при переносе research они **повиснут**. Чинить при переносе.

---

## C. Дубли внутри живого набора

**C1. Кластер `api/analysis/` — общий builder-API + одинаковые сниппеты размазаны по 4+ файлам.**
`pipeline.md` (375) ↔ `zones.md` (436) ↔ `strategies.md` (833) ↔ `README.md` (412):
один и тот же fluent-блок `analyze_zones()...build()` повторён в каждом; `zones.md`
дублирует `ZoneAnalysisBuilder` из `pipeline.md`.

**C2. Коллизии имён между уровнями** (одна тема, два файла — сильная путаница):
- `api/analysis/pipeline.md` (полный) vs `api/analysis/zones/pipeline.md` (85, только
  global-swing). Оба про `ZoneAnalysisPipeline`. `with_swing_scope()` есть только во втором →
  **ни один не полон в одиночку.**
- `api/analysis/strategies.md` (833, метрик-стратегии) vs `api/analysis/zones/strategies.md`
  (60, `SwingCalculationStrategy`). Разный контент, но **у обоих H1 = `bquant.analysis.zones.strategies`**.

**C3. Повторяющиеся блоки контента:**
- 23-полевой список SwingMetrics — в `zone_analysis.md`, `zone_analysis_result.md`,
  `swing_analysis_results.md`.
- Дерево артефактов `results/{instr}_{tf}/01_…08_` — в `best_practices.md` и `zone_analysis_result.md`.

**C4. Два каталога примеров:** `docs/examples/README.md` (17.7K) и корневой
`examples/README.md` (9K) — оба описывают один набор скриптов. Плюс `tutorials/README.md`
в шапке пересказывает тот же набор третий раз.

**C5. `tutorials/` ↔ `user_guide/`:** `tutorials/macd_basic_pipeline.md` (87) — сжатый
субсет `user_guide/zone_analysis.md` (701). Осознанное «краткий walkthrough vs полный»,
но покрытие пересекается; migration-доки считают `zone_analysis.md` каноном.

---

## D. Парити-красный флаг (мост к D1) — устаревший API прямо в доке

**`user_guide/swing_strategies.md` (139) описывает НЕсуществующий/старый API:**
- `.with_swing_strategy(...)`, `.with_auto_swing_thresholds(True)`, `zone.get_zone_swings(strategy='zigzag')`,
  `ZoneInfo.metadata['swing_scope']`.
- Текущий API (по `zone_analysis.md`/`zone_analysis_result.md`): `.with_strategies(swing=...)`,
  `.with_swing_preset(...)`, `get_zone_swings()` без аргумента, у `ZoneInfo` **нет** `.metadata`.

Это ровно то, что должен ловить doc-parity тест. Т.е. D1 не абстрактен — уже виден первый
кейс, где живой валидатор покраснел бы. Фикс = коррекция доки (или её реструктуризация).

---

## E. Стабы / неполнота
- `api/data/schemas.md` (38) — самоназван «заготовка».
- `api/analysis/base.md` — отмечает, что `create_analyzer` возвращает stub.
- `tutorials/README.md` — «future tutorials» TODO-блок + aspirational треки (Quick/Deep/Advanced),
  которых нет файлами.

---

## F. Мисплейсменты (не туда разнесено)
- `analytics/zones/swing.md` → `user_guide/` (usage, не analytics). [дубль пункта B]
- `user_guide/swing_analysis_results.md` → тип «отчёт», не reference; в лабу/архив. [дубль B]
- `api/analysis/pipeline.md` и `api/analysis/strategies.md` документируют члены пакета
  `bquant.analysis.zones`, но лежат **уровнем выше** `api/analysis/zones/`, где та же тема.
- `api/extension_guide.md` (1238) — это how-to guide, не reference; сидит в `api/`.

---

## G. Мета/скрэтч, трекнутые в `docs/`
- `docs/README.md` — build-мета (корректно вне toctree, keep как contributor-doc).
- `docs/BUILD_ISSUES.md` (260) — dev-scratch лог сборки; **внутренне противоречив**
  (статусы «в процессе» при таблице «56 файлов ✅ работает»); самоназван служебным. → архив/убрать из docs.
- `docs/_build/` — 34M артефакт в git → **Батч A** (gitignore + `git rm --cached`).

## H. Прочее
- `migration/MIGRATION_v2.md` (84) + `migration/global_swings_migration.md` (80) — исторические,
  архивируемы после снятия deprecated MACDZoneAnalyzer / старого кэша. Пока keep (ещё актуальны).
- `index.rst` — placeholder-ссылки `github.com/your-username/bquant` (стр. 145,146,152) → на реальный repo.

---

## Итог: как это меняет D1 (ответ на исходный вопрос владельца)

Аудит доков **до** парити-аудита оправдан — состав/число валидаторов D1 меняется:

1. **Сжатие scope.** Валидаторы, целящие в B-контент (analytics/case studies, philosophy,
   swing_analysis_results) — уезжают вместе с контентом в лабу. D1 их не касается.
2. **Схлопывание дублей.** Валидаторы на повторённые сниппеты (C1/C3) коллапсируют после дедупа —
   нет смысла упрочнять тест на снипет, который станет одним.
3. **Готовый парити-кейс.** D (swing_strategies.md) — уже найденное расхождение доки с API;
   D1 подтвердит инструментально, но правка — это доккоррекция.

Т.е. порядок правильный: **сначала устаканить структуру (что остаётся, где живёт, без дублей) →
потом D1 против устоявшегося набора.**

---

## Предлагаемая декомпозиция исполнения (на обсуждение, ничего не делаем без согласия)

- **DOC-1 (навигация, риск~0):** добавить `zone_analysis_result.md` в toctree; починить
  placeholder-ссылки в `index.rst`. Чистый выигрыш, обратимо.
- **DOC-2 (research → лаба):** сверить наличие B-файлов в `bquearch`, разместить в лабе
  недостающее, затем `git rm` из пакета + починить повисшие ссылки. Согласуется с C3 Батча C.
- **DOC-3 (мисфайлы):** `analytics/zones/swing.md` → `user_guide/`; решить судьбу `analytics/`
  каталога (пустеет ли он полностью).
- **DOC-4 (дедуп `api/analysis/`):** развести коллизии `pipeline.md`/`strategies.md`, свести
  повторённые builder-сниппеты к одному источнику + ссылки. Самый крупный, отдельным заходом.
- **DOC-5 (мета/скрэтч):** `BUILD_ISSUES.md` → архив; `docs/_build/` → Батч A.
- **→ D1:** парити 37 валидаторов против устоявшегося набора.

*Живой документ. Обновлять по мере исполнения DOC-1..5 и D1.*
