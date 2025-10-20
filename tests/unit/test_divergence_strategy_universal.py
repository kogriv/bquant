"""
Unit tests for ClassicDivergenceStrategy universality (v2.1)

Tests that ClassicDivergenceStrategy works with ANY oscillator, not just MACD.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy


class TestDivergenceStrategyUniversal:
    """Tests for universal divergence strategy (v2.1)."""
    
    @pytest.fixture
    def sample_divergence_data(self):
        """Create sample data with divergence patterns for multiple indicators."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        # Create price with trend
        close_prices = 100 + np.linspace(0, 10, 100) + np.random.uniform(-1, 1, 100)
        high_prices = close_prices + np.random.uniform(0.5, 2, 100)
        low_prices = close_prices - np.random.uniform(0.5, 2, 100)
        
        # MACD histogram - create divergence pattern
        macd_hist = -np.linspace(0, 5, 100) + np.random.uniform(-0.5, 0.5, 100)
        
        # RSI - also with divergence
        rsi = 50 - np.linspace(0, 20, 100) + np.random.uniform(-2, 2, 100)
        
        # AO
        ao = np.sin(np.linspace(0, 4*np.pi, 100)) * 10
        
        # Stochastic (2 lines)
        stoch_k = np.random.uniform(20, 80, 100)
        stoch_d = stoch_k * 0.9 + np.random.uniform(-5, 5, 100)
        
        return pd.DataFrame({
            'open': close_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(1000, 2000, 100),
            'macd_hist': macd_hist,
            'macd': macd_hist * 0.8,
            'RSI_14': rsi,
            'AO_5_34': ao,
            'STOCHk_14_3_3': stoch_k,
            'STOCHd_14_3_3': stoch_d,
            'FICTIONAL_99': np.random.uniform(-5, 5, 100)
        }, index=dates)
    
    def test_macd_divergence_explicit(self, sample_divergence_data):
        """Test divergence detection with MACD histogram (single line)."""
        strategy = ClassicDivergenceStrategy()
        
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='macd_hist'
        )
        
        assert metrics is not None
        assert metrics.strategy_name == 'classic'
        assert metrics.strategy_params['indicator_col'] == 'macd_hist'
        assert metrics.strategy_params['indicator_line_col'] is None
    
    def test_macd_2line_divergence_explicit(self, sample_divergence_data):
        """Test divergence detection with MACD (two lines)."""
        strategy = ClassicDivergenceStrategy()
        
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='macd_hist',
            indicator_line_col='macd'
        )
        
        assert metrics is not None
        assert metrics.strategy_params['indicator_col'] == 'macd_hist'
        assert metrics.strategy_params['indicator_line_col'] == 'macd'
    
    def test_rsi_divergence_explicit(self, sample_divergence_data):
        """Test divergence detection with RSI (v2.1 - should work without errors)."""
        strategy = ClassicDivergenceStrategy()
        
        # v1.0 would fail: ValueError: must contain 'macd_hist'
        # v2.1 works with explicit indicator_col
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='RSI_14'
        )
        
        assert metrics is not None
        assert metrics.divergence_count >= 0
        assert metrics.strategy_params['indicator_col'] == 'RSI_14'
    
    def test_ao_divergence_explicit(self, sample_divergence_data):
        """Test divergence detection with Awesome Oscillator (v2.1)."""
        strategy = ClassicDivergenceStrategy()
        
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='AO_5_34'
        )
        
        assert metrics is not None
        assert metrics.strategy_params['indicator_col'] == 'AO_5_34'
    
    def test_stochastic_2line_divergence(self, sample_divergence_data):
        """Test 2-line divergence with Stochastic."""
        strategy = ClassicDivergenceStrategy()
        
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='STOCHk_14_3_3',
            indicator_line_col='STOCHd_14_3_3'
        )
        
        assert metrics is not None
        assert metrics.strategy_params['indicator_col'] == 'STOCHk_14_3_3'
        assert metrics.strategy_params['indicator_line_col'] == 'STOCHd_14_3_3'
    
    def test_fictional_indicator_divergence(self, sample_divergence_data):
        """Test with FICTIONAL indicator (proof of true universality)."""
        strategy = ClassicDivergenceStrategy()
        
        # This indicator NEVER appears in the code
        # But strategy works anyway!
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='FICTIONAL_99'
        )
        
        assert metrics is not None
        assert metrics.strategy_params['indicator_col'] == 'FICTIONAL_99'
    
    def test_empty_data_raises(self):
        """Test error handling for empty data."""
        strategy = ClassicDivergenceStrategy()
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="Zone data cannot be empty"):
            strategy.calculate_divergence(empty_df, indicator_col='macd_hist')
    
    def test_invalid_column_raises(self, sample_divergence_data):
        """Test error handling for invalid indicator column."""
        strategy = ClassicDivergenceStrategy()
        
        with pytest.raises(ValueError, match="Zone data must contain columns"):
            strategy.calculate_divergence(
                sample_divergence_data,
                indicator_col='NONEXISTENT'
            )
    
    def test_missing_signal_line_raises(self, sample_divergence_data):
        """Test error handling when signal line column is missing."""
        strategy = ClassicDivergenceStrategy()
        
        with pytest.raises(ValueError, match="Zone data must contain columns"):
            strategy.calculate_divergence(
                sample_divergence_data,
                indicator_col='macd_hist',
                indicator_line_col='NONEXISTENT_LINE'
            )
    
    def test_insufficient_data_returns_empty(self):
        """Test minimal metrics for insufficient data."""
        strategy = ClassicDivergenceStrategy(min_peak_distance=5)
        
        # Only 8 bars - not enough for divergence (need at least min_peak_distance * 2)
        dates = pd.date_range('2024-01-01', periods=8, freq='1h')
        df = pd.DataFrame({
            'open': [100] * 8,
            'high': [102] * 8,
            'low': [98] * 8,
            'close': [100] * 8,
            'macd_hist': [1.0] * 8
        }, index=dates)
        
        metrics = strategy.calculate_divergence(df, indicator_col='macd_hist')
        
        # Should return empty metrics
        assert metrics.divergence_count == 0
        assert metrics.divergence_type == 'none'
        assert metrics.divergence_direction == 'none'
    
    def test_strategy_params_track_indicators(self, sample_divergence_data):
        """Test that strategy_params track which indicators were used."""
        strategy = ClassicDivergenceStrategy()
        
        # Test with different indicators
        test_cases = [
            ('macd_hist', None),
            ('RSI_14', None),
            ('AO_5_34', None),
            ('STOCHk_14_3_3', 'STOCHd_14_3_3')
        ]
        
        for ind_col, ind_line_col in test_cases:
            metrics = strategy.calculate_divergence(
                sample_divergence_data,
                indicator_col=ind_col,
                indicator_line_col=ind_line_col
            )
            
            # Verify indicators are tracked in params
            assert metrics.strategy_params['indicator_col'] == ind_col
            assert metrics.strategy_params['indicator_line_col'] == ind_line_col
    
    def test_divergence_metrics_structure(self, sample_divergence_data):
        """Test that DivergenceMetrics structure is correct."""
        strategy = ClassicDivergenceStrategy()
        
        metrics = strategy.calculate_divergence(
            sample_divergence_data,
            indicator_col='macd_hist'
        )
        
        # Verify all required fields exist
        assert hasattr(metrics, 'divergence_type')
        assert hasattr(metrics, 'divergence_count')
        assert hasattr(metrics, 'divergence_strength')
        assert hasattr(metrics, 'divergence_direction')
        assert hasattr(metrics, 'strategy_name')
        assert hasattr(metrics, 'strategy_params')
        
        # Verify types
        assert isinstance(metrics.divergence_count, int)
        assert isinstance(metrics.divergence_strength, float)
        assert metrics.divergence_type in ['regular', 'hidden', 'none']
        assert metrics.divergence_direction in ['bullish', 'bearish', 'mixed', 'none']


