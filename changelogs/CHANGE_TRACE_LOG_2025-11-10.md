[09:12:05] [not_included] [Added] Добавлены структуры SwingPoint и SwingContext в bquant/analysis/zones/models.py для хранения глобальных свингов с сериализацией и neighbor-aware slice.
[09:18:47] [not_included] [Technical] Создан ZoneAnalysisCache (bquant/analysis/zones/cache.py) с версионированием CACHE_VERSION=2, стабильными hash-ключами и автоматической инвалидацией устаревших результатов.
[09:24:30] [not_included] [Changed] ZoneAnalysisPipeline (bquant/analysis/zones/pipeline.py) расширен swing_scope='global', добавлен расчёт и инъекция SwingContext, обновлены cache-wrapper и builder.with_swing_scope().
[09:30:12] [not_included] [Changed] Документ devref/gaps/swing/gloswing.md обновлён: зафиксированы выполненные задачи Фазы 1, описаны глобальные свинги и статус проверки памяти.
[09:32:10] [not_included] [Changed] SwingCalculationStrategy protocol (bquant/analysis/zones/strategies/base.py) расширен методами calculate_global/aggregate_for_zone, docstrings обновлены.
[09:32:44] [not_included] [Changed] Глобальные стратегии ZigZag/FindPeaks/PivotPoints обновлены: calculate_global, aggregate_for_zone и единая `_aggregate_metrics()` реализованы с новым API.
[09:33:05] [not_included] [Changed] Адаптивный враппер перенесён в bquant/analysis/zones/strategies/swing/thresholds.py: добавлен `_global_threshold_cache`, поддержаны глобальные пороги; pipeline импорт обновлён.
[09:33:28] [not_included] [Changed] Документ devref/gaps/swing/gloswing.md (Фаза 2) — отмечены выполненные чекбоксы, зафиксированы результаты тестов и ограничения mypy.
[09:33:46] [not_included] [Test] Выполнены smoke-тесты: ZigZag.calculate_global (4 точки), aggregate_for_zone (1 свинг), FindPeaks.calculate_global (8 точек), PivotPoints.calculate_global (0 точек на синтетических данных). 【b599f1†L4-L4】【624104†L4-L5】【49e347†L1-L2】【1e7579†L4-L5】
==================== COMMIT DIVIDER ====================
[10:15:02] [not_included] [Docs] Обновлён devref/gaps/swing/gloswing.md: отмечен runtime_checkable для протокола и добавлен комментарий к невыполненному прогону mypy.
[08:28:05] [not_included] [Changed] ZoneAnalysisPipeline (bquant/analysis/zones/pipeline.py) дополнен глобальным расчётом: добавлены `_calculate_global_swings`, `_inject_swing_context`, обновлён `_run_without_cache` и builder.with_swing_scope().
[08:28:37] [not_included] [Docs] devref/gaps/swing/gloswing.md — чеклисты Фазы 3 помечены с комментариями, зафиксированы результаты тестов и статус validation.
[08:29:10] [not_included] [Test] Выполнены smoke-тесты пайплайна: глобальный режим, per_zone режим и fallback без стратегии подтверждают логирование и сохранение контекста. 【726fdf†L1-L96】【b783e6†L1-L40】
