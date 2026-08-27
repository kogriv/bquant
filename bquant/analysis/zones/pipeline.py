"""
Zone Analysis Pipeline

This module implements the orchestration layer for zone analytics and exposes a
fluent builder API.

Components:
* ``IndicatorSpec`` – which indicator to compute, and with what parameters.
* ``ZoneAnalysisConfig`` – full pipeline configuration container.
* ``ZoneAnalysisPipeline`` – executes the workflow (optionally with caching).
* ``ZoneAnalysisBuilder`` – fluent API entry point used by ``analyze_zones``.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional
import pandas as pd
import json

from bquant.indicators import IndicatorFactory
from bquant.indicators.schema import ColumnSchema
from bquant.indicators.base import IndicatorResult
from bquant.core.logging_config import get_logger
from bquant.core.cache import get_cache_manager
from bquant.core.config import DEFAULT_SWING_PRESET, SWING_PRESETS
from .strategies.swing.thresholds import _AdaptiveSwingStrategy

from .detection import ZoneDetectionRegistry, ZoneDetectionConfig
from .analyzer import UniversalZoneAnalyzer
from .models import ZoneInfo, ZoneAnalysisResult, SwingContext
from .cache import ZoneAnalysisCache
from .strategies.registry import StrategyRegistry
from .strategies.swing import (
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy,
    ZigZagSwingStrategy,
)

logger = get_logger(__name__)


_SWING_CLASS_TO_NAME = {
    ZigZagSwingStrategy: "zigzag",
    FindPeaksSwingStrategy: "find_peaks",
    PivotPointsSwingStrategy: "pivot_points",
}

# Bump whenever the schema/semantics of cached analysis output changes (new
# SwingPoint/ZoneInfo fields, changed swing computation, etc.), so that on-disk
# caches computed under an older schema are not silently served.
#   v2 (2026-07): SwingPoint.confirmation_index added (causal availability).
#   v3 (2026-07): confirmation_index now populated by find_peaks & pivot_points
#                 (previously only zigzag; changes cached swing output).
#   v4 (2026-08): find_peaks & pivot_points confirmation_index made replay-safe
#                 (G14) — distance-chain settling + first-swing warm-up hold.
#   v5 (2026-08): find_peaks auto prominence frozen on a warm-up window (G15) —
#                 changes the detected swing set, not only its confirmations.
#   v6 (2026-08): adaptive thresholds stop overwriting find_peaks' prominence with a
#                 relative value (G16); `peak_prominence` metadata key renamed.
#   v7 (2026-08): zone features carry start_idx/end_idx; sequence and hypothesis
#                 results derive from declared zone-type properties and count
#                 only transitions between adjacent zones (G20/G21); the
#                 asymmetry test key is now `contrast_asymmetry`.
#   v8 (2026-08): results carry a `column_schema` side-car mapping
#                 (indicator, role) -> column name (G8 stage C1).
#   v9 (2026-08): identity slugs changed for the preloaded indicator, which also
#                 declares roles now, so schema entries appear where v8 had none
#                 (G8 stage C2a). Column names themselves are unchanged.
#   v10 (2026-08): `run_regression=True` now yields regression results; the
#                 analyzer's import of ZoneRegressionAnalyzer was broken and
#                 swallowed, so v9 results have regression_results=None (G23).
#   v11 (2026-08): consumers address columns by role; zone feature metadata
#                 dropped the dead backward-compatibility aliases (G8 C2b-1).
#   v12 (2026-08): computed columns carry canonical names, slug + role
#                 (G8 stage C2b-2).
#   v13 (2026-08): detection returns the complete tiling — the length threshold
#                 moved out of detection into the aggregates (G21 variant c),
#                 so v12 results are missing the short zones entirely.
#   v14 (2026-08): zone feature names follow the role vocabulary rather than
#                 one indicator's name (`macd_amplitude` -> `line_amplitude`,
#                 `hist_*` -> `oscillator_*`), and the per-role metadata keys
#                 changed shape (`max_macd` -> `line_max`).
CACHE_SCHEMA_VERSION = 14


@dataclass
class IndicatorSpec:
    """Which indicator to compute, and with what parameters.

    Named `IndicatorConfig` until 2026-08-24, which collided with an unrelated
    public class of the same name in ``bquant.indicators.base`` — a different
    dataclass, with different fields, describing a *computed* indicator rather
    than a request to compute one. Two public classes sharing a name in one
    package is the same defect the column contract is about: the label carried
    no identity, and the reader had to guess which one was meant from context.

    The field was called ``params`` here and ``parameters`` there; it is
    ``parameters`` in both now.
    """
    source: Literal['preloaded', 'custom', 'pandas_ta', 'talib']
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneAnalysisConfig:
    """Complete configuration for the zone-analysis pipeline."""
    # Индикатор (None если уже в данных)
    indicator: Optional[IndicatorSpec] = None
    
    # Детекция зон (обязательно)
    zone_detection: ZoneDetectionConfig = None
    
    # Параметры анализа
    perform_clustering: bool = True
    n_clusters: int = 3
    run_regression: bool = False
    run_validation: bool = False
    swing_scope: Literal["per_zone", "global"] = "global"
    #: Порог длительности **отчётности**: зоны короче в агрегаты не берутся,
    #: но остаются в ``result.zones``. ``1`` = не отсеивать. Раньше стоял в
    #: детекции со значением ``2`` и рвал мощение молча.
    min_duration: int = 1

    def to_cache_key(self) -> str:
        """Serialize configuration into a stable JSON string for caching."""

        for attr_name, attr_value in self.__dict__.items():
            if callable(attr_value):
                raise ValueError(
                    f"ZoneAnalysisConfig field '{attr_name}' contains a callable. "
                    "Callables are not supported in cache keys. Convert the value "
                    "to a serializable representation before building the pipeline."
                )

        payload = {
            "indicator": asdict(self.indicator) if self.indicator else None,
            "zone_detection": asdict(self.zone_detection)
            if self.zone_detection
            else None,
            "perform_clustering": self.perform_clustering,
            "n_clusters": self.n_clusters,
            "run_regression": self.run_regression,
            "run_validation": self.run_validation,
            "swing_scope": self.swing_scope,
            "min_duration": self.min_duration,
            "schema_version": CACHE_SCHEMA_VERSION,
        }
        return json.dumps(payload, sort_keys=True, default=str)


class ZoneAnalysisPipeline:
    """
    Универсальный pipeline для анализа зон.
    
    ЕДИНСТВЕННЫЙ класс координации - НЕТ специализированных фасадов!
    Работает через конфигурацию - максимальная гибкость.
    
    Features:
    - Расчет индикатора через IndicatorFactory
    - Детекция зон через стратегии
    - Анализ через UniversalZoneAnalyzer
    - Автоматическое кэширование
    
    Example:
        config = ZoneAnalysisConfig(
            indicator=IndicatorSpec('custom', 'macd', {'fast': 12}),
            zone_detection=ZoneDetectionConfig(
                strategy_name='zero_crossing',
                rules={'indicator_role': 'hist'}
            )
        )
        pipeline = ZoneAnalysisPipeline(config, enable_cache=True)
        result = pipeline.run(df)
    """
    
    def __init__(self,
                 config: ZoneAnalysisConfig,
                 zone_analyzer: Optional[UniversalZoneAnalyzer] = None,
                 enable_cache: bool = True,
                 cache_ttl: int = 3600,
                 *,
                 strategy_auto_thresholds: bool = False,
                 auto_threshold_base_deviation: float = 0.01):
        """Initialize the pipeline with optional dependency overrides."""
        self.config = config
        self.analyzer = zone_analyzer or UniversalZoneAnalyzer()
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.cache_manager = get_cache_manager() if enable_cache else None
        self._cache = ZoneAnalysisCache(self.cache_manager) if enable_cache else None
        self.logger = get_logger(__name__)
        self.swing_strategies: Dict[str, Any] = {}
        self._active_swing_strategy: Optional[str] = self._detect_current_swing_strategy()
        self._swing_preset: str = DEFAULT_SWING_PRESET
        self.strategy_auto_thresholds = strategy_auto_thresholds
        self._auto_threshold_base_deviation = auto_threshold_base_deviation
        self._adaptive_swing_wrappers: Dict[str, _AdaptiveSwingStrategy] = {}
        self._swing_preset_params: Dict[str, Dict[str, Any]] = {}
        # Накапливается при расчёте индикаторов; переживает слияние в кадр и
        # уезжает в результат, чтобы потребитель спрашивал роль, а не строку.
        self.column_schema = ColumnSchema()
        self._apply_swing_preset(DEFAULT_SWING_PRESET, update_active=False)

    def run(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """Execute the end-to-end analysis workflow (with optional caching)."""
        cache_wrapper = self._get_cache_wrapper()
        if cache_wrapper is None:
            return self._run_without_cache(df)

        # Generate cache key based on configuration and data hash
        cache_key = self._generate_cache_key(df)

        # Attempt cache lookup
        cached_result = cache_wrapper.load(cache_key)
        if cached_result is not None:
            self.logger.info(f"Zone analysis result loaded from cache (key: {cache_key[:8]}...)")
            # Update metadata with fresh dataframe attributes if available
            if hasattr(df, 'attrs'):
                if 'symbol' in df.attrs:
                    cached_result.metadata['symbol'] = df.attrs['symbol']
                if 'timeframe' in df.attrs:
                    cached_result.metadata['timeframe'] = df.attrs['timeframe']
                if 'source' in df.attrs:
                    cached_result.metadata['source'] = df.attrs['source']
                if 'dataset_name' in df.attrs:
                    cached_result.metadata['dataset_name'] = df.attrs['dataset_name']
            return cached_result
        
        # Execute analysis and persist result to cache
        self.logger.info("Cache miss, running zone analysis...")
        result = self._run_without_cache(df)

        # Store result (in-memory and disk according to cache policy)
        cache_wrapper.save(cache_key, result, ttl=self.cache_ttl, disk=True)
        self.logger.info(f"Zone analysis result saved to cache (key: {cache_key[:8]}...)")

        return result
    
    def _run_without_cache(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """Execute the pipeline without consulting the cache."""

        # Step 1: prepare dataframe (indicator calculation, enrichment, etc.)
        df_prepared = self._prepare_data(df)

        # Step 2: run global swing calculation (optional)
        global_swing_context: Optional[SwingContext] = None
        if self.config.swing_scope == "global":
            try:
                global_swing_context = self._calculate_global_swings(df_prepared)
            except Exception as exc:  # noqa: BLE001 - стратегические исключения логируются
                self.logger.warning(
                    "Global swing calculation failed, falling back to per_zone mode: %s",
                    exc,
                )

        # Step 3: detect zones
        zones = self._detect_zones(df_prepared)

        # Step 4: inject swing context if available
        if global_swing_context is not None and zones:
            self._inject_swing_context(zones, global_swing_context)

        # Step 5: run feature analysis
        result = self._analyze_zones(zones, df_prepared)
        # Схема уезжает вместе с результатом: визуализатору и прочим потребителям
        # передают именно его, и они смогут спросить роль вместо строки.
        if self.column_schema:
            result.column_schema = self.column_schema
        return result

    def _get_active_swing_strategy(self) -> Optional[Any]:
        """Возвратить активную стратегию свингов, используемую анализатором зон."""

        features = getattr(self.analyzer, "features", None)
        if features is None:
            return None
        return getattr(features, "swing_strategy", None)

    def _calculate_global_swings(self, data: pd.DataFrame) -> SwingContext:
        """Рассчитать глобальные свинги на подготовленном наборе данных."""

        strategy = self._get_active_swing_strategy()
        if strategy is None:
            raise ValueError(
                "Swing strategy is not configured; cannot calculate global swings",
            )

        if not hasattr(strategy, "calculate_global"):
            raise ValueError(
                f"Swing strategy {strategy!r} does not support global calculation",
            )

        self.logger.info(
            "Calculating global swings with strategy: %s",
            strategy.__class__.__name__,
        )

        context = strategy.calculate_global(data)
        if not isinstance(context, SwingContext):
            raise TypeError(
                "Swing strategy returned unexpected context type: "
                f"{type(context).__name__}",
            )

        self.logger.info(
            "Global swings calculated: %d swing points detected",
            len(context.swing_points),
        )

        return context

    def _inject_swing_context(
        self, zones: List[ZoneInfo], swing_context: SwingContext
    ) -> None:
        """Attach the global swing context to all detected zones."""

        for zone in zones:
            zone.swing_context = swing_context

        self.logger.debug(
            "Injected swing_context into %d zones",
            len(zones),
        )
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich the dataframe with indicators when requested."""
        if self.config.indicator is None:
            return df  # Indicator already provided

        ind = self.config.indicator
        self.logger.info(f"Calculating indicator: {ind.source}.{ind.name}")

        indicator = IndicatorFactory.create(
            source=ind.source,
            indicator=ind.name,
            **ind.parameters,
        )

        result: IndicatorResult = indicator.calculate(df)

        # Схема-спутник: (индикатор, роль) -> фактическое имя колонки. После
        # слияния в кадр объекты исчезают и остаются строки — именно здесь знание
        # о том, что означает колонка, раньше и терялось. Схема переживает слияние
        # и позволяет потребителю спросить роль вместо того, чтобы угадывать имя.
        try:
            roles = indicator.get_output_roles()
            if roles:
                self.column_schema.register(indicator.get_indicator_id(), roles)
            else:
                self.logger.debug(
                    "Indicator %s.%s declares no output roles; role addressing "
                    "will be unavailable for it.", ind.source, ind.name,
                )
        except Exception as exc:  # pragma: no cover - чужой индикатор может не уметь
            self.logger.debug("Could not record the column schema: %s", exc)

        df_with_indicator = df.copy()
        # An indicator column whose name is already taken REPLACES the caller's data
        # (G17). This is easy to miss: the bundled TradingView sample ships its own
        # `macd` column, so computing MACD over it silently substitutes recomputed
        # values — and on that sample the final bar happens to agree, so a spot check
        # at the tail sees nothing. Warn rather than raise: some callers legitimately
        # recompute an indicator that arrived with the data. Silence is the defect,
        # not the overwrite itself.
        overwritten = [col for col in result.data.columns if col in df.columns]
        if overwritten:
            self.logger.warning(
                "Indicator %s.%s overwrites %d existing column(s) in the input data: "
                "%s. The original values are replaced and cannot be recovered from the "
                "result. Rename the incoming column(s), or drop them before analysis, "
                "if you meant to keep both.",
                ind.source,
                ind.name,
                len(overwritten),
                ", ".join(repr(c) for c in overwritten),
            )

        for col in result.data.columns:
            df_with_indicator[col] = result.data[col]

        if 'atr' not in df_with_indicator.columns:
            try:
                from bquant.data.processor import calculate_derived_indicators

                derived = calculate_derived_indicators(df_with_indicator)
                if 'atr' in derived.columns:
                    df_with_indicator['atr'] = derived['atr']
            except Exception as exc:
                self.logger.warning(f"Failed to add ATR: {exc}")

        return df_with_indicator
    
    def _resolve_indicator_role(self) -> None:
        """Turn every ``*_role`` detection rule into the column that holds it.

        ``indicator_role='hist'`` becomes ``indicator_col='macd_12_26_9__hist'``;
        ``line1_role``/``line2_role`` become ``line1_col``/``line2_col``. The
        pairing is by name rather than by a hardcoded list, so a new strategy
        gets role addressing for free by naming its rules ``<something>_col``.

        The pipeline knows the identity of the indicator because it created it,
        so a role is enough. Resolution happens here rather than in the builder
        because the schema is only populated once the indicator has run.
        """
        rules = self.config.zone_detection.rules
        # `*_role` — обычные публичные ключи правил, а не приватный канал
        # билдера: конфиг детекции собирают и напрямую, и такой код тоже вправе
        # адресоваться по роли, а не по имени колонки.
        role_keys = [key for key in list(rules) if key.endswith("_role")]
        for role_key in role_keys:
            role = rules.pop(role_key)
            if role is None:
                continue
            column_key = role_key[: -len("_role")] + "_col"
            if rules.get(column_key):
                raise ValueError(
                    f"pass either {role_key}= or {column_key}=, not both: they "
                    "address one series and can disagree."
                )

            column = self.column_schema.column(role)
            if column is None:
                available = self.column_schema.roles()
                raise ValueError(
                    f"cannot resolve {role_key}={role!r}: "
                    + (
                        f"the indicator in this analysis provides {list(available)}"
                        if available
                        else "no indicator in this analysis declares its output roles"
                    )
                    + f". Address the column by name with {column_key}= instead, or "
                    "declare the roles on the indicator."
                )

            self.logger.debug("Resolved %s=%r to column %r", role_key, role, column)
            rules[column_key] = column

    def _detect_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """Run the configured detection strategy and return zones."""
        self._resolve_indicator_role()
        detector = ZoneDetectionRegistry.get(
            self.config.zone_detection.strategy_name
        )
        return detector.detect_zones(df, self.config.zone_detection)
    
    def _analyze_zones(self, zones: List[ZoneInfo], df: pd.DataFrame) -> ZoneAnalysisResult:
        """Delegate zone feature extraction to :class:`UniversalZoneAnalyzer`."""
        return self.analyzer.analyze_zones(
            zones, df,
            perform_clustering=self.config.perform_clustering,
            n_clusters=self.config.n_clusters,
            run_regression=self.config.run_regression,
            run_validation=self.config.run_validation,
            column_schema=self.column_schema or None,
            min_duration=self.config.min_duration,
        )

    def _get_cache_wrapper(self) -> Optional[ZoneAnalysisCache]:
        """Return active cache wrapper or None if caching is disabled."""

        if not self.enable_cache or self.cache_manager is None:
            return None

        if self._cache is None or self._cache.cache_manager is not self.cache_manager:
            self._cache = ZoneAnalysisCache(self.cache_manager)

        return self._cache

    def _generate_cache_key(self, df: pd.DataFrame) -> str:
        """Generate a deterministic cache key based on configuration and data."""
        cache_wrapper = self._get_cache_wrapper()
        if cache_wrapper is None:
            raise RuntimeError("Caching is not enabled for this pipeline")

        data_hash = ZoneAnalysisCache.compute_data_hash(df)
        config_signature = self.config.to_cache_key()
        swing_signature = ZoneAnalysisCache.swing_signature(
            {
                "swing": self._serialize_swing_configuration(),
                "swing_scope": self.config.swing_scope,
            }
        )

        return cache_wrapper.generate_cache_key(
            data_hash,
            config_signature,
            swing_signature,
        )

    def with_swing_preset(self, name: str) -> "ZoneAnalysisPipeline":
        """Reconfigure swing strategies using a named preset."""

        self._apply_swing_preset(name, update_active=True)
        self._swing_preset = name
        return self

    def with_auto_swing_thresholds(
        self, enable: bool = True, *, base_deviation: Optional[float] = None
    ) -> "ZoneAnalysisPipeline":
        """Toggle adaptive swing threshold calculation."""

        self.strategy_auto_thresholds = enable
        if base_deviation is not None:
            self._auto_threshold_base_deviation = base_deviation
        self._rebuild_adaptive_wrappers()
        self._update_feature_swing_strategy()
        return self

    def invalidate_cache(self, df: pd.DataFrame) -> None:
        """Invalidate cached results for the given dataset."""
        cache_wrapper = self._get_cache_wrapper()
        if cache_wrapper is None:
            return

        cache_key = self._generate_cache_key(df)
        cache_wrapper.invalidate(cache_key)
        self.logger.info(f"Cache invalidated for key: {cache_key[:8]}...")

    def _strategy_name_from_instance(self, strategy: Any) -> Optional[str]:
        for cls, name in _SWING_CLASS_TO_NAME.items():
            if isinstance(strategy, cls):
                return name
        base_name = getattr(strategy, "base_strategy_name", None)
        if isinstance(base_name, str):
            return base_name
        return None

    def _detect_current_swing_strategy(self) -> Optional[str]:
        features = getattr(self.analyzer, "features", None)
        if features is None:
            return None
        strategy = getattr(features, "swing_strategy", None)
        return self._strategy_name_from_instance(strategy)

    def _rebuild_adaptive_wrappers(self) -> None:
        if not self.strategy_auto_thresholds:
            self._adaptive_swing_wrappers = {}
            return

        wrappers: Dict[str, _AdaptiveSwingStrategy] = {}
        for strategy_name, params in self._swing_preset_params.items():
            wrappers[strategy_name] = _AdaptiveSwingStrategy(
                strategy_name,
                params,
                base_deviation=self._auto_threshold_base_deviation,
            )
        self._adaptive_swing_wrappers = wrappers

    def _update_feature_swing_strategy(self) -> None:
        features = getattr(self.analyzer, "features", None)
        if features is None:
            return

        if not self._active_swing_strategy:
            return

        if (
            self.strategy_auto_thresholds
            and self._active_swing_strategy in self._adaptive_swing_wrappers
        ):
            features.swing_strategy = self._adaptive_swing_wrappers[
                self._active_swing_strategy
            ]
        elif self._active_swing_strategy in self.swing_strategies:
            features.swing_strategy = self.swing_strategies[
                self._active_swing_strategy
            ]

    def _serialize_swing_configuration(self) -> Dict[str, Any]:
        """Return JSON-serializable snapshot of swing-related settings."""

        strategies = {}
        for name, strategy in sorted(self.swing_strategies.items()):
            if hasattr(strategy, "config_hash"):
                strategies[name] = strategy.config_hash()
            else:
                strategies[name] = {"repr": repr(strategy)}

        preset_params = {
            name: dict(params)
            for name, params in sorted(self._swing_preset_params.items())
        }

        config: Dict[str, Any] = {
            "preset": self._swing_preset,
            "active_strategy": self._active_swing_strategy,
            "strategy_auto_thresholds": self.strategy_auto_thresholds,
            "auto_threshold_base_deviation": self._auto_threshold_base_deviation,
            "strategies": strategies,
            "preset_params": preset_params,
        }

        if self.strategy_auto_thresholds:
            config["adaptive_wrappers"] = {
                name: wrapper.config_hash()
                for name, wrapper in sorted(self._adaptive_swing_wrappers.items())
            }

        return config

    def _apply_swing_preset(self, name: str, *, update_active: bool) -> None:
        if name not in SWING_PRESETS:
            raise KeyError(f"Unknown swing preset: {name}")

        preset = SWING_PRESETS[name]
        preset_values = {
            "zigzag": dict(preset.zigzag),
            "find_peaks": dict(preset.find_peaks),
            "pivot_points": dict(preset.pivot_points),
        }
        self._swing_preset_params = {key: dict(value) for key, value in preset_values.items()}

        strategies: Dict[str, Any] = {}
        for strategy_name, params in preset_values.items():
            strategies[strategy_name] = StrategyRegistry.get_swing_strategy(
                strategy_name, **params
            )

        self.swing_strategies = strategies
        self._rebuild_adaptive_wrappers()

        if update_active or self._active_swing_strategy is None:
            self._active_swing_strategy = self._detect_current_swing_strategy()

        self._update_feature_swing_strategy()


