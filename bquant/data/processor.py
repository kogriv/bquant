"""
Data processing functions for BQuant

This module provides functions for preprocessing and cleaning financial data.
Перенесено и адаптировано из scripts/data/data_processor.py.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple
import warnings

from ..core.exceptions import DataProcessingError, create_data_validation_error
from ..core.logging_config import get_logger

# Получаем логгер для модуля
logger = get_logger(__name__)


def clean_ohlcv_data(
    df: pd.DataFrame, 
    fill_method: str = 'forward',
    remove_outliers: bool = True,
    outlier_threshold: float = 3.0
) -> pd.DataFrame:
    """
    Clean OHLCV data by handling missing values and outliers.
    
    Args:
        df: DataFrame with OHLCV data
        fill_method: Method for filling missing values ('forward', 'backward', 'interpolate')
        remove_outliers: Whether to remove outliers
        outlier_threshold: Standard deviation threshold for outlier detection
    
    Returns:
        Cleaned DataFrame
        
    Raises:
        DataProcessingError: If cleaning fails
    """
    try:
        logger.info("Starting OHLCV data cleaning")
        
        if df.empty:
            logger.warning("Empty DataFrame provided for cleaning")
            return df.copy()
        
        cleaned_df = df.copy()
        
        # Remove rows with all NaN values
        initial_rows = len(cleaned_df)
        cleaned_df.dropna(how='all', inplace=True)
        removed_empty = initial_rows - len(cleaned_df)
        if removed_empty > 0:
            logger.info(f"Removed {removed_empty} empty rows")
        
        # Handle missing values
        cleaned_df = _handle_missing_values(cleaned_df, fill_method)
        
        # Remove outliers if requested
        if remove_outliers:
            cleaned_df = remove_price_outliers(cleaned_df, threshold=outlier_threshold)
        
        # Validate OHLC relationships
        cleaned_df = _fix_ohlc_relationships(cleaned_df)
        
        logger.info(f"Data cleaning completed. Shape: {cleaned_df.shape}")
        return cleaned_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to clean OHLCV data: {e}",
            {'original_shape': df.shape, 'error': str(e)}
        )


def remove_price_outliers(
    df: pd.DataFrame, 
    columns: Optional[List[str]] = None,
    threshold: float = 3.0,
    method: str = 'z_score'
) -> pd.DataFrame:
    """
    Remove outliers from price data.
    
    Args:
        df: DataFrame with price data
        columns: Columns to check for outliers (default: ['open', 'high', 'low', 'close'])
        threshold: Outlier threshold
        method: Detection method ('z_score', 'iqr')
    
    Returns:
        DataFrame without outliers
        
    Raises:
        DataProcessingError: If outlier removal fails
    """
    try:
        if columns is None:
            columns = ['open', 'high', 'low', 'close']
        
        # Filter columns that actually exist in the DataFrame
        existing_columns = [col for col in columns if col in df.columns]
        if not existing_columns:
            logger.warning("No price columns found for outlier removal")
            return df.copy()
        
        logger.info(f"Removing outliers from columns: {existing_columns}")
        
        cleaned_df = df.copy()
        initial_rows = len(cleaned_df)
        
        if method == 'z_score':
            for col in existing_columns:
                z_scores = np.abs((cleaned_df[col] - cleaned_df[col].mean()) / cleaned_df[col].std())
                outlier_mask = z_scores <= threshold
                cleaned_df = cleaned_df[outlier_mask]
        
        elif method == 'iqr':
            for col in existing_columns:
                Q1 = cleaned_df[col].quantile(0.25)
                Q3 = cleaned_df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                
                outlier_mask = (cleaned_df[col] >= lower_bound) & (cleaned_df[col] <= upper_bound)
                cleaned_df = cleaned_df[outlier_mask]
        
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
        
        removed_rows = initial_rows - len(cleaned_df)
        if removed_rows > 0:
            logger.info(f"Removed {removed_rows} outlier rows ({removed_rows/initial_rows:.2%})")
        
        return cleaned_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to remove outliers: {e}",
            {'method': method, 'threshold': threshold, 'columns': columns}
        )


def calculate_derived_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate basic derived indicators from OHLCV data.
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with additional calculated columns
    """
    try:
        logger.info("Calculating derived indicators")
        
        result_df = df.copy()
        
        # Basic price indicators
        if all(col in df.columns for col in ['high', 'low']):
            result_df['hl_avg'] = (df['high'] + df['low']) / 2
        
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            result_df['ohlc_avg'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
            result_df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Price ranges
        if all(col in df.columns for col in ['high', 'low']):
            result_df['true_range'] = df['high'] - df['low']
        
        # Price changes
        if 'close' in df.columns:
            result_df['price_change'] = df['close'].diff()
            result_df['price_change_pct'] = df['close'].pct_change()
        
        # Gap detection
        if all(col in df.columns for col in ['open', 'close']):
            result_df['gap'] = df['open'] - df['close'].shift(1)
            result_df['gap_pct'] = result_df['gap'] / df['close'].shift(1)
        
        # Volume indicators (if volume exists)
        if 'volume' in df.columns:
            result_df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
            result_df['volume_ratio'] = df['volume'] / result_df['volume_sma_20']
        
        logger.info(f"Added {len(result_df.columns) - len(df.columns)} derived indicators")
        return result_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to calculate derived indicators: {e}",
            {'original_columns': list(df.columns)}
        )


