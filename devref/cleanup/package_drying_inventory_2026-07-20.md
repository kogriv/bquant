# Инвентаризация пакета bquant под сушку (OSS-подготовка)

**Дата:** 2026-07-20
**Тип:** cleanup-план / реестр (read-only инвентаризация, ничего не двигалось)
**Цель:** привести `bquant` в чистое, «сухое», пригодное для OSS состояние. Аналитика/альфа
переехали в приватную лабу `bquearch` → пакет держит только тулкит + образцовые примеры.
**Статус:** 🟡 черновик под утверждение. По каждому пункту — рекомендация; исполнять батчами
после ревью.

Легенда: 🔴 снести · 📦 в архив (`devref/archive/` или каталог-архив) · 🧪 в лабу
`bquearch` · ⭐ образец (оставить) · 🚫 gitignore + убрать из дерева · ✅ ок как есть.

---

## 0. Сводка

| Область | Файлов (tracked) | Размер | Вердикт |
|---|---|---|---|
| `test_bquant_install/` | 0 (untracked) | **818M** | 🚫 venv-инсталл в дереве, не игнорится |
| `docs/_build/` | 0 (ignored) | 34M | ✅ уже игнорится |
| `research/` | 91 | 13M | смесь: ⭐ демо (00–04) · 🧪 рисёрч (05–09) · 🔴 скретч · 🚫 артефакты |
| `devref/` | 126 | 3.4M | 27 ⭐keep · 98 📦archive · 2 🔴 |
| `output/` + `outputs/` | 59 | 5.4M | 🚫 артефакты прогонов (batch_summary, png) |
| `backup/indicators/` | 6 | 104K | 🔴 ручная копия удалённого мёртвого кода |
| `.vs/` | 3 | 1.9M | 🚫 IDE-мусор Visual Studio |
| `CLAUDE/GEMINI/VIBE.md` | 3 | — | 3 побайтно идентичных → 1 источник |
| `examples/` | 12 | 224K | ⭐ чистые нумерованные демо (оставить, верифицировать) |
| `scripts/` | 14 | 264K | смешанное, точечно |
| root clutter | ~3 | — | точечно |

Ориентир по высвобождению: из дерева ~**860M** мусора (`test_bquant_install` + артефакты),
из git-трекинга ~**8–9M** артефактов/мёртвого кода, ~**79% `devref/`** в архив.

---

## 1. Мусор и артефакты (🚫 gitignore + убрать из дерева)

| Путь | Что | Действие |
|---|---|---|
| `test_bquant_install/` (818M) | Полный venv тест-инсталла пакета, **не в git и не игнорится** | 🚫 добавить в `.gitignore`, `rm -rf` из дерева |
| `.vs/` (3 tracked) | `.vsidx`/`.wsuo`/`workspaceFileList.bin` — Visual Studio | 🚫 `git rm`, добавить `.vs/` в gitignore |
| `output/` (52 tracked) | 43 `batch_summary_*.txt` + png прогонов; gitignore уже ловит будущие, но старые закоммичены | 🚫 `git rm -r output/`, расширить ignore |
| `outputs/` (7 tracked) | Отчёты/png прогонов (дубль концепции `output/`) | 🚫 `git rm -r outputs/` |
| `research/notebooks/**/*_log.txt` (18) + `*_final.txt` | Захваченные логи прогонов | 🚫 `git rm`, ignore уже частично есть |
| `research/notebooks/outputs/**` (20) | Сгенерированные png/html/json | 🚫 `git rm -r` |
| `docs/_build/` (34M) | Сборка Sphinx | ✅ уже ignored — трогать не надо |

> Заодно: `output/` vs `outputs/` — две параллельные свалки результатов. После сноса — одна
> конвенция каталога вывода (или оба игнорятся целиком, вывод не коммитим).

---

## 2. Мёртвый код и дубли

| Путь | Действие |
|---|---|
| `backup/indicators/` (6 файлов: `base.py`, `library.py`, `loaders.py`, `macd.py`…) | 🔴 ручной бэкап уже удалённого мёртвого кода (G1). История в git. `git rm -r backup/` |
| `CLAUDE.md` = `GEMINI.md` = `VIBE.md` (md5 идентичны) | Свести к **одному источнику**: канон `CLAUDE.md`, а `GEMINI.md`/`VIBE.md` — симлинк или генерация (иначе разъедутся). Решение по механике — за тобой |
| `.cursor/rules/` (10 `.mdc`) + `.depr_rules/cursor.md` | AI-правила Cursor, пересекаются с `CLAUDE.md`. Оставить как editor-config или свести к общему источнику — отдельное решение |

