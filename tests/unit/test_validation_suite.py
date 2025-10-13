"""
Unit tests for ValidationSuite.

Tests validation methods including out-of-sample, walk-forward,
sensitivity analysis, and Monte Carlo simulation.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from bquant.analysis.validation import (
    ValidationResult,
    ValidationSuite
)
from bquant.core.exceptions import AnalysisError


def create_test_data(n_bars: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Create test OHLC data for validation testing.
    
    Args:
        n_bars: Number of bars
        seed: Random seed
    
    Returns:
        DataFrame with OHLC columns
    """
    np.random.seed(seed)
    
    # Generate price series with some structure
    dates = pd.date_range('2020-01-01', periods=n_bars, freq='1h')
    
    close = [2000.0]
    for _ in range(n_bars - 1):
        change = np.random.normal(0, 10)
        close.append(close[-1] + change)
    
    close = np.array(close)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': close + np.random.normal(0, 5, n_bars),
        'high': close + abs(np.random.normal(5, 3, n_bars)),
        'low': close - abs(np.random.normal(5, 3, n_bars)),
        'close': close,
        'volume': np.random.exponential(1000, n_bars)
    })
    
    data.set_index('timestamp', inplace=True)
    
    return data


def simple_analyze_func(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Simple analysis function for testing validation.
    
    Args:
        data: Input data
    
    Returns:
        Dictionary with analysis metrics
    """
    return {
        'total_zones': len(data) // 10,  # Simulate zones
        'mean_price': data['close'].mean(),
        'price_std': data['close'].std(),
        'price_range': data['close'].max() - data['close'].min()
    }


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test creation of ValidationResult."""
        result = ValidationResult(
            validation_type='out_of_sample',
            success=True,
            train_metrics={'metric': 100},
            test_metrics={'metric': 95},
            degradation_pct=5.0,
            iterations=1
        )
        
        assert result.validation_type == 'out_of_sample'
        assert result.success is True
        assert result.degradation_pct == 5.0
    
    def test_validation_result_to_dict(self):
        """Test conversion to dictionary."""
        result = ValidationResult(
            validation_type='walk_forward',
            success=False,
            train_metrics={'a': 1},
            test_metrics={'a': 2},
            degradation_pct=50.0,
            iterations=10
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['validation_type'] == 'walk_forward'
        assert result_dict['iterations'] == 10


class TestValidationSuite:
    """Tests for ValidationSuite methods."""
    
    @pytest.fixture
    def suite(self):
        """Create validation suite."""
        return ValidationSuite(degradation_threshold=0.2)
    
    @pytest.fixture
    def test_data(self):
        """Create test data."""
        return create_test_data(1000)
    
    def test_suite_initialization(self, suite):
        """Test suite initialization."""
        assert suite.degradation_threshold == 0.2
        assert suite.logger is not None
    
    def test_out_of_sample_basic(self, suite, test_data):
        """Test basic out-of-sample validation."""
        result = suite.out_of_sample_test(
            analyze_func=simple_analyze_func,
            data=test_data,
            train_ratio=0.7
        )
        
        assert isinstance(result, ValidationResult)
        assert result.validation_type == 'out_of_sample'
        assert isinstance(result.success, bool)
        assert result.train_metrics is not None
        assert result.test_metrics is not None
        assert result.degradation_pct is not None
        assert result.iterations == 1
    
    def test_out_of_sample_split_sizes(self, suite, test_data):
        """Test train/test split sizes."""
        result = suite.out_of_sample_test(
            simple_analyze_func,
            test_data,
            train_ratio=0.7
        )
        
        assert result.metadata['train_size'] == 700
        assert result.metadata['test_size'] == 300
        assert result.metadata['split_index'] == 700
    
    def test_out_of_sample_different_ratios(self, suite, test_data):
        """Test different train ratios."""
        ratios = [0.5, 0.7, 0.8]
        
        for ratio in ratios:
            result = suite.out_of_sample_test(
                simple_analyze_func,
                test_data,
                train_ratio=ratio
            )
            
            expected_train = int(len(test_data) * ratio)
            assert result.metadata['train_size'] == expected_train
    
    def test_walk_forward_basic(self, suite, test_data):
        """Test basic walk-forward validation."""
        result = suite.walk_forward_test(
            analyze_func=simple_analyze_func,
            data=test_data,
            train_window=500,
            test_window=100,
            step_size=100
        )
        
        assert isinstance(result, ValidationResult)
        assert result.validation_type == 'walk_forward'
        assert result.iterations > 0
        assert 'iterations_count' in result.metadata
        assert result.metadata['iterations_count'] == result.iterations
    
    def test_walk_forward_iterations(self, suite, test_data):
        """Test number of walk-forward iterations."""
        result = suite.walk_forward_test(
            simple_analyze_func,
            test_data,
            train_window=500,
            test_window=100,
            step_size=100
        )
        
        # Calculate expected iterations
        # Data length: 1000
        # Window: 500 + 100 = 600
        # Can fit: (1000 - 600) / 100 + 1 = 5 iterations
        expected_iterations = (len(test_data) - 500 - 100) // 100 + 1
        assert result.iterations == expected_iterations
    
    def test_walk_forward_metadata(self, suite, test_data):
        """Test walk-forward metadata."""
        result = suite.walk_forward_test(
            simple_analyze_func,
            test_data,
            train_window=500,
            test_window=100,
            step_size=100
        )
        
        assert 'train_window' in result.metadata
        assert 'test_window' in result.metadata
        assert 'step_size' in result.metadata
        assert 'iterations_detail' in result.metadata
        assert len(result.metadata['iterations_detail']) == result.iterations
    
    def test_sensitivity_analysis_basic(self, suite, test_data):
        """Test basic sensitivity analysis."""
        def parameterized_analyze(data, param_a=10, param_b=5):
            """Analysis function with parameters."""
            return {
                'total_zones': len(data) // param_a,
                'param_a': param_a,
                'param_b': param_b
            }
        
        param_ranges = {
            'param_a': [8, 10, 12],
            'param_b': [3, 5, 7]
        }
        
        result = suite.sensitivity_analysis(
            analyze_func=parameterized_analyze,
            data=test_data,
            param_ranges=param_ranges
        )
        
        assert isinstance(result, ValidationResult)
        assert result.validation_type == 'sensitivity_analysis'
        assert result.iterations == 9  # 3 x 3 combinations
    
    def test_sensitivity_analysis_finds_best(self, suite, test_data):
        """Test that sensitivity analysis identifies best parameters."""
        def parameterized_analyze(data, multiplier=1.0):
            return {'metric': len(data) * multiplier}
        
        param_ranges = {'multiplier': [0.5, 1.0, 1.5, 2.0]}
        
        result = suite.sensitivity_analysis(
            parameterized_analyze,
            test_data,
            param_ranges,
            metric_key='metric'
        )
        
        # Best should be multiplier=2.0
        assert result.metadata['best_params']['multiplier'] == 2.0
        assert result.metadata['worst_params']['multiplier'] == 0.5
    
    def test_sensitivity_stability_score(self, suite, test_data):
        """Test stability score calculation."""
        def stable_analyze(data, param=1):
            # Always returns same metric regardless of param
            return {'metric': 100}
        
        param_ranges = {'param': [1, 2, 3, 4, 5]}
        
        result = suite.sensitivity_analysis(
            stable_analyze,
            test_data,
            param_ranges,
            metric_key='metric'
        )
        
        # Perfect stability (no variation)
        assert result.metadata['stability_score'] > 0.99
        assert result.success == True or result.success is True  # Handle numpy boolean
    
    def test_monte_carlo_basic(self, suite, test_data):
        """Test basic Monte Carlo simulation."""
        result = suite.monte_carlo_test(
            analyze_func=simple_analyze_func,
            data=test_data,
            n_simulations=50,  # Reduced for speed
            metric_key='total_zones'
        )
        
        assert isinstance(result, ValidationResult)
        assert result.validation_type == 'monte_carlo'
        assert result.iterations > 0
        assert result.iterations <= 50
    
    def test_monte_carlo_shuffle_methods(self, suite, test_data):
        """Test different shuffle methods."""
        shuffle_methods = ['returns', 'prices', 'full']
        
        for method in shuffle_methods:
            result = suite.monte_carlo_test(
                simple_analyze_func,
                test_data,
                n_simulations=20,
                shuffle_method=method
            )
            
            assert result.metadata['shuffle_method'] == method
            assert result.iterations > 0
    
    def test_monte_carlo_real_vs_random(self, suite, test_data):
        """Test that real vs random comparison is meaningful."""
        result = suite.monte_carlo_test(
            simple_analyze_func,
            test_data,
            n_simulations=30
        )
        
        assert 'real_metric_value' in result.metadata
        assert 'sim_mean' in result.metadata
        assert 'sim_std' in result.metadata
        assert 'z_score' in result.metadata
        assert 'p95_threshold' in result.metadata
    
    def test_insufficient_data_errors(self, suite):
        """Test error handling for insufficient data."""
        tiny_data = create_test_data(5)
        
        with pytest.raises(AnalysisError, match="Insufficient data"):
            suite.out_of_sample_test(simple_analyze_func, tiny_data)
    
    def test_invalid_train_ratio(self, suite, test_data):
        """Test error for invalid train ratio."""
        with pytest.raises(AnalysisError, match="train_ratio must be between"):
            suite.out_of_sample_test(simple_analyze_func, test_data, train_ratio=1.5)
    
    def test_insufficient_simulations(self, suite, test_data):
        """Test error for too few simulations."""
        with pytest.raises(AnalysisError, match="at least 10 simulations"):
            suite.monte_carlo_test(simple_analyze_func, test_data, n_simulations=5)


class TestSyntheticDataGeneration:
    """Tests for synthetic data generation methods."""
    
    @pytest.fixture
    def suite(self):
        return ValidationSuite()
    
    @pytest.fixture
    def test_data(self):
        return create_test_data(100)
    
    def test_generate_synthetic_returns_method(self, suite, test_data):
        """Test synthetic data generation with returns method."""
        synthetic = suite._generate_synthetic_data(test_data, method='returns', seed=42)
        
        assert len(synthetic) == len(test_data)
        assert 'close' in synthetic.columns
        # Prices should be different
        assert not np.array_equal(synthetic['close'].values, test_data['close'].values)
    
    def test_generate_synthetic_prices_method(self, suite, test_data):
        """Test synthetic data generation with prices method."""
        synthetic = suite._generate_synthetic_data(test_data, method='prices', seed=42)
        
        assert len(synthetic) == len(test_data)
        # Should be permutation of original prices
        assert set(synthetic['close'].values) == set(test_data['close'].values)
    
    def test_generate_synthetic_full_method(self, suite, test_data):
        """Test synthetic data generation with full random walk."""
        synthetic = suite._generate_synthetic_data(test_data, method='full', seed=42)
        
        assert len(synthetic) == len(test_data)
        # Should start near original price
        assert abs(synthetic['close'].iloc[0] - test_data['close'].iloc[0]) < 1e-5
        # But follow different path
        assert not np.array_equal(synthetic['close'].values[10:], test_data['close'].values[10:])
    
    def test_synthetic_data_reproducibility(self, suite, test_data):
        """Test that synthetic data is reproducible with same seed."""
        synthetic1 = suite._generate_synthetic_data(test_data, method='returns', seed=123)
        synthetic2 = suite._generate_synthetic_data(test_data, method='returns', seed=123)
        
        np.testing.assert_array_almost_equal(
            synthetic1['close'].values,
            synthetic2['close'].values,
            decimal=10
        )


class TestValidationIntegration:
    """Integration tests for validation suite."""
    
    @pytest.fixture
    def suite(self):
        return ValidationSuite(degradation_threshold=0.3)
    
    @pytest.fixture
    def large_data(self):
        return create_test_data(2000, seed=456)
    
    def test_all_validation_methods(self, suite, large_data):
        """Test that all validation methods can run successfully."""
        # Out-of-sample
        oos_result = suite.out_of_sample_test(simple_analyze_func, large_data)
        assert isinstance(oos_result, ValidationResult)
        
        # Walk-forward
        wf_result = suite.walk_forward_test(
            simple_analyze_func,
            large_data,
            train_window=800,
            test_window=200,
            step_size=200
        )
        assert isinstance(wf_result, ValidationResult)
        
        # Sensitivity
        def param_func(data, window=10):
            return {'metric': len(data) / window}
        
        sens_result = suite.sensitivity_analysis(
            param_func,
            large_data,
            {'window': [8, 10, 12]}
        )
        assert isinstance(sens_result, ValidationResult)
        
        # Monte Carlo
        mc_result = suite.monte_carlo_test(
            simple_analyze_func,
            large_data.iloc[:500],  # Subset for speed
            n_simulations=20
        )
        assert isinstance(mc_result, ValidationResult)
        
        # All should have different validation types
        validation_types = {oos_result.validation_type, wf_result.validation_type,
                          sens_result.validation_type, mc_result.validation_type}
        assert len(validation_types) == 4
    
    def test_degradation_calculation(self, suite):
        """Test degradation percentage calculation."""
        # No degradation
        deg1 = suite._calculate_degradation(100, 100)
        assert deg1 == 0
        
        # 10% degradation
        deg2 = suite._calculate_degradation(100, 90)
        assert abs(deg2 - 10.0) < 0.01
        
        # Improvement (negative degradation)
        deg3 = suite._calculate_degradation(100, 110)
        assert deg3 < 0
    
    def test_extract_metrics_from_dict(self, suite):
        """Test metrics extraction from dictionary."""
        result_dict = {'metric_a': 10, 'metric_b': 20}
        metrics = suite._extract_metrics(result_dict)
        
        assert metrics == result_dict
    
    def test_extract_metrics_from_object(self, suite):
        """Test metrics extraction from object with to_dict."""
        class MockResult:
            def to_dict(self):
                return {'value': 42}
        
        metrics = suite._extract_metrics(MockResult())
        assert metrics == {'value': 42}


# Export
__all__ = [
    'create_test_data',
    'simple_analyze_func',
    'TestValidationResult',
    'TestValidationSuite',
    'TestSyntheticDataGeneration',
    'TestValidationIntegration'
]

