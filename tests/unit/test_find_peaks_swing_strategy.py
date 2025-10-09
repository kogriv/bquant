"""
Unit tests for FindPeaksSwingStrategy.

Tests the comprehensive swing metrics calculation using scipy.signal.find_peaks.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry


class TestFindPeaksSwingStrategy:
    """Test suite for FindPeaksSwingStrategy."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data with clear swing pattern."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
        
        # Simulate price with swings
        base_price = 3000
        trend = np.linspace(0, 100, 100)
        swings = 50 * np.sin(np.linspace(0, 4*np.pi, 100))
        
        close = base_price + trend + swings
        high = close + np.random.uniform(5, 15, 100)
        low = close - np.random.uniform(5, 15, 100)
        open_price = close + np.random.uniform(-10, 10, 100)
        
        df = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        }, index=dates)
        
        return df
    
    @pytest.fixture
    def strategy_default(self):
        """Create strategy with default parameters."""
        return FindPeaksSwingStrategy()
    
    def test_strategy_creation(self, strategy_default):
        """Test strategy can be created with default parameters."""
        assert strategy_default.prominence is None  # Auto-calculate
        assert strategy_default.distance == 5
        assert strategy_default.min_amplitude_pct == 0.02
    
    def test_strategy_custom_params(self):
        """Test strategy can be created with custom parameters."""
        strategy = FindPeaksSwingStrategy(prominence=10.0, distance=8, min_amplitude_pct=0.03)
        assert strategy.prominence == 10.0
        assert strategy.distance == 8
        assert strategy.min_amplitude_pct == 0.03
    
    def test_calculate_basic(self, strategy_default, sample_zone_data):
        """Test basic calculation returns SwingMetrics."""
        result = strategy_default.calculate(sample_zone_data)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'find_peaks'
        assert 'prominence' in result.strategy_params
        assert 'distance' in result.strategy_params
        assert 'min_amplitude_pct' in result.strategy_params
    
    def test_all_fields_populated(self, strategy_default, sample_zone_data):
        """Test all 23 fields of SwingMetrics are populated."""
        result = strategy_default.calculate(sample_zone_data)
        
        # Check all fields exist
        fields = [
            'num_swings', 'avg_rally_pct', 'avg_drop_pct', 'max_rally_pct', 'max_drop_pct',
            'rally_to_drop_ratio', 'rally_count', 'drop_count', 'min_rally_pct', 'min_drop_pct',
            'rally_amplitude_std', 'drop_amplitude_std', 'rally_amplitude_median', 'drop_amplitude_median',
            'avg_rally_duration_bars', 'avg_drop_duration_bars', 'max_rally_duration_bars', 'max_drop_duration_bars',
            'avg_rally_speed_pct_per_bar', 'avg_drop_speed_pct_per_bar',
            'max_rally_speed_pct_per_bar', 'max_drop_speed_pct_per_bar', 'duration_symmetry'
        ]
        
        for field in fields:
            assert hasattr(result, field)
            assert getattr(result, field) is not None
    
    def test_amplitude_filtering(self, sample_zone_data):
        """Test that min_amplitude_pct filters small movements."""
        # Strategy with tight filter (only large swings)
        strategy_strict = FindPeaksSwingStrategy(
            prominence=None,
            distance=3,
            min_amplitude_pct=0.05  # 5% minimum
        )
        
        # Strategy with loose filter (more swings)
        strategy_loose = FindPeaksSwingStrategy(
            prominence=None,
            distance=3,
            min_amplitude_pct=0.01  # 1% minimum
        )
        
        result_strict = strategy_strict.calculate(sample_zone_data)
        result_loose = strategy_loose.calculate(sample_zone_data)
        
        # Loose filter should find more or equal swings
        # (unless data is very smooth)
        total_swings_strict = result_strict.rally_count + result_strict.drop_count
        total_swings_loose = result_loose.rally_count + result_loose.drop_count
        
        assert total_swings_loose >= total_swings_strict
    
    def test_validate_method(self, strategy_default, sample_zone_data):
        """Test that validate() method works without errors."""
        result = strategy_default.calculate(sample_zone_data)
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, strategy_default, sample_zone_data):
        """Test to_dict() returns all fields."""
        result = strategy_default.calculate(sample_zone_data)
        result_dict = result.to_dict()
        
        # Should have 25 keys (23 metrics + 2 metadata)
        assert len(result_dict) == 25
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'find_peaks'
    
    def test_empty_data_handling(self, strategy_default):
        """Test handling of empty data."""
        empty_df = pd.DataFrame({'high': [], 'low': [], 'close': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy_default.calculate(empty_df)
    
    def test_missing_columns(self, strategy_default):
        """Test handling of missing required columns."""
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain columns"):
            strategy_default.calculate(df)
    
    def test_get_metadata(self, strategy_default):
        """Test get_metadata returns correct information."""
        metadata = strategy_default.get_metadata()
        
        assert metadata['name'] == 'FindPeaks'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'source' in metadata
        assert 'scipy' in metadata['source']
    
    def test_strategy_registry_integration(self):
        """Test strategy is properly registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_swing_strategy(
            'find_peaks',
            prominence=5.0,
            distance=10,
            min_amplitude_pct=0.03
        )
        
        assert isinstance(strategy, FindPeaksSwingStrategy)
        assert strategy.prominence == 5.0
        assert strategy.distance == 10
        assert strategy.min_amplitude_pct == 0.03
    
    def test_auto_prominence_calculation(self, sample_zone_data):
        """Test that prominence is auto-calculated when None."""
        strategy = FindPeaksSwingStrategy(prominence=None, distance=5, min_amplitude_pct=0.02)
        
        result = strategy.calculate(sample_zone_data)
        
        # Should work without errors
        assert isinstance(result, SwingMetrics)
        # Prominence in params should still be None (original value)
        assert result.strategy_params['prominence'] is None


def run_find_peaks_tests():
    """Run all FindPeaks swing strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_find_peaks_tests()

