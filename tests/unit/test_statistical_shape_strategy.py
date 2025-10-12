"""
Unit tests for StatisticalShapeStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
from bquant.analysis.zones.strategies.base import ShapeMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestStatisticalShapeStrategy:
    """Test suite for StatisticalShapeStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data and add macd_hist."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(df)
        
        # Add macd_hist to each zone (it's missing in sample data)
        for zone in zones:
            zone.data['macd_hist'] = zone.data['macd'] - zone.data['signal']
        
        return [z for z in zones if len(z.data) >= 10]
    
    @pytest.fixture
    def bull_zone(self, sample_zones):
        """Get first bull zone."""
        bull_zones = [z for z in sample_zones if z.type == 'bull']
        if not bull_zones:
            pytest.skip("No bull zones in sample data")
        return bull_zones[0].data
    
    @pytest.fixture
    def bear_zone(self, sample_zones):
        """Get first bear zone."""
        bear_zones = [z for z in sample_zones if z.type == 'bear']
        if not bear_zones:
            pytest.skip("No bear zones in sample data")
        return bear_zones[0].data
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = StatisticalShapeStrategy()
        assert strategy.calculate_smoothness == True
        assert strategy.bias_correction == True
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = StatisticalShapeStrategy(calculate_smoothness=False, bias_correction=False)
        assert strategy.calculate_smoothness == False
        assert strategy.bias_correction == False
    
    def test_calculate_symmetric_shape(self, bull_zone):
        """Test calculation on real bull zone data."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(bull_zone)
        
        assert isinstance(result, ShapeMetrics)
        assert result.strategy_name == 'statistical'
        
        # Skewness and kurtosis should be floats
        assert isinstance(result.hist_skewness, float)
        assert isinstance(result.hist_kurtosis, float)
        
        # Smoothness can be None or float
        assert result.hist_smoothness is None or isinstance(result.hist_smoothness, float)
    
    def test_calculate_early_impulse(self, sample_zones):
        """Test shape analysis on zones with different shapes."""
        strategy = StatisticalShapeStrategy()
        
        for zone in sample_zones[:3]:  # Test first 3 zones
            result = strategy.calculate(zone.data)
            
            # All metrics should be calculated
            assert isinstance(result.hist_skewness, float)
            assert isinstance(result.hist_kurtosis, float)
            assert not np.isnan(result.hist_skewness)
            assert not np.isnan(result.hist_kurtosis)
    
    def test_calculate_late_impulse(self, bear_zone):
        """Test calculation on bear zone."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(bear_zone)
        
        assert isinstance(result, ShapeMetrics)
        assert isinstance(result.hist_skewness, float)
        assert isinstance(result.hist_kurtosis, float)
    
    def test_smoothness_optional(self, bull_zone):
        """Test that smoothness is optional and handles edge cases."""
        strategy = StatisticalShapeStrategy(calculate_smoothness=True)
        result = strategy.calculate(bull_zone)
        
        # Smoothness might be None for small windows/data
        if result.hist_smoothness is not None:
            assert isinstance(result.hist_smoothness, float)
            assert result.hist_smoothness >= 0
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = StatisticalShapeStrategy()
        result = strategy.calculate(bull_zone)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'hist_skewness' in result_dict
        assert 'hist_kurtosis' in result_dict
        assert 'hist_smoothness' in result_dict
        assert 'strategy_name' in result_dict
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
        
        with pytest.raises(ValueError, match="must contain.*macd_hist"):
            strategy.calculate(df)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data for smoothness."""
        strategy = StatisticalShapeStrategy(calculate_smoothness=True)
        
        # Small data (less than window size)
        dates = pd.date_range('2025-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'macd_hist': [1.0, 2.0, 1.5, 0.5, -0.5]
        }, index=dates)
        
        result = strategy.calculate(df)
        
        # Should still calculate skewness/kurtosis
        assert isinstance(result.hist_skewness, float)
        assert isinstance(result.hist_kurtosis, float)
        
        # Smoothness might be calculated even with small data
        # (strategy uses rolling window which works with small data)
        assert result.hist_smoothness is None or isinstance(result.hist_smoothness, float)
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = StatisticalShapeStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'Statistical'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'source' in metadata
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_shape_strategy('statistical')
        
        assert isinstance(strategy, StatisticalShapeStrategy)
    
    def test_registry_with_params(self):
        """Test strategy creation from registry with custom params."""
        strategy = StrategyRegistry.get_shape_strategy('statistical', calculate_smoothness=False)
        
        assert isinstance(strategy, StatisticalShapeStrategy)
        assert strategy.calculate_smoothness == False
    
    def test_kurtosis_interpretation(self, sample_zones):
        """Test kurtosis values are reasonable."""
        strategy = StatisticalShapeStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate(zone.data)
            
            # Kurtosis should be a reasonable value (not extreme)
            # Excess kurtosis typically ranges from -2 (uniform) to ~10+ (heavy tails)
            assert -10 < result.hist_kurtosis < 50, \
                f"Kurtosis {result.hist_kurtosis} seems unreasonable"


def run_tests():
    """Run all statistical shape strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
