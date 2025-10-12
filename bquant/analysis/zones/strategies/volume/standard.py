"""
Standard Volume Analysis Strategy.

Analyzes trading volume within a zone relative to baseline to assess
trend strength and conviction. Volume confirmation is a key indicator
of sustainable price movement.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from ..base import VolumeMetrics, VolumeCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_volume_strategy('standard')
@dataclass
class StandardVolumeStrategy:
    """
    Standard volume analysis using volume ratio and correlation.
    
    Calculates:
    - Volume zone ratio: avg_volume_zone / baseline_volume
    - Volume change at entry: % change at zone start
    - Volume-MACD correlation: correlation between volume and macd_hist
    - Average volume in zone
    
    Attributes:
        baseline_window: Number of bars before zone to calculate baseline (default: 50)
        correlation_min_periods: Minimum periods for correlation calculation (default: 3)
    """
    
    baseline_window: int = 50
    correlation_min_periods: int = 3
    
    def calculate_volume(self, zone_data: pd.DataFrame, baseline_volume: Optional[float] = None) -> VolumeMetrics:
        """
        Calculate volume metrics for a zone.
        
        Args:
            zone_data: DataFrame with column: volume (and optionally macd_hist)
            baseline_volume: Pre-calculated baseline volume (if None, will attempt to estimate)
        
        Returns:
            VolumeMetrics with validated data
        
        Raises:
            ValueError: If volume column is missing
        
        Note:
            If baseline_volume is not provided and cannot be calculated,
            volume_zone_ratio and volume_at_entry_change will be None.
        """
        # Validate input
        if zone_data.empty:
            raise ValueError("Zone data cannot be empty")
        
        if 'volume' not in zone_data.columns:
            raise ValueError("Zone data must contain 'volume' column")
        
        # Check if volume has data
        volume = zone_data['volume']
        if volume.isna().all() or (volume == 0).all():
            logger.debug("Volume column exists but contains no valid data")
            return self._empty_metrics()
        
        try:
            # Calculate average volume in zone
            avg_volume_zone = float(volume.mean())
            
            # Calculate volume zone ratio (if baseline provided)
            volume_zone_ratio = None
            if baseline_volume is not None and baseline_volume > 0:
                volume_zone_ratio = avg_volume_zone / baseline_volume
            
            # Calculate volume change at entry
            volume_at_entry_change = None
            if baseline_volume is not None and baseline_volume > 0:
                volume_at_entry = float(volume.iloc[0])
                volume_at_entry_change = (volume_at_entry / baseline_volume) - 1
            
            # Calculate volume-MACD correlation (if macd_hist available)
            volume_macd_corr = None
            if 'macd_hist' in zone_data.columns and len(zone_data) >= self.correlation_min_periods:
                try:
                    volume_macd_corr = float(volume.corr(zone_data['macd_hist']))
                    # Handle NaN correlation
                    if pd.isna(volume_macd_corr):
                        volume_macd_corr = None
                except Exception as e:
                    logger.debug(f"Failed to calculate volume-MACD correlation: {e}")
                    volume_macd_corr = None
            
            result = VolumeMetrics(
                volume_zone_ratio=volume_zone_ratio,
                volume_at_entry_change=volume_at_entry_change,
                volume_macd_corr=volume_macd_corr,
                avg_volume_zone=avg_volume_zone,
                strategy_name='standard',
                strategy_params={
                    'baseline_window': self.baseline_window,
                    'correlation_min_periods': self.correlation_min_periods
                }
            )
            
            result.validate()
            return result
            
        except Exception as e:
            logger.error(f"Volume calculation failed: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _empty_metrics(self) -> VolumeMetrics:
        """Return empty/none volume metrics."""
        return VolumeMetrics(
            volume_zone_ratio=None,
            volume_at_entry_change=None,
            volume_macd_corr=None,
            avg_volume_zone=None,
            strategy_name='standard',
            strategy_params={
                'baseline_window': self.baseline_window,
                'correlation_min_periods': self.correlation_min_periods
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        return {
            'name': 'Standard',
            'description': 'Volume analysis using zone/baseline ratio and MACD correlation',
            'params': {
                'baseline_window': self.baseline_window,
                'correlation_min_periods': self.correlation_min_periods
            },
            'source': 'Classic volume analysis methodology'
        }

