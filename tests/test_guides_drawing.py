from ui_designer import SceneConfig, UIDesigner


def _blank_canvas(scene: SceneConfig) -> list[list[str]]:
    return [[" " for _ in range(scene.width)] for _ in range(scene.height)]


def test_draw_guides_vertical_and_horizontal():
    designer = UIDesigner(10, 6)
    scene = designer.create_scene("main")
    designer.show_guides = True
    designer.last_guides = [
        {"type": "v", "x": 2, "y1": 0, "y2": 5},
        {"type": "h", "y": 3, "x1": 0, "x2": 9},
    ]
    canvas = _blank_canvas(scene)

    designer._draw_guides(canvas, scene)

    assert all(canvas[y][2] == ("-" if y == 3 else "|") for y in range(scene.height))
    assert all(canvas[3][x] == "-" for x in range(scene.width))


def test_draw_center_guides_split_by_orientation():
    designer = UIDesigner(6, 4)
    scene = designer.create_scene("center")
    designer.show_guides = True
    designer.last_guides = [
        {"type": "v", "x": 1, "y1": 0, "y2": 3, "k": "C"},
        {"type": "h", "y": 2, "x1": 0, "x2": 5, "k": "C"},
    ]
    canvas = _blank_canvas(scene)

    designer._draw_guides(canvas, scene)

    assert all(canvas[y][1] == ("-" if y == 2 else "|") for y in range(scene.height))
    assert all(canvas[2][x] == "-" for x in range(scene.width))


def test_draw_guides_early_returns_on_empty():
    designer = UIDesigner(4, 2)
    scene = designer.create_scene("none")
    designer.show_guides = True
    designer.last_guides = []
    canvas = _blank_canvas(scene)

    designer._draw_guides(canvas, scene)

    assert all(cell == " " for row in canvas for cell in row)
