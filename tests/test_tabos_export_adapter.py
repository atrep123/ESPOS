"""Test-only scenes and opaque code; no production actions are fabricated."""

import copy
import json
import os

import pytest

from tools.tabos_export_adapter import AdapterError, adapt_document


def document():
    return {
        "width": 1280,
        "height": 720,
        "scenes": {
            "main": {
                "widgets": [
                    {
                        "_widget_id": "label.0",
                        "type": "label",
                        "x": 10,
                        "y": 10,
                        "width": 300,
                        "height": 40,
                        "text": "Český text",
                        "font_size": 16,
                    },
                    {
                        "id": "button.0",
                        "type": "button",
                        "x": 10,
                        "y": 100,
                        "width": 120,
                        "height": 81,
                        "text": "Test",
                    },
                ]
            }
        },
    }


def metadata():
    return {
        "actions": {"button.0": "test:explicit"},
        "states": [
            {"kind": "error", "description": "test-only actual error design"},
            {"kind": "unavailable", "description": "test-only unavailable design"},
        ],
    }


def test_conversion_source_and_supported_construct_roundtrip():
    source = document()
    source["code_blocks"] = [{"language": "undecided", "source": "opaque\n{}"}]
    source["scenes"]["other"] = {"future": "not exported, retained in source"}
    original = copy.deepcopy(source)
    raw = json.dumps(source, ensure_ascii=False, indent=3).encode("utf-8")
    exported = adapt_document(raw, "main", **metadata())
    assert exported.source_bytes == raw
    assert exported.restore_document() == original
    assert source == original
    assert exported.scene["widgets"][0]["font_px"] == 16
    assert exported.scene["widgets"][1]["action"] == "test:explicit"
    assert "code_blocks" not in exported.scene
    assert exported.restore_document()["code_blocks"] == source["code_blocks"]
    exported.restore_document()["scenes"].clear()
    assert exported.restore_document() == original


def test_injective_ids_are_stable_under_reorder_and_punctuation():
    source = document()
    source["scenes"]["main"]["widgets"] = [
        dict(source["scenes"]["main"]["widgets"][0], _widget_id=wid)
        for wid in ["a.b", "a_b", "w_612e62", "ž", "1"]
    ]
    kwargs = {"states": metadata()["states"]}
    first = adapt_document(source, "main", **kwargs)
    source["scenes"]["main"]["widgets"].reverse()
    assert adapt_document(source, "main", **kwargs).id_map == first.id_map
    assert len(set(first.id_map.values())) == 5


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("color_fg", "#ffffff"),
        ("style", "default"),
        ("rules", []),
        ("children", []),
        ("parent_id", "parent"),
        ("future", {}),
        ("type", "chart"),
        ("font_size", float("inf")),
        ("font_size", True),
        ("width", 0),
        ("x", -1),
        ("z_index", float("nan")),
    ],
)
def test_unsupported_or_invalid_widget_never_returns_partial_success(field, value):
    source = document()
    source["scenes"]["main"]["widgets"][0][field] = value
    before = copy.deepcopy(source)
    with pytest.raises(AdapterError) as failure:
        adapt_document(source, "main", **metadata())
    assert failure.value.diagnostics
    assert source.keys() == before.keys()
    assert source["scenes"]["main"]["widgets"][1] == before["scenes"]["main"]["widgets"][1]


def test_unknown_root_and_scene_metadata_reported_together():
    source = document()
    source["future"] = {"important": True}
    source["scenes"]["main"]["rules"] = ["important"]
    with pytest.raises(AdapterError) as failure:
        adapt_document(source, "main", **metadata())
    assert any("document.future" in d for d in failure.value.diagnostics)
    assert any("scene.rules" in d for d in failure.value.diagnostics)


def test_missing_states_actions_and_conflicting_metadata_are_errors():
    with pytest.raises(AdapterError, match="states"):
        adapt_document(document(), "main")
    with pytest.raises(AdapterError, match="real action"):
        adapt_document(document(), "main", states=metadata()["states"])
    source = document()
    source["scenes"]["main"]["widgets"][1]["action"] = "test:source"
    with pytest.raises(AdapterError, match="conflicts"):
        adapt_document(source, "main", **metadata())


