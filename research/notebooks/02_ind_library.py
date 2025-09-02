'''
Демонстрация работы встроенных индикаторов bquant.indicators.library

Этот скрипт показывает, как использовать встроенные технические индикаторы BQuant:
1.  SimpleMovingAverage - простая скользящая средняя
2.  ExponentialMovingAverage - экспоненциальная скользящая средняя
3.  RelativeStrengthIndex - индекс относительной силы
4.  MACD - Moving Average Convergence Divergence
5.  BollingerBands - полосы Боллинджера
6.  Регистрация встроенных индикаторов
7.  Сравнение различных параметров
8.  Анализ результатов и статистика
'''

from pathlib import Path
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.indicators.library import (
    SimpleMovingAverage,
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    MACD,
    BollingerBands,
    register_builtin_indicators
)
from bquant.indicators.base import IndicatorFactory

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы встроенных индикаторов bquant.indicators.library")

# --- Шаг 1: Загрузка тестовых данных ---
nb.step("Шаг 1: Загрузка тестовых данных")

nb.info("Для демонстрации встроенных индикаторов используем sample-данные.")

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
    
    nb.info("1.2. Анализ исходных данных:")
    
    # Анализируем исходные данные
    nb.log(f"Статистика по основным колонкам:")
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df_sample.columns:
            col_data = df_sample[col].dropna()
            if len(col_data) > 0:
                nb.log(f"  - {col}: min={col_data.min():.4f}, max={col_data.max():.4f}, mean={col_data.mean():.4f}")

nb.wait()

# --- Шаг 2: Регистрация встроенных индикаторов ---
nb.step("Шаг 2: Регистрация встроенных индикаторов")

nb.info("Регистрируем все встроенные индикаторы в системе BQuant.")

with nb.error_handling("Registering builtin indicators"):
    nb.info("2.1. Регистрация встроенных индикаторов:")
    
    # Регистрируем встроенные индикаторы
    registered_count = register_builtin_indicators()
    nb.log(f"Зарегистрировано {registered_count} встроенных индикаторов")
    
    nb.info("2.2. Проверка доступных индикаторов:")
    
    # Получаем список доступных индикаторов
    available_indicators = IndicatorFactory.list_indicators()
    nb.log(f"Доступные индикаторы в системе:")
    for name, source in available_indicators.items():
        nb.log(f"  - {name}: {source}")
    
    nb.info("2.3. Анализ типов зарегистрированных индикаторов:")
    
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
    
    nb.log(f"Типы зарегистрированных индикаторов:")
    for indicator_type, count in indicator_types.items():
        nb.log(f"  - {indicator_type}: {count}")

nb.wait()

# --- Шаг 3: Работа с SimpleMovingAverage ---
nb.step("Шаг 3: Работа с SimpleMovingAverage")

nb.info("SimpleMovingAverage - это встроенный индикатор простой скользящей средней.")

with nb.error_handling("Testing SimpleMovingAverage"):
    nb.info("3.1. Создание экземпляра SMA с различными периодами:")
    
    # Создаем SMA с различными периодами
    sma_periods = [5, 10, 20, 50]
    sma_indicators = {}
    
    for period in sma_periods:
        sma = SimpleMovingAverage(period=period)
        sma_indicators[period] = sma
        nb.log(f"  - SMA({period}): создан экземпляр")
    
    nb.info("3.2. Расчет SMA для различных периодов:")
    
    # Вычисляем SMA для всех периодов
    sma_results = {}
    for period, indicator in sma_indicators.items():
        result = indicator.calculate(df_sample)
        sma_results[period] = result
        nb.log(f"  - SMA({period}): {result.data.shape}, колонки: {list(result.data.columns)}")
    
    nb.info("3.3. Анализ результатов SMA:")
    
    # Анализируем результаты
    for period, result in sma_results.items():
        col_name = list(result.data.columns)[0]
        col_data = result.data[col_name].dropna()
        if len(col_data) > 0:
            nb.log(f"  - SMA({period}):")
            nb.log(f"    * Записей: {len(col_data)}")
            nb.log(f"    * Минимум: {col_data.min():.4f}")
            nb.log(f"    * Максимум: {col_data.max():.4f}")
            nb.log(f"    * Среднее: {col_data.mean():.4f}")
            nb.log(f"    * Последнее значение: {col_data.iloc[-1]:.4f}")

