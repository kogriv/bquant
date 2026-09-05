"""Core contracts and dataclasses for zone-analysis strategies.

This module defines the canonical :class:`SwingMetrics` container and
``Protocol`` interfaces that every zone-analysis strategy must implement.
Protocols are expressed explicitly to keep mypy enforcement strong while
allowing a flexible plug-in architecture for third-party strategies.
"""

import math
from dataclasses import dataclass, field
from typing import Protocol, Dict, Any, Optional, runtime_checkable

import pandas as pd

from bquant.core.exceptions import AnalysisError

from ..models import SwingContext, ZoneInfo


def _require(condition: bool, message: str) -> None:
    """Проверить инвариант метрики.

    Раньше все проверки в этом файле стояли на `assert` — их было 39. У `assert`
    два свойства, которые здесь нежелательны: он исчезает целиком под `python -O`
    (и тогда метрика с мусором уезжает в статистику молча), и он объявляет любое
    нарушение ошибкой программиста, тогда как речь о данных.
    """

    if not condition:
        raise AnalysisError(message)


def _is_defined(value: Any) -> bool:
    """`None` — законное «не измерено»; `NaN` — нет.

    G37: `NaN >= 0` ложно, поэтому проверка на неотрицательность срабатывала на
    величине, которой просто не существует, и роняла всю группу метрик, объясняя
    это неверными словами. Отсутствие значения выражается `None` и проходит
    проверки; `NaN` остаётся ошибкой, но названной своим именем.
    """

    return not (isinstance(value, float) and math.isnan(value))


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

    Note on adding a position-within-the-zone field (`rel_time`, `rel_price`, or
    anything normalised by the zone's span or price range):

        Such a value is **post-hoc**. It divides by a quantity — the zone's duration
        or its high-low range — that is known only once the zone has ended. It is a
        legitimate descriptor of a finished zone and it is NOT a feature available at
        bar `k`: using it as one leaks the future into the past, the same class of
        error as counting a leg that has not finished yet.

        The trap is the name. A field called "the swing's position in the zone" reads
        like a ready-made feature, and that is how it will be taken. If such a field
        is ever added here, the caveat goes with it, in this docstring, in the same
        change. Raised by the consumer on `kogriv/bquearch#2` after they measured it
        on their own side; the causal counterpart they use is normalised by the
        zone's *start* price, which is known immediately.
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
        """Проверить, что метрики не противоречат своему определению."""

        for name in (
            "num_swings",
            "avg_rally_pct",
            "avg_drop_pct",
            "max_rally_pct",
            "max_drop_pct",
            "rally_to_drop_ratio",
            "rally_count",
            "drop_count",
            "min_rally_pct",
            "min_drop_pct",
            "rally_amplitude_std",
            "drop_amplitude_std",
            "rally_amplitude_median",
            "drop_amplitude_median",
            "avg_rally_duration_bars",
            "avg_drop_duration_bars",
            "max_rally_duration_bars",
            "max_drop_duration_bars",
            "avg_rally_speed_pct_per_bar",
            "avg_drop_speed_pct_per_bar",
            "max_rally_speed_pct_per_bar",
            "max_drop_speed_pct_per_bar",
            "duration_symmetry",
        ):
            value = getattr(self, name)
            _require(_is_defined(value), f"{name} is NaN: величина не измерена, а не отрицательна")
            _require(value is None or value >= 0, f"{name} must be >= 0, got {value}")

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
    """Protocol that every swing-detection strategy must satisfy.

    The protocol explicitly models both the new global workflow and the
    legacy per-zone calculation path.  Strategies are expected to implement
    the global APIs while keeping :meth:`calculate` as a backwards-compatible
    entry point for older integrations and per-zone fallbacks.
    """

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """Compute swing points for the entire prepared dataset.

        Args:
            full_data: Prepared dataframe containing at least ``high`` and
                ``low`` columns (plus any auxiliary indicators the strategy
                requires).

        Returns:
            :class:`SwingContext` populated with global swing points and
            metadata required for subsequent zone-level aggregation.

        Raises:
            ValueError: If the supplied dataframe does not contain enough
                information for the strategy to operate.
            RuntimeError: If the underlying algorithm fails unexpectedly.
        """

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """Aggregate global swing data into metrics for a particular zone.

        Args:
            zone: Zone descriptor containing positional information.
            context: Global swing context produced by :meth:`calculate_global`.

        Returns:
            :class:`SwingMetrics` summarising swing behaviour inside the zone.
        """

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """Legacy per-zone calculation entry point.

        Implementations should keep this method functional for backwards
        compatibility.  New code should prefer the global workflow unless a
        strategy explicitly documents otherwise.

        Args:
            zone_data: Slice of data restricted to a single zone.

        Returns:
            :class:`SwingMetrics` calculated using zone-only information.
        """

    def get_metadata(self) -> Dict[str, Any]:
        """Return strategy metadata for logging and traceability."""

    def config_hash(self) -> Dict[str, Any]:
        """Return configuration snapshot used for cache-key generation."""


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
        """Проверить, что метрики не противоречат своему определению."""

        valid_types = ['none', 'regular', 'hidden', 'mixed']
        _require(
            self.divergence_type in valid_types,
            f"divergence_type must be in {valid_types}, got {self.divergence_type!r}",
        )
        _require(_is_defined(self.divergence_strength), "divergence_strength is NaN")
        _require(self.divergence_count >= 0, f"divergence_count must be >= 0, got {self.divergence_count}")
        _require(
            self.divergence_strength is None or self.divergence_strength >= 0,
            f"divergence_strength must be >= 0, got {self.divergence_strength}",
        )
        valid_directions = ['bullish', 'bearish', 'none']
        _require(
            self.divergence_direction in valid_directions,
            f"divergence_direction must be in {valid_directions}, got {self.divergence_direction!r}",
        )
    
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
    
    def calculate_divergence(
        self,
        zone_data: pd.DataFrame,
        indicator_col: str,
        indicator_line_col: Optional[str] = None,
    ) -> DivergenceMetrics:
        """
        Calculate divergence metrics.
        
        Args:
            zone_data: DataFrame with columns: close, high, low, and the
                indicator series named by ``indicator_col`` (e.g.
                ``macd_12_26_9__line``, ``macd_12_26_9__hist``)
        
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
        """Проверить, что метрики не противоречат своему определению."""

        # Асимметрия может быть любой, эксцесс — любым положительным; проверяется
        # не диапазон, а определённость: NaN здесь означает, что считать было не по
        # чему, и такую величину нельзя класть в статистику как измерение.
        for name in ("hist_skewness", "hist_kurtosis", "hist_smoothness"):
            _require(not pd.isna(getattr(self, name)), f"{name} is NaN: величина не измерена")
        _require(self.hist_smoothness >= 0, f"hist_smoothness must be >= 0, got {self.hist_smoothness}")
    
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
    
    def calculate(self, zone_data: pd.DataFrame, indicator_col: str) -> ShapeMetrics:
        """
        Calculate shape metrics — this is the call the feature analyzer makes.

        Until G68 this Protocol declared ``calculate_shape(zone_data)`` while
        the analyzer called ``calculate(zone_data, indicator_col=...)``; a
        strategy written to the Protocol raised inside the analyzer, where the
        error was swallowed, and every zone got ``shape_metrics = None``.

        Args:
            zone_data: DataFrame carrying the series named by ``indicator_col``
            indicator_col: Column holding the oscillator to describe

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
        """Проверить, что метрики не противоречат своему определению."""

        for name in ("volume_zone_ratio", "avg_volume_zone"):
            value = getattr(self, name)
            if value is None:
                continue
            _require(_is_defined(value), f"{name} is NaN: величина не измерена")
            _require(value >= 0, f"{name} must be >= 0, got {value}")

        if self.volume_indicator_corr is not None:
            _require(_is_defined(self.volume_indicator_corr), "volume_indicator_corr is NaN")
            _require(
                -1 <= self.volume_indicator_corr <= 1,
                f"volume_indicator_corr must be in [-1, 1], got {self.volume_indicator_corr}",
            )
    
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
    Until G68 this block was a copy of the volatility Protocol and declared
    ``calculate_volatility`` — a method no volume strategy has.
    """

    def calculate_volume(
        self,
        zone_data: pd.DataFrame,
        baseline_volume: Optional[float] = None,
        indicator_col: Optional[str] = None,
    ) -> VolumeMetrics:
        """
        Calculate volume metrics — the call the feature analyzer makes.

        Args:
            zone_data: DataFrame with columns: volume, close (plus the indicator)
            baseline_volume: Reference volume for ``volume_zone_ratio``; ``None``
                lets the strategy pick its own baseline
            indicator_col: Column of the oscillator for ``volume_indicator_corr``

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
    # Полосы Боллинджера считаются по окну `bb_length`; в зоне короче двух окон
    # часть величин не определена. `None` здесь означает «не измерено» и это не то
    # же самое, что `0.0`: ноль утверждал бы, что ширина полос нулевая, а разброс
    # отсутствует (G37).
    bollinger_width_pct: Optional[float]
    bollinger_width_std: Optional[float]
    bollinger_squeeze_ratio: Optional[float]
    bollinger_upper_touches: Optional[int]
    bollinger_lower_touches: Optional[int]
    atr_normalized_range: float
    atr_trend: str
    avg_atr: float
    # Композит по шкале 0–10 складывается из трёх компонент, две из которых
    # боллинджеровские. Без них число по той же шкале несопоставимо, поэтому его
    # не существует, а не «оно маленькое».
    volatility_score: Optional[float]
    volatility_regime: Optional[str]
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Проверить, что метрики не противоречат своему определению."""

        for name in (
            "bollinger_width_pct",
            "bollinger_width_std",
            "bollinger_squeeze_ratio",
            "bollinger_upper_touches",
            "bollinger_lower_touches",
            "atr_normalized_range",
            "avg_atr",
        ):
            value = getattr(self, name)
            _require(_is_defined(value), f"{name} is NaN: величина не измерена, а не отрицательна")
            _require(value is None or value >= 0, f"{name} must be >= 0, got {value}")

        valid_trends = ['increasing', 'decreasing', 'stable']
        _require(
            self.atr_trend in valid_trends,
            f"atr_trend must be in {valid_trends}, got {self.atr_trend!r}",
        )

        _require(_is_defined(self.volatility_score), "volatility_score is NaN")
        _require(
            self.volatility_score is None or 0 <= self.volatility_score <= 10,
            f"volatility_score must be in [0, 10], got {self.volatility_score}",
        )

        valid_regimes = ['low', 'medium', 'high', 'extreme']
        _require(
            self.volatility_regime is None or self.volatility_regime in valid_regimes,
            f"volatility_regime must be in {valid_regimes} or None, got {self.volatility_regime!r}",
        )
        # Режим — подпись к числу: без числа подписи не бывает и наоборот.
        _require(
            (self.volatility_score is None) == (self.volatility_regime is None),
            "volatility_score и volatility_regime обязаны отсутствовать вместе",
        )
    
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

