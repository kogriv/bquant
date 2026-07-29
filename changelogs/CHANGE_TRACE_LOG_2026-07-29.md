# Change Trace Log — 2026-07-29

[codemap — глубокая обкатка (5 осей): план с предрегистрированными гипотезами; docs-only, кода не трогали]

[included] [Added] codemap/gaps/deep_dogfood_2026-07-29.md — план глубокой обкатки на 5 непокрытых осях (contract/exemplar T1, dataflow по строковому ключу T2, change-set reasoning T3, RAG-самодостаточность T4, reachability/dead-code после M7 T5). Таксономия гэпов по причине (Extraction/Representation/Query-surface/Precision). Гипотезы H1…H5 записаны ДО прогона (falsifiable). Конфиг: repo-scoped full+deep, каждая задача только через codemap, где нужен grep — гэп. §5–§6 (результаты/findings F6+) заполняются по прогону
[included] [Changed] codemap/gaps/README.md — строка deep_dogfood_2026-07-29, назначение (5 осей, H1…H5)
[not_included] [Technical] Мотивация: две прошлые обкатки одноосевые, каждая нашла 1 гэп (F1→M6, F5→M7). Эта перебирает архетипы вопросов, не нагруженные ранее. Спайк-скрипты пойдут в scratchpad, bquest не трогаем. Сначала фиксируем план (этот коммит), потом прогон

==================== COMMIT DIVIDER ====================

[codemap — глубокая обкатка: прогон 5 осей на repo-scoped full+deep графе; 3 новых гэпа + 2 подтверждения; docs-only]

[not_included] [Technical] Прогон на едином графе (repo-scoped full --deep, схема 0.5, 3210 узлов/7542 ребра, ~56с). Каждая из 5 задач решалась только через codemap, где нужен grep — фиксировался гэп; всё сверено с исходником
[not_included] [Technical] T1 contract/exemplar → F4 подтверждён и РАСШИРЕН (Query-surface): семейство swing (12 registry-узлов + контракт-методы Protocol SwingCalculationStrategy через contains + RAG-текст «Registered as») ПОЛНОСТЬЮ в графе, но не собирается ниоткуда — query с обоих концов пусто (Protocol не наследуется), mermaid class пустой. ИИ «добавь стратегию» уходит в grep при наличии всех данных
[not_included] [Technical] T2 dataflow строк.ключ macd_hist → F6 НОВЫЙ (Extraction): колонка (grep 47 употреблений, producer→consumers) невидима целиком — 0 узлов/рёбер/extras, query пусто, RAG-текст 0 попаданий (хуже grep). Эмпирика к отложенному CM-10 value-level dataflow
[not_included] [Technical] T3 change-set get_indicator_params → F7 НОВЫЙ (Representation+Precision): report impact даёт вызывающие функции, но calls-рёбра несут только resolution (0 про арность/kwargs); call-sites схлопнуты до функции (examples/01 rsi+macd 2→1). Смену сигнатуры не обслуживает — и это НЕ потолок резолва, а выбор модели
[not_included] [Technical] T4 RAG MACDZoneAnalyzer → F3 подтверждён точно (Representation): function-чанки несут neighbors.calls (extract_zone_features→compute-методы через мост M7), но класс-чанк максимум bases/subclasses (69/285), у MACDZoneAnalyzer вообще нет neighbors; шов делегирования в pipeline (analyze_zones) застрял на метод-чанке analyze_complete_modular, невидим в класс-чанке
[not_included] [Technical] T5 dead-code после M7 → H5(M7) ОПРОВЕРГНУТА честно (регресса нет: ZigZag 52 входящих calls, registry-стратегии живые через мост); но вскрыт F8 НОВЫЙ (Representation) на оси M6: report dead-code даёт 124 orphan-модуля, 94% (116/124) — consumer-entrypoint'ы (tests 75/examples 11/research 24/scripts 6), orphan по природе; отчёт не провенанс-осознан
[included] [Changed] codemap/gaps/deep_dogfood_2026-07-29.md — §5 результаты T1…T5 (данные, вердикты, категории, фиксы), §6 сводка-таблица findings + приоритизация (F8→F4→F3→F7→F6 по дёшево×ценно)
[included] [Changed] codemap/BACKLOG.md — блок «Кандидаты из глубокой обкатки 2026-07-29» (F8/F4/F3/F7/F6, каждый с категорией и формой фикса; не блокеры)
[included] [Changed] codemap/gaps/README.md — строка deep_dogfood обновлена итогом (3 новых + 2 подтверждения + опровержение)
[not_included] [Technical] Кода тула НЕ трогали — только документация findings. Спайк-скрипты и граф в scratchpad, в репо не тащили; bquest не трогали
