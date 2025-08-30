"""
Configuration settings for the BQuant Project.

Universal configuration supporting multiple instruments, indicators, and analysis methods.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
NOTEBOOKS_DIR = PROJECT_ROOT / "research" / "notebooks"
ALLDATA_DIR = DATA_DIR / "alldata"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"

# Создаем директории если их нет
for directory in [PROCESSED_DATA_DIR, RESULTS_DIR, PROJECT_ROOT / "logs"]:
    directory.mkdir(exist_ok=True, parents=True)

# ============================================================================
# UNIVERSAL DATA CONFIGURATION
# ============================================================================

# ============================================================================
# TIMEFRAME MAPPING CONFIGURATION
# ============================================================================

# Маппинг таймфреймов для разных поставщиков данных
TIMEFRAME_MAPPING = {
    'tradingview': {
        # Внутричасовые таймфреймы (минуты)
        '1m': '1', '2m': '2', '3m': '3', '4m': '4', '5m': '5', '6m': '6', '10m': '10',
        '12m': '12', '15m': '15', '20m': '20', '30m': '30', '45m': '45',
        # Часовые таймфреймы
        '1h': '60', '2h': '120', '3h': '180', '4h': '240', '6h': '360', '8h': '480', '12h': '720',
        # Дневные и выше
        '1d': '1D', '1D': '1D', '1w': '1W', '1W': '1W', '1M': '1M', '3M': '3M', '6M': '6M', '12M': '12M'
    },
    'metatrader': {
        # Внутричасовые таймфреймы (минуты)
        '1m': 'M1', '2m': 'M2', '3m': 'M3', '4m': 'M4', '5m': 'M5', '6m': 'M6', '10m': 'M10',
        '12m': 'M12', '15m': 'M15', '20m': 'M20', '30m': 'M30', '45m': 'M45',
        # Часовые таймфреймы
        '1h': 'H1', '2h': 'H2', '3h': 'H3', '4h': 'H4', '6h': 'H6', '8h': 'H8', '12h': 'H12',
        # Дневные и выше
        '1d': 'Daily', '1D': 'Daily', '1w': 'Weekly', '1W': 'Weekly', '1M': 'Monthly', '3M': 'Monthly', '6M': 'Monthly', '12M': 'Monthly'
    }
}

# Универсальные паттерны файлов для разных поставщиков
DATA_FILE_PATTERNS = {
    'tradingview': {
        'oanda': "OANDA_{symbol}, {timeframe}.csv",
        'forexcom': "FOREXCOM_{symbol}, {timeframe}.csv",
        'icmarkets': "ICMARKETS_{symbol}, {timeframe}.csv",
        'default': "OANDA_{symbol}, {timeframe}.csv"  # По умолчанию OANDA
    },
    'metatrader': {
        'default': "{symbol}{timeframe}.csv"
    },
    'generic': {
        'default': "{symbol}_{timeframe}.csv"
    },
    'custom': {
        'default': "{symbol}_{timeframe}_{source}.csv"
    }
}

# Поддерживаемые таймфреймы (универсальные)
SUPPORTED_TIMEFRAMES = {
    # Внутричасовые таймфреймы (минуты)
    '1m': '1 minute', '2m': '2 minutes', '3m': '3 minutes', '4m': '4 minutes', 
    '5m': '5 minutes', '6m': '6 minutes', '10m': '10 minutes', '12m': '12 minutes',
    '15m': '15 minutes', '20m': '20 minutes', '30m': '30 minutes', '45m': '45 minutes',
    # Часовые таймфреймы
    '1h': '1 hour', '2h': '2 hours', '3h': '3 hours', '4h': '4 hours', 
    '6h': '6 hours', '8h': '8 hours', '12h': '12 hours',
    # Дневные и выше
    '1d': '1 day', '1D': '1 day', '1w': '1 week', '1W': '1 week', 
    '1M': '1 month', '3M': '3 months', '6M': '6 months', '12M': '12 months'
}

# Настройки валидации данных
DATA_VALIDATION = {
    'required_columns': ['open', 'high', 'low', 'close'],
    'optional_columns': ['volume'],
    'min_records': 100,
    'max_missing_ratio': 0.1,
    'outlier_threshold': 3.0
}

# Настройки кэширования
CACHE_CONFIG = {
    'enable_memory_cache': True,
    'enable_disk_cache': True,
    'memory_size': 100,  # Количество записей в памяти
    'default_ttl': 3600,  # Время жизни по умолчанию (секунды)
    'cache_dir': None,  # None = используется ~/.cache/bquant
    'auto_cleanup': True,  # Автоматическая очистка истекших записей
    'cleanup_interval': 300  # Интервал очистки в секундах
}

# ============================================================================
# UNIVERSAL INDICATOR CONFIGURATION
# ============================================================================

# Универсальные параметры индикаторов
DEFAULT_INDICATORS = {
    'macd': {
        'fast': 12,
        'slow': 26,
        'signal': 9
    },
    'rsi': {
        'length': 14
    },
    'bollinger_bands': {
        'length': 20,
        'std': 2
    },
    'atr': {
        'length': 14
    },
    'sma': {
        'length': 20
    },
    'ema': {
        'length': 20
    },
    'stochastic': {
        'k_length': 14,
        'd_length': 3
    },
    'williams_r': {
        'length': 14
    }
}

# ============================================================================
# UNIVERSAL ANALYSIS CONFIGURATION
# ============================================================================

# Универсальные параметры анализа
ANALYSIS_CONFIG = {
    'zone_analysis': {
        'min_duration': 2,
        'min_amplitude': 0.001,
        'normalization_method': 'atr',  # 'atr', 'price', 'none'
        'detection_method': 'sign_change'  # 'sign_change', 'threshold', 'custom'
    },
    'pattern_analysis': {
        'min_pattern_length': 3,
        'max_pattern_length': 50,
        'similarity_threshold': 0.8
    },
    'statistical_analysis': {
        'confidence_level': 0.95,
        'significance_level': 0.05,
        'bootstrap_samples': 1000,
        'random_state': 42
    }
}

# ============================================================================
# MACHINE LEARNING CONFIGURATION
# ============================================================================

ML_CONFIG = {
    'random_state': 42,
    'test_size': 0.3,
    'validation_size': 0.2,
    'cross_validation_folds': 5,
    'feature_selection_method': 'mutual_info',
    'hyperparameter_tuning': True
}

# ============================================================================
# VISUALIZATION CONFIGURATION
# ============================================================================

VISUALIZATION = {
    'figure_size': (12, 8),
    'dpi': 100,
    'style': 'seaborn-v0_8',
    'color_palette': 'viridis',
    'save_format': 'png',
    'save_dpi': 300
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'level': "INFO",
    'format': "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    'file_logging': True,
    'log_file': PROJECT_ROOT / "logs" / "bquant.log"
}

# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

EXPERIMENT_CONFIG = {
    'results_dir': RESULTS_DIR,
    'save_intermediate': True,
    'experiment_naming': 'timestamp',  # 'timestamp', 'custom', 'auto'
    'version_control': True
}

# ============================================================================
# CONFIGURATION MANAGEMENT FUNCTIONS
# ============================================================================

def get_data_path(symbol: str, timeframe: str, data_source: str = 'tradingview', quote_provider: str = 'default') -> Path:
    """
    Generate data file path based on symbol and timeframe for different data providers.
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSD', 'EURUSD')
        timeframe: Timeframe (e.g., '1h', '1d', '5m')
        data_source: Data source ('tradingview', 'metatrader', 'generic', 'custom')
        quote_provider: Quote provider for the data source (e.g., 'oanda', 'forexcom', 'icmarkets')
    
    Returns:
        Path to data file
    """
    # Validate timeframe first
    timeframe = validate_timeframe(timeframe)
    
    # Get mapped timeframe for the specific data source
    if data_source in TIMEFRAME_MAPPING:
        mapped_timeframe = TIMEFRAME_MAPPING[data_source].get(timeframe, timeframe)
    else:
        mapped_timeframe = timeframe
    
    # Get file pattern for the data source and quote provider
    source_patterns = DATA_FILE_PATTERNS.get(data_source, DATA_FILE_PATTERNS['generic'])
    
    if isinstance(source_patterns, dict):
        # New format with quote providers
        pattern = source_patterns.get(quote_provider, source_patterns.get('default', source_patterns))
    else:
        # Legacy format (backward compatibility)
        pattern = source_patterns
    
    # Generate filename
    filename = pattern.format(symbol=symbol, timeframe=mapped_timeframe)
    return DATA_DIR / filename

def get_indicator_params(indicator: str, **overrides) -> Dict[str, Any]:
    """
    Get indicator parameters with optional overrides.
    
    Args:
        indicator: Indicator name ('macd', 'rsi', etc.)
        **overrides: Parameter overrides
    
    Returns:
        Dictionary with indicator parameters
    """
    params = DEFAULT_INDICATORS.get(indicator, {}).copy()
    params.update(overrides)
    return params

def get_analysis_params(analysis_type: str, **overrides) -> Dict[str, Any]:
    """
    Get analysis parameters with optional overrides.
    
    Args:
        analysis_type: Analysis type ('zone_analysis', 'pattern_analysis', etc.)
        **overrides: Parameter overrides
    
    Returns:
        Dictionary with analysis parameters
    """
    params = ANALYSIS_CONFIG.get(analysis_type, {}).copy()
    params.update(overrides)
    return params

def validate_timeframe(timeframe: str) -> str:
    """
    Validate and normalize timeframe.
    
    Args:
        timeframe: Timeframe string
    
    Returns:
        Validated timeframe
    
    Raises:
        ValueError: If timeframe is not supported
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(SUPPORTED_TIMEFRAMES.keys())}")
    return timeframe

