"""TEST_ONLY source seams: actual AST functions, inert drawing/input, no GUI imports.

Run this file alone with --noconftest. App action declarations are extracted,
never importing the product app, constructing a window, or launching actions.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


class Rect:
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

    left = property(lambda self: self.x)
    top = property(lambda self: self.y)
    right = property(lambda self: self.x + self.width)
    bottom = property(lambda self: self.y + self.height)
    center = property(lambda self: (self.x + self.width // 2, self.y + self.height // 2))

    def collidepoint(self, *pos):
        x, y = pos[0] if len(pos) == 1 else pos
        return self.left <= x < self.right and self.top <= y < self.bottom

    def contains(self, other):
        return (
            self.left <= other.left <= other.right <= self.right
            and self.top <= other.top <= other.bottom <= self.bottom
        )

    def clip(self, other):
        x, y = max(self.left, other.left), max(self.top, other.top)
        return Rect(
            x,
            y,
            max(0, min(self.right, other.right) - x),
            max(0, min(self.bottom, other.bottom) - y),
        )


class Surface:
    def __init__(self):
        self.clip = Rect(0, 0, 4096, 4096)
        self.labels = []
        self.rects = []

    def get_clip(self):
        return self.clip

    def set_clip(self, rect):
        self.clip = rect

    def blit(self, text, pos):
        self.labels.append((text.label, pos, self.clip))


def reject(*args, **kwargs):
    raise AssertionError("Authored action/dirty/selection/inspector seam was invoked")


def source_tree(path):
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def load_functions(path, names, namespace):
    nodes = [
        node
        for node in source_tree(path).body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert {node.name for node in nodes} == set(names)
    future = ast.parse("from __future__ import annotations").body
    module = ast.fix_missing_locations(ast.Module(body=future + nodes, type_ignores=[]))
    exec(compile(module, str(ROOT / path), "exec"), namespace)  # noqa: S102


@pytest.fixture
def seams():
    modal = SimpleNamespace(click=None, wheel=None, calls=[])

    def import_modal(name, _globals=None, _locals=None, fromlist=(), level=0):
        if name == "__future__":
            return builtins.__import__(name, _globals, _locals, fromlist, level)
        assert name == "" and level == 1 and len(fromlist) == 1
        name = fromlist[0]
        assert name in {"icon_palette", "template_manager", "logic_editor", "build_flash"}

        def handle_click(app, pos):
            modal.calls.append((name, "click"))
            return modal.click == name

        def handle_wheel(app, dy):
            modal.calls.append((name, "wheel"))
            return modal.wheel == name

        module = SimpleNamespace(handle_click=handle_click, handle_wheel=handle_wheel)
        return SimpleNamespace(**{name: module})

    def text(app, label, color):
        return SimpleNamespace(label=label, get_width=lambda: len(label) * 6, get_height=lambda: 8)

    def draw_rect(surface, color, rect, *args):
        surface.rects.append(rect)

    namespace = {
        "__builtins__": {**vars(builtins), "__import__": import_modal},
        "pygame": SimpleNamespace(
            Rect=Rect,
            key=SimpleNamespace(get_mods=lambda: 0),
            draw=SimpleNamespace(rect=draw_rect, line=lambda *args: None),
        ),
        "GRID": 8,
        "PALETTE": dict.fromkeys(["panel", "panel_border", "text", "muted"], 0),
        "render_pixel_text": text,
        "safe_save_state": reject,
        "layout_tools": SimpleNamespace(clear_active_guides=lambda app: None),
        "tab5_validace": SimpleNamespace(po_pusteni=reject),
        "scene_origin": reject,
    }
    load_functions(
        "cyberpunk_designer/drawing/toolbar.py",
        ["_toolbar_pages", "_toolbar_button", "draw_toolbar"],
        namespace,
    )
    load_functions(
        "cyberpunk_designer/mouse_handlers.py",
        [
            "_inside_runtime_preview",
            "on_mouse_down",
            "on_mouse_move",
            "on_mouse_up",
            "on_mouse_wheel",
        ],
        namespace,
    )
    return SimpleNamespace(**namespace, modal=modal)


def actual_actions(app):
    cls = next(
        node
        for node in source_tree("cyberpunk_designer/app.py").body
        if isinstance(node, ast.ClassDef) and node.name == "CyberpunkEditorApp"
    )
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "_build_toolbar"
    )
    assignment = next(
        node
        for node in method.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == "toolbar_actions"
            for target in node.targets
        )
    )
    identities = []
    for label, action in (item.elts for item in assignment.value.elts):
        identities.append((label.value, action.attr))
        setattr(app, action.attr, lambda name=action.attr: app.calls.append(name))
    module = ast.fix_missing_locations(ast.Module(body=[assignment], type_ignores=[]))
    exec(compile(module, "actual_toolbar_assignment", "exec"), {"self": app})  # noqa: S102
    return identities


def make_app(seams, width=576, height=24, origin=(0, 0)):
    app = SimpleNamespace(
        layout=SimpleNamespace(
            toolbar_rect=Rect(*origin, width, height),
            inspector_rect=Rect(1000, 1000, 100, 100),
        ),
        logical_surface=Surface(),
        pixel_padding=8,
        pointer_down=False,
        pointer_pos=(0, 0),
        _is_pointer_over=lambda rect: False,
        _shade=lambda color, amount: amount,
        designer=SimpleNamespace(undo_stack=[1], redo_stack=[2]),
        state=SimpleNamespace(
            inspector_selected_field=None,
            dragging=False,
            resizing=False,
            box_select_start=None,
            box_select_rect=None,
            saved_this_drag=False,
            drag_start_positions={},
            drag_start_sizes={},
            drag_start_rect=None,
            resize_start_rect=None,
            resize_anchor=None,
        ),
        _mark_dirty=reject,
        _inspector_commit_edit=reject,
        _apply_click_selection=reject,
        _dirty=False,
        _dirty_scenes=set(),
        _force_full_redraw=False,
        calls=[],
    )
    app.identities = actual_actions(app)
    app._refresh_available_ports = lambda: app.calls.append("refresh_ports")
    app._draw_toolbar = lambda: seams.draw_toolbar(app)
    return app


def assert_bounded(app):
    boxes = [rect for rect, _key in app.toolbar_hitboxes + app.toolbar_scroll_hitboxes]
    for rect in boxes + app.logical_surface.rects:
        assert rect.width > 0 and rect.height > 0
        assert app.layout.toolbar_rect.contains(rect)
    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            intersection = left.clip(right)
            assert intersection.width == 0 or intersection.height == 0
    for _label, _pos, clip in app.logical_surface.labels:
        assert app.layout.toolbar_rect.contains(clip)
    app.logical_surface.rects.clear()
    app.logical_surface.labels.clear()


def advance(seams, app, direction=1):
    rect, target = app.toolbar_scroll_hitboxes[0 if direction < 0 else 1]
    previous = app._toolbar_offset
    seams.on_mouse_down(app, rect.center)
    assert app._toolbar_offset == target
    assert app.calls == [] and not app._dirty and app._dirty_scenes == set()
    return target != previous


@pytest.mark.parametrize("width", [576, 320, 160, 128, 96, 64, 32, 12, 3])
def test_every_actual_action_reachable_and_dispatched_in_both_directions(seams, width):
    app = make_app(seams, width, origin=(7, 3))
    app._draw_toolbar()
    expected = {label.lower(): name for label, name in app.identities}
    expected["refresh_ports"] = "refresh_ports"
    assert {"simulator", "stop simulator", "build", "flash", "refresh_ports"} <= expected.keys()
    seen, labels = set(), set()
    for _ in range(len(expected) + 1):
        labels.update(label for label, _pos, _clip in app.logical_surface.labels)
        assert_bounded(app)
        for rect, key in list(app.toolbar_hitboxes):
            seams.on_mouse_down(app, rect.center)
            assert app.calls == [expected[key]]
            app.calls.clear()
            seen.add(key)
        if not advance(seams, app):
            break
    else:
        pytest.fail("Toolbar navigation did not terminate")
    assert seen == set(expected)
    assert {label for label, _name in app.identities} | {"Refresh Ports"} <= labels
    seen.clear()
    for _ in range(len(expected) + 1):
        assert_bounded(app)
        seen.update(key for _rect, key in app.toolbar_hitboxes)
        if not advance(seams, app, -1):
            break
    assert seen == set(expected) and app._toolbar_offset == 0


def test_scroll_does_not_commit_pending_inspector_or_authored_state(seams):
    app = make_app(seams)
    app.state.inspector_selected_field = "text"
    app.designer.scene = {"widgets": [{"text": "unsaved"}]}
    app._draw_toolbar()
    assert advance(seams, app)
    assert app.state.inspector_selected_field == "text"
    assert app.designer.scene == {"widgets": [{"text": "unsaved"}]}
    assert app.designer.undo_stack == [1] and app.designer.redo_stack == [2]


@pytest.mark.parametrize("stack", ["undo", "redo"])
def test_disabled_undo_redo_checked_again_at_dispatch(seams, stack):
    app = make_app(seams)
    app._draw_toolbar()
    setattr(app.designer, f"{stack}_stack", [])
    rect = next(rect for rect, key in app.toolbar_hitboxes if key == stack)
    seams.on_mouse_down(app, rect.center)
    assert app.calls == []
    setattr(app.designer, f"{stack}_stack", [1])
    seams.on_mouse_down(app, rect.center)
    assert app.calls == [{label.lower(): name for label, name in app.identities}[stack]]


def test_generic_label_and_refresh_oserror_after_scrolling(seams):
    app = make_app(seams, 160)
    app.toolbar_actions.append(("Custom action", lambda: app.calls.append("custom")))
    app._draw_toolbar()
    while "custom action" not in {key for _rect, key in app.toolbar_hitboxes}:
        assert advance(seams, app)
    rect = next(rect for rect, key in app.toolbar_hitboxes if key == "custom action")
    seams.on_mouse_down(app, rect.center)
    assert app.calls == ["custom"]
    app.calls.clear()
    while "refresh_ports" not in {key for _rect, key in app.toolbar_hitboxes}:
        assert advance(seams, app)

    def unavailable():
        raise OSError("inert port seam")

    app._refresh_available_ports = unavailable
    rect = next(rect for rect, key in app.toolbar_hitboxes if key == "refresh_ports")
    seams.on_mouse_down(app, rect.center)
    assert app.calls == []


def test_stale_offsets_resize_action_changes_and_single_page(seams):
    app = make_app(seams)
    for width, offset in [(576, 9999), (96, -12), (320, 15), (4096, 9999)]:
        app.layout.toolbar_rect = Rect(5, 3, width, 24)
        app._toolbar_offset = offset
        app._draw_toolbar()
        assert_bounded(app)
        first_key = app.toolbar_hitboxes[0][1]
        keys = [label.lower() for label, _action in app.toolbar_actions] + ["refresh_ports"]
        assert keys[app._toolbar_offset] == first_key
        if width == 4096:
            assert app._toolbar_offset == 0 and app.toolbar_scroll_hitboxes == []
    app.toolbar_actions = []
    app._toolbar_offset = 9999
    app._draw_toolbar()
    assert app._toolbar_offset == 0
    assert [key for _rect, key in app.toolbar_hitboxes] == ["refresh_ports"]


@pytest.mark.parametrize(
    ("width", "height"), [(0, 24), (1, 24), (2, 24), (576, 0), (576, 1), (64, 7)]
)
def test_degenerate_or_short_toolbar_never_leaks_hitboxes(seams, width, height):
    app = make_app(seams, width, height)
    app._draw_toolbar()
    assert_bounded(app)
    if width < 3 or height == 0:
        assert app.toolbar_hitboxes == app.toolbar_scroll_hitboxes == []


def test_click_refits_stale_resize_hitboxes_and_preserves_clip(seams):
    app = make_app(seams)
    clip = app.logical_surface.clip
    app._draw_toolbar()
    assert app.logical_surface.clip is clip
    old_last_rect = app.toolbar_hitboxes[-1][0]
    assert_bounded(app)
    app.layout.toolbar_rect = Rect(0, 0, 64, 24)
    seams.on_mouse_down(app, (63, 2))
    assert app.calls == []
    assert not app.layout.toolbar_rect.contains(old_last_rect)
    assert_bounded(app)


def test_navigation_preserves_already_dirty_scene_and_history(seams):
    app = make_app(seams)
    app._dirty = True
    app._dirty_scenes = {"previously changed"}
    app.state.inspector_selected_field = "text"
    app._draw_toolbar()
    rect, offset = app.toolbar_scroll_hitboxes[1]
    seams.on_mouse_down(app, rect.center)
    assert app._toolbar_offset == offset
    assert app._dirty and app._dirty_scenes == {"previously changed"}
    assert app.designer.undo_stack == [1] and app.designer.redo_stack == [2]
    assert app.calls == []


def test_preview_outside_boundary_keeps_toolbar_dispatch(seams):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app._draw_toolbar()
    rect, key = app.toolbar_hitboxes[0]
    seams.on_mouse_down(app, rect.center)
    assert app.calls == [{label.lower(): name for label, name in app.identities}[key]]


def test_preview_captures_click_move_wheel_without_authoring(seams):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.pointer_pos = (120, 120)
    app.state.inspector_selected_field = "text"
    app.pointer_down = True
    # Even a pre-existing drag does not write widget positions through preview.
    app.state.dragging = True
    seams.on_mouse_down(app, app.pointer_pos)
    seams.on_mouse_move(app, app.pointer_pos, (1, 0, 0))
    seams.on_mouse_wheel(app, 0, 1)
    assert app._view_only_wheel
    assert app.calls == [] and not app._dirty and app._dirty_scenes == set()
    assert app.state.inspector_selected_field == "text" and app.state.dragging


@pytest.mark.parametrize("source", ["preview", "navigation"])
def test_view_only_press_captures_move_and_release_outside_without_validation(seams, source):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app._draw_toolbar()
    pos = (120, 120) if source == "preview" else app.toolbar_scroll_hitboxes[1][0].center
    seams.on_mouse_down(app, pos)
    assert app._view_only_pointer_down
    app.pointer_down = True
    seams.on_mouse_move(app, (500, 300), (1, 0, 0))
    seams.on_mouse_up(app, (500, 300))
    assert not app._view_only_pointer_down
    assert not app.state.dragging and not app.state.resizing
    assert app.calls == [] and not app._dirty and app._dirty_scenes == set()


@pytest.mark.parametrize(
    "name", ["icon_palette", "template_manager", "logic_editor", "build_flash"]
)
def test_preview_keeps_modal_priority(seams, name):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.pointer_pos = (120, 120)
    seams.modal.click = seams.modal.wheel = name
    seams.on_mouse_down(app, app.pointer_pos)
    assert seams.modal.calls[-1] == (name, "click")
    app._view_only_wheel = True  # A previous preview event must not leak into this modal.
    seams.on_mouse_wheel(app, 0, 1)
    assert seams.modal.calls[-1] == (name, "wheel")
    assert not app._view_only_wheel


@pytest.mark.parametrize("dy", [-1, 1])
def test_preview_wheel_is_view_only_and_does_not_dismiss_help_or_change_viewport(seams, dy):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.pointer_pos = (120, 120)
    app.scale = 2
    app.state.palette_scroll = 8
    app.state.inspector_scroll = 16
    app.designer.scene = {"widgets": [{"text": "unsaved"}]}
    app.show_help_overlay = app._help_pinned = True
    app._set_help_overlay = app._set_scale = app._switch_scene = reject
    seams.on_mouse_wheel(app, 0, dy)
    assert app._view_only_wheel
    assert app.show_help_overlay and app._help_pinned
    assert app.scale == 2
    assert app.state.palette_scroll == 8 and app.state.inspector_scroll == 16
    assert app.designer.scene == {"widgets": [{"text": "unsaved"}]}
    assert app.designer.undo_stack == [1] and app.designer.redo_stack == [2]
    assert app.calls == [] and not app._dirty and app._dirty_scenes == set()


def test_preview_wheel_flag_resets_for_normal_canvas_and_zero_delta_events(seams):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.pointer_pos = (120, 120)
    seams.on_mouse_wheel(app, 0, 1)
    assert app._view_only_wheel
    app.pointer_pos = (400, 300)
    app.pixel_row_height = 8
    app.layout.scene_tabs_rect = Rect(0, 24, 576, 20)
    app.layout.palette_rect = Rect(0, 44, 100, 400)
    app.layout.canvas_rect = Rect(100, 44, 476, 400)
    app.scale = 2
    app._set_scale = lambda scale: app.calls.append(("scale", scale))
    seams.on_mouse_wheel(app, 0, 1)
    assert not app._view_only_wheel
    assert app.calls == [("scale", 3)]
    app._view_only_wheel = True
    seams.on_mouse_wheel(app, 0, 0)
    assert not app._view_only_wheel
    assert app.calls == [("scale", 3)]


def test_preview_help_priority_and_optional_guard_boundary(seams):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.show_help_overlay = app._help_pinned = True
    app._set_help_overlay = lambda visible: app.calls.append(("help", visible))
    seams.on_mouse_down(app, (120, 120))
    assert app.calls == [("help", False)]
    assert not seams._inside_runtime_preview(app, (300, 120))
    app._runtime_preview_hitbox = None
    assert not seams._inside_runtime_preview(app, (120, 120))
    del app._runtime_preview_hitbox
    assert not seams._inside_runtime_preview(app, (120, 120))


@pytest.mark.parametrize("had_drag", [False, True])
def test_preview_mouse_up_releases_ownership_and_completes_existing_drag(seams, had_drag):
    app = make_app(seams)
    app._runtime_preview_hitbox = Rect(100, 100, 200, 128)
    app.state.dragging = had_drag
    app.state.drag_start_positions = {0: (10, 20)}
    app.state.drag_start_sizes = {0: (30, 40)}
    if had_drag:
        # Permit only completion of a pre-existing authored drag.
        seams.on_mouse_up.__globals__["tab5_validace"] = SimpleNamespace(
            po_pusteni=lambda current: current.calls.append("drag completed")
        )
    seams.on_mouse_up(app, (120, 120))
    assert not app.state.dragging and not app.state.resizing
    assert app.state.drag_start_positions == app.state.drag_start_sizes == {}
    assert app._tab_drag_idx is None and app._layer_drag_idx is None
    assert app.calls == (["drag completed"] if had_drag else [])
    assert not app._dirty and app._dirty_scenes == set()
