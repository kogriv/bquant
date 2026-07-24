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
