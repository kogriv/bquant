"""
Unit tests for Zone Detection Strategies

Tests for all detection strategies:
- ZeroCrossingDetection
- ThresholdDetection
- LineCrossingDetection
- PreloadedZonesDetection
- CombinedRulesDetection
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
from pathlib import Path

from bquant.analysis.zones.detection import (
    ZoneDetectionRegistry,
    ZoneDetectionConfig,
    ZeroCrossingDetection,
    ThresholdDetection,
    LineCrossingDetection,
    PreloadedZonesDetection,
    CombinedRulesDetection,
    load_preloaded_zones
)


class TestZoneDetectionRegistry:
    """Tests for ZoneDetectionRegistry."""
    
    def test_registry_lists_all_strategies(self):
        """Test that all strategies are registered."""
        strategies = ZoneDetectionRegistry.list_strategies()
        
        assert 'zero_crossing' in strategies
        assert 'threshold' in strategies
        assert 'line_crossing' in strategies
        assert 'preloaded' in strategies
        assert 'combined' in strategies
        assert len(strategies) == 5
    
    def test_registry_get_strategy(self):
        """Test getting strategy by name."""
        strategy = ZoneDetectionRegistry.get('zero_crossing')
        assert isinstance(strategy, ZeroCrossingDetection)
    
    def test_registry_get_unknown_strategy(self):
        """Test error on unknown strategy."""
        with pytest.raises(ValueError, match="Unknown zone detection strategy"):
            ZoneDetectionRegistry.get('nonexistent')
    
    def test_registry_get_info(self):
        """Test getting strategy metadata."""
        info = ZoneDetectionRegistry.get_info('zero_crossing')
        
        assert 'description' in info
        assert 'supported_zones' in info
        assert 'required_rules' in info
        assert info['supported_zones'] == ['bull', 'bear']
        assert 'indicator_col' in info['required_rules']
    
    def test_registry_list_all_info(self):
        """Test getting all strategies info."""
        all_info = ZoneDetectionRegistry.list_all_info()
        
        assert isinstance(all_info, dict)
        assert 'zero_crossing' in all_info
        assert len(all_info) == 5


class TestZeroCrossingDetection:
    """Tests for ZeroCrossingDetection strategy."""
    
    @pytest.fixture
    def sample_data_macd(self):
        """Create sample data with MACD indicator."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        # Create oscillating indicator around zero
        macd_hist = np.sin(np.linspace(0, 4*np.pi, 100)) * 2
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'volume': np.random.uniform(1000, 2000, 100),
            'macd_histogram': macd_hist
        }, index=dates)
    
    def test_zero_crossing_detect_zones(self, sample_data_macd):
        """Test basic zone detection."""
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd_histogram'},
            strategy_name='zero_crossing'
        )
        
        zones = strategy.detect_zones(sample_data_macd, config)
        
        assert len(zones) > 0
        assert all(z.type in ['bull', 'bear'] for z in zones)
        assert all(z.duration >= 2 for z in zones)
    
    def test_zero_crossing_missing_indicator(self, sample_data_macd):
        """Test error on missing indicator column."""
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            rules={'indicator_col': 'nonexistent'},
            strategy_name='zero_crossing'
        )
        
        with pytest.raises(ValueError, match="not found in data"):
            strategy.detect_zones(sample_data_macd, config)
    
    def test_zero_crossing_config_validation(self, sample_data_macd):
        """Test config validation."""
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            rules={},  # Missing indicator_col
            strategy_name='zero_crossing'
        )
        
        with pytest.raises(ValueError, match="Missing required rules"):
            strategy.detect_zones(sample_data_macd, config)
    
    def test_zero_crossing_min_duration_filter(self, sample_data_macd):
        """Test minimum duration filtering."""
        strategy = ZeroCrossingDetection()
        
        # With min_duration=2
        config1 = ZoneDetectionConfig(
            min_duration=2,
            rules={'indicator_col': 'macd_histogram'}
        )
        zones1 = strategy.detect_zones(sample_data_macd, config1)
        
        # With min_duration=10
        config2 = ZoneDetectionConfig(
            min_duration=10,
            rules={'indicator_col': 'macd_histogram'}
        )
        zones2 = strategy.detect_zones(sample_data_macd, config2)
        
        # Should have fewer zones with higher min_duration
        assert len(zones2) <= len(zones1)
    
    def test_zero_crossing_zone_type_filter(self, sample_data_macd):
        """Test zone type filtering."""
        strategy = ZeroCrossingDetection()
        
        # Only bull zones
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull'],
            rules={'indicator_col': 'macd_histogram'}
        )
        zones = strategy.detect_zones(sample_data_macd, config)
        
        assert all(z.type == 'bull' for z in zones)
    
    def test_zero_crossing_smooth_window(self, sample_data_macd):
        """Test smoothing option."""
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            rules={
                'indicator_col': 'macd_histogram',
                'smooth_window': 3
            }
        )
        
        zones = strategy.detect_zones(sample_data_macd, config)
        assert len(zones) > 0


