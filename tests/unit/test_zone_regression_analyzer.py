"""
Unit tests for ZoneRegressionAnalyzer.

Tests regression modeling for zone duration and price return prediction.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any

from bquant.analysis.statistical.regression import (
    RegressionResult,
    ZoneRegressionAnalyzer
)
from bquant.core.exceptions import StatisticalAnalysisError


def create_test_zones_for_regression(n_zones: int = 50, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Create test zone features for regression testing.
    
    Args:
        n_zones: Number of zones
        seed: Random seed
    
    Returns:
        List of zone feature dictionaries
    """
    np.random.seed(seed)
    
    zones = []
    
    for i in range(n_zones):
        # Generate correlated features
        macd_amplitude = np.random.exponential(2) + 0.5
        hist_amplitude = macd_amplitude * np.random.uniform(0.5, 1.5)
        
        # Duration correlated with amplitude
        duration = 10 + macd_amplitude * 5 + np.random.normal(0, 3)
        duration = max(2, int(duration))
        
        # Price return correlated with duration and correlation
        correlation_price_hist = np.random.uniform(-0.5, 0.9)
        price_return = (
            0.01 * duration + 
            0.02 * correlation_price_hist + 
            0.005 * macd_amplitude +
            np.random.normal(0, 0.02)
        )
        
        zone = {
            'zone_id': f'zone_{i}',
            'type': 'bull' if np.random.random() > 0.5 else 'bear',
            'duration': duration,
            'price_return': price_return,
            'macd_amplitude': macd_amplitude,
            'hist_amplitude': hist_amplitude,
            'correlation_price_hist': correlation_price_hist,
            'price_range_pct': np.random.exponential(0.05),
            'num_peaks': np.random.poisson(2),
            'num_troughs': np.random.poisson(2),
            'drawdown_from_peak': np.random.uniform(-0.3, -0.01) if np.random.random() > 0.5 else None,
            'hist_slope': np.random.exponential(0.1),
            'start_price': 2000 + np.random.normal(0, 50),
            'end_price': 2000 + np.random.normal(0, 50)
        }
        
        zones.append(zone)
    
    return zones


