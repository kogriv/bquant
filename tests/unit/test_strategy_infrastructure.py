"""
Tests for Strategy Pattern infrastructure (Phase 3.0).

Tests protocol contracts, registry functionality, and factory creation.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

# BQuant imports
from bquant.analysis.zones.strategies.base import (
    SwingMetrics,
    DivergenceMetrics,
    ShapeMetrics,
    VolumeMetrics,
    SwingCalculationStrategy,
    DivergenceCalculationStrategy,
    ShapeCalculationStrategy,
    VolumeCalculationStrategy
)
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.core.config import (
    create_swing_strategy,
    create_divergence_strategy,
    create_shape_strategy,
    create_volume_strategy
)

# Import real strategies to register them
from bquant.analysis.zones.strategies.swing import (
    ZigZagSwingStrategy,
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy
)


# Mock strategy implementations for testing

class MockSwingStrategy:
    """Mock swing strategy for testing."""
    
    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        return SwingMetrics(
            # Existing (6)
            num_swings=5,
            avg_rally_pct=1.5,
            avg_drop_pct=0.8,
            max_rally_pct=2.5,
            max_drop_pct=1.2,
            rally_to_drop_ratio=1.875,
            # Counters (2)
            rally_count=5,
            drop_count=5,
            # Minimums and distribution (6)
            min_rally_pct=0.5,
            min_drop_pct=0.3,
            rally_amplitude_std=0.5,
            drop_amplitude_std=0.3,
            rally_amplitude_median=1.4,
            drop_amplitude_median=0.75,
            # Duration (4)
            avg_rally_duration_bars=10.0,
            avg_drop_duration_bars=8.0,
            max_rally_duration_bars=15,
            max_drop_duration_bars=12,
            # Speed (4)
            avg_rally_speed_pct_per_bar=0.15,
            avg_drop_speed_pct_per_bar=0.10,
            max_rally_speed_pct_per_bar=0.25,
            max_drop_speed_pct_per_bar=0.15,
            # Symmetry (1)
            duration_symmetry=1.25,
            # Metadata
            strategy_name='mock',
            strategy_params={'threshold': self.threshold}
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'MockSwingStrategy',
            'description': 'Mock strategy for testing',
            'params': {'threshold': self.threshold}
        }


class MockDivergenceStrategy:
    """Mock divergence strategy for testing."""
    
    def calculate_divergence(self, zone_data: pd.DataFrame) -> DivergenceMetrics:
        return DivergenceMetrics(
            divergence_type='regular',
            divergence_count=2,
            divergence_strength=0.75,
            divergence_direction='bearish',
            strategy_name='mock',
            strategy_params={}
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'MockDivergenceStrategy',
            'description': 'Mock strategy for testing',
            'params': {}
        }


class MockShapeStrategy:
    """Mock shape strategy for testing."""
    
    def calculate_shape(self, zone_data: pd.DataFrame) -> ShapeMetrics:
        return ShapeMetrics(
            hist_skewness=0.5,
            hist_kurtosis=3.2,
            hist_smoothness=0.1,
            strategy_name='mock',
            strategy_params={}
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'MockShapeStrategy',
            'description': 'Mock strategy for testing',
            'params': {}
        }


class MockVolumeStrategy:
    """Mock volume strategy for testing."""
    
    def calculate_volume(self, zone_data: pd.DataFrame, baseline_volume: float) -> VolumeMetrics:
        return VolumeMetrics(
            volume_zone_ratio=1.5,
            volume_at_entry_change=0.2,
            volume_indicator_corr=0.75,
            avg_volume_zone=5000.0,
            strategy_name='mock',
            strategy_params={}
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'MockVolumeStrategy',
            'description': 'Mock strategy for testing',
            'params': {}
        }


class TestMetricsDataclasses:
    """Test metrics dataclasses and validation."""
    
    def test_swing_metrics_creation(self):
        """Test SwingMetrics creation and validation."""
        print("\nTesting SwingMetrics:")
        
        metrics = SwingMetrics(
            # Existing (6)
            num_swings=5,
            avg_rally_pct=1.5,
            avg_drop_pct=0.8,
            max_rally_pct=2.5,
            max_drop_pct=1.2,
            rally_to_drop_ratio=1.875,
            # Counters (2)
            rally_count=5,
            drop_count=5,
            # Minimums and distribution (6)
            min_rally_pct=0.5,
            min_drop_pct=0.3,
            rally_amplitude_std=0.5,
            drop_amplitude_std=0.3,
            rally_amplitude_median=1.4,
            drop_amplitude_median=0.75,
            # Duration (4)
            avg_rally_duration_bars=10.0,
            avg_drop_duration_bars=8.0,
            max_rally_duration_bars=15,
            max_drop_duration_bars=12,
            # Speed (4)
            avg_rally_speed_pct_per_bar=0.15,
            avg_drop_speed_pct_per_bar=0.10,
            max_rally_speed_pct_per_bar=0.25,
            max_drop_speed_pct_per_bar=0.15,
            # Symmetry (1)
            duration_symmetry=1.25,
            # Metadata
            strategy_name='test',
            strategy_params={'param1': 'value1'}
        )
        
        assert metrics.num_swings == 5
        assert metrics.avg_rally_pct == 1.5
        assert metrics.rally_to_drop_ratio == 1.875
        # Check new fields
        assert metrics.rally_count == 5
        assert metrics.duration_symmetry == 1.25
        
        print("[OK] SwingMetrics created successfully")
        
        # Test validation
        metrics.validate()
        print("[OK] SwingMetrics validation passed")
        
        # Test to_dict
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert 'num_swings' in metrics_dict
        assert 'strategy_name' in metrics_dict
        
        print("[OK] SwingMetrics to_dict() works")
    
    def test_divergence_metrics_creation(self):
        """Test DivergenceMetrics creation and validation."""
        print("\nTesting DivergenceMetrics:")
        
        metrics = DivergenceMetrics(
            divergence_type='regular',
            divergence_count=2,
            divergence_strength=0.75,
            divergence_direction='bearish',
            strategy_name='test',
            strategy_params={}
        )
        
        assert metrics.divergence_type == 'regular'
        assert metrics.divergence_count == 2
        
        print("[OK] DivergenceMetrics created successfully")
        
        # Test validation
        metrics.validate()
        print("[OK] DivergenceMetrics validation passed")
    
    def test_shape_metrics_creation(self):
        """Test ShapeMetrics creation and validation."""
        print("\nTesting ShapeMetrics:")
        
        metrics = ShapeMetrics(
            hist_skewness=0.5,
            hist_kurtosis=3.2,
            hist_smoothness=0.1,
            strategy_name='test',
            strategy_params={}
        )
        
        assert metrics.hist_skewness == 0.5
        assert metrics.hist_kurtosis == 3.2
        
        print("[OK] ShapeMetrics created successfully")
        
        # Test validation
        metrics.validate()
        print("[OK] ShapeMetrics validation passed")
    
    def test_volume_metrics_creation(self):
        """Test VolumeMetrics creation and validation."""
        print("\nTesting VolumeMetrics:")
        
        metrics = VolumeMetrics(
            volume_zone_ratio=1.5,
            volume_at_entry_change=0.2,
            volume_indicator_corr=0.75,
            avg_volume_zone=5000.0,
            strategy_name='test',
            strategy_params={}
        )
        
        assert metrics.volume_zone_ratio == 1.5
        assert metrics.volume_indicator_corr == 0.75
        
        print("[OK] VolumeMetrics created successfully")
        
        # Test validation
        metrics.validate()
        print("[OK] VolumeMetrics validation passed")


class TestStrategyRegistry:
    """Test strategy registry functionality."""
    
    def test_registry_registration(self):
        """Test strategy registration via decorators."""
        print("\nTesting StrategyRegistry registration:")
        
        # Register mock strategies
        StrategyRegistry.register_swing_strategy('mock_swing')(MockSwingStrategy)
        StrategyRegistry.register_divergence_strategy('mock_divergence')(MockDivergenceStrategy)
        StrategyRegistry.register_shape_strategy('mock_shape')(MockShapeStrategy)
        StrategyRegistry.register_volume_strategy('mock_volume')(MockVolumeStrategy)
        
        # Check registration
        assert 'mock_swing' in StrategyRegistry.list_swing_strategies()
        assert 'mock_divergence' in StrategyRegistry.list_divergence_strategies()
        assert 'mock_shape' in StrategyRegistry.list_shape_strategies()
        assert 'mock_volume' in StrategyRegistry.list_volume_strategies()
        
        print("[OK] All mock strategies registered successfully")
    
    def test_registry_retrieval(self):
        """Test strategy retrieval from registry."""
        print("\nTesting StrategyRegistry retrieval:")
        
        # Get strategies from registry
        swing_strategy = StrategyRegistry.get_swing_strategy('mock_swing', threshold=0.03)
        divergence_strategy = StrategyRegistry.get_divergence_strategy('mock_divergence')
        shape_strategy = StrategyRegistry.get_shape_strategy('mock_shape')
        volume_strategy = StrategyRegistry.get_volume_strategy('mock_volume')
        
        assert isinstance(swing_strategy, MockSwingStrategy)
        assert swing_strategy.threshold == 0.03
        
        print("[OK] Strategies retrieved successfully from registry")
        
        # Test get_metadata
        metadata = swing_strategy.get_metadata()
        assert isinstance(metadata, dict)
        assert 'name' in metadata
        
        print("[OK] Strategy metadata accessible")
    
    def test_registry_unknown_strategy(self):
        """Test error handling for unknown strategy."""
        print("\nTesting unknown strategy error handling:")
        
        try:
            StrategyRegistry.get_swing_strategy('nonexistent_strategy')
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert 'Unknown swing strategy' in str(e)
            assert 'Available' in str(e)
        
        print("[OK] Unknown strategy raises informative ValueError")
    
    def test_registry_stats(self):
        """Test registry statistics."""
        print("\nTesting registry statistics:")
        
        stats = StrategyRegistry.get_registry_stats()
        
        assert isinstance(stats, dict)
        assert 'swing' in stats
        assert 'divergence' in stats
        assert 'shape' in stats
        assert 'volume' in stats
        assert 'total' in stats
        
        assert stats['swing'] >= 1  # At least mock strategy
        assert stats['total'] >= 4  # At least 4 mock strategies
        
        print(f"[OK] Registry stats: {stats}")


class TestProtocolContracts:
    """Test that strategies conform to protocol contracts."""
    
    def test_swing_strategy_protocol(self):
        """Test SwingCalculationStrategy protocol."""
        print("\nTesting SwingCalculationStrategy protocol:")
        
        strategy = MockSwingStrategy()
        
        # Check protocol conformance
        assert isinstance(strategy, SwingCalculationStrategy)
        
        print("[OK] MockSwingStrategy conforms to SwingCalculationStrategy protocol")
        
        # Test calculate_swings method
        test_data = pd.DataFrame({
            'high': [100, 102, 101, 103, 102],
            'low': [98, 99, 98, 100, 99],
            'close': [99, 101, 100, 102, 101]
        })
        
        result = strategy.calculate_swings(test_data)
        assert isinstance(result, SwingMetrics)
        result.validate()
        
        print("[OK] calculate_swings() returns valid SwingMetrics")
    
    def test_divergence_strategy_protocol(self):
        """Test DivergenceCalculationStrategy protocol."""
        print("\nTesting DivergenceCalculationStrategy protocol:")
        
        strategy = MockDivergenceStrategy()
        
        assert isinstance(strategy, DivergenceCalculationStrategy)
        
        print("[OK] MockDivergenceStrategy conforms to protocol")
        
        test_data = pd.DataFrame({
            'close': [100, 101, 100, 102, 101],
            'high': [101, 102, 101, 103, 102],
            'low': [99, 100, 99, 101, 100],
            'macd': [0.5, 0.7, 0.6, 0.9, 0.8],
            'macd_hist': [0.1, 0.2, 0.15, 0.3, 0.25]
        })
        
        result = strategy.calculate_divergence(test_data)
        assert isinstance(result, DivergenceMetrics)
        result.validate()
        
        print("[OK] calculate_divergence() returns valid DivergenceMetrics")
    
    def test_shape_strategy_protocol(self):
        """Test ShapeCalculationStrategy protocol."""
        print("\nTesting ShapeCalculationStrategy protocol:")
        
        strategy = MockShapeStrategy()
        
        assert isinstance(strategy, ShapeCalculationStrategy)
        
        print("[OK] MockShapeStrategy conforms to protocol")
        
        test_data = pd.DataFrame({
            'macd_hist': [0.1, 0.3, 0.5, 0.4, 0.2]
        })
        
        result = strategy.calculate_shape(test_data)
        assert isinstance(result, ShapeMetrics)
        result.validate()
        
        print("[OK] calculate_shape() returns valid ShapeMetrics")
    
    def test_volume_strategy_protocol(self):
        """Test VolumeCalculationStrategy protocol."""
        print("\nTesting VolumeCalculationStrategy protocol:")
        
        strategy = MockVolumeStrategy()
        
        assert isinstance(strategy, VolumeCalculationStrategy)
        
        print("[OK] MockVolumeStrategy conforms to protocol")
        
        test_data = pd.DataFrame({
            'volume': [5000, 5500, 6000, 5800, 5200]
        })
        
        result = strategy.calculate_volume(test_data, baseline_volume=5000.0)
        assert isinstance(result, VolumeMetrics)
        result.validate()
        
        print("[OK] calculate_volume() returns valid VolumeMetrics")


class TestStrategyFactories:
    """Test strategy factory functions."""
    
    def test_create_swing_strategy_from_config(self):
        """Test creating swing strategy from config."""
        print("\nTesting create_swing_strategy():")
        
        # After Phase 3.1, default is 'zigzag' not 'none'
        strategy = create_swing_strategy()
        assert strategy is not None
        assert type(strategy).__name__ == 'ZigZagSwingStrategy'
        
        print(f"[OK] create_swing_strategy() returns {type(strategy).__name__}")
        
        # Test with explicit config
        strategy = create_swing_strategy({'type': 'mock_swing', 'params': {'threshold': 0.03}})
        assert isinstance(strategy, MockSwingStrategy)
        assert strategy.threshold == 0.03
        
        print("[OK] create_swing_strategy() creates strategy from config")
    
    def test_create_divergence_strategy_from_config(self):
        """Test creating divergence strategy from config."""
        print("\nTesting create_divergence_strategy():")
        
        strategy = create_divergence_strategy()
        assert strategy is None
        
        print("[OK] create_divergence_strategy() returns None when type='none'")
        
        strategy = create_divergence_strategy({'type': 'mock_divergence', 'params': {}})
        assert isinstance(strategy, MockDivergenceStrategy)
        
        print("[OK] create_divergence_strategy() creates strategy from config")
    
    def test_create_shape_strategy_from_config(self):
        """Test creating shape strategy from config."""
        print("\nTesting create_shape_strategy():")
        
        # After Phase 3.2, default is 'statistical' not 'none'
        strategy = create_shape_strategy()
        assert strategy is not None
        assert type(strategy).__name__ == 'StatisticalShapeStrategy'
        
        print(f"[OK] create_shape_strategy() returns {type(strategy).__name__}")
        
        strategy = create_shape_strategy({'type': 'mock_shape', 'params': {}})
        assert isinstance(strategy, MockShapeStrategy)
        
        print("[OK] create_shape_strategy() creates strategy from config")
    
    def test_create_volume_strategy_from_config(self):
        """Test creating volume strategy from config."""
        print("\nTesting create_volume_strategy():")
        
        strategy = create_volume_strategy()
        assert strategy is None
        
        print("[OK] create_volume_strategy() returns None when type='none'")
        
        strategy = create_volume_strategy({'type': 'mock_volume', 'params': {}})
        assert isinstance(strategy, MockVolumeStrategy)
        
        print("[OK] create_volume_strategy() creates strategy from config")


class TestZoneFeaturesAnalyzerIntegration:
    """Test ZoneFeaturesAnalyzer integration with strategies."""
    
    def test_analyzer_accepts_strategies(self):
        """Test that ZoneFeaturesAnalyzer accepts strategies in constructor."""
        print("\nTesting ZoneFeaturesAnalyzer strategy integration:")
        
        from bquant.analysis.zones import ZoneFeaturesAnalyzer
        
        # Create with custom strategies
        swing_strategy = MockSwingStrategy(threshold=0.025)
        divergence_strategy = MockDivergenceStrategy()
        shape_strategy = MockShapeStrategy()
        volume_strategy = MockVolumeStrategy()
        
        analyzer = ZoneFeaturesAnalyzer(
            min_duration=2,
            swing_strategy=swing_strategy,
            divergence_strategy=divergence_strategy,
            shape_strategy=shape_strategy,
            volume_strategy=volume_strategy
        )
        
        assert analyzer.swing_strategy == swing_strategy
        assert analyzer.divergence_strategy == divergence_strategy
        assert analyzer.shape_strategy == shape_strategy
        assert analyzer.volume_strategy == volume_strategy
        
        print("[OK] ZoneFeaturesAnalyzer accepts custom strategies")
    
    def test_analyzer_uses_default_strategies(self):
        """Test that analyzer uses default strategies from config."""
        print("\nTesting default strategy loading:")
        
        from bquant.analysis.zones import ZoneFeaturesAnalyzer
        
        # Create with defaults
        analyzer = ZoneFeaturesAnalyzer(min_duration=2)
        
        # After Phase 3.2: swing_strategy is ZigZag, shape_strategy is Statistical
        # divergence and volume still None
        assert analyzer.swing_strategy is not None
        assert type(analyzer.swing_strategy).__name__ == 'ZigZagSwingStrategy'
        assert analyzer.shape_strategy is not None
        assert type(analyzer.shape_strategy).__name__ == 'StatisticalShapeStrategy'
        assert analyzer.divergence_strategy is None
        assert analyzer.volume_strategy is None
        
        print(f"[OK] swing_strategy loaded as {type(analyzer.swing_strategy).__name__}")
        print(f"[OK] shape_strategy loaded as {type(analyzer.shape_strategy).__name__}")
        print("[OK] divergence and volume strategies are None (as per config)")


def run_strategy_infrastructure_tests():
    """Run all strategy infrastructure tests."""
    print("🚀 Running Strategy Infrastructure Tests (Phase 3.0)...")
    print("=" * 70)
    
    test_classes = [
        TestMetricsDataclasses(),
        TestStrategyRegistry(),
        TestProtocolContracts(),
        TestStrategyFactories(),
        TestZoneFeaturesAnalyzerIntegration()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n[DATA] {class_name}:")
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                print(f"[FAIL] {method_name}: FAILED - {e}")
    
    print("\n" + "=" * 70)
    print(f"[TARGET] Strategy Infrastructure Test Results:")
    print(f"   Total tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ALL STRATEGY INFRASTRUCTURE TESTS PASSED!")
        print("[OK] Phase 3.0 (Infrastructure) completed successfully")
        return True
    else:
        print("[WARN] Some tests failed")
        return False


if __name__ == "__main__":
    run_strategy_infrastructure_tests()

