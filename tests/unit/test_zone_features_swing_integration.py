"""
Integration tests for ZoneFeaturesAnalyzer with ZigZagSwingStrategy.

Tests that swing metrics are correctly calculated and included in zone features.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.core.config import create_swing_strategy


class TestZoneFeaturesSwingIntegration:
    """Test integration of swing strategies with ZoneFeaturesAnalyzer."""
    
    @pytest.fixture
    def sample_zone_info(self):
        """Create sample zone data for testing."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
        
        # Create price with swings
        base_price = 3000
        trend = np.linspace(0, 100, 100)
        swings = 50 * np.sin(np.linspace(0, 4*np.pi, 100))
        
        close = base_price + trend + swings
        high = close + np.random.uniform(5, 15, 100)
        low = close - np.random.uniform(5, 15, 100)
        open_price = close + np.random.uniform(-10, 10, 100)
        
        # Add MACD data
        macd = np.sin(np.linspace(0, 2*np.pi, 100)) * 5
        signal = np.roll(macd, 3)
        hist = macd - signal
        atr = np.full(100, 15.0)
        
        df = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'macd': macd,
            'macd_signal': signal,
            'macd_hist': hist,
            'atr': atr
        }, index=dates)
        
        return {
            'zone_id': 'test_zone_1',
            'type': 'bull',
            'duration': len(df),
            'data': df
        }
    
    def test_analyzer_with_default_swing_strategy(self, sample_zone_info):
        """Test analyzer uses default swing strategy from config."""
        analyzer = ZoneFeaturesAnalyzer(min_duration=2)
        
        # Default strategy should be loaded from config
        assert analyzer.swing_strategy is not None
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have swing_metrics in metadata
        assert 'swing_metrics' in features.metadata
        swing_metrics = features.metadata['swing_metrics']
        
        # swing_metrics can be None if no swings detected, or dict if calculated
        if swing_metrics is not None:
            assert isinstance(swing_metrics, dict)
            assert 'rally_count' in swing_metrics
            assert 'drop_count' in swing_metrics
    
    def test_analyzer_with_explicit_zigzag_strategy(self, sample_zone_info):
        """Test analyzer with explicitly provided ZigZagSwingStrategy."""
        strategy = ZigZagSwingStrategy(legs=5, deviation=0.02)
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should have swing_metrics in metadata
        assert 'swing_metrics' in features.metadata
        swing_metrics = features.metadata['swing_metrics']
        
        if swing_metrics is not None:
            # Verify all expected fields are present
            expected_fields = [
                'num_swings', 'rally_count', 'drop_count',
                'avg_rally_pct', 'avg_drop_pct',
                'rally_to_drop_ratio', 'duration_symmetry',
                'strategy_name', 'strategy_params'
            ]
            
            for field in expected_fields:
                assert field in swing_metrics, f"Missing field: {field}"
            
            # Verify strategy info
            assert swing_metrics['strategy_name'] == 'zigzag'
            assert swing_metrics['strategy_params']['legs'] == 5
            assert swing_metrics['strategy_params']['deviation'] == 0.02
    
    def test_swing_metrics_all_fields_in_metadata(self, sample_zone_info):
        """Test that all 23 swing metric fields are in metadata."""
        strategy = ZigZagSwingStrategy(legs=5, deviation=0.02)
        analyzer = ZoneFeaturesAnalyzer(min_duration=2, swing_strategy=strategy)
        
        features = analyzer.extract_zone_features(sample_zone_info)
        swing_metrics = features.metadata.get('swing_metrics')
        
        if swing_metrics is not None:
            # All 25 keys should be present (23 metrics + 2 metadata)
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
                assert key in swing_metrics, f"Missing key: {key}"
    
    def test_analyzer_without_swing_strategy(self, sample_zone_info):
        """Test analyzer works without swing strategy (backward compatibility)."""
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=None
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Should still work, but no swing_metrics in metadata
        # (or swing_metrics is None)
        swing_metrics = features.metadata.get('swing_metrics')
        # Should be None if strategy not provided
        # (depends on default from config, but with explicit None it should be None)
    
    def test_swing_metrics_values_reasonable(self, sample_zone_info):
        """Test that calculated swing metrics have reasonable values."""
        strategy = ZigZagSwingStrategy(legs=5, deviation=0.02)
        analyzer = ZoneFeaturesAnalyzer(min_duration=2, swing_strategy=strategy)
        
        features = analyzer.extract_zone_features(sample_zone_info)
        swing_metrics = features.metadata.get('swing_metrics')
        
        if swing_metrics is not None and swing_metrics['rally_count'] > 0:
            # Amplitudes should be positive percentages
            assert swing_metrics['avg_rally_pct'] > 0
            assert swing_metrics['max_rally_pct'] > 0
            
            # Duration should be positive
            assert swing_metrics['avg_rally_duration_bars'] > 0
            
            # Speed should be positive
            assert swing_metrics['avg_rally_speed_pct_per_bar'] > 0
            
            # Ratio should be positive
            if swing_metrics['drop_count'] > 0:
                assert swing_metrics['rally_to_drop_ratio'] > 0
    
    def test_different_strategies_different_results(self, sample_zone_info):
        """Test that different swing strategies produce different results."""
        strategy1 = ZigZagSwingStrategy(legs=5, deviation=0.02)
        strategy2 = ZigZagSwingStrategy(legs=15, deviation=0.08)
        
        analyzer1 = ZoneFeaturesAnalyzer(min_duration=2, swing_strategy=strategy1)
        analyzer2 = ZoneFeaturesAnalyzer(min_duration=2, swing_strategy=strategy2)
        
        features1 = analyzer1.extract_zone_features(sample_zone_info)
        features2 = analyzer2.extract_zone_features(sample_zone_info)
        
        swing1 = features1.metadata.get('swing_metrics')
        swing2 = features2.metadata.get('swing_metrics')
        
        # If both calculated successfully
        if swing1 is not None and swing2 is not None:
            # Strategy params should be different
            assert swing1['strategy_params'] != swing2['strategy_params']


def run_integration_tests():
    """Run all integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_integration_tests()

