[09:05:12] [not_included] [Technical] Stage 1 LibraryManager refactor: removed automatic pandas-ta loader instantiation so indicators no longer self-register on import and verified manual bootstrap path.
[09:12:47] [not_included] [Added] Stage 2 LibraryManager refactor: implemented dynamic pandas-ta discovery/registration that generates LibraryIndicator wrappers from function signatures and plugged them into the factory lookup.
[09:20:03] [not_included] [Changed] Stage 3 LibraryManager refactor: routed indicator initialization through LibraryManager.load_all_libraries() with availability logging to centralize external library setup.
[09:33:18] [not_included] [Technical] Stage 4 LibraryManager refactor: introduced unit tests covering dynamic pandas-ta registration, logging hooks, error propagation, and LibraryManager access.
[09:45:56] [not_included] [Changed] Stage 5 LibraryManager refactor: refreshed API docs, guides, README, and examples to describe the new LibraryManager workflow and “simple way” to load pandas-ta indicators.
[17:57:30] [not_included] [Fixed] Исправлена проблема визуализации MACD: добавлено поле data в ZoneAnalysisResult для передачи данных с MACD колонками в визуализацию
[17:57:45] [not_included] [Changed] Обновлен метод plot_macd_with_zones для поддержки как dict, так и dataclass объектов ZoneInfo (используется getattr вместо dict access)
[17:58:00] [not_included] [Fixed] Исправлены тесты визуализации: используются данные с MACD индикаторами из analysis_result.data вместо исходных данных
[17:58:15] [not_included] [Fixed] Обновлен формат временных интервалов: заменено 'H' на 'h' в тестовых фикстурах (tests/fixtures/__init__.py, tests/unit/test_analysis_structure.py) для совместимости с pandas 2.x
[17:58:30] [Files Modified] bquant/indicators/macd.py, bquant/visualization/charts.py, tests/integration/test_visualization_pipeline.py, tests/fixtures/__init__.py, tests/unit/test_analysis_structure.py
[18:16:50] [not_included] [Fixed] Исправлен test_statistical_visualization_pipeline: создаются DataFrame для scatter_plot и box_plot вместо передачи списков напрямую
[18:17:00] [not_included] [Fixed] Исправлен test_theming_pipeline: параметр columns передается как список ['close'] вместо строки 'close'
[18:17:10] [not_included] [Added] Добавлен метод get_statistics() в динамически создаваемые pandas-ta индикаторы для полной совместимости интерфейса
[18:17:20] [Files Modified] tests/integration/test_visualization_pipeline.py, bquant/indicators/library/pandas_ta.py
[18:24:00] [not_included] [Added] Установлен pytest-cov для измерения покрытия кода тестами
[18:24:10] [not_included] [Technical] Запущен coverage анализ: общее покрытие 59% (7109 строк, 2912 непокрытых), высокое покрытие в indicators (86-96%), analysis/zones (94%), средние показатели требуют внимания в visualization (33-56%) и CLI (0%)
[18:24:20] [Files Modified] pyproject.toml (добавлен pytest-cov в dev dependencies), создан htmlcov/ с HTML отчетом
