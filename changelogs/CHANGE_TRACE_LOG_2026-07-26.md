# Change Trace Log — 2026-07-26

[Мерж PR #109 — гэп-док покрытия codemap (сторонний Cursor-агент)]

[not_included] [Technical] PR #109 (DRAFT, ветка cursor/codemap-coverage-gapdoc-8cb4, Cursor-агент) — docs-only, +658/−1; база ровно d42ebda (текущий main) → fast-forward, ноль конфликтов
[not_included] [Technical] Верификация перед мержем: статистика графа в доке (1709 узлов / 2428 рёбер, 89/126/863/631, contains 1708 / export 479 / imports 241) точно совпала с живым прогоном; тезис «расхождение дизайн↔код» по inherits/decorated_by подтверждён — DESIGN §2 (стр.75-77) и §10.3 (стр.302) перечисляют их как v1-рёбра структурного уровня, но M0/M1 их не эмитили
[included] [Added] codemap/gaps/coverage_gap_analysis_2026-07-24.md (614 строк) + gaps/README.md — исчерпывающий гэп-анализ M0+M1: структурное vs семантическое покрытие, матрица сущностей/связей, 14 гэпов CM-01…CM-14, case study ZoneAnalysisResult и Universal Pipeline, риски переоценки graph.json, DoD полного покрытия
[included] [Changed] devref/gaps/gap_inventory_2026-07.md — запись G13; codemap/{README,BACKLOG,DESIGN}.md — кросс-ссылки + layout
[not_included] [Technical] Мерж ff, push origin (GitHub+GitLab) → оба зеркала на 1136af6; PR #109 закрылся как MERGED, ветка удалена на github, tracking-рефы подчищены

==================== COMMIT DIVIDER ====================

[codemap M1.5 — семантические рёбра: закрытие «быстрых wins» гэп-дока §11.1; схема 0.1 → 0.2]

[not_included] [Changed] codemap/model.py — SCHEMA_VERSION 0.2 (новые рёбра + обогащённые extras); extras остаётся открытой сумкой нейтрального ядра, новых полей Node/Edge не добавлено
[not_included] [Changed] codemap/extract/griffe_extractor.py — эмит inherits (класс→база; b.canonical_path резолвит абсолютно, внешние базы abc.ABC помечаются extras.external) и decorated_by (символ→callable_path декоратора); _extras() кладёт annotation атрибутов (str(obj.annotation) → "List[ZoneInfo]"), is_dataclass классов, и _registry_binding() парсит @Registry.register('key') из ExprCall.arguments[0] → extras.registry {decorator,key}
[not_included] [Changed] codemap/query.py — bases/subclasses (DiGraph по inherits) + decorated_with (по full-path или короткому имени)
[not_included] [Changed] codemap/cli.py — codemap query для класс-матча выводит bases/subclasses (json + text)
[not_included] [Added] codemap/tests/test_m1_5_semantics.py — 10 тестов: inherits внутр/внешн, subclasses/bases, decorated_by (deprecated, dataclass), annotation, is_dataclass, registry-key, детерминизм, схема 0.2
[not_included] [Technical] Прогон на bquant: 52 inherits (41 внутр / 11 внешн), 165 decorated_by; 23/23 теста зелены (6 M0 + 7 M1 + 10 M1.5); детерминизм держится
[not_included] [Changed] codemap/DESIGN.md §2.2 — пример схемы 0.2 (узлы с extras.annotation/registry, рёбра inherits/decorated_by); codemap/BACKLOG.md — веха M1.5 ✅, статус M0+M1+M1.5, M2.3 mermaid classDiagram разблокирован
[not_included] [Changed] codemap/gaps/coverage_gap_analysis_2026-07-24.md — баннер обновления M1.5, статусы CM-01/02/06/07/08 = закрыты в таблице §10 и матрице §6.2; devref/gaps/gap_inventory_2026-07.md — G13 → 🟡 частично
[not_included] [Technical] Осталось отложенным по дизайну §7: CM-09 call-graph, CM-10 data-flow, CM-11 локали; открыты CM-05 (import module→symbol), CM-12/13 (symbol dead-code, entry points), CM-14 (external-узлы)