class ZoneAnalysisBuilder:
    """
    Fluent builder that constructs :class:`ZoneAnalysisPipeline` instances.

    Example:
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
            .detect_zones('zero_crossing', indicator_role='line')
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
    """
    
    def __init__(self, data: pd.DataFrame):
        """Initialize the builder with the source dataframe."""
        self.data = data
        self._indicator_config: Optional[IndicatorSpec] = None
        self._zone_detection_config: Optional[ZoneDetectionConfig] = None
        self._perform_clustering = True
        self._n_clusters = 3
        self._run_regression = False
        self._run_validation = False
        self._min_duration = 1
        self._enable_cache = True
        self._cache_ttl = 3600
        # v2.1: Analytical strategies configuration
        self._swing_strategy: Optional[str] = None
        self._shape_strategy: Optional[str] = None
        self._divergence_strategy: Optional[str] = None
        self._volatility_strategy: Optional[str] = None
        self._volume_strategy: Optional[str] = None
        self._swing_preset: Optional[str] = None
        self._auto_swing_thresholds = False
        self._swing_scope: Literal["per_zone", "global"] = "global"
        self.logger = get_logger(__name__)
    
    def with_indicator(self, 
                      source: str, 
                      name: str, 
                      **params) -> 'ZoneAnalysisBuilder':
        """Schedule indicator calculation as part of the pipeline."""
        self._indicator_config = IndicatorSpec(
            source=source,
            name=name,
            parameters=params
        )
        return self
    
    def detect_zones(
        self,
        strategy: str,
        zone_types: List[str] = None,
        indicator_role: Optional[str] = None,
        **rules,
    ) -> 'ZoneAnalysisBuilder':
        """Configure zone detection rules.

        There is no ``min_duration`` here any more: detection returns the
        complete tiling of the timeline, and the length threshold is a
        **reporting** filter — :meth:`analyze`. See ``devref/gaps/sequence/``.

        Args:
            strategy: Registered detection strategy name.
            zone_types: Restrict the result to these types; ``None`` = no filter.
            indicator_role: Address the series by **role** instead of by column
                name — ``indicator_role='hist'`` rather than
                ``indicator_col='macd_12_26_9__hist'``. The pipeline knows the
                identity of the indicator because it created it, so the role is
                enough to resolve the column. This is the point of the
                abstraction: the caller stops being obliged to know the string.

                Resolved at build time against the column schema; passing both
                this and ``indicator_col`` is an error, since they could disagree.
            **rules: Strategy-specific rules (``indicator_col``, thresholds, ...).
                Any rule named ``<x>_role`` is resolved the same way into
                ``<x>_col`` — so ``line_crossing`` takes ``line1_role='line'``
                and ``line2_role='signal'``.
        """
        if indicator_role is not None:
            if "indicator_col" in rules:
                raise ValueError(
                    "pass either indicator_role or indicator_col, not both: they "
                    "address the same series and could disagree"
                )
            rules = dict(rules)
            rules["indicator_role"] = indicator_role

        self._zone_detection_config = ZoneDetectionConfig(
            zone_types=zone_types,
            rules=rules,
            strategy_name=strategy
        )
        return self

    def analyze(self,
               clustering: bool = True,
               n_clusters: int = 3,
               regression: bool = False,
               validation: bool = False,
               min_duration: int = 1) -> 'ZoneAnalysisBuilder':
        """Toggle optional analysis stages.

        Args:
            clustering: Run zone clustering.
            n_clusters: Number of clusters to ask for.
            regression: Run the regression step.
            validation: Run the validation suite.
            min_duration: Length threshold for the **aggregates**. Zones shorter
                than this stay in ``result.zones`` with their features, but are
                left out of the statistics, hypothesis tests, sequence analysis,
                clustering and regression; ``result.metadata['duration_filter']``
                says how many zones and bars that was. ``1`` = keep everything,
                which is the only setting under which the zones tile the frame
                exactly.
        """
        self._perform_clustering = clustering
        self._n_clusters = n_clusters
        self._run_regression = regression
        self._run_validation = validation
        self._min_duration = min_duration
        return self
    
    def with_strategies(self,
                       swing: Optional[str] = None,
                       shape: Optional[str] = None,
                       divergence: Optional[str] = None,
                       volatility: Optional[str] = None,
                       volume: Optional[str] = None) -> 'ZoneAnalysisBuilder':
        """Configure analytical strategy names for feature extraction."""
        if isinstance(swing, (list, tuple)):
            raise ValueError(
                "Only one swing strategy is supported per analysis run. "
                "To compare multiple strategies, run separate pipelines "
                "or refer to multiswing.md."
            )
        self._swing_strategy = swing
        self._shape_strategy = shape
        self._divergence_strategy = divergence
        self._volatility_strategy = volatility
        self._volume_strategy = volume
        return self

    def with_swing_preset(self, name: str) -> 'ZoneAnalysisBuilder':
        """Specify swing strategy preset to apply before execution."""

        self._swing_preset = name
        return self

    def with_auto_swing_thresholds(
        self, enable: bool = True
    ) -> 'ZoneAnalysisBuilder':
        """Enable adaptive thresholds for swing strategies."""

        self._auto_swing_thresholds = enable
        return self

    def with_swing_scope(
        self, scope: Literal["per_zone", "global"]
    ) -> 'ZoneAnalysisBuilder':
        """Configure swing calculation scope (``"per_zone"`` or ``"global"``).

        Example:
            >>> (analyze_zones(df)
            ...     .detect_zones('preloaded', zones_data=zones_df)
            ...     .with_strategies(swing='zigzag')
            ...     .with_swing_scope('global')
            ...     .build())
        """

        if scope not in ("per_zone", "global"):
            raise ValueError(
                "Invalid swing_scope: {0}. Must be 'per_zone' or 'global'".format(scope)
            )

        self._swing_scope = scope
        self.logger.info("Swing calculation mode set to: %s", scope)
        return self

    def with_cache(self,
                   enable: bool = True,
                   ttl: int = 3600) -> 'ZoneAnalysisBuilder':
        """
        Настроить кэширование.
        
        Args:
            enable: Включить/выключить кэш
            ttl: Время жизни кэша в секундах
            
        Returns:
            self для цепочки вызовов
            
        Example:
            # С кэшем (по умолчанию)
            result = analyze_zones(df).detect_zones(...).build()
            
            # Без кэша
            result = (
                analyze_zones(df)
                .with_cache(enable=False)
                .detect_zones(...)
                .build()
            )
            
            # Кэш с TTL 2 часа
            result = (
                analyze_zones(df)
                .with_cache(ttl=7200)
                .detect_zones(...)
                .build()
            )
        """
        self._enable_cache = enable
        self._cache_ttl = ttl
        return self
    
    def build(self) -> ZoneAnalysisResult:
        """
        Выполнить pipeline и вернуть результат.
        
        Returns:
            ZoneAnalysisResult с полным анализом
            
        Raises:
            ValueError: Если детекция зон не настроена
        """
        if self._zone_detection_config is None:
            raise ValueError("Zone detection strategy not configured. Call detect_zones() first.")
        
        # Создаем конфигурацию
        config = ZoneAnalysisConfig(
            indicator=self._indicator_config,
            zone_detection=self._zone_detection_config,
            perform_clustering=self._perform_clustering,
            n_clusters=self._n_clusters,
            run_regression=self._run_regression,
            run_validation=self._run_validation,
            swing_scope=self._swing_scope,
            min_duration=self._min_duration,
        )
        
        # ✅ v2.1: Create custom analyzer if strategies are specified
        custom_analyzer = None
        if any([self._swing_strategy, self._shape_strategy, 
                self._divergence_strategy, self._volatility_strategy, 
                self._volume_strategy]):
            from .analyzer import UniversalZoneAnalyzer
            custom_analyzer = UniversalZoneAnalyzer(
                swing_strategy=self._swing_strategy,
                shape_strategy=self._shape_strategy,
                divergence_strategy=self._divergence_strategy,
                volatility_strategy=self._volatility_strategy,
                volume_strategy=self._volume_strategy
            )
            self.logger.debug(
                f"Using custom analyzer with strategies: "
                f"swing={self._swing_strategy}, shape={self._shape_strategy}, "
                f"divergence={self._divergence_strategy}, "
                f"volatility={self._volatility_strategy}, volume={self._volume_strategy}"
            )
        
        # Выполняем через pipeline с кэшированием
        pipeline = ZoneAnalysisPipeline(
            config,
            zone_analyzer=custom_analyzer,  # ✅ v2.1: Pass custom analyzer
            enable_cache=self._enable_cache,
            cache_ttl=self._cache_ttl,
            strategy_auto_thresholds=self._auto_swing_thresholds,
        )
        if self._swing_preset is not None:
            pipeline.with_swing_preset(self._swing_preset)
        if self._auto_swing_thresholds:
            pipeline.with_auto_swing_thresholds(True)
        return pipeline.run(self.data)


