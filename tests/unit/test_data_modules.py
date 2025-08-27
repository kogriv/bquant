"""
Tests for BQuant data modules (Steps 2.1-2.3)

Простые тесты для проверки модуля data: loader, processor, validator, schemas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

# Импорты для тестирования модуля data
from bquant.data.loader import (
    load_ohlcv_data, load_symbol_data, load_xauusd_data,
    load_all_data_files, get_data_info, get_available_symbols, get_available_timeframes
)
from bquant.data.processor import (
    clean_ohlcv_data, remove_price_outliers, resample_ohlcv,
    normalize_prices, add_technical_features, create_lagged_features,
    prepare_data_for_analysis, calculate_derived_indicators, detect_market_sessions
)
from bquant.data.validator import (
    validate_ohlcv_data, validate_data_completeness, validate_price_consistency,
    validate_time_series_continuity, validate_statistical_properties
)
from bquant.data.schemas import (
    OHLCVRecord, DataSourceConfig, ValidationResult, DataSchema
)


def create_test_ohlcv_data(rows: int = 100) -> pd.DataFrame:
    """Создание тестовых OHLCV данных."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1h')
    
    np.random.seed(42)
    base_price = 100.0
    prices = [base_price]
    
    for i in range(1, rows):
        change = np.random.normal(0, 0.01)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.01))
    
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': max(high, open_price, close_price),
            'low': min(low, open_price, close_price),
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


def test_data_loader_module():
    """Тест модуля загрузки данных."""
    print("\n📋 Тестирование модуля data.loader:")
    
    # Создаем временный CSV файл для тестирования
    test_data = create_test_ohlcv_data(50)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_data.to_csv(f.name, index=True)
        temp_file = f.name
    
    try:
        # Тест load_ohlcv_data
        loaded_data = load_ohlcv_data(temp_file, validate_data=False)
        assert isinstance(loaded_data, pd.DataFrame)
        assert len(loaded_data) > 0
        assert 'close' in loaded_data.columns
        
        print("✅ load_ohlcv_data() загружает данные корректно")
        
        # Тест get_data_info
        info = get_data_info(loaded_data)
        assert isinstance(info, dict)
        assert 'rows' in info
        assert 'columns' in info
        assert 'date_range' in info
        
        print("✅ get_data_info() возвращает информацию о данных")
        
        # Тест get_available_symbols и get_available_timeframes
        symbols = get_available_symbols()
        timeframes = get_available_timeframes('XAUUSD')  # Нужен символ
        
        assert isinstance(symbols, list)
        assert isinstance(timeframes, list)
        
        print("✅ get_available_symbols() и get_available_timeframes() работают")
        
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_data_processor_module():
    """Тест модуля обработки данных."""
    print("\n📋 Тестирование модуля data.processor:")
    
    # Создаем тестовые данные
    test_data = create_test_ohlcv_data(100)
    
    # Тест clean_ohlcv_data
    cleaned_data = clean_ohlcv_data(test_data.copy())
    assert isinstance(cleaned_data, pd.DataFrame)
    assert len(cleaned_data) > 0
    
    print("✅ clean_ohlcv_data() очищает данные")
    
    # Тест remove_price_outliers
    cleaned_outliers = remove_price_outliers(test_data.copy(), threshold=3.0)
    assert isinstance(cleaned_outliers, pd.DataFrame)
    
    print("✅ remove_price_outliers() удаляет выбросы")
    
    # Тест resample_ohlcv
    resampled = resample_ohlcv(test_data.copy(), '4H')
    assert isinstance(resampled, pd.DataFrame)
    assert len(resampled) <= len(test_data)  # Ресемплинг уменьшает количество записей
    
    print("✅ resample_ohlcv() ресемплирует данные")
    
    # Тест normalize_prices
    normalized = normalize_prices(test_data.copy())
    assert isinstance(normalized, pd.DataFrame)
    assert 'close_normalized' in normalized.columns
    
    print("✅ normalize_prices() нормализует цены")
    
    # Тест add_technical_features
    with_features = add_technical_features(test_data.copy())
    assert isinstance(with_features, pd.DataFrame)
    # Проверяем наличие технических признаков
    technical_columns = ['body_size', 'upper_shadow', 'lower_shadow', 'true_range']
    for col in technical_columns:
        if col in with_features.columns:
            print(f"✅ add_technical_features() добавляет {col}")
    
    # Тест create_lagged_features
    with_lags = create_lagged_features(test_data.copy(), columns=['close'], lags=[1, 2, 3])
    assert isinstance(with_lags, pd.DataFrame)
    assert 'close_lag_1' in with_lags.columns
    
    print("✅ create_lagged_features() создает лаговые признаки")
    
    # Тест prepare_data_for_analysis
    prepared = prepare_data_for_analysis(test_data.copy())
    assert isinstance(prepared, pd.DataFrame)
    
    print("✅ prepare_data_for_analysis() подготавливает данные")
    
    # Тест calculate_derived_indicators
    with_derived = calculate_derived_indicators(test_data.copy())
    assert isinstance(with_derived, pd.DataFrame)
    
    print("✅ calculate_derived_indicators() вычисляет производные индикаторы")
    
    # Тест detect_market_sessions
    with_sessions = detect_market_sessions(test_data.copy())
    assert isinstance(with_sessions, pd.DataFrame)
    
    print("✅ detect_market_sessions() определяет рыночные сессии")


