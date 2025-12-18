from pathlib import Path

from tools.ui_codegen import border_style_for, generate_scenes_header, generate_ui_design_pair
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


def test_validate_main_scene_json_is_clean():
    issues = validate_file(Path("main_scene.json"), warnings_as_errors=False)
    assert issues == []

