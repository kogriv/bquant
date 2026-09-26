# Change Trace Log — 2026-09-26

[Разбор предупреждений полного прогона: заведены G83–G86]

[not_included] [Technical] Условия: чистый `uv sync --extra dev` по `uv.lock`, Python 3.12.3, pandas 2.3.3, scikit-learn 1.8.0, plotly 6.3.0, kaleido 1.0.0. Полный сьют — **3643 passed / 34 skipped**, 0 failed, 249–298 с. Все 34 пропуска — `test_scripts_parity.py:171` («script does not use pyplot»), пропуск по назначению
[not_included] [Technical] **92 предупреждения, разложены по источникам:** 85 — `datetime.utcnow()` в `zones/cache.py:223` (G83); 3 — `FutureWarning` pandas в `sequence_analysis.py:293` (G84); 3 — `DeprecationWarning` об `engine` из `plotly/io/_kaleido.py` (G85); 1 — намеренный, пример декоратора устаревания в `docs/api/core/utils.md:119`
[not_included] [Technical] **G83 — отметка кэша по UTC без пояса.** Не просто устаревший вызов: `created_at` — единственная из 28 отметок пакета по UTC, остальные 27 (`datetime.now()`) местные, и все выглядят одинаково. Поле в пакете не читается, на вычисления не влияет
[not_included] [Technical] **G84 — предупреждение pandas оказалось симптомом.** Замером через пайплайн: у RSI-зон (32) `line_amplitude` пуст во всех, кластеризация заполняла его нулём, называла в `features_used` и выдавала `feature_importance = 0.0`; у MACD-зон (77) он заполнен, важность 1.2727. Регрессия по той же колонке (G23) выбрасывает её громко — два соседних анализа обращаются с одной колонкой по-разному. Метки кластеров при этом не страдают: совпадение поэлементное при текущем и будущем поведении pandas
[not_included] [Technical] **G84, побочно — частично пустой признак.** `correlation_price_oscillator` пуст у 20/32 RSI и 15/77 MACD зон (зоны в 1–2 бара) и тоже становится нулём, а это на метки уже влияет. Записано открытым вопросом о методе, в правку не входит
[not_included] [Technical] **G85 — первичный диагноз был неверен, и я сказал его владельцу вслух.** «Пример передаёт устаревший `engine`» — неправда: `export.py` его не передаёт, plotly 6.x подставляет `engine="auto"` сам и сам на него предупреждает. Воспроизведено без BQuant на 6.3.0, 6.3.1, 6.4.0, 6.5.0; на 7.1.0 параметра нет. Поправлено в записи, а не молча
[not_included] [Technical] **G85, по дороге — plotly 7.** 452 теста визуализации на plotly 7.1.0 зелёные. Но PNG на 7.1.0 при нашем `kaleido` 1.0.0 падает внутри библиотеки (`Chromium.get_cli() received invalid args`): plotly 7.1 требует `kaleido>=1.3.0`, мы объявляем `>=1.0.0`. Правка `pyproject.toml` сдвигает кандидата — уходит в релизную подготовку, как состав `full` 2026-09-12
[not_included] [Technical] **G86 — найден проверкой G85, а не предупреждением.** `save_figure(prefer="png")` на всех трёх проверенных парах plotly/kaleido вернул `.html` молча: `except Exception` выбрасывал причину. Три разные причины (нет Chrome ×2, несовместимость версий ×1) снаружи неотличимы. Откат задокументирован и остаётся, теряется только причина

[included] [Added] `devref/gaps/cache/g83_the_cache_stamp_was_utc_and_did_not_say_so_2026-09.md`
[included] [Added] `devref/gaps/sequence/g84_clustering_counted_an_empty_feature_as_zero_2026-09.md`
[included] [Added] `devref/gaps/visualization/g85_the_engine_warning_is_plotly_s_own_2026-09.md`
[included] [Added] `devref/gaps/visualization/g86_save_figure_fell_back_to_html_without_a_word_2026-09.md`
[included] [Changed] `devref/gaps/gap_inventory_2026-07.md` — строки G83–G86 (🟠) и отметка даты в шапке раздела открытых

[not_included] [Technical] **Кандидат на релиз.** Этот коммит лежит в `devref/` и `changelogs/`, вне дистрибутива. Правки G83, G84 и G86 трогают `bquant/`, то есть сдвинут кандидата `8d77a55`, когда попадут в `main`. Делаются на ветке; решение о слиянии и о сообщении потребителю — за владельцем

---

[ОЖИДАНИЯ] Выписаны 2026-09-26 до правок G83, G84, G86 и до прогона. Предмет: полный сьют и замеры G84 после правки. Сверка — следующим блоком.

