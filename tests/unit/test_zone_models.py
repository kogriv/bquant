"""
Unit tests for bquant.analysis.zones.models

Tests for ZoneInfo and ZoneAnalysisResult including serialization/deserialization.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle
import gzip
import json
import tempfile
import shutil

from bquant.analysis.zones.models import ZoneInfo, ZoneAnalysisResult

# Check if pyarrow is available
try:
    import pyarrow
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False


class TestZoneInfo:
    """Tests for ZoneInfo dataclass."""
    
    @pytest.fixture
    def sample_zone_data(self):
        """Create sample DataFrame for zone."""
        dates = pd.date_range('2024-01-01', periods=10, freq='1h')
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 10),
            'high': np.random.uniform(105, 110, 10),
            'low': np.random.uniform(95, 100, 10),
            'close': np.random.uniform(100, 105, 10),
            'volume': np.random.uniform(1000, 2000, 10),
            'macd': np.random.uniform(-1, 1, 10)
        }, index=dates)
    
    @pytest.fixture
    def sample_zone(self, sample_zone_data):
        """Create sample ZoneInfo object."""
        return ZoneInfo(
            zone_id=1,
            type='bull',
            start_idx=0,
            end_idx=9,
            start_time=sample_zone_data.index[0],
            end_time=sample_zone_data.index[9],
            duration=10,
            data=sample_zone_data,
            features={'swing_count': 3, 'avg_volatility': 0.5}
        )
    
    def test_zone_info_creation(self, sample_zone):
        """Test ZoneInfo creation."""
        assert sample_zone.zone_id == 1
        assert sample_zone.type == 'bull'
        assert sample_zone.duration == 10
        assert len(sample_zone.data) == 10
        assert sample_zone.features is not None
    
    def test_to_analyzer_format(self, sample_zone):
        """Test to_analyzer_format method."""
        analyzer_format = sample_zone.to_analyzer_format()
        
        assert isinstance(analyzer_format, dict)
        assert 'zone_id' in analyzer_format
        assert 'type' in analyzer_format
        assert 'duration' in analyzer_format
        assert 'data' in analyzer_format
        assert 'swing_count' in analyzer_format
        assert 'avg_volatility' in analyzer_format
    
    def test_indicator_context_initialization(self, sample_zone_data):
        """Test that indicator_context is initialized as empty dict if None (v2.1)."""
        # Create zone without indicator_context
        zone = ZoneInfo(
            zone_id=1,
            type='bull',
            start_idx=0,
            end_idx=9,
            start_time=sample_zone_data.index[0],
            end_time=sample_zone_data.index[9],
            duration=10,
            data=sample_zone_data
        )
        
        # Verify indicator_context exists and is empty dict
        assert zone.indicator_context is not None
        assert isinstance(zone.indicator_context, dict)
        assert zone.indicator_context == {}
    
    def test_get_primary_indicator_column(self, sample_zone_data):
        """Test get_primary_indicator_column method (v2.1)."""
        # Create zone WITH indicator_context
        zone = ZoneInfo(
            zone_id=1,
            type='bull',
            start_idx=0,
            end_idx=9,
            start_time=sample_zone_data.index[0],
            end_time=sample_zone_data.index[9],
            duration=10,
            data=sample_zone_data,
            indicator_context={
                'detection_strategy': 'zero_crossing',
                'detection_indicator': 'macd',
                'signal_line': None,
                'detection_rules': {'indicator_col': 'macd'}
            }
        )
        
        # Verify method returns correct value
        assert zone.get_primary_indicator_column() == 'macd'
        assert zone.get_signal_line_column() is None
    
    def test_to_analyzer_format_includes_context(self, sample_zone_data):
        """Test that to_analyzer_format includes indicator_context (v2.1)."""
        # Create zone with indicator_context
        zone = ZoneInfo(
            zone_id=1,
            type='bull',
            start_idx=0,
            end_idx=9,
            start_time=sample_zone_data.index[0],
            end_time=sample_zone_data.index[9],
            duration=10,
            data=sample_zone_data,
            features={'swing_count': 3},
            indicator_context={
                'detection_strategy': 'line_crossing',
                'detection_indicator': 'ema_12',
                'signal_line': 'ema_26'
            }
        )
        
        # Get analyzer format
        analyzer_format = zone.to_analyzer_format()
        
        # Verify indicator_context is included
        assert 'indicator_context' in analyzer_format
        assert analyzer_format['indicator_context'] == zone.indicator_context
        assert analyzer_format['indicator_context']['detection_strategy'] == 'line_crossing'
        assert analyzer_format['indicator_context']['detection_indicator'] == 'ema_12'
        assert analyzer_format['indicator_context']['signal_line'] == 'ema_26'


class TestZoneAnalysisResult:
    """Tests for ZoneAnalysisResult dataclass and serialization."""
    
    @pytest.fixture
    def sample_zones(self):
        """Create sample list of ZoneInfo objects."""
        dates = pd.date_range('2024-01-01', periods=20, freq='1h')
        df = pd.DataFrame({
            'open': np.random.uniform(100, 105, 20),
            'high': np.random.uniform(105, 110, 20),
            'low': np.random.uniform(95, 100, 20),
            'close': np.random.uniform(100, 105, 20),
            'volume': np.random.uniform(1000, 2000, 20),
            'macd': np.random.uniform(-1, 1, 20)
        }, index=dates)
        
        zone1 = ZoneInfo(
            zone_id=0,
            type='bull',
            start_idx=0,
            end_idx=9,
            start_time=df.index[0],
            end_time=df.index[9],
            duration=10,
            data=df.iloc[0:10],
            features={'swing_count': 2}
        )
        
        zone2 = ZoneInfo(
            zone_id=1,
            type='bear',
            start_idx=10,
            end_idx=19,
            start_time=df.index[10],
            end_time=df.index[19],
            duration=10,
            data=df.iloc[10:20],
            features={'swing_count': 3}
        )
        
        return [zone1, zone2], df
    
    @pytest.fixture
    def sample_result(self, sample_zones):
        """Create sample ZoneAnalysisResult object."""
        zones, df = sample_zones
        
        return ZoneAnalysisResult(
            zones=zones,
            statistics={'bull_zones': 1, 'bear_zones': 1, 'avg_duration': 10.0},
            hypothesis_tests={'test1': {'p_value': 0.05, 'significant': True}},
            clustering={'n_clusters': 2, 'labels': [0, 1]},
            sequence_analysis={'transitions': 1},
            regression_results={'duration': {'r2': 0.8}},
            validation_results={'valid': True},
            data=df,
            metadata={'analysis_date': '2024-01-01'}
        )
    
    def test_result_creation(self, sample_result):
        """Test ZoneAnalysisResult creation."""
        assert len(sample_result.zones) == 2
        assert sample_result.statistics is not None
        assert sample_result.hypothesis_tests is not None
        assert sample_result.data is not None
    
    def test_save_load_pickle(self, sample_result):
        """Test save/load with pickle format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.pkl'
            
            # Save
            sample_result.save(filepath, format='pickle')
            assert filepath.exists()
            
            # Load
            loaded = ZoneAnalysisResult.load(filepath, format='pickle')
            
            # Verify
            assert len(loaded.zones) == len(sample_result.zones)
            assert loaded.statistics == sample_result.statistics
            assert loaded.hypothesis_tests == sample_result.hypothesis_tests
    
    def test_save_load_pickle_compressed(self, sample_result):
        """Test save/load with compressed pickle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.pkl'
            
            # Save with compression
            sample_result.save(filepath, format='pickle', compress=True)
            compressed_file = Path(tmpdir) / 'test_result.pkl.gz'
            assert compressed_file.exists()
            
            # Load
            loaded = ZoneAnalysisResult.load(compressed_file, format='pickle')
            
            # Verify
            assert len(loaded.zones) == len(sample_result.zones)
    
    def test_save_load_json(self, sample_result):
        """Test save/load with JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.json'
            
            # Save (without data - JSON doesn't handle DataFrame well)
            sample_result.save(filepath, format='json', include_data=False)
            assert filepath.exists()
            
            # Load
            loaded = ZoneAnalysisResult.load(filepath, format='json')
            
            # Verify
            assert len(loaded.zones) == len(sample_result.zones)
            assert loaded.statistics == sample_result.statistics
            assert loaded.data is None  # We didn't save data
    
    @pytest.mark.skipif(not PYARROW_AVAILABLE, reason="pyarrow not installed")
    def test_save_load_parquet(self, sample_result):
        """Test save/load with parquet format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.parquet'
            
            # Save
            sample_result.save(filepath, format='parquet')
            parquet_dir = Path(tmpdir) / 'test_result.parquet'
            assert parquet_dir.exists()
            assert (parquet_dir / 'zones.parquet').exists()
            assert (parquet_dir / 'metadata.json').exists()
            assert (parquet_dir / 'data.parquet').exists()
            
            # Load
            loaded = ZoneAnalysisResult.load(filepath, format='parquet')
            
            # Verify
            assert len(loaded.zones) == len(sample_result.zones)
            assert loaded.statistics == sample_result.statistics
    
    def test_save_without_data(self, sample_result):
        """Test save without including DataFrame."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.pkl'
            
            # Save without data
            sample_result.save(filepath, format='pickle', include_data=False)
            
            # Load
            loaded = ZoneAnalysisResult.load(filepath, format='pickle')
            
            # Verify data is None
            assert loaded.data is None
            assert len(loaded.zones) == len(sample_result.zones)
    
    def test_to_dict_from_dict(self, sample_result):
        """Test to_dict and from_dict methods."""
        # Convert to dict
        result_dict = sample_result.to_dict(include_data=False)
        
        assert isinstance(result_dict, dict)
        assert 'zones' in result_dict
        assert 'statistics' in result_dict
        assert len(result_dict['zones']) == 2
        
        # Convert back
        loaded = ZoneAnalysisResult.from_dict(result_dict)
        
        assert len(loaded.zones) == len(sample_result.zones)
        assert loaded.statistics == sample_result.statistics
    
    def test_zone_to_dict(self, sample_zones):
        """Test _zone_to_dict helper."""
        zones, _ = sample_zones
        zone = zones[0]
        
        zone_dict = ZoneAnalysisResult._zone_to_dict(zone)
        
        assert isinstance(zone_dict, dict)
        assert zone_dict['zone_id'] == 0
        assert zone_dict['type'] == 'bull'
        assert zone_dict['duration'] == 10
        assert isinstance(zone_dict['start_time'], str)
        assert isinstance(zone_dict['end_time'], str)
    
    def test_zone_from_dict(self):
        """Test _zone_from_dict helper."""
        zone_dict = {
            'zone_id': 1,
            'type': 'bear',
            'start_idx': 0,
            'end_idx': 9,
            'start_time': '2024-01-01T00:00:00',
            'end_time': '2024-01-01T09:00:00',
            'duration': 10,
            'features': {'swing_count': 5}
        }
        
        zone = ZoneAnalysisResult._zone_from_dict(zone_dict)
        
        assert isinstance(zone, ZoneInfo)
        assert zone.zone_id == 1
        assert zone.type == 'bear'
        assert zone.duration == 10
        assert zone.features['swing_count'] == 5
    
    def test_unsupported_format(self, sample_result):
        """Test error handling for unsupported format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'test_result.xyz'
            
            with pytest.raises(ValueError, match="Unsupported format"):
                sample_result.save(filepath, format='xyz')
    
    def test_load_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            ZoneAnalysisResult.load('nonexistent_file.pkl', format='pickle')
    
    def test_visualize_method_without_data(self, sample_result):
        """Test visualize method without data raises error."""
        sample_result.data = None
        
        with pytest.raises(ValueError, match="data not available"):
            sample_result.visualize('overview')
    
    def test_visualize_invalid_mode(self, sample_result):
        """Test visualize with invalid mode."""
        with pytest.raises(ValueError, match="Unknown mode"):
            sample_result.visualize('invalid_mode')

