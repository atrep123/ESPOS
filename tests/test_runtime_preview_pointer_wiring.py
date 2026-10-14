"""Actual outer editor pointer methods with inert collaborators, no GUI import."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


class Rect:
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

    def collidepoint(self, *pos):
        x, y = pos[0] if len(pos) == 1 else pos
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


@pytest.fixture
def app():
    tree = ast.parse((ROOT / "cyberpunk_designer/app.py").read_text(encoding="utf-8"))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CyberpunkEditorApp"
    )
    names = {
        "_dispatch_event",
        "_dispatch_mouse_down",
        "_handle_left_click",
        "_runtime_pointer_is_view_only",
    }
    cls.body = [
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    pygame = SimpleNamespace(
        event=SimpleNamespace(Event=object),
        QUIT=1,
        VIDEORESIZE=2,
        KEYDOWN=3,
        MOUSEBUTTONDOWN=4,
        MOUSEBUTTONUP=5,
        MOUSEMOTION=6,
        MOUSEWHEEL=7,
        TEXTINPUT=8,
    )
    calls = {
        "dirty": [],
        "down": [],
        "up": [],
        "move": [],
        "wheel": [],
        "double": [],
        "context": [],
        "pan": [],
    }
    namespace = {
        "pygame": pygame,
        "time": SimpleNamespace(time=lambda: 10.0),
        "DBLCLICK_SEC": 0.4,
        "DBLCLICK_PX": 6,
        "windowing": SimpleNamespace(
            pan_drag_start=lambda *args: calls["pan"].append(args), pan_drag_end=lambda *args: None
        ),
    }
    module = ast.Module(body=[cls], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, "TEST_ONLY-actual-editor-pointer", "exec"), namespace)  # noqa: S102 -- trusted source AST, inert collaborators
    value = namespace["CyberpunkEditorApp"]()
    value._dirty = value._force_full_redraw = False
    value._dirty_scenes = {"existing-edit"}
    value._runtime_preview_hitbox = Rect(40, 40, 80, 40)
    value._view_only_pointer_down = value._view_only_wheel = False
    value._context_menu = None
    value.sim_input_mode = False
    value.pointer_down, value.pointer_pos = False, (0, 0)
    value.state = SimpleNamespace(dragging=False, resizing=False, box_select_start=None)
    value.layout = SimpleNamespace(scene_tabs_rect=Rect(0, 0, 0, 0))
    value.toolbar_scroll_hitboxes = [(Rect(0, 0, 30, 20), 2)]
    value._screen_to_logical = lambda pos: pos
    value._mark_dirty = lambda: calls["dirty"].append("authored")
    value._handle_double_click = calls["double"].append
    value._open_context_menu = calls["context"].append

    def down(pos):
        calls["down"].append(pos)
        value._view_only_pointer_down = value._runtime_preview_hitbox.collidepoint(pos) or any(
            rect.collidepoint(pos) for rect, _ in value.toolbar_scroll_hitboxes
        )

    def up(pos):
        calls["up"].append(pos)
        value._view_only_pointer_down = False
        value.state.dragging = value.state.resizing = False
        value.state.box_select_start = None

    value._on_mouse_down, value._on_mouse_up = down, up
    value._on_mouse_move = lambda pos, buttons: calls["move"].append((pos, buttons))
    value._on_mouse_wheel = lambda dx, dy: calls["wheel"].append((dx, dy))
    return value, calls, pygame


@pytest.mark.parametrize("point", [(10, 10), (50, 50)])
def test_navigation_and_snapshot_press_motion_release_do_not_dirty_author(app, point):
    value, calls, pygame = app
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=point))
    assert value._view_only_pointer_down
    value._dispatch_event(
        SimpleNamespace(type=pygame.MOUSEMOTION, pos=(200, 200), buttons=(1, 0, 0))
    )
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(200, 200)))
    assert calls["dirty"] == calls["double"] == []
    assert calls["down"] == [point] and calls["up"] == [(200, 200)]
    assert value._dirty_scenes == {"existing-edit"}
    assert value._dirty and value._force_full_redraw
    assert not value._view_only_pointer_down and not value.pointer_down


def test_repeated_navigation_press_never_enters_widget_double_click(app):
    value, calls, pygame = app
    value._last_click_time, value._last_click_pos = 10.0, (10, 10)
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
    assert calls["down"] == [(10, 10)] and calls["double"] == calls["dirty"] == []


def test_snapshot_hover_and_unowned_release_are_view_only(app):
    value, calls, pygame = app
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEMOTION, pos=(50, 50), buttons=(0, 0, 0)))
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(50, 50)))
    assert calls["dirty"] == [] and calls["up"] == [(50, 50)]


@pytest.mark.parametrize(
    "gesture", ["dragging", "resizing", "box-select", "tab-drag", "layer-drag", "pan"]
)
def test_existing_outside_gesture_keeps_its_authored_release(app, gesture):
    value, calls, pygame = app
    if gesture in ("dragging", "resizing"):
        setattr(value.state, gesture, True)
    elif gesture == "box-select":
        value.state.box_select_start = (0, 0)
    else:
        setattr(
            value,
            {"tab-drag": "_tab_drag_idx", "layer-drag": "_layer_drag_idx", "pan": "_pan_drag_from"}[
                gesture
            ],
            0,
        )
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(50, 50)))
    assert calls["up"] == [(50, 50)] and calls["dirty"] == ["authored"]


@pytest.mark.parametrize("captured", [True, False])
def test_wheel_dispatch_honors_actual_handler_view_only_outcome(app, captured):
    value, calls, pygame = app

    def wheel(dx, dy):
        calls["wheel"].append((dx, dy))
        value._view_only_wheel = captured

    value._on_mouse_wheel = wheel
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=1))
    assert calls["wheel"] == [(0, 1)]
    assert calls["dirty"] == ([] if captured else ["authored"])


@pytest.mark.parametrize("button", [2, 3])
def test_read_only_snapshot_cannot_start_pan_or_underlying_context_menu(app, button):
    value, calls, pygame = app
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=button, pos=(50, 50)))
    assert calls["context"] == calls["pan"] == calls["dirty"] == []
    assert value._dirty and value._force_full_redraw


def test_normal_authored_click_remains_compatible(app):
    value, calls, pygame = app
    value._dispatch_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 200)))
    assert calls["down"] == [(200, 200)] and calls["dirty"] == ["authored"]