def resample_ohlcv(
    df: pd.DataFrame, 
    target_timeframe: str,
    method: str = 'standard'
) -> pd.DataFrame:
    """
    Resample OHLCV data to different timeframe.
    
    Args:
        df: DataFrame with OHLCV data
        target_timeframe: Target timeframe ('5min', '15min', '1H', '1D', etc.)
        method: Resampling method ('standard', 'custom')
    
    Returns:
        Resampled DataFrame
        
    Raises:
        DataProcessingError: If resampling fails
    """
    try:
        logger.info(f"Resampling data to {target_timeframe}")
        
        if df.empty:
            return df.copy()
        
        # Define aggregation rules for OHLCV data
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }
        
        # Add volume if it exists
        if 'volume' in df.columns:
            agg_rules['volume'] = 'sum'
        
        # Filter aggregation rules to only include existing columns
        existing_agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
        
        if not existing_agg_rules:
            raise DataProcessingError("No OHLCV columns found for resampling")
        
        # Perform resampling
        resampled = df.resample(target_timeframe).agg(existing_agg_rules)
        
        # Remove rows with NaN values (incomplete periods)
        resampled.dropna(inplace=True)
        
        logger.info(f"Resampled from {len(df)} to {len(resampled)} rows")
        return resampled
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to resample data to {target_timeframe}: {e}",
            {'target_timeframe': target_timeframe, 'method': method}
        )


def normalize_prices(
    df: pd.DataFrame, 
    base_column: str = 'close',
    method: str = 'first_value'
) -> pd.DataFrame:
    """
    Normalize price data to percentage changes or relative values.
    
    Args:
        df: DataFrame with price data
        base_column: Column to use as base for normalization
        method: Normalization method ('first_value', 'percentage_change', 'z_score')
    
    Returns:
        DataFrame with normalized prices
    """
    try:
        logger.info(f"Normalizing prices using method: {method}")
        
        if base_column not in df.columns:
            raise ValueError(f"Base column '{base_column}' not found in DataFrame")
        
        result_df = df.copy()
        price_columns = ['open', 'high', 'low', 'close']
        existing_price_columns = [col for col in price_columns if col in df.columns]
        
        if method == 'first_value':
            # Normalize to first value (set first value to 100)
            base_value = df[base_column].iloc[0]
            for col in existing_price_columns:
                result_df[f'{col}_normalized'] = (df[col] / base_value) * 100
        
        elif method == 'percentage_change':
            # Convert to percentage changes
            for col in existing_price_columns:
                result_df[f'{col}_pct_change'] = df[col].pct_change() * 100
        
        elif method == 'z_score':
            # Z-score normalization
            for col in existing_price_columns:
                mean_val = df[col].mean()
                std_val = df[col].std()
                result_df[f'{col}_zscore'] = (df[col] - mean_val) / std_val
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
        
        logger.info(f"Price normalization completed using {method}")
        return result_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to normalize prices: {e}",
            {'method': method, 'base_column': base_column}
        )


def detect_market_sessions(
    df: pd.DataFrame,
    timezone: str = 'UTC'
) -> pd.DataFrame:
    """
    Detect and label market sessions in the data.
    
    Args:
        df: DataFrame with datetime index
        timezone: Timezone for session detection
    
    Returns:
        DataFrame with session labels
    """
    try:
        logger.info("Detecting market sessions")
        
        result_df = df.copy()
        
        # Convert to specified timezone if needed
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            if str(df.index.tz) != timezone:
                result_df.index = df.index.tz_convert(timezone)
        
        # Define session times (UTC)
        sessions = {
            'asian': (0, 8),      # 00:00 - 08:00 UTC
            'london': (8, 16),    # 08:00 - 16:00 UTC  
            'new_york': (13, 21), # 13:00 - 21:00 UTC
            'overlap_london_ny': (13, 16)  # London-NY overlap
        }
        
        # Extract hour from index
        hours = result_df.index.hour
        
        # Label sessions
        result_df['session'] = 'none'
        for session_name, (start_hour, end_hour) in sessions.items():
            if session_name == 'overlap_london_ny':
                continue  # Handle overlap separately
            mask = (hours >= start_hour) & (hours < end_hour)
            result_df.loc[mask, 'session'] = session_name
        
        # Mark overlaps
        overlap_mask = (hours >= 13) & (hours < 16)
        result_df.loc[overlap_mask, 'london_ny_overlap'] = True
        result_df['london_ny_overlap'] = result_df.get('london_ny_overlap', False)
        
        logger.info("Market session detection completed")
        return result_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to detect market sessions: {e}",
            {'timezone': timezone}
        )


