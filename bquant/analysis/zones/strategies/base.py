"""
Base protocols and dataclasses for zone metrics calculation strategies.

Defines contracts for all metric calculation strategies using Protocol for type checking.
Each strategy type has its own protocol and result dataclass with validation.
"""

from dataclasses import dataclass, field
from typing import Protocol, Dict, Any, Optional, runtime_checkable
import pandas as pd


@dataclass
class SwingMetrics:
    """
    Standardized result of swing calculation.
    
    Extended version with comprehensive metrics for swing analysis.
    
    Attributes:
        # === EXISTING (6 fields) ===
        num_swings: Number of swings (impulse+correction pairs)
        avg_rally_pct: Average rally amplitude (%)
        avg_drop_pct: Average drop amplitude (%)
        max_rally_pct: Maximum rally amplitude (%)
        max_drop_pct: Maximum drop amplitude (%)
        rally_to_drop_ratio: Ratio of avg_rally to avg_drop
        
        # === COUNTERS (+2 fields) ===
        rally_count: Number of UP movements
        drop_count: Number of DOWN movements
        
        # === MINIMUMS AND DISTRIBUTION (+6 fields) ===
        min_rally_pct: Minimum rally amplitude (%)
        min_drop_pct: Minimum drop amplitude (%)
        rally_amplitude_std: Standard deviation of rally amplitudes
        drop_amplitude_std: Standard deviation of drop amplitudes
        rally_amplitude_median: Median rally amplitude (%)
        drop_amplitude_median: Median drop amplitude (%)
        
        # === DURATION IN BARS (+4 fields) ===
        avg_rally_duration_bars: Average rally duration (bars)
        avg_drop_duration_bars: Average drop duration (bars)
        max_rally_duration_bars: Maximum rally duration (bars)
        max_drop_duration_bars: Maximum drop duration (bars)
        
        # === SPEED (+4 fields) ===
        avg_rally_speed_pct_per_bar: Average rally speed (% per bar)
        avg_drop_speed_pct_per_bar: Average drop speed (% per bar)
        max_rally_speed_pct_per_bar: Maximum rally speed (% per bar)
        max_drop_speed_pct_per_bar: Maximum drop speed (% per bar)
        
        # === SYMMETRY (+1 field) ===
        duration_symmetry: Ratio of avg_rally_duration to avg_drop_duration
        
        # === METADATA ===
        strategy_name: Name of the strategy used
        strategy_params: Parameters of the strategy
    """
    # Existing fields (6)
    num_swings: int
    avg_rally_pct: float
    avg_drop_pct: float
    max_rally_pct: float
    max_drop_pct: float
    rally_to_drop_ratio: float
    
    # Counters (2)
    rally_count: int
    drop_count: int
    
    # Minimums and distribution (6)
    min_rally_pct: float
    min_drop_pct: float
    rally_amplitude_std: float
    drop_amplitude_std: float
    rally_amplitude_median: float
    drop_amplitude_median: float
    
    # Duration in bars (4)
    avg_rally_duration_bars: float
    avg_drop_duration_bars: float
    max_rally_duration_bars: int
    max_drop_duration_bars: int
    
    # Speed (4)
    avg_rally_speed_pct_per_bar: float
    avg_drop_speed_pct_per_bar: float
    max_rally_speed_pct_per_bar: float
    max_drop_speed_pct_per_bar: float
    
    # Symmetry (1)
    duration_symmetry: float
    
    # Metadata
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate metric correctness."""
        # Existing validations
        assert self.num_swings >= 0, "num_swings must be >= 0"
        assert self.avg_rally_pct >= 0, "avg_rally_pct must be >= 0"
        assert self.avg_drop_pct >= 0, "avg_drop_pct must be >= 0"
        assert self.max_rally_pct >= 0, "max_rally_pct must be >= 0"
        assert self.max_drop_pct >= 0, "max_drop_pct must be >= 0"
        assert self.rally_to_drop_ratio >= 0, "rally_to_drop_ratio must be >= 0"
        
        # New validations
        assert self.rally_count >= 0, "rally_count must be >= 0"
        assert self.drop_count >= 0, "drop_count must be >= 0"
        assert self.min_rally_pct >= 0, "min_rally_pct must be >= 0"
        assert self.min_drop_pct >= 0, "min_drop_pct must be >= 0"
        assert self.rally_amplitude_std >= 0, "rally_amplitude_std must be >= 0"
        assert self.drop_amplitude_std >= 0, "drop_amplitude_std must be >= 0"
        assert self.rally_amplitude_median >= 0, "rally_amplitude_median must be >= 0"
        assert self.drop_amplitude_median >= 0, "drop_amplitude_median must be >= 0"
        assert self.avg_rally_duration_bars >= 0, "avg_rally_duration_bars must be >= 0"
        assert self.avg_drop_duration_bars >= 0, "avg_drop_duration_bars must be >= 0"
        assert self.max_rally_duration_bars >= 0, "max_rally_duration_bars must be >= 0"
        assert self.max_drop_duration_bars >= 0, "max_drop_duration_bars must be >= 0"
        assert self.avg_rally_speed_pct_per_bar >= 0, "avg_rally_speed_pct_per_bar must be >= 0"
        assert self.avg_drop_speed_pct_per_bar >= 0, "avg_drop_speed_pct_per_bar must be >= 0"
        assert self.max_rally_speed_pct_per_bar >= 0, "max_rally_speed_pct_per_bar must be >= 0"
        assert self.max_drop_speed_pct_per_bar >= 0, "max_drop_speed_pct_per_bar must be >= 0"
        assert self.duration_symmetry >= 0, "duration_symmetry must be >= 0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            # Existing fields
            'num_swings': self.num_swings,
            'avg_rally_pct': self.avg_rally_pct,
            'avg_drop_pct': self.avg_drop_pct,
            'max_rally_pct': self.max_rally_pct,
            'max_drop_pct': self.max_drop_pct,
            'rally_to_drop_ratio': self.rally_to_drop_ratio,
            
            # Counters
            'rally_count': self.rally_count,
            'drop_count': self.drop_count,
            
            # Minimums and distribution
            'min_rally_pct': self.min_rally_pct,
            'min_drop_pct': self.min_drop_pct,
            'rally_amplitude_std': self.rally_amplitude_std,
            'drop_amplitude_std': self.drop_amplitude_std,
            'rally_amplitude_median': self.rally_amplitude_median,
            'drop_amplitude_median': self.drop_amplitude_median,
            
            # Duration
            'avg_rally_duration_bars': self.avg_rally_duration_bars,
            'avg_drop_duration_bars': self.avg_drop_duration_bars,
            'max_rally_duration_bars': self.max_rally_duration_bars,
            'max_drop_duration_bars': self.max_drop_duration_bars,
            
            # Speed
            'avg_rally_speed_pct_per_bar': self.avg_rally_speed_pct_per_bar,
            'avg_drop_speed_pct_per_bar': self.avg_drop_speed_pct_per_bar,
            'max_rally_speed_pct_per_bar': self.max_rally_speed_pct_per_bar,
            'max_drop_speed_pct_per_bar': self.max_drop_speed_pct_per_bar,
            
            # Symmetry
            'duration_symmetry': self.duration_symmetry,
            
            # Metadata
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }


@runtime_checkable
class SwingCalculationStrategy(Protocol):
    """
    Protocol for swing detection algorithms.
    
    Implementations must provide calculate_swings() and get_metadata() methods.
    """
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate swing metrics.
        
        Args:
            zone_data: DataFrame with columns: high, low, close
        
        Returns:
            SwingMetrics with validated data
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        ...


@dataclass
class DivergenceMetrics:
    """
    Standardized result of divergence calculation.
    
    Attributes:
        divergence_type: Type of divergence ('none', 'regular', 'hidden', 'mixed')
        divergence_count: Number of divergences in zone
        divergence_strength: Average divergence strength
        divergence_direction: Direction ('bullish', 'bearish', 'none')
        strategy_name: Name of the strategy used
        strategy_params: Parameters of the strategy
    """
    divergence_type: str
    divergence_count: int
    divergence_strength: float
    divergence_direction: str
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate metric correctness."""
        valid_types = ['none', 'regular', 'hidden', 'mixed']
        assert self.divergence_type in valid_types, f"divergence_type must be in {valid_types}"
        assert self.divergence_count >= 0, "divergence_count must be >= 0"
        assert self.divergence_strength >= 0, "divergence_strength must be >= 0"
        valid_directions = ['bullish', 'bearish', 'none']
        assert self.divergence_direction in valid_directions, f"divergence_direction must be in {valid_directions}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'divergence_type': self.divergence_type,
            'divergence_count': self.divergence_count,
            'divergence_strength': self.divergence_strength,
            'divergence_direction': self.divergence_direction,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }


