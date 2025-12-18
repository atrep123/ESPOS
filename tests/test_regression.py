import pytest

from ui_designer import UIDesigner, WidgetValidationError


def test_snap_position_respects_grid(designer_with_scene):
    designer, scene, _ = designer_with_scene
    designer.snap_to_grid = True
    x, y = designer.snap_position(5, 5)
    assert x % designer.grid_size == 0 and y % designer.grid_size == 0


def test_validate_scene_dict_rejects_non_str_profile():
    designer = UIDesigner()
    with pytest.raises(WidgetValidationError):
        designer._validate_scene_dict({"name": "bad", "hardware_profile": 123}, {"display": {}})
