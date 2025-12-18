import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import SceneLoadError, UIDesigner


def test_read_json_file_missing_raises_scene_load_error(tmp_path):
    designer = UIDesigner()
    missing = tmp_path / "missing.json"
    with pytest.raises(SceneLoadError):
        designer._read_json_file(str(missing))


def test_load_from_json_falls_back_on_bad_json(tmp_path, caplog):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    designer = UIDesigner()
    designer.load_from_json(str(bad))
    assert designer.current_scene is not None
    assert designer.scenes
    assert any("falling back to default scene" in msg for msg in caplog.text.lower().splitlines())
