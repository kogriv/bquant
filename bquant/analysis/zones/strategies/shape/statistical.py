"""
Statistical Shape Strategy - shape analysis using skewness and kurtosis.

This strategy analyzes the shape of MACD histogram within a zone using
statistical moments (skewness and kurtosis) to classify zone archetypes.
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
    
    Analyzes the shape of MACD histogram "bump" to classify zone archetypes:
    - Skewness: asymmetry of the distribution (early vs late impulse)
    - Kurtosis: peakedness (sharp spike vs smooth wave)
    - Smoothness: standard deviation of the derivative (choppy vs smooth)
    
    Attributes:
        calculate_smoothness: Whether to calculate smoothness metric (default: True)
        bias_correction: Whether to use bias correction in skewness/kurtosis (default: True)
    """
    calculate_smoothness: bool = True
    bias_correction: bool = True
    
    def calculate(self, zone_data: pd.DataFrame) -> ShapeMetrics:
        """
        Calculate shape metrics from MACD histogram.
        
        Args:
            zone_data: DataFrame with 'macd_hist' column
        
        Returns:
            ShapeMetrics with skewness, kurtosis, and optionally smoothness
        
        Raises:
            ValueError: If zone_data is empty or missing macd_hist column
        """
        # Validate input
        if 'macd_hist' not in zone_data.columns:
            raise ValueError("zone_data must contain 'macd_hist' column")
        
        if len(zone_data) == 0:
            raise ValueError("zone_data cannot be empty")
        
        try:
            hist = zone_data['macd_hist'].dropna()
            
            if len(hist) < 3:
                # Need at least 3 points for meaningful statistics
                logger.debug(f"Not enough data points for shape analysis: {len(hist)}")
                return self._minimal_metrics()
            
            # Calculate skewness
            # Positive: peak at the beginning (early impulse)
            # Negative: peak at the end (late impulse)
            # Near 0: symmetric distribution
            hist_skewness = float(skew(hist, bias=self.bias_correction))
            
            # Calculate kurtosis (excess kurtosis by default in scipy)
            # > 3: sharp peak (leptokurtic)
            # ≈ 3: normal distribution (mesokurtic)
            # < 3: flat top (platykurtic)
            # Note: scipy.stats.kurtosis returns excess kurtosis (kurtosis - 3)
            # So we add 3 to get absolute kurtosis for comparison with 3
            hist_kurtosis_excess = float(kurtosis(hist, bias=self.bias_correction))
            hist_kurtosis = hist_kurtosis_excess + 3.0  # Convert to absolute kurtosis
            
            # Calculate smoothness (optional)
            hist_smoothness = None
            if self.calculate_smoothness:
                # Smoothness = std of first derivative
                # Low value = smooth curve, high value = choppy/erratic
                hist_diff = hist.diff().dropna()
                if len(hist_diff) > 0:
                    hist_smoothness = float(hist_diff.std())
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
                    'bias_correction': self.bias_correction
                }
            )
            
            # Validate
            metrics.validate()
            
            smoothness_str = f"{hist_smoothness:.4f}" if hist_smoothness is not None else "N/A"
            logger.debug(
                f"Shape metrics calculated: skewness={hist_skewness:.2f}, "
                f"kurtosis={hist_kurtosis:.2f}, smoothness={smoothness_str}"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Statistical shape calculation failed: {e}", exc_info=True)
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
                'bias_correction': self.bias_correction
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'Statistical',
            'description': 'Shape analysis via skewness, kurtosis, and smoothness',
            'params': {
                'calculate_smoothness': self.calculate_smoothness,
                'bias_correction': self.bias_correction
            },
            'source': 'scipy.stats (skew, kurtosis)',
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

