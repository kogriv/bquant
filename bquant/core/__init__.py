"""
BQuant Core Module

Core functionality including configuration, utilities, and base classes.
"""

from .config import (
    get_data_path,
    get_indicator_params,
    validate_timeframe,
    PROJECT_ROOT,
    DATA_DIR,
    DEFAULT_INDICATORS,
    TIMEFRAME_MAPPING
)

from .utils import (
    setup_project_logging,
    calculate_returns,
    normalize_data,
    save_results,
    validate_ohlcv_columns,
    create_timestamp,
    memory_usage_info,
    ensure_directory
)

from .exceptions import (
    BQuantError,
    DataError,
    DataValidationError,
    DataLoadingError,
    DataProcessingError,
    ConfigurationError,
    InvalidTimeframeError,
    InvalidIndicatorParametersError,
    AnalysisError,
    IndicatorCalculationError,
    ZoneAnalysisError,
    StatisticalAnalysisError,
    VisualizationError,
    MLError,
    FileOperationError
)

from .logging_config import (
    setup_logging,
    get_logger,
    log_function_call,
    log_performance,
    LoggingContext
)

from .numpy_fix import (
    apply_numpy_fixes,
    check_numpy_compatibility,
    ensure_numpy_compatibility,
    NaN,
    nan
)

from .nb import (
    NotebookSimulator
)

__all__ = [
    # Config
    "get_data_path",
    "get_indicator_params",
    "validate_timeframe", 
    "PROJECT_ROOT",
    "DATA_DIR",
    "DEFAULT_INDICATORS",
    "TIMEFRAME_MAPPING",
    
    # Utils
    "setup_project_logging",
    "calculate_returns",
    "normalize_data",
    "save_results",
    "validate_ohlcv_columns",
    "create_timestamp",
    "memory_usage_info",
    "ensure_directory",
    
    # Exceptions
    "BQuantError",
    "DataError",
    "DataValidationError",
    "DataLoadingError",
    "DataProcessingError",
    "ConfigurationError",
    "InvalidTimeframeError",
    "InvalidIndicatorParametersError",
    "AnalysisError",
    "IndicatorCalculationError",
    "ZoneAnalysisError",
    "StatisticalAnalysisError",
    "VisualizationError",
    "MLError",
    "FileOperationError",
    
    # Logging
    "setup_logging",
    "get_logger",
    "log_function_call",
    "log_performance",
    "LoggingContext",
    
    # Numpy fix
    "apply_numpy_fixes",
    "check_numpy_compatibility",
    "ensure_numpy_compatibility",
    "NaN",
    "nan",
    
    # Notebook-style scripts
    "NotebookSimulator"
]
