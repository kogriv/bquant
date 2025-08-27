"""
BQuant Data Module

Data loading, processing, and validation functionality.
"""

from .loader import (
    load_ohlcv_data,
    load_symbol_data,
    load_xauusd_data,
    load_all_data_files,
    get_data_info,
    get_available_symbols,
    get_available_timeframes
)

from .processor import (
    clean_ohlcv_data,
    remove_price_outliers,
    calculate_derived_indicators,
    resample_ohlcv,
    normalize_prices,
    detect_market_sessions,
    add_technical_features,
    create_lagged_features,
    prepare_data_for_analysis
)

from .validator import (
    validate_ohlcv_data,
    validate_data_completeness,
    validate_price_consistency,
    validate_time_series_continuity,
    validate_statistical_properties
)

from .schemas import (
    OHLCVRecord,
    DataSourceConfig,
    ValidationResult,
    DataSchema,
    OHLCVSchema,
    IndicatorSchema,
    get_schema,
    validate_with_schema
)

__all__ = [
    # Loader functions
    "load_ohlcv_data",
    "load_symbol_data",
    "load_xauusd_data",
    "load_all_data_files",
    "get_data_info",
    "get_available_symbols",
    "get_available_timeframes",
    
    # Processor functions
    "clean_ohlcv_data",
    "remove_price_outliers",
    "calculate_derived_indicators",
    "resample_ohlcv",
    "normalize_prices",
    "detect_market_sessions",
    "add_technical_features",
    "create_lagged_features",
    "prepare_data_for_analysis",
    
    # Validator functions
    "validate_ohlcv_data",
    "validate_data_completeness",
    "validate_price_consistency",
    "validate_time_series_continuity",
    "validate_statistical_properties",
    
    # Schema classes and functions
    "OHLCVRecord",
    "DataSourceConfig",
    "ValidationResult",
    "DataSchema",
    "OHLCVSchema",
    "IndicatorSchema",
    "get_schema",
    "validate_with_schema"
]
