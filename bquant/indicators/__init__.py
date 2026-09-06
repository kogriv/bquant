"""BQuant Indicators Module."""

from bquant.core.logging_config import get_logger

# Base classes and architecture
from .base import (
    IndicatorSource,
    IndicatorConfig,
    IndicatorResult,
    BaseIndicator,
    PreloadedIndicator,
    CustomIndicator,
    LibraryIndicator,
    IndicatorFactory
)

# Built-in indicators (мигрированы в custom/ на Этапе 4)
from .custom import (
    SimpleMovingAverage,
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    MACD,
    BollingerBands
)

# External library loaders (moved from loaders.py)
from .library import (
    PandasTALoader,
    TALibLoader,
    LibraryManager,
    load_pandas_ta,
    load_talib,
    load_all_indicators
)

# High-level calculators (временно закомментировано до Этапа 4)
# from .calculators import (
#     IndicatorCalculator,
#     BatchCalculator,
#     calculate_indicator,
#     calculate_macd,
#     calculate_rsi,
#     calculate_bollinger_bands,
#     calculate_moving_averages,
#     create_indicator_suite,
#     get_available_indicators,
#     validate_indicator_data
# )

# MACDZoneAnalyzer and its convenience wrappers were removed (deprecated
# since v2.1). Use the Universal Zone Analysis pipeline instead:
#     from bquant.analysis.zones import analyze_zones, analyze_macd_zones
# ZoneInfo / ZoneAnalysisResult live in bquant.analysis.zones.models.

# PRELOADED indicators
from .preloaded import (
    MACDPreloadedIndicator
)

logger = get_logger(__name__)

# Один бутстрап реестра (G64). Регистрируются классы этого пакета — дёшево и без
# побочных эффектов. Внешние библиотеки (pandas-ta, TA-Lib) при импорте НЕ загружаются:
# их подхватит ``LibraryManager.ensure_loaded()`` при первом обращении к фабрике за
# библиотечным индикатором или за списком. До G64 импорт ``bquant.indicators`` тянул
# ``import pandas_ta`` (≈1 с на тёплом кэше numba, десятки секунд на холодном) и
# регистрировал встроенные индикаторы трижды.
from .custom import register_builtin_indicators
from .output_schema import IndicatorSchema, MACD_SCHEMA, RSI_SCHEMA


def _bootstrap_registry() -> None:
    """Регистрирует PRELOADED и CUSTOM индикаторы. Идемпотентно."""
    IndicatorFactory.register_indicator('macd_preloaded', MACDPreloadedIndicator)
    register_builtin_indicators()


_bootstrap_registry()

__all__ = [
    # Base classes
    "BaseIndicator",
    "PreloadedIndicator", 
    "LibraryIndicator",
    "CustomIndicator",
    "IndicatorResult",
    "IndicatorConfig",
    "IndicatorSource",
    "IndicatorFactory",
    
    # PRELOADED indicators
    "MACDPreloadedIndicator",
    
    # Built-in indicators (мигрированы в custom/ на Этапе 4)
    "SimpleMovingAverage",
    "ExponentialMovingAverage",
    "RelativeStrengthIndex",
    "MACD",
    "BollingerBands",
    
    # External library loaders (мигрированы в library/ на Этапе 5)
    "PandasTALoader",
    "TALibLoader",
    "LibraryManager",
    "load_pandas_ta",
    "load_talib",
    "load_all_indicators",
    "register_builtin_indicators",

    # Output schema of an indicator (moved from bquant.data.schemas, G64)
    "IndicatorSchema",
    "MACD_SCHEMA",
    "RSI_SCHEMA",
]
