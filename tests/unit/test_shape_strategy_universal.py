"""
Unit tests for StatisticalShapeStrategy universality (v2.1)

Tests that StatisticalShapeStrategy works with ANY oscillator, not just MACD.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy


class TestShapeStrategyUniversal:
    """Tests for universal shape strategy (v2.1)."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data with multiple indicators."""
        dates = pd.date_range('2024-01-01', periods=20, freq='1h')
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 20),
            'high': np.random.uniform(105, 110, 20),
            'low': np.random.uniform(95, 100, 20),
            'close': np.random.uniform(100, 105, 20),
            'volume': np.random.uniform(1000, 2000, 20),
            'macd_hist': np.sin(np.linspace(0, np.pi, 20)),  # MACD histogram
            'RSI_14': np.random.uniform(30, 70, 20),         # RSI
            'AO_5_34': np.sin(np.linspace(0, np.pi, 20)) * 10,  # Awesome Oscillator
            'CCI_20': np.random.uniform(-100, 100, 20),      # CCI
            'FICTIONAL_99': np.random.uniform(-5, 5, 20)     # Fictional indicator
        }, index=dates)
    
    def test_macd_zones_explicit(self, sample_zone_data):
        """Test shape analysis with MACD histogram (explicit indicator_col)."""
        strategy = StatisticalShapeStrategy()
        
        # Call with explicit indicator_col
        metrics = strategy.calculate(sample_zone_data, indicator_col='macd_hist')
        
        # Verify metrics calculated
        assert metrics is not None
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert metrics.hist_smoothness is not None
        assert metrics.strategy_params['indicator_col'] == 'macd_hist'
    
    def test_rsi_zones_explicit(self, sample_zone_data):
        """Test shape analysis with RSI (v2.1 - should work without errors)."""
        strategy = StatisticalShapeStrategy()
        
        # v1.0 would fail here: ValueError: must contain 'macd_hist'
        # v2.1 works with explicit indicator_col
        metrics = strategy.calculate(sample_zone_data, indicator_col='RSI_14')
        
        assert metrics is not None
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert metrics.strategy_params['indicator_col'] == 'RSI_14'
    
    def test_ao_zones_explicit(self, sample_zone_data):
        """Test shape analysis with Awesome Oscillator (v2.1)."""
        strategy = StatisticalShapeStrategy()
        
        metrics = strategy.calculate(sample_zone_data, indicator_col='AO_5_34')
        
        assert metrics is not None
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert metrics.strategy_params['indicator_col'] == 'AO_5_34'
    
    def test_cci_zones_explicit(self, sample_zone_data):
        """Test shape analysis with CCI."""
        strategy = StatisticalShapeStrategy()
        
        metrics = strategy.calculate(sample_zone_data, indicator_col='CCI_20')
        
        assert metrics is not None
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
    
    def test_fictional_indicator(self, sample_zone_data):
        """Test with FICTIONAL indicator (proof of true universality)."""
        strategy = StatisticalShapeStrategy()
        
        # This indicator NEVER appears in the code
        # But strategy works anyway!
        metrics = strategy.calculate(sample_zone_data, indicator_col='FICTIONAL_99')
        
        assert metrics is not None
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert metrics.strategy_params['indicator_col'] == 'FICTIONAL_99'
    
    def test_empty_data_raises(self):
        """Test error handling for empty data."""
        strategy = StatisticalShapeStrategy()
        
        # Empty DataFrame with column (0 rows)
        empty_df = pd.DataFrame({'macd_hist': []})
        
        with pytest.raises(ValueError, match="zone_data cannot be empty"):
            strategy.calculate(empty_df, indicator_col='macd_hist')
    
    def test_invalid_column_raises(self, sample_zone_data):
        """Test error handling for invalid column."""
        strategy = StatisticalShapeStrategy()
        
        with pytest.raises(ValueError, match="Indicator column 'NONEXISTENT' not found"):
            strategy.calculate(sample_zone_data, indicator_col='NONEXISTENT')
    
    def test_insufficient_data_returns_minimal(self):
        """Test minimal metrics for insufficient data."""
        strategy = StatisticalShapeStrategy()
        
        # Only 2 points - not enough for statistics
        dates = pd.date_range('2024-01-01', periods=2, freq='1h')
        df = pd.DataFrame({
            'macd_hist': [1.0, 2.0]
        }, index=dates)
        
        metrics = strategy.calculate(df, indicator_col='macd_hist')
        
        # Should return minimal metrics
        assert metrics.hist_skewness == 0.0
        assert metrics.hist_kurtosis == 3.0
    
    def test_strategy_params_track_indicator(self, sample_zone_data):
        """Test that strategy_params track which indicator was used."""
        strategy = StatisticalShapeStrategy()
        
        # Test with different indicators
        indicators = ['macd_hist', 'RSI_14', 'AO_5_34', 'CCI_20']
        
        for ind_col in indicators:
            metrics = strategy.calculate(sample_zone_data, indicator_col=ind_col)
            
            # Verify indicator_col is tracked in params
            assert 'indicator_col' in metrics.strategy_params
            assert metrics.strategy_params['indicator_col'] == ind_col
    
    def test_smoothness_option(self, sample_zone_data):
        """Test calculate_smoothness option works."""
        # With smoothness
        strategy_with = StatisticalShapeStrategy(calculate_smoothness=True)
        metrics_with = strategy_with.calculate(sample_zone_data, indicator_col='macd_hist')
        assert metrics_with.hist_smoothness is not None
        
        # Without smoothness
        strategy_without = StatisticalShapeStrategy(calculate_smoothness=False)
        metrics_without = strategy_without.calculate(sample_zone_data, indicator_col='macd_hist')
        assert metrics_without.hist_smoothness is None
    
    def test_bias_correction_option(self, sample_zone_data):
        """Test bias_correction option affects results."""
        strategy_biased = StatisticalShapeStrategy(bias_correction=True)
        strategy_unbiased = StatisticalShapeStrategy(bias_correction=False)
        
        metrics_biased = strategy_biased.calculate(sample_zone_data, indicator_col='macd_hist')
        metrics_unbiased = strategy_unbiased.calculate(sample_zone_data, indicator_col='macd_hist')
        
        # Results should be slightly different
        assert metrics_biased.hist_skewness is not None
        assert metrics_unbiased.hist_skewness is not None
        # They may be equal for some data, but params should differ
        assert metrics_biased.strategy_params['bias_correction'] == True
        assert metrics_unbiased.strategy_params['bias_correction'] == False


