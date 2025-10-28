"""
Unit tests for CombinedVolatilityStrategy using built-in sample data.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.strategies.volatility import CombinedVolatilityStrategy
from bquant.analysis.zones.strategies.base import VolatilityMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestCombinedVolatilityStrategy:
    """Test suite for CombinedVolatilityStrategy using real sample data."""
    
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
        
        # Filter zones with enough data for Bollinger Bands calculation (need > bb_length)
        return [z for z in zones if len(z.data) >= 30]  # BB default length is 20, use 30 for safety
    
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
        strategy = CombinedVolatilityStrategy()
        assert strategy.bb_length == 20
        assert strategy.bb_std == 2.0
        assert strategy.touch_threshold == 0.01
    
    def test_strategy_custom_params(self):
        """Test strategy with custom parameters."""
        strategy = CombinedVolatilityStrategy(
            bb_length=30,
            bb_std=2.5,
            touch_threshold=0.02
        )
        assert strategy.bb_length == 30
        assert strategy.bb_std == 2.5
        assert strategy.touch_threshold == 0.02
    
    def test_calculate_volatility_basic(self, bull_zone):
        """Test basic volatility calculation on real data."""
        strategy = CombinedVolatilityStrategy()
        result = strategy.calculate_volatility(bull_zone)
        
        assert isinstance(result, VolatilityMetrics)
        assert result.strategy_name == 'combined'
    
    def test_all_fields_populated(self, bull_zone):
        """Test that all 10 volatility fields are populated."""
        strategy = CombinedVolatilityStrategy()
        result = strategy.calculate_volatility(bull_zone)
        
        # Bollinger fields
        assert isinstance(result.bollinger_width_pct, (int, float))
        assert result.bollinger_width_pct >= 0
        assert isinstance(result.bollinger_width_std, (int, float))
        assert result.bollinger_width_std >= 0
        assert isinstance(result.bollinger_squeeze_ratio, (int, float))
        assert result.bollinger_squeeze_ratio >= 0
        assert isinstance(result.bollinger_upper_touches, int)
        assert result.bollinger_upper_touches >= 0
        assert isinstance(result.bollinger_lower_touches, int)
        assert result.bollinger_lower_touches >= 0
        
        # ATR fields
        assert isinstance(result.atr_normalized_range, (int, float))
        assert result.atr_normalized_range >= 0
        assert result.atr_trend in ['increasing', 'decreasing', 'stable']
        assert isinstance(result.avg_atr, (int, float))
        assert result.avg_atr >= 0
        
        # Composite fields
        assert isinstance(result.volatility_score, (int, float))
        assert 0 <= result.volatility_score <= 10
        assert result.volatility_regime in ['low', 'medium', 'high', 'extreme']
        
        # Metadata
        assert result.strategy_name == 'combined'
        assert isinstance(result.strategy_params, dict)
    
    def test_volatility_score_range(self, sample_zones):
        """Test volatility score is always in [0, 10] range."""
        strategy = CombinedVolatilityStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate_volatility(zone.data)
            
            assert 0 <= result.volatility_score <= 10, \
                f"Volatility score {result.volatility_score} out of range [0, 10]"
    
    def test_volatility_regime_classification(self, sample_zones):
        """Test volatility regime classification is consistent."""
        strategy = CombinedVolatilityStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate_volatility(zone.data)
            
            # Regime should match score
            if result.volatility_score < 2.5:
                assert result.volatility_regime == 'low'
            elif result.volatility_score < 5.0:
                assert result.volatility_regime == 'medium'
            elif result.volatility_score < 7.5:
                assert result.volatility_regime == 'high'
            else:
                assert result.volatility_regime == 'extreme'
    
    def test_atr_trend_detection(self, sample_zones):
        """Test ATR trend detection works."""
        strategy = CombinedVolatilityStrategy()
        
        trends = []
        for zone in sample_zones:
            result = strategy.calculate_volatility(zone.data)
            trends.append(result.atr_trend)
        
        # Should have various trends across zones
        unique_trends = set(trends)
        assert len(unique_trends) > 0
        assert all(t in ['increasing', 'decreasing', 'stable'] for t in trends)
        
        print(f"ATR trends found: {unique_trends}")
    
    def test_validate_method(self, bull_zone):
        """Test that validate() works without errors."""
        strategy = CombinedVolatilityStrategy()
        result = strategy.calculate_volatility(bull_zone)
        
        result.validate()  # Should not raise
    
    def test_to_dict_method(self, bull_zone):
        """Test to_dict() serialization."""
        strategy = CombinedVolatilityStrategy()
        result = strategy.calculate_volatility(bull_zone)
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'bollinger_width_pct' in result_dict
        assert 'bollinger_squeeze_ratio' in result_dict
        assert 'atr_normalized_range' in result_dict
        assert 'atr_trend' in result_dict
        assert 'volatility_score' in result_dict
        assert 'volatility_regime' in result_dict
        assert 'strategy_name' in result_dict
        assert result_dict['strategy_name'] == 'combined'
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        strategy = CombinedVolatilityStrategy()
        
        empty_df = pd.DataFrame({'high': [], 'low': [], 'close': [], 'atr': []})
        
        with pytest.raises(ValueError, match="cannot be empty"):
            strategy.calculate_volatility(empty_df)
    
    def test_missing_columns(self):
        """Test handling of missing columns."""
        strategy = CombinedVolatilityStrategy()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        with pytest.raises(ValueError, match="must contain"):
            strategy.calculate_volatility(df)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        strategy = CombinedVolatilityStrategy()
        
        # Too little data
        dates = pd.date_range('2025-01-01', periods=2, freq='1h')
        df = pd.DataFrame({
            'high': [100, 101],
            'low': [99, 100],
            'close': [99.5, 100.5],
            'atr': [1.0, 1.0]
        }, index=dates)
        
        with pytest.raises(ValueError, match="at least 3 bars"):
            strategy.calculate_volatility(df)
    
    def test_get_metadata(self):
        """Test get_metadata returns complete information."""
        strategy = CombinedVolatilityStrategy()
        metadata = strategy.get_metadata()
        
        assert metadata['name'] == 'Combined (Bollinger + ATR)'
        assert 'description' in metadata
        assert 'params' in metadata
        assert 'indicators' in metadata
        assert 'source' in metadata
    
    def test_registry_integration(self):
        """Test strategy is registered in StrategyRegistry."""
        strategy = StrategyRegistry.get_volatility_strategy('combined')
        
        assert isinstance(strategy, CombinedVolatilityStrategy)
    
    def test_registry_with_params(self):
        """Test strategy creation from registry with custom params."""
        strategy = StrategyRegistry.get_volatility_strategy(
            'combined',
            bb_length=30,
            bb_std=2.5
        )
        
        assert isinstance(strategy, CombinedVolatilityStrategy)
        assert strategy.bb_length == 30
        assert strategy.bb_std == 2.5
    
    def test_bollinger_touches_reasonable(self, sample_zones):
        """Test Bollinger band touches are reasonable."""
        strategy = CombinedVolatilityStrategy()
        
        for zone in sample_zones[:5]:
            result = strategy.calculate_volatility(zone.data)
            
            # Each touch count should not exceed zone length
            # (but their sum can exceed it because some bars may touch both bands)
            zone_len = len(zone.data)
            assert result.bollinger_upper_touches <= zone_len
            assert result.bollinger_lower_touches <= zone_len


def run_tests():
    """Run all combined volatility strategy tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

