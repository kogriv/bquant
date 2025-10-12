"""
Pytest configuration and fixtures for BQuant tests.

Общие fixtures и настройки для всех тестов BQuant.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Any

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.fixtures import (
    create_sample_ohlcv_data,
    create_sample_macd_data,
    create_sample_zones_data,
    create_sample_analysis_results,
    TestDataFixtures,
    MACD_PARAMS,
    ZONE_PARAMS,
    PERFORMANCE_THRESHOLDS
)


@pytest.fixture(scope="session")
def project_root_path():
    """Путь к корневой папке проекта."""
    return project_root


@pytest.fixture(scope="session")
def sample_ohlcv_data():
    """Sample OHLCV данные для тестов."""
    return create_sample_ohlcv_data(100)


@pytest.fixture(scope="session")
def small_ohlcv_data():
    """Небольшие OHLCV данные для быстрых тестов."""
    return TestDataFixtures.small_ohlcv(50)


@pytest.fixture(scope="session")
def large_ohlcv_data():
    """Большие OHLCV данные для performance тестов."""
    return TestDataFixtures.large_ohlcv(1000)


@pytest.fixture(scope="session")
def sample_macd_data():
    """Sample данные с рассчитанными MACD индикаторами."""
    return create_sample_macd_data(100)


@pytest.fixture(scope="session")
def sample_zones():
    """Sample зоны для тестирования анализа."""
    return create_sample_zones_data()


@pytest.fixture(scope="session")
def sample_analysis_results():
    """Sample результаты анализа."""
    return create_sample_analysis_results()


@pytest.fixture(scope="function")
def macd_params():
    """Параметры MACD для тестов."""
    return MACD_PARAMS.copy()


@pytest.fixture(scope="function")
def zone_params():
    """Параметры зон для тестов."""
    return ZONE_PARAMS.copy()


@pytest.fixture(scope="function")
def performance_thresholds():
    """Пороги производительности для тестов."""
    return PERFORMANCE_THRESHOLDS.copy()


@pytest.fixture(scope="function")
def test_symbols():
    """Список тестовых символов."""
    return ['XAUUSD', 'EURUSD', 'TEST_SYMBOL']


@pytest.fixture(scope="function")
def test_timeframes():
    """Список тестовых таймфреймов."""
    return ['1h', '4h', '1d']


@pytest.fixture(autouse=True)
def suppress_warnings():
    """Подавление предупреждений в тестах."""
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)


@pytest.fixture(scope="session")
def bquant_test_data():
    """
    Comprehensive тестовые данные BQuant.
    
    Returns:
        Dict с различными типами тестовых данных
    """
    return {
        'ohlcv_small': TestDataFixtures.small_ohlcv(50),
        'ohlcv_medium': TestDataFixtures.small_ohlcv(100),
        'ohlcv_large': TestDataFixtures.large_ohlcv(1000),
        'macd_data': TestDataFixtures.macd_with_zones(100),
        'zones': TestDataFixtures.sample_zones(),
        'analysis_results': TestDataFixtures.analysis_results(),
        'symbols': ['XAUUSD', 'EURUSD', 'BTCUSD'],
        'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
        'params': {
            'macd': MACD_PARAMS,
            'zones': ZONE_PARAMS,
            'performance': PERFORMANCE_THRESHOLDS
        }
    }


# Функции для создания временных данных в тестах
def create_temp_csv_data(tmp_path, symbol='TEST', periods=100):
    """Создать временный CSV файл с тестовыми данными."""
    data = create_sample_ohlcv_data(periods)
    file_path = tmp_path / f"{symbol}_test_data.csv"
    data.to_csv(file_path)
    return file_path


# Маркеры для категоризации тестов
def pytest_configure(config):
    """Конфигурация pytest с custom маркерами."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_sample_data: marks tests that require sample data"
    )
    
    # Register all strategies at test startup
    try:
        from bquant.analysis.zones.strategies.swing import (
            ZigZagSwingStrategy,
            FindPeaksSwingStrategy,
            PivotPointsSwingStrategy
        )
        from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
        from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
        from bquant.analysis.zones.strategies.volatility import CombinedVolatilityStrategy
        from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy
    except ImportError:
        pass  # Strategies may not be available in all test contexts


# Фикстуры для работы с BQuant sample data
@pytest.fixture(scope="session")
def sample_data_available():
    """Проверка доступности sample data."""
    try:
        from bquant.data.samples import list_dataset_names
        datasets = list_dataset_names()
        return len(datasets) > 0
    except ImportError:
        return False


@pytest.fixture(scope="function")
def skip_if_no_sample_data(sample_data_available):
    """Пропуск тестов если sample data недоступны."""
    if not sample_data_available:
        pytest.skip("Sample data not available")


# Helper функции для тестов
class TestHelpers:
    """Вспомогательные функции для тестов."""
    
    @staticmethod
    def assert_dataframe_structure(df: pd.DataFrame, expected_columns: List[str]):
        """Проверить структуру DataFrame."""
        assert isinstance(df, pd.DataFrame), "Expected pandas DataFrame"
        assert len(df) > 0, "DataFrame should not be empty"
        for col in expected_columns:
            assert col in df.columns, f"Column '{col}' missing from DataFrame"
    
    @staticmethod
    def assert_ohlcv_structure(df: pd.DataFrame):
        """Проверить структуру OHLCV DataFrame."""
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        TestHelpers.assert_dataframe_structure(df, expected_columns)
        
        # Проверяем логику OHLC
        assert (df['high'] >= df['open']).all(), "High should be >= Open"
        assert (df['high'] >= df['close']).all(), "High should be >= Close"
        assert (df['low'] <= df['open']).all(), "Low should be <= Open"
        assert (df['low'] <= df['close']).all(), "Low should be <= Close"
        assert (df['volume'] > 0).all(), "Volume should be positive"
    
    @staticmethod
    def assert_analysis_result_structure(result: Dict[str, Any]):
        """Проверить структуру результата анализа."""
        required_keys = ['metadata', 'data_info', 'macd_analysis', 'summary']
        for key in required_keys:
            assert key in result, f"Key '{key}' missing from analysis result"
        
        # Проверяем metadata
        metadata = result['metadata']
        assert 'symbol' in metadata
        assert 'timeframe' in metadata
        assert 'analysis_date' in metadata
        
        # Проверяем summary
        summary = result['summary']
        assert 'recommendation' in summary
        assert 'key_insights' in summary


@pytest.fixture(scope="session")
def test_helpers():
    """Доступ к helper функциям в тестах."""
    return TestHelpers
