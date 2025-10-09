"""
ZigZag Swing Strategy - swing detection using pandas-ta ZigZag indicator.

This strategy uses the pandas-ta ZigZag algorithm to identify significant
price swings within a trading zone, filtering out noise and focusing on
meaningful price movements.
"""

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd
import numpy as np

from ..base import SwingMetrics, SwingCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('zigzag')
@dataclass
class ZigZagSwingStrategy:
    """
    Swing detection using pandas-ta ZigZag algorithm.
    
    This strategy identifies swing points by finding price reversals that exceed
    a specified percentage threshold. It provides comprehensive metrics including
    amplitudes, durations, speeds, and distributions of both rally and drop movements.
    
    Attributes:
        legs: Number of bars to confirm a pivot (default: 10)
        deviation: Minimum percentage move to qualify as swing (default: 0.05 = 5%)
    """
    legs: int = 10
    deviation: float = 0.05  # 5% minimum movement
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate comprehensive swing metrics using ZigZag algorithm.
        
        Args:
            zone_data: DataFrame with columns: high, low, close, open
        
        Returns:
            SwingMetrics with all 23 fields populated
        
        Raises:
            ValueError: If zone_data is empty or missing required columns
        """
        # Validate input
        required_cols = ['high', 'low', 'close']
        if not all(col in zone_data.columns for col in required_cols):
            raise ValueError(f"zone_data must contain columns: {required_cols}")
        
        if len(zone_data) == 0:
            raise ValueError("zone_data cannot be empty")
        
        try:
            # Import LibraryManager dynamically to avoid circular imports
            from .....indicators import LibraryManager
            
            # Create ZigZag indicator
            zigzag = LibraryManager.create_indicator(
                'pandas_ta',
                'zigzag',
                legs=self.legs,
                deviation=self.deviation
            )
            
            # Calculate ZigZag
            result = zigzag.calculate(zone_data)
            
            # Extract swing data
            # ZigZag may return 1-3 columns depending on results
            # Usually: Column 0=signal, 1=values, 2=distance
            # But if no swings found, may return only 1 column
            
            if result.data.shape[1] < 2:
                # Not enough columns - no swings detected
                logger.debug(
                    f"ZigZag returned only {result.data.shape[1]} column(s), no swings detected"
                )
                return self._empty_metrics()
            
            swing_signal = result.data.iloc[:, 0]
            swing_values = result.data.iloc[:, 1]
            
            # Get swing points (non-NaN values)
            swing_points = swing_values.dropna()
            
            # If not enough swings, return empty metrics
            if len(swing_points) < 2:
                logger.debug(
                    f"Not enough swings detected: {len(swing_points)} points "
                    f"(legs={self.legs}, deviation={self.deviation})"
                )
                return self._empty_metrics()
            
            # Calculate detailed swing metrics
            return self._calculate_swing_metrics(swing_points, zone_data.index)
            
        except Exception as e:
            logger.error(f"ZigZag swing calculation failed: {e}", exc_info=True)
            # Return empty metrics on error
            return self._empty_metrics()
    
    def _calculate_swing_metrics(self, swing_points: pd.Series, 
                                 time_index: pd.Index) -> SwingMetrics:
        """
        Calculate comprehensive metrics from swing points.
        
        Args:
            swing_points: Series of swing prices (only pivot points, no NaN)
            time_index: Original time index for duration calculation
        
        Returns:
            SwingMetrics with all fields populated
        """
        rallies = []  # UP movements
        drops = []    # DOWN movements
        rally_durations = []
        drop_durations = []
        
        # Calculate movements between swing points
        for i in range(1, len(swing_points)):
            prev_price = swing_points.iloc[i-1]
            curr_price = swing_points.iloc[i]
            
            # Get indices in original data for duration calculation
            prev_idx = swing_points.index[i-1]
            curr_idx = swing_points.index[i]
            
            # Find positions in time_index
            prev_pos = time_index.get_loc(prev_idx)
            curr_pos = time_index.get_loc(curr_idx)
            duration_bars = curr_pos - prev_pos
            
            # Calculate price change percentage
            price_change_pct = (curr_price / prev_price - 1) * 100
            
            if price_change_pct > 0:
                # Rally (up movement)
                rallies.append({
                    'amplitude_pct': price_change_pct,
                    'duration_bars': duration_bars,
                    'speed_pct_per_bar': price_change_pct / duration_bars if duration_bars > 0 else 0
                })
            else:
                # Drop (down movement)
                drops.append({
                    'amplitude_pct': abs(price_change_pct),
                    'duration_bars': duration_bars,
                    'speed_pct_per_bar': abs(price_change_pct) / duration_bars if duration_bars > 0 else 0
                })
        
        # Calculate aggregate metrics
        rally_count = len(rallies)
        drop_count = len(drops)
        
        # Amplitude metrics
        if rally_count > 0:
            rally_amps = [r['amplitude_pct'] for r in rallies]
            avg_rally_pct = np.mean(rally_amps)
            max_rally_pct = np.max(rally_amps)
            min_rally_pct = np.min(rally_amps)
            rally_amplitude_std = np.std(rally_amps)
            rally_amplitude_median = np.median(rally_amps)
        else:
            avg_rally_pct = max_rally_pct = min_rally_pct = 0.0
            rally_amplitude_std = rally_amplitude_median = 0.0
        
        if drop_count > 0:
            drop_amps = [d['amplitude_pct'] for d in drops]
            avg_drop_pct = np.mean(drop_amps)
            max_drop_pct = np.max(drop_amps)
            min_drop_pct = np.min(drop_amps)
            drop_amplitude_std = np.std(drop_amps)
            drop_amplitude_median = np.median(drop_amps)
        else:
            avg_drop_pct = max_drop_pct = min_drop_pct = 0.0
            drop_amplitude_std = drop_amplitude_median = 0.0
        
        # Duration metrics
        if rally_count > 0:
            rally_durs = [r['duration_bars'] for r in rallies]
            avg_rally_duration_bars = float(np.mean(rally_durs))
            max_rally_duration_bars = int(np.max(rally_durs))
        else:
            avg_rally_duration_bars = 0.0
            max_rally_duration_bars = 0
        
        if drop_count > 0:
            drop_durs = [d['duration_bars'] for d in drops]
            avg_drop_duration_bars = float(np.mean(drop_durs))
            max_drop_duration_bars = int(np.max(drop_durs))
        else:
            avg_drop_duration_bars = 0.0
            max_drop_duration_bars = 0
        
        # Speed metrics
        if rally_count > 0:
            rally_speeds = [r['speed_pct_per_bar'] for r in rallies]
            avg_rally_speed_pct_per_bar = np.mean(rally_speeds)
            max_rally_speed_pct_per_bar = np.max(rally_speeds)
        else:
            avg_rally_speed_pct_per_bar = max_rally_speed_pct_per_bar = 0.0
        
        if drop_count > 0:
            drop_speeds = [d['speed_pct_per_bar'] for d in drops]
            avg_drop_speed_pct_per_bar = np.mean(drop_speeds)
            max_drop_speed_pct_per_bar = np.max(drop_speeds)
        else:
            avg_drop_speed_pct_per_bar = max_drop_speed_pct_per_bar = 0.0
        
        # Ratio and symmetry metrics
        rally_to_drop_ratio = avg_rally_pct / avg_drop_pct if avg_drop_pct > 0 else 0.0
        duration_symmetry = (avg_rally_duration_bars / avg_drop_duration_bars 
                           if avg_drop_duration_bars > 0 else 0.0)
        
        # Total swings (pairs)
        num_swings = min(rally_count, drop_count)  # Complete rally-drop pairs
        
        # Create result
        metrics = SwingMetrics(
            # Existing fields
            num_swings=num_swings,
            avg_rally_pct=avg_rally_pct,
            avg_drop_pct=avg_drop_pct,
            max_rally_pct=max_rally_pct,
            max_drop_pct=max_drop_pct,
            rally_to_drop_ratio=rally_to_drop_ratio,
            
            # Counters
            rally_count=rally_count,
            drop_count=drop_count,
            
            # Minimums and distribution
            min_rally_pct=min_rally_pct,
            min_drop_pct=min_drop_pct,
            rally_amplitude_std=rally_amplitude_std,
            drop_amplitude_std=drop_amplitude_std,
            rally_amplitude_median=rally_amplitude_median,
            drop_amplitude_median=drop_amplitude_median,
            
            # Duration
            avg_rally_duration_bars=avg_rally_duration_bars,
            avg_drop_duration_bars=avg_drop_duration_bars,
            max_rally_duration_bars=max_rally_duration_bars,
            max_drop_duration_bars=max_drop_duration_bars,
            
            # Speed
            avg_rally_speed_pct_per_bar=avg_rally_speed_pct_per_bar,
            avg_drop_speed_pct_per_bar=avg_drop_speed_pct_per_bar,
            max_rally_speed_pct_per_bar=max_rally_speed_pct_per_bar,
            max_drop_speed_pct_per_bar=max_drop_speed_pct_per_bar,
            
            # Symmetry
            duration_symmetry=duration_symmetry,
            
            # Metadata
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation}
        )
        
        # Validate before returning
        metrics.validate()
        
        logger.debug(
            f"ZigZag metrics calculated: {rally_count} rallies, {drop_count} drops, "
            f"ratio={rally_to_drop_ratio:.2f}, duration_symmetry={duration_symmetry:.2f}"
        )
        
        return metrics
    
    def _empty_metrics(self) -> SwingMetrics:
        """Return empty metrics when no swings detected."""
        return SwingMetrics(
            # Existing fields
            num_swings=0,
            avg_rally_pct=0.0,
            avg_drop_pct=0.0,
            max_rally_pct=0.0,
            max_drop_pct=0.0,
            rally_to_drop_ratio=0.0,
            
            # Counters
            rally_count=0,
            drop_count=0,
            
            # Minimums and distribution
            min_rally_pct=0.0,
            min_drop_pct=0.0,
            rally_amplitude_std=0.0,
            drop_amplitude_std=0.0,
            rally_amplitude_median=0.0,
            drop_amplitude_median=0.0,
            
            # Duration
            avg_rally_duration_bars=0.0,
            avg_drop_duration_bars=0.0,
            max_rally_duration_bars=0,
            max_drop_duration_bars=0,
            
            # Speed
            avg_rally_speed_pct_per_bar=0.0,
            avg_drop_speed_pct_per_bar=0.0,
            max_rally_speed_pct_per_bar=0.0,
            max_drop_speed_pct_per_bar=0.0,
            
            # Symmetry
            duration_symmetry=0.0,
            
            # Metadata
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation}
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'ZigZag',
            'description': 'Swing detection via pandas-ta ZigZag algorithm',
            'params': {
                'legs': self.legs,
                'deviation': self.deviation
            },
            'source': 'pandas-ta library via LibraryManager',
            'calculates': [
                'swing amplitudes (rally/drop)',
                'swing durations (bars)',
                'swing speeds (% per bar)',
                'distributions (std, median)',
                'symmetry metrics'
            ]
        }

