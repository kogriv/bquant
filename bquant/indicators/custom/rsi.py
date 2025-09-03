"""
Relative Strength Index (RSI) Indicator

Custom implementation of RSI indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class RelativeStrengthIndex(CustomIndicator):
    """
    Relative Strength Index (RSI) indicator.
    
    Measures the speed and magnitude of price changes to identify overbought/oversold conditions.
    """
    
    def __init__(self, period: int = 14):
        """
        Initialize RSI indicator.
        
        Args:
            period: Period for RSI calculation
        """
        self.period = period
        super().__init__('rsi', {'period': period})
    
    def get_output_columns(self) -> List[str]:
        """Returns output columns."""
        return [f'rsi_{self.period}']
    
    def get_description(self) -> str:
        """Returns indicator description."""
        return f"Relative Strength Index with {self.period} period"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.period + 1
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate RSI.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with RSI values
        """
        try:
            self.validate_data(data)
            
            period = kwargs.get('period', self.period)
            
            self.logger.info(f"Calculating RSI with period {period}")
            
            # Вычисляем изменения цен
            price_changes = data['close'].diff()
            
            # Разделяем на положительные и отрицательные изменения
            gains = price_changes.where(price_changes > 0, 0)
            losses = -price_changes.where(price_changes < 0, 0)
            
            # Вычисляем средние значения методом экспоненциального сглаживания
            avg_gains = gains.ewm(alpha=1/period).mean()
            avg_losses = losses.ewm(alpha=1/period).mean()
            
            # Вычисляем RS и RSI
            rs = avg_gains / avg_losses
            rsi_values = 100 - (100 / (1 + rs))
            
            result_data = pd.DataFrame({
                f'rsi_{period}': rsi_values
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'period': period,
                    'calculation_method': 'ewm_smoothing',
                    'overbought_level': 70,
                    'oversold_level': 30,
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate RSI: {e}",
                {'indicator': self.name, 'period': period}
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Returns default output columns."""
        return ['rsi_14']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Returns class information."""
        return {
            'name': 'RelativeStrengthIndex',
            'type': 'CUSTOM',
            'description': 'Relative Strength Index indicator implementation',
            'default_columns': cls.get_default_columns(),
            'required_fields': {
                'close': 'Close price values (numeric)'
            },
            'optional_fields': {
                'high': 'High price values (numeric)',
                'low': 'Low price values (numeric)',
                'open': 'Open price values (numeric)'
            },
            'parameters': {
                'period': 'Period for RSI calculation (default: 14)'
            },
            'usage_examples': {
                'basic': "RelativeStrengthIndex()",
                'custom_period': "RelativeStrengthIndex(period=21)"
            },
            'data_requirements': {
                'min_records': 15,
                'column_types': 'numeric',
                'required_columns': ['close']
            },
            'available_methods': [
                'calculate()',
                'validate_data()',
                'get_statistics()',
                'is_trending_up()',
                'is_trending_down()'
            ],
            'interpretation': {
                'overbought': 'RSI > 70 indicates overbought conditions',
                'oversold': 'RSI < 30 indicates oversold conditions',
                'neutral': 'RSI between 30-70 indicates neutral conditions'
            }
        }
