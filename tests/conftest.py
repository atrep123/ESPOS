import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig


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