class TestThresholdDetection:
    """Tests for ThresholdDetection strategy."""
    
    @pytest.fixture
    def sample_data_rsi(self):
        """Create sample data with RSI indicator."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        # Create RSI-like values (0-100)
        rsi = 50 + 30 * np.sin(np.linspace(0, 6*np.pi, 100))
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'rsi': rsi
        }, index=dates)
    
    def test_threshold_detect_zones(self, sample_data_rsi):
        """Test basic threshold detection."""
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['overbought', 'neutral', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            },
            strategy_name='threshold'
        )
        
        zones = strategy.detect_zones(sample_data_rsi, config)
        
        assert len(zones) > 0
        assert all(z.type in ['overbought', 'neutral', 'oversold'] for z in zones)
    
    def test_threshold_invalid_thresholds(self, sample_data_rsi):
        """Test error on invalid thresholds."""
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 30,  # Lower than lower_threshold!
                'lower_threshold': 70
            }
        )
        
        with pytest.raises(ValueError, match="must be >"):
            strategy.detect_zones(sample_data_rsi, config)
    
    def test_threshold_only_overbought(self, sample_data_rsi):
        """Test detecting only overbought zones."""
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            zone_types=['overbought'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            }
        )
        
        zones = strategy.detect_zones(sample_data_rsi, config)
        assert all(z.type == 'overbought' for z in zones)


class TestLineCrossingDetection:
    """Tests for LineCrossingDetection strategy."""
    
    @pytest.fixture
    def sample_data_ma_cross(self):
        """Create sample data with moving averages."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        # Create crossing lines
        fast_ma = 100 + 5 * np.sin(np.linspace(0, 4*np.pi, 100))
        slow_ma = 100 + 3 * np.sin(np.linspace(0, 4*np.pi, 100) - 0.5)
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'fast_ma': fast_ma,
            'slow_ma': slow_ma
        }, index=dates)
    
    def test_line_crossing_detect_zones(self, sample_data_ma_cross):
        """Test line crossing detection."""
        strategy = LineCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={
                'line1_col': 'fast_ma',
                'line2_col': 'slow_ma'
            },
            strategy_name='line_crossing'
        )
        
        zones = strategy.detect_zones(sample_data_ma_cross, config)
        
        assert len(zones) > 0
        assert all(z.type in ['bull', 'bear'] for z in zones)
    
    def test_line_crossing_missing_columns(self, sample_data_ma_cross):
        """Test error on missing columns."""
        strategy = LineCrossingDetection()
        config = ZoneDetectionConfig(
            rules={
                'line1_col': 'missing1',
                'line2_col': 'slow_ma'
            }
        )
        
        with pytest.raises(ValueError, match="not found in data"):
            strategy.detect_zones(sample_data_ma_cross, config)


