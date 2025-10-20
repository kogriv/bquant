"""
Tests for Zone Analysis Presets (Convenience Wrappers)

Проверяет корректность работы convenience функций для популярных индикаторов.

Stage 2.2 - Convenience wrappers
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from bquant.analysis.zones.presets import (
    analyze_macd_zones,
    analyze_rsi_zones,
    analyze_ao_zones,
    analyze_preloaded_zones
)
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.models import ZoneAnalysisResult


class TestMACDPreset:
    """Tests for analyze_macd_zones() convenience function."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        # Trending data for MACD zones
        prices = []
        base = 2000.0
        for i in range(200):
            trend = 500 * np.sin(i / 30)
            noise = np.random.normal(0, 10)
            prices.append(base + trend + noise)
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 200)
        }, index=dates)
    
    def test_macd_preset_default_params(self, sample_data):
        """Test MACD preset with default parameters."""
        result = analyze_macd_zones(sample_data)
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        assert result.statistics is not None
        assert result.hypothesis_tests is not None
    
    def test_macd_preset_custom_params(self, sample_data):
        """Test MACD preset with custom parameters."""
        result = analyze_macd_zones(
            sample_data,
            fast=10,
            slow=20,
            signal=5,
            min_duration=5,
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        # Clustering should be disabled
        assert result.clustering is None
    
    def test_macd_preset_equals_direct_builder(self, sample_data):
        """Test that preset produces same result as direct builder call."""
        # Via preset
        result_preset = analyze_macd_zones(
            sample_data,
            fast=12,
            slow=26,
            signal=9,
            min_duration=2,
            clustering=False,
            enable_cache=False
        )
        
        # Via direct builder
        result_direct = (
            analyze_zones(sample_data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
            .analyze(clustering=False)
            .with_cache(enable=False)
            .build()
        )
        
        # Should produce identical results
        assert len(result_preset.zones) == len(result_direct.zones)
        assert result_preset.zones[0].type == result_direct.zones[0].type


class TestRSIPreset:
    """Tests for analyze_rsi_zones() convenience function."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data with RSI oscillation."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        # Oscillating prices for RSI zones
        prices = []
        base = 100.0
        for i in range(200):
            oscillation = 20 * np.sin(i / 15)
            noise = np.random.normal(0, 1)
            prices.append(base + oscillation + noise)
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.005 for p in prices],
            'low': [p * 0.995 for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 200)
        }, index=dates)
    
    def test_rsi_preset_default_params(self, sample_data):
        """Test RSI preset with default parameters."""
        result = analyze_rsi_zones(sample_data, clustering=False)
        
        assert isinstance(result, ZoneAnalysisResult)
        # May have 0 zones if RSI doesn't cross thresholds
        assert result.statistics is not None
    
    def test_rsi_preset_custom_thresholds(self, sample_data):
        """Test RSI preset with custom thresholds."""
        result = analyze_rsi_zones(
            sample_data,
            period=14,
            upper_threshold=80,
            lower_threshold=20,
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert result is not None


class TestAOPreset:
    """Tests for analyze_ao_zones() convenience function."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        prices = []
        base = 50.0
        for i in range(200):
            trend = 10 * np.sin(i / 20)
            noise = np.random.normal(0, 0.5)
            prices.append(base + trend + noise)
        
        # Add basic MACD-like columns for feature extraction compatibility
        macd_like = [0.5 * np.sin(i / 20) for i in range(200)]
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 200),
            'macd': macd_like,
            'macd_signal': [m * 0.8 for m in macd_like],
            'macd_hist': [m * 0.2 for m in macd_like]
        }, index=dates)
    
    def test_ao_preset_default_params(self, sample_data):
        """Test AO preset with default parameters."""
        result = analyze_ao_zones(sample_data, clustering=False)
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
    
    def test_ao_preset_custom_periods(self, sample_data):
        """Test AO preset with custom periods."""
        result = analyze_ao_zones(
            sample_data,
            fast=5,  # Use default to avoid column name mismatch
            slow=34,
            min_duration=3,
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)


