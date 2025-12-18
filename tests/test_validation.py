import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetValidationError


def test_validate_scene_dict_invalid_bool_size():
    d = UIDesigner(10, 10)
    with pytest.raises(WidgetValidationError):
        d._validate_scene_dict({"name": "bad", "width": True, "height": 10}, {"display": {}})


def test_validate_scene_dict_missing_returns_defaults():
    d = UIDesigner(10, 10)
    result = d._validate_scene_dict({"name": "ok"}, {"display": {"width": 5, "height": 6}})
    assert result["width"] == 5
    assert result["height"] == 6
    assert result["theme"] == "default"
