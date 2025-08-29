# Отчет о несоответствиях документации и реализации модулей данных (bquant.data)

## Обзор

Цель: поверхностно сравнить реализацию пакета `bquant.data` с документацией в `docs/api/data` и выявить ошибки и расхождения.

Проверено:
- Реализация: `bquant/data/loader.py`, `bquant/data/processor.py`, `bquant/data/validator.py`, `bquant/data/samples/*`, `bquant/data/schemas.py`.
- Документация: `docs/api/data/README.md`.

Итог: базовый перечень функций в шапке дока частично совпадает с кодом, но примеры использования и «быстрый поиск» содержат существенные неточности, отсутствуют страницы модулей, на которые ведут ссылки.

## Что реально есть в коде (главное)

- Загрузка данных:
  - `load_ohlcv_data`, `load_symbol_data`, `load_xauusd_data`, `load_all_data_files`, `get_data_info`, `get_available_symbols`, `get_available_timeframes` (`bquant/data/loader.py`).
- Обработка данных:
  - `clean_ohlcv_data`, `remove_price_outliers`, `calculate_derived_indicators`, `resample_ohlcv`, `normalize_prices`, `detect_market_sessions`, `add_technical_features`, `create_lagged_features`, `prepare_data_for_analysis` (`bquant/data/processor.py`).
- Валидация:
  - `validate_ohlcv_data`, `validate_data_completeness`, `validate_price_consistency`, `validate_time_series_continuity`, `validate_statistical_properties` (`bquant/data/validator.py`).
- Сэмплы:
  - В `bquant/data/samples/__init__.py`: `get_sample_data`, `list_datasets`, `get_dataset_info`, `validate_dataset`, `get_sample_preview`, `get_data_statistics`, `find_datasets`, `compare_sample_datasets`, `print_sample_data_status`.
  - Утилиты (через `bquant.data.samples`): `convert_to_dataframe`, `convert_to_list_of_dicts`, `validate_data_integrity` (`bquant/data/samples/utils.py`).
- Схемы:
  - `OHLCVRecord`, `DataSourceConfig`, `ValidationResult`, `DataSchema`, `OHLCVSchema`, `IndicatorSchema`, `get_schema`, `validate_with_schema` (`bquant/data/schemas.py`).
  - Примечание: проверка по схемам — заглушка (пока без реальной валидации).

## Выявленные ошибки и несоответствия в документации

- Ссылки на несуществующие страницы:
  - В `docs/api/data/README.md` есть ссылки на `loader.md`, `processor.md`, `validator.md`, `samples.md`, `schemas.md`, однако этих файлов нет в `docs/api/data/`.

- Loader (несоответствия):
  - Упомянуты несуществующие функции: `load_tradingview_data`, `load_metatrader_data`, `DataLoader.load` — их нет в `bquant/data/loader.py`.
  - Пример с `load_ohlcv_data` использует неподдерживаемые аргументы `date_column`, `ohlcv_columns` — их нет в сигнатуре (`file_path, symbol=None, timeframe=None, validate_data=True`).

- Processor (несоответствия):
  - В примерах используются не те имена: `resample_data` → в коде `resample_ohlcv`; `remove_outliers` → в коде `remove_price_outliers`.
  - В примерах — параметр `fill_missing='forward'`, а в коде `fill_method='forward'`.
  - В документации фигурируют несуществующие классы/методы: `DataProcessor`, `set_cleaning_options`, `process`, `get_processing_stats` — их нет, API процедурный.

- Validator (несоответствия):
  - `validate_ohlcv_data` возвращает dict, но в примере обращения идут как к атрибутам (`result.is_valid`). Должно быть `result['is_valid']` и т. п.
  - Упомянутые функции `check_data_integrity`, `validate_dataframe`, `check_missing_values` отсутствуют в `bquant.data.validator`.
  - Близкая по названию `validate_data_integrity` есть только в модуле сэмплов (`bquant/data/samples/utils.py`) и работает со списком словарей (embedded-данные), а не с DataFrame.
  - В документации упоминается класс `DataValidator` с методами — в коде такого нет.

- Samples (мелкие несостыковки):
  - В примере используется `convert_to_dataframe(data)` без импорта. Функция есть и доступна через `from bquant.data.samples import convert_to_dataframe`, но это не показано в тексте примера.
  - `list_dataset_names` доступна (реэкспортируется), но не упомянута в явном списке экспортов; в примере используется без пояснения.

- Schemas (уточнения):
  - Документация подразумевает полноценную работу схем, однако реализация — заглушка: `DataSchema.validate_dataframe` возвращает успех с рекомендацией «Schema validation is not yet implemented».

- Общие проблемы примеров:
  - Смешение регистров таймфреймов ('1h'/'1H', 'M15'/'15M'): код поддерживает нормализацию через конфиг, но в примерах лучше использовать единый формат.
  - Документация местами описывает ОО-подход (классы Loader/Processor/Validator), а реализация — набор функций.

## Оценка соответствия

- Перечень ключевых функций в верхнем разделе — частично соответствует.
- Примеры и раздел «быстрый поиск» — содержат множество несоответствий именам функций, параметрам и типам возвращаемых значений.
- Структура документации — критично неполная: отсутствуют страницы модулей, на которые ссылается README.
- Раздел про схемы не отражает текущий «stub» статус.

## Рекомендации по исправлению

1) Навести порядок со ссылками:
- Создать минимальные страницы `loader.md`, `processor.md`, `validator.md`, `samples.md`, `schemas.md` (пусть даже краткие), либо заменить ссылки в README на существующие разделы.

2) Привести имена и параметры в соответствие коду:
- Везде заменить `resample_data` → `resample_ohlcv`, `remove_outliers` → `remove_price_outliers`, `fill_missing` → `fill_method`.
- В примерах с валидацией работать с dict: `res['is_valid']`, `res['errors']`, `res['warnings']`.
- Убрать из примеров неподдерживаемые параметры `load_ohlcv_data` (`date_column`, `ohlcv_columns`).

3) Убрать/пометить как «в планах» несуществующие сущности:
- `DataLoader`, `DataProcessor`, `DataValidator`, `SampleDataManager`, `load_tradingview_data`, `load_metatrader_data`, `check_missing_values`, `validate_dataframe` (в контексте валидатора), `check_data_integrity` (в контексте валидатора).

4) Исправить примеры импорта:
- Добавить `from bquant.data.samples import convert_to_dataframe` там, где функция используется.

5) Прояснить статус схем:
- Явно указать, что проверка через `validate_with_schema` — временная заглушка; полноценная схема-валидация в разработке.

6) Унифицировать формат таймфреймов в примерах:
- Использовать единый регистр (например, `'1H'`, `'15M'`) и/или отдельной строкой указать, что маппинг нормализуется конфигурацией.

## Возможные следующие шаги (по коду)
- По желанию, реализовать отсутствующие сущности, если они действительно нужны по роадмапу (например, тонкие загрузчики для отдельных источников, OO-обертки над пайплайном обработки/валидации).
- Иначе — упростить документацию до текущего процедурного API без упоминания несуществующих классов.

---

Примечание: анализ выполнен по состоянию репозитория на момент проверки; ссылки и строки могут измениться в будущих коммитах.

