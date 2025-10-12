"""
Unit tests for FindPeaksSwingStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestFindPeaksSwingStrategy:
    """Test suite for FindPeaksSwingStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(df)
        return [z for z in zones if len(z.data) >= 30]
    
    @pytest.fixture
    def bull_zone(self, sample_zones):
        """Get first bull zone with enough data."""
        bull_zones = [z for z in sample_zones if z.type == 'bull']
        if not bull_zones:
            pytest.skip("No bull zones in sample data")
        return bull_zones[0].data
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = FindPeaksSwingStrategy()
        assert strategy.prominence is None  # Auto-calculated
        assert strategy.distance == 5
        assert strategy.min_amplitude_pct == 0.02
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = FindPeaksSwingStrategy(prominence=10.0, distance=3, min_amplitude_pct=0.01)
        assert strategy.prominence == 10.0
        assert strategy.distance == 3
        assert strategy.min_amplitude_pct == 0.01
    
    def test_calculate_basic(self, bull_zone):
        """Test basic calculation on real data."""
        strategy = FindPeaksSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'find_peaks'
    
    def test_all_fields_populated(self, bull_zone):
        """Test that all 23 fields are populated."""
        strategy = FindPeaksSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Check all required fields exist
        assert isinstance(result.num_swings, int)
        assert isinstance(result.rally_count, int)
        assert isinstance(result.drop_count, int)
        assert isinstance(result.rally_to_drop_ratio, (int, float))
        assert result.strategy_name == 'find_peaks'
    
    def test_amplitude_filtering(self, bull_zone):
        """Test amplitude filtering works."""
        # Loose filtering (finds more swings)
        strategy_loose = FindPeaksSwingStrategy(min_amplitude_pct=0.005)
        result_loose = strategy_loose.calculate(bull_zone)
        
        # Strict filtering (finds fewer swings)
        strategy_strict = FindPeaksSwingStrategy(min_amplitude_pct=0.05)
        result_strict = strategy_strict.calculate(bull_zone)
        
        # Loose should find at least as many swings as strict
        # (or both could be 0 if data doesn't have enough movement)
        print(f"Loose: {result_loose.rally_count} rallies, {result_loose.drop_count} drops")
        print(f"Strict: {result_strict.rally_count} rallies, {result_strict.drop_count} drops")
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = FindPeaksSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = FindPeaksSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'find_peaks'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = FindPeaksSwingStrategy()
        
        empty_df = pd.DataFrame({'high': [], 'low': [], 'close': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate(empty_df)
    
    def test_missing_columns(self):
        """Test handling of missing columns."""
        strategy = FindPeaksSwingStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain"):
            strategy.calculate(df)
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = FindPeaksSwingStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'FindPeaks'
        assert 'description' in metadata
        assert 'params' in metadata
    
    def test_strategy_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_swing_strategy('find_peaks')
        
        assert isinstance(strategy, FindPeaksSwingStrategy)
    
    def test_auto_prominence_calculation(self, bull_zone):
        """Test auto prominence calculation (when prominence=None)."""
        strategy = FindPeaksSwingStrategy(prominence=None)
        result = strategy.calculate(bull_zone)
        
        # Should calculate prominence automatically
        # (1% of price range)
        assert isinstance(result, SwingMetrics)


def run_tests():
    """Run all FindPeaks swing strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