def get_results_path(experiment_name: str, file_type: str = 'csv') -> Path:
    """
    Generate results file path.
    
    Args:
        experiment_name: Name of the experiment
        file_type: File extension
    
    Returns:
        Path to results file
    """
    filename = f"{experiment_name}.{file_type}"
    return RESULTS_DIR / filename


def get_cache_config() -> Dict[str, Any]:
    """
    Получить конфигурацию кэширования.
    
    Returns:
        Словарь с настройками кэширования
    """
    return CACHE_CONFIG.copy()


# ============================================================================
# DIRECTORY MANAGEMENT FUNCTIONS
# ============================================================================

# Global variables для runtime изменения путей
_runtime_data_dir: Optional[Path] = None
_runtime_results_dir: Optional[Path] = None
_runtime_notebooks_dir: Optional[Path] = None
_runtime_processed_data_dir: Optional[Path] = None


def get_data_dir() -> Path:
    """
    Получить текущий путь к директории данных.
    
    Returns:
        Path к директории данных (runtime или default)
    """
    return _runtime_data_dir if _runtime_data_dir is not None else DATA_DIR


def set_data_dir(path: Union[str, Path]) -> None:
    """
    Установить новый путь к директории данных.
    
    Args:
        path: Новый путь к директории данных
        
    Raises:
        ValueError: Если путь не является директорией
    """
    global _runtime_data_dir
    new_path = Path(path)
    
    if new_path.exists() and not new_path.is_dir():
        raise ValueError(f"Path {path} exists but is not a directory")
    
    # Создаем директорию если её нет
    new_path.mkdir(exist_ok=True, parents=True)
    _runtime_data_dir = new_path


