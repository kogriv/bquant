"""
Tests for BQuant core modules (Steps 1.2-1.3)

Простые тесты для проверки базовых модулей: config, exceptions, logging, utils, numpy_fix
"""

import pytest
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
    print("\nТестирование модуля config:")
    
    # Тест получения пути к данным
    data_path = get_data_path('XAUUSD', '1h')
    assert isinstance(data_path, str) or hasattr(data_path, 'exists')
    
    print("[OK] get_data_path() возвращает корректный путь")
    
    # Тест получения параметров индикатора
    macd_params = get_indicator_params('macd')
    assert isinstance(macd_params, dict)
    assert 'fast' in macd_params
    assert 'slow' in macd_params
    
    print("[OK] get_indicator_params() возвращает параметры индикатора")
    
    # Тест получения параметров анализа
    analysis_params = get_analysis_params('zone_features')
    assert isinstance(analysis_params, dict)
    assert 'swing_strategy' in analysis_params
    
    print("[OK] get_analysis_params() возвращает параметры анализа")
    
    # Тест валидации таймфрейма
    valid_timeframe = validate_timeframe('1h')
    assert valid_timeframe == '1h'
    
    print("[OK] validate_timeframe() валидирует таймфреймы")
    
    # Тест получения пути к результатам
    results_path = get_results_path('test_experiment')
    assert isinstance(results_path, str) or hasattr(results_path, 'exists')
    
    print("[OK] get_results_path() возвращает путь к результатам")
    
    # Тест констант конфигурации
    assert isinstance(SUPPORTED_TIMEFRAMES, dict)
    assert isinstance(DEFAULT_INDICATORS, dict)
    assert isinstance(ANALYSIS_CONFIG, dict)
    assert isinstance(LOGGING, dict)
    
    print("[OK] Константы конфигурации доступны")


def test_exceptions_module():
    """Тест модуля исключений."""
    print("\nТестирование модуля exceptions:")
    
    # Тест базового исключения
    try:
        raise BQuantError("Test error", {'test': True})
    except BQuantError as e:
        assert "Test error" in str(e)
        assert e.details['test'] is True
    
    print("[OK] BQuantError работает корректно")
    
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
    
    print("[OK] Все специфические исключения наследуются от BQuantError")


def test_logging_module():
    """Тест модуля логгирования."""
    print("\nТестирование модуля logging:")
    
    # Тест получения логгера
    logger = get_logger(__name__)
    assert logger is not None
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')
    
    print("[OK] get_logger() возвращает корректный логгер")
    
    # Тест базовой настройки логгирования
    setup_logging(level='DEBUG')
    logger = get_logger('test_logger')
    logger.info("Test log message")
    
    print("[OK] setup_logging() настраивает логгирование")
    
    # Тест профилей логирования
    print("\nТестирование профилей логирования:")
    
    # Тест профиля 'research'
    setup_logging(profile='research')
    research_logger = get_logger('bquant.data.test')
    research_logger.info("Research profile test message")
    print("[OK] Профиль 'research' работает")
    
    # Тест профиля 'clean'
    setup_logging(profile='clean')
    clean_logger = get_logger('bquant.indicators.test')
    clean_logger.info("Clean profile test message")
    print("[OK] Профиль 'clean' работает")
    
    # Тест профиля 'debug'
    setup_logging(profile='debug')
    debug_logger = get_logger('bquant.test')
    debug_logger.debug("Debug profile test message")
    print("[OK] Профиль 'debug' работает")
    
    # Тест модульной настройки
    print("\nТестирование модульной настройки:")
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
    print("[OK] Модульная настройка работает")
    
    # Тест исключений
    print("\nТестирование исключений:")
    setup_logging(
        profile='research',
        exceptions={
            'bquant.test.special': 'DEBUG'
        }
    )
    special_logger = get_logger('bquant.test.special')
    special_logger.debug("Special logger debug message")
    print("[OK] Исключения работают")
    
    # Тест LoggingConfigurator
    print("\nТестирование LoggingConfigurator:")
    from bquant.core.logging_config import LoggingConfigurator
    
    configurator = LoggingConfigurator()
    configurator.preset('notebook', 'research').apply()
    configurator_logger = get_logger('bquant.test.configurator')
    configurator_logger.info("Configurator test message")
    print("[OK] LoggingConfigurator работает")


