"""
Zone Analysis Pipeline

Универсальный pipeline для анализа зон с fluent API.

Компоненты:
- IndicatorConfig: Конфигурация индикатора
- ZoneAnalysisConfig: Полная конфигурация pipeline
- ZoneAnalysisPipeline: Выполнение pipeline с кэшированием
- ZoneAnalysisBuilder: Fluent API для удобного построения
- analyze_zones(): Convenience функция - entry point
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional
import pandas as pd
import json

from bquant.indicators import IndicatorFactory
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


@dataclass
class IndicatorConfig:
    """
    Конфигурация индикатора (если нужно рассчитать).
    
    None означает что индикатор уже в данных.
    
    Attributes:
        source: Источник индикатора ('preloaded', 'custom', 'pandas_ta', 'talib')
        name: Название индикатора
        params: Параметры для расчета индикатора
    """
    source: Literal['preloaded', 'custom', 'pandas_ta', 'talib']
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneAnalysisConfig:
    """
    Полная конфигурация pipeline анализа зон.

    Attributes:
        indicator: Конфигурация индикатора (None если уже в данных)
        zone_detection: Конфигурация детекции зон (обязательно)
        perform_clustering: Выполнять ли кластеризацию
        n_clusters: Количество кластеров
        run_regression: Запустить регрессионный анализ
        run_validation: Запустить валидацию
        swing_scope: Режим расчёта свингов (``"per_zone"`` по умолчанию или
            ``"global"`` для глобального расчёта)
    """
    # Индикатор (None если уже в данных)
    indicator: Optional[IndicatorConfig] = None
    
    # Детекция зон (обязательно)
    zone_detection: ZoneDetectionConfig = None
    
    # Параметры анализа
    perform_clustering: bool = True
    n_clusters: int = 3
    run_regression: bool = False
    run_validation: bool = False
    swing_scope: Literal["per_zone", "global"] = "per_zone"

    def to_cache_key(self) -> str:
        """Serialize configuration into a stable JSON string for caching."""

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
            indicator=IndicatorConfig('custom', 'macd', {'fast': 12}),
            zone_detection=ZoneDetectionConfig(
                strategy_name='zero_crossing',
                rules={'indicator_col': 'macd_histogram'}
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
        """
        Инициализация pipeline.
        
        Args:
            config: Конфигурация pipeline
            zone_analyzer: Универсальный анализатор (DI)
            enable_cache: Включить кэширование результатов
            cache_ttl: Время жизни кэша в секундах (default: 1 час)
        """
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
        self._apply_swing_preset(DEFAULT_SWING_PRESET, update_active=False)

    def run(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """
        Выполнить полный pipeline анализа с кэшированием.

        Если enable_cache=True, результат будет сохранен в кэш
        (память + диск) для повторного использования.
        
        Args:
            df: DataFrame с OHLCV данными
            
        Returns:
            ZoneAnalysisResult с полным анализом
        """
        cache_wrapper = self._get_cache_wrapper()
        if cache_wrapper is None:
            return self._run_without_cache(df)

        # Генерируем ключ кэша на основе конфигурации и данных
        cache_key = self._generate_cache_key(df)

        # Проверяем кэш
        cached_result = cache_wrapper.load(cache_key)
        if cached_result is not None:
            self.logger.info(f"Zone analysis result loaded from cache (key: {cache_key[:8]}...)")
            # Обновляем метаданные из df.attrs (могли измениться после кэширования)
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
        
        # Выполняем анализ
        self.logger.info("Cache miss, running zone analysis...")
        result = self._run_without_cache(df)

        # Сохраняем в кэш (TTL по умолчанию, на диск)
        cache_wrapper.save(cache_key, result, ttl=self.cache_ttl, disk=True)
        self.logger.info(f"Zone analysis result saved to cache (key: {cache_key[:8]}...)")

        return result
    
    def _run_without_cache(self, df: pd.DataFrame) -> ZoneAnalysisResult:
        """
        Выполнить pipeline без кэширования.

        Обновлённый workflow (Phase 3):

        1. Подготовка данных и расчёт индикаторов.
        2. Глобальный расчёт свингов (если включён режим ``"global"``).
        3. Детекция зон на подготовленных данных.
        4. Инжекция глобального swing контекста в каждую зону.
        5. Анализ зон через ``UniversalZoneAnalyzer``.
        """

        # 1. Подготовка данных (расчёт индикатора)
        df_prepared = self._prepare_data(df)

        # 2. Глобальный расчёт свингов (опционально)
        global_swing_context: Optional[SwingContext] = None
        if self.config.swing_scope == "global":
            try:
                global_swing_context = self._calculate_global_swings(df_prepared)
            except Exception as exc:  # noqa: BLE001 - стратегические исключения логируются
                self.logger.warning(
                    "Global swing calculation failed, falling back to per_zone mode: %s",
                    exc,
                )

        # 3. Детекция зон
        zones = self._detect_zones(df_prepared)

        # 4. Инжекция глобального контекста в зоны (если доступен)
        if global_swing_context is not None and zones:
            self._inject_swing_context(zones, global_swing_context)

        # 5. Анализ зон
        return self._analyze_zones(zones, df_prepared)

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
        """Инжектировать глобальный swing контекст во все обнаруженные зоны."""

        for zone in zones:
            zone.swing_context = swing_context

        self.logger.debug(
            "Injected swing_context into %d zones",
            len(zones),
        )
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет индикатора через IndicatorFactory."""
        if self.config.indicator is None:
            return df  # Индикатор уже в данных
        
        ind = self.config.indicator
        self.logger.info(f"Calculating indicator: {ind.source}.{ind.name}")
        
        # Создаем через IndicatorFactory!
        indicator = IndicatorFactory.create(
            source=ind.source,
            indicator=ind.name,
            **ind.params
        )
        
        result: IndicatorResult = indicator.calculate(df)
        
        # Объединяем с исходными данными
        df_with_indicator = df.copy()
        for col in result.data.columns:
            df_with_indicator[col] = result.data[col]
        
        # Добавляем ATR для нормализации (если нужно)
        if 'atr' not in df_with_indicator.columns:
            try:
                from bquant.data.processor import calculate_derived_indicators
                derived = calculate_derived_indicators(df_with_indicator)
                if 'atr' in derived.columns:
                    df_with_indicator['atr'] = derived['atr']
            except Exception as e:
                self.logger.warning(f"Failed to add ATR: {e}")
        
        return df_with_indicator
    
    def _detect_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """Детекция зон через стратегию."""
        detector = ZoneDetectionRegistry.get(
            self.config.zone_detection.strategy_name
        )
        return detector.detect_zones(df, self.config.zone_detection)
    
    def _analyze_zones(self, zones: List[ZoneInfo], df: pd.DataFrame) -> ZoneAnalysisResult:
        """Анализ зон через UniversalZoneAnalyzer."""
        return self.analyzer.analyze_zones(
            zones, df,
            perform_clustering=self.config.perform_clustering,
            n_clusters=self.config.n_clusters,
            run_regression=self.config.run_regression,
            run_validation=self.config.run_validation
        )

    def _get_cache_wrapper(self) -> Optional[ZoneAnalysisCache]:
        """Return active cache wrapper or None if caching is disabled."""

        if not self.enable_cache or self.cache_manager is None:
            return None

        if self._cache is None or self._cache.cache_manager is not self.cache_manager:
            self._cache = ZoneAnalysisCache(self.cache_manager)

        return self._cache

    def _generate_cache_key(self, df: pd.DataFrame) -> str:
        """
        Генерация ключа кэша на основе конфигурации и данных.
        
        Ключ включает:
        - Хэш данных (OHLCV)
        - Конфигурацию индикатора
        - Конфигурацию детекции зон
        - Параметры анализа
        """
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
        """
        Инвалидировать кэш для конкретных данных.

        Args:
            df: DataFrame для которого нужно инвалидировать кэш
        """
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
    Fluent builder для анализа зон.
    
    Удобный интерфейс "через точку" для построения pipeline.
    Внутри создает ZoneAnalysisPipeline.
    
    Example:
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
            .detect_zones('zero_crossing', indicator_col='macd_histogram')
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Инициализация builder с данными.
        
        Args:
            data: DataFrame с OHLCV данными (+ опционально индикаторы)
        """
        self.data = data
        self._indicator_config: Optional[IndicatorConfig] = None
        self._zone_detection_config: Optional[ZoneDetectionConfig] = None
        self._perform_clustering = True
        self._n_clusters = 3
        self._run_regression = False
        self._run_validation = False
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
        self._swing_scope: Literal["per_zone", "global"] = "per_zone"
        self.logger = get_logger(__name__)
    
    def with_indicator(self, 
                      source: str, 
                      name: str, 
                      **params) -> 'ZoneAnalysisBuilder':
        """
        Добавить расчет индикатора в pipeline.
        
        Args:
            source: Источник ('preloaded', 'custom', 'pandas_ta', 'talib')
            name: Название индикатора
            **params: Параметры индикатора
        
        Returns:
            self для цепочки вызовов
        
        Example:
            .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
            .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
            .with_indicator('talib', 'rsi', timeperiod=14)
        """
        self._indicator_config = IndicatorConfig(
            source=source,
            name=name,
            params=params
        )
        return self
    
    def detect_zones(self, 
                    strategy: str, 
                    min_duration: int = 2,
                    zone_types: List[str] = None,
                    **rules) -> 'ZoneAnalysisBuilder':
        """
        Настроить детекцию зон.
        
        Args:
            strategy: Стратегия ('zero_crossing', 'line_crossing', 'threshold', 'preloaded', 'combined')
            min_duration: Минимальная длительность зоны
            zone_types: Типы зон для поиска (None = все для стратегии)
            **rules: Правила детекции (зависят от стратегии)
        
        Returns:
            self для цепочки вызовов
        
        Examples:
            .detect_zones('zero_crossing', indicator_col='macd_histogram')
            .detect_zones('threshold', indicator_col='rsi', upper_threshold=70, lower_threshold=30)
            .detect_zones('line_crossing', line1_col='close', line2_col='sma_20')
            .detect_zones('preloaded', zones_data='zones.csv')
        """
        self._zone_detection_config = ZoneDetectionConfig(
            min_duration=min_duration,
            zone_types=zone_types,
            rules=rules,
            strategy_name=strategy
        )
        return self
    
    def analyze(self,
               clustering: bool = True,
               n_clusters: int = 3,
               regression: bool = False,
               validation: bool = False) -> 'ZoneAnalysisBuilder':
        """
        Настроить параметры анализа.
        
        Args:
            clustering: Выполнять кластеризацию
            n_clusters: Количество кластеров
            regression: Запустить регрессионный анализ
            validation: Запустить валидацию
        
        Returns:
            self для цепочки вызовов
        
        Example:
            .analyze(clustering=True, n_clusters=4, regression=True)
        """
        self._perform_clustering = clustering
        self._n_clusters = n_clusters
        self._run_regression = regression
        self._run_validation = validation
        return self
    
    def with_strategies(self,
                       swing: Optional[str] = None,
                       shape: Optional[str] = None,
                       divergence: Optional[str] = None,
                       volatility: Optional[str] = None,
                       volume: Optional[str] = None) -> 'ZoneAnalysisBuilder':
        """
        Настроить analytical strategies для zone features extraction.
        
        v2.1 FEATURE: Configure strategies for swing analysis, shape analysis,
        divergence detection, volatility analysis, and volume analysis.
        
        Args:
            swing: Swing detection strategy name
                   - 'find_peaks': Detect peaks/troughs using scipy.signal.find_peaks
                   - 'zigzag': ZigZag indicator-based swing detection
                   - 'pivot_points': Classical pivot points detection
                   - None: Skip swing analysis (default)
            shape: Shape analysis strategy name
                   - 'statistical': Statistical shape metrics (skewness, kurtosis, etc.)
                   - None or custom strategy instance
            divergence: Divergence detection strategy name
                   - 'classic': Classic bullish/bearish divergence detection
                   - None or custom strategy instance
            volatility: Volatility analysis strategy name
                   - None or custom strategy instance
            volume: Volume analysis strategy name
                   - 'standard': Standard volume analysis (spikes, correlation, etc.)
                   - None or custom strategy instance
        
        Returns:
            self для цепочки вызовов
        
        Examples:
            # With swing analysis
            result = (
                analyze_zones(df)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_strategies(swing='find_peaks')
                .analyze(clustering=True)
                .build()
            )
            
            # With multiple strategies
            result = (
                analyze_zones(df)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_strategies(
                    swing='find_peaks',
                    shape='statistical',
                    divergence='classic',
                    volume='standard'
                )
                .analyze(clustering=True)
                .build()
            )
            
            # RSI with swing analysis
            result = (
                analyze_zones(df)
                .with_indicator('pandas_ta', 'rsi', period=14)
                .detect_zones('threshold', indicator_col='RSI_14', 
                             upper_threshold=70, lower_threshold=30)
                .with_strategies(swing='pivot_points')
                .build()
            )
        
        Note:
            Strategies are passed to UniversalZoneAnalyzer which creates
            specialized strategy instances (e.g., FindPeaksSwingStrategy,
            StatisticalShapeStrategy, etc.) based on the strategy names.
        """
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
            .detect_zones('zero_crossing', indicator_col='macd_histogram')
            .build()
        )
        
        # Полный пример
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
            .detect_zones('zero_crossing', indicator_col='macd_histogram')
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
    'IndicatorConfig',
    'ZoneAnalysisConfig',
    'ZoneAnalysisPipeline',
    'ZoneAnalysisBuilder',
    'analyze_zones'
]

