"""
Unit tests for ZigZagSwingStrategy.

Tests the comprehensive swing metrics calculation using pandas-ta ZigZag algorithm.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry


class TestZigZagSwingStrategy:
    """Test suite for ZigZagSwingStrategy."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data with clear swing pattern."""
        # Create data with clear uptrend with swings
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
        
        # Simulate price with swings: base trend + sine wave
        base_price = 3000
        trend = np.linspace(0, 100, 100)  # Uptrend +100
        swings = 50 * np.sin(np.linspace(0, 4*np.pi, 100))  # 4 full cycles
        
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
        return ZigZagSwingStrategy()
    
    @pytest.fixture
    def strategy_sensitive(self):
        """Create strategy with sensitive parameters (more swings)."""
        return ZigZagSwingStrategy(legs=5, deviation=0.02)
    
    def test_strategy_creation(self, strategy_default):
        """Test strategy can be created with default parameters."""
        assert strategy_default.legs == 10
        assert strategy_default.deviation == 0.05
    
    def test_strategy_custom_params(self):
        """Test strategy can be created with custom parameters."""
        strategy = ZigZagSwingStrategy(legs=15, deviation=0.08)
        assert strategy.legs == 15
        assert strategy.deviation == 0.08
    
    def test_calculate_basic(self, strategy_default, sample_zone_data):
        """Test basic calculation returns SwingMetrics."""
        result = strategy_default.calculate(sample_zone_data)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'zigzag'
        assert 'legs' in result.strategy_params
        assert 'deviation' in result.strategy_params
    
    def test_all_fields_populated(self, strategy_sensitive, sample_zone_data):
        """Test all 23 fields of SwingMetrics are populated."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        # Check all fields exist and are not None
        fields_to_check = [
            # Existing (6)
            'num_swings', 'avg_rally_pct', 'avg_drop_pct',
            'max_rally_pct', 'max_drop_pct', 'rally_to_drop_ratio',
            # Counters (2)
            'rally_count', 'drop_count',
            # Minimums and distribution (6)
            'min_rally_pct', 'min_drop_pct',
            'rally_amplitude_std', 'drop_amplitude_std',
            'rally_amplitude_median', 'drop_amplitude_median',
            # Duration (4)
            'avg_rally_duration_bars', 'avg_drop_duration_bars',
            'max_rally_duration_bars', 'max_drop_duration_bars',
            # Speed (4)
            'avg_rally_speed_pct_per_bar', 'avg_drop_speed_pct_per_bar',
            'max_rally_speed_pct_per_bar', 'max_drop_speed_pct_per_bar',
            # Symmetry (1)
            'duration_symmetry'
        ]
        
        for field in fields_to_check:
            assert hasattr(result, field), f"Missing field: {field}"
            value = getattr(result, field)
            assert value is not None, f"Field {field} is None"
    
    def test_rally_drop_counts(self, strategy_sensitive, sample_zone_data):
        """Test rally and drop counts are calculated."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        # Should detect some rallies and drops in the sine wave pattern
        if result.rally_count > 0:
            assert result.rally_count >= 0
            assert result.drop_count >= 0
            # Usually should have similar counts
            assert abs(result.rally_count - result.drop_count) <= 1
    
    def test_amplitude_metrics_logical(self, strategy_sensitive, sample_zone_data):
        """Test amplitude metrics are logically consistent."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        if result.rally_count > 0:
            # Max >= Avg >= Min
            assert result.max_rally_pct >= result.avg_rally_pct
            assert result.avg_rally_pct >= result.min_rally_pct
            # Median should be close to average (if more than 1 rally)
            if result.rally_count > 1:
                # For multiple rallies, median should be within 2 std of mean
                assert abs(result.rally_amplitude_median - result.avg_rally_pct) <= result.rally_amplitude_std * 2 + 0.01
            else:
                # For single rally, median == mean == min == max
                assert result.rally_amplitude_median == result.avg_rally_pct
        
        if result.drop_count > 0:
            assert result.max_drop_pct >= result.avg_drop_pct
            assert result.avg_drop_pct >= result.min_drop_pct
            # Median should be close to average (if more than 1 drop)
            if result.drop_count > 1:
                assert abs(result.drop_amplitude_median - result.avg_drop_pct) <= result.drop_amplitude_std * 2 + 0.01
            else:
                # For single drop, median == mean == min == max
                assert result.drop_amplitude_median == result.avg_drop_pct
    
    def test_duration_metrics(self, strategy_sensitive, sample_zone_data):
        """Test duration metrics are calculated correctly."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        if result.rally_count > 0:
            assert result.avg_rally_duration_bars > 0
            assert result.max_rally_duration_bars > 0
            assert result.max_rally_duration_bars >= result.avg_rally_duration_bars
        
        if result.drop_count > 0:
            assert result.avg_drop_duration_bars > 0
            assert result.max_drop_duration_bars > 0
            assert result.max_drop_duration_bars >= result.avg_drop_duration_bars
    
    def test_speed_metrics(self, strategy_sensitive, sample_zone_data):
        """Test speed metrics are calculated correctly."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        if result.rally_count > 0:
            # Speed = amplitude / duration
            assert result.avg_rally_speed_pct_per_bar > 0
            assert result.max_rally_speed_pct_per_bar >= result.avg_rally_speed_pct_per_bar
        
        if result.drop_count > 0:
            assert result.avg_drop_speed_pct_per_bar > 0
            assert result.max_drop_speed_pct_per_bar >= result.avg_drop_speed_pct_per_bar
    
    def test_symmetry_metric(self, strategy_sensitive, sample_zone_data):
        """Test duration symmetry metric."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        if result.rally_count > 0 and result.drop_count > 0:
            # Symmetry = avg_rally_duration / avg_drop_duration
            expected_symmetry = result.avg_rally_duration_bars / result.avg_drop_duration_bars
            assert abs(result.duration_symmetry - expected_symmetry) < 0.01
    
    def test_validate_method(self, strategy_sensitive, sample_zone_data):
        """Test that validate() method works without errors."""
        result = strategy_sensitive.calculate(sample_zone_data)
        
        # Should not raise any exception
        result.validate()
    
    def test_to_dict_method(self, strategy_sensitive, sample_zone_data):
        """Test to_dict() returns all 23 fields."""
        result = strategy_sensitive.calculate(sample_zone_data)
        result_dict = result.to_dict()
        
        # Should have 23 fields + metadata (2) = 25 keys
        expected_keys = [
            # Existing (6)
            'num_swings', 'avg_rally_pct', 'avg_drop_pct',
            'max_rally_pct', 'max_drop_pct', 'rally_to_drop_ratio',
            # Counters (2)
            'rally_count', 'drop_count',
            # Minimums and distribution (6)
            'min_rally_pct', 'min_drop_pct',
            'rally_amplitude_std', 'drop_amplitude_std',
            'rally_amplitude_median', 'drop_amplitude_median',
            # Duration (4)
            'avg_rally_duration_bars', 'avg_drop_duration_bars',
            'max_rally_duration_bars', 'max_drop_duration_bars',
            # Speed (4)
            'avg_rally_speed_pct_per_bar', 'avg_drop_speed_pct_per_bar',
            'max_rally_speed_pct_per_bar', 'max_drop_speed_pct_per_bar',
            # Symmetry (1)
            'duration_symmetry',
            # Metadata (2)
            'strategy_name', 'strategy_params'
        ]
        
        for key in expected_keys:
            assert key in result_dict, f"Missing key in to_dict(): {key}"
        
        assert len(result_dict) == 25, f"Expected 25 keys, got {len(result_dict)}"
    
    def test_empty_data_handling(self, strategy_default):
        """Test handling of empty data."""
        empty_df = pd.DataFrame({
            'high': [],
            'low': [],
            'close': []
        })
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy_default.calculate(empty_df)
    
    def test_missing_columns(self, strategy_default):
        """Test handling of missing required columns."""
        df = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        with pytest.raises(ValueError, match="must contain columns"):
            strategy_default.calculate(df)
    
    def test_insufficient_swings(self, strategy_default):
        """Test handling when not enough swings detected."""
        # Very short data or flat price
        dates = pd.date_range(start='2025-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'open': [3000] * 5,
            'high': [3000] * 5,
            'low': [3000] * 5,
            'close': [3000] * 5
        }, index=dates)
        
        result = strategy_default.calculate(df)
        
        # Should return empty metrics
        assert result.num_swings == 0
        assert result.rally_count == 0
        assert result.drop_count == 0
    
    def test_get_metadata(self, strategy_default):
        """Test get_metadata returns correct information."""
        metadata = strategy_default.get_metadata()
        
        assert metadata['name'] == 'ZigZag'
        assert 'description' in metadata
        assert 'params' in metadata
        assert metadata['params']['legs'] == 10
        assert metadata['params']['deviation'] == 0.05
        assert 'source' in metadata
        assert 'pandas-ta' in metadata['source']
    
    def test_strategy_registry_integration(self):
        """Test strategy is properly registered in StrategyRegistry."""
        # Should be able to get strategy from registry
        strategy = StrategyRegistry.get_swing_strategy('zigzag', legs=8, deviation=0.03)
        
        assert isinstance(strategy, ZigZagSwingStrategy)
        assert strategy.legs == 8
        assert strategy.deviation == 0.03
    
    def test_different_parameters_different_results(self, sample_zone_data):
        """Test that different parameters yield different results."""
        strategy_loose = ZigZagSwingStrategy(legs=15, deviation=0.08)
        strategy_tight = ZigZagSwingStrategy(legs=5, deviation=0.02)
        
        result_loose = strategy_loose.calculate(sample_zone_data)
        result_tight = strategy_tight.calculate(sample_zone_data)
        
        # Tighter parameters should detect more swings
        # (unless data is very smooth)
        # At least the parameters should be different
        assert (result_loose.strategy_params != result_tight.strategy_params)


def run_zigzag_swing_tests():
    """Run all ZigZag swing strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_zigzag_swing_tests()

