# Change Trace Log — 2026-07-29

[codemap — глубокая обкатка (5 осей): план с предрегистрированными гипотезами; docs-only, кода не трогали]

[included] [Added] codemap/gaps/deep_dogfood_2026-07-29.md — план глубокой обкатки на 5 непокрытых осях (contract/exemplar T1, dataflow по строковому ключу T2, change-set reasoning T3, RAG-самодостаточность T4, reachability/dead-code после M7 T5). Таксономия гэпов по причине (Extraction/Representation/Query-surface/Precision). Гипотезы H1…H5 записаны ДО прогона (falsifiable). Конфиг: repo-scoped full+deep, каждая задача только через codemap, где нужен grep — гэп. §5–§6 (результаты/findings F6+) заполняются по прогону
[included] [Changed] codemap/gaps/README.md — строка deep_dogfood_2026-07-29, назначение (5 осей, H1…H5)
[not_included] [Technical] Мотивация: две прошлые обкатки одноосевые, каждая нашла 1 гэп (F1→M6, F5→M7). Эта перебирает архетипы вопросов, не нагруженные ранее. Спайк-скрипты пойдут в scratchpad, bquest не трогаем. Сначала фиксируем план (этот коммит), потом прогон
