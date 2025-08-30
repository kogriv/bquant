"""
Data loading functions for BQuant

This module provides functions to load and prepare financial data for analysis.
Перенесено и адаптировано из scripts/data/data_loader.py.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import warnings
import chardet

from ..core.config import (
    DATA_DIR, get_data_path, validate_timeframe,
    DATA_VALIDATION, SUPPORTED_TIMEFRAMES, TIMEFRAME_MAPPING
)
from ..core.exceptions import (
    DataError, DataLoadingError, DataValidationError,
    create_data_validation_error
)
from ..core.logging_config import get_logger

# Получаем логгер для модуля
logger = get_logger(__name__)


def _detect_file_encoding(file_path: Path) -> str:
    """
    Detect file encoding using chardet library.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected encoding string
        
    Raises:
        DataLoadingError: If encoding cannot be detected
    """
    try:
        # Read a sample of the file to detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
        
        if not raw_data:
            raise DataLoadingError(f"File is empty: {file_path}")
        
        # Detect encoding
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        
        if not encoding or confidence < 0.7:
            # Fallback to common encodings
            common_encodings = ['utf-8', 'windows-1252', 'cp1252', 'iso-8859-1', 'utf-16']
            for enc in common_encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        f.read(1000)  # Test read
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
            
            if not encoding:
                raise DataLoadingError(f"Could not detect encoding for file: {file_path}")
        
        return encoding
        
    except Exception as e:
        raise DataLoadingError(f"Error detecting file encoding: {e}")


def _try_read_csv_with_encoding(file_path: Path, encoding: str, logger_with_context) -> Optional[pd.DataFrame]:
    """
    Try to read CSV file with specific encoding and date parsing.
    
    Args:
        file_path: Path to CSV file
        encoding: File encoding to use
        logger_with_context: Logger with context
        
    Returns:
        DataFrame if successful, None otherwise
    """
    date_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y.%m.%d %H:%M:%S', 
        '%Y-%m-%d'
    ]
    
    # Попытка 1: Стандартный формат с заголовками
    for i, date_format in enumerate(date_formats):
        try:
            if i == 0:  # Первая попытка с автоопределением индекса
                df = pd.read_csv(file_path, index_col=0, parse_dates=True, date_format=date_format, encoding=encoding)
            else:  # Остальные попытки
                df = pd.read_csv(file_path, parse_dates=['time'], date_format=date_format, encoding=encoding)
                if 'time' in df.columns:
                    df.set_index('time', inplace=True)
            
            # Проверяем, что это не MetaTrader формат без заголовков
            if not _is_mt_format_without_headers(df):
                return df
        except (ValueError, TypeError, UnicodeDecodeError):
            continue
    
    # Попытка 2: MetaTrader формат без заголовков
    try:
        # Читаем первые несколько строк для определения структуры
        sample_df = pd.read_csv(file_path, header=None, nrows=5, encoding=encoding)
        
        if _is_mt_format_without_headers(sample_df):
            logger_with_context.info("Detected MetaTrader format without headers")
            
            # Определяем количество колонок и маппинг
            num_cols = len(sample_df.columns)
            if num_cols >= 6:
                # Стандартный MT формат: time, open, high, low, close, volume
                column_names = ['time', 'open', 'high', 'low', 'close', 'volume']
                if num_cols > 6:
                    # Дополнительные колонки (spread, etc.)
                    column_names.extend([f'col_{i}' for i in range(6, num_cols)])
                
                # Читаем весь файл с правильными именами колонок
                df = pd.read_csv(file_path, header=None, names=column_names, encoding=encoding)
                
                # Устанавливаем время как индекс
                df.set_index('time', inplace=True)
                
                # Парсим время
                if df.index.dtype == 'object':
                    df.index = pd.to_datetime(df.index)
                
                return df
    except Exception:
        pass
    
    # Попытка 3: Автоопределение без парсинга дат
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True, encoding=encoding)
        if df.index.dtype == 'object':
            df.index = pd.to_datetime(df.index)
        return df
    except (ValueError, TypeError, UnicodeDecodeError):
        try:
            df = pd.read_csv(file_path, parse_dates=['time'], encoding=encoding)
            if 'time' in df.columns:
                df.set_index('time', inplace=True)
                if df.index.dtype == 'object':
                    df.index = pd.to_datetime(df.index)
            return df
        except (ValueError, TypeError, UnicodeDecodeError):
            pass
    
    return None


def _is_mt_format_without_headers(df: pd.DataFrame) -> bool:
    """
    Detect if DataFrame is in MetaTrader format without headers.
    
    Args:
        df: DataFrame to check
        
    Returns:
        True if it's MT format without headers
    """
    if df.empty or len(df.columns) < 6:
        return False
    
    # Проверяем первые несколько колонок на числовые значения
    # MT формат: время (строка), open, high, low, close, volume (числа)
    try:
        # Первая колонка должна быть строкой (время)
        first_col = df.iloc[:, 0]
        if not all(isinstance(str(val), str) for val in first_col.dropna()):
            return False
        
        # Колонки 1-5 должны быть числовыми (open, high, low, close, volume)
        numeric_cols = df.iloc[:, 1:6]
        for col in numeric_cols.columns:
            if not pd.to_numeric(numeric_cols[col], errors='coerce').notna().all():
                return False
        
        return True
    except Exception:
        return False


def load_ohlcv_data(
    file_path: Union[str, Path], 
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    validate_data: bool = True
) -> pd.DataFrame:
    """
    Load OHLCV data from CSV file with automatic validation.
    
    Args:
        file_path: Path to CSV file
        symbol: Symbol name (optional, for logging)
        timeframe: Timeframe (optional, for logging and validation)
        validate_data: Whether to validate loaded data
    
    Returns:
        DataFrame with OHLCV data
        
    Raises:
        DataLoadingError: If file cannot be loaded
        DataValidationError: If data validation fails
    """
    try:
        file_path = Path(file_path)
        context = {'symbol': symbol, 'timeframe': timeframe} if symbol and timeframe else None
        logger_with_context = get_logger(__name__, context)
        
        logger_with_context.info(f"Loading data from: {file_path}")
        
        # Validate timeframe if provided
        if timeframe:
            try:
                timeframe = validate_timeframe(timeframe)
            except ValueError as e:
                logger_with_context.warning(f"Timeframe validation warning: {e}")
        
        # Check if file exists
        if not file_path.exists():
            raise DataLoadingError(
                f"Data file not found: {file_path}",
                {'file_path': str(file_path), 'symbol': symbol, 'timeframe': timeframe}
            )
        
        # Try to read CSV file with encoding detection
        try:
            # Detect file encoding
            encoding = _detect_file_encoding(file_path)
            logger_with_context.info(f"Detected encoding: {encoding}")
            
            # Try to read with detected encoding
            df = _try_read_csv_with_encoding(file_path, encoding, logger_with_context)
            
            # If failed, try common encodings as fallback
            if df is None:
                common_encodings = ['utf-8', 'windows-1252', 'cp1252', 'iso-8859-1', 'utf-16']
                for fallback_encoding in common_encodings:
                    if fallback_encoding != encoding:
                        logger_with_context.info(f"Trying fallback encoding: {fallback_encoding}")
                        df = _try_read_csv_with_encoding(file_path, fallback_encoding, logger_with_context)
                        if df is not None:
                            break
            
            # If still failed, try without date parsing
            if df is None:
                try:
                    df = pd.read_csv(file_path, index_col=0, encoding=encoding)
                    logger_with_context.warning("Could not parse dates automatically")
                except Exception:
                    # Last resort: try without index_col
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        logger_with_context.warning("Could not set index automatically")
                    except Exception as e:
                        raise DataLoadingError(
                            f"Failed to read CSV file with any encoding: {e}",
                            {'file_path': str(file_path), 'error': str(e)}
                        )
                
        except Exception as e:
            raise DataLoadingError(
                f"Failed to read CSV file: {e}",
                {'file_path': str(file_path), 'error': str(e)}
            )
        
        # Validate column names (make lowercase and consistent)
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column name variations
        column_mapping = {
            'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
            'vol': 'volume', 'adj close': 'adj_close', 'adj_close': 'adj_close'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Validate data structure if requested
        if validate_data:
            _validate_ohlcv_structure(df, symbol, timeframe)
        
        # Remove any rows with all NaN values
        df.dropna(how='all', inplace=True)
        
        # Sort by index (time)
        if not df.index.is_monotonic_increasing:
            df.sort_index(inplace=True)
        
        logger_with_context.info(f"Successfully loaded {len(df)} rows of data")
        return df
        
    except (DataLoadingError, DataValidationError):
        raise
    except Exception as e:
        raise DataLoadingError(
            f"Unexpected error loading data from {file_path}: {e}",
            {'file_path': str(file_path), 'error': str(e)}
        )


def load_symbol_data(
    symbol: str, 
    timeframe: str, 
    data_source: str = 'tradingview', 
    quote_provider: str = 'default'
) -> pd.DataFrame:
    """
    Load data for any symbol and timeframe using config.
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSD', 'EURUSD')
        timeframe: Timeframe (e.g., '1h', '1d', '5m')
        data_source: Data source ('tradingview', 'metatrader', 'generic', 'custom')
        quote_provider: Quote provider (e.g., 'oanda', 'forexcom', 'icmarkets')
    
    Returns:
        DataFrame with OHLCV data
        
    Raises:
        DataLoadingError: If data cannot be loaded
        DataValidationError: If data validation fails
    """
    # Validate timeframe
    timeframe = validate_timeframe(timeframe)
    
    # Get mapped timeframe for the specific data source
    if data_source in TIMEFRAME_MAPPING:
        mapped_timeframe = TIMEFRAME_MAPPING[data_source].get(timeframe, timeframe)
    else:
        mapped_timeframe = timeframe
    
    # Get file path using config with mapped timeframe
    file_path = get_data_path(symbol, mapped_timeframe, data_source, quote_provider)
    
    # Load data
    return load_ohlcv_data(file_path, symbol, timeframe)


def load_xauusd_data(timeframe: str = '1h') -> pd.DataFrame:
    """
    Load XAUUSD data for specified timeframe (convenience function).
    
    Args:
        timeframe: Timeframe (e.g., '1h', '1d', '5m')
    
    Returns:
        DataFrame with XAUUSD data
    """
    return load_symbol_data('XAUUSD', timeframe)


def load_all_data_files(data_dir: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    """
    Load all available data files from data directory.
    
    Args:
        data_dir: Directory to search for data files (default: DATA_DIR)
    
    Returns:
        Dictionary with symbol_timeframe as key and DataFrame as value
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    all_data = {}
    
    if not data_dir.exists():
        logger.warning(f"Data directory not found: {data_dir}")
        return all_data
    
    # Поиск CSV файлов в директории
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return all_data
    
    logger.info(f"Found {len(csv_files)} CSV files in {data_dir}")
    
    for file_path in csv_files:
        try:
            # Parse filename to extract symbol and timeframe
            filename = file_path.stem
            
            # Try to detect data source and parse accordingly
            symbol, timeframe, quote_provider = _parse_filename(filename)
            
            if symbol is None or timeframe == 'unknown':
                logger.warning(f"Could not parse filename: {filename}")
                continue
            
            # Try to validate timeframe if it's supported
            try:
                if timeframe in SUPPORTED_TIMEFRAMES:
                    timeframe = validate_timeframe(timeframe)
            except ValueError:
                logger.warning(f"Unsupported timeframe '{timeframe}' for {symbol}, loading anyway")
            
            df = load_ohlcv_data(file_path, symbol, timeframe)
            key = f"{symbol}_{timeframe}"
            all_data[key] = df
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
    
    logger.info(f"Successfully loaded {len(all_data)} data files")
    return all_data


