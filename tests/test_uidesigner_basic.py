import json
from pathlib import Path

from ui_designer import UIDesigner, WidgetConfig, WidgetType


def test_uidesigner_create_and_save(tmp_path: Path):
    json_path = tmp_path / "scene.json"

    designer = UIDesigner(320, 240)
    designer.create_scene("main")
    designer.add_widget(WidgetType.LABEL, x=10, y=10, width=40, height=10, text="Hello")
    designer.add_widget(WidgetType.BUTTON, x=20, y=30, width=60, height=14, text="Click")
    designer.add_widget(WidgetType.PROGRESSBAR, x=20, y=50, width=80, height=8, value=50)

    designer.save_to_json(json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["width"] == 320
    assert data["height"] == 240
    assert "main" in data["scenes"]
    scene = data["scenes"]["main"]
    assert scene["width"] == 320
    assert scene["height"] == 240
    assert len(scene["widgets"]) == 3
    types = [w["type"] for w in scene["widgets"]]
    assert types == ["label", "button", "progressbar"]


def test_uidesigner_load_roundtrip(tmp_path: Path):
    # Prepare a JSON manually
    json_path = tmp_path / "scene.json"
    payload = {
        "width": 200,
        "height": 100,
        "scenes": {
            "main": {
                "name": "main",
                "width": 200,
                "height": 100,
                "bg_color": "#000000",
                "widgets": [
                    {"type": "label", "x": 1, "y": 2, "width": 30, "height": 10, "text": "A"},
                    {"type": "button", "x": 5, "y": 20, "width": 40, "height": 12, "text": "B"},
                ],
            }
        },
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    designer = UIDesigner()
    designer.load_from_json(json_path)

    assert designer.width == 200
    assert designer.height == 100
    assert designer.current_scene == "main"
    sc = designer.scenes["main"]
    assert len(sc.widgets) == 2
    assert sc.widgets[0].type == "label"
    assert sc.widgets[1].type == "button"


def test_uidesigner_groups_roundtrip(tmp_path: Path):
    json_path = tmp_path / "scene.json"

    designer = UIDesigner(64, 32)
    designer.create_scene("main")
    designer.add_widget("label", x=1, y=1, width=10, height=3, text="A")
    designer.add_widget("button", x=1, y=6, width=12, height=4, text="B")
    assert designer.create_group("group1", [0, 1])

    designer.save_to_json(json_path)

    loaded = UIDesigner()
    loaded.load_from_json(json_path)
    assert loaded.groups.get("group1") == [0, 1]


def test_hardware_profile_and_estimation():
    designer = UIDesigner(128, 64)
    designer.create_scene("main")
    designer.set_hardware_profile("oled_128x64")
    est = designer.estimate_resources()
    # 1bpp framebuffer
    assert int(est["framebuffer_bytes"]) == (128 * 64 + 7) // 8
    assert est["profile"] == "oled_128x64"


def test_preview_ascii_text_is_clipped_to_widget_box():
    designer = UIDesigner(30, 6)
    designer.create_scene("main")
    designer.current_scene = "main"
    sc = designer.scenes["main"]
    sc.widgets.clear()

    # Long label next to another bordered widget: text must not overwrite neighbour's border.
    sc.widgets.append(
        WidgetConfig(type="label", x=1, y=1, width=10, height=3, text="ABCDEFGHIJKLMN", border=True, border_style="single")
    )
    sc.widgets.append(WidgetConfig(type="box", x=12, y=1, width=10, height=3, text="", border=True, border_style="single"))

    out = designer.preview_ascii("main", show_grid=False)
    lines = out.splitlines()
    assert lines[2][12] == "|"


def test_preview_ascii_text_wraps_when_enabled():
    designer = UIDesigner(20, 8)
    designer.create_scene("main")
    designer.current_scene = "main"
    sc = designer.scenes["main"]
    sc.widgets.clear()

    sc.widgets.append(
        WidgetConfig(
            type="label",
            x=1,
            y=1,
            width=12,
            height=4,
            text="HELLO WORLD",
            border=True,
            border_style="single",
            text_overflow="wrap",
        )
    )

    out = designer.preview_ascii("main", show_grid=False)
    lines = out.splitlines()
    # Inner text box starts at x=1 + border(1) + padding_x(1) = 3, y=1 + border(1) + padding_y(0) = 2
    assert lines[2][3:8] == "HELLO"
    assert lines[3][3:8] == "WORLD"
