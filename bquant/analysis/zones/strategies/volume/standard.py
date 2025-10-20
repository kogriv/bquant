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
    
    UNIVERSAL STRATEGY (v2.1):
    - Works with ANY oscillator for volume-indicator correlation
    - Requires explicit indicator_col parameter (no auto-detection)
    - Backward compatible when indicator_col not provided
    
    Calculates:
    - Volume zone ratio: avg_volume_zone / baseline_volume
    - Volume change at entry: % change at zone start
    - Volume-indicator correlation: correlation between volume and any indicator (v2.1)
    - Average volume in zone
    
    Attributes:
        baseline_window: Number of bars before zone to calculate baseline (default: 50)
        correlation_min_periods: Minimum periods for correlation calculation (default: 3)
    """
    
    baseline_window: int = 50
    correlation_min_periods: int = 3
    
    def calculate_volume(self, 
                        zone_data: pd.DataFrame, 
                        baseline_volume: Optional[float] = None,
                        indicator_col: Optional[str] = None) -> VolumeMetrics:
        """
        Calculate volume metrics for a zone.
        
        UNIVERSAL METHOD (v2.1):
        Works with ANY oscillator for volume-indicator correlation.
        
        Args:
            zone_data: DataFrame with column: volume (and optionally oscillator column)
            baseline_volume: Pre-calculated baseline volume (if None, will attempt to estimate)
            indicator_col: Optional oscillator column for volume-indicator correlation
                          Examples: 'macd_hist', 'RSI_14', 'AO_5_34', 'CCI_20'
        
        Returns:
            VolumeMetrics with validated data
        
        Raises:
            ValueError: If volume column is missing
        
        Examples:
            # Without indicator correlation
            metrics = strategy.calculate_volume(zone_data, baseline_volume=1500)
            
            # With MACD correlation (legacy)
            metrics = strategy.calculate_volume(zone_data, baseline_volume=1500, indicator_col='macd_hist')
            
            # With RSI correlation (v2.1)
            metrics = strategy.calculate_volume(zone_data, baseline_volume=1500, indicator_col='RSI_14')
            
            # With AO correlation
            metrics = strategy.calculate_volume(zone_data, baseline_volume=1500, indicator_col='AO_5_34')
        
        Note:
            If baseline_volume is not provided and cannot be calculated,
            volume_zone_ratio and volume_at_entry_change will be None.
            
            If indicator_col is not provided or column doesn't exist,
            volume_indicator_corr will be None.
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
            return self._empty_metrics(indicator_col)
        
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
            
            # Calculate volume-indicator correlation (v2.1 - UNIVERSAL)
            volume_indicator_corr = None
            if indicator_col and indicator_col in zone_data.columns and len(zone_data) >= self.correlation_min_periods:
                try:
                    volume_indicator_corr = float(volume.corr(zone_data[indicator_col]))
                    # Handle NaN correlation
                    if pd.isna(volume_indicator_corr):
                        volume_indicator_corr = None
                except Exception as e:
                    logger.debug(f"Failed to calculate volume-{indicator_col} correlation: {e}")
                    volume_indicator_corr = None
            
            result = VolumeMetrics(
                volume_zone_ratio=volume_zone_ratio,
                volume_at_entry_change=volume_at_entry_change,
                volume_indicator_corr=volume_indicator_corr,  # v2.1: renamed field
                avg_volume_zone=avg_volume_zone,
                strategy_name='standard',
                strategy_params={
                    'baseline_window': self.baseline_window,
                    'correlation_min_periods': self.correlation_min_periods,
                    'indicator_col': indicator_col  # v2.1: track which indicator was used
                }
            )
            
            result.validate()
            return result
            
        except Exception as e:
            logger.error(f"Volume calculation failed: {e}", exc_info=True)
            return self._empty_metrics(indicator_col)
    
    def _empty_metrics(self, indicator_col: Optional[str] = None) -> VolumeMetrics:
        """Return empty/none volume metrics."""
        return VolumeMetrics(
            volume_zone_ratio=None,
            volume_at_entry_change=None,
            volume_indicator_corr=None,  # v2.1: renamed field
            avg_volume_zone=None,
            strategy_name='standard',
            strategy_params={
                'baseline_window': self.baseline_window,
                'correlation_min_periods': self.correlation_min_periods,
                'indicator_col': indicator_col
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        return {
            'name': 'Standard',
            'description': 'Volume analysis using zone/baseline ratio and oscillator correlation (UNIVERSAL - works with any oscillator)',
            'params': {
                'baseline_window': self.baseline_window,
                'correlation_min_periods': self.correlation_min_periods
            },
            'supported_indicators': 'ANY oscillator (MACD, RSI, AO, CCI, Stochastic, custom, etc.)',
            'source': 'Classic volume analysis methodology'
        }

