from pathlib import Path

from tools.ui_codegen import (
    border_style_for,
    generate_scenes_header,
    generate_ui_design_multi_pair,
    generate_ui_design_pair,
)
from tools.validate_design import validate_file


def test_generate_ui_design_pair_smoke():
    c_text, h_text = generate_ui_design_pair(
        Path("main_scene.json"),
        scene_name="main",
        source_label="main_scene.json",
    )
    assert "const UiScene ui_design" in c_text
    assert "extern const UiScene ui_design" in h_text
    assert "UIW_BUTTON" in c_text
    assert ".border_style = UI_BORDER_NONE" in c_text


def test_generate_scenes_header_smoke():
    header = generate_scenes_header(
        Path("main_scene.json"),
        guard="TEST_UI_H",
        source_name="main_scene.json",
        generated_ts="TS",
    )
    assert "#ifndef TEST_UI_H" in header
    assert "static const UiScene *all_scenes[]" in header
    assert "#define UI_SCENE_COUNT" in header


def test_border_style_for_respects_border_flag():
    assert border_style_for({"border_style": "single"}, border=0) == "UI_BORDER_NONE"
    assert border_style_for({"border_style": "single"}, border=1) == "UI_BORDER_SINGLE"


def test_validate_main_scene_json_no_errors():
    issues = validate_file(Path("main_scene.json"), warnings_as_errors=False)
    errors = [i for i in issues if i.level == "ERROR"]
    assert errors == [], f"Validation errors: {errors}"


def test_generate_ui_design_multi_pair_smoke(tmp_path):
    """Multi-scene export with a small 2-scene fixture."""
    scene_json = tmp_path / "multi.json"
    scene_json.write_text(
        '{"scenes":{"alpha":{"width":256,"height":128,"widgets":[{"type":"label","x":0,"y":0,"width":40,"height":10,"text":"Hello"}]},'
        '"beta":{"width":256,"height":128,"widgets":[{"type":"button","x":10,"y":20,"width":60,"height":12,"text":"OK","id":"btn_ok"}]}}}'
    )
    c_text, h_text = generate_ui_design_multi_pair(scene_json, source_label="multi.json")
    # Header checks
    assert "#define UI_SCENE_COUNT 2" in h_text
    assert "#define UI_SCENE_IDX_ALPHA 0" in h_text
    assert "#define UI_SCENE_IDX_BETA 1" in h_text
    assert "extern const UiScene ui_scenes[]" in h_text
    assert "#define UI_SCENE_DEMO ui_scenes[0]" in h_text
    # Source checks
    assert "const UiScene ui_scenes[]" in c_text
    assert "alpha_widgets" in c_text
    assert "beta_widgets" in c_text
    assert 'UIW_LABEL' in c_text
    assert 'UIW_BUTTON' in c_text
    assert '"Hello"' in c_text
    assert '"OK"' in c_text


def test_generate_ui_design_multi_pair_rc_scene():
    """Multi-scene export with the full RC scene JSON (9 scenes)."""
    rc = Path("rc_scene.json")
    if not rc.exists():
        import pytest
        pytest.skip("rc_scene.json not found")
    c_text, h_text = generate_ui_design_multi_pair(rc, source_label="rc_scene.json")
    assert "#define UI_SCENE_COUNT 9" in h_text
    assert "#define UI_SCENE_IDX_RC_MAIN 0" in h_text
    assert "extern const UiScene ui_scenes[]" in h_text
    assert "const UiScene ui_scenes[]" in c_text
    # Every scene should have a widget array
    assert "rc_main_widgets" in c_text
    assert "rc_channels_widgets" in c_text
    assert "rc_telemetry_widgets" in c_text

