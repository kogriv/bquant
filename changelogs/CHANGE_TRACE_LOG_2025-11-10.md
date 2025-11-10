[09:12:05] [not_included] [Added] Добавлены структуры SwingPoint и SwingContext в bquant/analysis/zones/models.py для хранения глобальных свингов с сериализацией и neighbor-aware slice.
[09:18:47] [not_included] [Technical] Создан ZoneAnalysisCache (bquant/analysis/zones/cache.py) с версионированием CACHE_VERSION=2, стабильными hash-ключами и автоматической инвалидацией устаревших результатов.
[09:24:30] [not_included] [Changed] ZoneAnalysisPipeline (bquant/analysis/zones/pipeline.py) расширен swing_scope='global', добавлен расчёт и инъекция SwingContext, обновлены cache-wrapper и builder.with_swing_scope().
[09:30:12] [not_included] [Changed] Документ devref/gaps/swing/gloswing.md обновлён: зафиксированы выполненные задачи Фазы 1, описаны глобальные свинги и статус проверки памяти.
[09:32:10] [not_included] [Changed] SwingCalculationStrategy protocol (bquant/analysis/zones/strategies/base.py) расширен методами calculate_global/aggregate_for_zone, docstrings обновлены.
[09:32:44] [not_included] [Changed] Глобальные стратегии ZigZag/FindPeaks/PivotPoints обновлены: calculate_global, aggregate_for_zone и единая `_aggregate_metrics()` реализованы с новым API.
[09:33:05] [not_included] [Changed] Адаптивный враппер перенесён в bquant/analysis/zones/strategies/swing/thresholds.py: добавлен `_global_threshold_cache`, поддержаны глобальные пороги; pipeline импорт обновлён.
[09:33:28] [not_included] [Changed] Документ devref/gaps/swing/gloswing.md (Фаза 2) — отмечены выполненные чекбоксы, зафиксированы результаты тестов и ограничения mypy.
[09:33:46] [not_included] [Test] Выполнены smoke-тесты: ZigZag.calculate_global (4 точки), aggregate_for_zone (1 свинг), FindPeaks.calculate_global (8 точек), PivotPoints.calculate_global (0 точек на синтетических данных). 【b599f1†L4-L4】【624104†L4-L5】【49e347†L1-L2】【1e7579†L4-L5】
[10:15:02] [not_included] [Docs] Обновлён devref/gaps/swing/gloswing.md: отмечен runtime_checkable для протокола и добавлен комментарий к невыполненному прогону mypy.
[08:28:05] [not_included] [Changed] ZoneAnalysisPipeline (bquant/analysis/zones/pipeline.py) дополнен глобальным расчётом: добавлены `_calculate_global_swings`, `_inject_swing_context`, обновлён `_run_without_cache` и builder.with_swing_scope().
[08:28:37] [not_included] [Docs] devref/gaps/swing/gloswing.md — чеклисты Фазы 3 помечены с комментариями, зафиксированы результаты тестов и статус validation.
[08:29:10] [not_included] [Test] Выполнены smoke-тесты пайплайна: глобальный режим, per_zone режим и fallback без стратегии подтверждают логирование и сохранение контекста. 【726fdf†L1-L96】【b783e6†L1-L40】
[08:43:30] [not_included] [Changed] ZoneFeaturesAnalyzer (bquant/analysis/zones/zone_features.py) обновлён для поддержки swing_context: добавлены ветки global/per_zone, temp_zone и маркировка режима в metadata.
[08:43:30] [not_included] [Docs] devref/gaps/swing/gloswing.md — чеклисты Фазы 4 заполнены с комментариями о реализации и подготовке к интеграционным тестам.
[08:43:30] [not_included] [Test] Smoke-скрипт подтвердил ветвление ZoneFeaturesAnalyzer: режимы per_zone/global и обработка исключений фиксируют swing_calculation_mode и fallback. 【9a5c13†L1-L21】
[09:12:21] [not_included] [Test] Выполнены pytest тесты глобальных свингов (unit/integration/performance) и сравнение coverage, все чекпоинты Фазы 5 зелёные. 【237dfc†L1-L15】【79565f†L1-L3】【695908†L1-L89】
[09:14:33] [not_included] [Test] Повторно прогнаны pytest unit/integration/performance сценарии Фазы 5 и research-скрипт coverage, подтверждены зелёные статусы чеклистов. 【354ab6†L2-L16】【13e762†L1-L88】
[15:42:18] [not_included] [Changed] Закрыты пробелы Фазы 5: параметризованы unit/edge-тесты по стратегиям и добавлен pytest-сценарий автоматической проверки coverage (`tests/unit/test_swing_global_calculation.py`, `tests/unit/test_swing_edge_cases.py`, `tests/integration/test_pipeline_global_swings.py`), обновлён чеклист в `devref/gaps/swing/gloswing.md`.
[15:55:03] [not_included] [Docs] Выполнен пункт 6.1.1: docstrings и inline-комментарии новых API приведены к английскому стилю в `bquant/analysis/zones/models.py`, `bquant/analysis/zones/pipeline.py`; статус зафиксирован в `devref/gaps/swing/gloswing.md`.
[16:18:42] [not_included] [Docs] Реализован пункт 6.1.3: добавлено русскоязычное руководство `docs/migration/global_swings_migration.md` (метрики 18.9/8.1/62.2 → 70–90%, шаги миграции, FAQ) и обновлён `devref/gaps/swing/gloswing.md` отметкой о выполнении.
[16:39:11] [not_included] [Docs] Выполнен пункт 6.2.1: `docs/user_guide/zone_analysis.md` дополнен разделом Global vs Per-Zone Swing Calculation, создано новое руководство `docs/user_guide/swing_strategies.md`, статус зафиксирован в `devref/gaps/swing/gloswing.md`.
[17:05:44] [not_included] [Docs] Реализован пункт 6.2.2: добавлены `docs/api/analysis/zones/{models,pipeline,strategies}.md`, обновлены ссылки в API-README и отмечен прогресс в `devref/gaps/swing/gloswing.md`.

[18:24:05] [not_included] [Docs] Обновлён `research/notebooks/05_case_study_zone_consistency.py`: сравнение режимов per_zone/global, графики покрытия и обновлённые выводы в NotebookSimulator.
[18:24:37] [not_included] [Docs] Создан `research/notebooks/06_swing_strategy_comparison.py` с бенчмарками стратегий, итоговыми таблицами и рекомендациями; прогресс отражён в `devref/gaps/swing/gloswing.md`.

[13:30:12] [not_included] [Docs] Реализован пункт 6.2.4: добавлен пример `examples/zone_analysis_global_swings.py` (coverage сравнение, предпросмотр пивотов, график), прогресс отмечен в gloswing.md.

==================== COMMIT DIVIDER ====================
[14:52:58] [not_included] [Docs] Добавлен отчёт `docs/analytics/zones/swing_strategy_comparison_case_study.md` по запуску 06_swing_strategy_comparison.py (--no-trap), зафиксированы метрики покрытия и рекомендации.
