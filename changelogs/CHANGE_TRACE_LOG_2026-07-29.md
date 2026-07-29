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

==================== COMMIT DIVIDER ====================

[codemap M8 — F8: провенанс-осознанный dead-code; закрывает шум мульти-рута; serve+query, без схемы]

[not_included] [Changed] codemap/codemap/query.py — orphan_modules(root=) фильтрует по провенанс-роуту (дефолт None = всё, обратно совместимо); новый orphan_modules_by_root() группирует. Docstring: consumer-роуты orphan по природе, root="core" изолирует настоящий dead code
[not_included] [Changed] codemap/codemap/serve/audit.py — render_dead_code разделяет: «Orphan modules — core» (сигнал, 8) и «Consumer entrypoints (orphan by nature, not dead code)» (свёрнуто по роутам с пояснением, 116); паттерн группировки как в report impact
[not_included] [Added] codemap/tests/test_m6_repo_scope.py — +2 теста (test_orphan_modules_provenance_aware, test_dead_code_report_separates_consumers); 65/65 (было 63)
[not_included] [Technical] Замер на bquant repo-scoped: было 124 orphan (94% шум), стало 8 core-кандидатов + 116 свёрнутых entrypoint'ов с дисклеймером. bquest не трогали

==================== COMMIT DIVIDER ====================

[codemap M9 — F4: вид семейства реестр+Protocol; синтез implements-рёбер; схема 0.5 → 0.6]

[not_included] [Changed] codemap/codemap/extract/dispatch.py — add_family_links(graph): Protocol'ы (наследуют typing.Protocol) × семейства (extras.registry) → implements-рёбра impl→Protocol. Матч data-driven: _match_protocol (токен семейства ⊂ имя Protocol; безтокенный регистратор — стем имени реестра, ZoneDetectionRegistry→ZoneDetectionStrategy); хардкода имён нет
[not_included] [Changed] codemap/codemap/extract/griffe_extractor.py — add_family_links после add_dispatch; codemap/model.py — SCHEMA_VERSION 0.6, Edge.type +implements
[not_included] [Changed] codemap/codemap/query.py — индекс _implements; implementers()/implements()/family_siblings()
[not_included] [Changed] codemap/codemap/cli.py — query класса печатает implements/implementers (registry family)/family siblings
[not_included] [Changed] codemap/codemap/serve/mermaid.py — classDiagram рисует implements как realization (Protocol <|.. Impl); скоуп подхватывает Protocol-цель. Семейство swing больше не пустая диаграмма
[not_included] [Changed] codemap/codemap/serve/rag.py — класс-чанк несёт neighbors implements/implementers + текст «Implements:/Implemented by:»
[not_included] [Added] codemap/tests/fixtures/dispatchpkg/base.py (ThingProtocol, структурная типизация) + codemap/tests/test_m9_family.py — 6 тестов (implements-рёбра, оба конца, family siblings, непустая диаграмма, RAG, детерминизм)
[not_included] [Changed] codemap/{BACKLOG,DESIGN}.md — M9 ✅ (§10.14/§7 обновление); gaps остаются. Замер bquant: 12 implements-рёбер (swing×3, detection×5, divergence/shape/volatility/volume ×1). query SwingCalculationStrategy → 3 implementers; query ZigZag → implements+siblings. 71/71 тестов; детерминизм; bquest не трогали

==================== COMMIT DIVIDER ====================

[codemap M10 — F3: класс-чанк агрегирует call-соседей своих методов; serve-only, без схемы]

[not_included] [Changed] codemap/codemap/serve/rag.py — _methods_calls(query, class_id): union внешних callees методов класса (сиблинг-методы отсекаются), каждый target с меткой via-метод → neighbors.calls_via_methods; _embed_text добавляет «Methods call: <target> (via <метод>)». Класс-чанк стал самодостаточным — поведение класса живёт на методах
[not_included] [Added] codemap/tests/test_m9_family.py — +1 тест test_class_chunk_aggregates_method_calls (Worker.work→run виден на классе, via-метка, текст). 72/72
[not_included] [Technical] Замер на bquant deep: MACDZoneAnalyzer класс-чанк теперь несёт 9 calls_via_methods, включая analyze_zones/detect_zones/with_indicator/build (via analyze_complete_modular) — шов делегирования deprecated→pipeline виден в чанке класса (был невидим, обкатка T4). Синергия с мостом M7 (рёбра уже на методах). bquest не трогали

==================== COMMIT DIVIDER ====================

[codemap M11 — F7: арг-контракт на call-site; смена сигнатуры теперь обслуживается; схема 0.6 → 0.7]

