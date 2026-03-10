"""Tests for cyberpunk_designer/perf.py — RenderCache LRU eviction and
SmartEventQueue event processing."""

from __future__ import annotations

from types import SimpleNamespace

import pygame

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
