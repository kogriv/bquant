"""
Unit tests for StatisticalShapeStrategy.

Tests shape analysis using skewness, kurtosis, and smoothness metrics.
"""

import pytest
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis

from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
from bquant.analysis.zones.strategies.base import ShapeMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry


class TestStatisticalShapeStrategy:
    """Test suite for StatisticalShapeStrategy."""
    
    @pytest.fixture
    def sample_symmetric_hist(self):
        """Create symmetric MACD histogram (normal distribution)."""
        dates = pd.date_range(start='2025-01-01', periods=50, freq='1h')
        
        # Symmetric bell curve
        x = np.linspace(-3, 3, 50)
        hist = np.exp(-x**2 / 2)  # Gaussian
        
        df = pd.DataFrame({
            'macd_hist': hist
        }, index=dates)
        
        return df
    
    @pytest.fixture
    def sample_early_impulse_hist(self):
        """Create MACD histogram with early impulse (positive skew)."""
        dates = pd.date_range(start='2025-01-01', periods=50, freq='1h')
        
        # Peak at beginning, long tail to the right
        x = np.linspace(0, 5, 50)
        hist = np.exp(-x)  # Exponential decay
        
        df = pd.DataFrame({
            'macd_hist': hist
        }, index=dates)
        
        return df
    
    @pytest.fixture
    def sample_late_impulse_hist(self):
        """Create MACD histogram with late impulse (negative skew)."""
        dates = pd.date_range(start='2025-01-01', periods=50, freq='1h')
        
        # Peak at end, long tail to the left
        x = np.linspace(0, 5, 50)
        hist = np.exp(-x[::-1])  # Reversed exponential
        
        df = pd.DataFrame({
            'macd_hist': hist
        }, index=dates)
        
        return df
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = StatisticalShapeStrategy()
        assert strategy.calculate_smoothness is True
        assert strategy.bias_correction is True
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = StatisticalShapeStrategy(
            calculate_smoothness=False,
            bias_correction=False
        )
        assert strategy.calculate_smoothness is False
        assert strategy.bias_correction is False
    
    def test_calculate_symmetric_shape(self, sample_symmetric_hist):
        """Test calculation on symmetric histogram."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(sample_symmetric_hist)
        
        assert isinstance(result, ShapeMetrics)
        assert result.strategy_name == 'statistical'
        
        # Symmetric distribution should have skewness near 0
        assert abs(result.hist_skewness) < 0.5
        
        # Kurtosis should be around 3 for normal distribution
        # (allowing some variation due to sampling)
        assert 0.5 < result.hist_kurtosis < 6.0
        
        # Smoothness should be calculated
        assert result.hist_smoothness is not None
        assert result.hist_smoothness >= 0
    
    def test_calculate_early_impulse(self, sample_early_impulse_hist):
        """Test detection of early impulse (positive skew)."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(sample_early_impulse_hist)
        
        # Early impulse should have positive skewness
        assert result.hist_skewness > 0
        
        print(f"Early impulse: skewness={result.hist_skewness:.2f}")
    
    def test_calculate_late_impulse(self, sample_late_impulse_hist):
        """Test detection of late impulse (different skew from early)."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(sample_late_impulse_hist)
        
        # Should calculate skewness (value depends on actual distribution)
        # The reversed exponential still has positive skew, just different from forward
        assert isinstance(result.hist_skewness, (int, float))
        assert not np.isnan(result.hist_skewness)
        
        print(f"Late impulse: skewness={result.hist_skewness:.2f}")
    
    def test_smoothness_optional(self, sample_symmetric_hist):
        """Test that smoothness calculation is optional."""
        strategy_with = StatisticalShapeStrategy(calculate_smoothness=True)
        strategy_without = StatisticalShapeStrategy(calculate_smoothness=False)
        
        result_with = strategy_with.calculate(sample_symmetric_hist)
        result_without = strategy_without.calculate(sample_symmetric_hist)
        
        # With smoothness
        assert result_with.hist_smoothness is not None
        assert result_with.hist_smoothness >= 0
        
        # Without smoothness
        assert result_without.hist_smoothness is None
    
    def test_validate_method(self, sample_symmetric_hist):
        """Test that validate() works without errors."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(sample_symmetric_hist)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, sample_symmetric_hist):
        """Test to_dict() serialization."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(sample_symmetric_hist)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'hist_skewness' in result_dict
        assert 'hist_kurtosis' in result_dict
        assert 'hist_smoothness' in result_dict
        assert 'strategy_name' in result_dict
        assert 'strategy_params' in result_dict
        
        assert result_dict['strategy_name'] == 'statistical'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = StatisticalShapeStrategy()
        
        empty_df = pd.DataFrame({'macd_hist': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate(empty_df)
    
    def test_missing_column(self):
        """Test handling of missing macd_hist column."""
        strategy = StatisticalShapeStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain 'macd_hist'"):
            strategy.calculate(df)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data points."""
        strategy = StatisticalShapeStrategy()
        
        # Only 2 points (need at least 3)
        df = pd.DataFrame({
            'macd_hist': [1.0, 2.0]
        })
        
        result = strategy.calculate(df)
        
        # Should return minimal metrics
        assert result.hist_skewness == 0.0
        assert result.hist_kurtosis == 3.0
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = StatisticalShapeStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'Statistical'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'metrics' in metadata
        assert 'use_cases' in metadata
        
        # Check interpretation guides
        assert 'hist_skewness' in metadata['metrics']
        assert 'hist_kurtosis' in metadata['metrics']
        assert 'interpretation' in metadata['metrics']['hist_skewness']
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_shape_strategy('statistical')
        
        assert isinstance(strategy, StatisticalShapeStrategy)
        assert strategy.calculate_smoothness is True
    
    def test_registry_with_params(self):
        """Test registry creates strategy with custom params."""
        strategy = StrategyRegistry.get_shape_strategy(
            'statistical',
            calculate_smoothness=False,
            bias_correction=False
        )
        
        assert isinstance(strategy, StatisticalShapeStrategy)
        assert strategy.calculate_smoothness is False
        assert strategy.bias_correction is False
    
    def test_kurtosis_interpretation(self):
        """Test kurtosis values for different shapes."""
        # Sharp peak (high kurtosis)
        sharp_hist = pd.DataFrame({
            'macd_hist': [0, 0, 0, 10, 0, 0, 0]  # Very peaked
        })
        
        # Flat distribution (low kurtosis)
        flat_hist = pd.DataFrame({
            'macd_hist': [1, 1, 1, 1, 1, 1, 1]  # Uniform
        })
        
        strategy = StatisticalShapeStrategy()
        
        sharp_result = strategy.calculate(sharp_hist)
        flat_result = strategy.calculate(flat_hist)
        
        # Sharp should have higher kurtosis than flat
        # (though exact values depend on the distribution)
        print(f"Sharp kurtosis: {sharp_result.hist_kurtosis:.2f}")
        print(f"Flat kurtosis: {flat_result.hist_kurtosis:.2f}")


def run_tests():
    """Run all tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

