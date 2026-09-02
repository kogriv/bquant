"""
Zone Analysis Models - shared data structures for the zone-analysis pipeline.

The module exposes the core entities used across zone detection and analytics:
* ``ZoneType`` / ``ZoneVocabulary`` – declared meaning of the zone types a
  detection strategy emits, so that universal layers can discriminate on
  properties instead of on hardcoded names.
* ``ZoneInfo`` – generic container describing a detected zone.
* ``ZoneAnalysisResult`` – aggregate result of running the analysis pipeline.

Responsibilities:
* Provide a consistent schema for downstream consumers and visualization.
* Support (de-)serialization to pickle/JSON/Parquet formats.
* Preserve backward compatibility between schema versions.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, Tuple, Iterable
from datetime import datetime
from pathlib import Path
from importlib import import_module
from bisect import bisect_left, bisect_right

import numpy as np
import pandas as pd
import pickle
import gzip
import json

from ...core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SwingPoint:
    """Represents a single swing point (peak or trough) detected globally.

    Attributes:
        point_id: Unique identifier within the swing sequence.
        timestamp: Timestamp of the swing point (index value from the dataset).
        index: Integer position of the point in the full dataset.
        price: Price at the swing point.
        swing_type: Type of swing, ``"peak"`` or ``"trough"``.
        amplitude_to_next: Percentage change to the next swing point (if available).
        duration_to_next: Number of bars to the next swing point (if available).
        strategy_name: Name of the strategy that detected the swing.
        strategy_params: Parameters of the strategy for traceability.
        confirmation_index: Integer position of the bar by which this swing is
            **causally confirmed** — i.e. the earliest bar at which a downstream,
            leak-free consumer may treat the pivot (and therefore its
            ``amplitude_to_next``) as known. Always ``>= index``. ``None`` means the
            pivot is not yet confirmed within the available data (typically the last,
            still-forming swing). The confirmation rule is **strategy-specific** (a
            ZigZag pivot confirms once price retraces the configured deviation; a
            fractal/pivot-point swing confirms after its fixed look-ahead window; etc.),
            so each swing strategy populates this field per its own semantics. A strategy
            that does not compute it leaves ``None``, and consumers must degrade
            gracefully. This field exists to let forecasting/OOS code build prefixes
            strictly from swings available at decision time, avoiding look-ahead through
            ``amplitude_to_next`` (whose endpoint lies in the future of ``index``).

    Example:
        >>> from datetime import datetime
        >>> point = SwingPoint(
        ...     point_id=1,
        ...     timestamp=datetime(2024, 1, 1),
        ...     index=10,
        ...     price=1825.5,
        ...     swing_type="peak",
        ...     strategy_name="zigzag",
        ... )
        >>> point.swing_type
        'peak'
    """

    point_id: int
    timestamp: datetime
    index: int
    price: float
    swing_type: str
    amplitude_to_next: Optional[float] = None
    duration_to_next: Optional[int] = None
    strategy_name: str = ""
    strategy_params: Dict[str, Any] = None
    confirmation_index: Optional[int] = None

    def __post_init__(self) -> None:
        if self.strategy_params is None:
            self.strategy_params = {}


@dataclass
class SwingContext:
    """Global context for swing points calculated on the full dataset.

    The context stores swing points detected by a strategy once and allows
    efficient slicing for individual zones without recomputing the strategy.

    Attributes:
        swing_points: Chronologically ordered list of :class:`SwingPoint` objects.
        indices: Sorted NumPy array of integer positions for fast slicing.
        full_data_length: Number of rows in the original dataset.
        strategy_name: Name of the strategy that produced the swings.
        strategy_params: Parameters of the strategy for traceability.

    Example:
        >>> context = SwingContext(
        ...     swing_points=[
        ...         SwingPoint(0, datetime(2024, 1, 1), 5, 1800.0, 'peak'),
        ...         SwingPoint(1, datetime(2024, 1, 2), 15, 1750.0, 'trough'),
        ...     ],
        ...     indices=np.array([5, 15]),
        ...     full_data_length=100,
        ...     strategy_name='zigzag',
        ...     strategy_params={'deviation': 0.05},
        ... )
        >>> [point.index for point in context.slice(0, 20)]
        [5, 15]
    """

    swing_points: List[SwingPoint]
    indices: np.ndarray
    full_data_length: int
    strategy_name: str
    strategy_params: Dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.indices, np.ndarray):
            self.indices = np.asarray(self.indices, dtype=int)
        if self.indices.ndim != 1:
            raise ValueError("SwingContext.indices must be a one-dimensional array")
        if len(self.indices) != len(self.swing_points):
            raise ValueError(
                "SwingContext.indices must have the same length as swing_points"
            )

    def slice(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """Return swing points for the given zone range with neighbor padding.

        Args:
            start_idx: Inclusive start index of the zone.
            end_idx: Inclusive end index of the zone.

        Returns:
            List of swing points that fall inside the zone boundaries including
            one neighboring swing point on each side (when available) to keep
            swing amplitudes intact.
        """

        if not self.swing_points:
            return []

        left = bisect_left(self.indices, start_idx)
        right = bisect_right(self.indices, end_idx)

        left_with_neighbor = max(0, left - 1)
        right_with_neighbor = min(len(self.swing_points), right + 1)

        return self.swing_points[left_with_neighbor:right_with_neighbor]

    def get_swings_for_zone(self, zone: "ZoneInfo") -> List[SwingPoint]:
        """Convenience helper to slice swings for the provided zone."""

        return self.slice(zone.start_idx, zone.end_idx)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the context for caching or persistence layers."""

        return {
            "swing_points": [
                {
                    "point_id": sp.point_id,
                    "timestamp": sp.timestamp.isoformat(),
                    "index": sp.index,
                    "price": sp.price,
                    "swing_type": sp.swing_type,
                    "amplitude_to_next": sp.amplitude_to_next,
                    "duration_to_next": sp.duration_to_next,
                    "strategy_name": sp.strategy_name,
                    "strategy_params": sp.strategy_params,
                    "confirmation_index": sp.confirmation_index,
                }
                for sp in self.swing_points
            ],
            "indices": self.indices.tolist(),
            "full_data_length": self.full_data_length,
            "strategy_name": self.strategy_name,
            "strategy_params": self.strategy_params,
        }


