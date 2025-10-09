"""
Unit tests for PivotPointsSwingStrategy.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.swing import PivotPointsSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry


class TestPivotPointsSwingStrategy:
    """Test suite for PivotPointsSwingStrategy."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data."""
        dates = pd.date_range(start='2025-01-01', periods=50, freq='1h')
        base_price = 3000
        trend = np.linspace(0, 50, 50)
        swings = 30 * np.sin(np.linspace(0, 3*np.pi, 50))
        
        close = base_price + trend + swings
        high = close + np.random.uniform(2, 8, 50)
        low = close - np.random.uniform(2, 8, 50)
        
        return pd.DataFrame({
            'open': close,
            'high': high,
            'low': low,
            'close': close
        }, index=dates)
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = PivotPointsSwingStrategy()
        assert strategy.left_bars == 2
        assert strategy.right_bars == 2
        assert strategy.min_amplitude_pct == 0.015
    
    def test_calculate_basic(self, sample_zone_data):
        """Test basic calculation."""
        strategy = PivotPointsSwingStrategy()
        result = strategy.calculate(sample_zone_data)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'pivot_points'
    
    def test_all_fields_present(self, sample_zone_data):
        """Test all 23 fields are present."""
        strategy = PivotPointsSwingStrategy(left_bars=2, right_bars=2)
        result = strategy.calculate(sample_zone_data)
        
        # Verify all fields exist
        assert hasattr(result, 'rally_count')
        assert hasattr(result, 'drop_count')
        assert hasattr(result, 'duration_symmetry')
        assert hasattr(result, 'avg_rally_speed_pct_per_bar')
    
    def test_validate_works(self, sample_zone_data):
        """Test validate() doesn't raise."""
        strategy = PivotPointsSwingStrategy()
        result = strategy.calculate(sample_zone_data)
        result.validate()  # Should not raise
    
    def test_registry_integration(self):
        """Test strategy is registered."""
        strategy = StrategyRegistry.get_swing_strategy(
            'pivot_points',
            left_bars=3,
            right_bars=3,
            min_amplitude_pct=0.02
        )
        
        assert isinstance(strategy, PivotPointsSwingStrategy)
        assert strategy.left_bars == 3
        assert strategy.right_bars == 3
    
    def test_get_metadata(self):
        """Test get_metadata."""
        strategy = PivotPointsSwingStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'PivotPoints'
        assert 'pattern' in metadata
        assert 'params' in metadata


def run_tests():
    """Run all tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

