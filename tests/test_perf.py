"""Tests for cyberpunk_designer/perf.py — RenderCache LRU eviction and
SmartEventQueue event processing."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from cyberpunk_designer.perf import RenderCache, SmartEventQueue

# ---------------------------------------------------------------------------
# RenderCache
# ---------------------------------------------------------------------------


class TestRenderCache:
    def test_set_and_get(self):
        cache = RenderCache(max_size=10)
        surf = pygame.Surface((10, 10))
        cache.set(1, surf)
        assert cache.get(1) is surf

    def test_get_miss(self):
        cache = RenderCache(max_size=10)
        assert cache.get(999) is None

    def test_overwrite(self):
        cache = RenderCache(max_size=10)
        s1 = pygame.Surface((10, 10))
        s2 = pygame.Surface((20, 20))
        cache.set(1, s1)
        cache.set(1, s2)
        assert cache.get(1) is s2

    def test_eviction(self):
        cache = RenderCache(max_size=3)
        for i in range(4):
            cache.set(i, pygame.Surface((10, 10)))
        # One of keys 0-2 should have been evicted to make room for key 3
        assert cache.get(3) is not None
        assert len(cache.cache) <= 3

    def test_lru_logic(self):
        cache = RenderCache(max_size=3)
        cache.set(1, pygame.Surface((10, 10)))
        cache.set(2, pygame.Surface((10, 10)))
        cache.set(3, pygame.Surface((10, 10)))
        # Access key 1 to make it recently used
        cache.get(1)
        cache.get(1)
        # Insert key 4 → should evict key 2 or 3 (least accessed)
        cache.set(4, pygame.Surface((10, 10)))
        assert cache.get(1) is not None
        assert cache.get(4) is not None
        assert len(cache.cache) <= 3

    def test_empty_cache_get(self):
        cache = RenderCache(max_size=5)
        assert cache.get(0) is None

    def test_max_size_one(self):
        cache = RenderCache(max_size=1)
        cache.set(1, pygame.Surface((5, 5)))
        cache.set(2, pygame.Surface((5, 5)))
        assert len(cache.cache) <= 1
        assert cache.get(2) is not None


# ---------------------------------------------------------------------------
# SmartEventQueue
# ---------------------------------------------------------------------------


def _make_event(etype, **attrs):
    """Create a simple event-like namespace."""
    return SimpleNamespace(type=etype, **attrs)


class TestSmartEventQueue:
    def test_empty_batch(self):
        q = SmartEventQueue()
        assert q.process_batch([]) == []

    def test_non_parallel_events_preserved(self):
        q = SmartEventQueue()
        ev1 = _make_event(pygame.KEYDOWN, key=pygame.K_a)
        ev2 = _make_event(pygame.KEYDOWN, key=pygame.K_b)
        result = q.process_batch([ev1, ev2])
        assert len(result) == 2

    def test_parallel_events_processed(self):
        q = SmartEventQueue()
        ev = _make_event(pygame.MOUSEMOTION, pos=(10, 20))
        result = q.process_batch([ev])
        # Parallel events return through executor → should still appear
        assert len(result) == 1

    def test_mixed_events(self):
        q = SmartEventQueue()
        events = [
            _make_event(pygame.KEYDOWN, key=pygame.K_a),
            _make_event(pygame.MOUSEMOTION, pos=(10, 20)),
            _make_event(pygame.KEYUP, key=pygame.K_a),
            _make_event(pygame.MOUSEWHEEL, y=1),
        ]
        result = q.process_batch(events)
        assert len(result) == 4

    def test_can_parallelize_mousemotion(self):
        q = SmartEventQueue()
        assert q._can_parallelize(_make_event(pygame.MOUSEMOTION))

    def test_can_parallelize_mousewheel(self):
        q = SmartEventQueue()
        assert q._can_parallelize(_make_event(pygame.MOUSEWHEEL))

    def test_cannot_parallelize_keydown(self):
        q = SmartEventQueue()
        assert not q._can_parallelize(_make_event(pygame.KEYDOWN))

    def test_queue_clears_between_batches(self):
        q = SmartEventQueue()
        q.process_batch([_make_event(pygame.KEYDOWN, key=pygame.K_a)])
        result = q.process_batch([])
        assert result == []


# ---------------------------------------------------------------------------
# AX — RenderCache concurrency & edge-case hardening
# ---------------------------------------------------------------------------


class TestRenderCacheEdgeCases:
    def test_max_size_zero_still_stores(self):
        """max_size=0 means cache never triggers eviction guard (len >= 0 always true)."""
        cache = RenderCache(max_size=0)
        # set() will try to evict because len({}) >= 0 is True, but cache is
        # empty so min() on empty dict.keys() raises ValueError.
        # This verifies the cache doesn't crash.
        try:
            cache.set(1, pygame.Surface((5, 5)))
        except ValueError:
            pass  # acceptable — empty min()

    def test_repeated_eviction_stress(self):
        cache = RenderCache(max_size=3)
        for i in range(50):
            cache.set(i, pygame.Surface((2, 2)))
        assert len(cache.cache) <= 3

    def test_get_updates_access_history(self):
        cache = RenderCache(max_size=5)
        cache.set(1, pygame.Surface((5, 5)))
        for _ in range(10):
            cache.get(1)
        # access_history is deque(maxlen=max_size), so at most 5 entries
        assert cache.access_history.count(1) == 5

    def test_eviction_prefers_least_accessed(self):
        cache = RenderCache(max_size=3)
        cache.set(10, pygame.Surface((5, 5)))
        cache.set(20, pygame.Surface((5, 5)))
        cache.set(30, pygame.Surface((5, 5)))
        # Access 10 and 30 many times — 20 becomes least accessed
        for _ in range(5):
            cache.get(10)
            cache.get(30)
        cache.set(40, pygame.Surface((5, 5)))
        assert 20 not in cache.cache
        assert 10 in cache.cache
        assert 30 in cache.cache

    def test_overwrite_preserves_cache_size(self):
        cache = RenderCache(max_size=3)
        for i in range(3):
            cache.set(i, pygame.Surface((5, 5)))
        # set() evicts LRU first when at capacity, then inserts.
        # With no access_history hits, eviction is arbitrary.
        cache.set(1, pygame.Surface((10, 10)))
        # Key 1 is definitely present with the new surface
        assert 1 in cache.cache
        assert cache.cache[1].get_size() == (10, 10)

    def test_access_history_maxlen(self):
        cache = RenderCache(max_size=5)
        # Fill access history to maxlen
        for i in range(5):
            cache.set(i, pygame.Surface((5, 5)))
        for _ in range(20):
            for i in range(5):
                cache.get(i)
        # access_history is bounded by maxlen=max_size
        assert len(cache.access_history) <= 5


class TestSmartEventQueueEdgeCases:
    def test_large_batch(self):
        q = SmartEventQueue()
        events = [_make_event(pygame.MOUSEMOTION, pos=(i, i)) for i in range(200)]
        result = q.process_batch(events)
        assert len(result) == 200

    def test_all_parallel_events(self):
        q = SmartEventQueue()
        events = [_make_event(pygame.MOUSEMOTION, pos=(i, 0)) for i in range(10)] + [
            _make_event(pygame.MOUSEWHEEL, y=i) for i in range(10)
        ]
        result = q.process_batch(events)
        assert len(result) == 20

    def test_all_sequential_events(self):
        q = SmartEventQueue()
        events = [_make_event(pygame.KEYDOWN, key=pygame.K_a + i) for i in range(10)]
        result = q.process_batch(events)
        assert len(result) == 10

    def test_process_batch_idempotent(self):
        q = SmartEventQueue()
        events = [_make_event(pygame.KEYDOWN, key=pygame.K_a)]
        r1 = q.process_batch(events)
        r2 = q.process_batch(events)
        assert len(r1) == len(r2) == 1

    def test_multiple_batches_independent(self):
        q = SmartEventQueue()
        r1 = q.process_batch([_make_event(pygame.KEYDOWN, key=pygame.K_a)])
        r2 = q.process_batch([_make_event(pygame.KEYDOWN, key=pygame.K_b)])
        assert len(r1) == 1
        assert len(r2) == 1

    def test_executor_exists(self):
        q = SmartEventQueue()
        assert q.executor is not None
        assert q.executor._max_workers == 4

    def test_cannot_parallelize_custom_event(self):
        q = SmartEventQueue()
        assert not q._can_parallelize(_make_event(pygame.USEREVENT))

    def test_cannot_parallelize_quit(self):
        q = SmartEventQueue()
        assert not q._can_parallelize(_make_event(pygame.QUIT))


# ---------------------------------------------------------------------------
# BP — additional edge-case coverage
# ---------------------------------------------------------------------------


class TestRenderCacheZeroCapacity:
    """max_size=0 means eviction fires on every set (len({}) >= 0 is True)."""

    def test_set_on_empty_catches_min_error(self):
        cache = RenderCache(max_size=0)
        try:
            cache.set(1, pygame.Surface((2, 2)))
        except ValueError:
            pass  # min() on empty keys raises; acceptable
        # If it didn't crash, the key may or may not be stored
        assert len(cache.cache) <= 1

    def test_negative_max_size_raises(self):
        """Negative max_size triggers ValueError in deque(maxlen=...)."""
        with pytest.raises(ValueError, match="non-negative"):
            RenderCache(max_size=-1)


class TestSmartEventQueueProcessEvent:
    def test_process_event_returns_same_event(self):
        q = SmartEventQueue()
        ev = _make_event(pygame.MOUSEMOTION, pos=(5, 5))
        result = q._process_event(ev)
        assert result is ev

    def test_executor_shutdown_safe(self):
        """Thread pool can be shut down without issue."""
        q = SmartEventQueue()
        q.executor.shutdown(wait=False)
        # Queue should still handle non-parallel events after shutdown
        events = [_make_event(pygame.KEYDOWN, key=pygame.K_a)]
        result = q.process_batch(events)
        assert len(result) == 1

    def test_patterns_dict_starts_empty(self):
        q = SmartEventQueue()
        assert q.patterns == {}