@runtime_checkable
class DivergenceCalculationStrategy(Protocol):
    """
    Protocol for divergence detection algorithms.
    
    Implementations must provide calculate_divergence() and get_metadata() methods.
    """
    
    def calculate_divergence(self, zone_data: pd.DataFrame) -> DivergenceMetrics:
        """
        Calculate divergence metrics.
        
        Args:
            zone_data: DataFrame with columns: close, high, low, macd, macd_hist
        
        Returns:
            DivergenceMetrics with validated data
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        ...


@dataclass
class ShapeMetrics:
    """
    Standardized result of shape calculation.
    
    Attributes:
        hist_skewness: Skewness of histogram (asymmetry)
        hist_kurtosis: Kurtosis of histogram (peakedness)
        hist_smoothness: Smoothness of histogram curve
        strategy_name: Name of the strategy used
        strategy_params: Parameters of the strategy
    """
    hist_skewness: float
    hist_kurtosis: float
    hist_smoothness: float
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate metric correctness."""
        # Skewness can be any value, but typically in range [-3, 3]
        # Kurtosis can be any positive value
        assert not pd.isna(self.hist_skewness), "hist_skewness must not be NaN"
        assert not pd.isna(self.hist_kurtosis), "hist_kurtosis must not be NaN"
        assert not pd.isna(self.hist_smoothness), "hist_smoothness must not be NaN"
        assert self.hist_smoothness >= 0, "hist_smoothness must be >= 0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hist_skewness': self.hist_skewness,
            'hist_kurtosis': self.hist_kurtosis,
            'hist_smoothness': self.hist_smoothness,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }


