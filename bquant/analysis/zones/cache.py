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

    CACHE_VERSION = 2

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

