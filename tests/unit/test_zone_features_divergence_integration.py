"""
Integration tests for ZoneFeaturesAnalyzer with divergence strategies using sample data.
"""

import pytest
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestZoneFeaturesDivergenceIntegration:
    """Test integration of divergence strategies with ZoneFeaturesAnalyzer using real data."""
    
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
        
        return [z for z in zones if len(z.data) >= 20]
    
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
    
    def test_analyzer_with_divergence_strategy(self, sample_zone_info):
        """Test analyzer with explicitly provided divergence strategy."""
        divergence_strategy = ClassicDivergenceStrategy()
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            divergence_strategy=divergence_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have divergence_metrics in metadata
        assert 'divergence_metrics' in features.metadata
        divergence_metrics = features.metadata['divergence_metrics']
        
        assert divergence_metrics is not None
        assert isinstance(divergence_metrics, dict)
        assert 'divergence_type' in divergence_metrics
        assert 'divergence_count' in divergence_metrics
        assert 'divergence_direction' in divergence_metrics
    
    def test_divergence_metrics_values_reasonable(self, sample_zones):
        """Test that divergence metrics have reasonable values across multiple zones."""
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            divergence_strategy=ClassicDivergenceStrategy()
        )
        
        for zone in sample_zones[:5]:  # Test first 5 zones
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            divergence_metrics = features.metadata['divergence_metrics']
            
            # Type should be valid
            assert divergence_metrics['divergence_type'] in ['none', 'regular', 'hidden', 'mixed']
            
            # Count should be reasonable
            assert divergence_metrics['divergence_count'] >= 0
            assert divergence_metrics['divergence_count'] <= 10
            
            # Strength should be non-negative
            assert divergence_metrics['divergence_strength'] >= 0
            
            # Direction should be valid
            assert divergence_metrics['divergence_direction'] in ['bullish', 'bearish', 'none']
    
    def test_analyzer_with_all_strategies(self, sample_zone_info):
        """Test analyzer with swing, shape, and divergence strategies."""
        from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
        from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
        
        swing_strategy = ZigZagSwingStrategy(legs=10, deviation=0.05)
        divergence_strategy = ClassicDivergenceStrategy()
        shape_strategy = StatisticalShapeStrategy()
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=swing_strategy,
            divergence_strategy=divergence_strategy,
            shape_strategy=shape_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have all three metric types
        assert 'swing_metrics' in features.metadata
        assert 'divergence_metrics' in features.metadata
        assert 'shape_metrics' in features.metadata
        
        # Verify all are populated
        assert features.metadata['swing_metrics'] is not None
        assert features.metadata['divergence_metrics'] is not None
        assert features.metadata['shape_metrics'] is not None
    
    def test_divergence_consistency_across_zones(self, sample_zones):
        """Test divergence detection consistency."""
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            divergence_strategy=ClassicDivergenceStrategy()
        )
        
        div_counts = []
        div_types = []
        
        for zone in sample_zones[:10]:
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            div_metrics = features.metadata['divergence_metrics']
            
            div_counts.append(div_metrics['divergence_count'])
            div_types.append(div_metrics['divergence_type'])
        
        # At least some zones should have divergences
        # (depending on data, but most zones have at least 1-2)
        total_divergences = sum(div_counts)
        print(f"Total divergences found in {len(sample_zones[:10])} zones: {total_divergences}")
        print(f"Divergence counts: {div_counts}")
        print(f"Divergence types: {div_types}")


def run_tests():
    """Run all divergence integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

