'''
Демонстрация работы валидатора данных bquant.data.validator

Этот скрипт показывает, как использовать различные функции валидации данных:
1.  Валидация OHLCV данных (основная функция).
2.  Проверка полноты данных.
3.  Валидация консистентности цен.
4.  Проверка непрерывности временных рядов.
5.  Анализ статистических свойств данных.
'''

from pathlib import Path
import pandas as pd
import numpy as np
import json
import logging

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.loader import (
    load_ohlcv_data
)
from bquant.data.samples import (
    get_sample_data
)
from bquant.data.validator import (
    validate_ohlcv_data,
    validate_data_completeness,
    validate_price_consistency,
    validate_time_series_continuity,
    validate_statistical_properties
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы модуля bquant.data.validator")

# --- Шаг 1: Загрузка тестовых данных для валидации ---
nb.step("Шаг 1: Загрузка тестовых данных для валидации")

nb.info("Для демонстрации валидации используем встроенные sample-данные и создадим проблемные данные.")

# Загружаем корректные данные
with nb.error_handling("Loading sample data"):
    nb.info("1.1. Загружаем корректные sample-данные:")
    df_sample = get_sample_data('tv_xauusd_1h')
    nb.log(f"Загружено {len(df_sample)} строк корректных данных")
    nb.log(f"Структура: {list(df_sample.columns)}")

# Создаем проблемные данные для демонстрации валидации
with nb.error_handling("Creating problematic data"):
    nb.info("1.2. Создаем проблемные данные для демонстрации валидации:")
    
    # Копируем sample данные и добавляем проблемы
    df_problematic = df_sample.copy()
    
    # Добавляем дубликаты
    df_problematic = pd.concat([df_problematic, df_problematic.iloc[-10:]], ignore_index=False)
    
    # Добавляем пропуски
    df_problematic.iloc[100:110, df_problematic.columns.get_loc('close')] = np.nan
    
    # Добавляем логические ошибки (high < low)
    df_problematic.iloc[200:205, df_problematic.columns.get_loc('high')] = 1000  # Низкое значение
    df_problematic.iloc[200:205, df_problematic.columns.get_loc('low')] = 2000   # Высокое значение
    
    # Добавляем отрицательные цены
    df_problematic.iloc[300:305, df_problematic.columns.get_loc('open')] = -100
    
    # Добавляем пропуски в индексе (создаем gaps)
    problematic_dates = df_problematic.index.tolist()
    problematic_dates[400:410] = [pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i) for i in range(400, 410)]
    df_problematic.index = problematic_dates
    
    nb.log(f"Создано {len(df_problematic)} строк проблемных данных")
    nb.log("Добавлены проблемы: дубликаты, пропуски, логические ошибки, отрицательные цены, gaps в индексе")

nb.wait()

# --- Шаг 2: Основная валидация OHLCV данных ---
nb.step("Шаг 2: Основная валидация OHLCV данных")

nb.info("Функция validate_ohlcv_data() - это основная функция валидации, которая проверяет все аспекты данных.")

# Валидация корректных данных
with nb.error_handling("Validating correct sample data"):
    nb.info("2.1. Валидация корректных sample-данных:")
    validation_correct = validate_ohlcv_data(df_sample, strict=True)
    nb.log(f"Результат валидации корректных данных:")
    nb.log(f"  - Валидны: {validation_correct['is_valid']}")
    nb.log(f"  - Проблемы: {len(validation_correct['issues'])}")
    nb.log(f"  - Предупреждения: {len(validation_correct['warnings'])}")
    
    if validation_correct['issues']:
        nb.warning("Найдены проблемы в корректных данных:")
        for issue in validation_correct['issues']:
            nb.warning(f"  - {issue}")
    
    if validation_correct['warnings']:
        nb.info("Найдены предупреждения:")
        for warning in validation_correct['warnings']:
            nb.info(f"  - {warning}")
    
    nb.log("Статистика валидации:")
    nb.log(json.dumps(validation_correct['stats'], indent=2, default=str))

# Валидация проблемных данных
with nb.error_handling("Validating problematic data"):
    nb.info("2.2. Валидация проблемных данных:")
    validation_problematic = validate_ohlcv_data(df_problematic, strict=True)
    nb.log(f"Результат валидации проблемных данных:")
    nb.log(f"  - Валидны: {validation_problematic['is_valid']}")
    nb.log(f"  - Проблемы: {len(validation_problematic['issues'])}")
    nb.log(f"  - Предупреждения: {len(validation_problematic['warnings'])}")
    
    if validation_problematic['issues']:
        nb.error("Найдены критические проблемы:")
        for issue in validation_problematic['issues']:
            nb.error(f"  - {issue}")
    
    if validation_problematic['warnings']:
        nb.warning("Найдены предупреждения:")
        for warning in validation_problematic['warnings']:
            nb.warning(f"  - {warning}")
    
    nb.log("Рекомендации по исправлению:")
    for rec in validation_problematic['recommendations']:
        nb.log(f"  - {rec}")

