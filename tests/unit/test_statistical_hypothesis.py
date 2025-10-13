"""
Тесты для модуля тестирования гипотез BQuant

Проверяют корректность переноса и адаптации функций из оригинального hypothesis_testing.py.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

# BQuant imports
from bquant.analysis.statistical.hypothesis_testing import (
    HypothesisTestResult,
    HypothesisTestSuite,
    run_all_hypothesis_tests,
    run_single_hypothesis_test
)
from bquant.analysis.statistical import run_all_hypothesis_tests as imported_run_all
from bquant.core.exceptions import StatisticalAnalysisError


def create_test_zones_features(n_zones: int = 50, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Создает тестовые данные с характеристиками зон для тестирования гипотез.
    
    Args:
        n_zones: Количество зон
        seed: Семя для генератора случайных чисел
    
    Returns:
        Список словарей с характеристиками зон
    """
    np.random.seed(seed)
    
    zones_features = []
    
    for i in range(n_zones):
        # Случайный тип зоны
        zone_type = 'bull' if np.random.random() > 0.5 else 'bear'
        
        # Длительность зоны (с некоторой корреляцией с типом)
        if zone_type == 'bull':
            duration = np.random.exponential(15) + 5  # Бычьи зоны немного дольше
        else:
            duration = np.random.exponential(12) + 3
        
        # Доходность (с небольшим bias для разных типов зон)
        if zone_type == 'bull':
            price_return = np.random.normal(0.02, 0.15)  # Слегка положительная
        else:
            price_return = np.random.normal(-0.01, 0.12)  # Слегка отрицательная
        
        # Наклон гистограммы (коррелирован с длительностью)
        hist_slope = np.random.normal(0, 0.1) + duration * 0.001
        
        # MACD амплитуда
        macd_amplitude = np.random.exponential(2) + 0.5
        
        # ATR-нормализованная доходность
        atr = np.random.exponential(1) + 0.1
        price_return_atr = price_return / atr
        
        # Корреляция цены и гистограммы MACD
        correlation_price_hist = np.random.uniform(-1, 1)
        
        # Специфичные для типа метрики
        drawdown_from_peak = None
        rally_from_trough = None
        
        if zone_type == 'bull':
            # Просадка от пика (обычно отрицательная)
            drawdown_from_peak = np.random.uniform(-0.3, -0.01)
        else:
            # Отскок от минимума (обычно положительный)
            rally_from_trough = np.random.uniform(0.01, 0.25)
        
        # Генерируем ценовые данные
        # Используем базовую цену с небольшой вариацией
        base_price = 2000.0
        start_price = base_price + np.random.normal(0, 50)
        end_price = start_price * (1 + price_return)
        
        zone_features = {
            'type': zone_type,
            'duration': duration,
            'price_return': price_return,
            'hist_slope': hist_slope,
            'macd_amplitude': macd_amplitude,
            'atr': atr,
            'price_return_atr': price_return_atr,
            'correlation_price_hist': correlation_price_hist,
            'drawdown_from_peak': drawdown_from_peak,
            'rally_from_trough': rally_from_trough,
            'start_price': start_price,
            'end_price': end_price
        }
        
        zones_features.append(zone_features)
    
    return zones_features