@runtime_checkable
class ShapeCalculationStrategy(Protocol):
    """
    Protocol for histogram shape analysis algorithms.
    
    Implementations must provide calculate_shape() and get_metadata() methods.
    """
    
    def calculate_shape(self, zone_data: pd.DataFrame) -> ShapeMetrics:
        """
        Calculate shape metrics.
        
        Args:
            zone_data: DataFrame with column: macd_hist
        
        Returns:
            ShapeMetrics with validated data
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        ...


@dataclass
class VolumeMetrics:
    """
    Standardized result of volume calculation.
    
    Attributes:
        volume_zone_ratio: Ratio of zone volume to baseline
        volume_at_entry_change: Volume change at zone entry (%)
        volume_indicator_corr: Correlation between volume and indicator (v2.1 - renamed from volume_macd_corr)
        avg_volume_zone: Average volume in zone
        strategy_name: Name of the strategy used
        strategy_params: Parameters of the strategy
    """
    volume_zone_ratio: Optional[float]
    volume_at_entry_change: Optional[float]
    volume_indicator_corr: Optional[float]  # v2.1: renamed from volume_macd_corr
    avg_volume_zone: Optional[float]
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate metric correctness."""
        if self.volume_zone_ratio is not None:
            assert self.volume_zone_ratio >= 0, "volume_zone_ratio must be >= 0"
        if self.avg_volume_zone is not None:
            assert self.avg_volume_zone >= 0, "avg_volume_zone must be >= 0"
        if self.volume_indicator_corr is not None:
            assert -1 <= self.volume_indicator_corr <= 1, "volume_indicator_corr must be in [-1, 1]"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'volume_zone_ratio': self.volume_zone_ratio,
            'volume_at_entry_change': self.volume_at_entry_change,
            'volume_indicator_corr': self.volume_indicator_corr,  # v2.1: renamed
            'avg_volume_zone': self.avg_volume_zone,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }


