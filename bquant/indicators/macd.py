"""
MACD Zone Analyzer - Backward Compatibility Wrapper

⚠️ DEPRECATED: This module provides backward compatibility only.

Recommended approach:
    from bquant.analysis.zones import analyze_zones
    
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=True)
        .build()
    )

This file was refactored from 517 lines (monolithic) to ~100 lines (thin wrapper)
as part of Universal Zone Analyzer architecture (Stage 2).

See: devref/gaps/zo/zonan.md for architecture details.
"""

from typing import Dict, Any, Optional
import warnings

# BQuant imports
from bquant.core.config import get_indicator_params, get_analysis_params
from bquant.core.logging_config import get_logger
from bquant.core.utils import deprecated

# Import models only (avoid circular import with pipeline)
from bquant.analysis.zones.models import ZoneInfo, ZoneAnalysisResult

# NOTE: ZoneInfo and ZoneAnalysisResult are now in bquant/analysis/zones/models.py
# Imported here for backward compatibility

logger = get_logger(__name__)


@deprecated(
    message=(
        "MACDZoneAnalyzer is deprecated and will be removed in v3.0.0. "
        "Use the universal zone analysis API instead:\n"
        "  from bquant.analysis.zones import analyze_zones\n"
        "  result = analyze_zones(df).with_indicator('custom', 'macd').detect_zones('zero_crossing', indicator_col='macd_hist').build()"
    )
)
class MACDZoneAnalyzer:
    """
    Deprecated wrapper for MACD zone analysis.
    
    ⚠️ This class is deprecated. Use universal zone analysis API instead.
    
    This wrapper provides backward compatibility for existing code.
    All analysis is delegated to the new universal architecture:
    - Detection: ZeroCrossingDetection strategy
    - Analysis: UniversalZoneAnalyzer
    - Pipeline: ZoneAnalysisPipeline
    
    Old approach (deprecated):
        analyzer = MACDZoneAnalyzer()
        result = analyzer.analyze_complete(df)
    
    New approach (recommended):
        from bquant.analysis.zones import analyze_zones
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=True)
            .build()
        )
    """
    
    def __init__(self, 
                 macd_params: Optional[Dict[str, Any]] = None,
                 zone_params: Optional[Dict[str, Any]] = None):
        """
        Initialize MACD zone analyzer with parameters.
        
        Args:
            macd_params: MACD parameters (fast, slow, signal)
            zone_params: Zone analysis parameters (min_duration, min_amplitude)
        """
        # Convert old param names to new ones if needed
        if macd_params is None:
            macd_params = get_indicator_params('macd')
        
        # Adapt parameter names: old format → new format
        self.macd_params = {
            'fast_period': macd_params.get('fast_period', macd_params.get('fast', 12)),
            'slow_period': macd_params.get('slow_period', macd_params.get('slow', 26)),
            'signal_period': macd_params.get('signal_period', macd_params.get('signal', 9))
        }
        
        self.zone_params = zone_params or get_analysis_params('zone_analysis')
        
        logger.info(
            f"MACDZoneAnalyzer initialized (DEPRECATED) with params: "
            f"MACD={self.macd_params}, Zones={self.zone_params}"
        )
        logger.warning(
            "MACDZoneAnalyzer is deprecated. "
            "Please migrate to: from bquant.analysis.zones import analyze_zones"
        )
    
    def analyze_complete(self, 
                        df,
                        perform_clustering: bool = True,
                        n_clusters: int = 3) -> ZoneAnalysisResult:
        """
        Full MACD zone analysis (delegates to analyze_complete_modular).
        
        ⚠️ DEPRECATED: Use universal API instead.
        
        Args:
            df: DataFrame with OHLCV data
            perform_clustering: Whether to perform clustering
            n_clusters: Number of clusters
            
        Returns:
            ZoneAnalysisResult with full analysis
        """
        logger.info("analyze_complete() called - delegating to analyze_complete_modular()")
        return self.analyze_complete_modular(df, perform_clustering, n_clusters)
    
    def analyze_complete_modular(self, 
                                 df,
                                 perform_clustering: bool = True,
                                 n_clusters: int = 3,
                                 run_regression: bool = False,
                                 run_validation: bool = False) -> ZoneAnalysisResult:
        """
        Full MACD zone analysis using universal pipeline.
        
        ⚠️ DEPRECATED: This is a backward compatibility wrapper.
        
        Delegates all work to the new universal zone analysis architecture:
        - Indicator calculation via IndicatorFactory
        - Zone detection via ZeroCrossingDetection strategy
        - Analysis via UniversalZoneAnalyzer
        
        Args:
            df: DataFrame with OHLCV data
            perform_clustering: Whether to perform clustering
            n_clusters: Number of clusters
            run_regression: Whether to run regression analysis
            run_validation: Whether to run validation
            
        Returns:
            ZoneAnalysisResult with full analysis
            
        Example (new recommended way):
            from bquant.analysis.zones import analyze_zones
            
            result = (
                analyze_zones(df)
                .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .analyze(clustering=True, n_clusters=3)
                .build()
            )
        """
        logger.info("analyze_complete_modular() - delegating to universal pipeline")
        
        # Import here to avoid circular dependency
        from bquant.analysis.zones import analyze_zones
        
        # Delegate to universal zone analysis pipeline
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', **self.macd_params)
            .detect_zones(
                'zero_crossing',
                indicator_col='macd_hist',
                min_duration=self.zone_params.get('min_duration', 2)
            )
            .analyze(
                clustering=perform_clustering,
                n_clusters=n_clusters,
                regression=run_regression,
                validation=run_validation
            )
            .build()
        )
        
        logger.info(
            f"Analysis complete via universal pipeline: {len(result.zones)} zones detected"
        )
        
        return result

