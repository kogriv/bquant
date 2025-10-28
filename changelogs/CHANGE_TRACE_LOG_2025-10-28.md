# Change Trace Log 2025-10-28


==================== COMMIT DIVIDER ====================

[10:30:00] [not_included] [Fixed] Исправлена ошибка OSError: [Errno 22] Invalid argument в логировании на Windows
[10:32:15] [not_included] [Added] Добавлены WindowsSafeStreamHandler и WindowsSafeRotatingFileHandler в bquant/core/logging_config.py
[10:34:30] [not_included] [Changed] Отключены ANSI цветовые коды в BQuantFormatter для Windows совместимости
[10:36:45] [not_included] [Added] Добавлена функция setup_windows_compatible_logging() для автоматической настройки
[10:38:00] [not_included] [Fixed] Исправлена ошибка UnicodeEncodeError в CLI модуле - заменены emoji на текстовые индикаторы
[10:40:15] [not_included] [Changed] Добавлена UTF-8 кодировка для stdout/stderr в bquant/cli.py на Windows
[10:42:30] [not_included] [Technical] Добавлены Windows-специфичные переменные окружения в tests/conftest.py
[10:44:45] [not_included] [Technical] Добавлены pytest хуки для Windows-совместимого тестирования
[10:46:00] [not_included] [Technical] Добавлены фильтры предупреждений для подавления Windows-специфичных warnings
[10:48:15] [not_included] [Technical] Все тесты проходят успешно на Windows (core modules: 15 passed, data modules: 8 passed)
[10:50:30] [not_included] [Technical] CLI команды работают без ошибок кодировки на Windows
[10:52:45] [not_included] [Technical] Zone analysis pipeline функционирует корректно на Windows
[11:00:00] [not_included] [Added] Создан файл docs/user_guide/swing_analysis_results.md - документация по результатам swing анализа
[11:02:15] [not_included] [Added] Создан файл docs/user_guide/zone_analysis_pipeline.md - документация по универсальному pipeline анализа зон
[11:04:30] [not_included] [Added] Создан файл examples/08_macd_swing_analysis.py - пример MACD swing анализа