class TestHypothesisTestResult:
    """Тесты класса HypothesisTestResult."""
    
    def test_hypothesis_test_result_creation(self):
        """Тест создания результата тестирования гипотезы."""
        result = HypothesisTestResult(
            hypothesis="Test hypothesis",
            test_type="t-test",
            statistic=2.5,
            p_value=0.013,
            significant=True,
            alpha=0.05,
            effect_size=0.4,
            sample_size=100
        )
        
        assert result.hypothesis == "Test hypothesis"
        assert result.test_type == "t-test"
        assert result.statistic == 2.5
        assert result.p_value == 0.013
        assert result.significant is True
        assert result.alpha == 0.05
        assert result.effect_size == 0.4
        assert result.sample_size == 100
        assert result.metadata == {}
    
    def test_hypothesis_test_result_to_dict(self):
        """Тест конвертации результата в словарь."""
        result = HypothesisTestResult(
            hypothesis="Test hypothesis",
            test_type="correlation",
            statistic=0.65,
            p_value=0.001,
            significant=True,
            confidence_interval=(0.3, 0.8),
            metadata={'sample_mean': 10.5}
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['hypothesis'] == "Test hypothesis"
        assert result_dict['test_type'] == "correlation"
        assert result_dict['statistic'] == 0.65
        assert result_dict['p_value'] == 0.001
        assert result_dict['significant'] is True
        assert result_dict['confidence_interval'] == (0.3, 0.8)
        assert result_dict['metadata'] == {'sample_mean': 10.5}


class TestHypothesisTestSuite:
    """Тесты класса HypothesisTestSuite."""
    
    @pytest.fixture
    def test_suite(self):
        """Создание тестового набора."""
        return HypothesisTestSuite(alpha=0.05)
    
    @pytest.fixture
    def test_zones(self):
        """Создание тестовых зон."""
        return create_test_zones_features(50)
    
    def test_suite_initialization(self, test_suite):
        """Тест инициализации набора тестов."""
        assert test_suite.alpha == 0.05
        assert test_suite.logger is not None
    
    def test_zone_duration_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы о длительности зон."""
        result = test_suite.test_zone_duration_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Zone duration affects price returns"
        assert result.test_type == "Independent t-test"
        assert isinstance(result.statistic, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.significant, (bool, np.bool_))
        assert result.sample_size > 0
        
        # Проверяем метаданные
        assert 'long_zones_count' in result.metadata
        assert 'short_zones_count' in result.metadata
        assert 'long_zones_mean_return' in result.metadata
        assert 'short_zones_mean_return' in result.metadata
    
    def test_histogram_slope_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы о наклоне гистограммы."""
        result = test_suite.test_histogram_slope_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Histogram slope correlates with zone duration"
        assert result.test_type == "Pearson correlation test"
        assert isinstance(result.statistic, float)
        assert isinstance(result.p_value, float)
        assert result.confidence_interval is not None
        assert len(result.confidence_interval) == 2
        
        # Проверяем метаданные
        assert 'correlation' in result.metadata
        assert 'sample_size' in result.metadata
        assert result.metadata['sample_size'] == result.sample_size
    
    def test_bull_bear_asymmetry_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы об асимметрии бычьих и медвежьих зон."""
        result = test_suite.test_bull_bear_asymmetry_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Bullish and bearish zones are asymmetric"
        assert result.test_type == "Multiple t-tests with Bonferroni correction"
        
        # Проверяем метаданные
        assert 'duration_test' in result.metadata
        assert 'return_test' in result.metadata
        assert 'bull_zones_count' in result.metadata
        assert 'bear_zones_count' in result.metadata
        
        duration_test = result.metadata['duration_test']
        assert 't_statistic' in duration_test
        assert 'p_value' in duration_test
        assert 'significant' in duration_test
    
    def test_sequence_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы о последовательностях."""
        result = test_suite.test_sequence_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Zone sequences follow non-random patterns"
        assert result.test_type == "Chi-square and runs tests"
        
        # Проверяем метаданные
        assert 'transitions' in result.metadata
        assert 'total_transitions' in result.metadata
        assert 'chi2_statistic' in result.metadata
        assert 'runs_statistic' in result.metadata
        assert 'sequence_length' in result.metadata
    
    def test_volatility_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы о волатильности."""
        result = test_suite.test_volatility_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Volatility affects zone characteristics"
        assert result.test_type == "Multiple correlation tests with Holm-Bonferroni correction"
        
        # Проверяем метаданные
        assert 'volatility_proxy' in result.metadata
        assert 'correlations' in result.metadata
        assert 'significant_correlations' in result.metadata
        assert 'volatility_mean' in result.metadata
    
    def test_correlation_drawdown_hypothesis(self, test_suite, test_zones):
        """Тест гипотезы о корреляции и просадке."""
        result = test_suite.test_correlation_drawdown_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "High correlation between price and MACD reduces drawdown"
        assert result.test_type == "Independent t-test"
        assert isinstance(result.statistic, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.significant, (bool, np.bool_))
        assert result.sample_size > 0
        
        # Проверяем метаданные
        assert 'high_corr_count' in result.metadata
        assert 'low_corr_count' in result.metadata
        assert 'high_corr_mean_drawdown' in result.metadata
        assert 'low_corr_mean_drawdown' in result.metadata
        assert 'overall_correlation' in result.metadata
        assert 'overall_correlation_p' in result.metadata
        assert 'bull_zones_used' in result.metadata
        assert 'bear_zones_used' in result.metadata
    
    def test_zone_duration_stationarity(self, test_suite, test_zones):
        """Тест стационарности длительности зон (ADF)."""
        result = test_suite.test_zone_duration_stationarity(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Zone duration time series is stationary"
        assert result.test_type == "Augmented Dickey-Fuller (ADF) test"
        assert isinstance(result.statistic, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.significant, (bool, np.bool_))
        assert result.sample_size == len(test_zones)
        
        # Проверяем метаданные
        assert 'adf_statistic' in result.metadata
        assert 'adf_p_value' in result.metadata
        assert 'adf_usedlag' in result.metadata
        assert 'adf_nobs' in result.metadata
        assert 'critical_values' in result.metadata
        assert 'is_stationary' in result.metadata
        assert 'trend_correlation' in result.metadata
        assert 'trend_p_value' in result.metadata
        assert 'has_trend' in result.metadata
        assert 'mean_duration' in result.metadata
        assert 'interpretation' in result.metadata
        
        # Проверяем критические значения
        critical_values = result.metadata['critical_values']
        assert '1%' in critical_values
        assert '5%' in critical_values
        assert '10%' in critical_values
    
    def test_support_resistance_hypothesis_with_auto_levels(self, test_suite, test_zones):
        """Тест гипотезы поддержки/сопротивления с автоматической идентификацией уровней."""
        result = test_suite.test_support_resistance_hypothesis(test_zones)
        
        assert isinstance(result, HypothesisTestResult)
        assert result.hypothesis == "Zones starting near support/resistance levels have different duration"
        assert result.test_type in ["Independent t-test", "Mann-Whitney U test"]
        assert isinstance(result.statistic, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.significant, (bool, np.bool_))
        assert result.sample_size > 0
        
        # Проверяем метаданные
        assert 'near_level_count' in result.metadata
        assert 'far_from_level_count' in result.metadata
        assert 'near_level_mean_duration' in result.metadata
        assert 'far_from_level_mean_duration' in result.metadata
        assert 'price_levels_count' in result.metadata
        assert 'price_levels' in result.metadata
        assert 'tolerance_pct' in result.metadata
        assert 'test_used' in result.metadata
        assert 'is_parametric' in result.metadata
        assert 'duration_difference' in result.metadata
        assert 'duration_difference_pct' in result.metadata
        
        # Проверяем, что уровни были идентифицированы
        assert len(result.metadata['price_levels']) > 0
        assert result.metadata['near_level_count'] > 0
        assert result.metadata['far_from_level_count'] > 0
    
    def test_support_resistance_hypothesis_with_manual_levels(self, test_suite, test_zones):
        """Тест гипотезы поддержки/сопротивления с явно заданными уровнями."""
        # Задаем уровни вручную
        price_levels = [1950.0, 2000.0, 2050.0]
        
        result = test_suite.test_support_resistance_hypothesis(
            test_zones,
            price_levels=price_levels,
            tolerance_pct=1.0
        )
        
        assert isinstance(result, HypothesisTestResult)
        assert result.metadata['price_levels_count'] == len(price_levels)
        assert result.metadata['price_levels'] == price_levels
        assert result.metadata['tolerance_pct'] == 1.0
    
    def test_identify_price_levels(self, test_suite, test_zones):
        """Тест функции идентификации уровней поддержки/сопротивления."""
        df_features = pd.DataFrame(test_zones)
        
        levels = test_suite._identify_price_levels(df_features)
        
        # Проверяем, что уровни идентифицированы
        assert isinstance(levels, list)
        assert len(levels) > 0
        
        # Проверяем, что уровни отсортированы и уникальны
        sorted_levels = sorted(levels)
        assert levels == sorted_levels or len(set(levels)) == len(levels)
    
    def test_is_near_level(self, test_suite):
        """Тест функции проверки близости к уровню."""
        levels = [1000.0, 2000.0, 3000.0]
        
        # Цена близка к уровню (в пределах 0.5%)
        assert test_suite._is_near_level(2005.0, levels, 0.5) == True
        assert test_suite._is_near_level(1995.0, levels, 0.5) == True
        
        # Цена далеко от уровней
        assert test_suite._is_near_level(2500.0, levels, 0.5) == False
        
        # Граничный случай
        assert test_suite._is_near_level(2010.0, levels, 0.5) == True  # 0.5% от 2000 = 10
        assert test_suite._is_near_level(2011.0, levels, 0.5) == False
    
    def test_run_all_tests(self, test_suite, test_zones):
        """Тест выполнения всех тестов."""
        analysis_result = test_suite.run_all_tests(test_zones)
        
        assert analysis_result.analysis_type == 'hypothesis_testing'
        assert 'tests' in analysis_result.results
        assert 'summary' in analysis_result.results
        
        tests = analysis_result.results['tests']
        summary = analysis_result.results['summary']
        
        # Проверяем, что все тесты выполнены (обновлено для Phase 3.7)
        expected_tests = ['zone_duration', 'histogram_slope', 'bull_bear_asymmetry', 
                         'sequence_patterns', 'volatility_effects',
                         'correlation_drawdown', 'duration_stationarity']
        
        for test_name in expected_tests:
            assert test_name in tests
        
        # Проверяем сводку
        assert 'total_tests' in summary
        assert 'significant_tests' in summary
        assert 'significance_rate' in summary
        assert summary['total_tests'] == len(expected_tests)


class TestErrorHandling:
    """Тесты обработки ошибок."""
    
    @pytest.fixture
    def test_suite(self):
        """Создание тестового набора."""
        return HypothesisTestSuite(alpha=0.05)
    
    def test_empty_zones_features(self, test_suite):
        """Тест с пустым списком зон."""
        with pytest.raises(StatisticalAnalysisError):
            test_suite.run_all_tests([])
    
    def test_missing_required_columns(self, test_suite):
        """Тест с отсутствующими обязательными колонками."""
        incomplete_zones = [
            {'type': 'bull'},  # Отсутствуют duration и price_return
            {'type': 'bear'}
        ]
        
        with pytest.raises(StatisticalAnalysisError):
            test_suite.test_zone_duration_hypothesis(incomplete_zones)
    
    def test_insufficient_data(self, test_suite):
        """Тест с недостаточным количеством данных."""
        minimal_zones = [
            {'type': 'bull', 'duration': 10, 'price_return': 0.05, 'hist_slope': 0.1}
        ]
        
        with pytest.raises(StatisticalAnalysisError):
            test_suite.test_bull_bear_asymmetry_hypothesis(minimal_zones)
    
    def test_single_zone_type(self, test_suite):
        """Тест с зонами только одного типа."""
        single_type_zones = [
            {'type': 'bull', 'duration': 10, 'price_return': 0.05},
            {'type': 'bull', 'duration': 15, 'price_return': 0.03}
        ]
        
        with pytest.raises(StatisticalAnalysisError):
            test_suite.test_bull_bear_asymmetry_hypothesis(single_type_zones)


class TestConvenienceFunctions:
    """Тесты удобных функций."""
    
    @pytest.fixture
    def test_zones(self):
        """Создание тестовых зон."""
        return create_test_zones_features(30)
    
    def test_run_all_hypothesis_tests_function(self, test_zones):
        """Тест функции run_all_hypothesis_tests."""
        results = run_all_hypothesis_tests(test_zones, alpha=0.05)
        
        assert isinstance(results, dict)
        assert 'tests' in results
        assert 'summary' in results
        
        # Проверяем совместимость с оригинальным API
        assert 'summary' in results
        summary = results['summary']
        assert 'total_tests' in summary
        assert 'significant_tests' in summary
    
    def test_imported_run_all_function(self, test_zones):
        """Тест импортированной функции из модуля statistical."""
        results = imported_run_all(test_zones, alpha=0.01)
        
        assert isinstance(results, dict)
        assert 'tests' in results
        assert 'summary' in results
    
    def test_test_single_hypothesis_function(self, test_zones):
        """Тест функции test_single_hypothesis."""
        # Тест каждого типа гипотезы (обновлено для Phase 3.7 + H5)
        test_types = ['duration', 'slope', 'asymmetry', 'sequence', 'volatility',
                     'correlation_drawdown', 'stationarity']
        
        for test_type in test_types:
            result = run_single_hypothesis_test(test_zones, test_type, alpha=0.05)
            assert isinstance(result, HypothesisTestResult)
            assert result.alpha == 0.05
        
        # Тест H5 (support_resistance) отдельно с параметрами
        result_h5 = run_single_hypothesis_test(
            test_zones, 
            'support_resistance',
            alpha=0.05,
            price_levels=None,  # Auto-detect
            tolerance_pct=0.5
        )
        assert isinstance(result_h5, HypothesisTestResult)
        assert result_h5.alpha == 0.05
    
    def test_unknown_test_type(self, test_zones):
        """Тест с неизвестным типом теста."""
        with pytest.raises(ValueError, match="Unknown test type"):
            run_single_hypothesis_test(test_zones, 'unknown_test', alpha=0.05)


class TestCompatibilityWithOriginal:
    """Тесты совместимости с оригинальным API."""
    
    @pytest.fixture
    def test_zones(self):
        """Создание тестовых зон.""" 
        return create_test_zones_features(40)
    
    def test_api_compatibility(self, test_zones):
        """Тест совместимости API с оригинальной версией."""
        # Оригинальный вызов
        results = run_all_hypothesis_tests(test_zones)
        
        # Проверяем структуру ответа как в оригинале
        assert isinstance(results, dict)
        assert 'summary' in results
        
        summary = results['summary']
        assert 'total_tests' in summary
        assert 'significant_tests' in summary
        assert 'significance_rate' in summary
        
        # Проверяем типы данных
        assert isinstance(summary['total_tests'], int)
        assert isinstance(summary['significant_tests'], int)
        assert isinstance(summary['significance_rate'], (int, float))
    
    def test_result_structure_compatibility(self, test_zones):
        """Тест совместимости структуры результатов."""
        results = run_all_hypothesis_tests(test_zones)
        
        # Проверяем наличие ключевых тестов (как в оригинале)
        expected_tests = [
            'zone_duration',
            'histogram_slope', 
            'bull_bear_asymmetry',
            'sequence_patterns',
            'volatility_effects'
        ]
        
        for test_name in expected_tests:
            assert test_name in results['tests']
            test_result = results['tests'][test_name]
            
            # Базовая структура результата теста
            if 'error' not in test_result:
                assert 'hypothesis' in test_result
                assert 'test_type' in test_result
                assert 'p_value' in test_result
                assert 'significant' in test_result


class TestIntegrationWithMACDAnalyzer:
    """Интеграционные тесты с MACDAnalyzer."""
    
    def test_hypothesis_tests_with_macd_zones(self):
        """Тест гипотез с реальными данными из MACD анализатора."""
        # Создаем синтетические MACD зоны
        macd_zones = []
        
        for i in range(20):
            zone_type = 'bull' if i % 2 == 0 else 'bear'
            
            zone_features = {
                'type': zone_type,
                'duration': np.random.exponential(10) + 2,
                'price_return': np.random.normal(0, 0.1),
                'hist_slope': np.random.normal(0, 0.05),
                'macd_amplitude': np.random.exponential(1),
                'atr': np.random.exponential(0.5) + 0.1
            }
            
            # Добавляем нормализованную доходность
            zone_features['price_return_atr'] = zone_features['price_return'] / zone_features['atr']
            
            macd_zones.append(zone_features)
        
        # Выполняем тесты
        results = run_all_hypothesis_tests(macd_zones)
        
        # Проверяем, что тесты выполняются без ошибок
        assert isinstance(results, dict)
        assert 'summary' in results
        assert results['summary']['total_tests'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