nb.wait()

# --- Шаг 4: Работа с ExponentialMovingAverage ---
nb.step("Шаг 4: Работа с ExponentialMovingAverage")

nb.info("ExponentialMovingAverage - это встроенный индикатор экспоненциальной скользящей средней.")

with nb.error_handling("Testing ExponentialMovingAverage"):
    nb.info("4.1. Создание экземпляров EMA с различными периодами:")
    
    # Создаем EMA с различными периодами
    ema_periods = [12, 26, 50]
    ema_indicators = {}
    
    for period in ema_periods:
        ema = ExponentialMovingAverage(period=period)
        ema_indicators[period] = ema
        nb.log(f"  - EMA({period}): создан экземпляр")
    
    nb.info("4.2. Расчет EMA для различных периодов:")
    
    # Вычисляем EMA для всех периодов
    ema_results = {}
    for period, indicator in ema_indicators.items():
        result = indicator.calculate(df_sample)
        ema_results[period] = result
        nb.log(f"  - EMA({period}): {result.data.shape}, колонки: {list(result.data.columns)}")
    
    nb.info("4.3. Сравнение SMA и EMA:")
    
    # Сравниваем SMA и EMA для периода 20
    if 20 in sma_results and 20 in ema_results:
        sma_20_data = sma_results[20].data.iloc[:, 0].dropna()
        ema_20_data = ema_results[20].data.iloc[:, 0].dropna()
        
        # Находим общий диапазон для сравнения
        common_length = min(len(sma_20_data), len(ema_20_data))
        if common_length > 0:
            sma_20_common = sma_20_data.iloc[-common_length:]
            ema_20_common = ema_20_data.iloc[-common_length:]
            
            # Вычисляем корреляцию
            correlation = sma_20_common.corr(ema_20_common)
            nb.log(f"  - Корреляция SMA(20) и EMA(20): {correlation:.4f}")
            
            # Сравниваем последние значения
            nb.log(f"  - Последние значения:")
            nb.log(f"    * SMA(20): {sma_20_common.iloc[-1]:.4f}")
            nb.log(f"    * EMA(20): {ema_20_common.iloc[-1]:.4f}")
            nb.log(f"    * Разница: {abs(sma_20_common.iloc[-1] - ema_20_common.iloc[-1]):.4f}")

nb.wait()

# --- Шаг 5: Работа с RelativeStrengthIndex ---
nb.step("Шаг 5: Работа с RelativeStrengthIndex")

nb.info("RelativeStrengthIndex - это встроенный индикатор индекса относительной силы.")

with nb.error_handling("Testing RelativeStrengthIndex"):
    nb.info("5.1. Создание экземпляров RSI с различными периодами:")
    
    # Создаем RSI с различными периодами
    rsi_periods = [7, 14, 21]
    rsi_indicators = {}
    
    for period in rsi_periods:
        rsi = RelativeStrengthIndex(period=period)
        rsi_indicators[period] = rsi
        nb.log(f"  - RSI({period}): создан экземпляр")
    
    nb.info("5.2. Расчет RSI для различных периодов:")
    
    # Вычисляем RSI для всех периодов
    rsi_results = {}
    for period, indicator in rsi_indicators.items():
        result = indicator.calculate(df_sample)
        rsi_results[period] = result
        nb.log(f"  - RSI({period}): {result.data.shape}, колонки: {list(result.data.columns)}")
    
    nb.info("5.3. Анализ результатов RSI:")
    
    # Анализируем результаты RSI
    for period, result in rsi_results.items():
        col_name = list(result.data.columns)[0]
        col_data = result.data[col_name].dropna()
        if len(col_data) > 0:
            nb.log(f"  - RSI({period}):")
            nb.log(f"    * Записей: {len(col_data)}")
            nb.log(f"    * Минимум: {col_data.min():.2f}")
            nb.log(f"    * Максимум: {col_data.max():.2f}")
            nb.log(f"    * Среднее: {col_data.mean():.2f}")
            nb.log(f"    * Последнее значение: {col_data.iloc[-1]:.2f}")
            
            # Анализируем экстремальные значения
            oversold_count = len(col_data[col_data < 30])
            overbought_count = len(col_data[col_data > 70])
            nb.log(f"    * Перепроданность (<30): {oversold_count} раз")
            nb.log(f"    * Перекупленность (>70): {overbought_count} раз")

