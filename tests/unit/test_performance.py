"""
Тесты производительности для BQuant

Этот модуль содержит тесты для измерения и оптимизации производительности
основных компонентов BQuant.
"""

import pytest
import pandas as pd
import numpy as np
import time
import psutil
import os
from typing import Dict, List, Any, Tuple
from functools import wraps
from datetime import datetime, timedelta
import warnings

# BQuant imports
from bquant.indicators.calculators import (
    IndicatorCalculator, 
    calculate_macd, 
    calculate_rsi, 
    calculate_bollinger_bands,
    calculate_moving_averages,
    create_indicator_suite
)
from bquant.indicators.macd import MACDZoneAnalyzer, analyze_macd_zones
from bquant.data.processor import (
    calculate_derived_indicators,
    clean_ohlcv_data,
    prepare_data_for_analysis
)
from bquant.core.logging_config import get_logger

warnings.filterwarnings('ignore')
logger = get_logger(__name__)


def performance_test(func):
    """Декоратор для измерения производительности тестов."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Измеряем использование памяти до теста
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Измеряем время выполнения
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # Измеряем использование памяти после теста
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = memory_after - memory_before
        
        execution_time = end_time - start_time
        
        logger.info(f"Performance test {func.__name__}:")
        logger.info(f"  Execution time: {execution_time:.4f} seconds")
        logger.info(f"  Memory usage: {memory_delta:.2f} MB delta, {memory_after:.2f} MB total")
        
        return result
    return wrapper


def create_large_ohlcv_data(rows: int = 10000, symbol: str = "XAUUSD") -> pd.DataFrame:
    """
    Создает большой набор OHLCV данных для тестирования производительности.
    
    Args:
        rows: Количество строк данных
        symbol: Символ инструмента
    
    Returns:
        DataFrame с OHLCV данными
    """
    logger.info(f"Creating large OHLCV dataset: {rows} rows for {symbol}")
    
    # Создаем синтетические данные
    np.random.seed(42)  # Для воспроизводимости
    
    # Базовые параметры для цены
    base_price = 2000.0  # Базовая цена для XAUUSD
    volatility = 0.02    # Дневная волатильность 2%
    
    # Генерируем временные метки
    start_date = datetime(2020, 1, 1)
    timestamps = [start_date + timedelta(hours=i) for i in range(rows)]
    
    # Генерируем ценовые данные с использованием случайного блуждания
    price_changes = np.random.normal(0, volatility, rows)
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # Цена не может быть отрицательной
    
    # Создаем OHLCV данные
    data = []
    
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Добавляем внутридневную волатильность
        intraday_vol = volatility * 0.3
        high = close * (1 + abs(np.random.normal(0, intraday_vol)))
        low = close * (1 - abs(np.random.normal(0, intraday_vol)))
        
        # Open цена - либо предыдущий close, либо близко к нему
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1] * (1 + np.random.normal(0, intraday_vol * 0.5))
        
        # Убеждаемся что high >= max(open, close) и low <= min(open, close)
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Объем - случайное число с некоторой корреляцией с волатильностью
        volume = abs(np.random.normal(10000, 5000))
        
        data.append({
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(volume)
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Created dataset with {len(df)} rows, shape: {df.shape}")
    return df


class TestIndicatorPerformance:
    """Тесты производительности для расчета индикаторов."""
    
    @pytest.fixture
    def small_data(self):
        """Малый набор данных (1000 баров)."""
        return create_large_ohlcv_data(1000)
    
    @pytest.fixture  
    def medium_data(self):
        """Средний набор данных (5000 баров)."""
        return create_large_ohlcv_data(5000)
    
    @pytest.fixture
    def large_data(self):
        """Большой набор данных (10000 баров)."""
        return create_large_ohlcv_data(10000)
    
    @performance_test
    def test_macd_performance_small(self, small_data):
        """Тест производительности MACD на малых данных."""
        macd_data = calculate_macd(small_data, fast=12, slow=26, signal=9)
        
        assert isinstance(macd_data, pd.DataFrame)
        assert 'macd' in macd_data.columns
        assert 'macd_signal' in macd_data.columns
        assert 'macd_hist' in macd_data.columns
        assert len(macd_data) == len(small_data)
        
        logger.info(f"MACD calculation completed for {len(small_data)} bars")
    
    @performance_test
    def test_macd_performance_medium(self, medium_data):
        """Тест производительности MACD на средних данных."""
        macd_data = calculate_macd(medium_data, fast=12, slow=26, signal=9)
        
        assert isinstance(macd_data, pd.DataFrame)
        assert 'macd' in macd_data.columns
        assert 'macd_signal' in macd_data.columns
        assert 'macd_hist' in macd_data.columns
        assert len(macd_data) == len(medium_data)
        
        logger.info(f"MACD calculation completed for {len(medium_data)} bars")
    
    @performance_test
    def test_macd_performance_large(self, large_data):
        """Тест производительности MACD на больших данных."""
        macd_data = calculate_macd(large_data, fast=12, slow=26, signal=9)
        
        assert isinstance(macd_data, pd.DataFrame)
        assert 'macd' in macd_data.columns
        assert 'macd_signal' in macd_data.columns
        assert 'macd_hist' in macd_data.columns
        assert len(macd_data) == len(large_data)
        
        logger.info(f"MACD calculation completed for {len(large_data)} bars")
    
    @performance_test
    def test_rsi_performance(self, large_data):
        """Тест производительности RSI."""
        rsi_data = calculate_rsi(large_data, period=14)
        
        assert isinstance(rsi_data, pd.Series)
        assert len(rsi_data) == len(large_data)
        assert not rsi_data.isna().all()
        
        logger.info(f"RSI calculation completed for {len(large_data)} bars")
    
    @performance_test
    def test_bollinger_bands_performance(self, large_data):
        """Тест производительности Bollinger Bands."""
        bb_data = calculate_bollinger_bands(large_data, period=20, std_dev=2.0)
        
        assert isinstance(bb_data, pd.DataFrame)
        assert 'bb_upper' in bb_data.columns
        assert 'bb_middle' in bb_data.columns  
        assert 'bb_lower' in bb_data.columns
        assert len(bb_data) == len(large_data)
        
        logger.info(f"Bollinger Bands calculation completed for {len(large_data)} bars")
    
    @performance_test
    def test_moving_averages_performance(self, large_data):
        """Тест производительности скользящих средних."""
        ma_data = calculate_moving_averages(large_data, periods=[10, 20, 50, 100, 200])
        
        assert isinstance(ma_data, pd.DataFrame)
        assert len(ma_data) == len(large_data)
        
        # Проверяем наличие основных колонок
        expected_cols = ['sma_10', 'sma_20', 'sma_50', 'ema_10', 'ema_20', 'ema_50']
        for col in expected_cols:
            assert col in ma_data.columns, f"Missing column: {col}"
        
        logger.info(f"Moving averages calculation completed for {len(large_data)} bars")
    
    @performance_test
    def test_indicator_suite_performance(self, large_data):
        """Тест производительности стандартного набора индикаторов."""
        results = create_indicator_suite(large_data)
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Проверяем основные индикаторы
        expected_indicators = ['sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi_14', 'macd', 'bbands']
        for indicator in expected_indicators:
            assert indicator in results, f"Missing indicator: {indicator}"
        
        logger.info(f"Indicator suite calculation completed: {len(results)} indicators")


class TestCalculatorPerformance:
    """Тесты производительности IndicatorCalculator."""
    
    @pytest.fixture
    def large_data(self):
        """Большой набор данных."""
        return create_large_ohlcv_data(10000)
    
    @performance_test
    def test_calculator_initialization(self, large_data):
        """Тест производительности инициализации калькулятора."""
        calculator = IndicatorCalculator(large_data, auto_load_libraries=True)
        
        assert calculator.data is not None
        assert len(calculator.data) == len(large_data)
        assert isinstance(calculator.results, dict)
        
        logger.info("IndicatorCalculator initialization completed")
    
    @performance_test
    def test_calculator_multiple_indicators(self, large_data):
        """Тест производительности расчета нескольких индикаторов."""
        calculator = IndicatorCalculator(large_data, auto_load_libraries=False)
        
        indicators = {
            'sma_20': {'period': 20},
            'ema_20': {'period': 20},
            'rsi_14': {'period': 14},
            'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
        }
        
        results = calculator.calculate_multiple(indicators)
        
        assert isinstance(results, dict)
        assert len(results) == len(indicators)
        
        for indicator_name in indicators.keys():
            assert indicator_name in results
            
        logger.info(f"Multiple indicators calculation completed: {len(results)} indicators")
    
    @performance_test
    def test_calculator_caching(self, large_data):
        """Тест производительности кэширования."""
        calculator = IndicatorCalculator(large_data, auto_load_libraries=False)
        
        # Первый расчет MACD
        start_time = time.perf_counter()
        result1 = calculator.calculate('macd', fast_period=12, slow_period=26, signal_period=9)
        first_calculation_time = time.perf_counter() - start_time
        
        # Повторный доступ к результату (должен быть из кэша)
        start_time = time.perf_counter()
        result2 = calculator.get_result('macd')
        cache_access_time = time.perf_counter() - start_time
        
        assert result1 is not None
        assert result2 is not None
        assert cache_access_time < first_calculation_time  # Кэш должен быть быстрее
        
        logger.info(f"Cache performance: first calculation {first_calculation_time:.4f}s, cache access {cache_access_time:.6f}s")


class TestMACDAnalyzerPerformance:
    """Тесты производительности MACDZoneAnalyzer."""
    
    @pytest.fixture
    def trending_data(self):
        """Трендовые данные для анализа зон."""
        data = create_large_ohlcv_data(5000)
        
        # Добавляем тренд для создания выраженных MACD зон
        trend = np.linspace(0, 100, len(data))
        noise = np.random.normal(0, 2, len(data))
        
        data['close'] = data['close'] + trend + noise
        data['high'] = data[['high', 'close']].max(axis=1) + 0.5
        data['low'] = data[['low', 'close']].min(axis=1) - 0.5
        
        return data
    
    @performance_test
    def test_zone_identification_performance(self, trending_data):
        """Тест производительности определения зон."""
        macd_params = {
            'fast': 12,
            'slow': 26, 
            'signal': 9
        }
        
        zone_params = {
            'min_zone_length': 5,
            'significance_threshold': 0.1
        }
        
        analyzer = MACDZoneAnalyzer(macd_params, zone_params)
        zones = analyzer.identify_zones(trending_data)
        
        assert isinstance(zones, list)
        assert len(zones) > 0
        
        for zone in zones:
            assert hasattr(zone, 'type')
            assert hasattr(zone, 'start_idx')
            assert hasattr(zone, 'end_idx')
            assert zone.type in ['bull', 'bear']
        
        logger.info(f"Zone identification completed: {len(zones)} zones found")
    
    @performance_test
    def test_zone_features_performance(self, trending_data):
        """Тест производительности расчета признаков зон."""
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(trending_data)
        
        all_features = []
        for zone in zones:
            features = analyzer.calculate_zone_features(zone, trending_data)
            all_features.append(features)
        
        assert len(all_features) == len(zones)
        
        for features in all_features:
            assert isinstance(features, dict)
            assert 'duration' in features
            assert 'amplitude' in features
            assert 'correlation_price_macd' in features
        
        logger.info(f"Zone features calculation completed for {len(zones)} zones")
    
    @performance_test
    def test_statistical_analysis_performance(self, trending_data):
        """Тест производительности статистических тестов."""
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(trending_data)
        
        # Вычисляем признаки для всех зон
        for zone in zones:
            zone.features = analyzer.calculate_zone_features(zone, trending_data)
        
        hypothesis_tests = analyzer.test_hypotheses(zones)
        
        assert isinstance(hypothesis_tests, list)
        assert len(hypothesis_tests) > 0
        
        for test in hypothesis_tests:
            assert 'hypothesis' in test
            assert 'p_value' in test
            assert 'result' in test
        
        logger.info(f"Statistical analysis completed: {len(hypothesis_tests)} tests")
    
    @performance_test
    def test_clustering_performance(self, trending_data):
        """Тест производительности кластеризации."""
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(trending_data)
        
        # Вычисляем признаки для всех зон
        for zone in zones:
            zone.features = analyzer.calculate_zone_features(zone, trending_data)
        
        if len(zones) >= 3:  # Нужно минимум 3 зоны для кластеризации
            cluster_result = analyzer.cluster_zones_by_shape(zones, n_clusters=3)
            
            assert 'cluster_labels' in cluster_result
            assert 'cluster_centers' in cluster_result
            assert 'silhouette_score' in cluster_result
            assert len(cluster_result['cluster_labels']) == len(zones)
            
            logger.info(f"Clustering completed for {len(zones)} zones")
        else:
            logger.warning(f"Not enough zones for clustering: {len(zones)}")
    
    @performance_test
    def test_complete_analysis_performance(self, trending_data):
        """Тест производительности полного анализа."""
        result = analyze_macd_zones(
            trending_data,
            perform_clustering=True,
            n_clusters=3
        )
        
        assert result is not None
        assert hasattr(result, 'zones')
        assert hasattr(result, 'statistics')
        assert hasattr(result, 'hypothesis_tests')
        
        logger.info(f"Complete MACD analysis completed: {len(result.zones)} zones")


class TestDataProcessingPerformance:
    """Тесты производительности обработки данных."""
    
    @pytest.fixture
    def large_data(self):
        """Большой набор данных."""
        return create_large_ohlcv_data(10000)
    
    @performance_test
    def test_data_validation_performance(self, large_data):
        """Тест производительности валидации данных."""
        prepared_data = prepare_data_for_analysis(large_data)
        
        assert prepared_data is not None
        assert isinstance(prepared_data, pd.DataFrame)
        
        logger.info(f"Data validation completed for {len(large_data)} rows")
    
    @performance_test
    def test_data_cleaning_performance(self, large_data):
        """Тест производительности очистки данных."""
        # Добавляем немного "грязных" данных
        dirty_data = large_data.copy()
        dirty_data.loc[100:110, 'close'] = np.nan
        dirty_data.loc[500:505, 'volume'] = -1  # Некорректные данные
        
        cleaned_data = clean_ohlcv_data(dirty_data)
        
        assert isinstance(cleaned_data, pd.DataFrame)
        assert len(cleaned_data) <= len(dirty_data)  # Могли удалить плохие строки
        
        logger.info(f"Data cleaning completed: {len(cleaned_data)} rows remaining")
    
    @performance_test
    def test_derived_indicators_performance(self, large_data):
        """Тест производительности расчета производных индикаторов."""
        derived_data = calculate_derived_indicators(large_data)
        
        assert isinstance(derived_data, pd.DataFrame)
        assert len(derived_data) == len(large_data)
        
        # Проверяем наличие производных индикаторов
        expected_cols = ['hl_avg', 'ohlc_avg', 'true_range']
        for col in expected_cols:
            assert col in derived_data.columns, f"Missing derived indicator: {col}"
        
        logger.info(f"Derived indicators calculation completed for {len(large_data)} rows")


class TestMemoryUsage:
    """Тесты использования памяти."""
    
    def test_memory_usage_large_dataset(self):
        """Тест использования памяти при работе с большими данными."""
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем очень большой набор данных
        large_data = create_large_ohlcv_data(50000)
        memory_after_data = process.memory_info().rss / 1024 / 1024
        
        # Вычисляем множественные индикаторы
        calculator = IndicatorCalculator(large_data, auto_load_libraries=False)
        results = create_indicator_suite(large_data)
        memory_after_calc = process.memory_info().rss / 1024 / 1024
        
        # Очищаем кэш
        calculator.clear_cache()
        del large_data, results, calculator
        memory_after_cleanup = process.memory_info().rss / 1024 / 1024
        
        logger.info("Memory usage test:")
        logger.info(f"  Initial: {memory_before:.2f} MB")
        logger.info(f"  After data creation: {memory_after_data:.2f} MB (+{memory_after_data-memory_before:.2f})")
        logger.info(f"  After calculations: {memory_after_calc:.2f} MB (+{memory_after_calc-memory_after_data:.2f})")
        logger.info(f"  After cleanup: {memory_after_cleanup:.2f} MB")
        
        # Проверяем, что память освобождается
        memory_increase = memory_after_cleanup - memory_before
        assert memory_increase < 100, f"Memory leak detected: {memory_increase:.2f} MB not released"


def benchmark_indicators(data_sizes: List[int] = None) -> Dict[str, List[float]]:
    """
    Бенчмарк производительности индикаторов для разных размеров данных.
    
    Args:
        data_sizes: Список размеров данных для тестирования
    
    Returns:
        Словарь с результатами бенчмарка
    """
    if data_sizes is None:
        data_sizes = [1000, 2500, 5000, 7500, 10000]
    
    indicators = {
        'MACD': lambda data: calculate_macd(data),
        'RSI': lambda data: calculate_rsi(data),
        'Bollinger Bands': lambda data: calculate_bollinger_bands(data),
        'Moving Averages': lambda data: calculate_moving_averages(data),
    }
    
    results = {indicator: [] for indicator in indicators.keys()}
    results['data_size'] = data_sizes
    
    logger.info(f"Starting benchmark for data sizes: {data_sizes}")
    
    for size in data_sizes:
        logger.info(f"Benchmarking with {size} bars...")
        test_data = create_large_ohlcv_data(size)
        
        for indicator_name, indicator_func in indicators.items():
            start_time = time.perf_counter()
            try:
                _ = indicator_func(test_data)
                execution_time = time.perf_counter() - start_time
                results[indicator_name].append(execution_time)
                logger.info(f"  {indicator_name}: {execution_time:.4f}s")
            except Exception as e:
                logger.error(f"  {indicator_name} failed: {e}")
                results[indicator_name].append(float('inf'))
    
    return results


def run_performance_suite():
    """Запуск полного набора тестов производительности."""
    logger.info("Starting BQuant performance test suite...")
    
    # Запускаем бенчмарк
    benchmark_results = benchmark_indicators()
    
    logger.info("Performance benchmark completed:")
    for indicator, times in benchmark_results.items():
        if indicator != 'data_size':
            avg_time = np.mean([t for t in times if t != float('inf')])
            logger.info(f"  {indicator}: average {avg_time:.4f}s per calculation")
    
    logger.info("Performance test suite completed!")
    return benchmark_results


if __name__ == "__main__":
    # Запуск всех тестов производительности
    run_performance_suite()
