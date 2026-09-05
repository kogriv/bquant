"""
Bollinger Bands Indicator

Custom implementation of Bollinger Bands indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError, DataValidationError
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
    
    #: Роли, которые объявляет этот индикатор, в порядке выдачи колонок.
    _ROLES = ("upper", "middle", "lower", "width", "percent")

    def get_output_roles(self) -> Dict[str, str]:
        """Роль → каноническое имя колонки (`bbands_20_2__upper`).

        Слаг берётся от `bbands`, а не от сокращения `bb`: сокращение не
        совпадало ни с именем индикатора в фабрике, ни с тем, как его зовёт
        pandas-ta, — третье написание одного и того же (§4.2 дизайна).
        """
        iid = self.get_indicator_id()
        return {role: iid.column(role) for role in self._ROLES}

    def get_output_columns(self) -> List[str]:
        """Колонки в порядке объявления ролей."""
        return list(self.get_output_roles().values())

    def get_description(self) -> str:
        """Returns indicator description."""
        return f"Bollinger Bands ({self.period}, {self.std_dev})"
    
    def get_required_columns(self) -> List[str]:
        """The one input column; validation checks its dtype and finiteness on it."""
        return ['close']

    def get_min_records(self, **params) -> int:
        """Minimum records for the effective parameters of a call, not of the constructor."""
        return params.get('period', self.period)
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate Bollinger Bands.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with Bollinger Bands values
        """
        period = kwargs.get('period', self.period)
        std_dev = kwargs.get('std_dev', self.std_dev)
        try:
            self.validate_data(data, period=period, std_dev=std_dev)
            
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
            
            # Имена — от идентичности по фактическим параметрам вызова (см. macd.py).
            columns = self.get_indicator_id(period=period, std_dev=std_dev)
            result_data = pd.DataFrame({
                columns.column('upper'): upper_band,
                columns.column('middle'): middle_band,
                columns.column('lower'): lower_band,
                columns.column('width'): bb_width,
                columns.column('percent'): bb_percent,
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
            
        except DataValidationError:
            raise
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate Bollinger Bands: {e}",
                {'indicator': self.name, 'period': period, 'std_dev': std_dev}
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Колонки экземпляра с параметрами по умолчанию (выводятся, см. macd.py)."""
        return cls().get_output_columns()
    
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
                'width': 'Band width as percentage of middle band',
                'percent': 'Price position within bands (0-100%)',
                'squeeze': 'Narrow bands indicate low volatility',
                'expansion': 'Wide bands indicate high volatility'
            }
        }
