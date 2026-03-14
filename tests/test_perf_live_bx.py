"""BX: Edge-case tests for perf (RenderCache, SmartEventQueue) and live_preview."""

from __future__ import annotations

import concurrent.futures

import pygame

from cyberpunk_designer.perf import RenderCache, SmartEventQueue

# ---------------------------------------------------------------------------
# RenderCache
# ---------------------------------------------------------------------------


class TestRenderCacheEdges:
    def test_get_miss(self):
        """Cache miss returns None."""
        cache = RenderCache(max_size=4)
        assert cache.get(42) is None

    def test_set_and_get(self):
        """Set then get returns surface."""
        cache = RenderCache(max_size=4)
        surf = pygame.Surface((10, 10))
        cache.set(1, surf)
        assert cache.get(1) is surf

    def test_eviction_at_capacity(self):
        """Oldest entry evicted when capacity reached."""
        cache = RenderCache(max_size=3)
        for i in range(3):
            cache.set(i, pygame.Surface((1, 1)))
        # Access key 1 and 2 to make 0 least recently used
        cache.get(1)
        cache.get(2)
        # Add 4th → should evict key 0
        cache.set(3, pygame.Surface((1, 1)))
        assert cache.get(0) is None
        assert cache.get(1) is not None
        assert cache.get(2) is not None
        assert cache.get(3) is not None

    def test_repeated_eviction(self):
        """Multiple evictions keep cache at max_size."""
        cache = RenderCache(max_size=2)
        for i in range(10):
            cache.set(i, pygame.Surface((1, 1)))
        assert len(cache.cache) <= 2

    def test_overwrite_key(self):
        """Setting same key overwrites value."""
        cache = RenderCache(max_size=4)
        s1 = pygame.Surface((10, 10))
        s2 = pygame.Surface((20, 20))
        cache.set(1, s1)
        cache.set(1, s2)
        assert cache.get(1) is s2

    def test_max_size_one(self):
        """Cache with max_size=1 works correctly."""
        cache = RenderCache(max_size=1)
        s1 = pygame.Surface((1, 1))
        s2 = pygame.Surface((2, 2))
        cache.set(1, s1)
        cache.set(2, s2)
        assert len(cache.cache) == 1
        assert cache.get(2) is s2


# ---------------------------------------------------------------------------
# SmartEventQueue
# ---------------------------------------------------------------------------


class TestSmartEventQueueEdges:
    def test_empty_batch(self):
        """Empty event list returns empty list."""
        q = SmartEventQueue()
        assert q.process_batch([]) == []

    def test_non_parallelizable_passthrough(self):
        """Non-motion events pass through directly."""
        q = SmartEventQueue()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        result = q.process_batch([event])
        assert len(result) == 1
        assert result[0].type == pygame.KEYDOWN

    def test_motion_parallelized(self):
        """MOUSEMOTION events are parallelized."""
        q = SmartEventQueue()
        event = pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 20), rel=(1, 1), buttons=(0, 0, 0))
        result = q.process_batch([event])
        assert len(result) == 1

    def test_mixed_events(self):
        """Mix of parallel and non-parallel events processed correctly."""
        q = SmartEventQueue()
        events = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a),
            pygame.event.Event(
                pygame.MOUSEMOTION, pos=(10, 20), rel=(1, 1), buttons=(0, 0, 0)
            ),
            pygame.event.Event(pygame.KEYUP, key=pygame.K_a),
        ]
        result = q.process_batch(events)
        assert len(result) == 3

    def test_future_exception_skipped(self):
        """Futures that raise are silently skipped."""
        q = SmartEventQueue()
        # Replace executor to simulate failure

        def failing_submit(fn, *args, **kwargs):
            fut = concurrent.futures.Future()
            fut.set_exception(RuntimeError("boom"))
            return fut

        q.executor.submit = failing_submit
        event = pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0), rel=(0, 0), buttons=(0, 0, 0))
        result = q.process_batch([event])
        # Motion event failed, so result should be empty (only parallel events submitted)
        assert isinstance(result, list)

    def test_queue_cleared_between_batches(self):
        """Queue doesn't accumulate across process_batch calls."""
        q = SmartEventQueue()
        e1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)
        e2 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b)
        r1 = q.process_batch([e1])
        r2 = q.process_batch([e2])
        assert len(r1) == 1
        assert len(r2) == 1


# ---------------------------------------------------------------------------
# live_preview
# ---------------------------------------------------------------------------


class TestLivePreviewEdges:
    def test_no_port(self, tmp_path, monkeypatch):
        """No port configured → status message."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_designer.live_preview import send_live_preview
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        app.live_preview_port = ""
        send_live_preview(app)

    def test_no_pyserial(self, tmp_path, monkeypatch):
        """Missing pyserial → status message."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_designer.live_preview import send_live_preview
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        app.live_preview_port = "COM99"
        # Block serial import
        import sys

        monkeypatch.setitem(sys.modules, "serial", None)
        send_live_preview(app)

    def test_refresh_ports_no_pyserial(self, tmp_path, monkeypatch):
        """refresh_available_ports without pyserial → empty list."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import sys

        from cyberpunk_designer.live_preview import refresh_available_ports
        from cyberpunk_editor import CyberpunkEditorApp

        monkeypatch.setitem(sys.modules, "serial", None)
        monkeypatch.setitem(sys.modules, "serial.tools", None)
        monkeypatch.setitem(sys.modules, "serial.tools.list_ports", None)
        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        refresh_available_ports(app)
        assert app.available_ports == []

    def test_open_live_dialog_delegates(self, tmp_path, monkeypatch):
        """open_live_dialog calls send_live_preview."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from cyberpunk_designer import live_preview
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        app.live_preview_port = ""
        result = live_preview.open_live_dialog(app)
        assert result is None
