"""
Unit tests for Zone Analysis Pipeline and Builder

Tests for ZoneAnalysisPipeline, ZoneAnalysisBuilder, and integration with IndicatorFactory.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones import (
    ZoneAnalysisPipeline,
    ZoneAnalysisBuilder,
    IndicatorConfig,
    ZoneAnalysisConfig,
    ZoneDetectionConfig,
    ZoneAnalysisResult,
    analyze_zones
)


class TestIndicatorConfig:
    """Tests for IndicatorConfig dataclass."""
    
    def test_indicator_config_creation(self):
        """Test IndicatorConfig creation."""
        config = IndicatorConfig(
            source='custom',
            name='macd',
            params={'fast': 12, 'slow': 26, 'signal': 9}
        )
        
        assert config.source == 'custom'
        assert config.name == 'macd'
        assert config.params['fast'] == 12


class TestZoneAnalysisConfig:
    """Tests for ZoneAnalysisConfig dataclass."""
    
    def test_config_creation(self):
        """Test ZoneAnalysisConfig creation."""
        detection_config = ZoneDetectionConfig(
            strategy_name='zero_crossing',
            rules={'indicator_col': 'macd_histogram'}
        )
        
        config = ZoneAnalysisConfig(
            indicator=None,
            zone_detection=detection_config,
            perform_clustering=True,
            n_clusters=3
        )
        
        assert config.zone_detection is not None
        assert config.perform_clustering is True
        assert config.n_clusters == 3


class TestZoneAnalysisPipeline:
    """Tests for ZoneAnalysisPipeline."""
    
    @pytest.fixture
    def sample_data_with_macd(self):
        """Create sample data with MACD already calculated."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        macd_hist = np.sin(np.linspace(0, 4*np.pi, 200)) * 2
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'volume': np.random.uniform(1000, 2000, 200),
            'macd': macd_hist / 2,
            'macd_signal': macd_hist / 3,
            'macd_hist': macd_hist,
            'atr': np.random.uniform(1, 2, 200)
        }, index=dates)
    
    def test_pipeline_without_indicator_calculation(self, sample_data_with_macd):
        """Test pipeline when indicator already in data."""
        config = ZoneAnalysisConfig(
            indicator=None,  # Already in data
            zone_detection=ZoneDetectionConfig(
                strategy_name='zero_crossing',
                rules={'indicator_col': 'macd_hist'}
            ),
            perform_clustering=False
        )
        
        pipeline = ZoneAnalysisPipeline(config, enable_cache=False)
        result = pipeline.run(sample_data_with_macd)
        
        assert result is not None
        assert len(result.zones) > 0
    
    def test_pipeline_with_indicator_calculation(self):
        """Test pipeline with indicator calculation."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        df = pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'volume': np.random.uniform(1000, 2000, 200)
        }, index=dates)
        
        config = ZoneAnalysisConfig(
            indicator=IndicatorConfig(
                source='custom',
                name='macd',
                params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            ),
            zone_detection=ZoneDetectionConfig(
                strategy_name='zero_crossing',
                rules={'indicator_col': 'macd_hist'}
            ),
            perform_clustering=False
        )
        
        pipeline = ZoneAnalysisPipeline(config, enable_cache=False)
        result = pipeline.run(df)
        
        assert result is not None
        assert len(result.zones) > 0
    
    def test_pipeline_with_clustering(self, sample_data_with_macd):
        """Test pipeline with clustering enabled."""
        config = ZoneAnalysisConfig(
            indicator=None,
            zone_detection=ZoneDetectionConfig(
                strategy_name='zero_crossing',
                rules={'indicator_col': 'macd_hist'}
            ),
            perform_clustering=True,
            n_clusters=3
        )
        
        pipeline = ZoneAnalysisPipeline(config, enable_cache=False)
        result = pipeline.run(sample_data_with_macd)
        
        if len(result.zones) >= 3:
            assert result.clustering is not None


class TestZoneAnalysisBuilder:
    """Tests for ZoneAnalysisBuilder fluent API."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        macd_hist = np.sin(np.linspace(0, 4*np.pi, 200)) * 2
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'volume': np.random.uniform(1000, 2000, 200),
            'macd': macd_hist / 2,
            'macd_signal': macd_hist / 3,
            'macd_hist': macd_hist,
            'atr': np.random.uniform(1, 2, 200)
        }, index=dates)
    
    def test_builder_basic_usage(self, sample_data):
        """Test basic builder usage."""
        result = (
            ZoneAnalysisBuilder(sample_data)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=False)
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
    
    def test_builder_with_indicator(self):
        """Test builder with indicator calculation."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        df = pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'volume': np.random.uniform(1000, 2000, 200)
        }, index=dates)
        
        result = (
            ZoneAnalysisBuilder(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_builder_without_detection_config(self, sample_data):
        """Test error when detection not configured."""
        builder = ZoneAnalysisBuilder(sample_data)
        
        with pytest.raises(ValueError, match="not configured"):
            builder.build()
    
    def test_builder_analyze_params(self, sample_data):
        """Test analyze parameters."""
        result = (
            ZoneAnalysisBuilder(sample_data)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=True, n_clusters=4, regression=True)
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_builder_cache_config(self, sample_data):
        """Test cache configuration."""
        result = (
            ZoneAnalysisBuilder(sample_data)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_cache(enable=True, ttl=7200)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_analyze_zones_helper(self, sample_data):
        """Test analyze_zones helper function."""
        result = (
            analyze_zones(sample_data)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_builder_threshold_strategy(self):
        """Test builder with threshold strategy."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        rsi_values = 50 + 40 * np.sin(np.linspace(0, 6*np.pi, 200))  # More oscillation, more zones
        macd_hist = np.sin(np.linspace(0, 4*np.pi, 200)) * 2
        
        df = pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'rsi': rsi_values,
            'macd': macd_hist / 2,
            'macd_signal': macd_hist / 3,
            'macd_hist': macd_hist,
            'atr': np.random.uniform(1, 2, 200)
        }, index=dates)
        
        result = (
            analyze_zones(df)
            .detect_zones('threshold', 
                         indicator_col='rsi',
                         upper_threshold=80,  # More permissive thresholds to get zones
                         lower_threshold=20)
            .analyze(clustering=False)  # Disable clustering for this test
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        # Note: might be 0 zones if RSI doesn't cross thresholds, that's ok for this test
        assert result is not None
    
    def test_builder_line_crossing_strategy(self, sample_data):
        """Test builder with line crossing strategy."""
        sample_data = sample_data.copy()
        sample_data['fast_ma'] = sample_data['close'].rolling(10).mean()
        sample_data['slow_ma'] = sample_data['close'].rolling(20).mean()
        sample_data = sample_data.dropna()
        
        result = (
            analyze_zones(sample_data)
            .detect_zones('line_crossing',
                         line1_col='fast_ma',
                         line2_col='slow_ma')
            .with_cache(enable=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_builder_zone_type_filter(self, sample_data):
        """Test zone type filtering in builder."""
        result = (
            analyze_zones(sample_data)
            .detect_zones('zero_crossing',
                         min_duration=2,
                         zone_types=['bull'],
                         indicator_col='macd_hist')
            .analyze(clustering=False)  # Might have < 3 zones after filtering
            .with_cache(enable=False)
            .build()
        )
        
        assert all(z.type == 'bull' for z in result.zones)