class TestRegressionResult:
    """Tests for RegressionResult dataclass."""
    
    def test_regression_result_creation(self):
        """Test creation of RegressionResult."""
        result = RegressionResult(
            target_variable='duration',
            r_squared=0.75,
            adjusted_r_squared=0.72,
            coefficients={'intercept': 5.0, 'macd_amplitude': 1.5},
            p_values={'intercept': 0.001, 'macd_amplitude': 0.01},
            predictions=np.array([10, 12, 15]),
            residuals=np.array([0.5, -0.3, 0.1]),
            n_observations=100,
            n_predictors=1
        )
        
        assert result.target_variable == 'duration'
        assert result.r_squared == 0.75
        assert result.adjusted_r_squared == 0.72
        assert len(result.coefficients) == 2
        assert len(result.predictions) == 3
    
    def test_regression_result_to_dict(self):
        """Test conversion to dictionary."""
        result = RegressionResult(
            target_variable='price_return',
            r_squared=0.60,
            adjusted_r_squared=0.58,
            coefficients={'intercept': 0.01},
            p_values={'intercept': 0.05},
            predictions=np.array([0.02, 0.03]),
            residuals=np.array([0.001, -0.002]),
            n_observations=50,
            n_predictors=1
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['target_variable'] == 'price_return'
        assert result_dict['r_squared'] == 0.60
        assert isinstance(result_dict['predictions'], list)
    
    def test_get_significant_predictors(self):
        """Test extraction of significant predictors."""
        result = RegressionResult(
            target_variable='duration',
            r_squared=0.70,
            adjusted_r_squared=0.68,
            coefficients={'intercept': 5.0, 'macd': 1.5, 'hist': 0.3},
            p_values={'intercept': 0.001, 'macd': 0.01, 'hist': 0.15},
            predictions=np.array([10]),
            residuals=np.array([0.5]),
            n_observations=100,
            n_predictors=2
        )
        
        significant = result.get_significant_predictors(alpha=0.05)
        
        assert len(significant) == 2  # intercept and macd
        assert 'macd' in significant
        assert 'hist' not in significant


class TestZoneRegressionAnalyzer:
    """Tests for ZoneRegressionAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ZoneRegressionAnalyzer(alpha=0.05)
    
    @pytest.fixture
    def test_zones(self):
        """Create test zones."""
        return create_test_zones_for_regression(50)
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.alpha == 0.05
        assert analyzer.logger is not None
    
    def test_predict_zone_duration_basic(self, analyzer, test_zones):
        """Test basic duration prediction."""
        result = analyzer.predict_zone_duration(test_zones)
        
        assert isinstance(result, RegressionResult)
        assert result.target_variable == 'duration'
        assert 0 <= result.r_squared <= 1
        assert result.adjusted_r_squared <= result.r_squared
        assert result.n_observations > 0
        assert result.n_predictors > 0
        assert len(result.predictions) == result.n_observations
        assert len(result.residuals) == result.n_observations
    
    def test_predict_zone_duration_custom_predictors(self, analyzer, test_zones):
        """Test duration prediction with custom predictors."""
        custom_predictors = ['macd_amplitude', 'hist_amplitude']
        
        result = analyzer.predict_zone_duration(test_zones, predictors=custom_predictors)
        
        assert isinstance(result, RegressionResult)
        # Check that only available predictors were used
        used_predictors = [k for k in result.coefficients.keys() if k != 'intercept']
        assert all(p in custom_predictors for p in used_predictors)
    
    def test_predict_zone_duration_coefficients(self, analyzer, test_zones):
        """Test that coefficients are populated."""
        result = analyzer.predict_zone_duration(test_zones)
        
        assert 'intercept' in result.coefficients
        assert 'intercept' in result.p_values
        assert len(result.coefficients) == len(result.p_values)
        assert result.n_predictors == len(result.coefficients) - 1  # Excluding intercept
    
    def test_predict_zone_duration_metadata(self, analyzer, test_zones):
        """Test metadata fields."""
        result = analyzer.predict_zone_duration(test_zones)
        
        assert 'available_predictors' in result.metadata
        assert 'f_statistic' in result.metadata
        assert 'f_pvalue' in result.metadata
        assert 'aic' in result.metadata
        assert 'bic' in result.metadata
        assert 'target_mean' in result.metadata
        assert 'target_std' in result.metadata
    
    def test_predict_price_return_basic(self, analyzer, test_zones):
        """Test basic price return prediction."""
        result = analyzer.predict_price_return(test_zones)
        
        assert isinstance(result, RegressionResult)
        assert result.target_variable == 'price_return'
        assert 0 <= result.r_squared <= 1
        assert result.adjusted_r_squared <= result.r_squared
        assert result.n_observations > 0
        assert result.n_predictors > 0
    
    def test_predict_price_return_custom_predictors(self, analyzer, test_zones):
        """Test price return prediction with custom predictors."""
        custom_predictors = ['duration', 'correlation_price_hist']
        
        result = analyzer.predict_price_return(test_zones, predictors=custom_predictors)
        
        assert isinstance(result, RegressionResult)
        used_predictors = [k for k in result.coefficients.keys() if k != 'intercept']
        assert all(p in custom_predictors for p in used_predictors)
    
    def test_model_quality_duration(self, analyzer, test_zones):
        """Test that duration model has reasonable fit."""
        result = analyzer.predict_zone_duration(test_zones)
        
        # With correlated data, should get decent R²
        assert result.r_squared > 0.1, "Model should explain >10% of variance"
        
        # Check that model is significant
        assert result.metadata['f_pvalue'] < 0.05, "Model should be significant"
    
    def test_model_quality_price_return(self, analyzer, test_zones):
        """Test that price return model has reasonable fit."""
        result = analyzer.predict_price_return(test_zones)
        
        # Price returns are noisier, but should still have some explanatory power
        assert result.r_squared >= 0, "R² should be non-negative"
        assert result.n_observations > result.n_predictors, "Should have more obs than predictors"
    
    def test_insufficient_data(self, analyzer):
        """Test with insufficient data."""
        # Only 3 zones with 6 predictors
        few_zones = create_test_zones_for_regression(3)
        
        with pytest.raises(StatisticalAnalysisError, match="Insufficient data"):
            analyzer.predict_zone_duration(few_zones)
    
    def test_missing_target_variable(self, analyzer, test_zones):
        """Test with missing target variable."""
        # Remove duration
        zones_no_duration = [{k: v for k, v in z.items() if k != 'duration'} 
                            for z in test_zones]
        
        with pytest.raises(StatisticalAnalysisError, match="Missing target variable"):
            analyzer.predict_zone_duration(zones_no_duration)
    
    def test_no_available_predictors(self, analyzer):
        """Test with no available predictors."""
        minimal_zones = [{'duration': 10, 'price_return': 0.05} for _ in range(20)]
        
        predictors = ['nonexistent_column', 'another_missing']
        
        with pytest.raises(StatisticalAnalysisError, match="No predictors available"):
            analyzer.predict_zone_duration(minimal_zones, predictors=predictors)
    
    def test_vif_calculation(self, analyzer, test_zones):
        """Test variance inflation factor calculation."""
        result = analyzer.predict_zone_duration(test_zones)
        
        if result.n_predictors >= 2:
            assert 'vif' in result.metadata
            assert isinstance(result.metadata['vif'], dict)
    
    def test_significant_predictors_filtering(self, analyzer, test_zones):
        """Test filtering of significant predictors."""
        result = analyzer.predict_zone_duration(test_zones)
        
        significant = result.get_significant_predictors(alpha=0.05)
        
        # All significant predictors should have p < 0.05
        for pred_name in significant.keys():
            assert result.p_values[pred_name] < 0.05


class TestRegressionIntegration:
    """Integration tests for regression analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return ZoneRegressionAnalyzer(alpha=0.05)
    
    @pytest.fixture
    def large_dataset(self):
        """Create larger dataset for more robust testing."""
        return create_test_zones_for_regression(100, seed=123)
    
    def test_both_models_on_same_data(self, analyzer, large_dataset):
        """Test both prediction models on same dataset."""
        duration_result = analyzer.predict_zone_duration(large_dataset)
        return_result = analyzer.predict_price_return(large_dataset)
        
        assert isinstance(duration_result, RegressionResult)
        assert isinstance(return_result, RegressionResult)
        
        # Different target variables
        assert duration_result.target_variable == 'duration'
        assert return_result.target_variable == 'price_return'
        
        # Both should have valid R²
        assert 0 <= duration_result.r_squared <= 1
        assert 0 <= return_result.r_squared <= 1
    
    def test_model_summary_available(self, analyzer, large_dataset):
        """Test that model summary is generated."""
        result = analyzer.predict_zone_duration(large_dataset)
        
        assert result.model_summary is not None
        assert isinstance(result.model_summary, str)
        assert len(result.model_summary) > 0
        assert 'OLS Regression Results' in result.model_summary
    
    def test_residuals_sum_to_zero(self, analyzer, large_dataset):
        """Test that residuals approximately sum to zero."""
        result = analyzer.predict_zone_duration(large_dataset)
        
        residual_sum = np.sum(result.residuals)
        
        # Should be very close to zero (within numerical precision)
        assert abs(residual_sum) < 1e-10 or abs(residual_sum) < abs(result.residuals.mean())
    
    def test_predictions_vs_actuals(self, analyzer, large_dataset):
        """Test relationship between predictions and actuals."""
        result = analyzer.predict_zone_duration(large_dataset)
        
        df = pd.DataFrame(large_dataset)
        actuals = df['duration'].dropna().values[:result.n_observations]
        
        # predictions + residuals should equal actuals
        reconstructed = result.predictions + result.residuals
        np.testing.assert_array_almost_equal(reconstructed, actuals, decimal=10)


# Export
__all__ = [
    'create_test_zones_for_regression',
    'TestRegressionResult',
    'TestZoneRegressionAnalyzer',
    'TestRegressionIntegration'
]