nb.wait()

# --- Шаг 6: Работа с MACD ---
nb.step("Шаг 6: Работа с MACD")

nb.info("MACD - это встроенный индикатор Moving Average Convergence Divergence.")

with nb.error_handling("Testing MACD"):
    nb.info("6.1. Создание экземпляров MACD с различными параметрами:")
    
    # Создаем MACD с различными параметрами
    macd_configs = [
        {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
        {'fast_period': 8, 'slow_period': 21, 'signal_period': 5},
        {'fast_period': 5, 'slow_period': 13, 'signal_period': 3}
    ]
    macd_indicators = {}
    
    for i, config in enumerate(macd_configs):
        macd = MACD(**config)
        macd_indicators[f"config_{i+1}"] = macd
        nb.log(f"  - MACD {i+1}: fast={config['fast_period']}, slow={config['slow_period']}, signal={config['signal_period']}")
    
    nb.info("6.2. Расчет MACD для различных конфигураций:")
    
    # Вычисляем MACD для всех конфигураций
    macd_results = {}
    for config_name, indicator in macd_indicators.items():
        result = indicator.calculate(df_sample)
        macd_results[config_name] = result
        nb.log(f"  - {config_name}: {result.data.shape}, колонки: {list(result.data.columns)}")
    
    nb.info("6.3. Анализ результатов MACD:")
    
    # Анализируем результаты MACD
    for config_name, result in macd_results.items():
        nb.log(f"  - {config_name}:")
        
        # Анализируем каждую колонку
        for col in result.data.columns:
            col_data = result.data[col].dropna()
            if len(col_data) > 0:
                nb.log(f"    * {col}:")
                nb.log(f"      - Записей: {len(col_data)}")
                nb.log(f"      - Минимум: {col_data.min():.4f}")
                nb.log(f"      - Максимум: {col_data.max():.4f}")
                nb.log(f"      - Среднее: {col_data.mean():.4f}")
                nb.log(f"      - Последнее значение: {col_data.iloc[-1]:.4f}")
        
        # Анализируем сигналы
        if 'macd' in result.data.columns and 'macd_signal' in result.data.columns:
            macd_line = result.data['macd'].dropna()
            signal_line = result.data['macd_signal'].dropna()
            
            if len(macd_line) > 0 and len(signal_line) > 0:
                # Находим пересечения
                common_length = min(len(macd_line), len(signal_line))
                macd_common = macd_line.iloc[-common_length:]
                signal_common = signal_line.iloc[-common_length:]
                
                # Простой анализ пересечений
                bullish_crosses = 0
                bearish_crosses = 0
                
                for i in range(1, len(macd_common)):
                    if (macd_common.iloc[i-1] <= signal_common.iloc[i-1] and 
                        macd_common.iloc[i] > signal_common.iloc[i]):
                        bullish_crosses += 1
                    elif (macd_common.iloc[i-1] >= signal_common.iloc[i-1] and 
                          macd_common.iloc[i] < signal_common.iloc[i]):
                        bearish_crosses += 1
                
                nb.log(f"    * Анализ пересечений:")
                nb.log(f"      - Бычьи пересечения: {bullish_crosses}")
                nb.log(f"      - Медвежьи пересечения: {bearish_crosses}")

nb.wait()

# --- Шаг 7: Работа с BollingerBands ---
nb.step("Шаг 7: Работа с BollingerBands")

nb.info("BollingerBands - это встроенный индикатор полос Боллинджера.")

with nb.error_handling("Testing BollingerBands"):
    nb.info("7.1. Создание экземпляров Bollinger Bands с различными параметрами:")
    
    # Создаем Bollinger Bands с различными параметрами
    bb_configs = [
        {'period': 20, 'std_dev': 2.0},
        {'period': 20, 'std_dev': 1.5},
        {'period': 50, 'std_dev': 2.0}
    ]
    bb_indicators = {}
    
    for i, config in enumerate(bb_configs):
        bb = BollingerBands(**config)
        bb_indicators[f"config_{i+1}"] = bb
        nb.log(f"  - BB {i+1}: period={config['period']}, std_dev={config['std_dev']}")
    
    nb.info("7.2. Расчет Bollinger Bands для различных конфигураций:")
    
    # Вычисляем Bollinger Bands для всех конфигураций
    bb_results = {}
    for config_name, indicator in bb_indicators.items():
        result = indicator.calculate(df_sample)
        bb_results[config_name] = result
        nb.log(f"  - {config_name}: {result.data.shape}, колонки: {list(result.data.columns)}")
    
    nb.info("7.3. Анализ результатов Bollinger Bands:")
    
    # Анализируем результаты Bollinger Bands
    for config_name, result in bb_results.items():
        nb.log(f"  - {config_name}:")
        
        # Анализируем каждую колонку
        for col in result.data.columns:
            col_data = result.data[col].dropna()
            if len(col_data) > 0:
                nb.log(f"    * {col}:")
                nb.log(f"      - Записей: {len(col_data)}")
                nb.log(f"      - Минимум: {col_data.min():.4f}")
                nb.log(f"      - Максимум: {col_data.max():.4f}")
                nb.log(f"      - Среднее: {col_data.mean():.4f}")
                nb.log(f"      - Последнее значение: {col_data.iloc[-1]:.4f}")
        
        # Анализируем ширину полос
        if 'bb_width' in result.data.columns:
            width_data = result.data['bb_width'].dropna()
            if len(width_data) > 0:
                nb.log(f"    * Анализ ширины полос:")
                nb.log(f"      - Средняя ширина: {width_data.mean():.4f}")
                nb.log(f"      - Минимальная ширина: {width_data.min():.4f}")
                nb.log(f"      - Максимальная ширина: {width_data.max():.4f}")
                
                # Анализируем сжатие/расширение
                recent_width = width_data.iloc[-min(20, len(width_data)):].mean()
                historical_width = width_data.mean()
                
                if recent_width < historical_width * 0.8:
                    nb.log(f"      - Состояние: Сжатие полос (волатильность снижается)")
                elif recent_width > historical_width * 1.2:
                    nb.log(f"      - Состояние: Расширение полос (волатильность растет)")
                else:
                    nb.log(f"      - Состояние: Нормальная ширина полос")

nb.wait()

# --- Шаг 8: Сравнение производительности индикаторов ---
nb.step("Шаг 8: Сравнение производительности индикаторов")

nb.info("Сравниваем производительность различных встроенных индикаторов.")

with nb.error_handling("Testing indicator performance"):
    nb.info("8.1. Тестирование производительности SMA:")
    
    # Тестируем производительность SMA с различными периодами
    sma_performance = {}
    for period in [5, 10, 20, 50]:
        indicator = SimpleMovingAverage(period=period)
        
        start_time = datetime.now()
        result = indicator.calculate(df_sample)
        calc_time = (datetime.now() - start_time).total_seconds()
        
        sma_performance[period] = {
            'calculation_time': calc_time,
            'records_processed': len(result.data),
            'speed': len(result.data) / calc_time if calc_time > 0 else 0
        }
    
    nb.log(f"Производительность SMA:")
    for period, metrics in sma_performance.items():
        nb.log(f"  - SMA({period}): {metrics['calculation_time']:.4f} сек, {metrics['speed']:.0f} записей/сек")
    
    nb.info("8.2. Тестирование производительности EMA:")
    
    # Тестируем производительность EMA с различными периодами
    ema_performance = {}
    for period in [12, 26, 50]:
        indicator = ExponentialMovingAverage(period=period)
        
        start_time = datetime.now()
        result = indicator.calculate(df_sample)
        calc_time = (datetime.now() - start_time).total_seconds()
        
        ema_performance[period] = {
            'calculation_time': calc_time,
            'records_processed': len(result.data),
            'speed': len(result.data) / calc_time if calc_time > 0 else 0
        }
    
    nb.log(f"Производительность EMA:")
    for period, metrics in ema_performance.items():
        nb.log(f"  - EMA({period}): {metrics['calculation_time']:.4f} сек, {metrics['speed']:.0f} записей/сек")
    
    nb.info("8.3. Сравнение общей производительности:")
    
    # Сравниваем общую производительность
    all_performance = {**sma_performance, **ema_performance}
    
    fastest_indicator = min(all_performance.items(), key=lambda x: x[1]['calculation_time'])
    slowest_indicator = max(all_performance.items(), key=lambda x: x[1]['calculation_time'])
    
    nb.log(f"Общая производительность:")
    nb.log(f"  - Самый быстрый: {fastest_indicator[0]} ({fastest_indicator[1]['calculation_time']:.4f} сек)")
    nb.log(f"  - Самый медленный: {slowest_indicator[0]} ({slowest_indicator[1]['calculation_time']:.4f} сек)")
    nb.log(f"  - Разница в скорости: {slowest_indicator[1]['calculation_time']/fastest_indicator[1]['calculation_time']:.2f}x")

nb.wait()

# --- Шаг 9: Создание комплексных наборов индикаторов ---
nb.step("Шаг 9: Создание комплексных наборов индикаторов")

nb.info("Создаем комплексные наборы встроенных индикаторов для анализа.")

with nb.error_handling("Creating comprehensive indicator sets"):
    nb.info("9.1. Создание набора трендовых индикаторов:")
    
    # Создаем набор трендовых индикаторов
    trend_indicators = {
        'sma_20': SimpleMovingAverage(period=20),
        'sma_50': SimpleMovingAverage(period=50),
        'ema_12': ExponentialMovingAverage(period=12),
        'ema_26': ExponentialMovingAverage(period=26)
    }
    
    trend_results = {}
    for name, indicator in trend_indicators.items():
        result = indicator.calculate(df_sample)
        trend_results[name] = result
        nb.log(f"  - {name}: {result.data.shape}")
    
    nb.info("9.2. Создание набора осцилляторов:")
    
    # Создаем набор осцилляторов
    oscillator_indicators = {
        'rsi_14': RelativeStrengthIndex(period=14),
        'rsi_21': RelativeStrengthIndex(period=21)
    }
    
    oscillator_results = {}
    for name, indicator in oscillator_indicators.items():
        result = indicator.calculate(df_sample)
        oscillator_results[name] = result
        nb.log(f"  - {name}: {result.data.shape}")
    
    nb.info("9.3. Создание набора объемных индикаторов:")
    
    # Создаем набор объемных индикаторов
    volume_indicators = {
        'macd': MACD(fast_period=12, slow_period=26, signal_period=9),
        'bbands': BollingerBands(period=20, std_dev=2.0)
    }
    
    volume_results = {}
    for name, indicator in volume_indicators.items():
        result = indicator.calculate(df_sample)
        volume_results[name] = result
        nb.log(f"  - {name}: {result.data.shape}")
    
    nb.info("9.4. Объединение всех результатов:")
    
    # Объединяем все результаты в один DataFrame
    all_results = {**trend_results, **oscillator_results, **volume_results}
    
    combined_data = df_sample.copy()
    for name, result in all_results.items():
        for col in result.data.columns:
            if col not in combined_data.columns:
                combined_data[col] = result.data[col]
            else:
                combined_data[f"{name}_{col}"] = result.data[col]
    
    nb.log(f"Комплексный датасет создан:")
    nb.log(f"  - Исходный размер: {df_sample.shape}")
    nb.log(f"  - Финальный размер: {combined_data.shape}")
    nb.log(f"  - Добавлено колонок: {combined_data.shape[1] - df_sample.shape[1]}")

nb.wait()

# --- Шаг 10: Анализ качества и валидация результатов ---
nb.step("Шаг 10: Анализ качества и валидация результатов")

nb.info("Анализируем качество результатов встроенных индикаторов.")

with nb.error_handling("Analyzing indicator quality"):
    nb.info("10.1. Анализ полноты данных:")
    
    # Анализируем полноту данных для каждого индикатора
    nb.log(f"Анализ полноты данных:")
    
    for name, result in all_results.items():
        total_records = len(result.data)
        valid_records = result.data.dropna().shape[0]
        completeness = (valid_records / total_records) * 100 if total_records > 0 else 0
        
        nb.log(f"  - {name}:")
        nb.log(f"    * Всего записей: {total_records}")
        nb.log(f"    * Валидных записей: {valid_records}")
        nb.log(f"    * Полнота данных: {completeness:.1f}%")
    
    nb.info("10.2. Анализ статистических свойств:")
    
    # Анализируем статистические свойства результатов
    nb.log(f"Анализ статистических свойств:")
    
    for name, result in all_results.items():
        nb.log(f"  - {name}:")
        
        for col in result.data.columns:
            col_data = result.data[col].dropna()
            if len(col_data) > 0:
                # Проверяем на выбросы (z-score > 3)
                z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                outliers = len(z_scores[z_scores > 3])
                
                nb.log(f"    * {col}:")
                nb.log(f"      - Среднее: {col_data.mean():.4f}")
                nb.log(f"      - Стандартное отклонение: {col_data.std():.4f}")
                nb.log(f"      - Выбросы (z-score > 3): {outliers}")
                nb.log(f"      - Коэффициент вариации: {col_data.std()/abs(col_data.mean()):.4f}" if col_data.mean() != 0 else "      - Коэффициент вариации: N/A")
    
    nb.info("10.3. Проверка логической корректности:")
    
    # Проверяем логическую корректность результатов
    nb.log(f"Проверка логической корректности:")
    
    # Проверяем RSI (должен быть в диапазоне 0-100)
    if 'rsi_14' in all_results:
        rsi_data = all_results['rsi_14'].data.iloc[:, 0].dropna()
        if len(rsi_data) > 0:
            rsi_valid = (rsi_data >= 0) & (rsi_data <= 100)
            invalid_rsi_count = len(rsi_data[~rsi_valid])
            nb.log(f"  - RSI(14):")
            nb.log(f"    * Валидных значений: {len(rsi_data[rsi_valid])}")
            nb.log(f"    * Некорректных значений: {invalid_rsi_count}")
    
    # Проверяем Bollinger Bands (верхняя должна быть выше нижней)
    if 'bbands' in all_results:
        bb_data = all_results['bbands'].data
        if 'bb_upper' in bb_data.columns and 'bb_lower' in bb_data.columns:
            upper = bb_data['bb_upper'].dropna()
            lower = bb_data['bb_lower'].dropna()
            
            if len(upper) > 0 and len(lower) > 0:
                common_length = min(len(upper), len(lower))
                upper_common = upper.iloc[-common_length:]
                lower_common = lower.iloc[-common_length:]
                
                bb_valid = upper_common >= lower_common
                invalid_bb_count = len(bb_valid[~bb_valid])
                nb.log(f"  - Bollinger Bands:")
                nb.log(f"    * Валидных значений: {len(bb_valid[bb_valid])}")
                nb.log(f"    * Некорректных значений: {invalid_bb_count}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные встроенные индикаторы BQuant:")
nb.log("✅ SimpleMovingAverage - простая скользящая средняя")
nb.log("✅ ExponentialMovingAverage - экспоненциальная скользящая средняя")
nb.log("✅ RelativeStrengthIndex - индекс относительной силы")
nb.log("✅ MACD - Moving Average Convergence Divergence")
nb.log("✅ BollingerBands - полосы Боллинджера")
nb.log("✅ Регистрация и управление встроенными индикаторами")

nb.info("Протестированы возможности встроенных индикаторов:")
nb.log("🔧 Различные периоды и параметры")
nb.log("🔧 Сравнение производительности")
nb.log("🔧 Создание комплексных наборов")
nb.log("🔧 Анализ качества результатов")
nb.log("🔧 Валидация логической корректности")

nb.info("Встроенные индикаторы BQuant предоставляют:")
nb.log("🏗️ Готовые к использованию технические индикаторы")
nb.log("🏗️ Оптимизированную производительность")
nb.log("🏗️ Единообразный интерфейс")
nb.log("🏗️ Автоматическую регистрацию в системе")
nb.log("🏗️ Высокое качество расчетов")
nb.log("🏗️ Возможность создания комплексных аналитических наборов")

nb.info("Это демонстрирует мощь и надежность встроенных индикаторов BQuant для технического анализа.")

nb.finish()
