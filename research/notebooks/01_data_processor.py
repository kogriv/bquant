'''
Демонстрация работы модуля обработки данных bquant.data.processor

Этот скрипт показывает, как использовать различные функции для обработки и подготовки данных:
1.  Очистка OHLCV данных (удаление выбросов, обработка пропусков).
2.  Расчет производных индикаторов.
3.  Ресемплинг данных на другие таймфреймы.
4.  Нормализация цен различными методами.
5.  Детекция рыночных сессий.
6.  Добавление технических признаков.
7.  Создание лаговых признаков.
8.  Комплексная подготовка данных для анализа.
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
from bquant.data.samples import get_sample_data
from bquant.data.processor import (
    clean_ohlcv_data,
    remove_price_outliers,
    calculate_derived_indicators,
    resample_ohlcv,
    normalize_prices,
    detect_market_sessions,
    add_technical_features,
    create_lagged_features,
    prepare_data_for_analysis
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы модуля bquant.data.processor")

# --- Шаг 1: Загрузка тестовых данных и создание проблемных данных ---
nb.step("Шаг 1: Загрузка тестовых данных и создание проблемных данных")

nb.info("Для демонстрации обработки данных используем встроенные sample-данные и создадим проблемные данные.")

# Загружаем корректные данные
with nb.error_handling("Loading sample data"):
    nb.info("1.1. Загружаем корректные sample-данные:")
    df_sample = get_sample_data('tv_xauusd_1h')
    
    # Преобразуем колонку time в DatetimeIndex для корректной работы с временными функциями
    if 'time' in df_sample.columns:
        df_sample = df_sample.set_index('time')
        nb.log("Колонка 'time' преобразована в DatetimeIndex")
    
    nb.log(f"Загружено {len(df_sample)} строк корректных данных")
    nb.log(f"Структура: {list(df_sample.columns)}")
    nb.log(f"Тип индекса: {type(df_sample.index)}")
    nb.log(f"Диапазон дат: {df_sample.index.min()} - {df_sample.index.max()}")

# Создаем проблемные данные для демонстрации обработки
with nb.error_handling("Creating problematic data"):
    nb.info("1.2. Создаем проблемные данные для демонстрации обработки:")
    
    # Копируем sample данные и добавляем проблемы
    df_problematic = df_sample.copy()
    
    # Добавляем дубликаты
    df_problematic = pd.concat([df_problematic, df_problematic.iloc[-10:]], ignore_index=False)
    
    # Добавляем пропуски
    df_problematic.iloc[100:110, df_problematic.columns.get_loc('close')] = np.nan
    df_problematic.iloc[200:205, df_problematic.columns.get_loc('high')] = np.nan
    
    # Добавляем логические ошибки (high < low)
    df_problematic.iloc[300:305, df_problematic.columns.get_loc('high')] = 1000  # Низкое значение
    df_problematic.iloc[300:305, df_problematic.columns.get_loc('low')] = 2000   # Высокое значение
    
    # Добавляем выбросы (экстремальные значения)
    df_problematic.iloc[400:405, df_problematic.columns.get_loc('close')] = 50000  # Нереально высокая цена
    
    # Добавляем отрицательные цены
    df_problematic.iloc[500:505, df_problematic.columns.get_loc('open')] = -100
    
    nb.log(f"Создано {len(df_problematic)} строк проблемных данных")
    nb.log("Добавлены проблемы: дубликаты, пропуски, логические ошибки, выбросы, отрицательные цены")

nb.wait()

# --- Шаг 2: Очистка OHLCV данных ---
nb.step("Шаг 2: Очистка OHLCV данных")

nb.info("Функция clean_ohlcv_data() - это основная функция очистки, которая обрабатывает все проблемы в данных.")

# Очистка проблемных данных
with nb.error_handling("Cleaning problematic data"):
    nb.info("2.1. Очистка проблемных данных:")
    df_cleaned = clean_ohlcv_data(
        df_problematic, 
        fill_method='forward',
        remove_outliers=True,
        outlier_threshold=3.0
    )
    
    nb.log(f"Результат очистки:")
    nb.log(f"  - Исходная форма: {df_problematic.shape}")
    nb.log(f"  - Очищенная форма: {df_cleaned.shape}")
    nb.log(f"  - Удалено строк: {len(df_problematic) - len(df_cleaned)}")
    
    # Проверяем, что логические ошибки исправлены
    if 'high' in df_cleaned.columns and 'low' in df_cleaned.columns:
        invalid_ohlc = (df_cleaned['high'] < df_cleaned['low']).sum()
        nb.log(f"  - Осталось невалидных OHLC: {invalid_ohlc}")
    
    # Проверяем пропуски
    missing_data = df_cleaned.isnull().sum().sum()
    nb.log(f"  - Осталось пропусков: {missing_data}")

# Демонстрация различных методов заполнения пропусков
with nb.error_handling("Testing different fill methods"):
    nb.info("2.2. Тестирование различных методов заполнения пропусков:")
    
    # Создаем данные с пропусками
    df_with_gaps = df_sample.copy()
    df_with_gaps.iloc[100:110, df_with_gaps.columns.get_loc('close')] = np.nan
    
    # Метод forward fill
    df_forward = clean_ohlcv_data(df_with_gaps, fill_method='forward', remove_outliers=False)
    forward_filled = df_forward['close'].isnull().sum()
    
    # Метод backward fill
    df_backward = clean_ohlcv_data(df_with_gaps, fill_method='backward', remove_outliers=False)
    backward_filled = df_backward['close'].isnull().sum()
    
    # Метод interpolate
    df_interpolate = clean_ohlcv_data(df_with_gaps, fill_method='interpolate', remove_outliers=False)
    interpolate_filled = df_interpolate['close'].isnull().sum()
    
    nb.log(f"Результаты различных методов заполнения:")
    nb.log(f"  - Forward fill: {forward_filled} пропусков осталось")
    nb.log(f"  - Backward fill: {backward_filled} пропусков осталось")
    nb.log(f"  - Interpolate: {interpolate_filled} пропусков осталось")

nb.wait()

# --- Шаг 3: Удаление выбросов ---
nb.step("Шаг 3: Удаление выбросов")

nb.info("Функция remove_price_outliers() позволяет удалять выбросы различными методами.")

# Создаем данные с выбросами
with nb.error_handling("Creating data with outliers"):
    nb.info("3.1. Создаем данные с выбросами:")
    
    df_with_outliers = df_sample.copy()
    
    # Добавляем выбросы в разные колонки
    df_with_outliers.iloc[100:105, df_with_outliers.columns.get_loc('close')] = 50000
    df_with_outliers.iloc[200:205, df_with_outliers.columns.get_loc('high')] = 60000
    df_with_outliers.iloc[300:305, df_with_outliers.columns.get_loc('low')] = 100
    
    nb.log(f"Добавлено выбросов: 5 в close, 5 в high, 5 в low")

# Удаление выбросов методом z-score
with nb.error_handling("Removing outliers with z-score method"):
    nb.info("3.2. Удаление выбросов методом z-score (threshold=3.0):")
    
    df_no_outliers_zscore = remove_price_outliers(
        df_with_outliers, 
        threshold=3.0, 
        method='z_score'
    )
    
    nb.log(f"Результат удаления выбросов (z-score):")
    nb.log(f"  - Исходная форма: {df_with_outliers.shape}")
    nb.log(f"  - После удаления: {df_no_outliers_zscore.shape}")
    nb.log(f"  - Удалено строк: {len(df_with_outliers) - len(df_no_outliers_zscore)}")

# Удаление выбросов методом IQR
with nb.error_handling("Removing outliers with IQR method"):
    nb.info("3.3. Удаление выбросов методом IQR:")
    
    df_no_outliers_iqr = remove_price_outliers(
        df_with_outliers, 
        threshold=1.5, 
        method='iqr'
    )
    
    nb.log(f"Результат удаления выбросов (IQR):")
    nb.log(f"  - Исходная форма: {df_with_outliers.shape}")
    nb.log(f"  - После удаления: {df_no_outliers_iqr.shape}")
    nb.log(f"  - Удалено строк: {len(df_with_outliers) - len(df_no_outliers_iqr)}")

nb.wait()

# --- Шаг 4: Расчет производных индикаторов ---
nb.step("Шаг 4: Расчет производных индикаторов")

nb.info("Функция calculate_derived_indicators() добавляет базовые технические индикаторы к данным.")

with nb.error_handling("Calculating derived indicators"):
    nb.info("4.1. Расчет производных индикаторов:")
    
    df_with_indicators = calculate_derived_indicators(df_sample)
    
    nb.log(f"Результат расчета индикаторов:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_with_indicators.columns)}")
    nb.log(f"  - Добавлено индикаторов: {len(df_with_indicators.columns) - len(df_sample.columns)}")
    
    # Показываем новые колонки
    new_columns = [col for col in df_with_indicators.columns if col not in df_sample.columns]
    nb.log(f"  - Новые колонки: {new_columns}")
    
    # Показываем примеры значений
    nb.log("Примеры значений новых индикаторов:")
    nb.log(df_with_indicators[new_columns].head(3).to_string())

nb.wait()

# --- Шаг 5: Ресемплинг данных ---
nb.step("Шаг 5: Ресемплинг данных")

nb.info("Функция resample_ohlcv() позволяет изменять таймфрейм данных.")

# Ресемплинг на 4-часовой таймфрейм
with nb.error_handling("Resampling to 4H timeframe"):
    nb.info("5.1. Ресемплинг данных с 1H на 4H:")
    
    # Проверяем, что у нас есть DatetimeIndex
    if not isinstance(df_sample.index, pd.DatetimeIndex):
        nb.warning("Индекс не является DatetimeIndex, пропускаем ресемплинг")
        df_4h = df_sample.copy()
    else:
        df_4h = resample_ohlcv(df_sample, target_timeframe='4H')
    
    nb.log(f"Результат ресемплинга:")
    nb.log(f"  - Исходная форма (1H): {df_sample.shape}")
    nb.log(f"  - Новая форма (4H): {df_4h.shape}")
    nb.log(f"  - Сжатие: {len(df_sample) / len(df_4h):.1f}x")
    
    # Показываем примеры
    nb.log("Примеры 4H данных:")
    nb.log(df_4h.head(3).to_string())

# Ресемплинг на дневной таймфрейм
with nb.error_handling("Resampling to daily timeframe"):
    nb.info("5.2. Ресемплинг данных с 1H на 1D:")
    
    # Проверяем, что у нас есть DatetimeIndex
    if not isinstance(df_sample.index, pd.DatetimeIndex):
        nb.warning("Индекс не является DatetimeIndex, пропускаем ресемплинг")
        df_daily = df_sample.copy()
    else:
        df_daily = resample_ohlcv(df_sample, target_timeframe='1D')
    
    nb.log(f"Результат ресемплинга на дневной таймфрейм:")
    nb.log(f"  - Исходная форма (1H): {df_sample.shape}")
    nb.log(f"  - Новая форма (1D): {df_daily.shape}")
    nb.log(f"  - Сжатие: {len(df_sample) / len(df_daily):.1f}x")
    
    # Показываем примеры
    nb.log("Примеры дневных данных:")
    nb.log(df_daily.head(3).to_string())

nb.wait()

# --- Шаг 6: Нормализация цен ---
nb.step("Шаг 6: Нормализация цен")

nb.info("Функция normalize_prices() предоставляет различные методы нормализации цен.")

# Нормализация к первому значению
with nb.error_handling("Normalizing prices to first value"):
    nb.info("6.1. Нормализация цен к первому значению (база = 100):")
    
    df_normalized_first = normalize_prices(
        df_sample, 
        base_column='close',
        method='first_value'
    )
    
    nb.log(f"Результат нормализации к первому значению:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_normalized_first.columns)}")
    
    # Показываем новые колонки
    new_norm_columns = [col for col in df_normalized_first.columns if 'normalized' in col]
    nb.log(f"  - Колонки нормализации: {new_norm_columns}")
    
    # Показываем примеры
    nb.log("Примеры нормализованных цен (первые 3 строки):")
    nb.log(df_normalized_first[new_norm_columns].head(3).to_string())

# Нормализация процентными изменениями
with nb.error_handling("Normalizing prices with percentage changes"):
    nb.info("6.2. Нормализация цен процентными изменениями:")
    
    df_normalized_pct = normalize_prices(
        df_sample, 
        base_column='close',
        method='percentage_change'
    )
    
    nb.log(f"Результат нормализации процентными изменениями:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_normalized_pct.columns)}")
    
    # Показываем новые колонки
    new_pct_columns = [col for col in df_normalized_pct.columns if 'pct_change' in col]
    nb.log(f"  - Колонки процентных изменений: {new_pct_columns}")
    
    # Показываем примеры
    nb.log("Примеры процентных изменений (первые 3 строки):")
    nb.log(df_normalized_pct[new_pct_columns].head(3).to_string())

# Z-score нормализация
with nb.error_handling("Normalizing prices with z-score"):
    nb.info("6.3. Z-score нормализация цен:")
    
    df_normalized_zscore = normalize_prices(
        df_sample, 
        base_column='close',
        method='z_score'
    )
    
    nb.log(f"Результат Z-score нормализации:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_normalized_zscore.columns)}")
    
    # Показываем новые колонки
    new_zscore_columns = [col for col in df_normalized_zscore.columns if 'zscore' in col]
    nb.log(f"  - Колонки Z-score: {new_zscore_columns}")
    
    # Показываем примеры
    nb.log("Примеры Z-score нормализации (первые 3 строки):")
    nb.log(df_normalized_zscore[new_zscore_columns].head(3).to_string())

nb.wait()

# --- Шаг 7: Детекция рыночных сессий ---
nb.step("Шаг 7: Детекция рыночных сессий")

nb.info("Функция detect_market_sessions() определяет и маркирует рыночные сессии в данных.")

with nb.error_handling("Detecting market sessions"):
    nb.info("7.1. Детекция рыночных сессий:")
    
    df_with_sessions = detect_market_sessions(df_sample, timezone='UTC')
    
    nb.log(f"Результат детекции сессий:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_with_sessions.columns)}")
    
    # Показываем новые колонки
    new_session_columns = [col for col in df_with_sessions.columns if col not in df_sample.columns]
    nb.log(f"  - Колонки сессий: {new_session_columns}")
    
    # Анализируем распределение сессий
    if 'session' in df_with_sessions.columns:
        session_counts = df_with_sessions['session'].value_counts()
        nb.log("Распределение сессий:")
        for session, count in session_counts.items():
            nb.log(f"  - {session}: {count} ({count/len(df_with_sessions)*100:.1f}%)")
    
    # Показываем примеры
    nb.log("Примеры данных с сессиями (первые 5 строк):")
    nb.log(df_with_sessions[['open', 'high', 'low', 'close', 'session']].head(5).to_string())

nb.wait()

# --- Шаг 8: Добавление технических признаков ---
nb.step("Шаг 8: Добавление технических признаков")

nb.info("Функция add_technical_features() добавляет комплексные технические признаки для анализа.")

with nb.error_handling("Adding technical features"):
    nb.info("8.1. Добавление технических признаков:")
    
    df_with_features = add_technical_features(df_sample)
    
    nb.log(f"Результат добавления технических признаков:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_with_features.columns)}")
    nb.log(f"  - Добавлено признаков: {len(df_with_features.columns) - len(df_sample.columns)}")
    
    # Показываем новые колонки
    new_feature_columns = [col for col in df_with_features.columns if col not in df_sample.columns]
    nb.log(f"  - Новые признаки: {new_feature_columns}")
    
    # Группируем признаки по типам
    price_features = [col for col in new_feature_columns if any(x in col for x in ['body', 'shadow', 'range', 'change'])]
    volume_features = [col for col in new_feature_columns if 'volume' in col]
    ma_features = [col for col in new_feature_columns if 'ma_' in col]
    momentum_features = [col for col in new_feature_columns if 'roc' in col]
    
    nb.log("Группировка признаков по типам:")
    nb.log(f"  - Ценовые признаки: {len(price_features)}")
    nb.log(f"  - Объемные признаки: {len(volume_features)}")
    nb.log(f"  - Скользящие средние: {len(ma_features)}")
    nb.log(f"  - Моментум: {len(momentum_features)}")
    
    # Показываем примеры
    nb.log("Примеры технических признаков (первые 3 строки):")
    sample_features = price_features[:3] + volume_features[:2] + ma_features[:2]
    if sample_features:
        nb.log(df_with_features[sample_features].head(3).to_string())

nb.wait()

# --- Шаг 9: Создание лаговых признаков ---
nb.step("Шаг 9: Создание лаговых признаков")

nb.info("Функция create_lagged_features() создает лаговые признаки для временного анализа.")

with nb.error_handling("Creating lagged features"):
    nb.info("9.1. Создание лаговых признаков:")
    
    # Выбираем колонки для лагов
    lag_columns = ['close', 'volume'] if 'volume' in df_sample.columns else ['close']
    lag_periods = [1, 2, 3, 5, 10]
    
    df_with_lags = create_lagged_features(
        df_sample, 
        columns=lag_columns,
        lags=lag_periods
    )
    
    nb.log(f"Результат создания лаговых признаков:")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Новые колонки: {len(df_with_lags.columns)}")
    nb.log(f"  - Добавлено лагов: {len(df_with_lags.columns) - len(df_sample.columns)}")
    nb.log(f"  - Колонки для лагов: {lag_columns}")
    nb.log(f"  - Периоды лагов: {lag_periods}")
    
    # Показываем новые колонки
    new_lag_columns = [col for col in df_with_lags.columns if col not in df_sample.columns]
    nb.log(f"  - Новые лаговые колонки: {new_lag_columns}")
    
    # Показываем примеры
    nb.log("Примеры лаговых признаков (первые 5 строк):")
    sample_lag_columns = [col for col in new_lag_columns if 'close_lag' in col][:3]
    if sample_lag_columns:
        nb.log(df_with_lags[sample_lag_columns].head(5).to_string())

nb.wait()

# --- Шаг 10: Комплексная подготовка данных для анализа ---
nb.step("Шаг 10: Комплексная подготовка данных для анализа")

nb.info("Функция prepare_data_for_analysis() - это комплексная функция, которая объединяет все этапы подготовки.")

with nb.error_handling("Preparing data for analysis"):
    nb.info("10.1. Комплексная подготовка данных для анализа:")
    
    df_prepared = prepare_data_for_analysis(
        df_sample,
        target_column='close',
        add_tech_features=True,
        normalize=True,
        create_lags=True,
        lag_periods=[1, 2, 3, 5]
    )
    
    nb.log(f"Результат комплексной подготовки:")
    nb.log(f"  - Исходная форма: {df_sample.shape}")
    nb.log(f"  - Подготовленная форма: {df_prepared.shape}")
    nb.log(f"  - Исходные колонки: {len(df_sample.columns)}")
    nb.log(f"  - Финальные колонки: {len(df_prepared.columns)}")
    nb.log(f"  - Добавлено признаков: {len(df_prepared.columns) - len(df_sample.columns)}")
    
    # Анализируем структуру подготовленных данных
    numeric_columns = df_prepared.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric_columns = df_prepared.select_dtypes(exclude=[np.number]).columns.tolist()
    
    nb.log("Структура подготовленных данных:")
    nb.log(f"  - Числовые колонки: {len(numeric_columns)}")
    nb.log(f"  - Нечисловые колонки: {len(non_numeric_columns)}")
    
    # Проверяем качество данных
    missing_values = df_prepared.isnull().sum().sum()
    nb.log(f"  - Пропущенные значения: {missing_values}")
    
    # Показываем финальные колонки
    nb.log("Финальные колонки для анализа:")
    nb.log(f"  - {list(df_prepared.columns)}")

# Демонстрация различных конфигураций подготовки
with nb.error_handling("Testing different preparation configurations"):
    nb.info("10.2. Тестирование различных конфигураций подготовки:")
    
    # Только технические признаки без нормализации
    df_tech_only = prepare_data_for_analysis(
        df_sample,
        target_column='close',
        add_tech_features=True,
        normalize=False,
        create_lags=False
    )
    
    # Только нормализация без технических признаков
    df_norm_only = prepare_data_for_analysis(
        df_sample,
        target_column='close',
        add_tech_features=False,
        normalize=True,
        create_lags=False
    )
    
    nb.log("Сравнение различных конфигураций:")
    nb.log(f"  - Только тех. признаки: {len(df_tech_only.columns)} колонок")
    nb.log(f"  - Только нормализация: {len(df_norm_only.columns)} колонок")
    nb.log(f"  - Полная подготовка: {len(df_prepared.columns)} колонок")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные функции модуля bquant.data.processor:")
nb.log("[OK] clean_ohlcv_data() - очистка и валидация OHLCV данных")
nb.log("[OK] remove_price_outliers() - удаление выбросов различными методами")
nb.log("[OK] calculate_derived_indicators() - расчет базовых технических индикаторов")
nb.log("[OK] resample_ohlcv() - изменение таймфрейма данных")
nb.log("[OK] normalize_prices() - нормализация цен различными методами")
nb.log("[OK] detect_market_sessions() - детекция рыночных сессий")
nb.log("[OK] add_technical_features() - добавление комплексных технических признаков")
nb.log("[OK] create_lagged_features() - создание лаговых признаков")
nb.log("[OK] prepare_data_for_analysis() - комплексная подготовка данных")

nb.info("Модуль processor успешно продемонстрировал:")
nb.log("[+] Очистку проблемных данных (пропуски, выбросы, логические ошибки)")
nb.log("[+] Создание технических индикаторов и признаков")
nb.log("[+] Изменение временных масштабов данных")
nb.log("[+] Нормализацию и стандартизацию данных")
nb.log("[+] Комплексную подготовку для машинного обучения")

nb.info("Это демонстрирует мощь системы обработки данных BQuant для подготовки качественных данных для анализа.")

nb.finish()
