'''
Демонстрация работы высокоуровневых калькуляторов индикаторов bquant.indicators.calculators

Этот скрипт показывает, как использовать удобные функции для расчета технических индикаторов:
1.  IndicatorCalculator - основной калькулятор для работы с индикаторами
2.  BatchCalculator - пакетная обработка множественных датасетов
3.  Удобные функции для расчета популярных индикаторов
4.  Создание стандартных наборов индикаторов
5.  Валидация данных для индикаторов
6.  Управление результатами и кэшированием
'''

from pathlib import Path
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from bquant.indicators.base import IndicatorResult

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.indicators.calculators import (
    IndicatorCalculator,
    BatchCalculator,
    calculate_indicator,
    calculate_macd,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_moving_averages,
    create_indicator_suite,
    get_available_indicators,
    validate_indicator_data
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы высокоуровневых калькуляторов индикаторов bquant.indicators.calculators")


def calculate_with_alias(
    calculator: IndicatorCalculator,
    indicator_name: str,
    alias: Optional[str] = None,
    **params: Any,
) -> IndicatorResult:
    """Вычислить индикатор и сохранить результат под удобным псевдонимом."""

    alias_name = alias or indicator_name
    base_result = calculator.calculate(indicator_name, **params)

    metadata = dict(base_result.metadata or {})
    metadata.update({"alias": alias_name, **params})

    data = base_result.data.copy()
    if alias_name != indicator_name:
        if data.shape[1] == 1:
            column_name = data.columns[0]
            data = data.rename(columns={column_name: alias_name})
        else:
            data = data.add_prefix(f"{alias_name}_")

    aliased_result = IndicatorResult(
        name=alias_name,
        data=data,
        config=base_result.config,
        metadata=metadata,
    )

    calculator.results[alias_name] = aliased_result
    if alias_name != indicator_name and indicator_name in calculator.results:
        del calculator.results[indicator_name]

    return aliased_result

# --- Шаг 1: Загрузка тестовых данных ---
nb.step("Шаг 1: Загрузка тестовых данных")

nb.info("Для демонстрации калькуляторов индикаторов используем sample-данные.")

with nb.error_handling("Loading sample data"):
    nb.info("1.1. Загружаем sample-данные для тестирования:")
    df_sample = get_sample_data('tv_xauusd_1h')
    
    # Преобразуем колонку time в DatetimeIndex для корректной работы
    if 'time' in df_sample.columns:
        df_sample = df_sample.set_index('time')
        nb.log("Колонка 'time' преобразована в DatetimeIndex")
    
    nb.log(f"Загружено {len(df_sample)} строк данных")
    nb.log(f"Структура: {list(df_sample.columns)}")
    nb.log(f"Тип индекса: {type(df_sample.index)}")
    nb.log(f"Диапазон дат: {df_sample.index.min()} - {df_sample.index.max()}")
    
    nb.info("1.2. Создание дополнительных датасетов для BatchCalculator:")
    
    # Создаем дополнительные датасеты для демонстрации BatchCalculator
    df_sample_2 = df_sample.iloc[::2].copy()  # Каждая вторая строка
    df_sample_3 = df_sample.iloc[::3].copy()  # Каждая третья строка
    
    nb.log(f"Создано 3 датасета:")
    nb.log(f"  - Основной: {len(df_sample)} строк")
    nb.log(f"  - Датасет 2: {len(df_sample_2)} строк")
    nb.log(f"  - Датасет 3: {len(df_sample_3)} строк")

nb.wait()

# --- Шаг 2: Работа с IndicatorCalculator ---
nb.step("Шаг 2: Работа с IndicatorCalculator")

nb.info("IndicatorCalculator - это основной класс для удобного расчета технических индикаторов.")

with nb.error_handling("Testing IndicatorCalculator"):
    nb.info("2.1. Создание экземпляра IndicatorCalculator:")
    
    # Создаем калькулятор
    calculator = IndicatorCalculator(df_sample, auto_load_libraries=True)
    nb.log(f"Создан IndicatorCalculator:")
    nb.log(f"  - Размер данных: {calculator.data.shape}")
    nb.log(f"  - Автозагрузка библиотек: {True}")
    nb.log(f"  - Кэшированных результатов: {len(calculator.results)}")
    
    nb.info("2.2. Расчет одиночного индикатора SMA:")
    
    # Вычисляем SMA с периодом 20
    sma_result = calculator.calculate('sma', period=20)
    nb.log(f"Результат расчета SMA(20):")
    nb.log(f"  - Название: {sma_result.name}")
    nb.log(f"  - Размер данных: {sma_result.data.shape}")
    nb.log(f"  - Колонки: {list(sma_result.data.columns)}")
    nb.log(f"  - Первые 5 значений:")
    nb.log(str(sma_result.data.head()))
    
    nb.info("2.3. Расчет множественных индикаторов:")
    
    # Определяем набор индикаторов для расчета
    indicators_to_calculate = {
        'ema': {'period': 12},
        'rsi': {'period': 14},
        'bbands': {'period': 20, 'std_dev': 2.0}
    }
    
    # Вычисляем все индикаторы
    multiple_results = calculator.calculate_multiple(indicators_to_calculate)
    nb.log(f"Вычислено {len(multiple_results)} индикаторов:")
    for name, result in multiple_results.items():
        nb.log(f"  - {name}: {result.data.shape}")
    
    nb.info("2.4. Получение и анализ результатов:")
    
    # Получаем все результаты
    all_results = calculator.get_all_results()
    nb.log(f"Всего кэшированных результатов: {len(all_results)}")
    nb.log(f"Доступные результаты: {list(all_results.keys())}")
    
    # Получаем конкретный результат
    rsi_result = calculator.get_result('rsi')
    if rsi_result:
        nb.log(f"RSI результат получен:")
        nb.log(f"  - Размер: {rsi_result.data.shape}")
        nb.log(f"  - Статистика: min={rsi_result.data.iloc[:, 0].min():.2f}, max={rsi_result.data.iloc[:, 0].max():.2f}")

nb.wait()

# --- Шаг 3: Объединение результатов индикаторов ---
nb.step("Шаг 3: Объединение результатов индикаторов")

nb.info("IndicatorCalculator позволяет объединять результаты различных индикаторов в единый DataFrame.")

with nb.error_handling("Testing result combination"):
    nb.info("3.1. Объединение всех результатов:")
    
    # Объединяем все результаты в один DataFrame
    combined_data = calculator.combine_results()
    nb.log(f"Объединенный датасет:")
    nb.log(f"  - Размер: {combined_data.shape}")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {combined_data.shape[1] - len(df_sample.columns)}")
    nb.log(f"  - Всего колонок: {combined_data.shape[1]}")
    
    nb.info("3.2. Объединение выбранных индикаторов:")
    
    # Объединяем только выбранные индикаторы
    selected_indicators = ['sma', 'ema', 'rsi']
    selected_combined = calculator.combine_results(selected_indicators)
    nb.log(f"Выборочно объединенный датасет:")
    nb.log(f"  - Размер: {selected_combined.shape}")
    nb.log(f"  - Выбранные индикаторы: {selected_indicators}")
    
    nb.info("3.3. Анализ структуры объединенных данных:")
    
    # Показываем структуру объединенных данных
    nb.log(f"Структура объединенных данных:")
    nb.log(f"  - OHLCV колонки: {[col for col in combined_data.columns if col in ['open', 'high', 'low', 'close', 'volume']]}")
    nb.log(f"  - Индикаторные колонки: {[col for col in combined_data.columns if col not in ['open', 'high', 'low', 'close', 'volume']]}")
    
    # Показываем первые несколько колонок
    nb.log(f"Первые 10 колонок:")
    nb.log(str(combined_data.columns[:10].tolist()))

nb.wait()

# --- Шаг 4: Удобные функции для расчета индикаторов ---
nb.step("Шаг 4: Удобные функции для расчета индикаторов")

nb.info("Модуль предоставляет удобные функции для быстрого расчета популярных индикаторов.")

with nb.error_handling("Testing convenience functions"):
    nb.info("4.1. Расчет MACD через удобную функцию:")
    
    # Вычисляем MACD
    macd_data = calculate_macd(df_sample, fast=12, slow=26, signal=9)
    nb.log(f"MACD рассчитан через удобную функцию:")
    nb.log(f"  - Размер: {macd_data.shape}")
    nb.log(f"  - Колонки: {list(macd_data.columns)}")
    nb.log(f"  - Первые 5 значений MACD:")
    nb.log(str(macd_data.head()))
    
    nb.info("4.2. Расчет RSI через удобную функцию:")
    
    # Вычисляем RSI
    rsi_series = calculate_rsi(df_sample, period=14)
    nb.log(f"RSI рассчитан через удобную функцию:")
    nb.log(f"  - Тип: {type(rsi_series)}")
    nb.log(f"  - Размер: {len(rsi_series)}")
    nb.log(f"  - Статистика: min={rsi_series.min():.2f}, max={rsi_series.max():.2f}, mean={rsi_series.mean():.2f}")
    
    nb.info("4.3. Расчет Bollinger Bands через удобную функцию:")
    
    # Вычисляем Bollinger Bands
    bb_data = calculate_bollinger_bands(df_sample, period=20, std_dev=2.0)
    nb.log(f"Bollinger Bands рассчитаны через удобную функцию:")
    nb.log(f"  - Размер: {bb_data.shape}")
    nb.log(f"  - Колонки: {list(bb_data.columns)}")
    nb.log(f"  - Первые 5 значений верхней полосы:")
    nb.log(str(bb_data.iloc[:5, 0]))  # Первая колонка - верхняя полоса
    
    nb.info("4.4. Расчет множественных скользящих средних:")
    
    # Вычисляем множественные скользящие средние
    ma_periods = [10, 20, 50]
    ma_data = calculate_moving_averages(df_sample, periods=ma_periods)
    nb.log(f"Множественные скользящие средние рассчитаны:")
    nb.log(f"  - Размер: {ma_data.shape}")
    nb.log(f"  - Периоды: {ma_periods}")
    nb.log(f"  - Колонки: {list(ma_data.columns)}")

nb.wait()

# --- Шаг 5: Создание стандартных наборов индикаторов ---
nb.step("Шаг 5: Создание стандартных наборов индикаторов")

nb.info("Модуль предоставляет функцию для создания стандартных наборов технических индикаторов.")

with nb.error_handling("Testing indicator suites"):
    nb.info("5.1. Создание стандартного набора индикаторов:")
    
    # Создаем стандартный набор
    standard_suite = create_indicator_suite(df_sample)
    nb.log(f"Стандартный набор индикаторов создан:")
    nb.log(f"  - Количество индикаторов: {len(standard_suite)}")
    nb.log(f"  - Доступные индикаторы: {list(standard_suite.keys())}")
    
    nb.info("5.2. Анализ результатов стандартного набора:")
    
    # Анализируем каждый индикатор в наборе
    for name, result in standard_suite.items():
        nb.log(f"  - {name}:")
        nb.log(f"    * Размер данных: {result.data.shape}")
        nb.log(f"    * Колонки: {list(result.data.columns)}")
        nb.log(f"    * Метаданные: {result.metadata}")
    
    nb.info("5.3. Создание пользовательского набора индикаторов:")

    # Создаем пользовательский набор через IndicatorCalculator
    custom_calculator = IndicatorCalculator(df_sample, auto_load_libraries=False)

    custom_specs = {
        'sma_5': ('sma', {'period': 5}),
        'sma_10': ('sma', {'period': 10}),
        'ema_5': ('ema', {'period': 5}),
        'ema_10': ('ema', {'period': 10}),
        'rsi_7': ('rsi', {'period': 7}),
        'rsi_21': ('rsi', {'period': 21})
    }

    custom_suite: Dict[str, IndicatorResult] = {}
    for alias, (indicator_name, params) in custom_specs.items():
        custom_suite[alias] = calculate_with_alias(
            custom_calculator,
            indicator_name,
            alias=alias,
            **params,
        )

    nb.log("Пользовательский набор индикаторов создан:")
    nb.log(f"  - Количество индикаторов: {len(custom_suite)}")
    nb.log(f"  - Доступные индикаторы: {list(custom_suite.keys())}")

    for alias, result in custom_suite.items():
        nb.log(f"  - {alias}:")
        nb.log(f"    * Размер данных: {result.data.shape}")
        nb.log(f"    * Колонки: {list(result.data.columns)}")
        nb.log(f"    * Метаданные: {result.metadata}")

nb.wait()

# --- Шаг 6: Работа с BatchCalculator ---
nb.step("Шаг 6: Работа с BatchCalculator")

nb.info("BatchCalculator позволяет обрабатывать множественные датасеты одновременно.")

with nb.error_handling("Testing BatchCalculator"):
    nb.info("6.1. Создание BatchCalculator:")
    
    # Создаем словарь датасетов
    datasets = {
        'main': df_sample,
        'subset_2': df_sample_2,
        'subset_3': df_sample_3
    }
    
    batch_calculator = BatchCalculator(datasets)
    nb.log(f"BatchCalculator создан:")
    nb.log(f"  - Количество датасетов: {len(batch_calculator.datasets)}")
    nb.log(f"  - Названия датасетов: {list(batch_calculator.datasets.keys())}")
    
    nb.info("6.2. Расчет одного индикатора для всех датасетов:")
    
    # Вычисляем SMA для всех датасетов
    sma_batch_results = batch_calculator.calculate_for_all('sma', period=20)
    nb.log(f"SMA(20) рассчитан для всех датасетов:")
    for dataset_name, result in sma_batch_results.items():
        nb.log(f"  - {dataset_name}: {result.data.shape}")
    
    nb.info("6.3. Расчет стандартного набора для всех датасетов:")
    
    # Вычисляем стандартный набор для всех датасетов
    suite_batch_results = batch_calculator.calculate_suite_for_all()
    nb.log(f"Стандартный набор рассчитан для всех датасетов:")
    for dataset_name, suite_results in suite_batch_results.items():
        nb.log(f"  - {dataset_name}: {len(suite_results)} индикаторов")
        nb.log(f"    * Доступные: {list(suite_results.keys())}")

nb.wait()

# --- Шаг 7: Валидация данных для индикаторов ---
nb.step("Шаг 7: Валидация данных для индикаторов")

nb.info("Модуль предоставляет функции для валидации данных без выполнения расчетов.")

with nb.error_handling("Testing data validation"):
    nb.info("7.1. Валидация корректных данных:")
    
    # Валидируем корректные данные для различных индикаторов
    validation_tests = [
        ('sma', {'period': 20}),
        ('ema', {'period': 12}),
        ('rsi', {'period': 14}),
        ('bbands', {'period': 20, 'std_dev': 2.0})
    ]
    
    nb.log(f"Валидация данных для различных индикаторов:")
    for indicator_name, params in validation_tests:
        is_valid = validate_indicator_data(df_sample, indicator_name, **params)
        nb.log(f"  - {indicator_name}: {'✅ Валидны' if is_valid else '❌ Невалидны'}")
    
    nb.info("7.2. Валидация некорректных данных:")
    
    # Создаем некорректные данные
    df_invalid = df_sample[['open', 'volume']].copy()  # Убираем high, low, close
    
    nb.log(f"Валидация некорректных данных:")
    for indicator_name, params in validation_tests:
        is_valid = validate_indicator_data(df_invalid, indicator_name, **params)
        nb.log(f"  - {indicator_name}: {'✅ Валидны' if is_valid else '❌ Невалидны'}")
    
    nb.info("7.3. Валидация данных с недостаточным количеством записей:")
    
    # Создаем короткие данные
    df_short = df_sample.head(5)  # Только 5 записей
    
    nb.log(f"Валидация коротких данных:")
    for indicator_name, params in validation_tests:
        is_valid = validate_indicator_data(df_short, indicator_name, **params)
        nb.log(f"  - {indicator_name}: {'✅ Валидны' if is_valid else '❌ Невалидны'}")

nb.wait()

# --- Шаг 8: Получение информации о доступных индикаторах ---
nb.step("Шаг 8: Получение информации о доступных индикаторах")

nb.info("Модуль предоставляет функции для получения информации о доступных индикаторах.")

with nb.error_handling("Testing indicator information"):
    nb.info("8.1. Получение списка доступных индикаторов:")
    
    # Получаем список всех доступных индикаторов
    available_indicators = get_available_indicators()
    nb.log(f"Доступные индикаторы:")
    nb.log(f"  - Общее количество: {len(available_indicators)}")
    
    # Группируем по источникам
    sources = {}
    for name, source in available_indicators.items():
        if source not in sources:
            sources[source] = []
        sources[source].append(name)
    
    for source, indicators in sources.items():
        nb.log(f"  - {source}: {len(indicators)} индикаторов")
        nb.log(f"    * Примеры: {indicators[:5]}")  # Показываем первые 5
    
    nb.info("8.2. Анализ типов индикаторов:")
    
    # Анализируем типы индикаторов
    indicator_types = {}
    for name in available_indicators.keys():
        if 'sma' in name or 'ema' in name:
            indicator_types['Moving Averages'] = indicator_types.get('Moving Averages', 0) + 1
        elif 'rsi' in name:
            indicator_types['RSI'] = indicator_types.get('RSI', 0) + 1
        elif 'macd' in name:
            indicator_types['MACD'] = indicator_types.get('MACD', 0) + 1
        elif 'bbands' in name or 'bb' in name:
            indicator_types['Bollinger Bands'] = indicator_types.get('Bollinger Bands', 0) + 1
        else:
            indicator_types['Other'] = indicator_types.get('Other', 0) + 1
    
    nb.log(f"Типы индикаторов:")
    for indicator_type, count in indicator_types.items():
        nb.log(f"  - {indicator_type}: {count}")

nb.wait()

# --- Шаг 9: Управление кэшем и производительность ---
nb.step("Шаг 9: Управление кэшем и производительность")

nb.info("IndicatorCalculator предоставляет возможности управления кэшем и оптимизации производительности.")

with nb.error_handling("Testing cache management and performance"):
    nb.info("9.1. Тестирование производительности с кэшем:")
    
    # Создаем новый калькулятор для тестирования производительности
    perf_calculator = IndicatorCalculator(df_sample, auto_load_libraries=False)
    
    # Первый расчет (без кэша)
    start_time = datetime.now()
    result1 = perf_calculator.calculate('sma', period=20)
    time1 = (datetime.now() - start_time).total_seconds()
    
    nb.log(f"Первый расчет SMA(20): {time1:.4f} сек")
    
    # Второй расчет (с кэша)
    start_time = datetime.now()
    result2 = perf_calculator.calculate('sma', period=20)
    time2 = (datetime.now() - start_time).total_seconds()
    
    nb.log(f"Второй расчет SMA(20): {time2:.4f} сек")
    nb.log(f"Ускорение: {time1/time2:.2f}x")
    
    nb.info("9.2. Управление кэшем:")
    
    # Проверяем размер кэша
    nb.log(f"Размер кэша до очистки: {len(perf_calculator.results)}")
    
    # Очищаем кэш
    perf_calculator.clear_cache()
    nb.log(f"Размер кэша после очистки: {len(perf_calculator.results)}")
    
    nb.info("9.3. Сравнение производительности различных подходов:")
    
    # Сравниваем производительность различных подходов
    approaches = {
        'IndicatorCalculator': lambda: IndicatorCalculator(df_sample, auto_load_libraries=False).calculate('sma', period=20),
        'calculate_indicator': lambda: calculate_indicator(df_sample, 'sma', period=20),
        'Direct calculation': lambda: df_sample['close'].rolling(window=20).mean()
    }
    
    performance_results = {}
    for approach_name, approach_func in approaches.items():
        start_time = datetime.now()
        try:
            result = approach_func()
            calc_time = (datetime.now() - start_time).total_seconds()
            performance_results[approach_name] = calc_time
        except Exception as e:
            performance_results[approach_name] = f"Ошибка: {e}"
    
    nb.log(f"Сравнение производительности подходов:")
    for approach_name, result in performance_results.items():
        if isinstance(result, (int, float)):
            nb.log(f"  - {approach_name}: {result:.4f} сек")
        else:
            nb.log(f"  - {approach_name}: {result}")

nb.wait()

# --- Шаг 10: Анализ результатов и создание комплексных датасетов ---
nb.step("Шаг 10: Анализ результатов и создание комплексных датасетов")

nb.info("Создание комплексных датасетов с множественными индикаторами для анализа.")

with nb.error_handling("Creating comprehensive datasets"):
    nb.info("10.1. Создание комплексного датасета с основными индикаторами:")
    
    # Создаем калькулятор для комплексного анализа
    comprehensive_calc = IndicatorCalculator(df_sample, auto_load_libraries=False)

    # Определяем комплексный набор индикаторов
    comprehensive_specs = {
        'sma_10': ('sma', {'period': 10}),
        'sma_20': ('sma', {'period': 20}),
        'sma_50': ('sma', {'period': 50}),
        'ema_12': ('ema', {'period': 12}),
        'ema_26': ('ema', {'period': 26}),
        'rsi_14': ('rsi', {'period': 14}),
        'rsi_21': ('rsi', {'period': 21}),
        'bbands_20_2': ('bbands', {'period': 20, 'std_dev': 2.0})
    }

    # Вычисляем все индикаторы
    comprehensive_results: Dict[str, IndicatorResult] = {}
    for alias, (indicator_name, params) in comprehensive_specs.items():
        comprehensive_results[alias] = calculate_with_alias(
            comprehensive_calc,
            indicator_name,
            alias=alias,
            **params,
        )

    nb.log("Комплексный набор индикаторов создан:")
    nb.log(f"  - Количество индикаторов: {len(comprehensive_results)}")
    nb.log(f"  - Доступные индикаторы: {list(comprehensive_results.keys())}")
    
    nb.info("10.2. Объединение в единый датасет:")
    
    # Объединяем все результаты
    comprehensive_data = comprehensive_calc.combine_results()
    nb.log(f"Комплексный датасет создан:")
    nb.log(f"  - Размер: {comprehensive_data.shape}")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Индикаторные колонки: {comprehensive_data.shape[1] - len(df_sample.columns)}")
    
    nb.info("10.3. Анализ качества данных:")
    
    # Анализируем качество данных
    nb.log(f"Анализ качества комплексного датасета:")
    
    # Проверяем наличие NaN значений
    nan_counts = comprehensive_data.isnull().sum()
    columns_with_nans = nan_counts[nan_counts > 0]
    
    if len(columns_with_nans) > 0:
        nb.log(f"  - Колонки с NaN значениями:")
        for col, count in columns_with_nans.items():
            nb.log(f"    * {col}: {count} NaN значений")
    else:
        nb.log(f"  - NaN значений не обнаружено")
    
    # Проверяем статистику по основным индикаторам
    nb.log(f"  - Статистика по основным индикаторам:")
    for indicator_name in ['sma_20', 'rsi_14']:
        if indicator_name in comprehensive_data.columns:
            col_data = comprehensive_data[indicator_name].dropna()
            if len(col_data) > 0:
                nb.log(f"    * {indicator_name}: min={col_data.min():.4f}, max={col_data.max():.4f}, mean={col_data.mean():.4f}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные компоненты высокоуровневых калькуляторов индикаторов BQuant:")
nb.log("[OK] IndicatorCalculator - основной калькулятор для работы с индикаторами")
nb.log("[OK] BatchCalculator - пакетная обработка множественных датасетов")
nb.log("[OK] Удобные функции для расчета популярных индикаторов")
nb.log("[OK] Создание стандартных и пользовательских наборов индикаторов")
nb.log("[OK] Валидация данных для индикаторов")
nb.log("[OK] Управление результатами и кэшированием")

nb.info("Протестированы функции расчета индикаторов:")
nb.log("[+] calculate_indicator() - универсальная функция расчета")
nb.log("[+] calculate_macd() - расчет MACD")
nb.log("[+] calculate_rsi() - расчет RSI")
nb.log("[+] calculate_bollinger_bands() - расчет Bollinger Bands")
nb.log("[+] calculate_moving_averages() - расчет множественных скользящих средних")
nb.log("[+] create_indicator_suite() - создание стандартных наборов")

nb.info("Высокоуровневые калькуляторы BQuant предоставляют:")
nb.log("[*] Удобный интерфейс для работы с техническими индикаторами")
nb.log("[*] Автоматическую загрузку и управление библиотеками")
nb.log("[*] Эффективное кэширование результатов")
nb.log("[*] Пакетную обработку множественных датасетов")
nb.log("[*] Валидацию данных без выполнения расчетов")
nb.log("[*] Создание комплексных наборов индикаторов")

nb.info("Это демонстрирует мощь и удобство высокоуровневых калькуляторов BQuant для технического анализа.")

nb.finish()
