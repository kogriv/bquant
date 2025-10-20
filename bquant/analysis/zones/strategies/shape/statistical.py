"""
Statistical Shape Strategy - universal shape analysis for ANY oscillator.

This strategy analyzes the shape of oscillator within a zone using
statistical moments (skewness and kurtosis) to classify zone archetypes.

UNIVERSAL (v2.1):
- Works with ANY oscillator: MACD, RSI, AO, CCI, Stochastic, custom, etc.
- Requires explicit indicator_col parameter
- NO hardcoded indicator names

Examples:
    strategy.calculate(data, indicator_col='macd_hist')  # MACD
    strategy.calculate(data, indicator_col='RSI_14')     # RSI
    strategy.calculate(data, indicator_col='AO_5_34')    # AO
"""

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis

from ..base import ShapeMetrics, ShapeCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_shape_strategy('statistical')
@dataclass
class StatisticalShapeStrategy:
    """
    Shape analysis using statistical moments (skewness and kurtosis).
    
    UNIVERSAL STRATEGY (v2.1):
    - Works with ANY oscillator (MACD, RSI, AO, Stochastic, etc.)
    - Analyzes shape of oscillator "bump" to classify zone archetypes
    - Requires explicit indicator_col parameter (no auto-detection)
    
    Metrics:
    - Skewness: asymmetry of the distribution (early vs late impulse)
    - Kurtosis: peakedness (sharp spike vs smooth wave)
    - Smoothness: standard deviation of the derivative (choppy vs smooth)
    
    Attributes:
        calculate_smoothness: Whether to calculate smoothness metric (default: True)
        bias_correction: Whether to use bias correction in skewness/kurtosis (default: True)
    """
    calculate_smoothness: bool = True
    bias_correction: bool = True
    
    def calculate(self, zone_data: pd.DataFrame, indicator_col: str) -> ShapeMetrics:
        """
        Calculate shape metrics from ANY oscillator.
        
        Args:
            zone_data: DataFrame with oscillator column
            indicator_col: Name of column to analyze (e.g., 'macd_hist', 'RSI_14', 'AO_5_34')
        
        Returns:
            ShapeMetrics with skewness, kurtosis, and optionally smoothness
        
        Raises:
            ValueError: If zone_data is empty or indicator_col not found
        
        Examples:
            # MACD histogram
            metrics = strategy.calculate(zone_data, indicator_col='macd_hist')
            
            # RSI
            metrics = strategy.calculate(zone_data, indicator_col='RSI_14')
            
            # Awesome Oscillator
            metrics = strategy.calculate(zone_data, indicator_col='AO_5_34')
        """
        # Validate input
        if indicator_col not in zone_data.columns:
            raise ValueError(
                f"Indicator column '{indicator_col}' not found. "
                f"Available: {list(zone_data.columns)}"
            )
        
        if len(zone_data) == 0:
            raise ValueError("zone_data cannot be empty")
        
        try:
            oscillator = zone_data[indicator_col].dropna()
            
            if len(oscillator) < 3:
                # Need at least 3 points for meaningful statistics
                logger.debug(f"Not enough data points for shape analysis: {len(oscillator)}")
                return self._minimal_metrics()
            
            # Calculate skewness
            # Positive: peak at the beginning (early impulse)
            # Negative: peak at the end (late impulse)
            # Near 0: symmetric distribution
            hist_skewness = float(skew(oscillator, bias=self.bias_correction))
            
            # Calculate kurtosis (excess kurtosis by default in scipy)
            # > 3: sharp peak (leptokurtic)
            # ≈ 3: normal distribution (mesokurtic)
            # < 3: flat top (platykurtic)
            # Note: scipy.stats.kurtosis returns excess kurtosis (kurtosis - 3)
            # So we add 3 to get absolute kurtosis for comparison with 3
            hist_kurtosis_excess = float(kurtosis(oscillator, bias=self.bias_correction))
            hist_kurtosis = hist_kurtosis_excess + 3.0  # Convert to absolute kurtosis
            
            # Calculate smoothness (optional)
            hist_smoothness = None
            if self.calculate_smoothness:
                # Smoothness = std of first derivative
                # Low value = smooth curve, high value = choppy/erratic
                oscillator_diff = oscillator.diff().dropna()
                if len(oscillator_diff) > 0:
                    hist_smoothness = float(oscillator_diff.std())
                else:
                    hist_smoothness = 0.0
            
            # Create result
            metrics = ShapeMetrics(
                hist_skewness=hist_skewness,
                hist_kurtosis=hist_kurtosis,
                hist_smoothness=hist_smoothness,
                strategy_name='statistical',
                strategy_params={
                    'calculate_smoothness': self.calculate_smoothness,
                    'bias_correction': self.bias_correction,
                    'indicator_col': indicator_col  # Track what was used (v2.1)
                }
            )
            
            # Validate
            metrics.validate()
            
            smoothness_str = f"{hist_smoothness:.4f}" if hist_smoothness is not None else "N/A"
            logger.debug(
                f"Shape metrics calculated for '{indicator_col}': "
                f"skewness={hist_skewness:.2f}, kurtosis={hist_kurtosis:.2f}, smoothness={smoothness_str}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Statistical shape calculation failed for '{indicator_col}': {e}", exc_info=True)
            return self._minimal_metrics()
    
    def _minimal_metrics(self) -> ShapeMetrics:
        """Return minimal metrics when calculation fails."""
        return ShapeMetrics(
            hist_skewness=0.0,
            hist_kurtosis=3.0,  # Normal distribution kurtosis
            hist_smoothness=0.0 if self.calculate_smoothness else None,
            strategy_name='statistical',
            strategy_params={
                'calculate_smoothness': self.calculate_smoothness,
                'bias_correction': self.bias_correction,
                'indicator_col': None  # Not available in error case
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'Statistical',
            'description': 'Shape analysis via skewness, kurtosis, and smoothness (UNIVERSAL - works with any oscillator)',
            'params': {
                'calculate_smoothness': self.calculate_smoothness,
                'bias_correction': self.bias_correction
            },
            'source': 'scipy.stats (skew, kurtosis)',
            'supported_indicators': 'ANY numeric column (MACD, RSI, AO, CCI, Stochastic, custom, etc.)',
            'metrics': {
                'hist_skewness': {
                    'interpretation': {
                        '> 0.5': 'Early impulse (peak at beginning)',
                        '≈ 0': 'Symmetric shape',
                        '< -0.5': 'Late impulse (peak at end)'
                    }
                },
                'hist_kurtosis': {
                    'interpretation': {
                        '> 5': 'Sharp spike (leptokurtic)',
                        '≈ 3': 'Normal distribution',
                        '< 1': 'Flat wave (platykurtic)'
                    }
                },
                'hist_smoothness': {
                    'interpretation': {
                        'low': 'Smooth curve',
                        'high': 'Choppy/erratic'
                    }
                }
            },
            'use_cases': [
                'Zone archetype classification',
                'Improved clustering (K-Means)',
                'Pattern recognition',
                'Quality assessment'
            ]
        }

