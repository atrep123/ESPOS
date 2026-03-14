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