# Вспомогательные функции

def _handle_missing_values(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Handle missing values in DataFrame."""
    if method == 'forward':
        return df.fillna(method='ffill')
    elif method == 'backward':
        return df.fillna(method='bfill')
    elif method == 'interpolate':
        return df.interpolate()
    else:
        raise ValueError(f"Unknown fill method: {method}")


def _fix_ohlc_relationships(df: pd.DataFrame) -> pd.DataFrame:
    """Fix logical inconsistencies in OHLC data."""
    result_df = df.copy()
    
    # Check if we have the required columns
    ohlc_columns = ['open', 'high', 'low', 'close']
    existing_ohlc = [col for col in ohlc_columns if col in df.columns]
    
    if len(existing_ohlc) < 3:
        return result_df
    
    # Fix high/low relationships
    if 'high' in existing_ohlc and 'low' in existing_ohlc:
        # Ensure high >= low
        mask = result_df['high'] < result_df['low']
        if mask.any():
            logger.warning(f"Fixed {mask.sum()} rows where high < low")
            # Swap values
            result_df.loc[mask, ['high', 'low']] = result_df.loc[mask, ['low', 'high']].values
    
    # Ensure open and close are within high/low range
    for price_col in ['open', 'close']:
        if price_col in existing_ohlc:
            if 'high' in existing_ohlc:
                above_high = result_df[price_col] > result_df['high']
                if above_high.any():
                    result_df.loc[above_high, price_col] = result_df.loc[above_high, 'high']
            
            if 'low' in existing_ohlc:
                below_low = result_df[price_col] < result_df['low']
                if below_low.any():
                    result_df.loc[below_low, price_col] = result_df.loc[below_low, 'low']
    
    return result_df


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add comprehensive technical features to the DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with added technical features
        
    Raises:
        DataProcessingError: If feature calculation fails
    """
    try:
        logger.info("Adding technical features")
        
        df_features = df.copy()
        
        # Price-based features
        if all(col in df_features.columns for col in ['open', 'high', 'low', 'close']):
            # Body size (candlestick body)
            df_features['body_size'] = df_features['close'] - df_features['open']
            df_features['body_size_pct'] = df_features['body_size'] / df_features['open']
            
            # Upper and lower shadows (candlestick wicks)
            df_features['upper_shadow'] = df_features['high'] - df_features[['open', 'close']].max(axis=1)
            df_features['lower_shadow'] = df_features[['open', 'close']].min(axis=1) - df_features['low']
            
            # True range (volatility measure)
            df_features['true_range'] = np.maximum(
                df_features['high'] - df_features['low'],
                np.maximum(
                    np.abs(df_features['high'] - df_features['close'].shift(1)),
                    np.abs(df_features['low'] - df_features['close'].shift(1))
                )
            )
            
            # Price changes
            df_features['price_change'] = df_features['close'].pct_change()
            df_features['price_change_abs'] = df_features['price_change'].abs()
            
            # Rolling statistics
            df_features['price_ma_20'] = df_features['close'].rolling(window=20).mean()
            df_features['price_ma_50'] = df_features['close'].rolling(window=50).mean()
            df_features['price_std_20'] = df_features['close'].rolling(window=20).std()
            
            # Price position within range
            df_features['price_position'] = (df_features['close'] - df_features['low']) / (df_features['high'] - df_features['low'])
            
            # Momentum indicators
            df_features['roc_5'] = df_features['close'].pct_change(periods=5)  # 5-period Rate of Change
            df_features['roc_10'] = df_features['close'].pct_change(periods=10)  # 10-period Rate of Change
        
        # Volume-based features
        if 'volume' in df_features.columns:
            df_features['volume_ma_20'] = df_features['volume'].rolling(window=20).mean()
            df_features['volume_ratio'] = df_features['volume'] / df_features['volume_ma_20']
            df_features['volume_std_20'] = df_features['volume'].rolling(window=20).std()
            
            # Volume-price relationship
            if 'close' in df_features.columns:
                df_features['volume_price_trend'] = df_features['volume'] * df_features['price_change']
        
        logger.info(f"Added {len(df_features.columns) - len(df.columns)} technical features")
        return df_features
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to add technical features: {e}",
            {'original_columns': list(df.columns)}
        )


