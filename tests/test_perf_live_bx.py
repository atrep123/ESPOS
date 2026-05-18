"""BX: Edge-case tests for perf (RenderCache) and live_preview."""

from __future__ import annotations

import pygame

from cyberpunk_designer.perf import RenderCache

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
