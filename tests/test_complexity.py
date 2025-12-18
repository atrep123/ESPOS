import sys
from dataclasses import asdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_designer import UIDesigner, WidgetConfig


def test_generate_imports_and_scene_init_helpers():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    sc.widgets.append(WidgetConfig(type="label", x=1, y=2, width=3, height=4, text="hi"))
    imports = d._generate_imports(sc)
    assert any("dataclass" in ln for ln in imports)
    scene_lines = d._generate_scene_init(sc)
    assert f"create_{sc.name.lower()}_scene" in "\n".join(scene_lines)


def test_calculate_center_helper():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=4, height=4))
    sc.widgets.append(WidgetConfig(type="box", x=6, y=6, width=2, height=2))
    avg_x = d._calculate_center(sc.widgets, axis="x")
    avg_y = d._calculate_center(sc.widgets, axis="y")
    assert isinstance(avg_x, int) and isinstance(avg_y, int)


def test_html_helpers_build_document(tmp_path):
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    html = d._build_html_export(sc, "X")
    assert "<html" in html and "X" in html and sc.name in html
    colors = d._html_colors()
    styles = d._html_styles(colors)
    assert any("body" in line for line in styles)


def test_resource_helpers_and_over_limits():
    d = UIDesigner(10, 10)
    assert d._resolve_color_depth(4, None) == 4
    assert d._resolve_color_depth(None, {"color_depth": 2}) == 2
    assert d._framebuffer_bytes(16, 1) == 2
    assert d._framebuffer_bytes(16, 8) == 16
    assert d._text_bytes([WidgetConfig(type="label", text="hi", x=0, y=0, width=1, height=1)]) == 2
    assert d._over_limit(2048, 1.0) is True


def test_scene_building_helpers():
    d = UIDesigner(10, 10)
    data = {"scenes": {"main": {"widgets": [{"id": "w1", "type": "box", "x": 0, "y": 0, "width": 1, "height": 1}]}}}
    scenes_dict = d._scenes_dict_from_data(data["scenes"], data)
    assert "main" in scenes_dict
    widgets = d._widgets_for_scene(data, "main")
    assert widgets[0]._widget_id == "w1"


def test_baseline_and_alignment_helpers():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    w = WidgetConfig(type="box", x=1, y=1, width=2, height=2)
    sc.widgets.append(w)
    baseline = d._baseline_for_widget(w, sc)
    assert baseline is not None
    action = d._alignment_action("left", [w])
    assert action is not None


def test_record_guides_helpers():
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    d.last_guides = []
    d._record_vertical_guide((1, -5, 20, "k"), sc)
    d._record_horizontal_guide((2, -1, 5, "k"), sc)
    assert any(g["type"] == "v" for g in d.last_guides)
    assert any(g["type"] == "h" for g in d.last_guides)


def test_undo_helpers_push_and_history(tmp_path):
    d = UIDesigner(10, 10)
    sc = d.create_scene("main")
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=1, height=1))
    payload = {"widgets": [asdict(sc.widgets[0])], "name": "main"}
    d._push_undo_state("{}")
    assert d.undo_stack
    d._record_history_meta(payload)
    d._write_backup_snapshot("{}")