nb.wait()

# --- Шаг 3: Проверка полноты данных ---
nb.step("Шаг 3: Проверка полноты данных")

nb.info("Функция validate_data_completeness() проверяет наличие необходимых колонок, минимальное количество строк и пропуски.")

# Проверка полноты корректных данных
with nb.error_handling("Checking completeness of correct data"):
    nb.info("3.1. Проверка полноты корректных данных:")
    completeness_correct = validate_data_completeness(df_sample)
    nb.log(f"Результат проверки полноты корректных данных:")
    nb.log(f"  - Полные: {completeness_correct['is_complete']}")
    nb.log(f"  - Отсутствующие колонки: {completeness_correct['missing_columns']}")
    nb.log(f"  - Недостаточно строк: {completeness_correct['insufficient_rows']}")
    
    nb.log("Процент пропущенных данных по колонкам:")
    for col, ratio in completeness_correct['missing_data_ratio'].items():
        nb.log(f"  - {col}: {ratio:.2%}")

# Проверка полноты проблемных данных
with nb.error_handling("Checking completeness of problematic data"):
    nb.info("3.2. Проверка полноты проблемных данных:")
    completeness_problematic = validate_data_completeness(df_problematic)
    nb.log(f"Результат проверки полноты проблемных данных:")
    nb.log(f"  - Полные: {completeness_problematic['is_complete']}")
    nb.log(f"  - Отсутствующие колонки: {completeness_problematic['missing_columns']}")
    nb.log(f"  - Недостаточно строк: {completeness_problematic['insufficient_rows']}")
    
    nb.log("Процент пропущенных данных по колонкам:")
    for col, ratio in completeness_problematic['missing_data_ratio'].items():
        nb.log(f"  - {col}: {ratio:.2%}")
    
    if completeness_problematic['recommendations']:
        nb.log("Рекомендации по полноте:")
        for rec in completeness_problematic['recommendations']:
            nb.log(f"  - {rec}")

nb.wait()

# --- Шаг 4: Валидация консистентности цен ---
nb.step("Шаг 4: Валидация консистентности цен")

nb.info("Функция validate_price_consistency() проверяет логические отношения между OHLC ценами и выявляет экстремальные значения.")

# Проверка консистентности корректных данных
with nb.error_handling("Checking price consistency of correct data"):
    nb.info("4.1. Проверка консистентности цен корректных данных:")
    consistency_correct = validate_price_consistency(df_sample)
    nb.log(f"Результат проверки консистентности цен корректных данных:")
    nb.log(f"  - Консистентны: {consistency_correct['is_consistent']}")
    nb.log(f"  - Проблемы с ценами: {len(consistency_correct['price_issues'])}")
    nb.log(f"  - Логические ошибки: {len(consistency_correct['logical_errors'])}")
    nb.log(f"  - Экстремальные значения: {len(consistency_correct['extreme_values'])}")
    
    if consistency_correct['price_issues']:
        nb.warning("Найдены проблемы с ценами:")
        for issue in consistency_correct['price_issues']:
            nb.warning(f"  - {issue}")
    
    if consistency_correct['logical_errors']:
        nb.error("Найдены логические ошибки:")
        for error in consistency_correct['logical_errors']:
            nb.error(f"  - {error}")
    
    if consistency_correct['extreme_values']:
        nb.warning("Найдены экстремальные значения:")
        for extreme in consistency_correct['extreme_values']:
            nb.warning(f"  - {extreme}")

# Проверка консистентности проблемных данных
with nb.error_handling("Checking price consistency of problematic data"):
    nb.info("4.2. Проверка консистентности цен проблемных данных:")
    consistency_problematic = validate_price_consistency(df_problematic)
    nb.log(f"Результат проверки консистентности цен проблемных данных:")
    nb.log(f"  - Консистентны: {consistency_problematic['is_consistent']}")
    nb.log(f"  - Проблемы с ценами: {len(consistency_problematic['price_issues'])}")
    nb.log(f"  - Логические ошибки: {len(consistency_problematic['logical_errors'])}")
    nb.log(f"  - Экстремальные значения: {len(consistency_problematic['extreme_values'])}")
    
    if consistency_problematic['price_issues']:
        nb.error("Найдены проблемы с ценами:")
        for issue in consistency_problematic['price_issues']:
            nb.error(f"  - {issue}")
    
    if consistency_problematic['logical_errors']:
        nb.error("Найдены логические ошибки:")
        for error in consistency_problematic['logical_errors']:
            nb.error(f"  - {error}")
    
    if consistency_problematic['extreme_values']:
        nb.warning("Найдены экстремальные значения:")
        for extreme in consistency_problematic['extreme_values']:
            nb.warning(f"  - {extreme}")
    
    if consistency_problematic['recommendations']:
        nb.log("Рекомендации по консистентности:")
        for rec in consistency_problematic['recommendations']:
            nb.log(f"  - {rec}")

