"""
Unit tests for ZoneFeaturesAnalyzer indicator_context handling (v2.1)

Tests that ZoneFeaturesAnalyzer correctly:
1. Reads indicator_context from zone_info
2. Passes indicator_col to strategies
3. Falls back to generic oscillator detection when context missing
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy


class TestZoneFeaturesAnalyzerContext:
    """Tests for ZoneFeaturesAnalyzer indicator_context handling (v2.1)."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample zone data with multiple indicators."""
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 50),
            'high': np.random.uniform(105, 110, 50),
            'low': np.random.uniform(95, 100, 50),
            'close': np.random.uniform(100, 105, 50),
            'volume': np.random.uniform(1000, 2000, 50),
            'macd_hist': np.sin(np.linspace(0, np.pi, 50)),
            'macd': np.sin(np.linspace(0, np.pi, 50)) * 0.8,
            'RSI_14': np.random.uniform(30, 70, 50),
            'AO_5_34': np.sin(np.linspace(0, np.pi, 50)) * 10,
            'atr': np.random.uniform(1, 3, 50)
        }, index=dates)
    
    def test_analyzer_reads_indicator_context(self, sample_zone_data):
        """Test that analyzer reads indicator_context from zone_info."""
        analyzer = ZoneFeaturesAnalyzer(
            shape_strategy=StatisticalShapeStrategy(),
            divergence_strategy=ClassicDivergenceStrategy(),
            volume_strategy=StandardVolumeStrategy()
        )
        
        zone_info = {
            'zone_id': 1,
            'type': 'bull',
            'duration': 50,
            'data': sample_zone_data,
            'indicator_context': {
                'detection_strategy': 'zero_crossing',
                'detection_indicator': 'RSI_14',
                'signal_line': None,
                'detection_rules': {}
            }
        }
        
        features = analyzer.extract_zone_features(zone_info)
        
        assert features is not None
        # Verify shape_metrics calculated (would fail in v1.0 for RSI)
        assert 'shape_metrics' in features.metadata
        assert features.metadata['shape_metrics'] is not None
        
        # Verify divergence_metrics calculated
        assert 'divergence_metrics' in features.metadata
        assert features.metadata['divergence_metrics'] is not None
        
        # Verify strategies used RSI_14 (from context)
        shape_params = features.metadata['shape_metrics']['strategy_params']
        assert shape_params['indicator_col'] == 'RSI_14'
        
        div_params = features.metadata['divergence_metrics']['strategy_params']
        assert div_params['indicator_col'] == 'RSI_14'
    
    def test_analyzer_passes_signal_line_to_divergence(self, sample_zone_data):
        """Test that analyzer passes signal_line to divergence strategy."""
        analyzer = ZoneFeaturesAnalyzer(
            divergence_strategy=ClassicDivergenceStrategy()
        )
        
        zone_info = {
            'zone_id': 1,
            'type': 'bull',
            'duration': 50,
            'data': sample_zone_data,
            'indicator_context': {
                'detection_strategy': 'line_crossing',
                'detection_indicator': 'macd_hist',
                'signal_line': 'macd',  # Two-line divergence
                'detection_rules': {}
            }
        }
        
        features = analyzer.extract_zone_features(zone_info)
        
        # Verify divergence received both indicators
        div_params = features.metadata['divergence_metrics']['strategy_params']
        assert div_params['indicator_col'] == 'macd_hist'
        assert div_params['indicator_line_col'] == 'macd'
    
    def test_no_context_means_no_oscillator_metrics_not_a_guess(self, sample_zone_data):
        """Без колонки индикатора метрики осциллятора — None (G61).

        До 2026-09-05 `_find_any_oscillator` брал первую числовую колонку вне
        короткого списка исключений и считал по ней амплитуду, корреляцию, форму
        и дивергенции: preloaded-зоны на сэмпле получали амплитуду 87205 по
        `accumulation_distribution`. Число из чужого ряда хуже отсутствия числа.
        """
        analyzer = ZoneFeaturesAnalyzer(
            shape_strategy=StatisticalShapeStrategy()
        )
        zone_info = {
            'zone_id': 1,
            'type': 'bull',
            'duration': 50,
            'data': sample_zone_data
            # NO indicator_context field
        }

        features = analyzer.extract_zone_features(zone_info)

        assert features.oscillator_amplitude is None
        assert features.correlation_price_oscillator is None
        assert features.metadata['oscillator_column'] is None
        assert features.metadata.get('shape_metrics') is None
        assert not hasattr(analyzer, '_find_any_oscillator')
    def test_shape_strategy_called_with_correct_indicator(self, sample_zone_data):
        """Test that shape strategy receives correct indicator_col from context."""
        analyzer = ZoneFeaturesAnalyzer(
            shape_strategy=StatisticalShapeStrategy()
        )
        
        # Test with AO indicator in context
        zone_info = {
            'zone_id': 1,
            'type': 'bull',
            'duration': 50,
            'data': sample_zone_data,
            'indicator_context': {
                'detection_indicator': 'AO_5_34',
                'signal_line': None
            }
        }
        
        features = analyzer.extract_zone_features(zone_info)
        
        # Verify AO was used (not MACD)
        shape_params = features.metadata['shape_metrics']['strategy_params']
        assert shape_params['indicator_col'] == 'AO_5_34'
    
    def test_volume_strategy_receives_indicator_from_context(self, sample_zone_data):
        """Test that volume strategy receives indicator_col from context."""
        analyzer = ZoneFeaturesAnalyzer(
            volume_strategy=StandardVolumeStrategy()
        )
        
        zone_info = {
            'zone_id': 1,
            'type': 'bull',
            'duration': 50,
            'data': sample_zone_data,
            'indicator_context': {
                'detection_indicator': 'RSI_14',
                'signal_line': None
            }
        }
        
        features = analyzer.extract_zone_features(zone_info)
        
        # Verify volume_indicator_corr was calculated with RSI
        vol_params = features.metadata['volume_metrics']['strategy_params']
        assert vol_params['indicator_col'] == 'RSI_14'