[not_included] [Technical] **Обязано измениться (1/4).** Предупреждений в полном прогоне: `utcnow` 85 → **0**; `FutureWarning` pandas 3 → **0**; всего 92 → **4** (3 от plotly — G85, не наш аргумент; 1 намеренный из `utils.md`). Число собранных тестов растёт ровно на число новых тестовых функций плюс по одному на каждый новый файл тестов (сторож молчаливых пропусков параметризован по файлам) плюс проверки, которые доковые сторожа добавят на новые блоки и ссылки; дельта объясняется без остатка
[not_included] [Technical] **Обязано остаться (2/4).** Ни один из 3643 прежде проходивших тестов не краснеет; пропусков — 34. На RSI-зонах (`tv_xauusd_1h`, RSI-14, 70/30, 32 зоны) метки кластеров поэлементно те же, что до правки. На MACD-зонах (77) `features_used` — те же 7 признаков с `line_amplitude`, `feature_importance['line_amplitude']` = 1.2727 (до 4 знаков)
[not_included] [Technical] **Отказ обязан прозвучать (3/4).** RSI-кластеризация пишет `WARNING` с именем `line_amplitude` и кладёт его в `empty_features`; кластеризация по одним пустым признакам — `AnalysisError` со списком; `save_figure(prefer="png")` в этом окружении пишет `WARNING` с текстом исключения kaleido («Kaleido requires Google Chrome»)
[not_included] [Technical] **Положительный контроль (4/4).** Пункт 1 проваливается на пустой правке (останется 92). Каждый новый сторож краснеет на откате своей правки — мутации по одной на гэп, откат мутации копией файла, а не `git checkout` (урок 2026-09-12)

[СВЕРКА] Прогон после правок G83, G84, G86, 2026-09-26. Все четыре пункта сошлись; сюрпризов в предмете нет.

[not_included] [Technical] **1/4 обязано измениться — сошлось.** Предупреждений 92 → **4**: `utcnow` 85 → 0, `FutureWarning` 3 → 0, plotly 3 (G85, не наш аргумент), намеренный 1 из `utils.md`. Сьют **3643 → 3656 passed / 34 skipped**; дельта +13 объяснена точно: 10 новых тестовых функций (2 + 5 + 3) и +3 от сторожа молчаливых пропусков, параметризованного по файлам тестов (три новых файла). Доковые сторожа не добавили ничего: новых python-блоков и ссылок в правке нет. 13 = 13, остатка нет
[not_included] [Technical] **2/4 обязано остаться — сошлось.** Прежние 3643 зелёные, пропусков 34, все по той же причине. RSI (32 зоны): метки кластеров поэлементно равны прежнему расчёту (сверка — проверка сторожа, прежний расчёт воспроизведён в тесте). MACD (77 зон): те же 7 признаков, `feature_importance['line_amplitude']` = 1.2726624, как до правки
[not_included] [Technical] **3/4 отказ обязан прозвучать — сошлось.** RSI-кластеризация: `WARNING … Dropping clustering feature(s) … line_amplitude`, имя в `empty_features`; одни пустые признаки → `AnalysisError: … Every clustering feature is empty … ['line_amplitude']`; `save_figure(prefer="png")` в этом окружении → `WARNING … PNG export of 'probe' failed, saved as HTML instead: RuntimeError: Kaleido requires Google Chrome to be installed.`
[not_included] [Technical] **4/4 положительный контроль — сошлось.** Пустая правка оставила бы 92 предупреждения. Мутации, откат каждой копией файла: G83 `utcnow()` — 2/2 красные; G84 полный откат — 4/5, откат только отбрасывания — 3/5 (зелёными остаются сверка меток и контроль MACD, то есть ровно то, что правка менять не должна); G86 без записи в лог — 1/3, ровно проверка причины
[not_included] [Technical] **Вне предмета, замечено:** на RSI-зонах пайплайн пишет `ERROR … Sequence hypothesis test failed: Need at least 2 different transition types, got 0 from 0 adjacent zone pairs`. У пороговых зон нет примыкающих пар, и отказ громкий и с причиной. Так было и до правки (проверено на `git stash`), к G84 не относится
[not_included] [Technical] **Мой промах:** первый сторож G84 ловил `WARNING` через `caplog` на корневом логгере и покраснел на исправленном коде. Логгеры пакета настроены с `propagate=False`, в `test_a_swing_strategy_that_finds_nothing_says_so.py` это уже было записано. Обработчик теперь вешается на логгер анализатора

[included] [Fixed] `bquant/analysis/zones/cache.py` — G83: `created_at` через `datetime.now(timezone.utc)`; `CACHE_VERSION` 28 → 29 ради G84
[included] [Fixed] `bquant/analysis/zones/sequence_analysis.py` — G84: пустой во всех зонах признак исключается с `WARNING` и `empty_features` (в `clustering_summary` и `metadata`), все пусты — `AnalysisError`, приведение к `float` до `fillna`
[included] [Fixed] `bquant/visualization/export.py` — G86: откат PNG → HTML пишет `WARNING` с типом и текстом исключения; докстрока об этом
[included] [Added] `tests/unit/test_the_cache_stamp_names_its_zone.py` (2), `tests/unit/test_clustering_does_not_count_an_empty_feature.py` (5), `tests/unit/test_save_figure_says_why_it_fell_back.py` (3)
[included] [Changed] `docs/api/analysis/pipeline.md`, `docs/user_guide/zone_analysis_result.md` — `empty_features` у кластеризации; `CHANGELOG.md` [Unreleased] — G83, G84 (с `Ломает:`), G86
[included] [Changed] `devref/gaps/gap_inventory_2026-07.md` и записи G83, G84, G86 — ✅ с тем, что сделано и чем проверено. G85 остаётся 🟠 по границе `kaleido`

[not_included] [Technical] **Кандидат на релиз:** правки в `bquant/` лежат на ветке. Попав в `main`, они сдвинут кандидата `8d77a55` и поднимут `CACHE_VERSION`: это сообщение потребителю (issue №15), и одно из изменений ломающее по форме (`feature_importance` без `line_amplitude` у зон без линии). Решение о слиянии — за владельцем

==================== COMMIT DIVIDER ====================