def get_results_dir() -> Path:
    """
    Получить текущий путь к директории результатов.
    
    Returns:
        Path к директории результатов (runtime или default)
    """
    return _runtime_results_dir if _runtime_results_dir is not None else RESULTS_DIR


def set_results_dir(path: Union[str, Path]) -> None:
    """
    Установить новый путь к директории результатов.
    
    Args:
        path: Новый путь к директории результатов
        
    Raises:
        ValueError: Если путь не является директорией
    """
    global _runtime_results_dir
    new_path = Path(path)
    
    if new_path.exists() and not new_path.is_dir():
        raise ValueError(f"Path {path} exists but is not a directory")
    
    # Создаем директорию если её нет
    new_path.mkdir(exist_ok=True, parents=True)
    _runtime_results_dir = new_path


def get_notebooks_dir() -> Path:
    """
    Получить текущий путь к директории ноутбуков.
    
    Returns:
        Path к директории ноутбуков (runtime или default)
    """
    return _runtime_notebooks_dir if _runtime_notebooks_dir is not None else NOTEBOOKS_DIR


def set_notebooks_dir(path: Union[str, Path]) -> None:
    """
    Установить новый путь к директории ноутбуков.
    
    Args:
        path: Новый путь к директории ноутбуков
        
    Raises:
        ValueError: Если путь не является директорией
    """
    global _runtime_notebooks_dir
    new_path = Path(path)
    
    if new_path.exists() and not new_path.is_dir():
        raise ValueError(f"Path {path} exists but is not a directory")
    
    # Создаем директорию если её нет
    new_path.mkdir(exist_ok=True, parents=True)
    _runtime_notebooks_dir = new_path


