"""Другой пакет — другой ключ кэша (G74).

`CACHE_VERSION` обязана подниматься, когда меняется форма результата. Это дисциплина, и
она не сработала: G70 (релиз 0.0.16) добавил в `swing_metrics` поле `degraded`, а версию
схемы не тронул — записи, положенные 0.0.15, продолжали читаться под 0.0.16 и 0.0.17.

Нашёл внешний потребитель, и нашёл дорого: его парный замер «0.0.15 против 0.0.16»
сравнил пикл сам с собой и честно сообщил «всё побайтово одинаково». Выдало время —
9.6 секунды там, где сборка занимает 27–48; с выключенным кэшем разница увидлась сразу
(25 ключей `swing_metrics` против 26).

Правило вместо памяти: версия пакета входит в ключ. Тогда «забыли поднять
`CACHE_VERSION`» перестаёт быть возможным — цена одна, пересчёт после обновления.

Замеренная цена молчания — не в этом файле, а в разборе:
`devref/gaps/cache/g74_the_cache_key_did_not_see_the_package_version_2026-09.md`.
"""

import pytest

import bquant.analysis.zones.cache as cache_module
from bquant.analysis.zones.cache import ZoneAnalysisCache


@pytest.fixture
def cache():
    return ZoneAnalysisCache(None)


def _key(cache):
    return cache.generate_cache_key("data-hash", "config", "swing", "analyzer")


def test_a_different_package_version_gives_a_different_key(cache, monkeypatch):
    """Главное утверждение: записи предыдущего релиза не читаются следующим."""
    before = _key(cache)
    monkeypatch.setattr(cache_module, "__version__", "99.99.99")
    after = _key(cache)

    assert before != after


def test_the_same_version_and_the_same_inputs_give_the_same_key(cache):
    """Ключ обязан оставаться стабильным внутри версии — иначе кэш бесполезен."""
    assert _key(cache) == _key(cache)


def test_the_schema_version_still_separates_results(cache, monkeypatch):
    """`CACHE_VERSION` не заменена версией пакета, а дополнена ею."""
    before = _key(cache)
    monkeypatch.setattr(ZoneAnalysisCache, "CACHE_VERSION", ZoneAnalysisCache.CACHE_VERSION + 1)
    assert _key(cache) != before


def test_every_input_that_changes_the_result_changes_the_key(cache):
    """Четыре подписи и версии — и ни одна из них не декоративна."""
    base = _key(cache)
    variants = [
        cache.generate_cache_key("other", "config", "swing", "analyzer"),
        cache.generate_cache_key("data-hash", "other", "swing", "analyzer"),
        cache.generate_cache_key("data-hash", "config", "other", "analyzer"),
        cache.generate_cache_key("data-hash", "config", "swing", "other"),
    ]

    assert len(set(variants)) == len(variants), "две разные конфигурации дали один ключ"
    assert base not in variants


def test_the_schema_version_is_ahead_of_the_release_that_changed_the_payload():
    """Пин, который краснеет, если форму payload поменяли и версию снова забыли.

    28 — версия, поднятая вместе с этой правкой. Меняете форму `swing_metrics`,
    `ZoneInfo` или сводки — поднимаете и её; тест напомнит, что число живое.
    """
    assert ZoneAnalysisCache.CACHE_VERSION >= 28
