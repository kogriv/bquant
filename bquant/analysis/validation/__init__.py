"""
Validation module for model robustness testing.

Provides tools for validating trading strategies and models:
- Out-of-sample testing
- Walk-forward analysis
- Sensitivity analysis
- Monte Carlo simulation

Every method compares one metric described by a :class:`MetricSpec` — key,
direction of quality, and whether a count is normalized per bar.
"""

from .suite import (
    MetricSpec,
    ModelValidationResult,
    ValidationSuite
)

__all__ = [
    'MetricSpec',
    'ModelValidationResult',
    'ValidationSuite'
]
