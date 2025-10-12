"""
Volatility calculation strategies.

This module contains strategies for assessing zone volatility using
Bollinger Bands, ATR, and other volatility indicators.
"""

from .combined import CombinedVolatilityStrategy

__all__ = ['CombinedVolatilityStrategy']

