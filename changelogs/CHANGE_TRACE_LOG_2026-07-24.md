# Change Trace Log — 2026-07-24

[E5 — гигиена веток и PR/issue-трекера; новый пункт Батча E в oss_readiness_plan_2026-07.md]

[not_included] [Technical] Синхронизация: локальный main == origin/main == gitlab/main == 4b17640, расхождений нет; fetch --prune подчистил два смёрдженных claude/* из origin
[not_included] [Technical] Аудит трекера: issues — 0 (ни одного, ни в каком состоянии); PR — 2 открытых, оба протухшие codex-хвосты
[not_included] [Removed] Закрыт без мержа PR #48 «Log stage 2.2 analysis README validation» (2025-10-26) — 0 изменённых файлов, 0 строк (прогон zodoctest не был закоммичен)
[not_included] [Removed] Закрыт без мержа PR #93 «Log swing regression checks in trace log» (2025-11-06) — документирует запуск research/notebooks/validate_swing_pivots.py, удалённого в C2 (01448a0); его же секция Testing фиксирует оба прогона упавшими (ModuleNotFoundError: pandas); экспорты в outputs/reports/, заигноренный в C1. Мерж внёс бы мёртвую ссылку в devref/gaps/swing/README.md
[not_included] [Technical] Верификация перед удалением веток: origin 105 веток (99 codex/* + 4 claude/*), из них 97 — прямые ancestor-ы main; оставшиеся 6 разобраны поштучно
[not_included] [Technical] Ветка claude/review-devref-gaps-graph-* = PR #104 MERGED (squash-мерж, потому не ancestor); claude/add-zomet-testing-* (1c108a1) — дерево идентично смёрдженному a92bcb8 (git diff пуст); claude/analyze-repository-* (259876d) — добавляет output/batch/*.txt, т.е. ровно артефакты, вычищенные в Батче A и заигноренные; три codex/* — ветки закрытых PR #93/#48/#56
[not_included] [Removed] Удалено 103 ветки на origin (GitHub) — осталась только main; бэкап типов сохранён перед операцией
[not_included] [Removed] Удалены 2 ветки claude/swing* на gitlab (смёрджены как PR #107/#108) и локальная claude/swing-confirmation-index-findpeaks-pivots (upstream исчез)
[not_included] [Technical] Итог: GitHub и GitLab держат по одной ветке main; открытых PR и issues нет
[not_included] [Changed] devref/cleanup/oss_readiness_plan_2026-07.md — добавлен пункт E5 в §6, запись в §8; скоуп D1 расширен: висящая ссылка на validate_swing_pivots.py найдена не только в docs/analytics/zones/swing.md:63, но и в живом devref/gaps/swing/README.md:30,39 (в devref/archive/gaps/swing/* не трогаем — исторические документы)
[not_included] [Technical] Напоминание: confirmation_index (PR #108) лежит в main непаблишенным — ждёт релиза 0.0.3, после которого пингануть лабу

==================== COMMIT DIVIDER ====================

[Bugfix регрессии сборки сьюта + E2/G7 — вскрыто фоновым прогоном полного сьюта во время планирования параллелизма]

[included] [Fixed] Регрессия сборки: C2 (01448a0) удалил research/notebooks/test_global_swing_coverage.py, но из него импортировался compare_swing_coverage в живом tests/integration/test_pipeline_global_swings.py → весь сьют падал на collection с этого коммита (уехало в main). Восстановлен как tests/fixtures/swing_coverage.py (истинное место — тест-инфраструктура на базе tests.fixtures, не research-скретч), импорт перецелен. Коммит 6f7c64e
[included] [Fixed] G7 (3 красных теста test_pandas_ta_dynamic_loader.py) — две первопричины: (1) порядок-зависимость: другие модули ставят BQUANT_SKIP_PANDAS_TA=1 через os.environ.setdefault (процесс-глобально) → в полном сьюте load_all_libraries() скипал pandas_ta и возвращал {}; фикстура теперь delenv-ит переменную; (2) дрейф лог-уровня: 2e8c4de намеренно понизил info→debug для quiet-init, а тест патчил logger.info; патчи переведены на logger.debug. Коммит 1200cc3
[included] [Technical] Полный сьют: 735 passed, 12 skipped, 0 failed (было: 3 failed / вообще не собирался). Впервые зелёный с момента C2. E2 закрыт
[not_included] [Technical] Изолированный прогон test_pandas_ta_dynamic_loader.py маскировал баг (3/3 pass) — фейл проявляется только в порядке полного сьюта (env-утечка). Урок: при удалении «скретча» в C2 надо было грепнуть tests/ на импорты research.notebooks.*

==================== COMMIT DIVIDER ====================

[DOC-4 — дедуп api/analysis, развязка коллизий, фикс toctree; полный объём по решению владельца «правильно и полноценно»]

[included] [Changed] Переименованы docs/api/analysis/zones/{models,pipeline,strategies}.md → zones/global_swings_*.md (git mv, история сохранена), H1 двух переклеймливающих файлов исправлены (выдавали себя за весь модуль, покрывая лишь global-swing срез). Сняты коллизии basename+неймспейс с верхними pipeline.md/strategies.md
[included] [Added] index.rst: 7 сирот api/analysis подключены в toctree (pipeline, zones, strategies, statistical + 3 global_swings_*). Orphan-warnings по api/analysis: 7→0
[included] [Changed] zones.md: дубль списка методов ZoneAnalysisBuilder схлопнут в указатель на канон pipeline.md (модели данных ZoneAnalysisResult/ZoneInfo оставлены — профиль zones.md); починены 2 ссылки ../developer_guide → ../../ (всплыли при вводе в toctree)
[included] [Added] pipeline.md: добавлен отсутствовавший метод .with_swing_scope() в канонический справочник билдера (есть в коде pipeline.py:600)
[included] [Changed] strategies.md: 5 устаревших протокол-блоков переписаны по коду (strategies/base.py + конкретные реализации): Swing→calculate_global/aggregate_for_zone/calculate; Shape/Divergence indicator_col обязателен; Volume+indicator_col; убран фиктивный get_name() (0 реализаций)
[included] [Technical] Верификация Sphinx-сборкой (8.2.3): build succeeded, warnings 79→70, orphans 24→17 (−7 = ровно эти страницы); новых предупреждений не внесено (2 битые ссылки zones.md, всплывшие из-за toctree, тут же починены)
[not_included] [Technical] Граница DOC-4/D1 удержана: правил только структуру + корректность ВНУТРИ тронутых файлов. Вне скоупа (флаги): сироты api/{core,data,indicators,visualization} (тот же класс, др. каталоги); сами Protocol-défs в base.py расходятся с реализациями (код-сайд парити → D1); отсутствие myst_heading_anchors ломает кросс-док якоря глобально (пре-существующее)
[not_included] [Files Modified] Коммит c90f5c6 (11 файлов docs/: 3 rename + README/pipeline/zones/strategies/index.rst + 2 H1-правки)

==================== COMMIT DIVIDER ====================

[D1 — парити: свинг-реконсиляция (часть A) + триаж 37 валидаторов zodoctest (часть B)]

[included] [Changed] D1-A: user_guide/swing_strategies.md переписан в корректный канон (весь API сверен с bquant/analysis/zones/): .with_strategies(swing=...), реальные параметры стратегий (zigzag legs/deviation, find_peaks prominence/distance, pivot_points left/right_bars), .with_swing_preset('default'|'narrow_zone'), .with_auto_swing_thresholds, .with_swing_scope, get_zone_swings() без аргументов, метрики через zone.features['metadata']['swing_metrics']. Сломанный was: with_swing_strategy() (не существует) + выдуманные threshold/backstep/retrace, min_bars/max_bars/sensitivity, get_zone_swings(strategy=), ZoneInfo.metadata
[included] [Removed] D1-A: analytics/zones/swing.md влит в канон и удалён (+ toctree); analytics/ держит comparison-case-study
[included] [Changed] D1-A: devref/gaps/swing/README.md — вычищены висящие ссылки на удалённый (C2) validate_swing_pivots.py и на архивный strat_issue.md; указатель на живой smoke-тест. Коммит 8bce9db
[included] [Technical] D1-B: прогон всех 36 валидаторов zodoctest — 26 зелёных / 10 падений, каждое диагностировано (TRIAGE_2026-07-24.md)
[included] [Fixed] D1-B: 2 реальных бага доки, пойманных валидаторами: strategies.md ссылалась на devref/gaps/swing_detection_approaches.md (уехал в archive) → путь + стейл-хардкод в test_strategies_validation.py (7/7); user_guide/README.md линковал ../MIGRATION_v2.md → ../migration/MIGRATION_v2.md
[not_included] [Technical] D1-B ключевой вывод: «поднять все 37» не выдержала — часть валидаторов env-зависимы (sphinx-build/pip), один тестит умирающий legacy-код (int-duration баг в ZoneAnalyzer, удаление в v3.0.0), несколько завязаны на pandas_ta zigzag (нет в окружении). D2 = курируемое подмножество ~20–24, конвертация в pytest
[not_included] [Technical] D1-B флаг (код, не дока): ZigZag-свинг-стратегия падает без pandas_ta zigzag — реальные примеры не выполняются, тесты сьюта зелены только на моке swing_mocks. Кандидат в robustness-тикет
[not_included] [Files Modified] Коммиты 8bce9db (D1-A) + 0bd80de (D1-B)

==================== COMMIT DIVIDER ====================

[D2 — промоушен парити в tests/: авто-сканирующий сьют вместо портирования 20+ протухающих валидаторов]

[included] [Added] tests/unit/test_docs_parity.py — портируемый авто-сканирующий парити-сьют: (1) все локальные file-ссылки в docs/**/*.md резолвятся (285); (2) каждый `from bquant... import ...` из python-блоков доков резолвится в модуль+символ (107). Итого 393 проверки, зелены. Без sphinx-build/pip/pandas_ta (в отличие от zodoctest-валидаторов)
[included] [Fixed] D2 разбор падений: реальный баг viz-README — plot_zone_detail/plot_zones_comparison/plot_zones_on_price_chart получали сырой data (без macd_hist) → KeyError; починено на result.data (обогащён индикатором, zones.md уже так делал)
[included] [Fixed] D2 12 битых markdown-ссылок неверной глубины: MIGRATION_v2→user_guide (×2), extension_guide→api-README (×4), strategies/pipeline→research/examples .py (×6). Плюс 1 backtick-регрессия DOC-4: global_swings_migration → zones/models.md → global_swings_models.md
[included] [Technical] Sphinx build: warnings 69→57 (−12 = починенные ссылки), orphans 17 (др. каталоги, вне D2). Парити-сьют 393 passed
[not_included] [Technical] D2 разбор: example-скрипты (02_macd — здоров, ложное срабатывание на «Traceback» в логах; 03_zones_universal — EOFError на интерактивном nb.wait в headless = инвокация; readme/strategies_demo — pandas_ta zigzag env). Валидаторы zodoctest оставлены как ручные инструменты (проверяют sphinx-build/исполнение, что портируемый сьют осознанно не покрывает); авторитетная CI-парити = test_docs_parity.py
[not_included] [Technical] Инженерное решение D2: не портировать хардкод-валидаторы (протухают — см. archival-path drift D1), а авто-сканировать живые доки → покрывает и будущие доки, ноль хардкода

