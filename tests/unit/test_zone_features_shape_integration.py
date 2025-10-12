"""
Integration tests for ZoneFeaturesAnalyzer with StatisticalShapeStrategy using sample data.
"""

import pytest
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestZoneFeaturesShapeIntegration:
    """Test integration of shape strategies with ZoneFeaturesAnalyzer using real data."""
    
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
    def sample_zone_info(self, sample_zones):
        """Get first zone as test data."""
        if not sample_zones:
            pytest.skip("No zones in sample data")
        
        zone = sample_zones[0]
        return {
            'zone_id': zone.zone_id,
            'type': zone.type,
            'duration': len(zone.data),
            'data': zone.data
        }
    
    def test_analyzer_with_default_shape_strategy(self, sample_zone_info):
        """Test analyzer uses default shape strategy from config."""
        analyzer = ZoneFeaturesAnalyzer(min_duration=2)
        
        # Default should be 'statistical' after Phase 3.2
        assert analyzer.shape_strategy is not None
        assert type(analyzer.shape_strategy).__name__ == 'StatisticalShapeStrategy'
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have shape_metrics in metadata
        assert 'shape_metrics' in features.metadata
        shape_metrics = features.metadata['shape_metrics']
        
        assert shape_metrics is not None
        assert isinstance(shape_metrics, dict)
        assert 'hist_skewness' in shape_metrics
        assert 'hist_kurtosis' in shape_metrics
        assert 'hist_smoothness' in shape_metrics
    
    def test_analyzer_with_explicit_strategy(self, sample_zone_info):
        """Test analyzer with explicitly provided shape strategy."""
        shape_strategy = StatisticalShapeStrategy(calculate_smoothness=False)
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            shape_strategy=shape_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have shape_metrics
        assert 'shape_metrics' in features.metadata
        shape_metrics = features.metadata['shape_metrics']
        
        assert 'hist_skewness' in shape_metrics
        assert 'hist_kurtosis' in shape_metrics
        assert isinstance(shape_metrics['hist_skewness'], (int, float))
        assert isinstance(shape_metrics['hist_kurtosis'], (int, float))
    
    def test_shape_metrics_values_reasonable(self, sample_zones):
        """Test that shape metrics have reasonable values across multiple zones."""
        analyzer = ZoneFeaturesAnalyzer(min_duration=2)
        
        for zone in sample_zones[:5]:  # Test first 5 zones
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            shape_metrics = features.metadata['shape_metrics']
            
            # Skewness typically ranges from -3 to +3 for most distributions
            assert -10 < shape_metrics['hist_skewness'] < 10, \
                f"Skewness {shape_metrics['hist_skewness']} seems unreasonable"
            
            # Kurtosis typically ranges from -2 (uniform) to ~10+ (heavy tails)
            assert -10 < shape_metrics['hist_kurtosis'] < 50, \
                f"Kurtosis {shape_metrics['hist_kurtosis']} seems unreasonable"
    
    def test_analyzer_with_both_strategies(self, sample_zone_info):
        """Test analyzer with both swing and shape strategies."""
        from bquant.analysis.zones.strategies.swing import FindPeaksSwingStrategy
        
        swing_strategy = FindPeaksSwingStrategy(distance=3)
        shape_strategy = StatisticalShapeStrategy()
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=swing_strategy,
            shape_strategy=shape_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have both swing and shape metrics
        assert 'swing_metrics' in features.metadata
        assert 'shape_metrics' in features.metadata
        
        swing_metrics = features.metadata['swing_metrics']
        shape_metrics = features.metadata['shape_metrics']
        
        # Verify both are populated
        assert 'rally_count' in swing_metrics
        assert 'hist_skewness' in shape_metrics


def run_tests():
    """Run all shape integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
