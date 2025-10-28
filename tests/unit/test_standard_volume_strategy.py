"""
Unit tests for StandardVolumeStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy
from bquant.analysis.zones.strategies.base import VolumeMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestStandardVolumeStrategy:
    """Test suite for StandardVolumeStrategy using real sample data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        result = analyzer.analyze_complete_modular(df)
        zones = result.zones
        
        # Add macd_hist to each zone
        for zone in zones:
            zone.data['macd_hist'] = zone.data['macd'] - zone.data['macd_signal']
        
        return [z for z in zones if len(z.data) >= 10 and 'volume' in z.data.columns]
    
    @pytest.fixture
    def bull_zone(self, sample_zones):
        """Get first bull zone with volume data."""
        bull_zones = [z for z in sample_zones if z.type == 'bull']
        if not bull_zones:
            pytest.skip("No bull zones with volume in sample data")
        return bull_zones[0].data
    
    def test_strategy_creation(self):
        """Test strategy creation with default parameters."""
        strategy = StandardVolumeStrategy()
        assert strategy.baseline_window == 50
        assert strategy.correlation_min_periods == 3
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = StandardVolumeStrategy(
            baseline_window=100,
            correlation_min_periods=5
        )
        assert strategy.baseline_window == 100
        assert strategy.correlation_min_periods == 5
    
    def test_calculate_volume_without_baseline(self, bull_zone):
        """Test volume calculation without baseline (baseline=None)."""
        strategy = StandardVolumeStrategy()
        result = strategy.calculate_volume(bull_zone, baseline_volume=None)
        
        assert isinstance(result, VolumeMetrics)
        assert result.strategy_name == 'standard'
        
        # Without baseline, ratio and entry_change should be None
        assert result.volume_zone_ratio is None
        assert result.volume_at_entry_change is None
        
        # But avg_volume should be calculated
        assert result.avg_volume_zone is not None
        assert result.avg_volume_zone > 0
    
    def test_calculate_volume_with_baseline(self, bull_zone):
        """Test volume calculation with baseline provided."""
        strategy = StandardVolumeStrategy()
        
        # Calculate baseline from zone data (for testing)
        baseline = float(bull_zone['volume'].mean() * 0.8)  # Slightly lower baseline
        
        result = strategy.calculate_volume(bull_zone, baseline_volume=baseline)
        
        assert isinstance(result, VolumeMetrics)
        
        # With baseline, ratio should be calculated
        assert result.volume_zone_ratio is not None
        assert result.volume_zone_ratio > 0
        
        # Avg volume should be calculated
        assert result.avg_volume_zone is not None
    
    def test_all_fields_populated(self, bull_zone):
        """Test that all volume fields can be populated."""
        strategy = StandardVolumeStrategy()
        baseline = float(bull_zone['volume'].mean())
        
        result = strategy.calculate_volume(bull_zone, baseline_volume=baseline)
        
        # Check all fields
        assert isinstance(result.volume_zone_ratio, (int, float))
        assert isinstance(result.volume_at_entry_change, (int, float))
        assert isinstance(result.avg_volume_zone, (int, float))
        
        # volume_indicator_corr depends on indicator presence  
        if 'macd_hist' in bull_zone.columns or 'macd' in bull_zone.columns:
            assert result.volume_indicator_corr is None or isinstance(result.volume_indicator_corr, (int, float))
        
        assert result.strategy_name == 'standard'
        assert isinstance(result.strategy_params, dict)
    
    def test_volume_macd_correlation(self, bull_zone):
        """Test volume-indicator correlation calculation."""
        strategy = StandardVolumeStrategy()
        result = strategy.calculate_volume(bull_zone, baseline_volume=None)
        
        # Should calculate correlation if indicator is present
        if ('macd_hist' in bull_zone.columns or 'macd' in bull_zone.columns) and len(bull_zone) >= 3:
            assert result.volume_indicator_corr is None or isinstance(result.volume_indicator_corr, (int, float))
            
            if result.volume_indicator_corr is not None:
                # Correlation should be in [-1, 1]
                assert -1 <= result.volume_indicator_corr <= 1
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = StandardVolumeStrategy()
        result = strategy.calculate_volume(bull_zone, baseline_volume=100.0)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = StandardVolumeStrategy()
        result = strategy.calculate_volume(bull_zone, baseline_volume=100.0)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'volume_zone_ratio' in result_dict
        assert 'volume_at_entry_change' in result_dict
        assert 'volume_indicator_corr' in result_dict
        assert 'avg_volume_zone' in result_dict
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'standard'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = StandardVolumeStrategy()
        
        empty_df = pd.DataFrame({'volume': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate_volume(empty_df)
    
    def test_missing_volume_column(self):
        """Test handling of missing volume column."""
        strategy = StandardVolumeStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain.*volume"):
            strategy.calculate_volume(df)
    
    def test_zero_volume_handling(self):
        """Test handling of zero/empty volume data."""
        strategy = StandardVolumeStrategy()
        
        # Volume column exists but all zeros
        dates = pd.date_range('2025-01-01', periods=10, freq='1h')
        df = pd.DataFrame({
            'volume': [0] * 10,
            'close': [100 + i for i in range(10)]
        }, index=dates)
        
        result = strategy.calculate_volume(df)
        
        # Should return empty metrics
        assert result.volume_zone_ratio is None
        assert result.avg_volume_zone is None
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = StandardVolumeStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'Standard'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'source' in metadata
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_volume_strategy('standard')
        
        assert isinstance(strategy, StandardVolumeStrategy)
    
    def test_registry_with_params(self):
        """Test strategy creation from registry with custom params."""
        strategy = StrategyRegistry.get_volume_strategy(
            'standard',
            baseline_window=100,
            correlation_min_periods=5
        )
        
        assert isinstance(strategy, StandardVolumeStrategy)
        assert strategy.baseline_window == 100
        assert strategy.correlation_min_periods == 5
    
    def test_baseline_ratio_calculation(self):
        """Test volume zone ratio calculation logic."""
        strategy = StandardVolumeStrategy()
        
        # Create test data
        dates = pd.date_range('2025-01-01', periods=20, freq='1h')
        df = pd.DataFrame({
            'volume': [200] * 20,  # Zone volume = 200
            'macd_hist': [1.0] * 20,
            'close': [100] * 20
        }, index=dates)
        
        baseline = 100.0  # Baseline = 100
        result = strategy.calculate_volume(df, baseline_volume=baseline)
        
        # Ratio should be 200/100 = 2.0
        assert result.volume_zone_ratio is not None
        assert abs(result.volume_zone_ratio - 2.0) < 0.01


def run_tests():
    """Run all standard volume strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

