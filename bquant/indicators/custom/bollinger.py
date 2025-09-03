"""
Bollinger Bands Indicator

Custom implementation of Bollinger Bands indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class BollingerBands(CustomIndicator):
    """
    Bollinger Bands indicator.
    
    Measures price volatility using moving average and standard deviation bands.
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        """
        Initialize Bollinger Bands indicator.
        
        Args:
            period: Period for moving average and standard deviation
            std_dev: Standard deviation multiplier
        """
        self.period = period
        self.std_dev = std_dev
        super().__init__('bbands', {'period': period, 'std_dev': std_dev})
    
    def get_output_columns(self) -> List[str]:
        """Returns output columns."""
        return ['bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_percent']
    
    def get_description(self) -> str:
        """Returns indicator description."""
        return f"Bollinger Bands ({self.period}, {self.std_dev})"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.period
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate Bollinger Bands.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with Bollinger Bands values
        """
        try:
            self.validate_data(data)
            
            period = kwargs.get('period', self.period)
            std_dev = kwargs.get('std_dev', self.std_dev)
            
            self.logger.info(f"Calculating Bollinger Bands ({period}, {std_dev})")
            
            # Вычисляем среднюю линию (SMA)
            middle_band = data['close'].rolling(window=period).mean()
            
            # Вычисляем стандартное отклонение
            std = data['close'].rolling(window=period).std()
            
            # Вычисляем верхнюю и нижнюю полосы
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            # Дополнительные метрики
            bb_width = (upper_band - lower_band) / middle_band * 100
            bb_percent = (data['close'] - lower_band) / (upper_band - lower_band) * 100
            
            result_data = pd.DataFrame({
                'bb_upper': upper_band,
                'bb_middle': middle_band,
                'bb_lower': lower_band,
                'bb_width': bb_width,
                'bb_percent': bb_percent
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'period': period,
                    'std_dev': std_dev,
                    'calculation_method': 'sma_plus_std',
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate Bollinger Bands: {e}",
                {'indicator': self.name, 'period': period, 'std_dev': std_dev}
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Returns default output columns."""
        return ['bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_percent']
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Returns class information."""
        return {
            'name': 'BollingerBands',
            'type': 'CUSTOM',
            'description': 'Bollinger Bands indicator implementation',
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
                'period': 'Period for moving average and standard deviation (default: 20)',
                'std_dev': 'Standard deviation multiplier (default: 2.0)'
            },
            'usage_examples': {
                'basic': "BollingerBands()",
                'custom_params': "BollingerBands(period=50, std_dev=2.5)"
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
            ],
            'interpretation': {
                'upper_band': 'Upper volatility boundary',
                'middle_band': 'Simple moving average (trend)',
                'lower_band': 'Lower volatility boundary',
                'bb_width': 'Band width as percentage of middle band',
                'bb_percent': 'Price position within bands (0-100%)',
                'squeeze': 'Narrow bands indicate low volatility',
                'expansion': 'Wide bands indicate high volatility'
            }
        }
