"""
Unit tests for ClassicDivergenceStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
from bquant.analysis.zones.strategies.base import DivergenceMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestClassicDivergenceStrategy:
    """Test suite for ClassicDivergenceStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(df)
        
        # Add macd_hist to each zone
        for zone in zones:
            zone.data['macd_hist'] = zone.data['macd'] - zone.data['signal']
        
        return [z for z in zones if len(z.data) >= 20]
    
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
        strategy = ClassicDivergenceStrategy()
        assert strategy.min_peak_distance == 5
        assert strategy.min_divergence_strength == 0.01
        assert strategy.use_macd_line == False
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = ClassicDivergenceStrategy(
            min_peak_distance=10,
            min_divergence_strength=0.05,
            use_macd_line=True
        )
        assert strategy.min_peak_distance == 10
        assert strategy.min_divergence_strength == 0.05
        assert strategy.use_macd_line == True
    
    def test_calculate_divergence_basic(self, bull_zone):
        """Test basic divergence calculation on real data."""
        strategy = ClassicDivergenceStrategy()
        result = strategy.calculate_divergence(bull_zone)
        
        assert isinstance(result, DivergenceMetrics)
        assert result.strategy_name == 'classic'
    
    def test_all_fields_populated(self, bull_zone):
        """Test that all divergence fields are populated."""
        strategy = ClassicDivergenceStrategy()
        result = strategy.calculate_divergence(bull_zone)
        
        # Check all required fields exist
        assert result.divergence_type in ['none', 'regular', 'hidden', 'mixed']
        assert isinstance(result.divergence_count, int)
        assert result.divergence_count >= 0
        assert isinstance(result.divergence_strength, (int, float))
        assert result.divergence_strength >= 0
        assert result.divergence_direction in ['bullish', 'bearish', 'none']
        assert result.strategy_name == 'classic'
        assert isinstance(result.strategy_params, dict)
    
    def test_divergence_counts_reasonable(self, sample_zones):
        """Test divergence counts are reasonable across zones."""
        strategy = ClassicDivergenceStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate_divergence(zone.data)
            
            # Counts should be non-negative
            assert result.divergence_count >= 0
            
            # Count should not be excessive (max ~5 divergences in a zone is reasonable)
            assert result.divergence_count <= 10
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = ClassicDivergenceStrategy()
        result = strategy.calculate_divergence(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = ClassicDivergenceStrategy()
        result = strategy.calculate_divergence(bull_zone)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'divergence_type' in result_dict
        assert 'divergence_count' in result_dict
        assert 'divergence_strength' in result_dict
        assert 'divergence_direction' in result_dict
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'classic'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = ClassicDivergenceStrategy()
        
        empty_df = pd.DataFrame({'close': [], 'high': [], 'low': [], 'macd_hist': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate_divergence(empty_df)
    
    def test_missing_columns(self):
        """Test handling of missing columns."""
        strategy = ClassicDivergenceStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain"):
            strategy.calculate_divergence(df)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        strategy = ClassicDivergenceStrategy(min_peak_distance=10)
        
        # Too little data for peak detection
        dates = pd.date_range('2025-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'close': [100, 101, 102, 101, 100],
            'high': [101, 102, 103, 102, 101],
            'low': [99, 100, 101, 100, 99],
            'macd_hist': [1.0, 2.0, 1.5, 0.5, -0.5]
        }, index=dates)
        
        result = strategy.calculate_divergence(df)
        
        # Should return empty metrics, not crash
        assert result.divergence_type == 'none'
        assert result.divergence_count == 0
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = ClassicDivergenceStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'Classic'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'source' in metadata
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_divergence_strategy('classic')
        
        assert isinstance(strategy, ClassicDivergenceStrategy)
    
    def test_registry_with_params(self):
        """Test strategy creation from registry with custom params."""
        strategy = StrategyRegistry.get_divergence_strategy(
            'classic',
            min_peak_distance=15,
            min_divergence_strength=0.02
        )
        
        assert isinstance(strategy, ClassicDivergenceStrategy)
        assert strategy.min_peak_distance == 15
        assert strategy.min_divergence_strength == 0.02
    
    def test_use_macd_line_option(self, bull_zone):
        """Test use_macd_line parameter."""
        strategy_hist = ClassicDivergenceStrategy(use_macd_line=False)
        strategy_line = ClassicDivergenceStrategy(use_macd_line=True)
        
        result_hist = strategy_hist.calculate_divergence(bull_zone)
        result_line = strategy_line.calculate_divergence(bull_zone)
        
        # Both should work (may have different results)
        assert isinstance(result_hist, DivergenceMetrics)
        assert isinstance(result_line, DivergenceMetrics)
    
    def test_direction_consistency(self, sample_zones):
        """Test that direction is consistent with count."""
        strategy = ClassicDivergenceStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate_divergence(zone.data)
            
            # If no divergences, direction should be 'none'
            if result.divergence_count == 0:
                assert result.divergence_direction == 'none'
            
            # If divergences exist, direction should not be 'none'
            if result.divergence_count > 0:
                assert result.divergence_direction in ['bullish', 'bearish']


def run_tests():
    """Run all classic divergence strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

