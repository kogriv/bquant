"""
Classic Divergence Detection Strategy - universal divergence detection for ANY oscillator.

Detects regular and hidden divergences between price and oscillator using 
traditional peak/trough comparison methodology.

UNIVERSAL (v2.1):
- Works with ANY oscillator: MACD, RSI, AO, CCI, Stochastic, custom, etc.
- Supports both single-line and two-line indicators
- Requires explicit indicator_col parameter

Examples:
    strategy.calculate_divergence(data, indicator_col='RSI_14')  # RSI
    strategy.calculate_divergence(data, indicator_col='macd_hist')  # MACD
    strategy.calculate_divergence(data, indicator_col='macd', indicator_line_col='macd_signal')  # 2-line
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
    Classic divergence detection using price and oscillator extrema comparison.
    
    UNIVERSAL STRATEGY (v2.1):
    - Works with ANY oscillator (MACD, RSI, AO, Stochastic, CCI, etc.)
    - Detects divergence between price and oscillator
    - Supports both single-line and two-line indicators
    - Requires explicit indicator_col parameter (no auto-detection)
    
    Detects:
    - Regular bullish divergence: Price makes lower low, Indicator makes higher low
    - Regular bearish divergence: Price makes higher high, Indicator makes lower high
    - Hidden bullish divergence: Price makes higher low, Indicator makes lower low
    - Hidden bearish divergence: Price makes lower high, Indicator makes higher high
    
    Attributes:
        min_peak_distance: Minimum distance between peaks/troughs (bars)
        min_divergence_strength: Minimum strength threshold for valid divergence
    """
    
    min_peak_distance: int = 5
    min_divergence_strength: float = 0.01
    
    def calculate_divergence(self, 
                            zone_data: pd.DataFrame,
                            indicator_col: str,
                            indicator_line_col: str = None) -> DivergenceMetrics:
        """
        Calculate divergence metrics for a zone.
        
        UNIVERSAL METHOD (v2.1):
        Works with ANY oscillator, not just MACD.
        
        Args:
            zone_data: DataFrame with columns: close, high, low, and oscillator column(s)
            indicator_col: Name of oscillator column (e.g., 'macd_hist', 'RSI_14', 'AO_5_34')
            indicator_line_col: Optional signal line column (e.g., 'macd' for 2-line divergence,
                               'STOCHd_14_3_3' for Stochastic)
        
        Returns:
            DivergenceMetrics with validated data
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        
        Examples:
            # MACD histogram (single line)
            metrics = strategy.calculate_divergence(zone_data, indicator_col='macd_hist')
            
            # MACD with signal line (two lines)
            metrics = strategy.calculate_divergence(
                zone_data, 
                indicator_col='macd_hist',
                indicator_line_col='macd'
            )
            
            # RSI (single line)
            metrics = strategy.calculate_divergence(zone_data, indicator_col='RSI_14')
            
            # Awesome Oscillator
            metrics = strategy.calculate_divergence(zone_data, indicator_col='AO_5_34')
            
            # Stochastic (two lines)
            metrics = strategy.calculate_divergence(
                zone_data,
                indicator_col='STOCHk_14_3_3',
                indicator_line_col='STOCHd_14_3_3'
            )
        """
        # Validate input
        if zone_data.empty:
            raise ValueError("Zone data cannot be empty")
        
        # Build required_cols dynamically based on parameters
        required_cols = ['close', 'high', 'low', indicator_col]
        if indicator_line_col:
            required_cols.append(indicator_line_col)
        
        missing_cols = [col for col in required_cols if col not in zone_data.columns]
        if missing_cols:
            raise ValueError(
                f"Zone data must contain columns: {missing_cols}. "
                f"Available: {list(zone_data.columns)}"
            )
        
        if len(zone_data) < self.min_peak_distance * 2:
            logger.debug(f"Insufficient data for divergence detection: {len(zone_data)} bars")
            return self._empty_metrics(indicator_col, indicator_line_col)
        
        try:
            # Find extrema
            price_peaks, price_troughs = self._find_price_extrema(zone_data)
            indicator_peaks, indicator_troughs = self._find_indicator_extrema(
                zone_data, indicator_col, indicator_line_col
            )
            
            # Detect divergences
            divergences = self._detect_divergences(
                zone_data, price_peaks, price_troughs, 
                indicator_peaks, indicator_troughs,
                indicator_col, indicator_line_col
            )
            
            # Calculate metrics
            if not divergences:
                return self._empty_metrics(indicator_col, indicator_line_col)
            
            return self._calculate_metrics(divergences, indicator_col, indicator_line_col)
            
        except Exception as e:
            logger.error(f"Divergence calculation failed for '{indicator_col}': {e}", exc_info=True)
            return self._empty_metrics(indicator_col, indicator_line_col)
    
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
    
    def _find_indicator_extrema(self, 
                                zone_data: pd.DataFrame,
                                indicator_col: str,
                                indicator_line_col: str = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find indicator peaks and troughs (UNIVERSAL - works with any oscillator).
        
        Args:
            zone_data: DataFrame
            indicator_col: Primary oscillator column
            indicator_line_col: Optional signal line (if provided, uses it instead of primary)
        
        Returns:
            Tuple of (peak_indices, trough_indices)
        """
        # Use signal line if provided, otherwise primary indicator
        if indicator_line_col and indicator_line_col in zone_data.columns:
            indicator_values = zone_data[indicator_line_col].values
        else:
            indicator_values = zone_data[indicator_col].values
        
        # Find peaks
        peaks, _ = find_peaks(
            indicator_values,
            distance=self.min_peak_distance,
            prominence=np.std(indicator_values) * 0.3
        )
        
        # Find troughs
        troughs, _ = find_peaks(
            -indicator_values,
            distance=self.min_peak_distance,
            prominence=np.std(indicator_values) * 0.3
        )
        
        return peaks, troughs
    
    def _detect_divergences(
        self,
        zone_data: pd.DataFrame,
        price_peaks: np.ndarray,
        price_troughs: np.ndarray,
        indicator_peaks: np.ndarray,
        indicator_troughs: np.ndarray,
        indicator_col: str,
        indicator_line_col: str = None
    ) -> List[Dict[str, Any]]:
        """
        Detect all types of divergences (UNIVERSAL - works with any oscillator).
        
        Args:
            indicator_col: Primary oscillator column to use
            indicator_line_col: Optional signal line column
        
        Returns:
            List of divergence dictionaries with type, strength, and direction
        """
        divergences = []
        
        # Regular bearish divergence (price higher high, indicator lower high)
        if len(price_peaks) >= 2 and len(indicator_peaks) >= 2:
            divs = self._find_regular_bearish(
                zone_data, price_peaks, indicator_peaks, 
                indicator_col, indicator_line_col
            )
            divergences.extend(divs)
        
        # Regular bullish divergence (price lower low, indicator higher low)
        if len(price_troughs) >= 2 and len(indicator_troughs) >= 2:
            divs = self._find_regular_bullish(
                zone_data, price_troughs, indicator_troughs,
                indicator_col, indicator_line_col
            )
            divergences.extend(divs)
        
        # Hidden divergences (optional, less common)
        # Could be added in future versions
        
        return divergences
    
    def _find_regular_bearish(
        self,
        zone_data: pd.DataFrame,
        price_peaks: np.ndarray,
        indicator_peaks: np.ndarray,
        indicator_col: str,
        indicator_line_col: str = None
    ) -> List[Dict[str, Any]]:
        """Find regular bearish divergences (UNIVERSAL - works with any oscillator)."""
        divergences = []
        
        price_highs = zone_data['high'].values
        
        # Use signal line if provided, otherwise primary indicator
        if indicator_line_col and indicator_line_col in zone_data.columns:
            indicator_values = zone_data[indicator_line_col].values
        else:
            indicator_values = zone_data[indicator_col].values
        
        # Compare consecutive peaks
        for i in range(len(price_peaks) - 1):
            p1_idx, p2_idx = price_peaks[i], price_peaks[i + 1]
            
            # Find corresponding indicator peaks nearby
            ind_p1 = self._find_nearest_peak(p1_idx, indicator_peaks)
            ind_p2 = self._find_nearest_peak(p2_idx, indicator_peaks)
            
            if ind_p1 is None or ind_p2 is None:
                continue
            
            # Check for divergence: price HH, indicator LH
            price_slope = price_highs[p2_idx] - price_highs[p1_idx]
            indicator_slope = indicator_values[ind_p2] - indicator_values[ind_p1]
            
            if price_slope > 0 and indicator_slope < 0:
                # Regular bearish divergence detected
                strength = abs(price_slope / price_highs[p1_idx]) * abs(indicator_slope / indicator_values[ind_p1])
                
                if strength >= self.min_divergence_strength:
                    divergences.append({
                        'type': 'regular',
                        'direction': 'bearish',
                        'strength': strength,
                        'price_indices': (p1_idx, p2_idx),
                        'indicator_indices': (ind_p1, ind_p2)
                    })
        
        return divergences
    
    def _find_regular_bullish(
        self,
        zone_data: pd.DataFrame,
        price_troughs: np.ndarray,
        indicator_troughs: np.ndarray,
        indicator_col: str,
        indicator_line_col: str = None
    ) -> List[Dict[str, Any]]:
        """Find regular bullish divergences (UNIVERSAL - works with any oscillator)."""
        divergences = []
        
        price_lows = zone_data['low'].values
        
        # Use signal line if provided, otherwise primary indicator
        if indicator_line_col and indicator_line_col in zone_data.columns:
            indicator_values = zone_data[indicator_line_col].values
        else:
            indicator_values = zone_data[indicator_col].values
        
        # Compare consecutive troughs
        for i in range(len(price_troughs) - 1):
            t1_idx, t2_idx = price_troughs[i], price_troughs[i + 1]
            
            # Find corresponding indicator troughs nearby
            ind_t1 = self._find_nearest_peak(t1_idx, indicator_troughs)
            ind_t2 = self._find_nearest_peak(t2_idx, indicator_troughs)
            
            if ind_t1 is None or ind_t2 is None:
                continue
            
            # Check for divergence: price LL, indicator HL
            price_slope = price_lows[t2_idx] - price_lows[t1_idx]
            indicator_slope = indicator_values[ind_t2] - indicator_values[ind_t1]
            
            if price_slope < 0 and indicator_slope > 0:
                # Regular bullish divergence detected
                strength = abs(price_slope / price_lows[t1_idx]) * abs(indicator_slope / indicator_values[ind_t1])
                
                if strength >= self.min_divergence_strength:
                    divergences.append({
                        'type': 'regular',
                        'direction': 'bullish',
                        'strength': strength,
                        'price_indices': (t1_idx, t2_idx),
                        'indicator_indices': (ind_t1, ind_t2)
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
    
    def _calculate_metrics(self, 
                          divergences: List[Dict[str, Any]],
                          indicator_col: str,
                          indicator_line_col: str = None) -> DivergenceMetrics:
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
                'indicator_col': indicator_col,  # Track which indicator was used (v2.1)
                'indicator_line_col': indicator_line_col
            }
        )
        
        result.validate()
        return result
    
    def _empty_metrics(self, 
                      indicator_col: str = None,
                      indicator_line_col: str = None) -> DivergenceMetrics:
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
                'indicator_col': indicator_col,
                'indicator_line_col': indicator_line_col
            }
        )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        return {
            'name': 'Classic',
            'description': 'Traditional divergence detection using price vs oscillator extrema comparison (UNIVERSAL - works with any oscillator)',
            'params': {
                'min_peak_distance': self.min_peak_distance,
                'min_divergence_strength': self.min_divergence_strength
            },
            'supported_indicators': 'ANY oscillator (MACD, RSI, AO, Stochastic, CCI, custom, etc.)',
            'supports_two_line': True,
            'source': 'Classic technical analysis methodology'
        }

