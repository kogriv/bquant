"""
Validation module for model robustness testing.

Provides tools for validating trading strategies and models:
- Out-of-sample testing
- Walk-forward analysis  
- Sensitivity analysis
- Monte Carlo simulation
"""

from .suite import (
    ValidationResult,
    ValidationSuite
)

__all__ = [
    'ValidationResult',
    'ValidationSuite'
]