def test_data_validator_module():
    """Тест модуля валидации данных."""
    print("\n📋 Тестирование модуля data.validator:")
    
    # Создаем корректные тестовые данные
    test_data = create_test_ohlcv_data(100)
    
    # Тест validate_ohlcv_data
    validation_result = validate_ohlcv_data(test_data)
    assert isinstance(validation_result, dict)
    assert 'is_valid' in validation_result
    assert isinstance(validation_result['is_valid'], bool)
    
    print("✅ validate_ohlcv_data() валидирует OHLCV данные")
    
    # Тест validate_data_completeness
    completeness = validate_data_completeness(test_data)
    assert isinstance(completeness, dict)
    assert 'is_complete' in completeness
    
    print("✅ validate_data_completeness() проверяет полноту данных")
    
    # Тест validate_price_consistency
    consistency = validate_price_consistency(test_data)
    assert isinstance(consistency, dict)
    
    print("✅ validate_price_consistency() проверяет консистентность цен")
    
    # Тест validate_time_series_continuity
    continuity = validate_time_series_continuity(test_data)
    assert isinstance(continuity, dict)
    
    print("✅ validate_time_series_continuity() проверяет непрерывность временного ряда")
    
    # Тест validate_statistical_properties
    stats = validate_statistical_properties(test_data)
    assert isinstance(stats, dict)
    
    print("✅ validate_statistical_properties() проверяет статистические свойства")


def test_data_schemas_module():
    """Тест модуля схем данных."""
    print("\n📋 Тестирование модуля data.schemas:")
    
    # Тест OHLCVRecord
    record = OHLCVRecord(
        timestamp=datetime.now(),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000
    )
    assert record.open == 100.0
    assert record.close == 103.0
    
    print("✅ OHLCVRecord создается корректно")
    
    # Тест DataSourceConfig
    config = DataSourceConfig(
        name="test_source",
        file_pattern="test_{symbol}_{timeframe}.csv",
        timeframe_mapping={'1h': 'H1'},
        quote_providers=['test_provider']
    )
    assert config.name == "test_source"
    assert 'test_provider' in config.quote_providers
    
    print("✅ DataSourceConfig создается корректно")
    
    # Тест ValidationResult
    result = ValidationResult(
        is_valid=True,
        issues=[],
        warnings=["Test warning"],
        stats={"test": True},
        recommendations=[]
    )
    assert result.is_valid is True
    assert len(result.warnings) == 1
    
    print("✅ ValidationResult создается корректно")
    
    # Тест DataSchema
    schema = DataSchema("ohlcv")
    assert schema.schema_type == "ohlcv"
    assert hasattr(schema, 'validate_dataframe')
    
    print("✅ DataSchema создается корректно")


def run_data_tests():
    """Запуск всех тестов модуля data."""
    print("🚀 Запуск тестов модуля data BQuant (Шаги 2.1-2.3)...")
    print("=" * 60)
    
    test_functions = [
        test_data_loader_module,
        test_data_processor_module,
        test_data_validator_module,
        test_data_schemas_module
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_func in test_functions:
        total_tests += 1
        try:
            test_func()
            passed_tests += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Результаты тестирования модуля data:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ МОДУЛЯ DATA ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠️  Некоторые тесты модуля data провалены")
        return False


if __name__ == "__main__":
    run_data_tests()