def test_utils_module():
    """Тест модуля утилит."""
    print("\nТестирование модуля utils:")
    
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
    
    print("[OK] calculate_returns() работает корректно")
    
    # Тест normalize_data
    normalized = normalize_data(test_data, method='zscore')
    assert isinstance(normalized, pd.DataFrame)
    assert normalized.shape == test_data.shape
    
    print("[OK] normalize_data() работает корректно")
    
    # Тест validate_ohlcv_columns
    validation = validate_ohlcv_columns(test_data)
    assert isinstance(validation, dict)
    assert 'is_valid' in validation
    
    print("[OK] validate_ohlcv_columns() работает корректно")
    
    # Тест create_timestamp
    timestamp = create_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) > 0
    
    print("[OK] create_timestamp() работает корректно")
    
    # Тест memory_usage_info
    memory_info = memory_usage_info(test_data)
    assert isinstance(memory_info, dict)
    assert 'total_memory_mb' in memory_info
    
    print("[OK] memory_usage_info() работает корректно")


def test_numpy_fix_module():
    """Тест модуля исправлений NumPy."""
    print("\nТестирование модуля numpy_fix:")
    
    # Применяем исправления
    apply_numpy_fixes()
    
    # Проверяем, что исправления применены
    # (конкретные проверки зависят от того, какие исправления применяются)
    print("[OK] apply_numpy_fixes() выполняется без ошибок")


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
            print(f"[FAIL] {test_func.__name__}: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print(f"[TARGET] Результаты тестирования базовых модулей:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ БАЗОВЫХ МОДУЛЕЙ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("[WARN] Некоторые тесты базовых модулей провалены")
        return False


if __name__ == "__main__":
    run_core_tests()


def test_data_path_takes_the_universal_timeframe_not_the_providers():
    """Кто переводит имя таймфрейма — тот и один.

    `get_data_path` принимает универсальное имя (`1h`) и само переводит его в
    словарь провайдера (`H1` у MetaTrader, `60` у TradingView). `load_symbol_data`
    переводил его **тоже** и передавал сюда уже переведённое, то есть значение
    чужого словаря под именем параметра, которое о словаре ничего не говорит.
    Валидацию из-за этого закомментировали 2025-08-31 — она честно сообщала
    «Unsupported timeframe: H1», и выключили сигнал, а не причину.

    Путь при этом не портился, но лишь по случайности: второй перевод — это
    `.get(x, x)`, который проваливается насквозь, когда переведённого имени нет
    среди ключей. Стоит любому провайдеру завести ключ, совпадающий с чужим
    выходом, и путь молча уедет.

    Разбор: `devref/gaps/deffered/issue_double_timeframe_validation.md`.
    """
    from bquant.core.config import get_data_path

    # Универсальное имя переводится ровно один раз.
    assert get_data_path('XAUUSD', '1h', 'metatrader').name == 'XAUUSDH1.csv'
    assert get_data_path('XAUUSD', '15m', 'metatrader').name == 'XAUUSDM15.csv'
    assert get_data_path('XAUUSD', '1h', 'tradingview').name == 'OANDA_XAUUSD, 60.csv'

    # Имя чужого словаря сюда попасть не должно, и проверка снова это ловит.
    # (`validate_timeframe` бросает голый `ValueError`, а не `ConfigurationError`
    # из иерархии `bquant.core.exceptions`, вопреки правилу AGENTS.md. Здесь
    # закрепляется поведение как есть; смена типа исключения — отдельная правка,
    # ломающая `except ValueError` у вызывающих.)
    for providers_name in ('H1', 'M15', 'Daily', '60'):
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            get_data_path('XAUUSD', providers_name, 'metatrader')

    # И тот же путь через публичную функцию загрузки: она обязана дойти до
    # поиска файла, а не упасть на валидации собственного перевода.
    from bquant.data.loader import load_symbol_data
    from bquant.core.exceptions import DataLoadingError

    with pytest.raises(DataLoadingError, match="XAUUSDH1.csv"):
        load_symbol_data('XAUUSD', '1h', data_source='metatrader')