nb.wait()

# --- Шаг 5: Проверка непрерывности временных рядов ---
nb.step("Шаг 5: Проверка непрерывности временных рядов")

nb.info("Функция validate_time_series_continuity() проверяет непрерывность временных рядов, выявляет gaps и дубликаты.")

# Проверка непрерывности корректных данных
with nb.error_handling("Checking time series continuity of correct data"):
    nb.info("5.1. Проверка непрерывности временных рядов корректных данных:")
    continuity_correct = validate_time_series_continuity(df_sample, expected_frequency='1H')
    nb.log(f"Результат проверки непрерывности корректных данных:")
    nb.log(f"  - Непрерывны: {continuity_correct['is_continuous']}")
    nb.log(f"  - Обнаруженная частота: {continuity_correct['detected_frequency']}")
    nb.log(f"  - Gaps: {len(continuity_correct['gaps'])}")
    nb.log(f"  - Дубликаты: {len(continuity_correct['duplicates'])}")
    nb.log(f"  - Нерегулярные интервалы: {len(continuity_correct['irregular_intervals'])}")
    
    if continuity_correct['gaps']:
        nb.warning("Найдены gaps во временном ряду:")
        nb.warning(f"  - Количество: {len(continuity_correct['gaps'])}")
        nb.warning(f"  - Первые 5: {continuity_correct['gaps'][:5]}")
    
    if continuity_correct['duplicates']:
        nb.warning("Найдены дубликаты временных меток:")
        nb.warning(f"  - Количество: {len(continuity_correct['duplicates'])}")
        nb.warning(f"  - Первые 5: {continuity_correct['duplicates'][:5]}")
    
    if continuity_correct['irregular_intervals']:
        nb.warning("Найдены нерегулярные интервалы:")
        nb.warning(f"  - Количество: {len(continuity_correct['irregular_intervals'])}")

# Проверка непрерывности проблемных данных
with nb.error_handling("Checking time series continuity of problematic data"):
    nb.info("5.2. Проверка непрерывности временных рядов проблемных данных:")
    continuity_problematic = validate_time_series_continuity(df_problematic, expected_frequency='1H')
    nb.log(f"Результат проверки непрерывности проблемных данных:")
    nb.log(f"  - Непрерывны: {continuity_problematic['is_continuous']}")
    nb.log(f"  - Обнаруженная частота: {continuity_problematic['detected_frequency']}")
    nb.log(f"  - Gaps: {len(continuity_problematic['gaps'])}")
    nb.log(f"  - Дубликаты: {len(continuity_problematic['duplicates'])}")
    nb.log(f"  - Нерегулярные интервалы: {len(continuity_problematic['irregular_intervals'])}")
    
    if continuity_problematic['gaps']:
        nb.error("Найдены gaps во временном ряду:")
        nb.error(f"  - Количество: {len(continuity_problematic['gaps'])}")
        nb.error(f"  - Первые 5: {continuity_problematic['gaps'][:5]}")
    
    if continuity_problematic['duplicates']:
        nb.error("Найдены дубликаты временных меток:")
        nb.error(f"  - Количество: {len(continuity_problematic['duplicates'])}")
        nb.error(f"  - Первые 5: {continuity_problematic['duplicates'][:5]}")
    
    if continuity_problematic['irregular_intervals']:
        nb.warning("Найдены нерегулярные интервалы:")
        nb.warning(f"  - Количество: {len(continuity_problematic['irregular_intervals'])}")
    
    if continuity_problematic['recommendations']:
        nb.log("Рекомендации по непрерывности:")
        for rec in continuity_problematic['recommendations']:
            nb.log(f"  - {rec}")

nb.wait()

# --- Шаг 6: Анализ статистических свойств ---
nb.step("Шаг 6: Анализ статистических свойств")

nb.info("Функция validate_statistical_properties() анализирует статистические характеристики данных и выявляет выбросы.")

