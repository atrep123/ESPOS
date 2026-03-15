import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig

try:
    import pytest_benchmark.plugin as _pytest_benchmark_plugin  # noqa: F401

    _HAS_PYTEST_BENCHMARK = True
except ImportError:
    _HAS_PYTEST_BENCHMARK = False


if not _HAS_PYTEST_BENCHMARK:

    @pytest.fixture
    def benchmark():
        """Fallback benchmark fixture when pytest-benchmark plugin is unavailable."""

        def _run(func, *args, **kwargs):
            return func(*args, **kwargs)

        return _run


@pytest.fixture
def designer_with_scene(tmp_path):
    designer = UIDesigner(128, 64)
    scene = designer.create_scene("main")
    designer.current_scene = scene.name
    scene.widgets.append(WidgetConfig(type="box", x=0, y=0, width=10, height=10))
    return designer, scene, tmp_path


@pytest.fixture
def temp_json(tmp_path):
    return tmp_path / "scene.json"


@pytest.fixture(autouse=True)
def isolate_templates_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("ESP32OS_TEMPLATES_PATH", str(tmp_path / "templates.json"))


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    """Factory fixture to create a CyberpunkEditorApp with common defaults.

    Usage::

        def test_something(make_app):
            app = make_app()
            app = make_app(widgets=[WidgetConfig(...)])
            app = make_app(profile="...", snap=True)
    """
    from cyberpunk_editor import CyberpunkEditorApp

    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    def _factory(
        *,
        widgets=None,
        profile=None,
        snap=False,
        extra_scenes=False,
        scenes_count=1,
        scenes=None,
        size=(256, 128),
    ):
        json_path = tmp_path / "scene.json"
        app = CyberpunkEditorApp(json_path, size)
        if not hasattr(app, "_save_undo_state"):
            app._save_undo_state = lambda: None
        if profile:
            app.hardware_profile = profile
        app.snap_enabled = snap
        app.show_help_overlay = False
        app._help_shown_once = True
        if widgets:
            sc = app.state.current_scene()
            for w in widgets:
                sc.widgets.append(w)
        if extra_scenes:
            app.designer.create_scene("scene2")
        if scenes:
            for name, sc in scenes.items():
                app.designer.scenes[name] = sc
        for i in range(2, scenes_count):
            name = f"extra_{i}"
            app.designer.create_scene(name)
        return app

    return _factory