@dataclass(frozen=True)
class ZoneType:
    """Declared description of one kind of zone a detection strategy can emit.

    A zone type used to be a bare string, and every universal layer downstream
    discriminated on that string: ``if zone_type == 'bull'``. Three independent
    assumptions were fused into that single comparison — that there are exactly
    two types, that they are mutually opposite, and that they are spelled
    ``bull``/``bear``. A threshold or regime detector therefore produced zones
    correctly and then lost its direction metrics, its Markov chain and its
    hypothesis tests (analysis: ``devref/gaps/zone_types/``).

    The rule this type exists to enforce: **a consumer needs the declared
    properties of a zone type, not its name.** Names are an open vocabulary —
    ``bull``, ``overbought``, ``regime_a``, whatever the domain invents.
    Properties are a closed one, and that is exactly what lets universal code
    work without knowing any names.

    Attributes:
        name: The label carried by :attr:`ZoneInfo.type`. Open vocabulary.
        polarity: Where the zone sits on the axis of **the series it was detected
            on** — ``+1`` elevated (MACD histogram above zero, RSI above the upper
            threshold, volatility high), ``-1`` depressed, ``0`` a declared neutral
            band, ``None`` the axis is not ordered and directional maths does not
            apply to this type.

            Deliberately *not* "price direction": ``bull`` = "price rises" is a
            MACD assumption, false for RSI ``overbought`` and meaningless for a
            volatility regime.

            ``None`` means *declared absence of direction*, not "unknown". A
            consumer must react to it explicitly — skip the metric and say so.
            Silently returning ``None`` is the same defect, only quieter.
        counterpart: Name of the contrasting type, when one exists. Hypothesis
            tests compare a **pair**, and which type pairs with which is knowledge
            the producer has. Left unset it can be derived (see
            :meth:`ZoneVocabulary.counterpart_of`), but derivation is ambiguous as
            soon as a sign is represented by more than one type
            (``strong_bull``/``weak_bull``), which is precisely the case this
            abstraction exists to support.
        label: Human-readable caption for charts. Defaults to :attr:`name`.

    Example:
        >>> ZoneType('overbought', polarity=+1, counterpart='oversold')
        ZoneType(name='overbought', polarity=1, counterpart='oversold', label=None)
    """

    name: str
    polarity: Optional[int] = None
    counterpart: Optional[str] = None
    label: Optional[str] = None

    _VALID_POLARITIES = (None, -1, 0, 1)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"ZoneType.name must be a non-empty string, got {self.name!r}")
        # Проверка по типу, а не только по значению: `True == 1` и `1.0 == 1`,
        # поэтому одного `in` мало — булев флаг или float молча прошли бы за
        # объявленную полярность.
        valid = (
            self.polarity is None
            or (type(self.polarity) is int and self.polarity in (-1, 0, 1))
        )
        if not valid:
            raise ValueError(
                f"ZoneType({self.name!r}).polarity must be one of "
                f"{self._VALID_POLARITIES} as an int, got {self.polarity!r} "
                f"({type(self.polarity).__name__}). The vocabulary of properties is "
                "closed on purpose: it is what universal layers discriminate on."
            )

    @property
    def display_label(self) -> str:
        """Caption for charts and reports."""
        return self.label or self.name

    @property
    def is_directional(self) -> bool:
        """True when directional maths (drawdown vs rally, runs test) applies."""
        return self.polarity in (-1, 1)

    @classmethod
    def coerce(cls, value: Union[str, "ZoneType"]) -> "ZoneType":
        """Accept a plain name or a descriptor.

        A bare string is lifted to a descriptor with no declared properties. Such
        a type still detects zones, but universal layers will report directional
        analyses as not applicable rather than guessing — degradation is explicit,
        not silent.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(name=value)
        raise TypeError(
            f"zone type must be a str or ZoneType, got {type(value).__name__}: {value!r}"
        )


@dataclass(frozen=True)
class ZoneVocabulary:
    """The set of zone types a strategy declares, with lookups for consumers.

    An **empty** vocabulary is not "no zones"; it means the strategy does not
    declare its types statically because they are determined at runtime — from
    the imported data (``preloaded``) or from the caller's rules (``combined``).
    Consumers must read :attr:`is_declared` and refrain from filtering, rather
    than treating emptiness as an empty allow-list.
    """

    types: Tuple[ZoneType, ...] = ()

    def __post_init__(self):
        seen = [t.name for t in self.types]
        duplicates = {n for n in seen if seen.count(n) > 1}
        if duplicates:
            raise ValueError(f"duplicate zone type names in vocabulary: {sorted(duplicates)}")

    @classmethod
    def coerce(cls, values: Optional[Iterable[Union[str, ZoneType]]]) -> "ZoneVocabulary":
        """Build from a list of names and/or descriptors; ``None`` yields empty."""
        if values is None:
            return cls()
        if isinstance(values, cls):
            return values
        return cls(types=tuple(ZoneType.coerce(v) for v in values))

    @property
    def is_declared(self) -> bool:
        """False when the vocabulary is determined at runtime, not statically."""
        return bool(self.types)

    def names(self) -> List[str]:
        """Declared type names, in declaration order."""
        return [t.name for t in self.types]

    def get(self, name: str) -> Optional[ZoneType]:
        """Descriptor for ``name``, or ``None`` if this vocabulary does not declare it."""
        for zone_type in self.types:
            if zone_type.name == name:
                return zone_type
        return None

    def polarity_of(self, name: str) -> Optional[int]:
        """Declared polarity of ``name``; ``None`` if undeclared or non-directional."""
        zone_type = self.get(name)
        return zone_type.polarity if zone_type else None

    def counterpart_of(self, name: str) -> Optional[str]:
        """Contrasting type for ``name`` — declared, else derived.

        Derivation is the fallback and applies only when the opposite polarity is
        represented by exactly one type. With ``strong_bull``/``weak_bull`` both at
        ``+1`` there is no single answer, and this returns ``None`` instead of
        picking one.
        """
        zone_type = self.get(name)
        if zone_type is None:
            return None
        if zone_type.counterpart is not None:
            return zone_type.counterpart
        if not zone_type.is_directional:
            return None
        opposite = [t.name for t in self.types if t.polarity == -zone_type.polarity]
        return opposite[0] if len(opposite) == 1 else None

    def contrast_pairs(self) -> List[Tuple[str, str]]:
        """Mutually contrasting pairs, each listed once, deterministically ordered."""
        pairs = set()
        for zone_type in self.types:
            other = self.counterpart_of(zone_type.name)
            if other and self.counterpart_of(other) == zone_type.name:
                pairs.add(tuple(sorted((zone_type.name, other))))
        return sorted(pairs)


@dataclass
class ZoneInfo:
    """Normalized representation of a detected zone.

    Attributes:
        zone_id: Unique identifier of the zone within the analysis batch.
        type: Zone type label (``"bull"``, ``"bear"``, ``"oversold"``, etc.). An open
            vocabulary: the detection strategy names its own types and declares what
            they mean via :class:`ZoneType`. Consumers must discriminate on the
            declared properties, never on this string.
        start_idx: Inclusive positional index (``iloc``) at which the zone begins.
        end_idx: Inclusive positional index (``iloc``) at which the zone ends.
        start_time: Timestamp of the first bar belonging to the zone.
        end_time: Timestamp of the last bar belonging to the zone.
        duration: Number of bars in the zone.
        data: Slice of the source dataframe containing OHLCV columns (plus indicators).
        features: Optional dictionary of computed feature metrics (populated by analyzers).
        indicator_context: Optional metadata produced by the detection strategy
            (strategy name, indicator columns, thresholds, etc.).
        swing_context: Optional :class:`SwingContext` providing access to global swings.

    Notes:
        * ``indicator_context`` is set by the detection stage; the pipeline does not mutate it.
        * ``swing_context`` is injected in global swing mode and remains ``None`` for per-zone mode.
    """
    zone_id: int
    type: str
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None
    indicator_context: Optional[Dict[str, Any]] = None
    swing_context: Optional[SwingContext] = None
    
    def __post_init__(self):
        """Ensure ``indicator_context`` is always a dictionary."""
        if self.indicator_context is None:
            self.indicator_context = {}

    def get_zone_swings(self) -> List[SwingPoint]:
        """Return swing points for the zone using the attached swing context.

        Returns:
            List of :class:`SwingPoint` extracted from the associated
            :class:`SwingContext`. Returns an empty list if no context is
            attached.

        Example:
            >>> swings = zone.get_zone_swings()
            >>> len(swings)
            4
        """

        if self.swing_context is None:
            return []
        return self.swing_context.get_swings_for_zone(self)
    
    def get_primary_indicator_column(self) -> Optional[str]:
        """Return the primary indicator column name stored in the detector context."""
        return self.indicator_context.get('detection_indicator')
    
    def get_signal_line_column(self) -> Optional[str]:
        """Return the secondary indicator (signal line) column name if available."""
        return self.indicator_context.get('signal_line')
    
    def to_analyzer_format(self) -> Dict[str, Any]:
        """Convert the zone into a dictionary consumed by feature analyzers."""
        return {
            'zone_id': self.zone_id,
            'type': self.type,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'data': self.data,
            'indicator_context': self.indicator_context,  # Pass to analyzers
            'swing_context': self.swing_context,
            **(self.features or {})
        }



def _schema_from(payload):
    """Rebuild a :class:`ColumnSchema` from a serialized result.

    Imported lazily: ``bquant.indicators`` pulls in the whole indicator stack, and
    the zone models are imported by it in turn.
    """
    if not payload:
        return None
    from ...indicators.schema import ColumnSchema

    return ColumnSchema.from_dict(payload)

@dataclass
class ZoneAnalysisResult:
    """
    Результат анализа зон.
    
    Attributes:
        zones: Список обнаруженных зон
        statistics: Статистические метрики зон
        hypothesis_tests: Результаты статистических тестов
        clustering: Результаты кластеризации (опционально)
        sequence_analysis: Анализ последовательностей зон (опционально)
        regression_results: Результаты регрессионного анализа (опционально)
        validation_results: Результаты валидации (опционально)
        data: Исходный DataFrame с данными (опционально)
        metadata: Дополнительные метаданные
    """
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    regression_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    #: ``(indicator, role) -> column`` for the indicators this analysis computed.
    #: Survives the merge into :attr:`data`, where the objects are gone and only
    #: strings remain — which is exactly where the meaning of a column used to be
    #: lost. Lets a consumer ask for "the histogram" instead of guessing
    #: ``'macd_hist'``. Empty when the caller supplied the indicator columns
    #: themselves, since nothing then declared what they mean.
    column_schema: Optional[Any] = None
    
    def save(
        self,
        filepath: Union[str, Path],
        format: str = 'pickle',
        compress: bool = False,
        include_data: bool = True,
    ) -> None:
        """Persist the analysis result to disk.

        Args:
            filepath: Destination path for the serialized payload.
            format: Output format (``"pickle"``, ``"json"``, or ``"parquet"``).
            compress: Enable gzip compression for pickle/parquet outputs.
            include_data: Include the full dataframe in the serialized payload.

        Examples:
            >>> result.save('results/zones.pkl')
            >>> result.save('results/zones.pkl.gz', compress=True)
            >>> result.save('results/zones.json', format='json', include_data=False)
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'pickle':
            self._save_pickle(filepath, compress, include_data)
        elif format == 'json':
            self._save_json(filepath, include_data)
        elif format == 'parquet':
            self._save_parquet(filepath, compress, include_data)
        else:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: 'pickle', 'json', 'parquet'"
            )
        
        logger.info(f"Saved ZoneAnalysisResult to {filepath} (format: {format})")
    
    def _save_pickle(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Serialize the result using Python pickle."""
        # Temporarily drop the dataframe if it should not be serialized
        data_backup = None
        if not include_data and self.data is not None:
            data_backup = self.data
            self.data = None
        
        try:
            if compress:
                with gzip.open(filepath.with_suffix('.pkl.gz'), 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            # Restore dataframe reference after writing
            if data_backup is not None:
                self.data = data_backup
    
    def _save_json(self, filepath: Path, include_data: bool) -> None:
        """Serialize the result to JSON."""
        data_dict = self.to_dict(include_data=include_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
    
    def _save_parquet(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Serialize the result to a directory containing Parquet/JSON artifacts."""
        # Ensure output directory exists
        output_dir = filepath.with_suffix('.parquet')
        output_dir.mkdir(exist_ok=True)
        
        # Persist zones metadata
        zones_data = [self._zone_to_dict(z) for z in self.zones]
        zones_df = pd.DataFrame(zones_data)
        zones_df.to_parquet(output_dir / 'zones.parquet', compression='gzip' if compress else None)
        
        # Persist aggregate analysis outputs
        metadata = {
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'column_schema': self.column_schema.to_dict() if self.column_schema else None,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Persist raw dataframe if requested
        if include_data and self.data is not None:
            self.data.to_parquet(output_dir / 'data.parquet', compression='gzip' if compress else None)
    
    @classmethod
    def load(cls, 
             filepath: Union[str, Path],
             format: str = 'pickle') -> 'ZoneAnalysisResult':
        """Load a serialized analysis result from disk."""
        filepath = Path(filepath)
        
        if format == 'pickle':
            result = cls._load_pickle(filepath)
        elif format == 'json':
            result = cls._load_json(filepath)
        elif format == 'parquet':
            result = cls._load_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Loaded ZoneAnalysisResult from {filepath} (format: {format})")
        return result
    
    @classmethod
    def _load_pickle(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Internal helper that deserializes a pickle artifact."""
        # Auto-detect gzip compression
        if filepath.suffix == '.gz' or filepath.name.endswith('.pkl.gz'):
            with gzip.open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
    
    @classmethod
    def _load_json(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Internal helper that deserializes a JSON artifact."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
        
        return cls.from_dict(data_dict)
    
    @classmethod
    def _load_parquet(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Internal helper that deserializes a Parquet artifact."""
        parquet_dir = filepath.with_suffix('.parquet')
        
        # Загружаем зоны
        zones_df = pd.read_parquet(parquet_dir / 'zones.parquet')
        zones = [cls._zone_from_dict(row.to_dict()) for _, row in zones_df.iterrows()]
        
        # Загружаем метаданные
        with open(parquet_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        # Загружаем исходные данные если есть
        data_file = parquet_dir / 'data.parquet'
        data = pd.read_parquet(data_file) if data_file.exists() else None
        
        return cls(
            zones=zones,
            statistics=metadata['statistics'],
            hypothesis_tests=metadata['hypothesis_tests'],
            clustering=metadata.get('clustering'),
            sequence_analysis=metadata.get('sequence_analysis'),
            column_schema=_schema_from(metadata.get('column_schema')),
            regression_results=metadata.get('regression_results'),
            validation_results=metadata.get('validation_results'),
            data=data,
            metadata=metadata.get('metadata', {})
        )
    
    def to_dict(self, include_data: bool = False) -> Dict[str, Any]:
        """Convert the result into a JSON-serializable dictionary."""
        result = {
            'zones': [self._zone_to_dict(z) for z in self.zones],
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'column_schema': self.column_schema.to_dict() if self.column_schema else None,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        if include_data and self.data is not None:
            # This may be large; use with caution
            result['data'] = self.data.to_dict('records')
        
        return result
    
    @classmethod
    def from_dict(cls, data_dict: Dict[str, Any]) -> 'ZoneAnalysisResult':
        """Reconstruct an instance from a dictionary representation."""
        zones = [cls._zone_from_dict(z) for z in data_dict['zones']]
        
        # Rebuild dataframe when present
        data = None
        if 'data' in data_dict and data_dict['data']:
            data = pd.DataFrame(data_dict['data'])
        
        return cls(
            zones=zones,
            statistics=data_dict['statistics'],
            hypothesis_tests=data_dict['hypothesis_tests'],
            clustering=data_dict.get('clustering'),
            sequence_analysis=data_dict.get('sequence_analysis'),
            column_schema=_schema_from(data_dict.get('column_schema')),
            regression_results=data_dict.get('regression_results'),
            validation_results=data_dict.get('validation_results'),
            data=data,
            metadata=data_dict.get('metadata', {})
        )
    
    @staticmethod
    def _zone_to_dict(zone: ZoneInfo) -> Dict[str, Any]:
        """Convert a :class:`ZoneInfo` into a serializable dictionary."""
        return {
            'zone_id': zone.zone_id,
            'type': zone.type,
            'start_idx': zone.start_idx,
            'end_idx': zone.end_idx,
            'start_time': zone.start_time.isoformat(),
            'end_time': zone.end_time.isoformat(),
            'duration': zone.duration,
            'features': zone.features,
            'indicator_context': zone.indicator_context  # v2.1: Save indicator context
            # data не сохраняем в dict (слишком большой)
        }
    
    @staticmethod
    def _zone_from_dict(zone_dict: Dict[str, Any]) -> ZoneInfo:
        """Recreate a :class:`ZoneInfo` from its dictionary representation."""
        return ZoneInfo(
            zone_id=zone_dict['zone_id'],
            type=zone_dict['type'],
            start_idx=zone_dict['start_idx'],
            end_idx=zone_dict['end_idx'],
            start_time=datetime.fromisoformat(zone_dict['start_time']),
            end_time=datetime.fromisoformat(zone_dict['end_time']),
            duration=zone_dict['duration'],
            data=pd.DataFrame(),  # Пустой DataFrame, нужно загружать отдельно
            features=zone_dict.get('features'),
            indicator_context=zone_dict.get('indicator_context')  # v2.1: Load indicator context
        )
    
    def visualize(self,
                  mode: str = 'overview',
                  zone_id: Optional[int] = None,
                  date_range: Optional[Tuple[datetime, datetime]] = None,
                  symbol: Optional[str] = None,
                  timeframe: Optional[str] = None,
                  source: Optional[str] = None,
                  **kwargs):
        """Render interactive visualizations for the analysis result.

        Args:
            mode: Visualization mode. Supported values are ``"overview"`` (price
                chart with all zones), ``"detail"`` (single-zone view), ``"comparison"``
                (side-by-side comparison), and ``"statistics"`` (aggregated metrics).
            zone_id: Zone identifier required for ``mode="detail"``.
            date_range: Optional datetime tuple used by comparison/overview modes.
            symbol: Optional symbol override passed to the visualizer metadata.
            timeframe: Optional timeframe override passed to the visualizer metadata.
            source: Optional data-source label passed to the visualizer metadata.
            **kwargs: Additional keyword arguments forwarded to ``ZoneVisualizer``.

        Returns:
            Visualization object (Plotly figure or matplotlib figure depending
            on the active backend).

        Raises:
            ImportError: If visualization dependencies are missing.
            ValueError: If required data is unavailable for the chosen mode.

        Examples:
            >>> result.visualize('overview', title='Zones vs Price')
            >>> result.visualize('detail', zone_id=3, context_bars=20)
            >>> result.visualize('comparison', max_zones=5)
            >>> result.visualize('statistics', title='Zone Metrics')
        """
        try:
            visualization_module = import_module('bquant.visualization')
            ZoneVisualizer = getattr(visualization_module, 'ZoneVisualizer')
        except (ImportError, AttributeError):
            try:
                zones_module = import_module('bquant.visualization.zones')
                ZoneVisualizer = getattr(zones_module, 'ZoneVisualizer')
            except (ImportError, AttributeError) as exc:
                raise ImportError(
                    "ZoneVisualizer is not available. Install optional "
                    "visualization dependencies (e.g. 'bquant[viz]') "
                    "to enable chart rendering."
                ) from exc

        if self.data is None or self.data.empty:
            raise ValueError("data not available in ZoneAnalysisResult")

        if not self.zones and mode in {'overview', 'detail', 'comparison', 'statistics'}:
            raise ValueError("zones data is empty - nothing to visualize")

        visualizer_backend = kwargs.pop('backend', None)
        visualizer_config = kwargs.pop('visualizer_config', {})
        visualizer_kwargs = {**visualizer_config}
        if visualizer_backend is not None:
            visualizer_kwargs['backend'] = visualizer_backend

        visualizer = ZoneVisualizer(**visualizer_kwargs)
        
        # Собираем метаинформацию из параметров или metadata
        chart_info = {}
        if symbol or self.metadata.get('symbol'):
            chart_info['symbol'] = symbol or self.metadata.get('symbol')
        if timeframe or self.metadata.get('timeframe'):
            chart_info['timeframe'] = timeframe or self.metadata.get('timeframe')
        if source or self.metadata.get('source'):
            chart_info['source'] = source or self.metadata.get('source')
        
        # Передаем chart_info в kwargs для visualizer
        if chart_info:
            kwargs['chart_info'] = chart_info

        if mode == 'overview':
            # Поддержка date_range для режима overview
            if date_range is not None:
                start_date, end_date = date_range
                # Границы приводим к представлению времени самих данных: наивная
                # `pd.Timestamp('2025-06-01')` рядом с tz-aware индексом давала голый
                # `TypeError` из pandas, по которому неясно, что чинить. Сэмплы идут
                # с зоной (`UTC+07:00`), так что случай обычный, а не экзотический.
                index_tz = getattr(self.data.index, 'tz', None)
                if index_tz is not None:
                    start_date = pd.Timestamp(start_date)
                    end_date = pd.Timestamp(end_date)
                    if start_date.tzinfo is None:
                        start_date = start_date.tz_localize(index_tz)
                    if end_date.tzinfo is None:
                        end_date = end_date.tz_localize(index_tz)
                # Фильтруем данные по датам
                filtered_data = self.data[
                    (self.data.index >= start_date) & (self.data.index <= end_date)
                ]
                # Фильтруем зоны, которые реально пересекаются с диапазоном данных
                # Зона должна НАЧАТЬСЯ до конца диапазона И ЗАКОНЧИТЬСЯ после начала диапазона
                # Исключаем зоны которые заканчиваются ДО ИЛИ РОВНО в начале диапазона
                filtered_zones = [
                    z for z in self.zones
                    if z.start_time < end_date and z.end_time > start_date
                ]
                return visualizer.plot_zones_on_price_chart(
                    filtered_data, filtered_zones, **kwargs
                )
            else:
                return visualizer.plot_zones_on_price_chart(
                    self.data, self.zones, **kwargs
                )

        if mode == 'detail':
            if zone_id is None:
                raise ValueError("zone_id required for detail mode")
            zone = next((z for z in self.zones if z.zone_id == zone_id), None)
            if zone is None:
                raise ValueError(f"Zone {zone_id} not found")
            return visualizer.plot_zone_detail(self.data, zone, **kwargs)

        if mode == 'comparison':
            return visualizer.plot_zones_comparison(
                self.data, self.zones, date_range=date_range, **kwargs
            )

        if mode == 'statistics':
            if not self.statistics:
                raise ValueError("statistics data is empty - cannot build visualization")
            return visualizer.plot_zones_analysis(
                self.zones, self.statistics, **kwargs
            )

        raise ValueError(
            f"Unknown mode: {mode}. "
            f"Available: 'overview', 'detail', 'comparison', 'statistics'"
        )


# Экспорт
__all__ = [
    'ZoneInfo',
    'ZoneAnalysisResult',
    'SwingPoint',
    'SwingContext',
    'ZoneType',
    'ZoneVocabulary'
]

