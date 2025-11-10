[09:12:05] [not_included] [Added] Добавлены структуры SwingPoint и SwingContext в bquant/analysis/zones/models.py для хранения глобальных свингов с сериализацией и neighbor-aware slice.
[09:18:47] [not_included] [Technical] Создан ZoneAnalysisCache (bquant/analysis/zones/cache.py) с версионированием CACHE_VERSION=2, стабильными hash-ключами и автоматической инвалидацией устаревших результатов.
[09:24:30] [not_included] [Changed] ZoneAnalysisPipeline (bquant/analysis/zones/pipeline.py) расширен swing_scope='global', добавлен расчёт и инъекция SwingContext, обновлены cache-wrapper и builder.with_swing_scope().
[09:30:12] [not_included] [Changed] Документ devref/gaps/swing/gloswing.md обновлён: зафиксированы выполненные задачи Фазы 1, описаны глобальные свинги и статус проверки памяти.
==================== COMMIT DIVIDER ====================