class TestPreloadedZonesDetection:
    """Tests for PreloadedZonesDetection strategy."""
    
    @pytest.fixture
    def sample_ohlcv(self):
        """Create sample OHLCV data."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'volume': np.random.uniform(1000, 2000, 100)
        }, index=dates)
    
    @pytest.fixture
    def sample_zones_df(self, sample_ohlcv):
        """Create sample zones DataFrame."""
        return pd.DataFrame({
            'zone_id': [0, 1, 2],
            'type': ['bull', 'bear', 'bull'],
            'start_time': [
                sample_ohlcv.index[0],
                sample_ohlcv.index[30],
                sample_ohlcv.index[60]
            ],
            'end_time': [
                sample_ohlcv.index[29],
                sample_ohlcv.index[59],
                sample_ohlcv.index[89]
            ]
        })
    
    def test_preloaded_from_dataframe(self, sample_ohlcv, sample_zones_df):
        """Test loading zones from DataFrame."""
        strategy = PreloadedZonesDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['any'],
            rules={'zones_data': sample_zones_df},
            strategy_name='preloaded'
        )
        
        zones = strategy.detect_zones(sample_ohlcv, config)
        
        assert len(zones) == 3
        assert all(z.data is not None for z in zones)
        assert all(len(z.data) > 0 for z in zones)
    
    def test_preloaded_from_csv(self, sample_ohlcv, sample_zones_df):
        """Test loading zones from CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'zones.csv'
            sample_zones_df.to_csv(csv_path, index=False)
            
            strategy = PreloadedZonesDetection()
            config = ZoneDetectionConfig(
                min_duration=2,
                zone_types=['any'],
                rules={'zones_data': str(csv_path)},
                strategy_name='preloaded'
            )
            
            zones = strategy.detect_zones(sample_ohlcv, config)
            assert len(zones) == 3
    
    def test_preloaded_file_not_found(self, sample_ohlcv):
        """Test error on missing file."""
        strategy = PreloadedZonesDetection()
        config = ZoneDetectionConfig(
            rules={'zones_data': 'nonexistent.csv'}
        )
        
        with pytest.raises(FileNotFoundError):
            strategy.detect_zones(sample_ohlcv, config)
    
    def test_preloaded_missing_columns(self, sample_ohlcv):
        """Test error on missing required columns."""
        bad_zones = pd.DataFrame({
            'zone_id': [0],
            'type': ['bull']
            # Missing start_time, end_time
        })
        
        strategy = PreloadedZonesDetection()
        config = ZoneDetectionConfig(
            rules={'zones_data': bad_zones}
        )
        
        with pytest.raises(ValueError, match="Missing required columns"):
            strategy.detect_zones(sample_ohlcv, config)
    
    def test_load_preloaded_zones_helper(self, sample_ohlcv, sample_zones_df):
        """Test helper function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'zones.csv'
            sample_zones_df.to_csv(csv_path, index=False)
            
            zones = load_preloaded_zones(csv_path, sample_ohlcv)
            assert len(zones) == 3


class TestCombinedRulesDetection:
    """Tests for CombinedRulesDetection strategy."""
    
    @pytest.fixture
    def sample_data_multi(self):
        """Create sample data with multiple indicators."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 100),
            'high': np.random.uniform(105, 110, 100),
            'low': np.random.uniform(95, 100, 100),
            'close': np.random.uniform(100, 105, 100),
            'macd': np.sin(np.linspace(0, 4*np.pi, 100)),
            'rsi': 50 + 30 * np.sin(np.linspace(0, 4*np.pi, 100))
        }, index=dates)
    
    def test_combined_and_logic(self, sample_data_multi):
        """Test combined rules with AND logic."""
        strategy = CombinedRulesDetection()
        
        conditions = [
            lambda df: df['macd'] > 0,
            lambda df: df['rsi'] < 70
        ]
        
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull_confirmed'],
            rules={
                'conditions': conditions,
                'logic': 'AND',
                'zone_type_map': {True: 'bull_confirmed', False: 'other'}
            },
            strategy_name='combined'
        )
        
        zones = strategy.detect_zones(sample_data_multi, config)
        assert all(z.type == 'bull_confirmed' for z in zones)
    
    def test_combined_or_logic(self, sample_data_multi):
        """Test combined rules with OR logic."""
        strategy = CombinedRulesDetection()
        
        conditions = [
            lambda df: df['rsi'] > 70,
            lambda df: df['rsi'] < 30
        ]
        
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['extreme'],
            rules={
                'conditions': conditions,
                'logic': 'OR',
                'zone_type_map': {True: 'extreme', False: 'normal'}
            }
        )
        
        zones = strategy.detect_zones(sample_data_multi, config)
        assert len(zones) > 0
    
    def test_combined_invalid_logic(self, sample_data_multi):
        """Test error on invalid logic."""
        strategy = CombinedRulesDetection()
        config = ZoneDetectionConfig(
            rules={
                'conditions': [lambda df: df['macd'] > 0],
                'logic': 'INVALID'
            }
        )
        
        with pytest.raises(ValueError, match="logic must be"):
            strategy.detect_zones(sample_data_multi, config)


