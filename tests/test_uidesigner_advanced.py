import json
from pathlib import Path

from ui_designer import UIDesigner, WidgetType


def test_undo_redo_add_delete(tmp_path: Path):
    designer = UIDesigner(200, 100)
    designer.create_scene("main")

    designer.add_widget(WidgetType.LABEL, x=0, y=0, width=10, height=10, text="A")
    designer.add_widget(WidgetType.BUTTON, x=10, y=10, width=20, height=10, text="B")
    sc = designer.scenes["main"]
    assert len(sc.widgets) == 2

    designer.delete_widget(1)
    assert len(sc.widgets) == 1
    assert sc.widgets[0].text == "A"

    assert designer.undo()  # restore deleted button
    assert len(designer.scenes["main"].widgets) == 2
    assert designer.scenes["main"].widgets[1].text == "B"

    assert designer.redo()  # redo deletion
    assert len(designer.scenes["main"].widgets) == 1


def test_move_respects_lock_and_snap(tmp_path: Path):
    designer = UIDesigner(200, 100)
    designer.create_scene("main")
    designer.snap_to_grid = False  # avoid snapping for precise move
    designer.add_widget(WidgetType.BOX, x=5, y=5, width=10, height=10)
    sc = designer.scenes["main"]
    w = sc.widgets[0]

    designer.move_widget(0, 3, 4)
    assert (w.x, w.y) == (8, 9)

    w.locked = True
    designer.move_widget(0, 10, 10)
    # locked widget should not move
    assert (w.x, w.y) == (8, 9)


def test_save_and_load_roundtrip(tmp_path: Path):
    json_path = tmp_path / "roundtrip.json"
    designer = UIDesigner(150, 90)
    designer.create_scene("main")
    designer.add_widget(WidgetType.SLIDER, x=1, y=2, width=30, height=8, value=25)
    designer.save_to_json(json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["width"] == 150 and data["height"] == 90
    assert len(data["scenes"]["main"]["widgets"]) == 1

    d2 = UIDesigner()
    d2.load_from_json(json_path)
    assert d2.width == 150 and d2.height == 90
    sc = d2.scenes["main"]
    assert len(sc.widgets) == 1
    assert sc.widgets[0].type == "slider"
    assert sc.widgets[0].value == 25
