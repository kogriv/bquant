"""
Pivot Points Swing Strategy - swing detection using N-bar pivot patterns.

This strategy identifies swing points using classic technical analysis pivot
patterns, where a pivot high is a bar whose high is greater than N bars before
and after it, and a pivot low is a bar whose low is less than N bars before
and after it.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from ..base import SwingMetrics, SwingCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_swing_strategy('pivot_points')
@dataclass
class PivotPointsSwingStrategy:
    """
    Swing detection using classic Pivot Points (N-bar pattern).
    
    Identifies pivot highs and lows using the traditional technical analysis
    pattern: a pivot high is confirmed when the high at position i is greater
    than the highs of N bars before and after it. Similarly for pivot lows.
    
    Attributes:
        left_bars: Number of bars to check on the left (default: 2)
        right_bars: Number of bars to check on the right (default: 2)
        min_amplitude_pct: Minimum movement percentage to qualify as swing (default: 0.015 = 1.5%)
    """
    left_bars: int = 2
    right_bars: int = 2
    min_amplitude_pct: float = 0.015  # 1.5% minimum movement
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate comprehensive swing metrics using Pivot Points pattern.
        
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
        
        # Need minimum bars for pattern
        min_bars = self.left_bars + self.right_bars + 1
        if len(zone_data) < min_bars:
            logger.debug(
                f"Not enough bars for pivot pattern: {len(zone_data)} < {min_bars} "
                f"(left={self.left_bars}, right={self.right_bars})"
            )
            return self._empty_metrics()
        
        try:
            # Find pivot highs and lows
            pivot_highs = self._find_pivot_highs(zone_data)
            pivot_lows = self._find_pivot_lows(zone_data)
            
            # Combine into extrema list
            all_extrema = []
            
            for idx in pivot_highs:
                all_extrema.append({
                    'index': idx,
                    'type': 'peak',
                    'price': float(zone_data['high'].iloc[idx]),
                    'timestamp': zone_data.index[idx]
                })
            
            for idx in pivot_lows:
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
                    f"Not enough pivot points detected: {len(all_extrema)} "
                    f"(highs={len(pivot_highs)}, lows={len(pivot_lows)})"
                )
                return self._empty_metrics()
            
            # Calculate metrics from extrema
            return self._calculate_swing_metrics(all_extrema)
            
        except Exception as e:
            logger.error(f"PivotPoints swing calculation failed: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _find_pivot_highs(self, data: pd.DataFrame) -> List[int]:
        """
        Find pivot high points.
        
        A pivot high at position i is confirmed when:
        high[i] > high[i-j] for all j in [1..left_bars] AND
        high[i] > high[i+j] for all j in [1..right_bars]
        
        Returns:
            List of indices where pivot highs occur
        """
        highs = data['high'].values
        pivot_indices = []
        
        for i in range(self.left_bars, len(highs) - self.right_bars):
            # Check left side
            is_pivot = all(
                highs[i] > highs[i-j] for j in range(1, self.left_bars + 1)
            )
            
            # Check right side
            if is_pivot:
                is_pivot = all(
                    highs[i] > highs[i+j] for j in range(1, self.right_bars + 1)
                )
            
            if is_pivot:
                pivot_indices.append(i)
        
        return pivot_indices
    
    def _find_pivot_lows(self, data: pd.DataFrame) -> List[int]:
        """
        Find pivot low points.
        
        A pivot low at position i is confirmed when:
        low[i] < low[i-j] for all j in [1..left_bars] AND
        low[i] < low[i+j] for all j in [1..right_bars]
        
        Returns:
            List of indices where pivot lows occur
        """
        lows = data['low'].values
        pivot_indices = []
        
        for i in range(self.left_bars, len(lows) - self.right_bars):
            # Check left side
            is_pivot = all(
                lows[i] < lows[i-j] for j in range(1, self.left_bars + 1)
            )
            
            # Check right side
            if is_pivot:
                is_pivot = all(
                    lows[i] < lows[i+j] for j in range(1, self.right_bars + 1)
                )
            
            if is_pivot:
                pivot_indices.append(i)
        
        return pivot_indices
    
    def _calculate_swing_metrics(self, extrema: list) -> SwingMetrics:
        """
        Calculate comprehensive metrics from pivot points.
        
        Args:
            extrema: List of dicts with 'index', 'type', 'price', 'timestamp'
        
        Returns:
            SwingMetrics with all fields populated
        """
        rallies = []
        drops = []
        
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
                continue
            
            if price_change_pct > 0:
                rallies.append({
                    'amplitude_pct': price_change_pct,
                    'duration_bars': duration_bars,
                    'speed_pct_per_bar': price_change_pct / duration_bars if duration_bars > 0 else 0
                })
            else:
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
        
        # Ratio and symmetry
        rally_to_drop_ratio = avg_rally_pct / avg_drop_pct if avg_drop_pct > 0 else 0.0
        duration_symmetry = (avg_rally_duration_bars / avg_drop_duration_bars 
                           if avg_drop_duration_bars > 0 else 0.0)
        
        # Total swings
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
            strategy_name='pivot_points',
            strategy_params={
                'left_bars': self.left_bars,
                'right_bars': self.right_bars,
                'min_amplitude_pct': self.min_amplitude_pct
            }
        )
        
        # Validate
        metrics.validate()
        
        logger.debug(
            f"PivotPoints metrics calculated: {rally_count} rallies, {drop_count} drops, "
            f"ratio={rally_to_drop_ratio:.2f}"
        )
        
        return metrics
    
    def _empty_metrics(self) -> SwingMetrics:
        """Return empty metrics when no swings detected."""
        return SwingMetrics(
            num_swings=0, avg_rally_pct=0.0, avg_drop_pct=0.0,
            max_rally_pct=0.0, max_drop_pct=0.0, rally_to_drop_ratio=0.0,
            rally_count=0, drop_count=0,
            min_rally_pct=0.0, min_drop_pct=0.0,
            rally_amplitude_std=0.0, drop_amplitude_std=0.0,
            rally_amplitude_median=0.0, drop_amplitude_median=0.0,
            avg_rally_duration_bars=0.0, avg_drop_duration_bars=0.0,
            max_rally_duration_bars=0, max_drop_duration_bars=0,
            avg_rally_speed_pct_per_bar=0.0, avg_drop_speed_pct_per_bar=0.0,
            max_rally_speed_pct_per_bar=0.0, max_drop_speed_pct_per_bar=0.0,
            duration_symmetry=0.0,
            strategy_name='pivot_points',
            strategy_params={
                'left_bars': self.left_bars,
                'right_bars': self.right_bars,
                'min_amplitude_pct': self.min_amplitude_pct
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get strategy metadata for logging and traceability."""
        return {
            'name': 'PivotPoints',
            'description': 'Classic N-bar pivot pattern swing detection',
            'params': {
                'left_bars': self.left_bars,
                'right_bars': self.right_bars,
                'min_amplitude_pct': self.min_amplitude_pct
            },
            'source': 'Classic technical analysis pattern',
            'pattern': (
                f'Pivot High: high[i] > high[i±j] for j in [1..{self.left_bars}] (left) '
                f'and [1..{self.right_bars}] (right). Similarly for Pivot Low.'
            ),
            'calculates': [
                'pivot highs and lows',
                'filtered by minimum amplitude',
                'comprehensive swing metrics (23 fields)'
            ],
            'advantages': [
                'Classic trader-friendly pattern',
                'Natural noise filtering via confirmation',
                'Adjustable sensitivity (left/right bars)'
            ]
        }

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration parameters for cache key generation."""
        return {
            'left_bars': self.left_bars,
            'right_bars': self.right_bars,
            'min_amplitude_pct': self.min_amplitude_pct
        }

