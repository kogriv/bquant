"""
Data validation functions for BQuant

This module provides comprehensive validation functions for financial data.
Перенесено и адаптировано из scripts/data/data_validator.py.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta

from ..core.config import DATA_VALIDATION
from ..core.exceptions import DataValidationError, create_data_validation_error
from ..core.logging_config import get_logger

# Получаем логгер для модуля
logger = get_logger(__name__)


def validate_ohlcv_data(df: pd.DataFrame, strict: bool = True) -> Dict[str, Any]:
    """
    Validate OHLCV data for common issues.
    
    Args:
        df: DataFrame with OHLCV data
        strict: Whether to perform strict validation
    
    Returns:
        Dictionary with validation results
        
    Structure:
        {
            'is_valid': bool,
            'issues': List[str],
            'warnings': List[str],
            'stats': Dict[str, Any],
            'recommendations': List[str]
        }
    """
    logger.info("Validating OHLCV data")
    
    validation_results = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'stats': {},
        'recommendations': []
    }
    
    try:
        # Basic structure validation
        _validate_basic_structure(df, validation_results, strict)
        
        # Data quality validation
        _validate_data_quality(df, validation_results)
        
        # OHLC relationship validation
        _validate_ohlc_relationships(df, validation_results)
        
        # Time series validation
        _validate_time_series(df, validation_results)
        
        # Volume validation (if present)
        if 'volume' in df.columns:
            _validate_volume_data(df, validation_results)
        
        # Calculate summary statistics
        validation_results['stats'] = _calculate_validation_stats(df)
        
        # Generate recommendations
        _generate_recommendations(validation_results)
        
        # Final validation status
        if validation_results['issues']:
            validation_results['is_valid'] = False
        
        logger.info(f"Validation completed. Valid: {validation_results['is_valid']}, "
                   f"Issues: {len(validation_results['issues'])}, "
                   f"Warnings: {len(validation_results['warnings'])}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            'is_valid': False,
            'issues': [f"Validation error: {str(e)}"],
            'warnings': [],
            'stats': {},
            'recommendations': ['Fix validation errors before proceeding']
        }


def validate_data_completeness(
    df: pd.DataFrame, 
    required_columns: Optional[List[str]] = None,
    min_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Validate data completeness.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required columns
        min_rows: Minimum number of rows required
    
    Returns:
        Validation results dictionary
    """
    if required_columns is None:
        required_columns = DATA_VALIDATION['required_columns']
    
    if min_rows is None:
        min_rows = DATA_VALIDATION['min_records']
    
    results = {
        'is_complete': True,
        'missing_columns': [],
        'insufficient_rows': False,
        'missing_data_ratio': {},
        'recommendations': []
    }
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        results['is_complete'] = False
        results['missing_columns'] = missing_columns
        results['recommendations'].append(f"Add missing columns: {missing_columns}")
    
    # Check minimum rows
    if len(df) < min_rows:
        results['is_complete'] = False
        results['insufficient_rows'] = True
        results['recommendations'].append(f"Increase data size to at least {min_rows} rows")
    
    # Check missing data ratios
    max_missing_ratio = DATA_VALIDATION.get('max_missing_ratio', 0.1)
    for col in df.columns:
        missing_ratio = df[col].isnull().sum() / len(df)
        results['missing_data_ratio'][col] = missing_ratio
        
        if missing_ratio > max_missing_ratio:
            results['is_complete'] = False
            results['recommendations'].append(
                f"Column '{col}' has {missing_ratio:.2%} missing data (>{max_missing_ratio:.2%})"
            )
    
    return results


