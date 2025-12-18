import json
import os

from ui_designer import UIDesigner


def test_last_loaded_json_and_mtime_tracked(tmp_path, monkeypatch):
    sample = tmp_path / "scene.json"
    sample.write_text(json.dumps({"width": 8, "height": 8, "scenes": {}}), encoding="utf-8")
    designer = UIDesigner(8, 8)
    designer.load_from_json(str(sample))

    assert designer._last_loaded_json == str(sample)
    assert isinstance(designer._json_watch_mtime, float)

    # If file disappears, watch fields reset gracefully
    os.remove(sample)
    designer._record_json_watch(str(sample))
    assert designer._last_loaded_json is None
    assert designer._json_watch_mtime is None
