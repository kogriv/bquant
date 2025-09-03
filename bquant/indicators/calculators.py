"""
High-level calculators and utilities for BQuant indicators

This module provides convenient functions for calculating indicators and managing indicator workflows.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

from .base import IndicatorFactory, IndicatorResult, BaseIndicator, IndicatorConfig, IndicatorSource
from .custom import register_builtin_indicators
from .library import LibraryManager
from ..core.exceptions import IndicatorCalculationError
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class IndicatorCalculator:
    """
    High-level calculator for technical indicators.
    
    Provides convenient methods for calculating multiple indicators and managing results.
    """
    
    def __init__(self, data: pd.DataFrame, auto_load_libraries: bool = True):
        """
        Initialize calculator with price data.
        
        Args:
            data: DataFrame with OHLCV price data
            auto_load_libraries: Whether to automatically load external libraries
        """
        self.data = data.copy()
        self.results = {}
        self.logger = get_logger(f"{__name__}.IndicatorCalculator")
        
        # Автоматическая загрузка библиотек
        if auto_load_libraries:
            self._load_all_indicators()
    
    def _load_all_indicators(self):
        """Load all available indicators."""
        try:
            # Загружаем встроенные индикаторы
            builtin_count = register_builtin_indicators()
            self.logger.info(f"Loaded {builtin_count} builtin indicators")
            
            # Загружаем внешние библиотеки
            library_results = LibraryManager.load_all_libraries()
            total_library = sum(library_results.values())
            self.logger.info(f"Loaded {total_library} external indicators")
            
        except Exception as e:
            self.logger.warning(f"Failed to load some indicators: {e}")
    
    def calculate(self, indicator_name: str, **kwargs) -> IndicatorResult:
        """
        Calculate single indicator.
        
        Args:
            indicator_name: Name of the indicator
            **kwargs: Indicator parameters
        
        Returns:
            IndicatorResult with calculation results
        """
        try:
            self.logger.info(f"Calculating indicator: {indicator_name}")
            
            # Создаем индикатор через фабрику
            indicator = IndicatorFactory.create_indicator(indicator_name, self.data, **kwargs)
            
            # Вычисляем результат
            result = indicator.calculate_with_cache(self.data, **kwargs)
            
            # Сохраняем результат
            self.results[indicator_name] = result
            
            self.logger.info(f"Successfully calculated {indicator_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to calculate {indicator_name}: {e}")
            raise IndicatorCalculationError(
                f"Calculation failed for {indicator_name}: {e}",
                {'indicator': indicator_name, 'parameters': kwargs}
            )
    
    def calculate_multiple(self, indicators: Dict[str, Dict[str, Any]]) -> Dict[str, IndicatorResult]:
        """
        Calculate multiple indicators.
        
        Args:
            indicators: Dictionary {indicator_name: parameters}
        
        Returns:
            Dictionary of results {indicator_name: IndicatorResult}
        """
        results = {}
        
        for name, params in indicators.items():
            try:
                result = self.calculate(name, **params)
                results[name] = result
            except Exception as e:
                self.logger.error(f"Failed to calculate {name}: {e}")
                # Продолжаем вычисления остальных индикаторов
                continue
        
        return results
    
    def get_result(self, indicator_name: str) -> Optional[IndicatorResult]:
        """
        Get cached result for indicator.
        
        Args:
            indicator_name: Name of the indicator
        
        Returns:
            IndicatorResult or None if not calculated
        """
        return self.results.get(indicator_name)
    
    def get_all_results(self) -> Dict[str, IndicatorResult]:
        """Get all cached results."""
        return self.results.copy()
    
    def combine_results(self, indicator_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Combine multiple indicator results into single DataFrame.
        
        Args:
            indicator_names: List of indicators to include (None for all)
        
        Returns:
            Combined DataFrame with all indicator data
        """
        if indicator_names is None:
            indicator_names = list(self.results.keys())
        
        combined_data = self.data.copy()
        
        for name in indicator_names:
            if name in self.results:
                result = self.results[name]
                # Добавляем колонки с префиксом если необходимо
                for col in result.data.columns:
                    if col not in combined_data.columns:
                        combined_data[col] = result.data[col]
                    else:
                        combined_data[f"{name}_{col}"] = result.data[col]
        
        return combined_data
    
    def clear_cache(self):
        """Clear all cached results."""
        self.results.clear()
        self.logger.info("Cleared all cached results")


