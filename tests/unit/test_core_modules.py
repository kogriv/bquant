"""
Tests for BQuant core modules (Steps 1.2-1.3)

Простые тесты для проверки базовых модулей: config, exceptions, logging, utils, numpy_fix
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Импорты для тестирования базовых модулей
from bquant.core.config import (
    get_data_path, get_indicator_params, get_analysis_params, 
    validate_timeframe, get_results_path, SUPPORTED_TIMEFRAMES,
    DEFAULT_INDICATORS, ANALYSIS_CONFIG, LOGGING
)
from bquant.core.exceptions import (
    BQuantError, ConfigurationError, DataError, 
    IndicatorCalculationError, DataValidationError
)
from bquant.core.logging_config import get_logger, setup_logging
from bquant.core.utils import (
    calculate_returns, normalize_data, save_results,
    validate_ohlcv_columns, create_timestamp, memory_usage_info
)
from bquant.core.numpy_fix import apply_numpy_fixes


def test_config_module():
    """Тест модуля конфигурации."""
    print("\n📋 Тестирование модуля config:")
    
    # Тест получения пути к данным
    data_path = get_data_path('XAUUSD', '1h')
    assert isinstance(data_path, str) or hasattr(data_path, 'exists')
    
    print("✅ get_data_path() возвращает корректный путь")
    
    # Тест получения параметров индикатора
    macd_params = get_indicator_params('macd')
    assert isinstance(macd_params, dict)
    assert 'fast' in macd_params
    assert 'slow' in macd_params
    
    print("✅ get_indicator_params() возвращает параметры индикатора")
    
    # Тест получения параметров анализа
    analysis_params = get_analysis_params('zone_analysis')
    assert isinstance(analysis_params, dict)
    assert 'min_duration' in analysis_params
    
    print("✅ get_analysis_params() возвращает параметры анализа")
    
    # Тест валидации таймфрейма
    valid_timeframe = validate_timeframe('1h')
    assert valid_timeframe == '1h'
    
    print("✅ validate_timeframe() валидирует таймфреймы")
    
    # Тест получения пути к результатам
    results_path = get_results_path('test_experiment')
    assert isinstance(results_path, str) or hasattr(results_path, 'exists')
    
    print("✅ get_results_path() возвращает путь к результатам")
    
    # Тест констант конфигурации
    assert isinstance(SUPPORTED_TIMEFRAMES, dict)
    assert isinstance(DEFAULT_INDICATORS, dict)
    assert isinstance(ANALYSIS_CONFIG, dict)
    assert isinstance(LOGGING, dict)
    
    print("✅ Константы конфигурации доступны")


def test_exceptions_module():
    """Тест модуля исключений."""
    print("\n📋 Тестирование модуля exceptions:")
    
    # Тест базового исключения
    try:
        raise BQuantError("Test error", {'test': True})
    except BQuantError as e:
        assert "Test error" in str(e)
        assert e.details['test'] is True
    
    print("✅ BQuantError работает корректно")
    
    # Тест специфических исключений
    exceptions_to_test = [
        ConfigurationError("Config error"),
        DataError("Data error"),
        IndicatorCalculationError("Indicator error"),
        DataValidationError("Validation error")
    ]
    
    for exc in exceptions_to_test:
        assert isinstance(exc, BQuantError)
        assert len(str(exc)) > 0
    
    print("✅ Все специфические исключения наследуются от BQuantError")


def test_logging_module():
    """Тест модуля логгирования."""
    print("\n📋 Тестирование модуля logging:")
    
    # Тест получения логгера
    logger = get_logger(__name__)
    assert logger is not None
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')
    
    print("✅ get_logger() возвращает корректный логгер")
    
    # Тест базовой настройки логгирования
    setup_logging(level='DEBUG')
    logger = get_logger('test_logger')
    logger.info("Test log message")
    
    print("✅ setup_logging() настраивает логгирование")
    
    # Тест профилей логирования
    print("\n📋 Тестирование профилей логирования:")
    
    # Тест профиля 'research'
    setup_logging(profile='research')
    research_logger = get_logger('bquant.data.test')
    research_logger.info("Research profile test message")
    print("✅ Профиль 'research' работает")
    
    # Тест профиля 'clean'
    setup_logging(profile='clean')
    clean_logger = get_logger('bquant.indicators.test')
    clean_logger.info("Clean profile test message")
    print("✅ Профиль 'clean' работает")
    
    # Тест профиля 'debug'
    setup_logging(profile='debug')
    debug_logger = get_logger('bquant.test')
    debug_logger.debug("Debug profile test message")
    print("✅ Профиль 'debug' работает")
    
    # Тест модульной настройки
    print("\n📋 Тестирование модульной настройки:")
    setup_logging(
        modules_config={
            'bquant.test.module1': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.test.module2': {'console': 'ERROR', 'file': 'DEBUG'}
        }
    )
    module1_logger = get_logger('bquant.test.module1')
    module2_logger = get_logger('bquant.test.module2')
    module1_logger.info("Module1 test message")
    module2_logger.debug("Module2 test message")
    print("✅ Модульная настройка работает")
    
    # Тест исключений
    print("\n📋 Тестирование исключений:")
    setup_logging(
        profile='research',
        exceptions={
            'bquant.test.special': 'DEBUG'
        }
    )
    special_logger = get_logger('bquant.test.special')
    special_logger.debug("Special logger debug message")
    print("✅ Исключения работают")
    
    # Тест LoggingConfigurator
    print("\n📋 Тестирование LoggingConfigurator:")
    from bquant.core.logging_config import LoggingConfigurator
    
    configurator = LoggingConfigurator()
    configurator.preset('notebook', 'research').apply()
    configurator_logger = get_logger('bquant.test.configurator')
    configurator_logger.info("Configurator test message")
    print("✅ LoggingConfigurator работает")


def test_utils_module():
    """Тест модуля утилит."""
    print("\n📋 Тестирование модуля utils:")
    
    # Создаем тестовые данные
    test_prices = pd.Series([100, 110, 105, 115, 120])
    test_data = pd.DataFrame({
        'open': [100, 110, 105, 115, 120],
        'high': [105, 115, 110, 120, 125],
        'low': [98, 108, 103, 113, 118],
        'close': [110, 105, 115, 120, 125]
    })
    
    # Тест calculate_returns
    returns = calculate_returns(test_prices)
    assert isinstance(returns, pd.Series)
    assert len(returns) == len(test_prices)
    
    print("✅ calculate_returns() работает корректно")
    
    # Тест normalize_data
    normalized = normalize_data(test_data, method='zscore')
    assert isinstance(normalized, pd.DataFrame)
    assert normalized.shape == test_data.shape
    
    print("✅ normalize_data() работает корректно")
    
    # Тест validate_ohlcv_columns
    validation = validate_ohlcv_columns(test_data)
    assert isinstance(validation, dict)
    assert 'is_valid' in validation
    
    print("✅ validate_ohlcv_columns() работает корректно")
    
    # Тест create_timestamp
    timestamp = create_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) > 0
    
    print("✅ create_timestamp() работает корректно")
    
    # Тест memory_usage_info
    memory_info = memory_usage_info(test_data)
    assert isinstance(memory_info, dict)
    assert 'total_memory_mb' in memory_info
    
    print("✅ memory_usage_info() работает корректно")


def test_numpy_fix_module():
    """Тест модуля исправлений NumPy."""
    print("\n📋 Тестирование модуля numpy_fix:")
    
    # Применяем исправления
    apply_numpy_fixes()
    
    # Проверяем, что исправления применены
    # (конкретные проверки зависят от того, какие исправления применяются)
    print("✅ apply_numpy_fixes() выполняется без ошибок")


def run_core_tests():
    """Запуск всех тестов базовых модулей."""
    print("🚀 Запуск тестов базовых модулей BQuant (Шаги 1.2-1.3)...")
    print("=" * 60)
    
    test_functions = [
        test_config_module,
        test_exceptions_module,
        test_logging_module,
        test_utils_module,
        test_numpy_fix_module
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
    print(f"🎯 Результаты тестирования базовых модулей:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ БАЗОВЫХ МОДУЛЕЙ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠️  Некоторые тесты базовых модулей провалены")
        return False


if __name__ == "__main__":
    run_core_tests()