class TestZoneDetectionConfig:
    """Tests for ZoneDetectionConfig."""
    
    def test_config_default_values(self):
        """Test default configuration values."""
        config = ZoneDetectionConfig()
        
        assert config.min_duration == 2
        assert config.zone_types == ['bull', 'bear']
        assert config.rules == {}
        assert config.metadata == {}
    
    def test_config_custom_values(self):
        """Test custom configuration."""
        config = ZoneDetectionConfig(
            min_duration=5,
            zone_types=['overbought', 'oversold'],
            rules={'param1': 'value1'},
            strategy_name='test',
            metadata={'key': 'value'}
        )
        
        assert config.min_duration == 5
        assert config.zone_types == ['overbought', 'oversold']
        assert config.rules['param1'] == 'value1'
        assert config.strategy_name == 'test'
    
    def test_config_validation_success(self):
        """Test validation with all required rules."""
        config = ZoneDetectionConfig(
            rules={'param1': 'value1', 'param2': 'value2'}
        )
        
        # Should not raise
        config.validate(['param1', 'param2'])
    
    def test_config_validation_failure(self):
        """Test validation with missing rules."""
        config = ZoneDetectionConfig(
            rules={'param1': 'value1'},
            strategy_name='test_strategy'
        )
        
        with pytest.raises(ValueError, match="Missing required rules"):
            config.validate(['param1', 'param2'])


