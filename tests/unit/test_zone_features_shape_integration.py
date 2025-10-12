"""
Integration tests for ZoneFeaturesAnalyzer with StatisticalShapeStrategy.

Tests that shape metrics are correctly calculated and included in zone features.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
# Import swing strategies to register them (needed for default config)
from bquant.analysis.zones.strategies.swing import (
    ZigZagSwingStrategy,
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy
)


class TestZoneFeaturesShapeIntegration:
    """Test integration of shape strategies with ZoneFeaturesAnalyzer."""
    
    @pytest.fixture
    def sample_zone_info(self):
        """Create sample zone data."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
        
        # Create MACD histogram with interesting shape
        x = np.linspace(-2, 2, 100)
        hist = 5 * np.exp(-x**2 / 2) * (1 + 0.3 * x)  # Slightly skewed Gaussian
        
        # Price data
        close = 3000 + 50 * np.sin(x) + np.random.uniform(-2, 2, 100)
        high = close + np.random.uniform(5, 10, 100)
        low = close - np.random.uniform(5, 10, 100)
        
        # Other required fields
        macd = hist * 0.5
        signal = np.roll(macd, 2)
        atr = np.full(100, 15.0)
        
        df = pd.DataFrame({
            'open': close,
            'high': high,
            'low': low,
            'close': close,
            'macd': macd,
            'macd_signal': signal,
            'macd_hist': hist,
            'atr': atr
        }, index=dates)
        
        return {
            'zone_id': 'test_zone_shape',
            'type': 'bull',
            'duration': len(df),
            'data': df
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
        """Test analyzer with explicitly provided strategy."""
        strategy = StatisticalShapeStrategy(
            calculate_smoothness=False,
            bias_correction=False
        )
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            shape_strategy=strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        shape_metrics = features.metadata['shape_metrics']
        
        assert shape_metrics is not None
        assert shape_metrics['hist_smoothness'] is None  # Disabled
        assert shape_metrics['strategy_params']['calculate_smoothness'] is False
    
    def test_shape_metrics_values_reasonable(self, sample_zone_info):
        """Test that calculated shape metrics have reasonable values."""
        strategy = StatisticalShapeStrategy()
        analyzer = ZoneFeaturesAnalyzer(min_duration=2, shape_strategy=strategy)
        
        features = analyzer.extract_zone_features(sample_zone_info)
        shape_metrics = features.metadata['shape_metrics']
        
        assert shape_metrics is not None
        
        # Skewness should be finite
        assert isinstance(shape_metrics['hist_skewness'], (int, float))
        assert not np.isnan(shape_metrics['hist_skewness'])
        assert not np.isinf(shape_metrics['hist_skewness'])
        
        # Kurtosis should be positive
        assert shape_metrics['hist_kurtosis'] > 0
        
        # Smoothness should be non-negative
        if shape_metrics['hist_smoothness'] is not None:
            assert shape_metrics['hist_smoothness'] >= 0
    
    def test_analyzer_with_both_strategies(self, sample_zone_info):
        """Test analyzer with both swing and shape strategies."""
        from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
        
        swing_strategy = ZigZagSwingStrategy(legs=10, deviation=0.05)
        shape_strategy = StatisticalShapeStrategy(calculate_smoothness=True)
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=swing_strategy,
            shape_strategy=shape_strategy
        )
        
        features = analyzer.extract_zone_features(sample_zone_info)
        
        # Both metrics should be present
        assert 'swing_metrics' in features.metadata
        assert 'shape_metrics' in features.metadata
        
        # Both should be calculated (or None if failed)
        swing = features.metadata['swing_metrics']
        shape = features.metadata['shape_metrics']
        
        # Shape should definitely be calculated
        assert shape is not None
        assert 'hist_skewness' in shape
        assert 'hist_kurtosis' in shape


def run_tests():
    """Run all integration tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()

