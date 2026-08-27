#!/usr/bin/env python3
"""
BQuant - Пример работы с данными

Этот пример демонстрирует:
1. Загрузку данных из различных источников (CSV, sample data)
2. Обработку и очистку данных
3. Валидацию данных и схем
4. Применение производных индикаторов
5. Сохранение обработанных данных

Требования:
- Установленный BQuant пакет: pip install -e .
- Опционально: файлы данных в CSV формате
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Добавляем путь к BQuant для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Пример импортировал шесть имён, которых в пакете нет ни под каким модулем —
# API переименовали, а пример остался и не запускался вовсе. Актуальные имена:
#   create_sample_data -> встроенные сэмплы (`bquant.data.samples`)
#   load_ohlcv_csv     -> load_ohlcv_data
#   clean_data         -> clean_ohlcv_data
#   remove_outliers    -> remove_price_outliers
#   resample_data      -> resample_ohlcv
#   normalize_data     -> normalize_prices
from bquant.data import (
    load_ohlcv_data, get_available_timeframes,
    validate_ohlcv_data, clean_ohlcv_data, remove_price_outliers,
    resample_ohlcv, calculate_derived_indicators,
    create_lagged_features, normalize_prices
)
from bquant.data.samples import get_sample_data


def create_sample_data(symbol: str, start_date: str, end_date: str,
                       timeframe: str = "1h") -> pd.DataFrame:
    """Кадр для демонстрации, нарезанный из встроенного сэмпла.

    Синтетическую генерацию здесь заменяет правило проекта: примеры работают на
    встроенных данных, а не на выдуманных (`AGENTS.md`). Символ и таймфрейм
    используются как подписи — данные одни и те же.
    """
    data = get_sample_data('tv_xauusd_1h').copy()
    if 'time' in data.columns:
        data = data.set_index(pd.to_datetime(data['time'])).drop(columns=['time'])
    span = pd.Timestamp(end_date) - pd.Timestamp(start_date)
    bars = max(int(span / pd.Timedelta('1h')), 24)
    data = data.head(bars)
    data.attrs['symbol'] = symbol
    data.attrs['timeframe'] = timeframe
    return data
from bquant.data.schemas import OHLCVRecord, DataSourceConfig, DataValidationResult
from bquant.core.config import get_data_path, SUPPORTED_TIMEFRAMES


def demonstrate_data_creation():
    """Демонстрация создания различных типов данных."""
    
    print("📊 Создание тестовых данных")
    print("-" * 40)
    
    # 1. Создание простых sample данных
    print(f"\n1️⃣ Создание sample данных:")
    
    sample_data = create_sample_data(
        symbol="XAUUSD",
        start_date="2024-01-01",
        end_date="2024-01-10",
        timeframe="1h"
    )
    
    print(f"   ✅ Создано {len(sample_data)} баров для XAUUSD")
    print(f"   📅 Период: {sample_data.index[0]} - {sample_data.index[-1]}")
    print(f"   💰 Ценовой диапазон: ${sample_data['close'].min():.2f} - ${sample_data['close'].max():.2f}")
    print(f"   📊 Колонки: {list(sample_data.columns)}")
    
    # 2. Создание данных с различными характеристиками
    print(f"\n2️⃣ Создание данных с трендом:")
    
    trending_data = create_trending_dataset(300, "EURUSD", trend_strength=0.002)
    print(f"   ✅ Создано {len(trending_data)} баров с трендом")
    
    volatile_data = create_volatile_dataset(200, "BTCUSD", volatility=0.05)
    print(f"   ✅ Создано {len(volatile_data)} баров с высокой волатильностью")
    
    return sample_data, trending_data, volatile_data


def create_trending_dataset(rows: int, symbol: str, trend_strength: float = 0.001) -> pd.DataFrame:
    """Создание данных с выраженным трендом."""
    
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='4H')
    np.random.seed(42)
    
    if symbol == "EURUSD":
        base_price = 1.1000
    elif symbol == "BTCUSD":
        base_price = 50000
    else:
        base_price = 2000
    
    prices = [base_price]
    
    for i in range(1, rows):
        # Линейный тренд + случайность
        trend = trend_strength * i
        noise = np.random.normal(0, 0.005)
        change = trend + noise
        
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, base_price * 0.1))
    
    # Создаем OHLCV
    data = []
    for i, close_price in enumerate(prices):
        open_price = prices[i-1] if i > 0 else close_price
        high = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.003)))
        low = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.003)))
        volume = np.random.randint(10000, 100000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


def create_volatile_dataset(rows: int, symbol: str, volatility: float = 0.02) -> pd.DataFrame:
    """Создание данных с высокой волатильностью."""
    
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='15min')
    np.random.seed(123)
    
    if symbol == "BTCUSD":
        base_price = 50000
    else:
        base_price = 2000
    
    prices = [base_price]
    
    for i in range(1, rows):
        # Высокая случайная волатильность
        change = np.random.normal(0, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, base_price * 0.1))
    
    # Создаем OHLCV
    data = []
    for i, close_price in enumerate(prices):
        open_price = prices[i-1] if i > 0 else close_price
        high = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.01)))
        low = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.01)))
        volume = np.random.randint(50000, 500000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


def demonstrate_data_validation():
    """Демонстрация валидации данных."""
    
    print(f"\n🔍 Валидация данных")
    print("-" * 40)
    
    # 1. Создаем корректные данные
    good_data = create_sample_data("EURUSD", "2024-01-01", "2024-01-05", "1h")
    
    print(f"\n1️⃣ Валидация корректных данных:")
    validation_result = validate_ohlcv_data(good_data)
    
    print(f"   ✅ Результат валидации: {validation_result}")
    
    if isinstance(validation_result, dict):
        is_valid = validation_result.get('is_valid', False)
        print(f"   📊 Данные валидны: {'Да' if is_valid else 'Нет'}")
        
        if 'issues' in validation_result:
            issues = validation_result['issues']
            if issues:
                print(f"   ⚠️ Найдено проблем: {len(issues)}")
                for issue in issues[:3]:  # Показываем первые 3
                    print(f"      • {issue}")
            else:
                print(f"   ✅ Проблемы не найдены")
    
    # 2. Создаем данные с проблемами
    print(f"\n2️⃣ Валидация данных с проблемами:")
    
    # Данные с пропусками
    bad_data = good_data.copy()
    bad_data.loc[bad_data.index[10:15], 'close'] = np.nan  # Добавляем пропуски
    bad_data.loc[bad_data.index[20], 'high'] = bad_data.loc[bad_data.index[20], 'low'] - 10  # Некорректная цена
    
    validation_result_bad = validate_ohlcv_data(bad_data)
    
    if isinstance(validation_result_bad, dict):
        is_valid = validation_result_bad.get('is_valid', False)
        print(f"   📊 Данные валидны: {'Да' if is_valid else 'Нет'}")
        
        if 'issues' in validation_result_bad:
            issues = validation_result_bad['issues']
            if issues:
                print(f"   ⚠️ Найдено проблем: {len(issues)}")
                for issue in issues[:5]:  # Показываем первые 5
                    print(f"      • {issue}")


def demonstrate_data_cleaning():
    """Демонстрация очистки данных."""
    
    print(f"\n🧹 Очистка и обработка данных")
    print("-" * 40)
    
    # Создаем данные с проблемами
    dirty_data = create_volatile_dataset(150, "XAUUSD", volatility=0.03)
    
    # Добавляем искусственные проблемы
    dirty_data.loc[dirty_data.index[10:15], 'volume'] = np.nan  # Пропуски в объеме
    dirty_data.loc[dirty_data.index[50], 'high'] = dirty_data.loc[dirty_data.index[50], 'close'] * 2  # Выброс
    dirty_data.loc[dirty_data.index[80:85], 'close'] = np.nan  # Пропуски в цене закрытия
    
    print(f"\n1️⃣ Исходные 'грязные' данные:")
    print(f"   📊 Количество строк: {len(dirty_data)}")
    print(f"   🕳️ Пропуски в данных:")
    missing_info = dirty_data.isnull().sum()
    for col, missing_count in missing_info.items():
        if missing_count > 0:
            print(f"      {col}: {missing_count} пропусков")
    
    # 2. Очистка данных
    print(f"\n2️⃣ Применение очистки данных:")
    
    try:
        cleaned_data = clean_ohlcv_data(dirty_data)
        print(f"   ✅ Данные очищены")
        print(f"   📊 Количество строк после очистки: {len(cleaned_data)}")
        
        # Проверяем пропуски после очистки
        missing_after = cleaned_data.isnull().sum()
        total_missing = missing_after.sum()
        if total_missing == 0:
            print(f"   ✅ Все пропуски устранены")
        else:
            print(f"   ⚠️ Осталось пропусков: {total_missing}")
        
    except Exception as e:
        print(f"   ❌ Ошибка очистки: {e}")
        cleaned_data = dirty_data  # Используем исходные данные
    
    # 3. Удаление выбросов
    print(f"\n3️⃣ Удаление выбросов:")
    
    try:
        outlier_free_data = remove_price_outliers(cleaned_data, columns=['close', 'high', 'low'], method='z_score')
        print(f"   ✅ Выбросы удалены")
        print(f"   📊 Количество строк: {len(cleaned_data)} → {len(outlier_free_data)}")
        
        removed_count = len(cleaned_data) - len(outlier_free_data)
        if removed_count > 0:
            print(f"   🗑️ Удалено выбросов: {removed_count}")
        else:
            print(f"   ✅ Выбросы не найдены")
        
    except Exception as e:
        print(f"   ❌ Ошибка удаления выбросов: {e}")
        outlier_free_data = cleaned_data
    
    return outlier_free_data


def demonstrate_data_transformations():
    """Демонстрация трансформации данных."""
    
    print(f"\n🔄 Трансформация данных")
    print("-" * 40)
    
    # Используем исходные данные
    base_data = create_sample_data("GBPUSD", "2024-01-01", "2024-01-15", "1h")
    
    print(f"\n1️⃣ Исходные данные:")
    print(f"   📊 Размер: {base_data.shape}")
    print(f"   📅 Timeframe: 1h")
    print(f"   📈 Ценовой диапазон: {base_data['close'].min():.4f} - {base_data['close'].max():.4f}")
    
    # 2. Ресэмплинг данных
    print(f"\n2️⃣ Ресэмплинг данных:")
    
    try:
        # Преобразуем в 4-часовые данные
        resampled_4h = resample_ohlcv(base_data, target_timeframe='4h')
        print(f"   ✅ Ресэмплинг в 4h: {len(base_data)} → {len(resampled_4h)} баров")
        
        # Преобразуем в дневные данные
        resampled_1d = resample_ohlcv(base_data, target_timeframe='1d')
        print(f"   ✅ Ресэмплинг в 1d: {len(base_data)} → {len(resampled_1d)} баров")
        
    except Exception as e:
        print(f"   ❌ Ошибка ресэмплинга: {e}")
        resampled_4h = base_data
    
    # 3. Расчет производных индикаторов
    print(f"\n3️⃣ Расчет производных индикаторов:")
    
    try:
        derived_data = calculate_derived_indicators(base_data)
        new_columns = [col for col in derived_data.columns if col not in base_data.columns]
        
        print(f"   ✅ Рассчитано производных индикаторов: {len(new_columns)}")
        print(f"   📊 Новые колонки: {', '.join(new_columns[:5])}{'...' if len(new_columns) > 5 else ''}")
        print(f"   📈 Размер данных: {base_data.shape} → {derived_data.shape}")
        
    except Exception as e:
        print(f"   ❌ Ошибка расчета производных: {e}")
        derived_data = base_data
    
    # 4. Создание лаговых признаков
    print(f"\n4️⃣ Создание лаговых признаков:")
    
    try:
        lagged_data = create_lagged_features(
            derived_data, 
            columns=['close', 'volume'], 
            lags=[1, 2, 5, 10]
        )
        
        lag_columns = [col for col in lagged_data.columns if '_lag_' in col]
        print(f"   ✅ Создано лаговых признаков: {len(lag_columns)}")
        print(f"   📊 Примеры: {', '.join(lag_columns[:3])}{'...' if len(lag_columns) > 3 else ''}")
        print(f"   📈 Размер данных: {derived_data.shape} → {lagged_data.shape}")
        
    except Exception as e:
        print(f"   ❌ Ошибка создания лагов: {e}")
        lagged_data = derived_data
    
    # 5. Нормализация данных
    print(f"\n5️⃣ Нормализация данных:")
    
    try:
        numeric_columns = ['close', 'high', 'low', 'open', 'volume']
        available_columns = [col for col in numeric_columns if col in lagged_data.columns]
        
        normalized_data = normalize_prices(lagged_data, base_column='close', method='first_value')
        
        print(f"   ✅ Нормализованы колонки: {', '.join(available_columns)}")
        
        # Проверяем диапазоны после нормализации
        for col in available_columns[:3]:  # Показываем первые 3
            norm_col = f"{col}_normalized"
            if norm_col in normalized_data.columns:
                min_val = normalized_data[norm_col].min()
                max_val = normalized_data[norm_col].max()
                print(f"      {col}: [{min_val:.3f}, {max_val:.3f}]")
        
    except Exception as e:
        print(f"   ❌ Ошибка нормализации: {e}")
        normalized_data = lagged_data
    
    return normalized_data


def demonstrate_data_schemas():
    """Демонстрация работы со схемами данных."""
    
    print(f"\n📋 Работа со схемами данных")
    print("-" * 40)
    
    # 1. Создание записи OHLCV
    print(f"\n1️⃣ Создание записи OHLCVRecord:")
    
    try:
        sample_record = OHLCVRecord(
            timestamp=datetime.now(),
            open=1.1234,
            high=1.1250,
            low=1.1220,
            close=1.1245,
            volume=100000
        )
        
        print(f"   ✅ Запись создана:")
        print(f"      Время: {sample_record.timestamp}")
        print(f"      OHLC: {sample_record.open}/{sample_record.high}/{sample_record.low}/{sample_record.close}")
        print(f"      Объем: {sample_record.volume:,}")
        
    except Exception as e:
        print(f"   ❌ Ошибка создания записи: {e}")
    
    # 2. Конфигурация источника данных
    print(f"\n2️⃣ Конфигурация источника данных:")
    
    try:
        data_config = DataSourceConfig(
            name="MT5_EURUSD",
            file_pattern="EURUSD_*.csv",
            timeframe_mapping={'1h': '60', '4h': '240', '1d': '1440'},
            quote_providers=['MetaTrader5', 'TradingView']
        )
        
        print(f"   ✅ Конфигурация создана:")
        print(f"      Название: {data_config.name}")
        print(f"      Паттерн файлов: {data_config.file_pattern}")
        print(f"      Таймфреймы: {data_config.timeframe_mapping}")
        print(f"      Провайдеры: {data_config.quote_providers}")
        
    except Exception as e:
        print(f"   ❌ Ошибка создания конфигурации: {e}")
    
    # 3. Результат валидации
    print(f"\n3️⃣ Результат валидации:")
    
    try:
        validation_result = DataValidationResult(
            issues=["Missing data in close column", "Price gaps detected"],
            stats={'total_rows': 1000, 'missing_values': 5, 'outliers': 2},
            recommendations=["Fill missing values", "Review price gaps"]
        )
        
        print(f"   ✅ Результат валидации создан:")
        print(f"      Проблемы: {len(validation_result.issues)}")
        for issue in validation_result.issues:
            print(f"        • {issue}")
        print(f"      Статистики: {validation_result.stats}")
        print(f"      Рекомендации: {len(validation_result.recommendations)}")
        
    except Exception as e:
        print(f"   ❌ Ошибка создания результата: {e}")


def save_processed_data(data: pd.DataFrame, filename: str = "processed_data.csv"):
    """Сохранение обработанных данных."""
    
    print(f"\n💾 Сохранение обработанных данных:")
    
    try:
        filepath = os.path.join("examples", filename)
        data.to_csv(filepath)
        
        print(f"   ✅ Данные сохранены: {filepath}")
        print(f"   📊 Размер: {data.shape}")
        print(f"   📅 Период: {data.index[0]} - {data.index[-1]}")
        print(f"   📈 Колонки: {len(data.columns)} ({', '.join(data.columns[:5])}{'...' if len(data.columns) > 5 else ''})")
        
        # Статистика по размеру файла
        file_size = os.path.getsize(filepath)
        size_mb = file_size / (1024 * 1024)
        print(f"   💽 Размер файла: {size_mb:.2f} MB")
        
    except Exception as e:
        print(f"   ❌ Ошибка сохранения: {e}")


def demonstrate_timeframes_support():
    """Демонстрация поддержки различных таймфреймов."""
    
    print(f"\n⏰ Поддержка таймфреймов")
    print("-" * 40)
    
    print(f"\n📊 Поддерживаемые таймфреймы:")
    for tf in SUPPORTED_TIMEFRAMES:
        print(f"   ✓ {tf}")
    
    # Проверяем доступные таймфреймы для символа
    print(f"\n🔍 Проверка доступных таймфреймов:")
    
    try:
        available_tf = get_available_timeframes("XAUUSD")
        print(f"   📈 Для XAUUSD доступно: {len(available_tf)} таймфреймов")
        for tf in available_tf[:5]:  # Показываем первые 5
            print(f"      • {tf}")
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки таймфреймов: {e}")


if __name__ == "__main__":
    try:
        print("🚀 BQuant - Демонстрация работы с данными")
        print("=" * 60)
        
        # 1. Создание данных
        sample_data, trending_data, volatile_data = demonstrate_data_creation()
        
        # 2. Валидация данных
        demonstrate_data_validation()
        
        # 3. Очистка данных
        cleaned_data = demonstrate_data_cleaning()
        
        # 4. Трансформации данных
        processed_data = demonstrate_data_transformations()
        
        # 5. Работа со схемами
        demonstrate_data_schemas()
        
        # 6. Поддержка таймфреймов
        demonstrate_timeframes_support()
        
        # 7. Сохранение результатов
        save_processed_data(processed_data, "comprehensive_processed_data.csv")
        save_processed_data(sample_data, "sample_ohlcv_data.csv")
        save_processed_data(trending_data, "trending_data.csv")
        save_processed_data(volatile_data, "volatile_data.csv")
        
        print(f"\n🎉 Демонстрация работы с данными завершена!")
        print(f"\n💡 Ключевые возможности:")
        print(f"   ✓ Создание и загрузка данных")
        print(f"   ✓ Валидация и очистка данных")
        print(f"   ✓ Трансформации и ресэмплинг")
        print(f"   ✓ Расчет производных индикаторов")
        print(f"   ✓ Создание лаговых признаков")
        print(f"   ✓ Нормализация данных")
        print(f"   ✓ Работа со схемами данных")
        print(f"   ✓ Поддержка различных таймфреймов")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
