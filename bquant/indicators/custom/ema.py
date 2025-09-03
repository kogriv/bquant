"""
Exponential Moving Average (EMA) Indicator

Custom implementation of EMA indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class ExponentialMovingAverage(CustomIndicator):
    """
    Exponential Moving Average (EMA) indicator.
    
    Calculates the exponential moving average of prices over a specified period.
    """
    
    def __init__(self, period: int = 20):
        """
        Initialize EMA indicator.
        
        Args:
            period: Period for exponential moving average calculation
        """
        self.period = period
        super().__init__('ema', {'period': period})
    
    def get_output_columns(self) -> List[str]:
        """Returns output columns."""
        return [f'ema_{self.period}']
    
    def get_description(self) -> str:
        """Returns indicator description."""
        return f"Exponential Moving Average with {self.period} period"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.period
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate EMA.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with EMA values
        """
        try:
            self.validate_data(data)
            
            # Получаем период из kwargs или используем значение по умолчанию
            period = kwargs.get('period', self.period)
            
            self.logger.info(f"Calculating EMA with period {period}")
            
            # Вычисляем EMA
            ema_values = data['close'].ewm(span=period, adjust=False).mean()
            
            result_data = pd.DataFrame({
                f'ema_{period}': ema_values
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'period': period,
                    'calculation_method': 'ewm_mean',
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate EMA: {e}",
                {'indicator': self.name, 'period': period}
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Returns default output columns."""
        return ['ema_20']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Returns class information."""
        return {
            'name': 'ExponentialMovingAverage',
            'type': 'CUSTOM',
            'description': 'Exponential Moving Average indicator implementation',
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
                'period': 'Period for exponential moving average calculation (default: 20)'
            },
            'usage_examples': {
                'basic': "ExponentialMovingAverage()",
                'custom_period': "ExponentialMovingAverage(period=50)"
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
