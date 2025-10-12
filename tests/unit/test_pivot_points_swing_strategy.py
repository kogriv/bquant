"""
Unit tests for PivotPointsSwingStrategy using built-in sample data.
"""

import pytest
import pandas as pd

from bquant.analysis.zones.strategies.swing import PivotPointsSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestPivotPointsSwingStrategy:
    """Test suite for PivotPointsSwingStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(df)
        return [z for z in zones if len(z.data) >= 20]
    
    @pytest.fixture
    def bull_zone(self, sample_zones):
        """Get first bull zone."""
        bull_zones = [z for z in sample_zones if z.type == 'bull']
        if not bull_zones:
            pytest.skip("No bull zones in sample data")
        return bull_zones[0].data
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = PivotPointsSwingStrategy()
        assert strategy.left_bars == 2
        assert strategy.right_bars == 2
        assert strategy.min_amplitude_pct == 0.015
    
    def test_calculate_basic(self, bull_zone):
        """Test basic calculation on real data."""
        strategy = PivotPointsSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'pivot_points'
    
    def test_all_fields_present(self, bull_zone):
        """Test that all swing metric fields are present."""
        strategy = PivotPointsSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Check all fields exist
        assert hasattr(result, 'num_swings')
        assert hasattr(result, 'rally_count')
        assert hasattr(result, 'drop_count')
        assert hasattr(result, 'rally_to_drop_ratio')
        assert hasattr(result, 'duration_symmetry')
        assert hasattr(result, 'strategy_name')
        assert result.strategy_name == 'pivot_points'
    
    def test_validate_works(self, bull_zone):
        """Test that validate() method works."""
        strategy = PivotPointsSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_swing_strategy('pivot_points')
        
        assert isinstance(strategy, PivotPointsSwingStrategy)
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = PivotPointsSwingStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'PivotPoints'  # Actual name without space
        assert 'description' in metadata
        assert 'params' in metadata


def run_tests():
    """Run all PivotPoints swing strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