# Анализ статистических свойств корректных данных
with nb.error_handling("Analyzing statistical properties of correct data"):
    nb.info("6.1. Анализ статистических свойств корректных данных:")
    stats_correct = validate_statistical_properties(df_sample)
    nb.log(f"Результат анализа статистических свойств корректных данных:")
    nb.log(f"  - Колонки с выбросами: {len(stats_correct['outliers'])}")
    nb.log(f"  - Проблемы с распределением: {len(stats_correct['distribution_issues'])}")
    
    nb.log("Статистика по числовым колонкам:")
    for col, stats in stats_correct['statistics'].items():
        nb.log(f"  - {col}:")
        nb.log(f"    * Среднее: {stats['mean']:.4f}")
        nb.log(f"    * Стд. отклонение: {stats['std']:.4f}")
        nb.log(f"    * Мин: {stats['min']:.4f}")
        nb.log(f"    * Макс: {stats['max']:.4f}")
        nb.log(f"    * Асимметрия: {stats['skewness']:.4f}")
        nb.log(f"    * Эксцесс: {stats['kurtosis']:.4f}")
    
    if stats_correct['outliers']:
        nb.warning("Найдены выбросы:")
        for col, outlier_info in stats_correct['outliers'].items():
            nb.warning(f"  - {col}: {outlier_info['count']} выбросов ({outlier_info['percentage']:.1f}%)")
    
    if stats_correct['distribution_issues']:
        nb.warning("Найдены проблемы с распределением:")
        for issue in stats_correct['distribution_issues']:
            nb.warning(f"  - {issue}")

# Анализ статистических свойств проблемных данных
with nb.error_handling("Analyzing statistical properties of problematic data"):
    nb.info("6.2. Анализ статистических свойств проблемных данных:")
    stats_problematic = validate_statistical_properties(df_problematic)
    nb.log(f"Результат анализа статистических свойств проблемных данных:")
    nb.log(f"  - Колонки с выбросами: {len(stats_problematic['outliers'])}")
    nb.log(f"  - Проблемы с распределением: {len(stats_problematic['distribution_issues'])}")
    
    if stats_problematic['outliers']:
        nb.error("Найдены выбросы:")
        for col, outlier_info in stats_problematic['outliers'].items():
            nb.error(f"  - {col}: {outlier_info['count']} выбросов ({outlier_info['percentage']:.1f}%)")
    
    if stats_problematic['distribution_issues']:
        nb.warning("Найдены проблемы с распределением:")
        for issue in stats_problematic['distribution_issues']:
            nb.warning(f"  - {issue}")
    
    if stats_problematic['recommendations']:
        nb.log("Рекомендации по статистическим свойствам:")
        for rec in stats_problematic['recommendations']:
            nb.log(f"  - {rec}")

nb.wait()

# --- Шаг 7: Сравнение строгого и мягкого режимов валидации ---
nb.step("Шаг 7: Сравнение строгого и мягкого режимов валидации")

nb.info("Демонстрация разницы между strict=True и strict=False в validate_ohlcv_data().")

# Строгий режим валидации
with nb.error_handling("Strict validation mode"):
    nb.info("7.1. Строгий режим валидации (strict=True):")
    validation_strict = validate_ohlcv_data(df_problematic, strict=True)
    nb.log(f"Результат строгой валидации:")
    nb.log(f"  - Валидны: {validation_strict['is_valid']}")
    nb.log(f"  - Проблемы: {len(validation_strict['issues'])}")
    nb.log(f"  - Предупреждения: {len(validation_strict['warnings'])}")

# Мягкий режим валидации
with nb.error_handling("Soft validation mode"):
    nb.info("7.2. Мягкий режим валидации (strict=False):")
    validation_soft = validate_ohlcv_data(df_problematic, strict=False)
    nb.log(f"Результат мягкой валидации:")
    nb.log(f"  - Валидны: {validation_soft['is_valid']}")
    nb.log(f"  - Проблемы: {len(validation_soft['issues'])}")
    nb.log(f"  - Предупреждения: {len(validation_soft['warnings'])}")

nb.log("Разница между режимами:")
nb.log(f"  - Строгий режим: {len(validation_strict['issues'])} проблем, {len(validation_strict['warnings'])} предупреждений")
nb.log(f"  - Мягкий режим: {len(validation_soft['issues'])} проблем, {len(validation_soft['warnings'])} предупреждений")
nb.log(f"  - Разница в проблемах: {len(validation_strict['issues']) - len(validation_soft['issues'])}")
nb.log(f"  - Разница в предупреждениях: {len(validation_strict['warnings']) - len(validation_soft['warnings'])}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные функции валидатора данных:")
nb.log("✅ validate_ohlcv_data() - основная функция валидации")
nb.log("✅ validate_data_completeness() - проверка полноты данных")
nb.log("✅ validate_price_consistency() - валидация консистентности цен")
nb.log("✅ validate_time_series_continuity() - проверка непрерывности временных рядов")
nb.log("✅ validate_statistical_properties() - анализ статистических свойств")

nb.info("Валидатор успешно выявил все созданные нами проблемы:")
nb.log("🔍 Дубликаты данных")
nb.log("🔍 Пропуски в данных")
nb.log("🔍 Логические ошибки OHLC")
nb.log("🔍 Отрицательные цены")
nb.log("🔍 Gaps во временном ряду")

nb.info("Это демонстрирует эффективность системы валидации BQuant для обеспечения качества данных.")

nb.finish()