def calculate_indicator(data: pd.DataFrame, indicator_name: str, **kwargs) -> IndicatorResult:
    """
    Convenience function to calculate single indicator.
    
    Args:
        data: DataFrame with price data
        indicator_name: Name of the indicator
        **kwargs: Indicator parameters
    
    Returns:
        IndicatorResult with calculation results
    """
    calculator = IndicatorCalculator(data, auto_load_libraries=False)
    return calculator.calculate(indicator_name, **kwargs)


def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Convenience function to calculate MACD.
    
    Args:
        data: DataFrame with price data
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
    
    Returns:
        DataFrame with MACD data
    """
    result = calculate_indicator(data, 'macd', fast_period=fast, slow_period=slow, signal_period=signal)
    return result.data


def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Convenience function to calculate RSI.
    
    Args:
        data: DataFrame with price data
        period: RSI period
    
    Returns:
        Series with RSI values
    """
    result = calculate_indicator(data, 'rsi', period=period)
    return result.data.iloc[:, 0]  # Возвращаем первую колонку как Series


def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    Convenience function to calculate Bollinger Bands.
    
    Args:
        data: DataFrame with price data
        period: Period for calculation
        std_dev: Standard deviation multiplier
    
    Returns:
        DataFrame with Bollinger Bands data
    """
    result = calculate_indicator(data, 'bbands', period=period, std_dev=std_dev)
    return result.data


def calculate_moving_averages(data: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
    """
    Calculate multiple moving averages.
    
    Args:
        data: DataFrame with price data
        periods: List of periods for moving averages
    
    Returns:
        DataFrame with moving averages
    """
    if periods is None:
        periods = [10, 20, 50, 200]
    
    calculator = IndicatorCalculator(data, auto_load_libraries=False)
    
    # Вычисляем SMA для каждого периода
    sma_indicators = {'sma': {'period': periods[0]}}  # Используем первый период для базового SMA
    
    # Вычисляем EMA для каждого периода  
    ema_indicators = {'ema': {'period': periods[0]}}  # Используем первый период для базового EMA
    
    # Объединяем все индикаторы
    all_indicators = {**sma_indicators, **ema_indicators}
    
    results = calculator.calculate_multiple(all_indicators)
    
    # Объединяем результаты
    combined_data = pd.DataFrame(index=data.index)
    for name, result in results.items():
        for col in result.data.columns:
            combined_data[col] = result.data[col]
    
    # Добавляем дополнительные периоды как колонки
    for period in periods:
        # Для SMA
        if 'sma' in results:
            combined_data[f'sma_{period}'] = data['close'].rolling(window=period).mean()
        
        # Для EMA
        if 'ema' in results:
            combined_data[f'ema_{period}'] = data['close'].ewm(span=period).mean()
    
    return combined_data


def create_indicator_suite(data: pd.DataFrame) -> Dict[str, IndicatorResult]:
    """
    Calculate standard suite of technical indicators.
    
    Args:
        data: DataFrame with price data
    
    Returns:
        Dictionary with all calculated indicators
    """
    calculator = IndicatorCalculator(data)
    
    # Определяем базовые индикаторы (которые можно создать)
    base_indicators = {
        'sma': {'period': 20},  # Базовый SMA
        'ema': {'period': 12},  # Базовый EMA
        'rsi': {'period': 14},  # RSI
        'macd': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},  # MACD
        'bbands': {'period': 20, 'std_dev': 2.0},  # Bollinger Bands
    }
    
    # Вычисляем базовые индикаторы
    results = calculator.calculate_multiple(base_indicators)
    
    # Добавляем дополнительные периоды как отдельные результаты
    additional_results = {}
    
    # SMA с разными периодами
    if 'sma' in results:
        sma_base = results['sma']
        for period in [20, 50]:
            sma_data = data['close'].rolling(window=period).mean()
            sma_result = IndicatorResult(
                name=f'sma_{period}',
                data=pd.DataFrame({f'sma_{period}': sma_data}),
                config=IndicatorConfig(
                    name=f'sma_{period}',
                    parameters={'period': period},
                    source=IndicatorSource.CUSTOM,
                    columns=[f'sma_{period}'],
                    description=f'SMA ({period})'
                ),
                metadata={'period': period, 'calculation_method': 'rolling_mean'}
            )
            additional_results[f'sma_{period}'] = sma_result
    
    # EMA с разными периодами
    if 'ema' in results:
        ema_base = results['ema']
        for period in [26]:
            ema_data = data['close'].ewm(span=period).mean()
            ema_result = IndicatorResult(
                name=f'ema_{period}',
                data=pd.DataFrame({f'ema_{period}': ema_data}),
                config=IndicatorConfig(
                    name=f'ema_{period}',
                    parameters={'period': period},
                    source=IndicatorSource.CUSTOM,
                    columns=[f'ema_{period}'],
                    description=f'EMA ({period})'
                ),
                metadata={'period': period, 'calculation_method': 'ewm_mean'}
            )
            additional_results[f'ema_{period}'] = ema_result
    
    # Объединяем все результаты
    all_results = {**results, **additional_results}
    
    logger.info(f"Calculated {len(all_results)} indicators in standard suite")
    return all_results


def get_available_indicators() -> Dict[str, str]:
    """
    Get list of all available indicators.
    
    Returns:
        Dictionary {indicator_name: source}
    """
    # Загружаем все индикаторы
    register_builtin_indicators()
    LibraryManager.load_all_libraries()
    
    return IndicatorFactory.list_indicators()


def validate_indicator_data(data: pd.DataFrame, indicator_name: str, **kwargs) -> bool:
    """
    Validate data for specific indicator without calculating.
    
    Args:
        data: DataFrame with price data
        indicator_name: Name of the indicator
        **kwargs: Indicator parameters
    
    Returns:
        True if data is valid for the indicator
    """
    try:
        indicator = IndicatorFactory.create_indicator(indicator_name, **kwargs)
        return indicator.validate_data(data)
    except Exception as e:
        logger.warning(f"Data validation failed for {indicator_name}: {e}")
        return False


class BatchCalculator:
    """
    Calculator for batch processing of multiple datasets.
    """
    
    def __init__(self, datasets: Dict[str, pd.DataFrame]):
        """
        Initialize batch calculator.
        
        Args:
            datasets: Dictionary {dataset_name: DataFrame}
        """
        self.datasets = datasets
        self.results = {}
        self.logger = get_logger(f"{__name__}.BatchCalculator")
    
    def calculate_for_all(self, indicator_name: str, **kwargs) -> Dict[str, IndicatorResult]:
        """
        Calculate indicator for all datasets.
        
        Args:
            indicator_name: Name of the indicator
            **kwargs: Indicator parameters
        
        Returns:
            Dictionary {dataset_name: IndicatorResult}
        """
        results = {}
        
        for dataset_name, data in self.datasets.items():
            try:
                calculator = IndicatorCalculator(data, auto_load_libraries=False)
                result = calculator.calculate(indicator_name, **kwargs)
                results[dataset_name] = result
                
                self.logger.info(f"Calculated {indicator_name} for {dataset_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to calculate {indicator_name} for {dataset_name}: {e}")
        
        return results
    
    def calculate_suite_for_all(self) -> Dict[str, Dict[str, IndicatorResult]]:
        """
        Calculate standard indicator suite for all datasets.
        
        Returns:
            Nested dictionary {dataset_name: {indicator_name: IndicatorResult}}
        """
        results = {}
        
        for dataset_name, data in self.datasets.items():
            try:
                suite_results = create_indicator_suite(data)
                results[dataset_name] = suite_results
                
                self.logger.info(f"Calculated indicator suite for {dataset_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to calculate suite for {dataset_name}: {e}")
        
        return results


# Экспорт
__all__ = [
    'IndicatorCalculator',
    'BatchCalculator',
    'calculate_indicator',
    'calculate_macd',
    'calculate_rsi',
    'calculate_bollinger_bands',
    'calculate_moving_averages',
    'create_indicator_suite',
    'get_available_indicators',
    'validate_indicator_data'
]
