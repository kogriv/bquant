# Changelog Trace Log - 2025-08-30

## [18:30:00] [not_included] [Added] Система управления директориями в bquant.core.config
- Добавлены getter функции: get_data_dir(), get_results_dir(), get_notebooks_dir(), get_processed_data_dir()
- Добавлены setter функции: set_data_dir(), set_results_dir(), set_notebooks_dir(), set_processed_data_dir()
- Добавлены утилиты: reset_directories_to_defaults(), get_directory_status()
- Поддержка runtime изменения путей директорий без изменения констант

## [18:30:30] [not_included] [Changed] Обновлена документация docs/api/core/config.md
- Добавлен раздел "Управление директориями" с описанием новых функций
- Добавлены примеры использования getter/setter функций
- Описаны функции проверки статуса директорий

## [18:31:00] [not_included] [Technical] Добавлен импорт Union в bquant.core.config
- Исправлена проблема с type hints для параметров функций set_*_dir()
- Улучшена типизация для поддержки Union[str, Path]

## [19:45:00] [not_included] [Added] Гибкая система логирования в bquant.core.logging_config
- Добавлены параметры console_level и file_level для раздельной настройки уровней
- Добавлен параметр console_enabled для отключения консольного вывода
- Реализована поддержка разных уровней логирования для консоли и файла

## [19:45:30] [not_included] [Added] Preset функции для типовых сценариев логирования
- setup_notebook_logging() - для Jupyter ноутбуков (WARNING→консоль, INFO→файл)
- setup_development_logging() - для разработки (DEBUG везде)
- setup_production_logging() - для продакшена (только файл, INFO+)
- setup_quiet_logging() - тихий режим (ERROR→консоль, INFO→файл)

## [19:46:00] [not_included] [Changed] Обновлена документация docs/api/core/logging.md
- Добавлено описание новых параметров setup_logging()
- Документированы все preset функции с примерами использования
- Обновлены примеры для быстрой настройки в ноутбуках
- Добавлены примеры гибкой настройки с разными уровнями

## [18:21:00] [not_included] [Fixed] Исправлены deprecated warnings в loader.py - заменены date_parser и infer_datetime_format на современные параметры pandas

## [18:21:15] [not_included] [Technical] Обновлен алгоритм парсинга дат в load_ohlcv_data() - добавлено автоопределение форматов и fallback логика

## [18:21:30] [not_included] [Files Modified] bquant/data/loader.py - исправлены deprecated параметры pandas для совместимости с будущими версиями

## [18:21:45] [not_included] [Technical] Протестированы исправления - deprecated warnings устранены, загрузка данных работает корректно

## [18:22:00] [not_included] [Fixed] Добавлена поддержка автоопределения кодировки файлов в loader.py - решена проблема с MetaTrader CSV файлами

## [18:22:15] [not_included] [Added] Функция _detect_file_encoding() - использует chardet для автоматического определения кодировки файлов

## [18:22:30] [not_included] [Added] Функция _try_read_csv_with_encoding() - читает CSV с указанной кодировкой и различными форматами дат

## [18:22:45] [not_included] [Technical] Добавлена зависимость chardet>=5.0.0 в pyproject.toml и requirements.txt

## [18:23:00] [not_included] [Changed] Обновлена логика загрузки CSV - теперь поддерживает windows-1252, cp1252, iso-8859-1, utf-16 кодировки

## [18:23:15] [not_included] [Files Modified] bquant/data/loader.py - добавлена поддержка автоопределения кодировки для совместимости с MetaTrader файлами

## [18:24:00] [not_included] [Fixed] Добавлена поддержка MetaTrader формата без заголовков в loader.py - решена проблема с загрузкой XAUUSDH1.csv

## [18:24:15] [not_included] [Added] Функция _is_mt_format_without_headers() - детекция MetaTrader формата без заголовков колонок

## [18:24:30] [not_included] [Changed] Обновлена _try_read_csv_with_encoding() - добавлена поддержка header=None и автоматическое именование колонок

## [18:24:45] [not_included] [Technical] Добавлен маппинг колонок для MT формата: time, open, high, low, close, volume

## [18:25:00] [not_included] [Files Modified] bquant/data/loader.py - исправлена загрузка MetaTrader CSV файлов без заголовков