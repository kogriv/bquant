"""
Simple Moving Average (SMA) Indicator

Custom implementation of SMA indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class SimpleMovingAverage(CustomIndicator):
    """
    Simple Moving Average (SMA) indicator.
    
    Calculates the arithmetic mean of prices over a specified period.
    """
    
    def __init__(self, period: int = 20):
        """
        Initialize SMA indicator.
        
        Args:
            period: Period for moving average calculation
        """
        self.period = period
        super().__init__('sma', {'period': period})
    
    def get_output_columns(self) -> List[str]:
        """Returns output columns."""
        return [f'sma_{self.period}']
    
    def get_description(self) -> str:
        """Returns indicator description."""
        return f"Simple Moving Average with {self.period} period"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.period
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate SMA.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with SMA values
        """
        try:
            self.validate_data(data)
            
            # Получаем период из kwargs или используем значение по умолчанию
            period = kwargs.get('period', self.period)
            
            self.logger.info(f"Calculating SMA with period {period}")
            
            # Вычисляем SMA
            sma_values = data['close'].rolling(window=period).mean()
            
            result_data = pd.DataFrame({
                f'sma_{period}': sma_values
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'period': period,
                    'calculation_method': 'rolling_mean',
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate SMA: {e}",
                {'indicator': self.name, 'period': period}
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Returns default output columns."""
        return ['sma_20']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Returns class information."""
        return {
            'name': 'SimpleMovingAverage',
            'type': 'CUSTOM',
            'description': 'Simple Moving Average indicator implementation',
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
                'period': 'Period for moving average calculation (default: 20)'
            },
            'usage_examples': {
                'basic': "SimpleMovingAverage()",
                'custom_period': "SimpleMovingAverage(period=50)"
            },
            'data_requirements': {
                'min_records': 20,
                'column_types': 'numeric',
                'required_columns': ['close']
            },
            'available_methods': [
                'calculate()',
                'validate_data()',
                'get_statistics()',
                'is_trending_up()',
                'is_trending_down()'
            ]
        }
