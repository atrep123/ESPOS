import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from ui_designer import UIDesigner, WidgetValidationError


def test_validate_scene_dict_accepts_valid_fields():
    designer = UIDesigner(100, 50)
    data = {
        "scenes": {
            "main": {
                "name": "main",
                "width": 120,
                "height": 60,
                "theme": "pixel",
                "hardware_profile": "oled_128x64",
                "max_fb_kb": 2,
                "max_flash_kb": 4,
            }
        }
    }
    result = designer._validate_scene_dict(data["scenes"]["main"], data)
    assert result["name"] == "main"
    assert result["width"] == 120
    assert result["height"] == 60
    assert result["theme"] == "pixel"
    assert result["hardware_profile"] == "oled_128x64"
    assert result["max_fb_kb"] == 2
    assert result["max_flash_kb"] == 4


def test_validate_scene_dict_rejects_bad_types():
    designer = UIDesigner(100, 50)
    bad_data = {"name": "main", "width": "wide", "height": 60}
    with pytest.raises(WidgetValidationError):
        designer._validate_scene_dict(bad_data, {"scenes": {}})


def test_build_scenes_applies_defaults_and_sets_fields():
    designer = UIDesigner(100, 50)
    raw = {
        "display": {"width": 200, "height": 100},
        "scenes": {
            "one": {
                "name": "one",
                "theme": "retro",
                "hardware_profile": None,
                "max_fb_kb": None,
                "max_flash_kb": None,
            }
        },
    }
    scenes = designer._build_scenes_from_data(raw)
    scene = scenes["one"]
    assert scene.width == 200 and scene.height == 100
    assert scene.theme == "retro"
    assert scene.hardware_profile is None
    assert scene.max_fb_kb is None and scene.max_flash_kb is None
