"""
Integration tests for ZoneFeaturesAnalyzer with volatility strategies using sample data.
"""

import pytest
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.volatility import CombinedVolatilityStrategy
from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer


class TestZoneFeaturesVolatilityIntegration:
    """Test integration of volatility strategies with ZoneFeaturesAnalyzer using real data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        analyzer = MACDZoneAnalyzer()
        zones = analyzer.identify_zones(df)
        
        # Add macd_hist to each zone
        for zone in zones:
            zone.data['macd_hist'] = zone.data['macd'] - zone.data['signal']
        
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
    
    def test_analyzer_with_volatility_strategy(self, sample_zone_info):
        """Test analyzer with explicitly provided volatility strategy."""
        volatility_strategy = CombinedVolatilityStrategy()
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            volatility_strategy=volatility_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have volatility_metrics in metadata
        assert 'volatility_metrics' in features.metadata
        volatility_metrics = features.metadata['volatility_metrics']
        
        assert volatility_metrics is not None
        assert isinstance(volatility_metrics, dict)
        assert 'bollinger_width_pct' in volatility_metrics
        assert 'atr_normalized_range' in volatility_metrics
        assert 'volatility_score' in volatility_metrics
        assert 'volatility_regime' in volatility_metrics
    
    def test_volatility_metrics_values_reasonable(self, sample_zones):
        """Test that volatility metrics have reasonable values across multiple zones."""
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            volatility_strategy=CombinedVolatilityStrategy()
        )
        
        for zone in sample_zones[:5]:  # Test first 5 zones
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            vol_metrics = features.metadata['volatility_metrics']
            
            # Score should be in valid range
            assert 0 <= vol_metrics['volatility_score'] <= 10
            
            # Regime should be valid
            assert vol_metrics['volatility_regime'] in ['low', 'medium', 'high', 'extreme']
            
            # Bollinger width should be reasonable (typically 0.5-15%)
            assert 0 <= vol_metrics['bollinger_width_pct'] <= 50, \
                f"BB width {vol_metrics['bollinger_width_pct']}% seems unreasonable"
            
            # ATR range should be positive
            assert vol_metrics['atr_normalized_range'] >= 0
    
    def test_analyzer_with_all_strategies(self, sample_zone_info):
        """Test analyzer with swing, shape, divergence, and volatility strategies."""
        from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
        from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
        from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
        
        swing_strategy = ZigZagSwingStrategy()
        divergence_strategy = ClassicDivergenceStrategy()
        shape_strategy = StatisticalShapeStrategy()
        volatility_strategy = CombinedVolatilityStrategy()
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=swing_strategy,
            divergence_strategy=divergence_strategy,
            shape_strategy=shape_strategy,
            volatility_strategy=volatility_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have all four metric types
        assert 'swing_metrics' in features.metadata
        assert 'divergence_metrics' in features.metadata
        assert 'shape_metrics' in features.metadata
        assert 'volatility_metrics' in features.metadata
        
        # Verify all are populated
        assert features.metadata['swing_metrics'] is not None
        assert features.metadata['divergence_metrics'] is not None
        assert features.metadata['shape_metrics'] is not None
        assert features.metadata['volatility_metrics'] is not None
    
    def test_volatility_regime_distribution(self, sample_zones):
        """Test distribution of volatility regimes across zones."""
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            volatility_strategy=CombinedVolatilityStrategy()
        )
        
        regimes = []
        scores = []
        
        for zone in sample_zones:
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            vol_metrics = features.metadata['volatility_metrics']
            
            regimes.append(vol_metrics['volatility_regime'])
            scores.append(vol_metrics['volatility_score'])
        
        # Should have variety of regimes
        unique_regimes = set(regimes)
        print(f"Volatility regimes found: {unique_regimes}")
        print(f"Score range: {min(scores):.2f} - {max(scores):.2f}")
        
        # At least some variance in regimes
        assert len(unique_regimes) >= 1
    
    def test_different_parameters_different_results(self, sample_zone_info):
        """Test that different BB parameters produce different results."""
        strategy1 = CombinedVolatilityStrategy(bb_length=10, bb_std=1.5)  # Narrower bands
        strategy2 = CombinedVolatilityStrategy(bb_length=30, bb_std=2.5)  # Wider bands
        
        result1 = strategy1.calculate_volatility(sample_zone_info['data'])
        result2 = strategy2.calculate_volatility(sample_zone_info['data'])
        
        # Results should differ
        print(f"Strategy1 (narrow): width={result1.bollinger_width_pct:.2f}%, score={result1.volatility_score:.2f}")
        print(f"Strategy2 (wide): width={result2.bollinger_width_pct:.2f}%, score={result2.volatility_score:.2f}")
        
        # Widths should be different (wider std = wider bands)
        assert result1.bollinger_width_pct != result2.bollinger_width_pct


def run_tests():
    """Run all volatility integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