==================== COMMIT DIVIDER ====================

[E4 — актуализация AGENTS.md под реальность; финальный этап OSS-плана]

[included] [Changed] AGENTS.md сверен с кодом и обновлён: indicators/library.py → пакет library/ (manager/pandas_ta/talib); macd.py MACDZoneAnalyzer помечен deprecated (v3.0.0, делегирует в analyze_zones); analysis/zones/ переписан как Universal Pipeline v2.1 (analyze_zones builder, detection/+strategies/+models/presets) вместо «sequence analysis, feature extraction»
[included] [Added] AGENTS.md: флагманский паттерн Universal Zone Analysis Pipeline первым в Key Design Patterns (пример сверен и исполняется end-to-end, 72 зоны) + раздел Documentation Parity с указанием на tests/unit/test_docs_parity.py
[included] [Technical] Все пути в AGENTS.md проверены на существование; pipeline-пример прогнан (Zones: 72, result.data содержит macd_hist). CLAUDE/GEMINI/VIBE.md подхватят через @AGENTS.md-импорт
[not_included] [Files Modified] Коммит 62b6909. OSS-план завершён: остались только опциональные флаги (0.0.3 релиз; robustness-тикеты; сироты api/*; myst_heading_anchors)

==================== COMMIT DIVIDER ====================

[Хвосты (опциональные флаги вне плана): навигация/якоря доков + ZigZag robustness. 0.0.3 НЕ трогаем (отложен владельцем)]

[included] [Added] index.rst: 17 сирот api/{core,data,indicators,visualization} подключены в toctree (были доступны только через README-хабы). Sphinx orphans 17→0
[included] [Changed] conf.py: myst_heading_anchors=4 — кросс-док и in-page якорные ссылки file.md#slug резолвятся (часть целей были h4-заголовки без авто-якоря)
[included] [Fixed] стейл-якоря: 3 ссылки на удалённый заголовок «Управление логированием» → #модульная-настройка; убраны литеральные {#logging} из 3 заголовков (рендерились как текст, MyST не регистрировал) → одна входящая ссылка на авто-slug #логирование. Sphinx warnings 57→32 (остаток — намеренные ссылки на директории/repo-файлы + косметика header-level/highlighting). Коммит 11094f7
[included] [Fixed] ZigZag robustness: calculate_global() зависел от опционального pandas-ta zigzag без обёртки → при отсутствии индикатора бросал (пайплайн ловил фолбэком в per_zone, но с шумным ERROR+traceback). Обёрнут в try/except → чистый WARNING + пустой SwingContext, как в per-zone calculate(). Регресс-тест test_zigzag_global_degrades_when_pandas_ta_zigzag_unavailable
[not_included] [Technical] Проверено: zigzag+global+skip pandas_ta → 72 зоны, graceful, без краша. Остаточный ERROR из IndicatorFactory.create правдив (создание правда упало), WARNING поясняет обработку; пре-чек ненадёжен в skip-сценарии, не делаем

==================== COMMIT DIVIDER ====================

[Релиз bquant 0.0.3 на боевой PyPI]

[included] [Changed] Бамп версии 0.0.2 → 0.0.3 в pyproject.toml + bquant/__init__.py (версия в 2 местах)
[included] [Added] CHANGELOG.md секция [0.0.3] - 2026-07-24: Added confirmation_index для find_peaks/pivot_points (было ZigZag-only в 0.0.2); Changed CACHE_SCHEMA_VERSION 2→3; Fixed ZigZag graceful degradation без pandas-ta zigzag
[included] [Technical] Прогон pytest перед релизом: 1129 passed, 12 skipped, 0 failed
[included] [Technical] Чистая сборка dist/bquant-0.0.3.{tar.gz,whl} (venv_bquant -m build); twine check PASSED для обоих; confirmation_index присутствует в wheel (find_peaks+pivot_points)
[included] [Files Modified] Коммит c7c1bc1 + аннотированный тег v0.0.3; пуш main+тег на origin (GitHub) и gitlab
[included] [Added] Публикация bquant 0.0.3 на боевой PyPI (twine upload); подтверждено: simple-индекс содержит whl+tar.gz, страница версии 200 — https://pypi.org/project/bquant/0.0.3/
[not_included] [Technical] Напоминание: пингануть лабу (bquearch) о релизе 0.0.3 — causal confirmation_index теперь для всех свинг-стратегий

==================== COMMIT DIVIDER ====================

[Смена стратегической рамки: пакет = самостоятельный фундамент, лаба по запросу. Закрытие старого плана + новая конвенция/роадмап]

[included] [Changed] revival_plan_2026-07.md ЗАКРЫТ/суперседед: его главная ось (#1 поиск альфы) уехала в лабу, обслуживающая ось (#3/#4) выполнена как OSS-уборка+0.0.3. Добавлен блок закрытия с указанием на новые доки
[included] [Added] devref/architecture/package_charter.md — durable-конвенция (хартия): что такое пакет / чем не является / отношения с лабой (только по явному запросу) / north-star / рабочие конвенции (трейслоги, doc-parity, релиз, AGENTS.md)
[included] [Added] devref/architecture/package_roadmap_2026-07.md — живой роадмап (черновик): где мы, честная оценка north-star по готовности (доки-как-продукт есть фундамент; граф+RAG greenfield), предлагаемые стадии P1(доки-как-продукт)/P2(граф+RAG)/P3(DX) + 6 решений для конкретизации
[not_included] [Technical] Развилка зафиксирована владельцем: «пакет как аккуратный фундамент», лабу обслуживаем только по явному запросу. Приоритет перевёрнут: бывшее «обслуживание» стало основной работой пакета

==================== COMMIT DIVIDER ====================

[Дизайн-фаза codemap (P1): strawman-дизайн продукта перед разработкой]

[included] [Added] codemap/DESIGN.md — тщательный strawman-дизайн (v0.1) статического анализатора кода: §1 каталог запросов от 3 потребителей (дока-как-продукт / CLI-AI-RAG / аудит) как краеугольная спека; §2 модель графа (узлы/рёбра/атрибуты); §3 вход (ast, без импорта рантайма); §4 канонический JSON-стор → много рендеров (query/отчёты/диаграммы/RAG-экспорт); §5 конвейер Extract→Build→Store→Serve с плагин-экстракторами; §6 CLI+API; §7 границы v1; §8 тонкий срез M0 (API-поверхность bquant); §9 структура каталога; §10 открытые вопросы
[included] [Added] codemap/README.md — что это, статус (стадия дизайна, кода нет), зачем изолирован, прицел на вынос в отдельный репо
[included] [Changed] roadmap: починен устаревший пример dead-code (base_old.py/library.py-тень уже вычищены)
[not_included] [Technical] Подтверждено: упаковка whitelist include=["bquant*"] → codemap/ авто-исключён из wheel (0.0.3 wheel = только bquant), правок конфига не нужно. Дизайн заземлён на факты bquant: 63 модуля, слоёный __all__ (analyze_zones не в top-level), удалённые dead-code кандидаты

==================== COMMIT DIVIDER ====================

[Гэп-док codemap: полнота покрытия кода bquant (M0+M1)]

[not_included] [Added] codemap/gaps/README.md — индекс гэпов подпроекта codemap
[not_included] [Added] codemap/gaps/coverage_gap_analysis_2026-07-24.md — исчерпывающий гэп-анализ: структурное vs семантическое покрытие, матрица сущностей/связей, 14 гэпов CM-01…CM-14, case study ZoneAnalysisResult и Universal Pipeline, риски переоценки, DoD полного покрытия; эмпирика graph.json (1709 узлов, 2428 рёбер)
[not_included] [Changed] devref/gaps/gap_inventory_2026-07.md — запись G13 (codemap semantic coverage)
[not_included] [Changed] codemap/README.md, codemap/BACKLOG.md — ссылки на codemap/gaps/
