import logging

from bquant.analysis.zones.cache import ZoneAnalysisCache


class DummyCacheManager:
    def __init__(self, payload):
        self._payload = payload
        self.invalidated_keys = []

    def get(self, key):
        return self._payload

    def invalidate(self, key):
        self.invalidated_keys.append(key)

    def put(self, *args, **kwargs):
        # ZoneAnalysisCache may call put() during other tests; keep as no-op.
        pass


def test_cache_invalidation_on_version_upgrade(caplog):
    legacy_payload = {
        "cache_version": ZoneAnalysisCache.CACHE_VERSION - 1,
        "result": object(),
    }
    manager = DummyCacheManager(legacy_payload)
    cache = ZoneAnalysisCache(manager)

    caplog.set_level(
        logging.INFO,
        logger="bquant.analysis.zones.cache.ZoneAnalysisCache",
    )

    result = cache.load("legacy-key")

    assert result is None
    assert manager.invalidated_keys == ["legacy-key"]


def test_cache_load_returns_payload_for_current_version(caplog):
    expected = object()
    current_payload = {
        "cache_version": ZoneAnalysisCache.CACHE_VERSION,
        "result": expected,
    }
    manager = DummyCacheManager(current_payload)
    cache = ZoneAnalysisCache(manager)

    caplog.set_level(
        logging.DEBUG,
        logger="bquant.analysis.zones.cache.ZoneAnalysisCache",
    )

    result = cache.load("current-key")

    assert result is expected
    assert manager.invalidated_keys == []