---

## 3. `research/` — образцы vs рисёрч vs скретч

### ⭐ KEEP-AS-EXAMPLE (~26) — чистые демо публичного API (00–04)
`00_logging_demo.py` + `00_logging/*`, `01_data*.py` (5), `02_ind_*.py` (кроме `02_ind_lib.py`),
`03_analysis_base/statistical/new_features.py` + `03_zones_universal.py`, `04_zones_*` (3),
`notebook-style-scripts.md`.
→ **Оставить**, но `research/README.md` и `research/notebooks/README.md` **переписать**
(сейчас набиты дат-логами прогонов, читаются как артефакт). Возможно, перенести демо в
`examples/` или `docs/` (см. §6 — дубль с `examples/`).

### 🧪 MOVE-TO-LAB (~13) — альфа-рисёрч и методология (05–09)
`05_case_study_zone_consistency.py` + `05.ipynb`, `06_swing_strategy_comparison.py`,
`07_s1_swing_anatomy.py`, `08_layerA_zone_structure.py`, `09_layerA_ii_representations.py`,
`validate_swing_pivots.py`, `research/methodology/*.md` (5: macd_research, swing_structure_
research_program, method_tool_stack, bquant_analysis_pack, README), `experiments/README.md`,
`studies/README.md`.
→ Концептуально место в `bquearch`. **Важно:** сперва сверить, что они уже есть/актуальны в
лабе (не потерять); я работаю только с пакетом → перенос оформляю доком в лабу, из пакета
удаляем после подтверждения.

### 🔴 REMOVE (~13) — скретч, ad-hoc тесты, устаревшие дубли
`test_global_swing_coverage.py`, `test_legacy_fix.py`, `test_legacy_simple.py`,
`test_with_strategies.py` (тесты вне `tests/`), `swing_strategy_analysis.py`,
`swing_test_simple.py`, `bq.py` (дубль `01_data.py`), `02_ind_lib.py` (устар. → `02_ind_library.py`),
`03_analysis_zones.py` (legacy → `03_zones_universal.py`), `00_config.ipynb`, `01_data.ipynb`,
`04_zones_visualization_demo.ipynb` (ipynb-дубли .py).

### 🚫 ARTIFACT — см. §1.

---

## 4. `devref/` — 79% в архив

### ⭐ KEEP-REFERENCE (27)
- **Публикация/сборка:** `publish/publishing.md`, `build-instructions.md`, `cleanup-instructions.md`,
  `docs_update_manual.md`, `cleanup.ps1/.sh`; `cicd/eol_git_guide.md`.
- **Стратегия/гэпы (живые, 2026-07):** `architecture/revival_plan_2026-07.md`,
  `gaps/gap_inventory_2026-07.md`, `gaps/issue_indicator_consistency.md`,
  `gaps/issue_research_method_naivety_2026-07.md`, `gaps/cli-init-optimization/README.md`,
  `gaps/deffered/issue_double_timeframe_validation.md`.
- **Архитектура-канон zo:** `gaps/zo/zonan.md` (v7.1), `gaps/zo/zouni_v2.md` (v2.1),
  `gaps/zo/zomodul.md`, `gaps/zo/README.md`; numba-issues `zo/zo_issue_numba_*`.
- **Живой бэклог/дизайн:** `gaps/graph/zomet*.md` (2), `gaps/swing/{README,gloswing,multiswing,
  future_optimizations}.md`, `graph/{dense_time,plotly_yaxis_autoscale}.md`.

### 📦 ARCHIVE (98) → `devref/archive/`
- 12 `phaseX_completion_report.md` + 5 `phase*_final_summary.md`.
- 6 дат-сессий/тестинга (`SUMMARY_2025-*`, `TESTING_*`, `WEEK1_*`, `testing_coverage_analysis`).
- 7 завершённых анализов/doc-ceremony (`IMPLEMENTATION_ANALYSIS`, `impl`, `DOCUMENTATION_*`,
  `docmod`, `UNIVERSAL_ZONE_ANALYSIS`, `shape_detection`).
- 5 swing-ceremony, 5 `gaps/done/*`, 3 `gaps/logging_design/*`, 15 `gaps/zo/*` (устар. планы/аудиты),
  3 migration/future-plan снапшота.

