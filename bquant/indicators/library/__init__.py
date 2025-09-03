"""
BQuant External Library Indicators Module

This module provides functionality to load and integrate external technical indicator libraries.
Contains loaders for TA-Lib, pandas-ta, and other external libraries.
"""

# External library loaders (moved from loaders.py)
from .pandas_ta import PandasTALoader
from .talib import TALibLoader

# Library management
from .manager import LibraryManager, load_pandas_ta, load_talib, load_all_indicators, create_library_indicator

__all__ = [
    # External library loaders
    "PandasTALoader",
    "TALibLoader", 
    
    # Library management
    "LibraryManager",
    "load_pandas_ta",
    "load_talib",
    "load_all_indicators",
    "create_library_indicator",
]

# Auto-load external libraries
try:
    # Will be implemented after migration
    pass
except Exception:
    pass  # Ignore errors during auto-loading
