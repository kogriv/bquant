"""
Unit tests for UniversalZoneAnalyzer

Tests for universal zone analyzer with dependency injection.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones import (
    UniversalZoneAnalyzer,
    ZoneInfo,
    ZoneAnalysisResult
)


class TestUniversalZoneAnalyzer:
    """Tests for UniversalZoneAnalyzer."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 200),
            'high': np.random.uniform(105, 110, 200),
            'low': np.random.uniform(95, 100, 200),
            'close': np.random.uniform(100, 105, 200),
            'volume': np.random.uniform(1000, 2000, 200),
            'macd': np.sin(np.linspace(0, 4*np.pi, 200)),
            'macd_signal': np.sin(np.linspace(0, 4*np.pi, 200) - 0.2),
            'macd_hist': np.sin(np.linspace(0, 4*np.pi, 200)) * 0.5
        }, index=dates)
    
    @pytest.fixture
    def sample_zones(self, sample_data):
        """Create sample zones."""
        zones = []
        
        # Create 4 zones
        for i in range(4):
            start_idx = i * 40
            end_idx = start_idx + 39
            
            zone = ZoneInfo(
                zone_id=i,
                type='bull' if i % 2 == 0 else 'bear',
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=sample_data.index[start_idx],
                end_time=sample_data.index[end_idx],
                duration=40,
                data=sample_data.iloc[start_idx:end_idx + 1].copy()
            )
            zones.append(zone)
        
        return zones
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = UniversalZoneAnalyzer()
        
        assert analyzer.features is not None
        assert analyzer.hypotheses is not None
        assert analyzer.sequences is not None
    
    def test_analyzer_with_di(self):
        """Test analyzer with dependency injection."""
        from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
        
        custom_features = ZoneFeaturesAnalyzer(min_duration=3)
        analyzer = UniversalZoneAnalyzer(features_analyzer=custom_features)
        
        assert analyzer.features is custom_features
    
    def test_analyze_zones_basic(self, sample_data, sample_zones):
        """Test basic zone analysis."""
        analyzer = UniversalZoneAnalyzer()
        
        result = analyzer.analyze_zones(
            sample_zones,
            sample_data,
            perform_clustering=False,
            run_regression=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) == 4
        assert result.statistics is not None
        assert result.hypothesis_tests is not None
        assert result.sequence_analysis is not None
    
    def test_analyze_zones_with_clustering(self, sample_data, sample_zones):
        """Test zone analysis with clustering."""
        analyzer = UniversalZoneAnalyzer()
        
        result = analyzer.analyze_zones(
            sample_zones,
            sample_data,
            perform_clustering=True,
            n_clusters=2
        )
        
        assert result.clustering is not None
    
    def test_analyze_zones_with_regression(self, sample_data, sample_zones):
        """Test zone analysis with regression."""
        analyzer = UniversalZoneAnalyzer()
        
        # Need more zones for regression (>10)
        extra_zones = sample_zones * 3  # 12 zones
        
        result = analyzer.analyze_zones(
            extra_zones,
            sample_data,
            run_regression=True
        )
        
        # Regression may or may not run depending on data quality
        # Just check it doesn't crash
        assert isinstance(result, ZoneAnalysisResult)
    
    def test_analyze_empty_zones(self, sample_data):
        """Test handling empty zones list."""
        analyzer = UniversalZoneAnalyzer()
        
        result = analyzer.analyze_zones([], sample_data)
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) == 0
        assert result.statistics == {}
    
    def test_analyze_few_zones(self, sample_data, sample_zones):
        """Test analysis with few zones (not enough for clustering)."""
        analyzer = UniversalZoneAnalyzer()
        
        # Use 3 zones - minimum for sequence analysis, but not enough for clustering
        result = analyzer.analyze_zones(
            sample_zones[:3],
            sample_data,
            perform_clustering=False
        )
        
        assert len(result.zones) == 3
        assert result.statistics is not None
    
    def test_analyze_zones_metadata(self, sample_data, sample_zones):
        """Test result metadata."""
        analyzer = UniversalZoneAnalyzer()
        
        result = analyzer.analyze_zones(sample_zones, sample_data)
        
        assert 'analysis_timestamp' in result.metadata
        assert 'total_zones' in result.metadata
        assert 'zone_types' in result.metadata
        assert result.metadata['total_zones'] == 4
        assert set(result.metadata['zone_types']) == {'bull', 'bear'}