def validate_price_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate price data consistency and logical relationships.
    
    Args:
        df: DataFrame with price data
    
    Returns:
        Validation results dictionary
    """
    results = {
        'is_consistent': True,
        'price_issues': [],
        'logical_errors': [],
        'extreme_values': [],
        'recommendations': []
    }
    
    price_columns = ['open', 'high', 'low', 'close']
    existing_price_columns = [col for col in price_columns if col in df.columns]
    
    if len(existing_price_columns) < 2:
        results['recommendations'].append("Need at least 2 price columns for consistency validation")
        return results
    
    # Check for non-positive prices
    for col in existing_price_columns:
        non_positive = (df[col] <= 0).sum()
        if non_positive > 0:
            results['is_consistent'] = False
            results['price_issues'].append(f"{non_positive} non-positive values in {col}")
    
    # Check OHLC relationships
    if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        # High should be >= Low
        high_low_errors = (df['high'] < df['low']).sum()
        if high_low_errors > 0:
            results['is_consistent'] = False
            results['logical_errors'].append(f"{high_low_errors} cases where high < low")
        
        # High should be >= Open, Close
        for col in ['open', 'close']:
            errors = (df['high'] < df[col]).sum()
            if errors > 0:
                results['logical_errors'].append(f"{errors} cases where high < {col}")
        
        # Low should be <= Open, Close
        for col in ['open', 'close']:
            errors = (df['low'] > df[col]).sum()
            if errors > 0:
                results['logical_errors'].append(f"{errors} cases where low > {col}")
    
    # Check for extreme price changes
    for col in existing_price_columns:
        if len(df) > 1:
            price_changes = df[col].pct_change().abs()
            extreme_changes = (price_changes > 0.5).sum()  # >50% change
            if extreme_changes > 0:
                results['extreme_values'].append(
                    f"{extreme_changes} extreme price changes (>50%) in {col}"
                )
    
    if results['logical_errors']:
        results['is_consistent'] = False
        results['recommendations'].append("Fix OHLC logical inconsistencies")
    
    return results


def validate_time_series_continuity(
    df: pd.DataFrame, 
    expected_frequency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate time series continuity and frequency.
    
    Args:
        df: DataFrame with datetime index
        expected_frequency: Expected frequency (e.g., '1H', '1D')
    
    Returns:
        Validation results dictionary
    """
    results = {
        'is_continuous': True,
        'detected_frequency': None,
        'gaps': [],
        'duplicates': [],
        'irregular_intervals': [],
        'recommendations': []
    }
    
    if not isinstance(df.index, pd.DatetimeIndex):
        results['is_continuous'] = False
        results['recommendations'].append("Index should be DatetimeIndex for time series validation")
        return results
    
    if len(df) < 2:
        results['recommendations'].append("Need at least 2 records for continuity validation")
        return results
    
    # Detect frequency
    try:
        inferred_freq = pd.infer_freq(df.index)
        results['detected_frequency'] = inferred_freq
    except Exception:
        results['detected_frequency'] = None
    
    # Check for duplicates
    duplicate_indices = df.index.duplicated()
    if duplicate_indices.any():
        results['is_continuous'] = False
        results['duplicates'] = df.index[duplicate_indices].tolist()
        results['recommendations'].append(f"Remove {duplicate_indices.sum()} duplicate timestamps")
    
    # Check for gaps
    if expected_frequency:
        expected_index = pd.date_range(
            start=df.index.min(),
            end=df.index.max(),
            freq=expected_frequency
        )
        missing_timestamps = expected_index.difference(df.index)
        if len(missing_timestamps) > 0:
            results['is_continuous'] = False
            results['gaps'] = missing_timestamps.tolist()
            results['recommendations'].append(f"Fill {len(missing_timestamps)} missing timestamps")
    
    # Check for irregular intervals
    intervals = df.index.to_series().diff().dropna()
    if len(intervals) > 0:
        most_common_interval = intervals.mode()
        if len(most_common_interval) > 0:
            irregular_mask = intervals != most_common_interval.iloc[0]
            irregular_count = irregular_mask.sum()
            if irregular_count > len(intervals) * 0.1:  # >10% irregular
                results['irregular_intervals'] = intervals[irregular_mask].tolist()
                results['recommendations'].append(
                    f"{irregular_count} irregular time intervals detected"
                )
    
    return results


