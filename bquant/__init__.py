"""
BQuant - Quantitative Research Toolkit for Financial Markets

A comprehensive toolkit for quantitative analysis of financial data,
starting with MACD analysis and expandable to all aspects of market research.
"""

__version__ = "0.0.1"
__author__ = "kogriv"
__email__ = "kogriv@gmail.com"

# Core exports
from bquant.core.config import (
    get_data_path,
    get_indicator_params,
    validate_timeframe,
    PROJECT_ROOT,
    DATA_DIR
)

# Version info
__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "get_data_path",
    "get_indicator_params", 
    "validate_timeframe",
    "PROJECT_ROOT",
    "DATA_DIR"
]