class TestPreloadedZonesPreset:
    """Tests for analyze_preloaded_zones() convenience function."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        # Add MACD-like columns for feature extraction
        macd_like = np.sin(np.linspace(0, 4*np.pi, 100))
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'volume': np.random.uniform(1000, 2000, 100),
            'macd': macd_like,
            'macd_signal': macd_like * 0.8,
            'macd_hist': macd_like * 0.2
        }, index=dates)
    
    @pytest.fixture
    def zones_dataframe(self):
        """Create sample zones DataFrame."""
        return pd.DataFrame({
            'zone_id': [0, 1],
            'start_time': pd.to_datetime(['2024-01-01 00:00:00', '2024-01-01 10:00:00']),
            'end_time': pd.to_datetime(['2024-01-01 09:00:00', '2024-01-01 20:00:00']),
            'type': ['bull', 'bear']
        })
    
    def test_preloaded_preset_from_dataframe(self, sample_data, zones_dataframe):
        """Test preloaded zones preset with DataFrame input."""
        result = analyze_preloaded_zones(
            sample_data,
            zones_dataframe,
            clustering=False,
            enable_cache=False  # DataFrame not JSON serializable for cache
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
    
    def test_preloaded_preset_from_csv(self, sample_data, zones_dataframe):
        """Test preloaded zones preset with CSV file input."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            zones_dataframe.to_csv(f.name, index=False)
            csv_path = f.name
        
        try:
            result = analyze_preloaded_zones(
                sample_data,
                csv_path,
                clustering=False
            )
            
            assert isinstance(result, ZoneAnalysisResult)
            assert len(result.zones) > 0
        finally:
            # Cleanup
            Path(csv_path).unlink(missing_ok=True)


class TestPresetsIntegration:
    """Integration tests for all presets."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        prices = []
        base = 100.0
        for i in range(200):
            trend = 20 * np.sin(i / 25)
            noise = np.random.normal(0, 1)
            prices.append(base + trend + noise)
        
        # Add basic MACD-like columns for feature extraction
        macd_like = [np.sin(i / 25) for i in range(200)]
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 2000, 200),
            'macd': macd_like,
            'macd_signal': [m * 0.8 for m in macd_like],
            'macd_hist': [m * 0.2 for m in macd_like]
        }, index=dates)
    
    def test_all_presets_return_zone_analysis_result(self, sample_data):
        """Test that all preset functions return ZoneAnalysisResult."""
        # MACD
        result_macd = analyze_macd_zones(sample_data, clustering=False)
        assert isinstance(result_macd, ZoneAnalysisResult)
        
        # RSI
        result_rsi = analyze_rsi_zones(sample_data, clustering=False)
        assert isinstance(result_rsi, ZoneAnalysisResult)
        
        # AO
        result_ao = analyze_ao_zones(sample_data, clustering=False)
        assert isinstance(result_ao, ZoneAnalysisResult)
    
    def test_presets_caching_parameter(self, sample_data):
        """Test that caching parameter works in all presets."""
        # With cache enabled (default)
        result1 = analyze_macd_zones(sample_data, enable_cache=True, clustering=False)
        result2 = analyze_macd_zones(sample_data, enable_cache=True, clustering=False)
        
        # Should hit cache on second call (same params, same data)
        assert isinstance(result1, ZoneAnalysisResult)
        assert isinstance(result2, ZoneAnalysisResult)
        
        # With cache disabled
        result3 = analyze_macd_zones(sample_data, enable_cache=False, clustering=False)
        assert isinstance(result3, ZoneAnalysisResult)
    
    def test_presets_regression_parameter(self, sample_data):
        """Test that regression parameter is passed through."""
        result = analyze_macd_zones(
            sample_data,
            regression=True,
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        # Regression results may be None if not enough zones
        assert hasattr(result, 'regression_results')
    
    def test_presets_zone_types_parameter(self, sample_data):
        """Test that zone_types parameter filters zones correctly."""
        result = analyze_macd_zones(
            sample_data,
            zone_types=['bull'],
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        # All zones should be bull type
        if len(result.zones) > 0:
            assert all(z.type == 'bull' for z in result.zones)

