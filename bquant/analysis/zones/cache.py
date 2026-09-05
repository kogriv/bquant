"""Specialised caching helpers for zone analysis results."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
import hashlib
import json

import pandas as pd

from bquant import __version__
from bquant.core.logging_config import get_logger

from .models import ZoneAnalysisResult

if TYPE_CHECKING:
    from .pipeline import ZoneAnalysisConfig


class ZoneAnalysisCache:
    """Manage cached results for the zone analysis pipeline.

    The cache wrapper is responsible for generating stable cache keys that are
    aware of schema upgrades and for storing versioned payloads. Older cache
    entries are automatically invalidated when the schema version increases.
    """

    # v3 (issue #110): ZigZag swings now come from the non-repainting backtest=True
    # detector, so serialized swing sets / confirmation_index differ from v2.
    # v4 (G14): find_peaks confirmation waits for the distance-suppression chain to
    # settle, and both find_peaks and pivot_points hold the first swing back to the
    # second's confirmation — serialized confirmation_index values differ from v3.
    # v5 (G15): the find_peaks auto prominence is frozen on a warm-up window instead
    # of the whole observed range, so the detected swing set itself differs (strictly
    # additive), and confirmations are floored at the end of warm-up.
    # v6 (G16): the adaptive-threshold layer no longer overwrites find_peaks' prominence
    # with a relative value, so adaptive runs detect a different (smaller) swing set.
    # v7 (G20/G21): zone features carry start_idx/end_idx; sequence and hypothesis
    # results are computed from declared zone-type properties and only between
    # adjacent zones, so transitions, the Markov matrix, the runs test and the
    # hypothesis summary all differ. The asymmetry test key was renamed
    # bull_bear_asymmetry -> contrast_asymmetry.
    # v8 (G8 stage C1): the result carries a `column_schema` side-car recording
    # (indicator, role) -> column, so a cached result from v7 lacks it.
    # v9 (G8 stage C2a): identity slugs changed — the preloaded indicator no
    # longer renders a list through `str()` and no longer carries `source` as a
    # parameter — and it now declares roles, so results computed over
    # pre-calculated data carry schema entries where v8 had none. Column names
    # themselves are unchanged.
    # v10 (G23): regression actually runs — the analyzer used to import the
    # regression class from a module that does not export it, so
    # `run_regression=True` produced None. Cached v9 results carry that None.
    # v11 (G8 stage C2b-1): consumers resolve columns by role. Zone feature
    # metadata no longer carries the dead `hist_max`/`rsi_*`/`ao_*` aliases, so
    # a v10 result has keys a v11 result does not.
    # v12 (G8 stage C2b-2): computed columns are named canonically
    # (`macd_12_26_9__hist`), so a v11 result carries the old names throughout —
    # in `data`, in the schema and in every zone's frame.
    # v13 (G21 variant c): detection no longer drops short zones, so a v12
    # result is missing them — and its aggregates were computed over a zone
    # sequence with gaps in it.
    # v14 (2026-08): zone feature names follow the role vocabulary instead of one
    # indicator's name — `macd_amplitude` -> `line_amplitude`,
    # `hist_amplitude`/`hist_slope` -> `oscillator_*`, `correlation_price_hist` ->
    # `correlation_price_oscillator` — and the per-role metadata keys changed
    # shape (`max_macd` -> `line_max`). A v13 result carries the old keys.
    # v15 (G30): пайплайн ставит время на индекс на входе, поэтому границы зон —
    # `Timestamp`, а не позиции, если в кадре есть колонка времени. Кэш v14 хранит
    # результаты, посчитанные до нормализации: те же зоны, но с позициями в
    # `start_time`/`end_time`.
    # v16 (G36): в ключ вошла подпись стратегий метрик. До v15 `shape`,
    # `divergence`, `volatility` и `volume` в ключ не попадали вовсе, поэтому
    # записи v15 и раньше отвечают на вопрос «этот индикатор, эта детекция», не
    # различая, какие метрики просили посчитать. Такая запись может быть
    # посчитана без стратегии, которую спрашивают сейчас.
    # v17 (G35): в метаданных результата появился `swing_coverage` — сколько зон
    # получили хотя бы один свинг. Запись v16 его не содержит, и отличить «стратегия
    # ничего не нашла» от «поле ещё не считалось» по такой записи нельзя.
    # v18 (G34): `total_statistics` отдаёт распределение по фактическим типам зон
    # (`zones_by_type`, `ratios_by_type`), а `bull_*`/`bear_*` присутствуют только
    # у словаря, который эти типы содержит. Запись v17 несёт нули там, где деления
    # не существует.
    # v19 (G35, вторая половина): пресет свингов по умолчанию — `narrow_zone` вместо
    # прежнего `default` (переименован в `wide_zone`). Прогон без явного пресета даёт
    # другой набор свингов, а запись v18 посчитана по старому умолчанию.
    # v20 (G45): встроенные EMA и MACD больше не публикуют значения на неполном
    # окне. Голова ряда стала NaN, поэтому зоны, стоявшие целиком в прогреве
    # индикатора, исчезают — записи v19 посчитаны с ними.
    # v21 (G38): адаптивный слой больше не выставляет `min_amplitude_pct`. Записи v20,
    # сделанные с `with_auto_swing_thresholds(True)` для `find_peaks` и
    # `pivot_points`, содержат ноль свингов во всех зонах — порог стоял выше движения,
    # которое должен был пропускать. Теперь те же прогоны дают 36.4% и 49.4% покрытия.
    # v22 (G53): хэш данных берётся по всему кадру, а не по OHLC. Записи v21 могли
    # быть сохранены под ключом, общим для кадров с разными `RSI_14`, `volume` или
    # колонками combined-условий, — и отдавались на любой из них; а у find_peaks в
    # ключ не входил `prominence_warmup`.
    # v23 (G55): `.analyze(validation=True)` исполняется — `validation_results`
    # содержит out-of-sample проверку, `metadata['validation']` различает
    # `not_requested` / `executed` / `failed`. Записи v22 с `run_validation=True`
    # несут `None` и ключа в метаданных не имеют.
    # v24 (G56): `hypothesis_tests` — словарь `.results`, `regression_results` —
    # словари `to_dict()`, как у остальных разделов. Записи v23 несут объекты
    # `AnalysisResult`/`RegressionResult`, которых читатели больше не ждут.
    # v25 (G58): `ColumnSchema` ключует записи `source.slug`, а не `slug`, и
    # `IndicatorId.parameters` — `FrozenParameters`. Записи v24 несут схему,
    # неотличающую два источника с одним slug.
    CACHE_VERSION = 25

    def __init__(self, cache_manager: Optional[Any]) -> None:
        self._cache_manager = cache_manager
        self.logger = get_logger(f"{__name__}.ZoneAnalysisCache")

    @property
    def cache_manager(self) -> Optional[Any]:
        """Return underlying cache manager (used by pipeline helpers)."""

        return self._cache_manager

    def generate_cache_key(
        self,
        data_hash: str,
        config_signature: str,
        swing_signature: str,
        analyzer_signature: str,
    ) -> str:
        """Create a version-aware cache key.

        Every input that changes the result must appear here. ``analyzer_signature``
        is the fourth part precisely because it did not exist: the metric
        strategies reach the analyzer past :class:`ZoneAnalysisConfig`, so the key
        could not see them, and a run asking for volatility metrics silently
        received a cached result computed without them (G36).

        Args:
            data_hash: Hash of the OHLC price data.
            config_signature: JSON signature of :class:`ZoneAnalysisConfig`.
            swing_signature: JSON signature of swing configuration.
            analyzer_signature: JSON signature of the metric strategies the
                analyzer will run (shape, divergence, volatility, volume) and of
                the injected components themselves.

        Returns:
            Deterministic cache key string.
        """

        key_parts = [
            f"version={self.CACHE_VERSION}",
            f"data={data_hash}",
            f"config={hashlib.sha256(config_signature.encode()).hexdigest()}",
            f"swing={hashlib.sha256(swing_signature.encode()).hexdigest()}",
            f"analyzer={hashlib.sha256(analyzer_signature.encode()).hexdigest()}",
        ]
        final_hash = hashlib.sha256("|".join(key_parts).encode()).hexdigest()
        return f"zone_analysis_{final_hash}"

    def load(self, cache_key: str) -> Optional[ZoneAnalysisResult]:
        """Load a result from cache if available and version compatible."""

        if self._cache_manager is None:
            return None

        cached_data = self._cache_manager.get(cache_key)
        if cached_data is None:
            return None

        if not isinstance(cached_data, dict):
            self.logger.info(
                "Cache entry missing version metadata; invalidating and recalculating."
            )
            self._cache_manager.invalidate(cache_key)
            return None

        cached_version = cached_data.get("cache_version", 1)
        if cached_version < self.CACHE_VERSION:
            self.logger.info(
                "Cache invalidated due to schema upgrade (v%s → v%s). Recalculating...",
                cached_version,
                self.CACHE_VERSION,
            )
            self._cache_manager.invalidate(cache_key)
            return None

        return cached_data.get("result")

    def save(
        self,
        cache_key: str,
        result: ZoneAnalysisResult,
        *,
        ttl: Optional[int] = None,
        disk: bool = True,
    ) -> None:
        """Persist a result to cache with version metadata."""

        if self._cache_manager is None:
            return

        payload = {
            "cache_version": self.CACHE_VERSION,
            "result": result,
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "schema": "ZoneAnalysisResult_v2",
                "bquant_version": __version__,
            },
        }

        self._cache_manager.put(cache_key, payload, ttl=ttl, disk=disk)
        self.logger.debug("Saved zone analysis cache entry: %s", cache_key[:12])

    def invalidate(self, cache_key: str) -> None:
        """Invalidate a cache entry if caching is enabled."""

        if self._cache_manager is None:
            return

        self._cache_manager.invalidate(cache_key)

    @staticmethod
    def compute_data_hash(df: pd.DataFrame) -> str:
        """Compute a deterministic hash of everything in the dataframe.

        Every column, the column names and the index. Until CACHE_VERSION 22 only
        ``open/high/low/close`` were hashed, and the cache is on by default — so
        the same OHLC with a different precomputed ``RSI_14`` returned the zones
        cut on the other RSI (64 zones from cache against 1 on a cold run), and a
        volume strategy returned volume metrics of a frame whose volume was ten
        times smaller (G53). What a strategy reads is not known here — combined
        conditions read whatever they like — so the honest key is the whole frame.
        """

        if not set(["open", "high", "low", "close"]).issubset(df.columns):
            raise ValueError("Dataframe must contain open, high, low, close columns")
        digest = hashlib.sha256()
        digest.update("|".join(map(str, df.columns)).encode())
        digest.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
        return digest.hexdigest()

    @staticmethod
    def config_signature(config: "ZoneAnalysisConfig") -> str:
        """Create JSON signature for :class:`ZoneAnalysisConfig`."""

        payload = {
            "indicator": asdict(config.indicator) if config.indicator else None,
            "zone_detection": asdict(config.zone_detection)
            if config.zone_detection
            else None,
            "perform_clustering": config.perform_clustering,
            "n_clusters": config.n_clusters,
            "run_regression": config.run_regression,
            "run_validation": config.run_validation,
            "swing_scope": config.swing_scope,
        }
        return json.dumps(payload, sort_keys=True, default=str)

    @staticmethod
    def swing_signature(swing_config: Any) -> str:
        """Serialize swing configuration for cache hashing."""

        return json.dumps(swing_config, sort_keys=True, default=str)

    @staticmethod
    def analyzer_signature(analyzer_config: Any) -> str:
        """Serialize the analyzer's metric configuration for cache hashing."""

        return json.dumps(analyzer_config, sort_keys=True, default=str)

