import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner


def test_class_vars_initialized_to_none(tmp_path, monkeypatch):
    # Reset class-level state that may have been set by prior tests
    UIDesigner._last_loaded_json = None
    UIDesigner._json_watch_mtime = None
    d = UIDesigner(8, 8)
    assert UIDesigner._last_loaded_json is None
    assert UIDesigner._json_watch_mtime is None

    f = tmp_path / "scene.json"
    f.write_text('{"width":8,"height":8,"scenes":{}}', encoding="utf-8")
    d.load_from_json(str(f))
    assert isinstance(UIDesigner._last_loaded_json, str)
    assert UIDesigner._json_watch_mtime is not None


def test_record_json_watch_resets_on_missing(tmp_path):
    d = UIDesigner(8, 8)
    missing = tmp_path / "missing.json"
    d._record_json_watch(str(missing))
    assert UIDesigner._last_loaded_json is None
    assert UIDesigner._json_watch_mtime is None
