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
    'StrategyRegistry'
]

