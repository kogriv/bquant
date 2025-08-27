"""
BQuant built-in indicator library

This module contains preloaded technical indicators implemented specifically for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

from .base import PreloadedIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ..core.exceptions import IndicatorCalculationError
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SimpleMovingAverage(PreloadedIndicator):
    """
    Simple Moving Average (SMA) indicator.
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


class ExponentialMovingAverage(PreloadedIndicator):
    """
    Exponential Moving Average (EMA) indicator.
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
            
            period = kwargs.get('period', self.period)
            
            self.logger.info(f"Calculating EMA with period {period}")
            
            # Вычисляем EMA
            ema_values = data['close'].ewm(span=period).mean()
            
            result_data = pd.DataFrame({
                f'ema_{period}': ema_values
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'period': period,
                    'calculation_method': 'exponential_weighted_mean',
                    'alpha': 2 / (period + 1),
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            raise IndicatorCalculationError(
                f"Failed to calculate EMA: {e}",
                {'indicator': self.name, 'period': period}
            )


class RelativeStrengthIndex(PreloadedIndicator):
    """
    Relative Strength Index (RSI) indicator.
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


class MACD(PreloadedIndicator):
    """
    Moving Average Convergence Divergence (MACD) indicator.
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD indicator.
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period  
            signal_period: Signal line EMA period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        super().__init__('macd', {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period
        })
    
    def get_output_columns(self) -> List[str]:
        """Returns output columns."""
        return ['macd', 'macd_signal', 'macd_hist']
    
    def get_description(self) -> str:
        """Returns indicator description."""
        return f"MACD ({self.fast_period}, {self.slow_period}, {self.signal_period})"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.slow_period + self.signal_period
    
    def get_required_columns(self) -> List[str]:
        """Returns required input columns."""
        return ['close']
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate MACD.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with MACD values
        """
        try:
            self.validate_data(data)
            
            fast_period = kwargs.get('fast_period', self.fast_period)
            slow_period = kwargs.get('slow_period', self.slow_period)
            signal_period = kwargs.get('signal_period', self.signal_period)
            
            self.logger.info(f"Calculating MACD ({fast_period}, {slow_period}, {signal_period})")
            
            # Вычисляем быструю и медленную EMA
            fast_ema = data['close'].ewm(span=fast_period).mean()
            slow_ema = data['close'].ewm(span=slow_period).mean()
            
            # Вычисляем MACD линию
            macd_line = fast_ema - slow_ema
            
            # Вычисляем сигнальную линию
            signal_line = macd_line.ewm(span=signal_period).mean()
            
            # Вычисляем гистограмму
            histogram = macd_line - signal_line
            
            result_data = pd.DataFrame({
                'macd': macd_line,
                'macd_signal': signal_line,
                'macd_hist': histogram
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period,
                    'calculation_method': 'ema_difference',
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            fast_period = kwargs.get('fast_period', self.fast_period)
            slow_period = kwargs.get('slow_period', self.slow_period)
            signal_period = kwargs.get('signal_period', self.signal_period)
            
            raise IndicatorCalculationError(
                f"Failed to calculate MACD: {e}",
                {
                    'indicator': self.name,
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period
                }
            )


class BollingerBands(PreloadedIndicator):
    """
    Bollinger Bands indicator.
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


# Реестр встроенных индикаторов
BUILTIN_INDICATORS = {
    'sma': SimpleMovingAverage,
    'ema': ExponentialMovingAverage,
    'rsi': RelativeStrengthIndex,
    'macd': MACD,
    'bbands': BollingerBands,
}


def register_builtin_indicators():
    """
    Регистрация всех встроенных индикаторов в фабрике.
    """
    from .base import IndicatorFactory
    
    registered_count = 0
    
    for name, indicator_class in BUILTIN_INDICATORS.items():
        try:
            IndicatorFactory.register_indicator(name, indicator_class)
            registered_count += 1
        except Exception as e:
            logger.error(f"Failed to register {name}: {e}")
    
    logger.info(f"Registered {registered_count} builtin indicators")
    return registered_count


def get_builtin_indicators() -> List[str]:
    """
    Получить список встроенных индикаторов.
    
    Returns:
        Список названий встроенных индикаторов
    """
    return list(BUILTIN_INDICATORS.keys())


def create_indicator(name: str, **kwargs):
    """
    Создать встроенный индикатор по имени.
    
    Args:
        name: Название индикатора
        **kwargs: Параметры индикатора
    
    Returns:
        Экземпляр индикатора
    """
    if name.lower() not in BUILTIN_INDICATORS:
        raise ValueError(f"Unknown builtin indicator: {name}")
    
    indicator_class = BUILTIN_INDICATORS[name.lower()]
    return indicator_class(**kwargs)


# Экспорт
__all__ = [
    'SimpleMovingAverage',
    'ExponentialMovingAverage', 
    'RelativeStrengthIndex',
    'MACD',
    'BollingerBands',
    'BUILTIN_INDICATORS',
    'register_builtin_indicators',
    'get_builtin_indicators',
    'create_indicator'
]
