# ZO Validation Check

| Файлы | Результат теста | Соответствие примеров | Непокрытые примеры кода |
| --- | --- | --- | --- |
| docs/api/README.md<br>devref/gaps/zo/zodoctest/test_api_readme_validation.py | ✅ 9/9 тестов пройдено | Universal Pipeline и PRELOADED MACD сценарии из документации запускаются в тестах `test_universal_pipeline_example` и `test_actual_macd_examples`; прочие шаги воспроизведены. | Вызов PRELOADED MACD `macd_indicator.calculate(data)` отсутствует в тесте. |
| docs/api/analysis/README.md<br>devref/gaps/zo/zodoctest/test_analysis_readme_validation.py | ✅ 9/9 тестов пройдено (требуется запуск с `PYTHONPATH=.`) | Проверяются примеры Universal Pipeline, t-test, анализ характеристик и последовательностей зон, `StatisticalAnalyzer`, кастомный `VolatilityAnalyzer`. | Раздел «Экспорт результатов анализа»: `run_all_hypothesis_tests(zones_info)` не исполняется. |
| docs/api/analysis/zones.md<br>devref/gaps/zo/zodoctest/test_zones_validation.py | ❌ 10/11 тестов (legacy API `AttributeError: 'int' object has no attribute 'total_seconds'`) | Актуальные примеры `indicator_context`, MACD/RSI/Stochastic, кастомный индикатор и `.with_strategies()` воспроизводятся тестами; Universal Pipeline сценарии совпадают с документацией. | Legacy-блок `find_support_resistance`/`ZoneFeaturesAnalyzer` падает на расчёте `total_seconds()`; маркетинговые декларации (`FICTIONAL_INDICATOR_99`, перечисление стратегий) не покрыты. |

