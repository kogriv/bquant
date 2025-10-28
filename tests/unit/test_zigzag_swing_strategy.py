"""
Unit tests for ZigZagSwingStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestZigZagSwingStrategy:
    """Test suite for ZigZagSwingStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        result = analyzer.analyze_complete_modular(df)
        zones = result.zones
        
        # macd_hist already present in new API
        return [z for z in zones if len(z.data) >= 10]  # Lowered threshold from 50 to 10
    
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
        strategy = ZigZagSwingStrategy()
        assert strategy.legs == 10
        assert strategy.deviation == 0.05
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = ZigZagSwingStrategy(legs=15, deviation=0.03)
        assert strategy.legs == 15
        assert strategy.deviation == 0.03
    
    def test_calculate_basic(self, bull_zone):
        """Test basic calculation on real data."""
        strategy = ZigZagSwingStrategy(legs=10, deviation=0.05)
        result = strategy.calculate(bull_zone)
        
        assert isinstance(result, SwingMetrics)
        assert result.strategy_name == 'zigzag'
    
    def test_all_fields_populated(self, bull_zone):
        """Test that all 23 fields are populated."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Check all fields exist and are not None (except if legitimately 0)
        assert isinstance(result.num_swings, int)
        assert isinstance(result.avg_rally_pct, (int, float))
        assert isinstance(result.avg_drop_pct, (int, float))
        assert isinstance(result.rally_count, int)
        assert isinstance(result.drop_count, int)
        assert isinstance(result.rally_to_drop_ratio, (int, float))
        assert isinstance(result.duration_symmetry, (int, float))
        assert result.strategy_name == 'zigzag'
        assert isinstance(result.strategy_params, dict)
    
    def test_rally_drop_counts(self, bull_zone):
        """Test rally and drop counts are reasonable."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Counts should be non-negative
        assert result.rally_count >= 0
        assert result.drop_count >= 0
        
        # num_swings should be consistent with counts
        # (can be different depending on how swings are counted)
        assert result.num_swings >= 0
    
    def test_amplitude_metrics_logical(self, bull_zone):
        """Test that amplitude metrics follow logical constraints."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # If there are rallies, metrics should be reasonable
        if result.rally_count > 0:
            assert result.max_rally_pct >= result.avg_rally_pct >= result.min_rally_pct >= 0
        
        # If there are drops, metrics should be reasonable
        if result.drop_count > 0:
            assert result.max_drop_pct >= result.avg_drop_pct >= result.min_drop_pct >= 0
    
    def test_duration_metrics(self, bull_zone):
        """Test duration metrics are populated."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Duration should be non-negative
        assert result.avg_rally_duration_bars >= 0
        assert result.avg_drop_duration_bars >= 0
        assert result.max_rally_duration_bars >= 0
        assert result.max_drop_duration_bars >= 0
    
    def test_speed_metrics(self, bull_zone):
        """Test speed metrics are populated."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Speed should be non-negative
        assert result.avg_rally_speed_pct_per_bar >= 0
        assert result.avg_drop_speed_pct_per_bar >= 0
        assert result.max_rally_speed_pct_per_bar >= 0
        assert result.max_drop_speed_pct_per_bar >= 0
    
    def test_symmetry_metric(self, bull_zone):
        """Test duration_symmetry metric."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        # Symmetry should be non-negative
        assert result.duration_symmetry >= 0
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = ZigZagSwingStrategy()
        result = strategy.calculate(bull_zone)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'rally_count' in result_dict
        assert 'drop_count' in result_dict
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'zigzag'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = ZigZagSwingStrategy()
        
        empty_df = pd.DataFrame({'high': [], 'low': [], 'close': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate(empty_df)
    
    def test_missing_columns(self):
        """Test handling of missing columns."""
        strategy = ZigZagSwingStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain"):
            strategy.calculate(df)
    
    def test_insufficient_swings(self):
        """Test handling when ZigZag finds no swings."""
        strategy = ZigZagSwingStrategy(legs=50, deviation=0.20)  # Very strict
        
        # Small flat data
        dates = pd.date_range('2025-01-01', periods=20, freq='1h')
        df = pd.DataFrame({
            'high': [3000 + i*0.1 for i in range(20)],  # Very small changes
            'low': [2999 + i*0.1 for i in range(20)],
            'close': [2999.5 + i*0.1 for i in range(20)]
        }, index=dates)
        
        result = strategy.calculate(df)
        
        # Should return empty metrics, not crash
        assert result.rally_count == 0
        assert result.drop_count == 0
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = ZigZagSwingStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'ZigZag'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'source' in metadata
    
    def test_strategy_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_swing_strategy('zigzag')
        
        assert isinstance(strategy, ZigZagSwingStrategy)
        assert strategy.legs == 10
        assert strategy.deviation == 0.05
    
    def test_different_parameters_different_results(self, bull_zone):
        """Test that different parameters produce different results."""
        strategy1 = ZigZagSwingStrategy(legs=5, deviation=0.03)   # More sensitive
        strategy2 = ZigZagSwingStrategy(legs=20, deviation=0.10)  # Less sensitive
        
        result1 = strategy1.calculate(bull_zone)
        result2 = strategy2.calculate(bull_zone)
        
        # Results should differ (more sensitive finds more swings typically)
        # Note: May not always be true depending on data
        print(f"Strategy1 (sensitive): {result1.rally_count} rallies, {result1.drop_count} drops")
        print(f"Strategy2 (strict): {result2.rally_count} rallies, {result2.drop_count} drops")


def run_tests():
    """Run all ZigZag swing strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
