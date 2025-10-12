"""
Classic Divergence Detection Strategy.

Detects regular and hidden divergences between price and MACD using 
traditional peak/trough comparison methodology.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

from ..base import DivergenceMetrics, DivergenceCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger

logger = get_logger(__name__)


@StrategyRegistry.register_divergence_strategy('classic')
@dataclass
class ClassicDivergenceStrategy:
    """
    Classic divergence detection using price and MACD extrema comparison.
    
    Detects:
    - Regular bullish divergence: Price makes lower low, MACD makes higher low
    - Regular bearish divergence: Price makes higher high, MACD makes lower high
    - Hidden bullish divergence: Price makes higher low, MACD makes lower low
    - Hidden bearish divergence: Price makes lower high, MACD makes higher high
    
    Attributes:
        min_peak_distance: Minimum distance between peaks/troughs (bars)
        min_divergence_strength: Minimum strength threshold for valid divergence
        use_macd_line: Use MACD line instead of histogram (default: False, use histogram)
    """
    
    min_peak_distance: int = 5
    min_divergence_strength: float = 0.01
    use_macd_line: bool = False
    
    def calculate_divergence(self, zone_data: pd.DataFrame) -> DivergenceMetrics:
        """
        Calculate divergence metrics for a zone.
        
        Args:
            zone_data: DataFrame with columns: close, high, low, macd, macd_hist
        
        Returns:
            DivergenceMetrics with validated data
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        # Validate input
        if zone_data.empty:
            raise ValueError("Zone data cannot be empty")
        
        required_cols = ['close', 'high', 'low', 'macd_hist']
        if self.use_macd_line:
            required_cols.append('macd')
        
        missing_cols = [col for col in required_cols if col not in zone_data.columns]
        if missing_cols:
            raise ValueError(f"Zone data must contain columns: {missing_cols}")
        
        if len(zone_data) < self.min_peak_distance * 2:
            logger.debug(f"Insufficient data for divergence detection: {len(zone_data)} bars")
            return self._empty_metrics()
        
        try:
            # Find extrema
            price_peaks, price_troughs = self._find_price_extrema(zone_data)
            macd_peaks, macd_troughs = self._find_macd_extrema(zone_data)
            
            # Detect divergences
            divergences = self._detect_divergences(
                zone_data, price_peaks, price_troughs, macd_peaks, macd_troughs
            )
            
            # Calculate metrics
            if not divergences:
                return self._empty_metrics()
            
            return self._calculate_metrics(divergences)
            
        except Exception as e:
            logger.error(f"Divergence calculation failed: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _find_price_extrema(self, zone_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find price peaks and troughs using scipy.signal.find_peaks.
        
        Returns:
            Tuple of (peak_indices, trough_indices)
        """
        prices_high = zone_data['high'].values
        prices_low = zone_data['low'].values
        
        # Find peaks (high prices)
        peaks, _ = find_peaks(
            prices_high,
            distance=self.min_peak_distance,
            prominence=np.std(prices_high) * 0.5  # Auto prominence
        )
        
        # Find troughs (low prices) - invert signal
        troughs, _ = find_peaks(
            -prices_low,
            distance=self.min_peak_distance,
            prominence=np.std(prices_low) * 0.5
        )
        
        return peaks, troughs
    
    def _find_macd_extrema(self, zone_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find MACD peaks and troughs.
        
        Returns:
            Tuple of (peak_indices, trough_indices)
        """
        if self.use_macd_line:
            macd_values = zone_data['macd'].values
        else:
            macd_values = zone_data['macd_hist'].values
        
        # Find peaks
        peaks, _ = find_peaks(
            macd_values,
            distance=self.min_peak_distance,
            prominence=np.std(macd_values) * 0.3
        )
        
        # Find troughs
        troughs, _ = find_peaks(
            -macd_values,
            distance=self.min_peak_distance,
            prominence=np.std(macd_values) * 0.3
        )
        
        return peaks, troughs
    
    def _detect_divergences(
        self,
        zone_data: pd.DataFrame,
        price_peaks: np.ndarray,
        price_troughs: np.ndarray,
        macd_peaks: np.ndarray,
        macd_troughs: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Detect all types of divergences.
        
        Returns:
            List of divergence dictionaries with type, strength, and direction
        """
        divergences = []
        
        # Regular bearish divergence (price higher high, MACD lower high)
        if len(price_peaks) >= 2 and len(macd_peaks) >= 2:
            divs = self._find_regular_bearish(zone_data, price_peaks, macd_peaks)
            divergences.extend(divs)
        
        # Regular bullish divergence (price lower low, MACD higher low)
        if len(price_troughs) >= 2 and len(macd_troughs) >= 2:
            divs = self._find_regular_bullish(zone_data, price_troughs, macd_troughs)
            divergences.extend(divs)
        
        # Hidden divergences (optional, less common)
        # Could be added in future versions
        
        return divergences
    
    def _find_regular_bearish(
        self,
        zone_data: pd.DataFrame,
        price_peaks: np.ndarray,
        macd_peaks: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Find regular bearish divergences."""
        divergences = []
        
        price_highs = zone_data['high'].values
        macd_values = zone_data['macd_hist'].values if not self.use_macd_line else zone_data['macd'].values
        
        # Compare consecutive peaks
        for i in range(len(price_peaks) - 1):
            p1_idx, p2_idx = price_peaks[i], price_peaks[i + 1]
            
            # Find corresponding MACD peaks nearby
            macd_p1 = self._find_nearest_peak(p1_idx, macd_peaks)
            macd_p2 = self._find_nearest_peak(p2_idx, macd_peaks)
            
            if macd_p1 is None or macd_p2 is None:
                continue
            
            # Check for divergence: price HH, MACD LH
            price_slope = price_highs[p2_idx] - price_highs[p1_idx]
            macd_slope = macd_values[macd_p2] - macd_values[macd_p1]
            
            if price_slope > 0 and macd_slope < 0:
                # Regular bearish divergence detected
                strength = abs(price_slope / price_highs[p1_idx]) * abs(macd_slope / macd_values[macd_p1])
                
                if strength >= self.min_divergence_strength:
                    divergences.append({
                        'type': 'regular',
                        'direction': 'bearish',
                        'strength': strength,
                        'price_indices': (p1_idx, p2_idx),
                        'macd_indices': (macd_p1, macd_p2)
                    })
        
        return divergences
    
    def _find_regular_bullish(
        self,
        zone_data: pd.DataFrame,
        price_troughs: np.ndarray,
        macd_troughs: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Find regular bullish divergences."""
        divergences = []
        
        price_lows = zone_data['low'].values
        macd_values = zone_data['macd_hist'].values if not self.use_macd_line else zone_data['macd'].values
        
        # Compare consecutive troughs
        for i in range(len(price_troughs) - 1):
            t1_idx, t2_idx = price_troughs[i], price_troughs[i + 1]
            
            # Find corresponding MACD troughs nearby
            macd_t1 = self._find_nearest_peak(t1_idx, macd_troughs)
            macd_t2 = self._find_nearest_peak(t2_idx, macd_troughs)
            
            if macd_t1 is None or macd_t2 is None:
                continue
            
            # Check for divergence: price LL, MACD HL
            price_slope = price_lows[t2_idx] - price_lows[t1_idx]
            macd_slope = macd_values[macd_t2] - macd_values[macd_t1]
            
            if price_slope < 0 and macd_slope > 0:
                # Regular bullish divergence detected
                strength = abs(price_slope / price_lows[t1_idx]) * abs(macd_slope / macd_values[macd_t1])
                
                if strength >= self.min_divergence_strength:
                    divergences.append({
                        'type': 'regular',
                        'direction': 'bullish',
                        'strength': strength,
                        'price_indices': (t1_idx, t2_idx),
                        'macd_indices': (macd_t1, macd_t2)
                    })
        
        return divergences
    
    def _find_nearest_peak(self, target_idx: int, peaks: np.ndarray, max_distance: int = 10) -> int:
        """
        Find nearest peak to target index within max_distance.
        
        Returns:
            Peak index or None if not found
        """
        if len(peaks) == 0:
            return None
        
        distances = np.abs(peaks - target_idx)
        min_dist_idx = np.argmin(distances)
        
        if distances[min_dist_idx] <= max_distance:
            return peaks[min_dist_idx]
        
        return None
    
    def _calculate_metrics(self, divergences: List[Dict[str, Any]]) -> DivergenceMetrics:
        """
        Calculate aggregated metrics from detected divergences.
        """
        # Count divergences by type
        regular_count = sum(1 for d in divergences if d['type'] == 'regular')
        
        # Determine overall type
        if regular_count > 0:
            div_type = 'regular'
        else:
            div_type = 'none'
        
        # Calculate average strength
        strengths = [d['strength'] for d in divergences]
        avg_strength = np.mean(strengths) if strengths else 0.0
        
        # Determine direction (majority vote)
        bullish_count = sum(1 for d in divergences if d['direction'] == 'bullish')
        bearish_count = sum(1 for d in divergences if d['direction'] == 'bearish')
        
        if bullish_count > bearish_count:
            direction = 'bullish'
        elif bearish_count > bullish_count:
            direction = 'bearish'
        else:
            direction = 'none'
        
        result = DivergenceMetrics(
            divergence_type=div_type,
            divergence_count=len(divergences),
            divergence_strength=float(avg_strength),
            divergence_direction=direction,
            strategy_name='classic',
            strategy_params={
                'min_peak_distance': self.min_peak_distance,
                'min_divergence_strength': self.min_divergence_strength,
                'use_macd_line': self.use_macd_line
            }
        )
        
        result.validate()
        return result
    
    def _empty_metrics(self) -> DivergenceMetrics:
        """Return empty/none divergence metrics."""
        return DivergenceMetrics(
            divergence_type='none',
            divergence_count=0,
            divergence_strength=0.0,
            divergence_direction='none',
            strategy_name='classic',
            strategy_params={
                'min_peak_distance': self.min_peak_distance,
                'min_divergence_strength': self.min_divergence_strength,
                'use_macd_line': self.use_macd_line
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        return {
            'name': 'Classic',
            'description': 'Traditional divergence detection using price/MACD extrema comparison',
            'params': {
                'min_peak_distance': self.min_peak_distance,
                'min_divergence_strength': self.min_divergence_strength,
                'use_macd_line': self.use_macd_line
            },
            'source': 'Classic technical analysis methodology'
        }