# Convenience functions (also delegate to universal API)

@deprecated(
    message="create_macd_analyzer() is deprecated. Use 'analyze_zones()' directly."
)
def create_macd_analyzer(macd_params: Optional[Dict[str, Any]] = None,
                        zone_params: Optional[Dict[str, Any]] = None) -> MACDZoneAnalyzer:
    """
    Create MACD analyzer instance.
    
    ⚠️ DEPRECATED: Use universal API instead.
    
    Args:
        macd_params: MACD parameters
        zone_params: Zone analysis parameters
        
    Returns:
        MACDZoneAnalyzer instance (deprecated)
    """
    return MACDZoneAnalyzer(macd_params, zone_params)


@deprecated(
    message=(
        "analyze_macd_zones() is deprecated. Use universal API instead:\n"
        "  from bquant.analysis.zones import analyze_zones\n"
        "  result = analyze_zones(df).with_indicator('custom', 'macd').detect_zones('zero_crossing', indicator_col='macd_hist').build()"
    )
)
def analyze_macd_zones(df,
                      macd_params: Optional[Dict[str, Any]] = None,
                      zone_params: Optional[Dict[str, Any]] = None,
                      perform_clustering: bool = True,
                      n_clusters: int = 3) -> ZoneAnalysisResult:
    """
    Convenience function for full MACD zone analysis.
    
    ⚠️ DEPRECATED: Use universal API instead.
    
    Args:
        df: DataFrame with OHLCV data
        macd_params: MACD parameters
        zone_params: Zone analysis parameters
        perform_clustering: Whether to perform clustering
        n_clusters: Number of clusters
        
    Returns:
        Full zone analysis result
    """
    analyzer = MACDZoneAnalyzer(macd_params, zone_params)
    return analyzer.analyze_complete(df, perform_clustering, n_clusters)


# Export for backward compatibility
__all__ = [
    'MACDZoneAnalyzer',
    'create_macd_analyzer',
    'analyze_macd_zones',
    'ZoneInfo',           # Re-export from models
    'ZoneAnalysisResult'  # Re-export from models
]
