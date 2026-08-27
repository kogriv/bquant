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
    CACHE_VERSION = 14

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
    ) -> str:
        """Create a version-aware cache key.

        Args:
            data_hash: Hash of the OHLC price data.
            config_signature: JSON signature of :class:`ZoneAnalysisConfig`.
            swing_signature: JSON signature of swing configuration.

        Returns:
            Deterministic cache key string.
        """

        key_parts = [
            f"version={self.CACHE_VERSION}",
            f"data={data_hash}",
            f"config={hashlib.sha256(config_signature.encode()).hexdigest()}",
            f"swing={hashlib.sha256(swing_signature.encode()).hexdigest()}",
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
        """Compute a deterministic hash for the OHLC portion of the dataframe."""

        if not set(["open", "high", "low", "close"]).issubset(df.columns):
            raise ValueError("Dataframe must contain open, high, low, close columns")
        return str(pd.util.hash_pandas_object(df[["open", "high", "low", "close"]]).sum())

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