def get_data_info(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get information about loaded data.
    
    Args:
        df: DataFrame with financial data
    
    Returns:
        Dictionary with data information
    """
    if df.empty:
        return {'rows': 0, 'columns': [], 'date_range': None, 'memory_usage_mb': 0}
    
    info = {
        'rows': len(df),
        'columns': list(df.columns),
        'date_range': {
            'start': df.index.min() if not df.index.empty else None,
            'end': df.index.max() if not df.index.empty else None
        },
        'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024**2,
        'missing_values': df.isnull().sum().to_dict(),
        'data_types': df.dtypes.to_dict()
    }
    
    return info


def get_available_symbols(data_dir: Optional[Path] = None) -> List[str]:
    """
    Get list of available symbols in data directory.
    
    Args:
        data_dir: Directory to search (default: DATA_DIR)
    
    Returns:
        List of available symbols
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    symbols = set()
    
    if not data_dir.exists():
        return []
    
    for file_path in data_dir.glob("*.csv"):
        symbol, _, _ = _parse_filename(file_path.stem)
        if symbol and symbol != 'unknown':
            symbols.add(symbol)
    
    return sorted(list(symbols))


def get_available_timeframes(symbol: str, data_dir: Optional[Path] = None) -> List[str]:
    """
    Get list of available timeframes for a symbol.
    
    Args:
        symbol: Trading symbol
        data_dir: Directory to search (default: DATA_DIR)
    
    Returns:
        List of available timeframes for the symbol
    """
    if data_dir is None:
        data_dir = DATA_DIR
    
    timeframes = set()
    
    if not data_dir.exists():
        return []
    
    for file_path in data_dir.glob("*.csv"):
        parsed_symbol, timeframe, _ = _parse_filename(file_path.stem)
        if parsed_symbol == symbol and timeframe != 'unknown':
            timeframes.add(timeframe)
    
    return sorted(list(timeframes))


# Вспомогательные функции

def _validate_ohlcv_structure(df: pd.DataFrame, symbol: Optional[str] = None, timeframe: Optional[str] = None):
    """
    Validate OHLCV data structure.
    
    Args:
        df: DataFrame to validate
        symbol: Symbol name for error context
        timeframe: Timeframe for error context
        
    Raises:
        DataValidationError: If validation fails
    """
    # Check required columns
    required_columns = DATA_VALIDATION['required_columns']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise create_data_validation_error(
            f"Missing required columns: {missing_columns}",
            expected_type="OHLCV columns",
            actual_type=list(df.columns)
        )
    
    # Check minimum number of records
    min_records = DATA_VALIDATION.get('min_records', 1)
    if len(df) < min_records:
        raise create_data_validation_error(
            f"Insufficient data: {len(df)} rows, minimum required: {min_records}",
            expected_shape=f"(>={min_records}, {len(df.columns)})",
            actual_shape=df.shape
        )
    
    # Check for excessive missing values
    max_missing_ratio = DATA_VALIDATION.get('max_missing_ratio', 0.5)
    for col in required_columns:
        missing_ratio = df[col].isnull().sum() / len(df)
        if missing_ratio > max_missing_ratio:
            raise create_data_validation_error(
                f"Too many missing values in column '{col}': {missing_ratio:.2%} > {max_missing_ratio:.2%}",
                column=col
            )
    
    # Check for logical consistency (high >= low, etc.)
    if 'high' in df.columns and 'low' in df.columns:
        invalid_hl = df['high'] < df['low']
        if invalid_hl.any():
            logger.warning(f"Found {invalid_hl.sum()} rows where high < low")
    
    # Check for logical price ranges
    price_columns = ['open', 'high', 'low', 'close']
    for col in price_columns:
        if col in df.columns:
            if (df[col] <= 0).any():
                raise create_data_validation_error(
                    f"Non-positive prices found in column '{col}'",
                    column=col
                )


def _parse_filename(filename: str) -> tuple:
    """
    Parse filename to extract symbol, timeframe, and quote provider.
    
    Args:
        filename: Filename without extension
    
    Returns:
        Tuple of (symbol, timeframe, quote_provider)
    """
    # Try TradingView format first (PROVIDER_SYMBOL, TIMEFRAME)
    quote_providers = ['OANDA', 'FOREXCOM', 'ICMARKETS']
    
    for provider in quote_providers:
        if filename.startswith(f'{provider}_'):
            symbol_part = filename[len(provider) + 1:]  # Remove "PROVIDER_" prefix
            if ', ' in symbol_part:
                symbol, timeframe = symbol_part.split(', ', 1)
                return symbol, timeframe, provider.lower()
    
    # Try generic format (SYMBOL_TIMEFRAME)
    if '_' in filename:
        parts = filename.split('_')
        if len(parts) >= 2:
            symbol = parts[0]
            timeframe = '_'.join(parts[1:])
            return symbol, timeframe, 'default'
    
    # Try MetaTrader format (SYMBOLTIMEFRAME)
    timeframe_patterns = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'Daily', 'Weekly']
    for pattern in timeframe_patterns:
        if filename.endswith(pattern):
            symbol = filename[:-len(pattern)]
            return symbol, pattern, 'default'
    
    return filename, 'unknown', 'unknown'


# Экспорт для удобства
__all__ = [
    'load_ohlcv_data',
    'load_symbol_data',
    'load_xauusd_data',
    'load_all_data_files',
    'get_data_info',
    'get_available_symbols',
    'get_available_timeframes'
]
