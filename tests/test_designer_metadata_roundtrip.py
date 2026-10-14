"""Headless document roundtrips through the actual UIDesigner class."""

import copy
import json
import os

import pytest

from ui_designer import UIDesigner, WidgetValidationError


@pytest.fixture
def document():
    return {
        "width": 256,
        "height": 128,
        "device": "ssd1363",
        "board": "esp32-s3-devkitm-1",
        "profile": {"id": "esp32os_256x128_gray4", "custom": [1, None]},
        "active_board": "esp32-s3-devkitm-1",
        "hardware_profile": "esp32os_256x128_gray4",
        "code_blocks": [{"language": "python", "source": "raise RuntimeError('NEVER EXECUTE')\n"}],
        "vendor_extension": {"opaque": [False, "český text"]},
        "scenes": {
            "main": {
                "name": "Main",
                "width": 256,
                "height": 128,
                "bg_color": "#112233",
                "theme": "dark",
                "hardware_profile": "esp32os_256x128_gray4",
                "max_fb_kb": 32,
                "max_flash_kb": 64,
                "states": {"unavailable": {"text": "Nedostupné"}},
                "code_blocks": {"init": "__import__('os').environ['ESPOS_TEST_CODE_EXECUTED']='1'"},
                "navrh": {"koren": True},
                "custom_scene": {"data": [3, 2, 1]},
                "widgets": [
                    {
                        "type": "label",
                        "x": 1,
                        "y": 2,
                        "width": 30,
                        "height": 10,
                        "text": "Before",
                        "id": "label",
                    }
                ],
            }
        },
    }


def roundtrip(tmp_path, monkeypatch, document):
    monkeypatch.setenv("ESP32OS_AUTO_EXPORT", "0")
    source = tmp_path / "source.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    designer = UIDesigner()
    designer.load_from_json(str(source))
    designer.scenes[next(iter(designer.scenes))].widgets[0].text = "Edited"
    output = tmp_path / "saved.json"
    designer.save_to_json(str(output))
    return designer, json.loads(output.read_text(encoding="utf-8"))


def test_metadata_and_opaque_blocks_survive_actual_edit_save(tmp_path, monkeypatch, document):
    monkeypatch.delenv("ESPOS_TEST_CODE_EXECUTED", raising=False)
    _, saved = roundtrip(tmp_path, monkeypatch, document)
    for key in document.keys() - {"width", "height", "scenes"}:
        assert saved.get(key) == document[key], f"root metadata lost: {key}"
    for key in document["scenes"]["main"].keys() - {"widgets"}:
        assert saved["scenes"]["main"].get(key) == document["scenes"]["main"][key], key
    assert saved["scenes"]["main"]["widgets"][0]["text"] == "Edited"
    assert "ESPOS_TEST_CODE_EXECUTED" not in os.environ


def test_list_scenes_preserve_shape_metadata_and_widgets(tmp_path, monkeypatch, document):
    scene = document["scenes"]["main"]
    document["scenes"] = [dict(scene, id="stable_scene_id")]
    _, saved = roundtrip(tmp_path, monkeypatch, document)
    assert isinstance(saved["scenes"], list)
    assert saved["scenes"][0]["id"] == "stable_scene_id"
    assert saved["scenes"][0]["states"] == scene["states"]
    assert saved["scenes"][0]["widgets"][0]["text"] == "Edited"


@pytest.mark.parametrize("field", ["children", "states", "unknown_widget_property"])
def test_unsupported_widget_fields_refused_without_mutating_loaded_document(
    tmp_path, monkeypatch, document, field
):
    monkeypatch.setenv("ESP32OS_AUTO_EXPORT", "0")
    source = tmp_path / "valid.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    designer = UIDesigner()
    designer.load_from_json(str(source))
    previous_scene = designer.scenes["main"]
    unsupported = copy.deepcopy(document)
    unsupported["device"] = "must_not_replace_previous"
    unsupported["scenes"]["main"]["widgets"][0][field] = [{"id": "nested"}]
    bad = tmp_path / "unsupported.json"
    bad.write_text(json.dumps(unsupported), encoding="utf-8")
    with pytest.raises(WidgetValidationError, match=field):
        designer.load_from_json(str(bad))
    assert designer.scenes["main"] is previous_scene
    designer.save_to_json(str(tmp_path / "unchanged.json"))
    saved = json.loads((tmp_path / "unchanged.json").read_text(encoding="utf-8"))
    assert saved["device"] == document["device"]


def test_scene_children_and_root_states_are_preserved_as_opaque_extensions(
    tmp_path, monkeypatch, document
):
    document["states"] = [{"id": "error", "code_blocks": "do not execute"}]
    children = [{"type": "container", "children": [{"id": "nested", "states": ["error"]}]}]
    document["scenes"]["main"]["children"] = children
    _, saved = roundtrip(tmp_path, monkeypatch, document)
    assert saved["states"] == document["states"]
    assert saved["scenes"]["main"]["children"] == children


def test_reload_and_scene_replacement_do_not_leak_metadata(tmp_path, monkeypatch, document):
    designer, _ = roundtrip(tmp_path, monkeypatch, document)
    designer.create_scene("main")
    output = tmp_path / "replaced.json"
    designer.save_to_json(str(output))
    assert "code_blocks" not in json.loads(output.read_text())["scenes"]["main"]
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps({"scenes": {"fresh": {"widgets": []}}}))
    designer.load_from_json(str(clean))
    designer.save_to_json(str(output))
    saved = json.loads(output.read_text())
    assert "code_blocks" not in saved
    assert "device" not in saved
    assert list(saved["scenes"]) == ["fresh"]


def test_studio_root_widgets_are_explicitly_refused(tmp_path, document):
    source = tmp_path / "studio.json"
    source.write_text(
        json.dumps(
            {"widgets": document["scenes"]["main"]["widgets"], "states": ["error", "unavailable"]}
        )
    )
    with pytest.raises(WidgetValidationError, match="root widgets are unsupported"):
        UIDesigner().load_from_json(str(source))


def test_duplicate_scene_ids_are_explicitly_refused(tmp_path, document):
    scene = dict(document["scenes"]["main"], id="duplicate")
    source = tmp_path / "duplicates.json"
    source.write_text(json.dumps({"scenes": [scene, scene]}))
    with pytest.raises(WidgetValidationError, match="duplicate scene id"):
        UIDesigner().load_from_json(str(source))


def test_undo_redo_preserve_loaded_scene_profile_and_opaque_code(tmp_path, monkeypatch, document):
    designer, _ = roundtrip(tmp_path, monkeypatch, document)
    # Keep the regression entirely within its private directory.
    monkeypatch.setattr(designer, "_write_backup_snapshot", lambda state: None)
    designer._save_state()
    designer.scenes["main"].widgets[0].text = "After undo snapshot"
    for operation, expected_text in (
        (designer.undo, "Edited"),
        (designer.redo, "After undo snapshot"),
    ):
        assert operation()
        output = tmp_path / "history.json"
        designer.save_to_json(str(output))
        saved = json.loads(output.read_text(encoding="utf-8"))
        scene = saved["scenes"]["main"]
        assert scene["widgets"][0]["text"] == expected_text
        for key in ("theme", "hardware_profile", "max_fb_kb", "max_flash_kb", "code_blocks"):
            assert scene[key] == document["scenes"]["main"][key], key