def get_processed_data_dir() -> Path:
    """
    Получить текущий путь к директории обработанных данных.
    
    Returns:
        Path к директории обработанных данных (runtime или default)
    """
    return _runtime_processed_data_dir if _runtime_processed_data_dir is not None else PROCESSED_DATA_DIR


def set_processed_data_dir(path: Union[str, Path]) -> None:
    """
    Установить новый путь к директории обработанных данных.
    
    Args:
        path: Новый путь к директории обработанных данных
        
    Raises:
        ValueError: Если путь не является директорией
    """
    global _runtime_processed_data_dir
    new_path = Path(path)
    
    if new_path.exists() and not new_path.is_dir():
        raise ValueError(f"Path {path} exists but is not a directory")
    
    # Создаем директорию если её нет
    new_path.mkdir(exist_ok=True, parents=True)
    _runtime_processed_data_dir = new_path


def reset_directories_to_defaults() -> None:
    """
    Сбросить все пути директорий к значениям по умолчанию.
    """
    global _runtime_data_dir, _runtime_results_dir, _runtime_notebooks_dir, _runtime_processed_data_dir
    _runtime_data_dir = None
    _runtime_results_dir = None
    _runtime_notebooks_dir = None
    _runtime_processed_data_dir = None


def get_directory_status() -> Dict[str, Any]:
    """
    Получить информацию о текущих путях директорий.
    
    Returns:
        Словарь с информацией о директориях
    """
    return {
        'data_dir': {
            'current': str(get_data_dir()),
            'default': str(DATA_DIR),
            'is_custom': _runtime_data_dir is not None,
            'exists': get_data_dir().exists()
        },
        'results_dir': {
            'current': str(get_results_dir()),
            'default': str(RESULTS_DIR),
            'is_custom': _runtime_results_dir is not None,
            'exists': get_results_dir().exists()
        },
        'notebooks_dir': {
            'current': str(get_notebooks_dir()),
            'default': str(NOTEBOOKS_DIR),
            'is_custom': _runtime_notebooks_dir is not None,
            'exists': get_notebooks_dir().exists()
        },
        'processed_data_dir': {
            'current': str(get_processed_data_dir()),
            'default': str(PROCESSED_DATA_DIR),
            'is_custom': _runtime_processed_data_dir is not None,
            'exists': get_processed_data_dir().exists()
        }
    }