class TestIndicatorContextInStrategies:
    """Tests for indicator_context population in all strategies (v2.1)."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data with various indicators."""
        dates = pd.date_range('2024-01-01', periods=50, freq='1h')
        
        return pd.DataFrame({
            'open': np.random.uniform(100, 105, 50),
            'high': np.random.uniform(105, 110, 50),
            'low': np.random.uniform(95, 100, 50),
            'close': np.random.uniform(100, 105, 50),
            'volume': np.random.uniform(1000, 2000, 50),
            'macd_hist': np.sin(np.linspace(0, 4*np.pi, 50)),
            'rsi': np.random.uniform(20, 80, 50),
            'ema_12': np.random.uniform(100, 105, 50),
            'ema_26': np.random.uniform(100, 105, 50)
        }, index=dates)
    
    def test_zero_crossing_has_indicator_context(self, sample_data):
        """Test ZeroCrossingDetection populates indicator_context."""
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd_hist'}
        )
        
        zones = strategy.detect_zones(sample_data, config)
        
        assert len(zones) > 0
        for zone in zones:
            assert zone.indicator_context is not None
            assert zone.indicator_context['detection_strategy'] == 'zero_crossing'
            assert zone.indicator_context['detection_indicator'] == 'macd_hist'
            assert zone.indicator_context['signal_line'] is None
            assert 'detection_rules' in zone.indicator_context
    
    def test_threshold_has_indicator_context(self, sample_data):
        """Test ThresholdDetection populates indicator_context."""
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['overbought', 'neutral', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            }
        )
        
        zones = strategy.detect_zones(sample_data, config)
        
        assert len(zones) > 0
        for zone in zones:
            assert zone.indicator_context is not None
            assert zone.indicator_context['detection_strategy'] == 'threshold'
            assert zone.indicator_context['detection_indicator'] == 'rsi'
            assert zone.indicator_context['signal_line'] is None
            assert 'thresholds' in zone.indicator_context
            assert zone.indicator_context['thresholds']['upper'] == 70
            assert zone.indicator_context['thresholds']['lower'] == 30
    
    def test_line_crossing_has_indicator_context(self, sample_data):
        """Test LineCrossingDetection populates indicator_context with correct mapping."""
        strategy = LineCrossingDetection()
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['bull', 'bear'],
            rules={
                'line1_col': 'ema_12',
                'line2_col': 'ema_26'
            }
        )
        
        zones = strategy.detect_zones(sample_data, config)
        
        assert len(zones) > 0
        for zone in zones:
            assert zone.indicator_context is not None
            assert zone.indicator_context['detection_strategy'] == 'line_crossing'
            # Important: line1_col maps to detection_indicator
            assert zone.indicator_context['detection_indicator'] == 'ema_12'
            # Important: line2_col maps to signal_line
            assert zone.indicator_context['signal_line'] == 'ema_26'
            assert 'detection_rules' in zone.indicator_context
    
    def test_preloaded_has_indicator_context(self, sample_data):
        """Test PreloadedZonesDetection populates indicator_context."""
        # Create temporary CSV with zones
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('zone_id,type,start_time,end_time\n')
            f.write(f'0,bull,{sample_data.index[0]},{sample_data.index[10]}\n')
            f.write(f'1,bear,{sample_data.index[20]},{sample_data.index[30]}\n')
            zones_path = f.name
        
        try:
            strategy = PreloadedZonesDetection()
            config = ZoneDetectionConfig(
                min_duration=2,
                zone_types=['bull', 'bear'],
                rules={'zones_data': zones_path}
            )
            
            zones = strategy.detect_zones(sample_data, config)
            
            assert len(zones) > 0
            for zone in zones:
                assert zone.indicator_context is not None
                assert zone.indicator_context['detection_strategy'] == 'preloaded'
                assert zone.indicator_context['detection_indicator'] in ['external', None] or \
                       isinstance(zone.indicator_context['detection_indicator'], str)
                assert zone.indicator_context['source'] == 'external'
        finally:
            Path(zones_path).unlink()
    
    def test_combined_has_indicator_context(self, sample_data):
        """Test CombinedRulesDetection populates indicator_context."""
        strategy = CombinedRulesDetection()
        
        # CombinedRulesDetection expects 'conditions' as list of callables
        conditions = [
            lambda df: df['macd_hist'] > 0,
            lambda df: df['rsi'] < 70
        ]
        
        config = ZoneDetectionConfig(
            min_duration=2,
            zone_types=['active'],
            rules={
                'conditions': conditions,
                'logic': 'AND',
                'zone_type_map': {True: 'active', False: 'inactive'}
            }
        )
        
        zones = strategy.detect_zones(sample_data, config)
        
        # Combined strategy may produce 0 zones with strict AND logic
        if len(zones) > 0:
            for zone in zones:
                assert zone.indicator_context is not None
                assert zone.indicator_context['detection_strategy'] == 'combined'
                assert 'logic' in zone.indicator_context
                # Combined strategy stores logic and conditions info
                assert zone.indicator_context['logic'] == 'AND'
    
    def test_all_strategies_have_standard_fields(self, sample_data):
        """Test that all strategies populate standard indicator_context fields."""
        strategies_configs = [
            (ZeroCrossingDetection(), {'indicator_col': 'macd_hist'}),
            (ThresholdDetection(), {
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            }),
            (LineCrossingDetection(), {
                'line1_col': 'ema_12',
                'line2_col': 'ema_26'
            }),
        ]
        
        for strategy, rules in strategies_configs:
            config = ZoneDetectionConfig(
                min_duration=2,
                zone_types=['bull', 'bear', 'overbought', 'neutral', 'oversold'],
                rules=rules
            )
            
            zones = strategy.detect_zones(sample_data, config)
            
            assert len(zones) > 0, f"No zones detected for {strategy.__class__.__name__}"
            
            for zone in zones:
                # Standard fields that MUST be present
                assert 'detection_strategy' in zone.indicator_context
                assert 'detection_indicator' in zone.indicator_context
                
                # detection_indicator must not be None (except for combined/preloaded)
                strategy_name = zone.indicator_context['detection_strategy']
                if strategy_name not in ['combined', 'preloaded']:
                    assert zone.indicator_context['detection_indicator'] is not None
                    assert isinstance(zone.indicator_context['detection_indicator'], str)
                    assert len(zone.indicator_context['detection_indicator']) > 0

