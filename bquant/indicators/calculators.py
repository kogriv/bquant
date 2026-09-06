"""
High-level calculators and utilities for BQuant indicators

This module provides convenient functions for calculating indicators and managing indicator workflows.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

from .base import IndicatorFactory, IndicatorResult, BaseIndicator, IndicatorConfig, IndicatorSource
from .library import LibraryManager
from ..core.exceptions import IndicatorCalculationError
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class IndicatorCalculator:
    """
    High-level calculator for technical indicators.

    Results are stored by the indicator's **identity** (``IndicatorId.key``, e.g.
    ``custom.sma_10``), not by bare name: until G65 (2026-09-06) ``calculate('sma',
    period=50)`` silently replaced the result of ``calculate('sma', period=10)``.
    """

    def __init__(self, data: pd.DataFrame, auto_load_libraries: bool = True):
        """
        Initialize calculator with price data.

        Args:
            data: DataFrame with OHLCV price data
            auto_load_libraries: load external indicator libraries now (they are
                loaded lazily on first use anyway — G64)
        """
        self.data = data.copy()
        self.results: Dict[str, IndicatorResult] = {}
        self._names: Dict[str, str] = {}
        self.logger = get_logger(f"{__name__}.IndicatorCalculator")

        if auto_load_libraries:
            LibraryManager.ensure_loaded()

    def calculate(self, indicator_name: str, **kwargs) -> IndicatorResult:
        """
        Calculate a CUSTOM indicator and keep the result under its identity key.

        Args:
            indicator_name: Name of the indicator
            **kwargs: Indicator parameters

        Returns:
            IndicatorResult with calculation results
        """
        try:
            indicator = IndicatorFactory.create('custom', indicator_name, **kwargs)
            result = indicator.calculate(self.data)
        except Exception as e:
            self.logger.error(f"Failed to calculate {indicator_name}: {e}")
            raise IndicatorCalculationError(
                f"Calculation failed for {indicator_name}: {e}",
                {'indicator': indicator_name, 'parameters': kwargs}
            )
        key = indicator.get_indicator_id().key
        self.results[key] = result
        self._names[key] = indicator_name.lower()
        self.logger.debug(f"Calculated {key}")
        return result

    def calculate_multiple(self, indicators: Dict[str, Dict[str, Any]]) -> Dict[str, IndicatorResult]:
        """
        Calculate several indicators: ``{name: params}`` → ``{name: IndicatorResult}``.
        A failure is raised, not skipped: a missing entry in the answer used to be
        indistinguishable from an indicator that was never asked for.
        """
        return {name: self.calculate(name, **params) for name, params in indicators.items()}

    def _resolve_key(self, name_or_key: str) -> Optional[str]:
        if name_or_key in self.results:
            return name_or_key
        matches = [key for key, name in self._names.items() if name == name_or_key.lower()]
        if len(matches) > 1:
            raise KeyError(
                f"'{name_or_key}' names {len(matches)} results: {matches}; ask by identity key"
            )
        return matches[0] if matches else None

    def get_result(self, indicator_name: str) -> Optional[IndicatorResult]:
        """
        Get a stored result by identity key (``custom.sma_10``) or by name when the
        name maps to exactly one stored result.

        Raises:
            KeyError: the bare name is ambiguous (several parameterizations stored).
        """
        key = self._resolve_key(indicator_name)
        return self.results.get(key) if key else None

    def get_all_results(self) -> Dict[str, IndicatorResult]:
        """All stored results by identity key."""
        return self.results.copy()

    def combine_results(self, indicator_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Combine stored indicator results with the price data into one DataFrame.

        Args:
            indicator_names: keys or names to include (None for all)
        """
        keys = list(self.results) if indicator_names is None else [
            k for k in (self._resolve_key(n) for n in indicator_names) if k
        ]
        combined_data = self.data.copy()
        for key in keys:
            result = self.results[key]
            for col in result.data.columns:
                target = col if col not in combined_data.columns else f"{key}_{col}"
                combined_data[target] = result.data[col]
        return combined_data

    def clear_cache(self):
        """Forget stored results."""
        self.results.clear()
        self._names.clear()


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
    SMA and EMA for every period — each through its indicator object.

    Until G65 (2026-09-06) only the first period went through the factory; the rest
    were ``rolling().mean()`` / ``ewm(span).mean()`` written here again, which skipped
    the EMA warm-up contract and differed from ``ExponentialMovingAverage`` on 38–174
    bars of the sample depending on the period.

    Returns:
        DataFrame with columns ``sma_<p>`` and ``ema_<p>`` for every period.
    """
    if periods is None:
        periods = [10, 20, 50, 200]

    combined_data = pd.DataFrame(index=data.index)
    for period in periods:
        for name in ('sma', 'ema'):
            result = IndicatorFactory.create('custom', name, period=period).calculate(data)
            for col in result.data.columns:
                combined_data[col] = result.data[col]
    return combined_data


#: The standard suite: (indicator, parameters). Keys of the answer are identity slugs.
STANDARD_SUITE = (
    ('sma', {'period': 20}),
    ('sma', {'period': 50}),
    ('ema', {'period': 12}),
    ('ema', {'period': 26}),
    ('rsi', {'period': 14}),
    ('macd', {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),
    ('bbands', {'period': 20, 'std_dev': 2.0}),
)


def create_indicator_suite(data: pd.DataFrame) -> Dict[str, IndicatorResult]:
    """
    Calculate the standard suite (:data:`STANDARD_SUITE`) — every entry through its
    indicator object, keyed by identity slug (``sma_20``, ``macd_12_26_9``, …).
    """
    results: Dict[str, IndicatorResult] = {}
    for name, params in STANDARD_SUITE:
        indicator = IndicatorFactory.create('custom', name, **params)
        results[indicator.get_indicator_id().slug] = indicator.calculate(data)
    logger.info(f"Calculated {len(results)} indicators in standard suite")
    return results


def get_available_indicators() -> Dict[str, str]:
    """
    Registered indicators ``{name: source}``. Built-ins are registered when
    ``bquant.indicators`` is imported; external libraries load on this first ask (G64).
    """
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
        indicator = IndicatorFactory.create('custom', indicator_name, **kwargs)
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
    'STANDARD_SUITE',
    'get_available_indicators',
    'validate_indicator_data'
]
