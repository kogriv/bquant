'''
Демонстрация работы модуля валидации данных bquant.data.schemas

Этот скрипт показывает, как использовать различные функции для валидации данных:
1.  Создание и настройка схем данных.
2.  Валидация OHLCV записей.
3.  Валидация технических индикаторов.
4.  Валидация DataFrame с помощью схем.
5.  Работа с конфигурацией источников данных.
6.  Создание пользовательских схем валидации.
'''

from pathlib import Path
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.data.schemas import (
    OHLCVRecord,
    DataSourceConfig,
    ValidationResult,
    DataSchema,
    OHLCVSchema,
    IndicatorSchema,
    OHLCV_SCHEMA,
    MACD_SCHEMA,
    RSI_SCHEMA,
    get_schema,
    validate_with_schema,
    AVAILABLE_SCHEMAS
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы модуля bquant.data.schemas")

# --- Шаг 1: Загрузка тестовых данных и создание проблемных данных ---
nb.step("Шаг 1: Загрузка тестовых данных и создание проблемных данных")

nb.info("Для демонстрации валидации данных используем встроенные sample-данные и создадим проблемные данные.")

# Загружаем корректные данные
with nb.error_handling("Loading sample data"):
    nb.info("1.1. Загружаем корректные sample-данные:")
    df_sample = get_sample_data('tv_xauusd_1h')
    
    # Преобразуем колонку time в DatetimeIndex для корректной работы
    if 'time' in df_sample.columns:
        df_sample = df_sample.set_index('time')
        nb.log("Колонка 'time' преобразована в DatetimeIndex")
    
    nb.log(f"Загружено {len(df_sample)} строк корректных данных")
    nb.log(f"Структура: {list(df_sample.columns)}")
    nb.log(f"Тип индекса: {type(df_sample.index)}")
    nb.log(f"Диапазон дат: {df_sample.index.min()} - {df_sample.index.max()}")

# Создаем проблемные данные для демонстрации валидации
with nb.error_handling("Creating problematic data"):
    nb.info("1.2. Создаем проблемные данные для демонстрации валидации:")
    
    # Копируем sample данные и добавляем проблемы
    df_problematic = df_sample.copy()
    
    # Добавляем логические ошибки (high < low)
    df_problematic.iloc[100:105, df_problematic.columns.get_loc('high')] = 1000  # Низкое значение
    df_problematic.iloc[100:105, df_problematic.columns.get_loc('low')] = 2000   # Высокое значение
    
    # Добавляем отрицательные цены
    df_problematic.iloc[200:205, df_problematic.columns.get_loc('open')] = -100
    df_problematic.iloc[200:205, df_problematic.columns.get_loc('close')] = -200
    
    # Добавляем нулевые цены
    df_problematic.iloc[300:305, df_problematic.columns.get_loc('low')] = 0
    
    # Добавляем отрицательный объем
    if 'volume' in df_problematic.columns:
        df_problematic.iloc[400:405, df_problematic.columns.get_loc('volume')] = -50000
    
    nb.log(f"Создано {len(df_problematic)} строк проблемных данных")
    nb.log("Добавлены проблемы: логические ошибки OHLC, отрицательные цены, нулевые цены, отрицательный объем")

nb.wait()

# --- Шаг 2: Работа с OHLCVRecord ---
nb.step("Шаг 2: Работа с OHLCVRecord")

nb.info("Класс OHLCVRecord предоставляет схему для валидации отдельных OHLCV записей.")

# Создание корректных OHLCV записей
with nb.error_handling("Creating valid OHLCV records"):
    nb.info("2.1. Создание корректных OHLCV записей:")
    
    # Создаем несколько корректных записей
    valid_records = [
        OHLCVRecord(
            timestamp=datetime.now(),
            open=3330.0,
            high=3340.0,
            low=3320.0,
            close=3335.0,
            volume=100000
        ),
        OHLCVRecord(
            timestamp=datetime.now() + timedelta(hours=1),
            open=3335.0,
            high=3350.0,
            low=3330.0,
            close=3345.0,
            volume=150000
        )
    ]
    
    nb.log(f"Создано {len(valid_records)} корректных OHLCV записей")
    
    # Валидируем каждую запись
    for i, record in enumerate(valid_records):
        is_valid = record.validate()
        nb.log(f"  - Запись {i+1}: {'✅ Валидна' if is_valid else '❌ Невалидна'}")
        nb.log(f"    * Timestamp: {record.timestamp}")
        nb.log(f"    * OHLC: {record.open}/{record.high}/{record.low}/{record.close}")
        nb.log(f"    * Volume: {record.volume}")

# Создание проблемных OHLCV записей
with nb.error_handling("Creating problematic OHLCV records"):
    nb.info("2.2. Создание проблемных OHLCV записей:")
    
    # Создаем проблемные записи
    problematic_records = [
        OHLCVRecord(
            timestamp=datetime.now(),
            open=3330.0,
            high=3320.0,  # high < low - логическая ошибка
            low=3340.0,
            close=3335.0,
            volume=100000
        ),
        OHLCVRecord(
            timestamp=datetime.now() + timedelta(hours=1),
            open=-100.0,  # Отрицательная цена
            high=3350.0,
            low=3330.0,
            close=3345.0,
            volume=150000
        ),
        OHLCVRecord(
            timestamp=datetime.now() + timedelta(hours=2),
            open=3330.0,
            high=3350.0,
            low=0.0,  # Нулевая цена
            close=3345.0,
            volume=-50000  # Отрицательный объем
        )
    ]
    
    nb.log(f"Создано {len(problematic_records)} проблемных OHLCV записей")
    
    # Валидируем каждую проблемную запись
    for i, record in enumerate(problematic_records):
        is_valid = record.validate()
        nb.log(f"  - Запись {i+1}: {'✅ Валидна' if is_valid else '❌ Невалидна'}")
        nb.log(f"    * Timestamp: {record.timestamp}")
        nb.log(f"    * OHLC: {record.open}/{record.high}/{record.low}/{record.close}")
        nb.log(f"    * Volume: {record.volume}")

nb.wait()

# --- Шаг 3: Работа с DataSourceConfig ---
nb.step("Шаг 3: Работа с DataSourceConfig")

nb.info("Класс DataSourceConfig предоставляет конфигурацию для источников данных.")

with nb.error_handling("Creating data source configurations"):
    nb.info("3.1. Создание конфигураций источников данных:")
    
    # Конфигурация для TradingView
    tv_config = DataSourceConfig(
        name="TradingView",
        file_pattern="OANDA_{symbol}, {timeframe}.csv",
        timeframe_mapping={
            "1m": "1",
            "5m": "5", 
            "15m": "15",
            "1h": "60",
            "4h": "240",
            "1d": "1D"
        },
        quote_providers=["OANDA", "FXCM", "Interactive Brokers"]
    )
    
    # Конфигурация для MetaTrader
    mt_config = DataSourceConfig(
        name="MetaTrader",
        file_pattern="{symbol}{timeframe}.csv",
        timeframe_mapping={
            "1m": "M1",
            "5m": "M5",
            "15m": "M15", 
            "1h": "H1",
            "4h": "H4",
            "1d": "D1"
        },
        quote_providers=["MetaTrader", "cTrader", "NinjaTrader"]
    )
    
    nb.log(f"Создано {2} конфигурации источников данных:")
    
    # Показываем детали конфигураций
    for config in [tv_config, mt_config]:
        nb.log(f"  - {config.name}:")
        nb.log(f"    * Паттерн файлов: {config.file_pattern}")
        nb.log(f"    * Маппинг таймфреймов: {len(config.timeframe_mapping)}")
        nb.log(f"    * Провайдеры котировок: {len(config.quote_providers)}")
        
        # Показываем примеры маппинга
        sample_timeframes = list(config.timeframe_mapping.items())[:3]
        nb.log(f"    * Примеры маппинга: {dict(sample_timeframes)}")

nb.wait()

# --- Шаг 4: Работа с базовым классом DataSchema ---
nb.step("Шаг 4: Работа с базовым классом DataSchema")

nb.info("Класс DataSchema - это базовый класс для создания пользовательских схем валидации.")

with nb.error_handling("Creating custom data schema"):
    nb.info("4.1. Создание пользовательской схемы данных:")
    
    # Создаем пользовательскую схему для анализа
    analysis_schema = DataSchema('analysis')
    
    # Добавляем обязательные поля
    analysis_schema.add_required_field('timestamp', datetime)
    analysis_schema.add_required_field('price', float)
    analysis_schema.add_required_field('signal', str)
    
    # Добавляем опциональные поля
    analysis_schema.add_optional_field('confidence', float)
    analysis_schema.add_optional_field('volume', float)
    
    # Добавляем правила валидации
    analysis_schema.add_validation_rule('price', lambda x: x > 0)
    analysis_schema.add_validation_rule('confidence', lambda x: 0 <= x <= 1 if x is not None else True)
    analysis_schema.add_validation_rule('signal', lambda x: x in ['buy', 'sell', 'hold'])
    
    nb.log(f"Создана пользовательская схема 'analysis':")
    nb.log(f"  - Тип схемы: {analysis_schema.schema_type}")
    nb.log(f"  - Обязательные поля: {analysis_schema.required_fields}")
    nb.log(f"  - Опциональные поля: {analysis_schema.optional_fields}")
    nb.log(f"  - Правила валидации: {len(analysis_schema.validation_rules)}")
    
    # Создаем тестовые данные для валидации
    test_data = pd.DataFrame({
        'timestamp': [datetime.now(), datetime.now() + timedelta(hours=1)],
        'price': [3330.0, 3340.0],
        'signal': ['buy', 'sell'],
        'confidence': [0.8, 0.9],
        'volume': [100000, 150000]
    })
    
    nb.log(f"Создан тестовый DataFrame для валидации: {test_data.shape}")
    
    # Валидируем данные с помощью схемы
    validation_result = analysis_schema.validate_dataframe(test_data)
    nb.log(f"Результат валидации:")
    nb.log(f"  - Валидны: {validation_result.is_valid}")
    nb.log(f"  - Проблемы: {len(validation_result.issues)}")
    nb.log(f"  - Предупреждения: {len(validation_result.warnings)}")
    nb.log(f"  - Статистика: {validation_result.stats}")

nb.wait()

# --- Шаг 5: Работа с OHLCVSchema ---
nb.step("Шаг 5: Работа с OHLCVSchema")

nb.info("OHLCVSchema предоставляет специализированную схему для валидации OHLCV данных.")

with nb.error_handling("Testing OHLCV schema"):
    nb.info("5.1. Тестирование OHLCV схемы:")
    
    nb.log(f"Детали OHLCV схемы:")
    nb.log(f"  - Тип схемы: {OHLCV_SCHEMA.schema_type}")
    nb.log(f"  - Обязательные поля: {OHLCV_SCHEMA.required_fields}")
    nb.log(f"  - Опциональные поля: {OHLCV_SCHEMA.optional_fields}")
    nb.log(f"  - Правила валидации: {len(OHLCV_SCHEMA.validation_rules)}")
    
    # Валидируем корректные данные
    nb.info("5.2. Валидация корректных OHLCV данных:")
    valid_ohlcv_result = OHLCV_SCHEMA.validate_dataframe(df_sample)
    
    nb.log(f"Результат валидации корректных данных:")
    nb.log(f"  - Валидны: {valid_ohlcv_result.is_valid}")
    nb.log(f"  - Проблемы: {len(valid_ohlcv_result.issues)}")
    nb.log(f"  - Предупреждения: {len(valid_ohlcv_result.warnings)}")
    nb.log(f"  - Статистика: {valid_ohlcv_result.stats}")
    
    # Валидируем проблемные данные
    nb.info("5.3. Валидация проблемных OHLCV данных:")
    problematic_ohlcv_result = OHLCV_SCHEMA.validate_dataframe(df_problematic)
    
    nb.log(f"Результат валидации проблемных данных:")
    nb.log(f"  - Валидны: {problematic_ohlcv_result.is_valid}")
    nb.log(f"  - Проблемы: {len(problematic_ohlcv_result.issues)}")
    nb.log(f"  - Предупреждения: {len(problematic_ohlcv_result.warnings)}")
    nb.log(f"  - Статистика: {problematic_ohlcv_result.stats}")

nb.wait()

# --- Шаг 6: Работа с IndicatorSchema ---
nb.step("Шаг 6: Работа с IndicatorSchema")

nb.info("IndicatorSchema предоставляет схемы для валидации технических индикаторов.")

with nb.error_handling("Testing indicator schemas"):
    nb.info("6.1. Тестирование MACD схемы:")
    
    nb.log(f"Детали MACD схемы:")
    nb.log(f"  - Тип схемы: {MACD_SCHEMA.schema_type}")
    nb.log(f"  - Индикатор: {MACD_SCHEMA.indicator_name}")
    nb.log(f"  - Обязательные поля: {MACD_SCHEMA.required_fields}")
    nb.log(f"  - Правила валидации: {len(MACD_SCHEMA.validation_rules)}")
    
    # Создаем тестовые MACD данные
    macd_data = pd.DataFrame({
        'macd': [0.5, -0.3, 0.8],
        'macd_signal': [0.2, -0.1, 0.6],
        'macd_hist': [0.3, -0.2, 0.2]
    })
    
    nb.log(f"Создан тестовый DataFrame для MACD: {macd_data.shape}")
    
    # Валидируем MACD данные
    macd_result = MACD_SCHEMA.validate_dataframe(macd_data)
    nb.log(f"Результат валидации MACD:")
    nb.log(f"  - Валидны: {macd_result.is_valid}")
    nb.log(f"  - Проблемы: {len(macd_result.issues)}")
    nb.log(f"  - Статистика: {macd_result.stats}")
    
    nb.info("6.2. Тестирование RSI схемы:")
    
    nb.log(f"Детали RSI схемы:")
    nb.log(f"  - Тип схемы: {RSI_SCHEMA.schema_type}")
    nb.log(f"  - Индикатор: {RSI_SCHEMA.indicator_name}")
    nb.log(f"  - Обязательные поля: {RSI_SCHEMA.required_fields}")
    nb.log(f"  - Правила валидации: {len(RSI_SCHEMA.validation_rules)}")
    
    # Создаем тестовые RSI данные
    rsi_data = pd.DataFrame({
        'rsi': [30.5, 50.0, 70.2, 85.1, 15.3]
    })
    
    nb.log(f"Создан тестовый DataFrame для RSI: {rsi_data.shape}")
    
    # Валидируем RSI данные
    rsi_result = RSI_SCHEMA.validate_dataframe(rsi_data)
    nb.log(f"Результат валидации RSI:")
    nb.log(f"  - Валидны: {rsi_result.is_valid}")
    nb.log(f"  - Проблемы: {len(rsi_result.issues)}")
    nb.log(f"  - Статистика: {rsi_result.stats}")

nb.wait()

# --- Шаг 7: Работа с функцией get_schema ---
nb.step("Шаг 7: Работа с функцией get_schema")

nb.info("Функция get_schema() позволяет получать предопределенные схемы по имени.")

with nb.error_handling("Testing get_schema function"):
    nb.info("7.1. Получение доступных схем:")
    
    # Получаем список доступных схем
    available_schemas = list(AVAILABLE_SCHEMAS.keys())
    nb.log(f"Доступные схемы: {available_schemas}")
    
    # Тестируем получение каждой схемы
    for schema_name in available_schemas:
        schema = get_schema(schema_name)
        if schema:
            nb.log(f"  - {schema_name}: получена схема типа '{schema.schema_type}'")
        else:
            nb.log(f"  - {schema_name}: схема не найдена")
    
    # Тестируем получение несуществующей схемы
    nb.info("7.2. Тестирование получения несуществующей схемы:")
    non_existent_schema = get_schema('non_existent')
    nb.log(f"Результат получения 'non_existent': {non_existent_schema}")
    
    # Тестируем получение схемы по названию
    nb.info("7.3. Тестирование получения схемы 'ohlcv':")
    ohlcv_schema = get_schema('ohlcv')
    if ohlcv_schema:
        nb.log(f"Получена схема OHLCV:")
        nb.log(f"  - Тип: {ohlcv_schema.schema_type}")
        nb.log(f"  - Обязательные поля: {ohlcv_schema.required_fields}")
        nb.log(f"  - Опциональные поля: {ohlcv_schema.optional_fields}")

nb.wait()

# --- Шаг 8: Работа с функцией validate_with_schema ---
nb.step("Шаг 8: Работа с функцией validate_with_schema")

nb.info("Функция validate_with_schema() позволяет валидировать DataFrame с помощью предопределенных схем.")

with nb.error_handling("Testing validate_with_schema function"):
    nb.info("8.1. Валидация данных с помощью схемы 'ohlcv':")
    
    # Валидируем корректные данные
    ohlcv_validation = validate_with_schema(df_sample, 'ohlcv')
    nb.log(f"Результат валидации корректных данных с 'ohlcv':")
    nb.log(f"  - Валидны: {ohlcv_validation.is_valid}")
    nb.log(f"  - Проблемы: {len(ohlcv_validation.issues)}")
    nb.log(f"  - Предупреждения: {len(ohlcv_validation.warnings)}")
    nb.log(f"  - Статистика: {ohlcv_validation.stats}")
    
    # Валидируем проблемные данные
    problematic_ohlcv_validation = validate_with_schema(df_problematic, 'ohlcv')
    nb.log(f"Результат валидации проблемных данных с 'ohlcv':")
    nb.log(f"  - Валидны: {problematic_ohlcv_validation.is_valid}")
    nb.log(f"  - Проблемы: {len(problematic_ohlcv_validation.issues)}")
    nb.log(f"  - Предупреждения: {len(problematic_ohlcv_validation.warnings)}")
    nb.log(f"  - Статистика: {problematic_ohlcv_validation.stats}")
    
    nb.info("8.2. Валидация данных с помощью схемы 'macd':")
    
    # Создаем данные с MACD колонками
    if all(col in df_sample.columns for col in ['macd', 'signal']):
        macd_validation = validate_with_schema(df_sample, 'macd')
        nb.log(f"Результат валидации данных с 'macd':")
        nb.log(f"  - Валидны: {macd_validation.is_valid}")
        nb.log(f"  - Проблемы: {len(macd_validation.issues)}")
        nb.log(f"  - Статистика: {macd_validation.stats}")
    else:
        nb.log("MACD колонки не найдены в sample данных")
    
    nb.info("8.3. Тестирование валидации с несуществующей схемой:")
    
    # Тестируем валидацию с несуществующей схемой
    invalid_schema_validation = validate_with_schema(df_sample, 'non_existent')
    nb.log(f"Результат валидации с несуществующей схемой:")
    nb.log(f"  - Валидны: {invalid_schema_validation.is_valid}")
    nb.log(f"  - Проблемы: {invalid_schema_validation.issues}")
    nb.log(f"  - Рекомендации: {invalid_schema_validation.recommendations}")

nb.wait()

# --- Шаг 9: Создание комплексной схемы валидации ---
nb.step("Шаг 9: Создание комплексной схемы валидации")

nb.info("Демонстрация создания комплексной схемы валидации для финансовых данных.")

with nb.error_handling("Creating comprehensive validation schema"):
    nb.info("9.1. Создание комплексной схемы для финансовых данных:")
    
    # Создаем комплексную схему
    financial_schema = DataSchema('financial_comprehensive')
    
    # Добавляем обязательные поля для OHLCV
    financial_schema.add_required_field('open', float)
    financial_schema.add_required_field('high', float)
    financial_schema.add_required_field('low', float)
    financial_schema.add_required_field('close', float)
    
    # Добавляем опциональные поля
    financial_schema.add_optional_field('volume', float)
    financial_schema.add_optional_field('rsi', float)
    financial_schema.add_optional_field('macd', float)
    
    # Добавляем правила валидации
    financial_schema.add_validation_rule('open', lambda x: x > 0)
    financial_schema.add_validation_rule('high', lambda x: x > 0)
    financial_schema.add_validation_rule('low', lambda x: x > 0)
    financial_schema.add_validation_rule('close', lambda x: x > 0)
    financial_schema.add_validation_rule('volume', lambda x: x >= 0 if x is not None else True)
    financial_schema.add_validation_rule('rsi', lambda x: 0 <= x <= 100 if x is not None else True)
    
    nb.log(f"Создана комплексная финансовая схема:")
    nb.log(f"  - Тип схемы: {financial_schema.schema_type}")
    nb.log(f"  - Обязательные поля: {financial_schema.required_fields}")
    nb.log(f"  - Опциональные поля: {financial_schema.optional_fields}")
    nb.log(f"  - Правила валидации: {len(financial_schema.validation_rules)}")
    
    # Тестируем комплексную схему
    nb.info("9.2. Тестирование комплексной схемы:")
    
    # Создаем тестовые данные
    test_financial_data = pd.DataFrame({
        'open': [3330.0, 3340.0, 3350.0],
        'high': [3340.0, 3350.0, 3360.0],
        'low': [3320.0, 3330.0, 3340.0],
        'close': [3335.0, 3345.0, 3355.0],
        'volume': [100000, 150000, 200000],
        'rsi': [45.5, 55.2, 65.8],
        'macd': [0.2, 0.3, 0.4]
    })
    
    nb.log(f"Создан тестовый DataFrame: {test_financial_data.shape}")
    
    # Валидируем данные
    financial_validation = financial_schema.validate_dataframe(test_financial_data)
    nb.log(f"Результат валидации комплексной схемы:")
    nb.log(f"  - Валидны: {financial_validation.is_valid}")
    nb.log(f"  - Проблемы: {len(financial_validation.issues)}")
    nb.log(f"  - Предупреждения: {len(financial_validation.warnings)}")
    nb.log(f"  - Статистика: {financial_validation.stats}")

nb.wait()

# --- Шаг 10: Анализ результатов валидации ---
nb.step("Шаг 10: Анализ результатов валидации")

nb.info("Анализ результатов валидации различных типов данных.")

with nb.error_handling("Analyzing validation results"):
    nb.info("10.1. Сводка результатов валидации:")
    
    # Собираем все результаты валидации
    validation_results = {
        'OHLCV корректные': validate_with_schema(df_sample, 'ohlcv'),
        'OHLCV проблемные': validate_with_schema(df_problematic, 'ohlcv'),
        'MACD тест': validate_with_schema(df_sample, 'macd') if 'macd' in df_sample.columns else None,
        'RSI тест': validate_with_schema(df_sample, 'rsi') if 'rsi' in df_sample.columns else None,
        'Комплексная схема': financial_validation if 'financial_validation' in locals() else None
    }
    
    nb.log("Результаты валидации по схемам:")
    for name, result in validation_results.items():
        if result:
            status = "✅ Валидны" if result.is_valid else "❌ Невалидны"
            nb.log(f"  - {name}: {status}")
            nb.log(f"    * Проблемы: {len(result.issues)}")
            nb.log(f"    * Предупреждения: {len(result.warnings)}")
            if result.stats:
                nb.log(f"    * Статистика: {result.stats}")
        else:
            nb.log(f"  - {name}: Не протестировано")
    
    nb.info("10.2. Анализ качества данных:")
    
    # Анализируем качество sample данных
    sample_quality = {
        'Всего строк': len(df_sample),
        'Всего колонок': len(df_sample.columns),
        'Числовые колонки': len(df_sample.select_dtypes(include=[np.number]).columns),
        'Пропущенные значения': df_sample.isnull().sum().sum(),
        'Отрицательные цены': ((df_sample[['open', 'high', 'low', 'close']] < 0).any(axis=1)).sum(),
        'Логические ошибки OHLC': ((df_sample['high'] < df_sample['low']).sum())
    }
    
    nb.log("Качество sample данных:")
    for metric, value in sample_quality.items():
        nb.log(f"  - {metric}: {value}")
    
    # Анализируем качество проблемных данных
    problematic_quality = {
        'Всего строк': len(df_problematic),
        'Всего колонок': len(df_problematic.columns),
        'Пропущенные значения': df_problematic.isnull().sum().sum(),
        'Отрицательные цены': ((df_problematic[['open', 'high', 'low', 'close']] < 0).any(axis=1)).sum(),
        'Логические ошибки OHLC': ((df_problematic['high'] < df_problematic['low']).sum())
    }
    
    nb.log("Качество проблемных данных:")
    for metric, value in problematic_quality.items():
        nb.log(f"  - {metric}: {value}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные функции модуля bquant.data.schemas:")
nb.log("✅ OHLCVRecord - валидация отдельных OHLCV записей")
nb.log("✅ DataSourceConfig - конфигурация источников данных")
nb.log("✅ DataSchema - базовый класс для создания схем")
nb.log("✅ OHLCVSchema - специализированная схема для OHLCV данных")
nb.log("✅ IndicatorSchema - схемы для технических индикаторов")
nb.log("✅ get_schema() - получение предопределенных схем")
nb.log("✅ validate_with_schema() - валидация DataFrame по схемам")

nb.info("Модуль schemas успешно продемонстрировал:")
nb.log("🔧 Создание и настройку схем валидации")
nb.log("🔧 Валидацию различных типов финансовых данных")
nb.log("🔧 Работу с конфигурацией источников данных")
nb.log("🔧 Создание пользовательских схем валидации")
nb.log("🔧 Анализ качества данных")

nb.info("Это демонстрирует возможности системы валидации данных BQuant для обеспечения качества и консистентности финансовых данных.")

nb.finish()