def create_lagged_features(
    df: pd.DataFrame, 
    columns: List[str],
    lags: List[int]
) -> pd.DataFrame:
    """
    Create lagged features for time series analysis.
    
    Args:
        df: DataFrame with time series data
        columns: Columns to create lags for
        lags: List of lag periods
    
    Returns:
        DataFrame with lagged features
        
    Raises:
        DataProcessingError: If lagged feature creation fails
    """
    try:
        logger.info(f"Creating lagged features for {len(columns)} columns with lags {lags}")
        
        df_lagged = df.copy()
        
        # Validate columns exist
        missing_columns = [col for col in columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Columns not found in DataFrame: {missing_columns}")
        
        created_features = 0
        for col in columns:
            for lag in lags:
                if lag < 0:
                    raise ValueError(f"Lag must be non-negative, got: {lag}")
                
                lag_col_name = f"{col}_lag_{lag}"
                df_lagged[lag_col_name] = df_lagged[col].shift(lag)
                created_features += 1
        
        logger.info(f"Created {created_features} lagged features")
        return df_lagged
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to create lagged features: {e}",
            {'columns': columns, 'lags': lags}
        )


def prepare_data_for_analysis(
    df: pd.DataFrame,
    target_column: str = 'close',
    feature_columns: Optional[List[str]] = None,
    add_tech_features: bool = True,
    normalize: bool = True,
    create_lags: bool = False,
    lag_periods: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Prepare data for analysis by adding features and cleaning.
    
    Args:
        df: DataFrame with OHLCV data
        target_column: Name of target column
        feature_columns: Specific columns to use as features (if None, use all numeric)
        add_tech_features: Whether to add technical features
        normalize: Whether to normalize features
        create_lags: Whether to create lagged features
        lag_periods: Lag periods to create (default: [1, 2, 3, 5])
    
    Returns:
        Prepared DataFrame for analysis
        
    Raises:
        DataProcessingError: If data preparation fails
    """
    try:
        logger.info("Preparing data for analysis")
        
        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in DataFrame")
        
        # Start with cleaned data
        prepared_df = clean_ohlcv_data(df, remove_outliers=True)
        
        # Add technical features if requested
        if add_tech_features:
            prepared_df = add_technical_features(prepared_df)
        
        # Create lagged features if requested
        if create_lags:
            if lag_periods is None:
                lag_periods = [1, 2, 3, 5]
            
            # Use feature columns or all numeric columns except target for lags
            if feature_columns is None:
                lag_columns = [col for col in prepared_df.select_dtypes(include=[np.number]).columns 
                              if col != target_column]
            else:
                lag_columns = [col for col in feature_columns if col in prepared_df.columns]
            
            if lag_columns:
                prepared_df = create_lagged_features(prepared_df, lag_columns, lag_periods)
        
        # Select feature columns
        if feature_columns is None:
            feature_columns = [col for col in prepared_df.select_dtypes(include=[np.number]).columns 
                             if col != target_column]
        else:
            # Filter to existing columns
            feature_columns = [col for col in feature_columns if col in prepared_df.columns]
        
        # Normalize features if requested
        if normalize and feature_columns:
            prepared_df = normalize_prices(
                prepared_df, 
                base_column=target_column,
                method='z_score'
            )
        
        # Remove rows with NaN values (from lagging, etc.)
        initial_rows = len(prepared_df)
        prepared_df.dropna(inplace=True)
        final_rows = len(prepared_df)
        
        if final_rows < initial_rows:
            logger.info(f"Removed {initial_rows - final_rows} rows with missing values")
        
        logger.info(f"Data preparation completed. Final shape: {prepared_df.shape}")
        return prepared_df
        
    except Exception as e:
        raise DataProcessingError(
            f"Failed to prepare data for analysis: {e}",
            {'target_column': target_column, 'feature_columns': feature_columns}
        )


# Экспорт функций
__all__ = [
    'clean_ohlcv_data',
    'remove_price_outliers',
    'calculate_derived_indicators',
    'resample_ohlcv',
    'normalize_prices',
    'detect_market_sessions',
    'add_technical_features',
    'create_lagged_features',
    'prepare_data_for_analysis'
]
