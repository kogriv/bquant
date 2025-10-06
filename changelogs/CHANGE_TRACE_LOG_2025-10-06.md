# CHANGE TRACE LOG - 2025-10-06

[13:19:12] [not_included] [Fixed] Исправлен скрипт research/notebooks/02_ind_calculators.py - устранены проблемы с созданием пользовательских наборов индикаторов
[13:19:15] [not_included] [Fixed] Исправлен скрипт research/notebooks/02_ind_calculators.py - устранены проблемы с созданием комплексных наборов индикаторов
[13:23:16] [not_included] [Fixed] Заменены deprecated вызовы IndicatorFactory.create_indicator() на IndicatorFactory.create() в bquant/indicators/calculators.py
[13:23:18] [not_included] [Fixed] Заменены deprecated вызовы IndicatorFactory.create_indicator() на IndicatorFactory.create() в bquant/indicators/library/manager.py
[13:24:02] [not_included] [Technical] Протестирован исправленный функционал - скрипт 02_ind_calculators.py выполняется без ошибок и deprecated предупреждений
[13:24:14] [not_included] [Technical] Проверена работоспособность unit-тестов - все тесты IndicatorFactory проходят успешно
[13:24:18] [not_included] [Technical] Подтверждено отсутствие deprecated предупреждений в основном коде при использовании IndicatorCalculator
[13:30:56] [not_included] [Fixed] Повторно исправлены deprecated методы в bquant/indicators/calculators.py (строки 74, 373)
[13:30:58] [not_included] [Fixed] Повторно исправлены deprecated методы в bquant/indicators/library/manager.py (строка 162)
[13:31:01] [not_included] [Technical] Подтверждено отсутствие deprecated предупреждений после повторного исправления
[13:33:06] [not_included] [Fixed] Исправлены импорты в скрипте research/notebooks/02_ind_library.py - изменен импорт с bquant.indicators.library на bquant.indicators.custom
[13:33:06] [not_included] [Technical] Протестирован скрипт 02_ind_library.py - успешно выполняется с новой архитектурой индикаторов
[13:35:09] [not_included] [Technical] Протестирован скрипт 02_ind_macd.py - успешно выполняется с новой архитектурой
[13:35:33] [not_included] [Fixed] Исправлен импорт в скрипте research/notebooks/02_ind_macd.py (строка 647) - изменен импорт с bquant.indicators.library на bquant.indicators.custom
[13:37:15] [not_included] [Technical] Протестирован скрипт 02_ind_types.py - успешно выполняется с новой архитектурой индикаторов без изменений
[13:38:17] [not_included] [Technical] Протестирован скрипт 03_analysis_base.py - успешно выполняется с модулем анализа без изменений
[13:39:06] [not_included] [Technical] Протестирован скрипт 03_analysis_statistical.py - успешно выполняется с модулем статистического анализа без изменений
[13:40:55] [not_included] [Technical] Протестирован скрипт 03_analysis_zones.py - успешно выполняется с модулем анализа зон без изменений
