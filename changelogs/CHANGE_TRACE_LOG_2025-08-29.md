[15:07:12] [not_included] [Fixed] Дополнен docs/api/data/README_gaps.md: добавлены упущенные несоответствия (параметр add_tech_features, недокументированная create_lagged_features, наличие get_data_statistics и convert_to_list_of_dicts, алиас load_sample_data, предопределенные схемы OHLCV_SCHEMA/MACD_SCHEMA/RSI_SCHEMA), уточнено поведение load_all_data_files (без рекурсии).
[15:07:12] [not_included] [Changed] Уточнено покрытие генератора: отмечено, что SampleDataGenerator упомянут в docs/api/data/README.md (список возможностей) и подробно показан в bquant/data/samples/README.md; рекомендовано добавить раздел/ссылку в docs/api/data.
[15:07:12] [not_included] [Files Modified] docs/api/data/README_gaps.md
[16:25:40] [not_included] [Fixed] Приведена в соответствие документация: обновлен docs/api/data/README.md (исправлены имена функций и параметры, корректные примеры импорта/вызовов, добавлены функции create_lagged_features, get_data_statistics, convert_to_list_of_dicts; убраны несуществующие DataLoader/DataProcessor/DataValidator; исправлены вызовы валидации на dict-доступ; уточнено поведение load_all_data_files).
[16:25:40] [not_included] [Changed] Навигация по generator: добавлен раздел «Генератор Sample данных» в docs/api/data/README.md с примером использования SampleDataGenerator.
[16:25:40] [not_included] [Files Modified] docs/api/data/README.md
[16:25:40] [not_included] [Technical] Перенесен файл README_gaps.md из docs/api/data/ в devref/gaps/done/README_gaps.md.
[16:44:22] [not_included] [Added] Создан docs/api/data/samples.md — перенесена полная документация sample‑данных из модульного README.
[16:44:22] [not_included] [Changed] Сокращен bquant/data/samples/README.md до короткой ссылки на docs/api/data/samples.md, чтобы исключить дублирование.
[16:44:22] [not_included] [Files Modified] docs/api/data/samples.md; bquant/data/samples/README.md; docs/api/data/README.md
[16:55:10] [not_included] [Changed] Приведен docs/README.md к роли "Quick Start"; оставлены краткие инструкции по установке зависимостей, сборке и просмотру, добавлена ссылка на подробный гайд SETUP_READTHEDOCS.md
[16:55:25] [not_included] [Changed] Обновлен SETUP_READTHEDOCS.md: добавлен TL;DR с командами, закреплен единый источник зависимостей (extras `docs`), безопасная автогенерация API в docs/api/autogen, четкие шаги по версионированию и сборке на Read the Docs, уточнения по PDF/ePub
[16:55:40] [not_included] [Technical] Синхронизирована версия пакета: bquant/__init__.py __version__ обновлен до 0.0.1 в соответствии с pyproject.toml и docs/conf.py
[16:55:55] [not_included] [Technical] Удален дублирующий файл requirements-docs.txt; источник зависимостей для документации — extras `docs` в pyproject.toml
[16:56:10] [not_included] [Files Modified] docs/README.md; SETUP_READTHEDOCS.md; bquant/__init__.py; (удалено) requirements-docs.txt
[17:02:20] [not_included] [Technical] Уточнены правила ведения трэйслогов: один файл на дату, при наличии файла — дописывать записи; обновлен changelogs/README.md
[17:02:30] [not_included] [Files Modified] changelogs/README.md; changelogs/CHANGE_TRACE_LOG_2025-08-29.md
[17:15:05] [not_included] [Changed] Обновлен SETUP_READTHEDOCS.md: основной поток — ручные API страницы без автогенерации; выделен отдельный опциональный блок про автоген с плюсами/минусами и краткими шагами; убран блок про PDF/ePub
[17:15:05] [not_included] [Files Modified] SETUP_READTHEDOCS.md
[17:25:10] [not_included] [Fixed] Исправлены битые ссылки в docs/api/README.md: ссылки на подпапки заменены на явные файлы README.md (core/data/indicators/analysis/visualization), а также поправлены межразделные ссылки на README.md
[17:25:10] [not_included] [Files Modified] docs/api/README.md
[17:25:25] [not_included] [Added] Добавлен мануал по обновлению документации: devref/publish/docs_update_manual.md
[17:25:25] [not_included] [Files Modified] devref/publish/docs_update_manual.md
[17:33:40] [not_included] [Fixed] Исправлены ссылки в docs/user_guide/README.md: заменены на существующие страницы API (core/data/indicators/visualization/analysis) и README.md в смежных разделах; обновлено требование Python до 3.11+
[17:33:40] [not_included] [Files Modified] docs/user_guide/README.md
[17:45:10] [not_included] [Added] Созданы страницы модулей ядра API: docs/api/core/config.md; exceptions.md; logging.md; performance.md; utils.md — на основе анализа кода
[17:45:10] [not_included] [Changed] Обновлены ссылки в docs/api/core/README.md на смежные разделы (README.md)
[17:45:10] [not_included] [Files Modified] docs/api/core/README.md; docs/api/core/config.md; docs/api/core/exceptions.md; docs/api/core/logging.md; docs/api/core/performance.md; docs/api/core/utils.md
[17:58:20] [not_included] [Added] Созданы страницы модулей анализа: docs/api/analysis/base.md; statistical.md; zones.md. Обновлены ссылки и тексты в docs/api/analysis/README.md
[17:58:20] [not_included] [Files Modified] docs/api/analysis/README.md; docs/api/analysis/base.md; docs/api/analysis/statistical.md; docs/api/analysis/zones.md
[18:12:10] [not_included] [Fixed] Актуализирован docs/api/indicators/README.md: корректные ссылки, примеры, названия сущностей (Factory/Result/Config)
[18:12:10] [not_included] [Added] Созданы страницы индикаторов: docs/api/indicators/base.md; macd.md; factory.md
[18:12:10] [not_included] [Files Modified] docs/api/indicators/README.md; docs/api/indicators/base.md; docs/api/indicators/macd.md; docs/api/indicators/factory.md
[18:21:30] [not_included] [Changed] Обновлён docs/api/data/README.md: добавлены ссылки на module pages и перечень детальной документации
[18:21:30] [not_included] [Added] Созданы страницы модулей данных: docs/api/data/loader.md; processor.md; validator.md; schemas.md
[18:21:30] [not_included] [Files Modified] docs/api/data/README.md; docs/api/data/loader.md; docs/api/data/processor.md; docs/api/data/validator.md; docs/api/data/schemas.md