@runtime_checkable
class VolumeCalculationStrategy(Protocol):
    """
    Protocol for volume analysis algorithms.
    
    Implementations must provide calculate_volume() and get_metadata() methods.
    """
    
    def calculate_volume(self, zone_data: pd.DataFrame, baseline_volume: float) -> VolumeMetrics:
        """
        Calculate volume metrics.
        
        Args:
            zone_data: DataFrame with column: volume
            baseline_volume: Baseline volume for comparison
        
        Returns:
            VolumeMetrics with validated data
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        ...


@dataclass
class VolatilityMetrics:
    """
    Standardized result of volatility calculation.
    
    Volatility metrics assess the "activity" and uncertainty of price movement
    within a zone using Bollinger Bands and ATR indicators.
    
    Attributes:
        bollinger_width_pct: Average Bollinger Bands width as % of price
        bollinger_width_std: Standard deviation of BB width (stability)
        bollinger_squeeze_ratio: Current width / historical average width
        bollinger_upper_touches: Count of price touches to upper band
        bollinger_lower_touches: Count of price touches to lower band
        atr_normalized_range: Price range / average ATR
        atr_trend: ATR trend direction ('increasing', 'decreasing', 'stable')
        avg_atr: Average ATR in zone
        volatility_score: Composite volatility score (0-10)
        volatility_regime: Volatility regime classification
        strategy_name: Name of the strategy used
        strategy_params: Parameters of the strategy
    """
    bollinger_width_pct: float
    bollinger_width_std: float
    bollinger_squeeze_ratio: float
    bollinger_upper_touches: int
    bollinger_lower_touches: int
    atr_normalized_range: float
    atr_trend: str
    avg_atr: float
    volatility_score: float
    volatility_regime: str
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate metric correctness."""
        assert self.bollinger_width_pct >= 0, "bollinger_width_pct must be >= 0"
        assert self.bollinger_width_std >= 0, "bollinger_width_std must be >= 0"
        assert self.bollinger_squeeze_ratio >= 0, "bollinger_squeeze_ratio must be >= 0"
        assert self.bollinger_upper_touches >= 0, "bollinger_upper_touches must be >= 0"
        assert self.bollinger_lower_touches >= 0, "bollinger_lower_touches must be >= 0"
        assert self.atr_normalized_range >= 0, "atr_normalized_range must be >= 0"
        assert self.atr_trend in ['increasing', 'decreasing', 'stable'], \
            f"atr_trend must be in ['increasing', 'decreasing', 'stable'], got {self.atr_trend}"
        assert self.avg_atr >= 0, "avg_atr must be >= 0"
        assert 0 <= self.volatility_score <= 10, "volatility_score must be in [0, 10]"
        assert self.volatility_regime in ['low', 'medium', 'high', 'extreme'], \
            f"volatility_regime must be in ['low', 'medium', 'high', 'extreme'], got {self.volatility_regime}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'bollinger_width_pct': self.bollinger_width_pct,
            'bollinger_width_std': self.bollinger_width_std,
            'bollinger_squeeze_ratio': self.bollinger_squeeze_ratio,
            'bollinger_upper_touches': self.bollinger_upper_touches,
            'bollinger_lower_touches': self.bollinger_lower_touches,
            'atr_normalized_range': self.atr_normalized_range,
            'atr_trend': self.atr_trend,
            'avg_atr': self.avg_atr,
            'volatility_score': self.volatility_score,
            'volatility_regime': self.volatility_regime,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }


@runtime_checkable
class VolatilityCalculationStrategy(Protocol):
    """
    Protocol for volatility analysis algorithms.
    
    Implementations must provide calculate_volatility() and get_metadata() methods.
    """
    
    def calculate_volatility(self, zone_data: pd.DataFrame) -> VolatilityMetrics:
        """
        Calculate volatility metrics.
        
        Args:
            zone_data: DataFrame with columns: high, low, close, atr
        
        Returns:
            VolatilityMetrics with validated data
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Strategy metadata for logging and traceability."""
        ...


__all__ = [
    # Metrics dataclasses
    'SwingMetrics',
    'DivergenceMetrics',
    'ShapeMetrics',
    'VolumeMetrics',
    'VolatilityMetrics',
    # Strategy protocols
    'SwingCalculationStrategy',
    'DivergenceCalculationStrategy',
    'ShapeCalculationStrategy',
    'VolumeCalculationStrategy',
    'VolatilityCalculationStrategy'
]