def validate_statistical_properties(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate statistical properties of the data.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Statistical validation results
    """
    results = {
        'statistics': {},
        'outliers': {},
        'distribution_issues': [],
        'recommendations': []
    }
    
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        
        # Basic statistics
        stats = {
            'mean': series.mean(),
            'std': series.std(),
            'min': series.min(),
            'max': series.max(),
            'skewness': series.skew(),
            'kurtosis': series.kurtosis()
        }
        results['statistics'][col] = stats
        
        # Outlier detection using IQR method
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = series[(series < lower_bound) | (series > upper_bound)]
        if len(outliers) > 0:
            results['outliers'][col] = {
                'count': len(outliers),
                'percentage': len(outliers) / len(series) * 100,
                'bounds': (lower_bound, upper_bound)
            }
        
        # Check for extreme skewness
        if abs(stats['skewness']) > 2:
            results['distribution_issues'].append(
                f"Column '{col}' has extreme skewness: {stats['skewness']:.2f}"
            )
        
        # Check for extreme kurtosis
        if abs(stats['kurtosis']) > 7:
            results['distribution_issues'].append(
                f"Column '{col}' has extreme kurtosis: {stats['kurtosis']:.2f}"
            )
    
    if results['distribution_issues']:
        results['recommendations'].append("Consider data transformation for extreme distributions")
    
    if any(outlier_info['percentage'] > 5 for outlier_info in results['outliers'].values()):
        results['recommendations'].append("Consider outlier treatment (>5% outliers detected)")
    
    return results


# Вспомогательные функции для валидации

def _validate_basic_structure(df: pd.DataFrame, results: Dict, strict: bool):
    """Validate basic DataFrame structure."""
    if df.empty:
        results['issues'].append("DataFrame is empty")
        return
    
    # Check required columns
    required_columns = DATA_VALIDATION['required_columns']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        if strict:
            results['issues'].append(f"Missing required columns: {missing_columns}")
        else:
            results['warnings'].append(f"Missing required columns: {missing_columns}")
    
    # Check minimum rows
    min_records = DATA_VALIDATION.get('min_records', 1)
    if len(df) < min_records:
        results['issues'].append(f"Insufficient data: {len(df)} rows, minimum: {min_records}")


def _validate_data_quality(df: pd.DataFrame, results: Dict):
    """Validate data quality issues."""
    # Check for missing values
    total_cells = df.size
    missing_cells = df.isnull().sum().sum()
    missing_ratio = missing_cells / total_cells
    
    if missing_ratio > 0.1:  # >10% missing
        results['warnings'].append(f"High missing data ratio: {missing_ratio:.2%}")
    
    # Check for duplicate rows
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        results['warnings'].append(f"{duplicate_rows} duplicate rows found")


def _validate_ohlc_relationships(df: pd.DataFrame, results: Dict):
    """Validate OHLC logical relationships."""
    ohlc_columns = ['open', 'high', 'low', 'close']
    existing_ohlc = [col for col in ohlc_columns if col in df.columns]
    
    if len(existing_ohlc) < 3:
        return
    
    # High >= Low
    if 'high' in existing_ohlc and 'low' in existing_ohlc:
        violations = (df['high'] < df['low']).sum()
        if violations > 0:
            results['issues'].append(f"{violations} cases where high < low")


def _validate_time_series(df: pd.DataFrame, results: Dict):
    """Validate time series properties."""
    if isinstance(df.index, pd.DatetimeIndex):
        # Check for chronological order
        if not df.index.is_monotonic_increasing:
            results['warnings'].append("Time series is not in chronological order")
        
        # Check for duplicate timestamps
        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            results['warnings'].append(f"{duplicates} duplicate timestamps")


def _validate_volume_data(df: pd.DataFrame, results: Dict):
    """Validate volume data."""
    volume = df['volume']
    
    # Check for negative volume
    negative_volume = (volume < 0).sum()
    if negative_volume > 0:
        results['issues'].append(f"{negative_volume} negative volume values")
    
    # Check for zero volume
    zero_volume = (volume == 0).sum()
    if zero_volume > len(df) * 0.1:  # >10% zero volume
        results['warnings'].append(f"{zero_volume} zero volume periods ({zero_volume/len(df):.1%})")


def _calculate_validation_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate summary statistics for validation."""
    stats = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'date_range': None,
        'missing_data_summary': {}
    }
    
    # Date range
    if isinstance(df.index, pd.DatetimeIndex) and not df.index.empty:
        stats['date_range'] = {
            'start': df.index.min(),
            'end': df.index.max(),
            'duration_days': (df.index.max() - df.index.min()).days
        }
    
    # Missing data summary
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        stats['missing_data_summary'][col] = {
            'count': missing_count,
            'percentage': missing_count / len(df) * 100
        }
    
    return stats


def _generate_recommendations(results: Dict):
    """Generate recommendations based on validation results."""
    if results['issues']:
        results['recommendations'].append("Fix all critical issues before proceeding with analysis")
    
    if results['warnings']:
        results['recommendations'].append("Review warnings and consider data cleaning")
    
    if not results['recommendations']:
        results['recommendations'].append("Data quality is acceptable for analysis")


# Экспорт функций
__all__ = [
    'validate_ohlcv_data',
    'validate_data_completeness',
    'validate_price_consistency',
    'validate_time_series_continuity',
    'validate_statistical_properties'
]