[not_included] [Changed] codemap/codemap/extract/behavior.py — _arg_shape(call) (позиц.счёт|None при *args, kwnames, splat) + _arg_contract(shapes) (callsites, posargs, kwargs, splat); _process_function агрегирует форму по target перед эмиссией ребра (дедуп сохранён, схлопывание видно через callsites)
[not_included] [Changed] codemap/codemap/extract/roots.py — consumer-скан тоже захватывает контракт (call_by_func map по id(func)); calls-рёбра потребителей несут ту же форму. Импорт _arg_shape/_arg_contract из behavior
[not_included] [Changed] codemap/model.py — SCHEMA_VERSION 0.7 (calls-рёбра: callsites + posargs/kwargs/splat)
[not_included] [Changed] codemap/codemap/query.py — индекс _call_in (callee→[(caller,extras)]); Query.call_contract(symbol) отдаёт по-вызывающему форму (только behavioral-рёбра, мост пропускается)
[not_included] [Changed] codemap/codemap/serve/impact.py — секция «Call-site contract (N sites — for signature change)»: по вызывающему posargs/kwargs/+splat, дисклеймер
[not_included] [Added] codemap/tests/fixtures/argpkg (api.configure + callers: positional/kwargs/2-site/splat) + codemap/tests/test_m11_argcontract.py — 5 тестов (форма, схлопнутые сайты видны ×2, splat флаг, секция impact, детерминизм)
[not_included] [Technical] Замер на bquant repo-scoped: report impact get_indicator_params → секция контракта: MACD.__init__ ×1, examples ×2 (было схлопнуто в «examples 1»), tests ×1 — все «1 positional, kwargs —». Рефактор видит ломкие сайты. НЕ потолок резолва — рёбра разрешены. 77/77; bquest не трогали

==================== COMMIT DIVIDER ====================

[codemap M12 — F6: dataflow по строковым ключам (колонки датафрейма); схема 0.7 → 0.8]

[not_included] [Added] codemap/codemap/extract/dataflow.py — add_dataflow(graph, root, pkg): проход по функциям, string-keyed subscript'ы (df['k']) → column-узел (column:<key>) + рёбра writes (ctx Store) / reads (ctx Load); dict-литерал-ключи {'k':…} → writes (продюсер). Embedded-датасеты (samples.embedded) исключены. Честность: over-set строковых ключей (dict-доступ тоже), запрос конкретного ключа точен
[not_included] [Changed] codemap/codemap/extract/griffe_extractor.py — add_dataflow после add_family_links; codemap/model.py — SCHEMA_VERSION 0.8, kind +column, Edge.type +reads/+writes
[not_included] [Changed] codemap/codemap/query.py — индексы _col_writers/_col_readers; Query.column(name)→{writes,reads}, columns()
[not_included] [Changed] codemap/codemap/cli.py — query <col> печатает «string-key dataflow: written by / read by»; exit-код учитывает column
[not_included] [Changed] codemap/tests/test_m0_api_surface.py — инвариант contains-дерева уточнён на узлы-определения (overlay doc/column вне дерева)
[not_included] [Added] codemap/tests/fixtures/flowpkg (продюсер dict-литерал + subscript-write, потребитель subscript-read) + codemap/tests/test_m12_dataflow.py — 6 тестов (продюсер↔потребитель, subscript-write продюсер, неизвестный ключ None, список колонок, embedded, детерминизм)
[not_included] [Technical] Замер на bquant: 1007 column-узлов / 2381 reads-writes рёбер. query macd_hist → written by bquant.indicators.custom.macd.MACD.calculate; read by extract_zone_features + 4 визуализатора (было — query давал пусто, F6). Топ-ключи = словарь колонок (close/macd/macd_hist/volume/high/low). 83/83; детерминизм; bquest не трогали

==================== COMMIT DIVIDER ====================

[codemap — финализация findings глубокой обкатки: все F3/F4/F6/F7/F8 закрыты вехами M8–M12; docs-only]

[included] [Changed] codemap/gaps/deep_dogfood_2026-07-29.md — §6 сводка: статусы всех 5 находок → ✅ закрыт с привязкой к вехе (F8/M8, F4/M9, F3/M10, F7/M11, F6/M12); блок «Итог реализации» (схема 0.5→0.8, тесты 57→83, порядок дёшево×ценно)
[included] [Changed] codemap/gaps/README.md — строка deep_dogfood: все 5 закрыты M8–M12; дата 2026-07-29; вехи M0–M12
[included] [Changed] codemap/BACKLOG.md — статус-шапка M0…M12 (было M0…M7)
[not_included] [Technical] Итог дня: обкатка (план+прогон, 2 docs-коммита) → реализация 5 вех M8–M12 (5 фича-коммитов). Схема 0.5→0.8. Тесты 57→83, детерминизм в каждой вехе. Кода bquant не трогали; bquest не трогали; секреты не трогали