def test_duplicate_source_ids_and_json_keys_are_rejected():
    source = document()
    source["scenes"]["main"]["widgets"][1]["id"] = "label.0"
    with pytest.raises(AdapterError, match="duplicate source"):
        adapt_document(source, "main", **metadata())
    with pytest.raises(AdapterError, match="duplicate key"):
        adapt_document(b'{"scenes":{},"scenes":{}}', "main", **metadata())


def test_array_selection_is_explicit_and_unique():
    source = document()
    scene = source["scenes"]["main"]
    scene["name"] = "main"
    source["scenes"] = [scene]
    assert adapt_document(source, "main", **metadata()).scene["name"] == "main"
    source["scenes"].append(copy.deepcopy(scene))
    with pytest.raises(AdapterError, match="exactly once"):
        adapt_document(source, "main", **metadata())


def test_explicit_missing_studio_root_has_no_fallback(tmp_path):
    with pytest.raises(AdapterError, match="studio_root"):
        adapt_document(document(), "main", studio_root=tmp_path, **metadata())


def test_text_source_and_object_are_detached_from_export():
    source = document()
    text = json.dumps(source, indent=4)
    assert adapt_document(text, "main", **metadata()).source_text == text
    exported = adapt_document(source, "main", **metadata())
    exported.scene["widgets"][0]["text"] = "edited export"
    assert source["scenes"]["main"]["widgets"][0]["text"] == "Český text"
    source["scenes"]["main"]["widgets"][0]["text"] = "later source edit"
    assert exported.restore_document()["scenes"]["main"]["widgets"][0]["text"] == "Český text"


@pytest.mark.parametrize("height", [80, True, 10**400, float("inf")])
def test_interactive_numeric_bounds(height):
    source = document()
    source["scenes"]["main"]["widgets"][1]["height"] = height
    with pytest.raises(AdapterError):
        adapt_document(source, "main", **metadata())


@pytest.mark.parametrize(
    "states",
    [
        [],
        [{"kind": "error"}],
        [{"kind": "error", "handler": "opaque-unsupported"}, {"kind": "unavailable"}],
    ],
)
def test_incomplete_or_unknown_state_metadata_is_not_erased(states):
    with pytest.raises(AdapterError):
        adapt_document(document(), "main", actions=metadata()["actions"], states=states)


def test_unused_actions_conflicting_ids_and_group_semantics_fail():
    source = document()
    kwargs = metadata()
    kwargs["actions"]["unknown"] = "test:unused"
    with pytest.raises(AdapterError, match="unused metadata"):
        adapt_document(source, "main", **kwargs)
    source["scenes"]["main"]["widgets"][0]["id"] = "different"
    source["groups"] = {"main": {"group": ["label.0"]}}
    with pytest.raises(AdapterError) as failure:
        adapt_document(source, "main", **metadata())
    assert any("aliases conflict" in d for d in failure.value.diagnostics)
    assert any("group semantics" in d for d in failure.value.diagnostics)


def test_all_exact_supported_types_preserve_flat_geometry_and_explicit_source_metadata():
    source = document()
    scene = source["scenes"]["main"]
    scene["states"] = metadata()["states"]
    scene["code_blocks"] = {"opaque": "no language decision"}
    scene["widgets"][1]["action"] = "test:explicit"
    scene["widgets"] += [
        {
            "id": "container",
            "type": "container",
            "x": 400,
            "y": 10,
            "width": 300,
            "height": 100,
            "z_index": -1,
        },
        {
            "id": "tile",
            "type": "tile",
            "x": 800,
            "y": 100,
            "width": 120,
            "height": 81,
            "action": "test:tile",
        },
    ]
    exported = adapt_document(source, "main")
    assert [w["type"] for w in exported.scene["widgets"]] == [
        "label",
        "button",
        "container",
        "tile",
    ]
    assert exported.scene["widgets"][2]["x"] == 400
    assert exported.scene["widgets"][2]["layer"] == -1
    assert exported.restore_document() == source
    root = os.environ.get("TABOS_STUDIO_ROOT")
    if root is not None:
        assert "lv_button_create" in adapt_document(source, "main", studio_root=root).generated_cpp


