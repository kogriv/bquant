# ZO Validation Check

| Документация | Тестовый файл | Результат теста | Соответствие примеров |
| --- | --- | --- | --- |
| docs/api/README.md | devref/gaps/zo/zodoctest/test_api_readme_validation.py | ✅ 9/9 тестов пройдено | Примеры Universal Pipeline и PRELOADED MACD из документации запускаются тестами `test_actual_macd_examples` и `test_universal_pipeline_example`; тестовый скрипт не покрывает вызов `macd_indicator.calculate(data)` перед использованием PRELOADED индикатора, но остальные шаги соответствуют документации. |
| docs/api/analysis/README.md | devref/gaps/zo/zodoctest/test_analysis_readme_validation.py | ✅ 9/9 тестов пройдено (требуется запуск с `PYTHONPATH=.`) | Скрипт воспроизводит примеры Universal Pipeline, t-test, анализ характеристик и последовательностей зон, использование `StatisticalAnalyzer` и кастомного `VolatilityAnalyzer`; раздел «Экспорт результатов анализа» с `run_all_hypothesis_tests(zones_info)` не исполняется тестами и остаётся непокрытым. |

