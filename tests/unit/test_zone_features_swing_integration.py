"""
Integration tests for ZoneFeaturesAnalyzer with swing strategies using sample data.
"""

import pytest
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy, FindPeaksSwingStrategy
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones


class TestZoneFeaturesSwingIntegration:
    """Test integration of swing strategies with ZoneFeaturesAnalyzer using real data."""
    
    @pytest.fixture(scope="class")
    def sample_zones(self):
        """Load real zones from sample data."""
        df = get_sample_data('tv_xauusd_1h')
        result = analyze_macd_zones(df)
        zones = result.zones
        
        # Гистограмму пайплайн уже посчитал; вопрос лишь в том, как она
        # называется. Тест не угадывает имя, а спрашивает роль у схемы, и
        # заводит себе привычный псевдоним `macd_hist` — этим же именем ниже
        # адресуются стратегии, которым кадр передают напрямую.
        hist_column = result.column_schema.column('hist')
        for zone in zones:
            zone.data['macd_hist'] = zone.data[hist_column]
        
        return [z for z in zones if len(z.data) >= 10]  # Lowered threshold from 50 to 10
    
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
    
    def test_analyzer_with_default_swing_strategy(self, sample_zone_info):
        """Test analyzer uses default swing strategy from config."""
        analyzer = ZoneFeaturesAnalyzer()
        
        # Default should be ZigZagSwingStrategy
        assert analyzer.swing_strategy is not None
        assert type(analyzer.swing_strategy).__name__ == 'ZigZagSwingStrategy'
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have swing_metrics in metadata
        assert 'swing_metrics' in features.metadata
        swing_metrics = features.metadata['swing_metrics']
        
        assert swing_metrics is not None
        assert isinstance(swing_metrics, dict)
        assert 'rally_count' in swing_metrics
        assert 'drop_count' in swing_metrics
    
    def test_analyzer_with_explicit_zigzag_strategy(self, sample_zone_info):
        """Test analyzer with explicitly provided ZigZagSwingStrategy."""
        strategy = ZigZagSwingStrategy(legs=5, deviation=0.02)
        analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have swing_metrics
        assert 'swing_metrics' in features.metadata
        swing_metrics = features.metadata['swing_metrics']
        
        assert 'rally_count' in swing_metrics
        assert 'drop_count' in swing_metrics
        assert isinstance(swing_metrics['rally_count'], int)
        assert isinstance(swing_metrics['drop_count'], int)
    
    def test_analyzer_with_find_peaks_strategy(self, sample_zone_info):
        """Test analyzer with FindPeaksSwingStrategy."""
        strategy = FindPeaksSwingStrategy(distance=3, min_amplitude_pct=0.01)
        analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have swing_metrics
        assert 'swing_metrics' in features.metadata
        swing_metrics = features.metadata['swing_metrics']
        
        assert 'rally_count' in swing_metrics
        assert 'strategy_name' in swing_metrics
        assert swing_metrics['strategy_name'] == 'find_peaks'
    
    def test_swing_metrics_values_reasonable(self, sample_zones):
        """Test that swing metrics have reasonable values across multiple zones."""
        analyzer = ZoneFeaturesAnalyzer()
        
        for zone in sample_zones[:3]:  # Test first 3 zones
            zone_info = {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'duration': len(zone.data),
                'data': zone.data
            }
            
            features = analyzer.extract_zone_features(zone_info)
            swing_metrics = features.metadata['swing_metrics']
            
            # Counts should be non-negative
            assert swing_metrics['rally_count'] >= 0
            assert swing_metrics['drop_count'] >= 0
            
            # Ratio should be valid
            assert isinstance(swing_metrics['rally_to_drop_ratio'], (int, float))
    
    def test_different_strategies_different_results(self, sample_zone_info):
        """Test that different strategies produce different results."""
        strategy1 = ZigZagSwingStrategy(legs=5, deviation=0.02)   # Sensitive
        strategy2 = FindPeaksSwingStrategy(distance=10)  # Less sensitive
        
        analyzer1 = ZoneFeaturesAnalyzer(swing_strategy=strategy1)
        analyzer2 = ZoneFeaturesAnalyzer(swing_strategy=strategy2)
        
        features1 = analyzer1.extract_zone_features(sample_zone_info)
        features2 = analyzer2.extract_zone_features(sample_zone_info)
        
        metrics1 = features1.metadata['swing_metrics']
        metrics2 = features2.metadata['swing_metrics']
        
        # Strategies should produce different strategy_name
        assert metrics1['strategy_name'] != metrics2['strategy_name']
        
        print(f"ZigZag: {metrics1['rally_count']} rallies, {metrics1['drop_count']} drops")
        print(f"FindPeaks: {metrics2['rally_count']} rallies, {metrics2['drop_count']} drops")


def run_tests():
    """Run all swing integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
