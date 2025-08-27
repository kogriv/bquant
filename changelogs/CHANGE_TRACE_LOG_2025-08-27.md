# Change Trace Log 2025-08-27

[18:10:15] [not_included] [Fixed] Исправлена проблема с избыточным выводом JavaScript кода Plotly - теперь графики сохраняются в HTML файлы вместо попытки отображения в консоли
[18:10:30] [not_included] [Fixed] Исправлена ошибка "Mime type rendering requires nbformat>=4.2.0" - добавлена зависимость nbformat>=4.2.0
[18:10:45] [not_included] [Added] Новая опция --quiet (-q) для минимального вывода без подробной информации
[18:11:00] [not_included] [Added] Автоматическое сохранение графиков в HTML файлы с временными метками
[18:11:15] [not_included] [Added] Улучшенная обработка ошибок в модуле визуализации
[18:11:30] [not_included] [Added] Обновленная справка с примерами использования новых опций
[18:11:45] [not_included] [Changed] Изменена логика отображения графиков - теперь всегда сохраняются в HTML вместо попытки отображения в браузере
[18:12:00] [not_included] [Changed] Улучшен пользовательский интерфейс CLI с более информативными сообщениями
[18:12:15] [not_included] [Technical] Добавлена зависимость nbformat>=4.2.0 в pyproject.toml и requirements.txt
[18:12:30] [not_included] [Technical] Обновлена функция analyze_macd() для поддержки тихого режима
[18:12:45] [not_included] [Technical] Улучшена функция create_price_chart() с обработкой ошибок
[18:13:00] [not_included] [Technical] Обновлена версия проекта до 0.0.2 (откачена обратно к 0.0.1 для накопления изменений)
[18:13:15] [not_included] [Files Modified] pyproject.toml - добавлена зависимость nbformat, обновлена версия (откачена обратно к 0.0.1)
[18:13:30] [not_included] [Files Modified] requirements.txt - добавлена зависимость nbformat
[18:13:45] [not_included] [Files Modified] bquant/cli.py - добавлена опция --quiet, изменена логика отображения графиков, изменен путь сохранения на results/charts
[18:14:00] [not_included] [Files Modified] bquant/visualization/charts.py - улучшена обработка ошибок
[18:14:15] [not_included] [Files Modified] CHANGELOG.md - откачены изменения (перенесены в этот файл)
[18:14:30] [not_included] [Files Modified] CHANGE_TRACE_LOG.md - создан новый файл для отслеживания изменений
[18:14:45] [not_included] [Files Modified] results/charts/ - создана директория для сохранения графиков
[18:15:00] [not_included] [Changed] Изменен путь сохранения графиков по умолчанию - теперь графики сохраняются в results/charts/ вместо корневой директории
[18:15:15] [not_included] [Changed] Автоматическое создание директории - директория results/charts/ создается автоматически при необходимости
[18:15:30] [not_included] [Technical] Обновлена функция analyze_macd() для использования os.path.join() и os.makedirs()
[18:15:45] [not_included] [Technical] Добавлен импорт модуля os в CLI
[18:16:00] [not_included] [Added] Создан модуль bquant/data/samples/generator.py - генератор embedded данных в составе пакета
[18:16:15] [not_included] [Added] Класс SampleDataGenerator - использует loader.py и config.py вместо хардкода
[18:16:30] [not_included] [Added] Упрощенная обертка scripts/generate_samples.py - использует новый генератор из пакета
[18:16:45] [not_included] [Changed] Убрана хардкод конфигурация - теперь используется get_data_path() из config.py
[18:17:00] [not_included] [Changed] Использование loader.py - вместо прямого чтения CSV через pd.read_csv()
[18:17:15] [not_included] [Changed] Улучшена архитектура - функционал генерации перенесен в пакет
[18:17:30] [not_included] [Technical] Добавлен импорт SampleDataGenerator в bquant/data/samples/__init__.py
[18:17:45] [not_included] [Technical] Обновлен __all__ список для экспорта нового класса
[18:18:00] [not_included] [Technical] Добавлены примеры использования в документации модуля
[18:18:15] [not_included] [Files Modified] bquant/bquant/data/samples/generator.py - создан новый модуль генератора
[18:18:30] [not_included] [Files Modified] bquant/bquant/data/samples/__init__.py - добавлен экспорт SampleDataGenerator
[18:18:45] [not_included] [Files Modified] scripts/generate_samples.py - создана упрощенная обертка (заменяет extract_samples.py)
[18:19:00] [not_included] [Files Modified] tests/unit/test_sample_generator.py - созданы тесты для нового генератора
[18:19:15] [not_included] [other] Создана папка changelogs/ для новой системы трэйслогов
[18:19:30] [not_included] [other] Перенесена описательная часть в changelogs/README.md
[18:19:45] [not_included] [other] Изменен формат записей на компактный: [время] [статус] [тип] [содержание]
[18:20:00] [not_included] [other] Удален старый файл CHANGE_TRACE_LOG.md
[18:20:15] [not_included] [other] Создана новая система трэйслогов в папке changelogs/