### 🔴 REMOVE (2)
`gaps/zo/zonan_v3_backup.md` (literal backup-дубль), `gaps/zo/zouni.md` (v1.0 «УСТАРЕЛ/Отклонён»).

### ⚙️ ОСОБЫЙ СЛУЧАЙ — `gaps/zo/zodoctest/` (37 файлов): ПОДНЯТЬ В `tests/`, не в архив
`README.md` + 36 `test_*_validation.py` — валидаторы примеров документации против кода.
Сейчас осиротели (не в `tests/`, не в CI). Это **ровно та doc-parity инфраструктура**, которую
мы планируем под doc-driven → **промоутить в `tests/` и подключить к сьюту** (после починки под
текущий API), а не архивировать. Решение — за тобой; я бы сохранил как основу парити.

---

## 5. `examples/` (⭐ оставить, верифицировать)
`01`–`09` + `zone_analysis_global_swings.py` + `README.md` — чистые нумерованные демо на public
API. Оставить как основной набор примеров. Задача-хвост: прогнать их (что все запускаются на
текущем API) и снять дубль с `research/notebooks/` демо (см. §3/§6).

## 6. Развилка «examples/ vs research/notebooks 00–04»
И там и там — демо тулкита (напр. `examples/09_zones_visualization_demo.py` ↔
`research/notebooks/04_zones_visualization_demo.py`). **Один дом для примеров.** Рекомендация:
`examples/` — канон (чистый, public API), а `research/notebooks/00–04` либо консолидировать в
`examples/`, либо в `docs/` как walkthrough. `research/` в пакете после этого почти опустеет →
можно упразднить как каталог.

## 7. `scripts/` (точечно)
Оставить: `publishing/cleanup.*`, `data/{generate_samples,extract_samples}.py`. Проверить на
актуальность/дубль: `analysis/{batch_analysis,run_macd_analysis,test_hypotheses}.py`,
`data/data_loader.py`, `cloud_setup.sh`. READMEs-заглушки подчистить.

## 8. root clutter
- `SETUP_READTHEDOCS.md` (20K) → 📦 в `devref/publish/` или архив (разовая setup-инструкция).
- `zoval_check.md` (root) → матрица doc↔test (результаты zodoctest). Связать с промоушеном
  zodoctest в `tests/` (§4) или 📦 архив.
- `.git_commit_message.txt` — уже ignored, ок.
- `changelogs/` — 37 трейслогов: система нужная, оставить; старые можно позже консолидировать.

---

## 9. Порядок исполнения (батчами, каждый — отдельный PR)

1. **Батч A — мусор/артефакты (безопасно, крупный эффект):** §1 + §2 (backup, .vs) +
   gitignore-хардненинг. ~860M из дерева, ~8M из git. Риск нулевой.
2. **Батч B — `devref/` архивация:** §4 (98 → `devref/archive/`, 2 снести). Чистит корень
   разработки, ничего в коде не трогает.
3. **Батч C — `research/` сушка:** §3 REMOVE + ARTIFACT; MOVE-TO-LAB — через док в лабу.
   Консолидация демо `research↔examples` (§6).
4. **Батч D — doc-parity фундамент:** промоут `zodoctest/` → `tests/`, починка под API,
   подключение к сьюту. Это стык с твоей doc-driven/RAG-целью.
5. **Батч E — гигиена:** guides к одному источнику, G7 (зелёный сьют), `.gitattributes`
   linguist для `docs/**`, актуализация `CLAUDE.md`.

## 10. Что НЕ трогаем (anti-todo)
Кэш/логи/nb/performance (работают), формальный сплит на 3 репо, синхронная пара RU↔EN,
исходник доков (остаётся в пакете), новые process-completion-report'ы.

---

## 11. Решения, нужные от тебя (borderline)
1. `zodoctest/` (37) — поднять в `tests/` (рекоменд.) или в архив?
2. Демо-дом: `examples/` как канон + упразднить `research/` в пакете — ок?
3. `CLAUDE/GEMINI/VIBE` — механика единого источника (симлинк / генерация / просто оставить `CLAUDE.md`)?
4. MOVE-TO-LAB (05–09, methodology) — сверить наличие в `bquearch` до сноса из пакета; кто двигает?
5. `.cursor/rules` + `.depr_rules` — оставить как editor-config или свести?
