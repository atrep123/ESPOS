"""Registry contracts using production profiles; no simulated hardware."""

import json
from dataclasses import replace

import pytest

from espos_targets import TargetProfile, TargetRegistry, TargetRegistryError, load_registry
from ui_designer import HARDWARE_PROFILES


@pytest.mark.parametrize("profile_id", HARDWARE_PROFILES)
def test_actual_profiles_keep_ids_and_metadata(profile_id):
    target = load_registry().get(profile_id)
    source = HARDWARE_PROFILES[profile_id]
    assert (target.width, target.height, target.color_depth, target.label) == (
        source["width"],
        source["height"],
        source["color_depth"],
        source["label"],
    )
    assert TargetProfile.from_dict(json.loads(json.dumps(target.to_dict()))) == target


def test_registry_schema_roundtrip_preserves_all_existing_ids():
    original = load_registry()
    encoded = json.loads(json.dumps(original.to_dict()))
    restored = TargetRegistry.from_dict(encoded)
    assert restored.ids() == tuple(HARDWARE_PROFILES)
    assert restored.to_dict() == original.to_dict()


def test_runtime_and_export_support_are_independent():
    registry = load_registry()
    tab5 = registry.get("tab5_1280x720")
    assert (tab5.runtime, tab5.input_kind, tab5.codegen) == ("tabos_lvgl", "touch", "unavailable")
    assert "ui_scene_c_export" not in tab5.capabilities
    assert registry.get("esp32os_256x128_gray4").input_kind == "focus_navigation"
    assert registry.get("tft_320x240").runtime == "unavailable"
    assert registry.get("tft_320x240").input_kind == "unavailable"
    assert not any(
        "simulator" in c for p in registry.to_dict()["profiles"] for c in p["capabilities"]
    )


@pytest.mark.parametrize("profile_id", ["missing", "tab5", "", None, []])
def test_unknown_profile_is_explicit_error(profile_id):
    with pytest.raises(TargetRegistryError, match="unknown profile"):
        load_registry().get(profile_id)


def test_duplicate_registration_and_serialized_duplicate_are_errors():
    registry = load_registry()
    with pytest.raises(TargetRegistryError, match="duplicate profile"):
        registry.register(registry.get(registry.ids()[0]))
    document = registry.to_dict()
    document["profiles"].append(document["profiles"][0])
    with pytest.raises(TargetRegistryError, match="duplicate profile"):
        TargetRegistry.from_dict(document)


@pytest.mark.parametrize("field", ["width", "height"])
@pytest.mark.parametrize("value", [0, -1, 65536, True, 1.5, float("inf"), float("nan"), "128"])
def test_dimension_bounds(field, value):
    with pytest.raises(TargetRegistryError):
        replace(load_registry().get("tab5_1280x720"), **{field: value})


def test_bounds_and_new_profile_extension():
    base = load_registry().get("oled_128x64")
    extension = replace(base, profile_id="test_canvas", width=1, height=65535)
    registry = TargetRegistry([extension])
    assert registry.get("test_canvas") == extension


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("profile_id", "Bad id"),
        ("label", ""),
        ("color_depth", True),
        ("color_depth", 24),
        ("color_model", "rgb888"),
        ("input_kind", "imaginary"),
        ("runtime", "imaginary"),
        ("codegen", "imaginary"),
        ("capabilities", ("wifi",)),
        ("capabilities", ("display_profile", "display_profile")),
        ("capabilities", ("display_profile",)),
        ("input_kind", []),
        ("runtime", {}),
        ("codegen", []),
    ],
)
def test_invalid_metadata(field, value):
    with pytest.raises(TargetRegistryError):
        replace(load_registry().get("oled_128x64"), **{field: value})


@pytest.mark.parametrize("version", [0, 2, True, "1"])
def test_unknown_schema_version(version):
    document = load_registry().to_dict()
    document["schema_version"] = version
    with pytest.raises(TargetRegistryError):
        TargetRegistry.from_dict(document)


def test_unknown_fields_and_wrong_arrays_fail():
    document = load_registry().to_dict()
    document["profiles"][0]["hardware_verified"] = True
    with pytest.raises(TargetRegistryError):
        TargetRegistry.from_dict(document)
    document = load_registry().to_dict()
    document["profiles"][0]["capabilities"] = "display_profile"
    with pytest.raises(TargetRegistryError):
        TargetRegistry.from_dict(document)


def test_existing_mcp_display_board_profiles_resolve_without_new_board_claims():
    from board_registry import load_registry as load_boards

    targets = load_registry()
    for board in load_boards().boards:
        if board.has_display:
            profile = targets.get(board.display_profile)
            assert (profile.width, profile.height, profile.color_depth) == (
                board.display.w,
                board.display.h,
                board.display.depth,
            )
        else:
            assert board.display_profile is None
        assert board.id not in targets.ids()
