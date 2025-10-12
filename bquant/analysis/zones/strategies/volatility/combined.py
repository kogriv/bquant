"""
Combined Volatility Strategy using Bollinger Bands and ATR.

This strategy combines two classic volatility indicators to provide
a comprehensive assessment of zone volatility and market conditions.
"""

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd
import numpy as np

from ..base import VolatilityMetrics, VolatilityCalculationStrategy
from ..registry import StrategyRegistry
from .....core.logging_config import get_logger
from .....indicators import LibraryManager

logger = get_logger(__name__)


@StrategyRegistry.register_volatility_strategy('combined')
@dataclass
class CombinedVolatilityStrategy:
    """
    Combined volatility assessment using Bollinger Bands and ATR.
    
    Combines:
    - Bollinger Bands: Width, squeeze ratio, band touches
    - ATR: Normalized range, trend direction, average value
    - Composite score: Overall volatility assessment (0-10)
    
    Attributes:
        bb_length: Bollinger Bands period (default: 20)
        bb_std: Number of standard deviations (default: 2.0)
        touch_threshold: Threshold for band touch detection (default: 0.01, i.e. 1%)
    """
    
    bb_length: int = 20
    bb_std: float = 2.0
    touch_threshold: float = 0.01
    
    def calculate_volatility(self, zone_data: pd.DataFrame) -> VolatilityMetrics:
        """
        Calculate volatility metrics using Bollinger Bands and ATR.
        
        Args:
            zone_data: DataFrame with columns: high, low, close, atr
        
        Returns:
            VolatilityMetrics with validated data
        
        Raises:
            ValueError: If required columns are missing or data is insufficient
        """
        # Validate input
        if zone_data.empty:
            raise ValueError("Zone data cannot be empty")
        
        required_cols = ['high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in zone_data.columns]
        if missing_cols:
            raise ValueError(f"Zone data must contain columns: {missing_cols}")
        
        if len(zone_data) < 3:
            raise ValueError(f"Zone data must have at least 3 bars, got {len(zone_data)}")
        
        # Check if ATR is available
        has_atr = 'atr' in zone_data.columns
        
        try:
            # Calculate Bollinger Bands metrics
            bb_metrics = self._calculate_bollinger_metrics(zone_data)
            
            # Calculate ATR metrics (or defaults if ATR not available)
            if has_atr:
                atr_metrics = self._calculate_atr_metrics(zone_data)
            else:
                logger.warning("ATR column not found, using estimated ATR from price range")
                atr_metrics = self._estimate_atr_metrics(zone_data)
            
            # Calculate composite score and regime
            volatility_score = self._calculate_volatility_score(bb_metrics, atr_metrics)
            volatility_regime = self._classify_volatility_regime(volatility_score)
            
            result = VolatilityMetrics(
                bollinger_width_pct=bb_metrics['width_pct'],
                bollinger_width_std=bb_metrics['width_std'],
                bollinger_squeeze_ratio=bb_metrics['squeeze_ratio'],
                bollinger_upper_touches=bb_metrics['upper_touches'],
                bollinger_lower_touches=bb_metrics['lower_touches'],
                atr_normalized_range=atr_metrics['normalized_range'],
                atr_trend=atr_metrics['trend'],
                avg_atr=atr_metrics['avg_atr'],
                volatility_score=volatility_score,
                volatility_regime=volatility_regime,
                strategy_name='combined',
                strategy_params={
                    'bb_length': self.bb_length,
                    'bb_std': self.bb_std,
                    'touch_threshold': self.touch_threshold
                }
            )
            
            result.validate()
            return result
            
        except Exception as e:
            logger.error(f"Volatility calculation failed: {e}", exc_info=True)
            raise
    
    def _calculate_bollinger_metrics(self, zone_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate Bollinger Bands metrics."""
        try:
            # Create Bollinger Bands indicator via LibraryManager
            bbands_indicator = LibraryManager.create_indicator(
                'pandas_ta',
                'bbands',
                length=self.bb_length,
                std=self.bb_std
            )
            
            # Calculate Bollinger Bands
            bb_result = bbands_indicator.calculate(zone_data)
            bb_df = bb_result.data
            
            # Extract bands (pandas-ta returns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0)
            # Find column names
            bb_cols = [col for col in bb_df.columns if 'BB' in col]
            
            # Identify specific columns
            lower_col = [col for col in bb_cols if 'BBL' in col][0]
            middle_col = [col for col in bb_cols if 'BBM' in col][0]
            upper_col = [col for col in bb_cols if 'BBU' in col][0]
            
            bb_lower = bb_df[lower_col]
            bb_middle = bb_df[middle_col]
            bb_upper = bb_df[upper_col]
            
            # Calculate width as percentage of middle band
            bb_width = (bb_upper - bb_lower) / bb_middle * 100
            bb_width = bb_width.replace([np.inf, -np.inf], np.nan).dropna()
            
            # Metrics
            width_pct = float(bb_width.mean()) if len(bb_width) > 0 else 0.0
            width_std = float(bb_width.std()) if len(bb_width) > 0 else 0.0
            
            # Squeeze ratio (current vs average)
            current_width = float(bb_width.iloc[-1]) if len(bb_width) > 0 else width_pct
            squeeze_ratio = (current_width / width_pct) if width_pct > 0 else 1.0
            
            # Band touches (price within threshold of band)
            close = zone_data['close']
            upper_threshold = bb_upper * (1 - self.touch_threshold)
            lower_threshold = bb_lower * (1 + self.touch_threshold)
            
            upper_touches = int((close >= upper_threshold).sum())
            lower_touches = int((close <= lower_threshold).sum())
            
            return {
                'width_pct': width_pct,
                'width_std': width_std,
                'squeeze_ratio': squeeze_ratio,
                'upper_touches': upper_touches,
                'lower_touches': lower_touches
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate Bollinger metrics: {e}")
            # Return defaults
            return {
                'width_pct': 0.0,
                'width_std': 0.0,
                'squeeze_ratio': 1.0,
                'upper_touches': 0,
                'lower_touches': 0
            }
    
    def _calculate_atr_metrics(self, zone_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate ATR-based metrics."""
        atr = zone_data['atr']
        
        # Average ATR
        avg_atr = float(atr.mean())
        
        # Price range normalized by ATR
        price_range = float(zone_data['high'].max() - zone_data['low'].min())
        normalized_range = (price_range / avg_atr) if avg_atr > 0 else 0.0
        
        # ATR trend
        atr_start = float(atr.iloc[0])
        atr_end = float(atr.iloc[-1])
        atr_change = ((atr_end / atr_start) - 1) if atr_start > 0 else 0.0
        
        if atr_change > 0.2:
            atr_trend = 'increasing'
        elif atr_change < -0.2:
            atr_trend = 'decreasing'
        else:
            atr_trend = 'stable'
        
        return {
            'avg_atr': avg_atr,
            'normalized_range': normalized_range,
            'trend': atr_trend
        }
    
    def _estimate_atr_metrics(self, zone_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Estimate ATR metrics when ATR column is not available.
        Uses True Range calculation as proxy for ATR.
        """
        # Calculate True Range manually
        high = zone_data['high']
        low = zone_data['low']
        close = zone_data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        avg_atr = float(true_range.mean())
        
        # Price range normalized by estimated ATR
        price_range = float(high.max() - low.min())
        normalized_range = (price_range / avg_atr) if avg_atr > 0 else 0.0
        
        # Estimate trend from True Range
        tr_start = float(true_range.iloc[:5].mean()) if len(true_range) >= 5 else float(true_range.iloc[0])
        tr_end = float(true_range.iloc[-5:].mean()) if len(true_range) >= 5 else float(true_range.iloc[-1])
        tr_change = ((tr_end / tr_start) - 1) if tr_start > 0 else 0.0
        
        if tr_change > 0.2:
            atr_trend = 'increasing'
        elif tr_change < -0.2:
            atr_trend = 'decreasing'
        else:
            atr_trend = 'stable'
        
        return {
            'avg_atr': avg_atr,
            'normalized_range': normalized_range,
            'trend': atr_trend
        }
    
    def _calculate_volatility_score(
        self,
        bb_metrics: Dict[str, Any],
        atr_metrics: Dict[str, Any]
    ) -> float:
        """
        Calculate composite volatility score (0-10).
        
        Combines:
        - Bollinger width (wider = higher volatility)
        - ATR normalized range (larger = higher volatility)
        - Band touches (more touches = more volatility)
        """
        # Bollinger component (0-5)
        # Typical BB width is 2-8%, so normalize to 0-5 range
        bb_score = min(bb_metrics['width_pct'] / 2.0, 5.0)
        
        # ATR component (0-3)
        # Normalized range typically 1-5, normalize to 0-3
        atr_score = min(atr_metrics['normalized_range'] / 2.0, 3.0)
        
        # Band touches component (0-2)
        total_touches = bb_metrics['upper_touches'] + bb_metrics['lower_touches']
        touch_score = min(total_touches / 5.0, 2.0)  # 5+ touches = max score
        
        # Total score (0-10)
        total_score = bb_score + atr_score + touch_score
        
        return float(min(max(total_score, 0.0), 10.0))
    
    def _classify_volatility_regime(self, score: float) -> str:
        """
        Classify volatility regime based on composite score.
        
        Ranges:
        - low: 0-2.5
        - medium: 2.5-5.0
        - high: 5.0-7.5
        - extreme: 7.5-10.0
        """
        if score < 2.5:
            return 'low'
        elif score < 5.0:
            return 'medium'
        elif score < 7.5:
            return 'high'
        else:
            return 'extreme'
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        return {
            'name': 'Combined (Bollinger + ATR)',
            'description': 'Volatility assessment combining Bollinger Bands and ATR indicators',
            'params': {
                'bb_length': self.bb_length,
                'bb_std': self.bb_std,
                'touch_threshold': self.touch_threshold
            },
            'indicators': ['Bollinger Bands (pandas-ta)', 'ATR'],
            'source': 'Classic technical analysis'
        }

