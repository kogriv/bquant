"""Глобальное состояние обещает то, что написано в docs/user_guide/caching.md §9 (G64).

Замер до правки: восемь потоков на ``MemoryCache(max_size=40)`` по 3000 операций —
7–8 исключений за прогон (``list.remove`` по ключу, который уже удалил сосед) и
список порядка длиннее словаря (41 против 40). Загрузка внешних библиотек шла при
импорте и не была идемпотентной по своему флагу.
"""

from __future__ import annotations

import random
import threading

from bquant.core.cache import MemoryCache, get_cache_manager
from bquant.indicators.library.manager import LibraryManager


def _hammer(cache: MemoryCache, threads: int = 8, ops: int = 3000):
    errors: list[str] = []

    def worker(seed: int):
        rng = random.Random(seed)
        try:
            for i in range(ops):
                key = f"k{rng.randrange(60)}"
                cache.put(key, i)
                cache.get(key)
                if i % 7 == 0:
                    cache.invalidate(key)
        except Exception as exc:  # noqa: BLE001 — сам факт исключения и есть замер
            errors.append(repr(exc))

    pool = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()
    return errors


def test_memory_cache_survives_concurrent_use():
    cache = MemoryCache(max_size=40, default_ttl=0)
    errors = _hammer(cache)
    assert errors == [], f"{len(errors)} exceptions under 8 threads, e.g. {errors[0]}"
    assert set(cache._cache) == set(cache._access_order)
    assert len(cache._access_order) == len(set(cache._access_order))
    assert len(cache._cache) <= cache.max_size


def test_the_global_manager_is_one_object_across_threads(monkeypatch):
    import bquant.core.cache as cache_module

    monkeypatch.setattr(cache_module, "_global_cache_manager", None)
    seen = []
    barrier = threading.Barrier(8)

    def grab():
        barrier.wait()
        seen.append(id(get_cache_manager()))

    pool = [threading.Thread(target=grab) for _ in range(8)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()
    assert len(set(seen)) == 1, f"{len(set(seen))} distinct managers created"


def test_ensure_loaded_loads_once_per_process(monkeypatch):
    calls = []
    monkeypatch.setattr(LibraryManager, "_loaded", False)
    monkeypatch.setattr(LibraryManager, "load_all_libraries",
                        classmethod(lambda cls: (calls.append(1), setattr(cls, "_loaded", True), {"x": 1})[-1]))
    first, second, third = LibraryManager.ensure_loaded(), LibraryManager.ensure_loaded(), LibraryManager.ensure_loaded()
    assert first == {"x": 1} and second == {} and third == {}
    assert len(calls) == 1