def test_actual_studio_validator_and_generator_when_root_explicit():
    root = os.environ.get("TABOS_STUDIO_ROOT")
    if root is None:
        pytest.skip("actual Studio integration unverified: supply TABOS_STUDIO_ROOT")
    exported = adapt_document(document(), "main", studio_root=root, **metadata())
    assert "lv_obj_t* build(" in exported.generated_cpp
    assert "LVGL_VERSION_PATCH != 2" in exported.generated_cpp
    # Validator catches same-layer overlap; adapter must not return success.
    source = document()
    source["scenes"]["main"]["widgets"][1]["y"] = 10
    with pytest.raises(AdapterError, match="Studio"):
        adapt_document(source, "main", studio_root=root, **metadata())


@pytest.mark.parametrize("as_json", [False, True])
def test_deep_document_returns_adapter_error(as_json):
    if as_json:
        source = '{"code_blocks":' + "[" * 2000 + "0" + "]" * 2000 + "}"
    else:
        source = document()
        nested = []
        source["code_blocks"] = nested
        for _ in range(2000):
            child = []
            nested.append(child)
            nested = child
    with pytest.raises(AdapterError, match="depth"):
        adapt_document(source, "main", **metadata())


def studio_root():
    root = os.environ.get("TABOS_STUDIO_ROOT")
    if root is None:
        pytest.skip("actual Studio integration unverified: supply TABOS_STUDIO_ROOT")
    return root


@pytest.mark.parametrize(
    ("target", "size", "accepted"),
    [(64, 64, True), (64, 63, False), (96, 96, True), (96, 95, False)],
)
def test_actual_owner_threshold_and_opaque_retention(tmp_path, target, size, accepted):
    tokens = tmp_path / "tokens.json"
    tokens.write_text(json.dumps({"touch": {"target_min_px": target, "hard_floor_px": 58}}))
    source = document()
    source["code_blocks"] = [{"source": "opaque\n{}", "language": "pending"}]
    source["scenes"]["main"]["widgets"][1]["height"] = size
    before = copy.deepcopy(source)
    raw = json.dumps(source, indent=3).encode()
    kwargs = dict(metadata(), studio_root=studio_root(), owner_tokens=tokens)
    if accepted:
        result = adapt_document(raw, "main", **kwargs)
        assert result.generated_cpp and result.source_bytes == raw
        assert result.restore_document() == before
        assert adapt_document(source, "main", **kwargs).restore_document() == before
    else:
        with pytest.raises(AdapterError, match="Studio"):
            adapt_document(source, "main", **kwargs)
    assert source == before


@pytest.mark.parametrize(
    "content",
    [
        None,
        "not-json",
        "{}",
        '{"touch":{"target_min_px":64,"hard_floor_px":65}}',
        '{"touch":{"target_min_px":true,"hard_floor_px":58}}',
    ],
)
def test_owner_tokens_missing_or_invalid_never_fall_back(tmp_path, content):
    tokens = tmp_path / "tokens.json"
    if content is not None:
        tokens.write_text(content)
    source = document()
    before = copy.deepcopy(source)
    with pytest.raises(AdapterError, match="Studio"):
        adapt_document(source, "main", studio_root=studio_root(), owner_tokens=tokens, **metadata())
    assert source == before


def test_tokens_require_explicit_studio_root(tmp_path):
    with pytest.raises(AdapterError, match="studio_root"):
        adapt_document(document(), "main", owner_tokens=tmp_path / "tokens.json", **metadata())


@pytest.mark.parametrize("with_studio", [False, True])
@pytest.mark.parametrize(("height", "accepted"), [(80, False), (81, True)])
def test_omitted_tokens_preserve_standalone_snapshot(height, accepted, with_studio):
    source = document()
    source["scenes"]["main"]["widgets"][1]["height"] = height
    kwargs = dict(metadata(), studio_root=studio_root() if with_studio else None)
    if accepted:
        assert adapt_document(source, "main", **kwargs).scene["widgets"][1]["h"] == height
    else:
        with pytest.raises(AdapterError):
            adapt_document(source, "main", **kwargs)


def test_cyclic_opaque_metadata_is_bounded_error():
    source = document()
    source["code_blocks"] = source
    with pytest.raises(AdapterError, match="cyclic"):
        adapt_document(source, "main", **metadata())
    assert source["code_blocks"] is source


@pytest.mark.parametrize("source", [None, 1, [], b'{"scenes":', b"\xff"])
def test_malformed_document_is_adapter_error(source):
    with pytest.raises(AdapterError):
        adapt_document(source, "main", **metadata())
