"""
Divergence detection strategies.

This module contains various strategies for detecting divergences between
price and MACD indicator.
"""

from .classic import ClassicDivergenceStrategy

__all__ = ['ClassicDivergenceStrategy']
