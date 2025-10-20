"""
Tests for MACD Zone Analyzer Backward Compatibility

Проверяет что MACDZoneAnalyzer корректно работает как thin wrapper
поверх универсальной архитектуры и выдает deprecation warnings.

Stage 2.1 - Slim down MACDZoneAnalyzer
"""

import pytest
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

from bquant.indicators.macd import (
    MACDZoneAnalyzer,
    create_macd_analyzer,
    analyze_macd_zones,
    ZoneAnalysisResult
)


class TestMACDBackwardCompatibility:
    """Tests for backward compatibility after slim down refactoring."""
    
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
    
    def test_analyzer_initialization_with_deprecation_warning(self):
        """Test that initializing MACDZoneAnalyzer shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer()
            
            # Check deprecation warning was raised
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()
            assert "analyze_zones" in str(w[0].message)
    
    def test_analyzer_with_old_param_format(self):
        """Test analyzer works with old parameter format (fast, slow, signal)."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            # Old format
            analyzer = MACDZoneAnalyzer(
                macd_params={'fast': 12, 'slow': 26, 'signal': 9},
                zone_params={'min_duration': 3}
            )
            
            # Check conversion to new format
            assert analyzer.macd_params['fast_period'] == 12
            assert analyzer.macd_params['slow_period'] == 26
            assert analyzer.macd_params['signal_period'] == 9
            assert analyzer.zone_params['min_duration'] == 3
    
    def test_analyzer_with_new_param_format(self):
        """Test analyzer works with new parameter format (fast_period, etc)."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            # New format
            analyzer = MACDZoneAnalyzer(
                macd_params={'fast_period': 10, 'slow_period': 20, 'signal_period': 5}
            )
            
            assert analyzer.macd_params['fast_period'] == 10
            assert analyzer.macd_params['slow_period'] == 20
            assert analyzer.macd_params['signal_period'] == 5
    
    def test_analyze_complete_delegates_to_pipeline(self, sample_data):
        """Test that analyze_complete correctly delegates to universal pipeline."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer()
            result = analyzer.analyze_complete(sample_data, perform_clustering=False)
            
            # Check result structure
            assert isinstance(result, ZoneAnalysisResult)
            assert len(result.zones) > 0
            assert result.statistics is not None
            assert result.hypothesis_tests is not None
            assert result.sequence_analysis is not None or len(result.zones) < 3
    
    def test_analyze_complete_modular_delegates_to_pipeline(self, sample_data):
        """Test that analyze_complete_modular correctly delegates to universal pipeline."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer()
            result = analyzer.analyze_complete_modular(
                sample_data, 
                perform_clustering=True,
                n_clusters=3
            )
            
            # Check result structure
            assert isinstance(result, ZoneAnalysisResult)
            assert len(result.zones) > 0
            assert result.statistics is not None
            assert result.hypothesis_tests is not None
            
            # Check clustering was performed
            if len(result.zones) >= 3:
                assert result.clustering is not None
    
    def test_create_macd_analyzer_shows_deprecation(self):
        """Test create_macd_analyzer() shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            analyzer = create_macd_analyzer()
            
            # Check at least one deprecation warning
            deprecation_warnings = [warning for warning in w 
                                   if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            
            # Check it returns a valid object (type doesn't matter due to decorator)
            assert analyzer is not None
            assert hasattr(analyzer, 'analyze_complete')
    
    def test_analyze_macd_zones_function_shows_deprecation(self, sample_data):
        """Test analyze_macd_zones() function shows deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = analyze_macd_zones(sample_data, perform_clustering=False)
            
            # Check deprecation warnings
            deprecation_warnings = [warning for warning in w 
                                   if issubclass(warning.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            
            # Check it returns valid result
            assert isinstance(result, ZoneAnalysisResult)
            assert len(result.zones) > 0
    
    def test_backward_compatibility_parameters(self, sample_data):
        """Test backward compatibility with various parameter combinations."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            # Test 1: Default parameters
            analyzer1 = MACDZoneAnalyzer()
            result1 = analyzer1.analyze_complete(sample_data, perform_clustering=False)
            assert len(result1.zones) > 0
            
            # Test 2: Custom MACD params (old format)
            analyzer2 = MACDZoneAnalyzer(
                macd_params={'fast': 5, 'slow': 10, 'signal': 3}
            )
            result2 = analyzer2.analyze_complete(sample_data, perform_clustering=False)
            assert len(result2.zones) > 0
            
            # Test 3: Custom zone params
            analyzer3 = MACDZoneAnalyzer(
                zone_params={'min_duration': 5}
            )
            result3 = analyzer3.analyze_complete(sample_data, perform_clustering=False)
            assert len(result3.zones) > 0
    
    def test_result_structure_matches_universal_api(self, sample_data):
        """Test that result structure matches universal API output."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            # Via old API (deprecated wrapper)
            analyzer = MACDZoneAnalyzer()
            result_old = analyzer.analyze_complete(sample_data, perform_clustering=False)
            
            # Via new universal API
            from bquant.analysis.zones import analyze_zones
            result_new = (
                analyze_zones(sample_data)
                .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
                .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
                .analyze(clustering=False)
                .build()
            )
            
            # Both should return ZoneAnalysisResult
            assert isinstance(result_old, ZoneAnalysisResult)
            assert isinstance(result_new, ZoneAnalysisResult)
            
            # Both should have same number of zones (same data, same params)
            assert len(result_old.zones) == len(result_new.zones)
            
            # Both should have required fields
            assert result_old.statistics is not None
            assert result_new.statistics is not None
            assert result_old.hypothesis_tests is not None
            assert result_new.hypothesis_tests is not None
    
    def test_clustering_parameter_works(self, sample_data):
        """Test that clustering parameter is correctly passed through."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer()
            
            # Without clustering
            result_no_cluster = analyzer.analyze_complete(
                sample_data, 
                perform_clustering=False
            )
            assert result_no_cluster.clustering is None
            
            # With clustering
            result_with_cluster = analyzer.analyze_complete(
                sample_data, 
                perform_clustering=True,
                n_clusters=3
            )
            
            if len(result_with_cluster.zones) >= 3:
                assert result_with_cluster.clustering is not None
    
    def test_analyze_complete_and_modular_produce_same_results(self, sample_data):
        """Test that analyze_complete and analyze_complete_modular produce identical results."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer()
            
            result1 = analyzer.analyze_complete(sample_data, perform_clustering=False)
            result2 = analyzer.analyze_complete_modular(sample_data, perform_clustering=False)
            
            # Should produce identical results (same underlying implementation)
            assert len(result1.zones) == len(result2.zones)
            assert result1.zones[0].type == result2.zones[0].type
            assert result1.zones[0].duration == result2.zones[0].duration

