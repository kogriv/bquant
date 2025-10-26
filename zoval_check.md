# ZO Validation Check

| Документация | Тестовый файл | Результат теста | Соответствие примеров |
| --- | --- | --- | --- |
| docs/api/README.md | devref/gaps/zo/zodoctest/test_api_readme_validation.py | ✅ 9/9 тестов пройдено | Примеры Universal Pipeline и PRELOADED MACD из документации запускаются тестами `test_actual_macd_examples` и `test_universal_pipeline_example`; тестовый скрипт не покрывает вызов `macd_indicator.calculate(data)` перед использованием PRELOADED индикатора, но остальные шаги соответствуют документации. |

