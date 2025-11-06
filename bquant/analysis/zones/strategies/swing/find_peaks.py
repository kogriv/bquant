"""
FindPeaks Swing Strategy - swing detection using scipy.signal.find_peaks.

This strategy uses scipy's find_peaks algorithm to identify local extrema
and filters them by minimum amplitude to get significant swings.
"""

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

from ..base import SwingMetrics, SwingCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('find_peaks')
@dataclass
class FindPeaksSwingStrategy:
    """
    Swing detection using scipy.signal.find_peaks algorithm.
    
    This strategy finds all local maxima and minima using scipy's find_peaks,
    then filters them by minimum amplitude threshold to identify significant
    swings. Provides full control over peak detection parameters.
    
    Attributes:
        prominence: Required prominence (height) of peaks (default: None = auto)
        distance: Minimum number of bars between peaks (default: 5)
        min_amplitude_pct: Minimum movement percentage to qualify as swing (default: 0.02 = 2%)
    """
    prominence: float = None  # Auto-calculate if None
    distance: int = 5
    min_amplitude_pct: float = 0.02  # 2% minimum movement
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate comprehensive swing metrics using find_peaks algorithm.
        
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
            # Auto-calculate prominence if not specified
            prominence = self.prominence
            if prominence is None:
                # Use a fraction of price range as prominence
                price_range = zone_data['high'].max() - zone_data['low'].min()
                prominence = price_range * 0.01  # 1% of range
            
            # Find peaks (local maxima)
            peaks_idx, _ = find_peaks(
                zone_data['high'].values,
                prominence=prominence,
                distance=self.distance
            )
            
            # Find troughs (local minima)
            troughs_idx, _ = find_peaks(
                -zone_data['low'].values,
                prominence=prominence,
                distance=self.distance
            )
            
            # Combine peaks and troughs
            all_extrema = []
            for idx in peaks_idx:
                all_extrema.append({
                    'index': idx,
                    'type': 'peak',
                    'price': float(zone_data['high'].iloc[idx]),
                    'timestamp': zone_data.index[idx]
                })
            
            for idx in troughs_idx:
                all_extrema.append({
                    'index': idx,
                    'type': 'trough',
                    'price': float(zone_data['low'].iloc[idx]),
                    'timestamp': zone_data.index[idx]
                })
            
            # Sort by index (time)
            all_extrema.sort(key=lambda x: x['index'])
            
            if len(all_extrema) < 2:
                logger.debug(
                    f"Not enough extrema detected: {len(all_extrema)} points "
                    f"(prominence={prominence}, distance={self.distance})"
                )
                return self._empty_metrics()
            
            # Filter by amplitude and calculate metrics
            return self._calculate_swing_metrics(all_extrema)
            
        except Exception as e:
            logger.error(f"FindPeaks swing calculation failed: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _calculate_swing_metrics(self, extrema: list) -> SwingMetrics:
        """
        Calculate comprehensive metrics from extrema points.
        
        Args:
            extrema: List of dicts with 'index', 'type', 'price', 'timestamp'
        
        Returns:
            SwingMetrics with all fields populated
        """
        rallies = []  # UP movements
        drops = []    # DOWN movements
        
        # Calculate movements between extrema
        for i in range(1, len(extrema)):
            prev = extrema[i-1]
            curr = extrema[i]
            
            prev_price = prev['price']
            curr_price = curr['price']
            duration_bars = curr['index'] - prev['index']
            
            # Calculate price change percentage
            price_change_pct = (curr_price / prev_price - 1) * 100
            
            # Filter by minimum amplitude
            if abs(price_change_pct) < self.min_amplitude_pct * 100:
                continue  # Skip insignificant movements
            
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
        num_swings = min(rally_count, drop_count)
        
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
            strategy_name='find_peaks',
            strategy_params={
                'prominence': self.prominence,
                'distance': self.distance,
                'min_amplitude_pct': self.min_amplitude_pct
            }
        )
        
        # Validate before returning
        metrics.validate()
        
        logger.debug(
            f"FindPeaks metrics calculated: {rally_count} rallies, {drop_count} drops, "
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
            strategy_name='find_peaks',
            strategy_params={
                'prominence': self.prominence,
                'distance': self.distance,
                'min_amplitude_pct': self.min_amplitude_pct
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'FindPeaks',
            'description': 'Swing detection via scipy.signal.find_peaks with amplitude filtering',
            'params': {
                'prominence': self.prominence,
                'distance': self.distance,
                'min_amplitude_pct': self.min_amplitude_pct
            },
            'source': 'scipy.signal library',
            'calculates': [
                'local extrema (peaks and troughs)',
                'filtered by minimum amplitude',
                'comprehensive swing metrics (23 fields)'
            ],
            'advantages': [
                'Flexible parameter control',
                'Fast vectorized algorithm',
                'Can detect more swings than ZigZag'
            ]
        }

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration parameters for cache key generation."""
        return {
            'prominence': self.prominence,
            'distance': self.distance,
            'min_amplitude_pct': self.min_amplitude_pct
        }

