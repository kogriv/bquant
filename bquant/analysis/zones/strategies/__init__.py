"""
Strategies module for zone analysis metrics calculation.

Provides extensible architecture for metric calculation using Strategy Pattern.
"""

from .base import (
    SwingMetrics,
    DivergenceMetrics,
    ShapeMetrics,
    VolumeMetrics,
    SwingCalculationStrategy,
    DivergenceCalculationStrategy,
    ShapeCalculationStrategy,
    VolumeCalculationStrategy
)

from .registry import StrategyRegistry

# Import concrete strategies to trigger registration via decorators
from .swing import (
    ZigZagSwingStrategy,
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy
)

from .divergence import ClassicDivergenceStrategy

from .shape import StatisticalShapeStrategy

from .volume import StandardVolumeStrategy

from .volatility import CombinedVolatilityStrategy

__all__ = [
    # Metrics dataclasses
    'SwingMetrics',
    'DivergenceMetrics',
    'ShapeMetrics',
    'VolumeMetrics',
    # Strategy protocols
    'SwingCalculationStrategy',
    'DivergenceCalculationStrategy',
    'ShapeCalculationStrategy',
    'VolumeCalculationStrategy',
    # Registry
    'StrategyRegistry',
    # Concrete strategies
    'ZigZagSwingStrategy',
    'FindPeaksSwingStrategy',
    'PivotPointsSwingStrategy',
    'ClassicDivergenceStrategy',
    'StatisticalShapeStrategy',
    'StandardVolumeStrategy',
    'CombinedVolatilityStrategy'
]