def analyze_zones(df: pd.DataFrame) -> ZoneAnalysisBuilder:
    """
    Создать builder для анализа зон.
    
    Fluent API entry point.
    
    Args:
        df: DataFrame с OHLCV данными
        
    Returns:
        ZoneAnalysisBuilder для построения цепочки
    
    Example:
        from bquant.analysis.zones import analyze_zones
        
        # Минимальный пример
        result = (
            analyze_zones(df)
            .detect_zones('zero_crossing', indicator_role='line')
            .build()
        )
        
        # Полный пример
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
            .detect_zones('zero_crossing', indicator_role='line')
            .analyze(clustering=True, n_clusters=3, regression=True)
            .with_cache(enable=True, ttl=7200)
            .build()
        )
        
        # Для RSI
        result = (
            analyze_zones(df)
            .with_indicator('pandas_ta', 'rsi', timeperiod=14)
            .detect_zones('threshold', 
                         indicator_col='rsi', 
                         upper_threshold=70, 
                         lower_threshold=30)
            .build()
        )
    """
    return ZoneAnalysisBuilder(df)


# Экспорт
__all__ = [
    'IndicatorSpec',
    'ZoneAnalysisConfig',
    'ZoneAnalysisPipeline',
    'ZoneAnalysisBuilder',
    'analyze_zones'
]

