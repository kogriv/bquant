"""
Unit tests for StandardVolumeStrategy universality (v2.1)

Tests that StandardVolumeStrategy works with ANY oscillator for correlation, not just MACD.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy


class TestVolumeStrategyUniversal:
    """Tests for universal volume strategy (v2.1)."""
    
    @pytest.fixture
    def sample_volume_data(self):
        """Create sample zone data with volume and multiple indicators."""
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        
        volume = np.random.uniform(1000, 2000, 50)
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 50),
            'high': np.random.uniform(105, 110, 50),
            'low': np.random.uniform(95, 100, 50),
            'close': np.random.uniform(100, 105, 50),
            'volume': volume,
            'macd_hist': np.sin(np.linspace(0, np.pi, 50)),
            'RSI_14': np.random.uniform(30, 70, 50),
            'AO_5_34': np.sin(np.linspace(0, np.pi, 50)) * 10,
            'CCI_20': np.random.uniform(-100, 100, 50),
            'FICTIONAL_99': np.random.uniform(-5, 5, 50)
        }, index=dates)
    
    def test_volume_without_indicator(self, sample_volume_data):
        """Test volume analysis without indicator correlation (backward compatible)."""
        strategy = StandardVolumeStrategy()
        
        metrics = strategy.calculate_volume(sample_volume_data, baseline_volume=1500)
        
        assert metrics is not None
        assert metrics.volume_zone_ratio is not None
        assert metrics.volume_at_entry_change is not None
        assert metrics.volume_indicator_corr is None  # No indicator provided
        assert metrics.avg_volume_zone is not None
        assert metrics.strategy_params['indicator_col'] is None
    
    def test_volume_with_macd_correlation(self, sample_volume_data):
        """Test volume-MACD correlation (legacy, backward compatible)."""
        strategy = StandardVolumeStrategy()
        
        metrics = strategy.calculate_volume(
            sample_volume_data, 
            baseline_volume=1500,
            indicator_col='macd_hist'
        )
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is not None
        assert -1 <= metrics.volume_indicator_corr <= 1
        assert metrics.strategy_params['indicator_col'] == 'macd_hist'
    
    def test_volume_with_rsi_correlation(self, sample_volume_data):
        """Test volume-RSI correlation (v2.1 - new capability)."""
        strategy = StandardVolumeStrategy()
        
        # v1.0: volume_macd_corr only available for MACD
        # v2.1: volume_indicator_corr works with any oscillator
        metrics = strategy.calculate_volume(
            sample_volume_data,
            baseline_volume=1500,
            indicator_col='RSI_14'
        )
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is not None
        assert -1 <= metrics.volume_indicator_corr <= 1
        assert metrics.strategy_params['indicator_col'] == 'RSI_14'
    
    def test_volume_with_ao_correlation(self, sample_volume_data):
        """Test volume-AO correlation (v2.1)."""
        strategy = StandardVolumeStrategy()
        
        metrics = strategy.calculate_volume(
            sample_volume_data,
            baseline_volume=1500,
            indicator_col='AO_5_34'
        )
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is not None
        assert metrics.strategy_params['indicator_col'] == 'AO_5_34'
    
    def test_volume_with_fictional_indicator(self, sample_volume_data):
        """Test with FICTIONAL indicator (proof of universality)."""
        strategy = StandardVolumeStrategy()
        
        # This indicator NEVER appears in the code
        # But strategy works anyway!
        metrics = strategy.calculate_volume(
            sample_volume_data,
            baseline_volume=1500,
            indicator_col='FICTIONAL_99'
        )
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is not None
        assert metrics.strategy_params['indicator_col'] == 'FICTIONAL_99'
    
    def test_volume_indicator_corr_renamed(self, sample_volume_data):
        """Test that old field volume_macd_corr no longer exists."""
        strategy = StandardVolumeStrategy()
        
        metrics = strategy.calculate_volume(
            sample_volume_data,
            baseline_volume=1500,
            indicator_col='macd_hist'
        )
        
        # v2.1: field renamed
        assert hasattr(metrics, 'volume_indicator_corr')
        assert not hasattr(metrics, 'volume_macd_corr')  # Old field removed
    
    def test_volume_without_indicator_graceful(self, sample_volume_data):
        """Test graceful handling when indicator_col not provided."""
        strategy = StandardVolumeStrategy()
        
        # No indicator_col - correlation should be None
        metrics = strategy.calculate_volume(sample_volume_data, baseline_volume=1500)
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is None
        assert metrics.volume_zone_ratio is not None
        assert metrics.avg_volume_zone is not None
    
    def test_volume_invalid_indicator_graceful(self, sample_volume_data):
        """Test graceful handling when indicator column doesn't exist."""
        strategy = StandardVolumeStrategy()
        
        # indicator_col doesn't exist - correlation should be None
        metrics = strategy.calculate_volume(
            sample_volume_data,
            baseline_volume=1500,
            indicator_col='NONEXISTENT'
        )
        
        assert metrics is not None
        assert metrics.volume_indicator_corr is None  # Graceful degradation
        assert metrics.volume_zone_ratio is not None
    
    def test_empty_data_raises(self):
        """Test error handling for empty data."""
        strategy = StandardVolumeStrategy()
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="Zone data cannot be empty"):
            strategy.calculate_volume(empty_df, baseline_volume=1500)
    
    def test_missing_volume_column_raises(self):
        """Test error handling for missing volume column."""
        strategy = StandardVolumeStrategy()
        
        dates = pd.date_range('2024-01-01', periods=10, freq='1h')
        df = pd.DataFrame({
            'close': [100] * 10,
            'macd_hist': [1.0] * 10
        }, index=dates)
        
        with pytest.raises(ValueError, match="must contain 'volume' column"):
            strategy.calculate_volume(df, baseline_volume=1500)
    
    def test_strategy_params_track_indicator(self, sample_volume_data):
        """Test that strategy_params track which indicator was used."""
        strategy = StandardVolumeStrategy()
        
        # Test with different indicators
        indicators = ['macd_hist', 'RSI_14', 'AO_5_34', 'CCI_20', None]
        
        for ind_col in indicators:
            metrics = strategy.calculate_volume(
                sample_volume_data,
                baseline_volume=1500,
                indicator_col=ind_col
            )
            
            # Verify indicator_col is tracked in params
            assert 'indicator_col' in metrics.strategy_params
            assert metrics.strategy_params['indicator_col'] == ind_col
    
    def test_correlation_min_periods(self):
        """Test correlation_min_periods option."""
        strategy = StandardVolumeStrategy(correlation_min_periods=5)
        
        # Only 4 data points - not enough for correlation with min_periods=5
        dates = pd.date_range('2024-01-01', periods=4, freq='1h')
        df = pd.DataFrame({
            'volume': [1000, 1100, 1200, 1300],
            'macd_hist': [1.0, 1.5, 2.0, 2.5]
        }, index=dates)
        
        metrics = strategy.calculate_volume(df, baseline_volume=1500, indicator_col='macd_hist')
        
        # Should not calculate correlation (insufficient data)
        assert metrics.volume_indicator_corr is None
    
    def test_nan_correlation_handling(self):
        """Test handling of NaN correlation."""
        strategy = StandardVolumeStrategy()
        
        # Constant volume - correlation will be NaN
        dates = pd.date_range('2024-01-01', periods=10, freq='1h')
        df = pd.DataFrame({
            'volume': [1000] * 10,  # Constant
            'macd_hist': [1.0, 2.0, 3.0, 4.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0]
        }, index=dates)
        
        metrics = strategy.calculate_volume(df, baseline_volume=1500, indicator_col='macd_hist')
        
        # NaN correlation should be converted to None
        assert metrics.volume_indicator_corr is None


