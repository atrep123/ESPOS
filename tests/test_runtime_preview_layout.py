"""Source-only AST seams with inert drawing; --noconftest, no app/pygame import."""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PALETTE = {"bg": "bg", "panel": "panel", "panel_border": "border", "text": "text"}


class Rect:
    """Only the integer rectangle operations exercised by actual source."""

    def __init__(self, *args):
        if len(args) == 1:
            args = args[0].values if isinstance(args[0], Rect) else args[0]
        elif len(args) == 2:
            args = (*args[0], *args[1])
        self.x, self.y, self.width, self.height = args

    @property
    def values(self):
        return self.x, self.y, self.width, self.height

    @property
    def top(self):
        return self.y

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def clip(self, other):
        x, y = max(self.x, other.x), max(self.y, other.y)
        width = max(0, min(self.right, other.right) - x)
        height = max(0, min(self.bottom, other.bottom) - y)
        return Rect(x, y, width, height)

    def contains(self, other):
        return (
            self.x <= other.x <= other.right <= self.right
            and self.y <= other.y <= other.bottom <= self.bottom
        )

    def collidepoint(self, *args):
        x, y = args[0] if len(args) == 1 else args
        return self.x <= x < self.right and self.y <= y < self.bottom

    def __eq__(self, other):
        return isinstance(other, Rect) and self.values == other.values


class Surface:
    def __init__(self, size, *, tag="surface", pixels=b"", log=None):
        self.size, self.tag, self.pixels = size, tag, pixels
        self.clip = self.get_rect()
        self.log = [] if log is None else log
        self.operations = []

    def get_size(self):
        return self.size

    def get_width(self):
        return self.size[0]

    def get_height(self):
        return self.size[1]

    def get_rect(self):
        return Rect(0, 0, *self.size)

    def get_clip(self):
        return Rect(self.clip)

    def set_clip(self, rect):
        self.clip = Rect(rect)

    def blit(self, surface, position):
        rect = Rect(*position, *surface.size)
        self.operations.append((surface.tag, rect, self.get_clip()))
        self.log.append(("blit", surface.tag))
        return rect.clip(self.clip)

    def fill(self, color):
        self.log.append(("fill", color))

    def copy(self):
        return Surface(self.size, tag=self.tag, pixels=self.pixels, log=self.log)


class Font:
    def __init__(self):
        self.calls = []

    def render(self, text, antialias, color):
        self.calls.append((text, antialias, color))
        return Surface((len(text) * 6, 10), tag=text)


def source_nodes(path, *, class_name=None, names=None):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    if class_name is not None:
        tree = next(
            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name
        )
    return [node for node in tree.body if names is None or getattr(node, "name", None) in names]


def execute(nodes, namespace):
    module = ast.Module(
        body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
            *nodes,
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    exec(compile(module, "TEST_ONLY-actual-preview-source", "exec"), namespace)  # noqa: S102 -- trusted source AST, inert collaborators
    return namespace


@pytest.fixture
def harness():
    log, scaled, decoded = [], [], []

    def scale(surface, size):
        scaled.append((surface, size))
        return Surface(size, tag="snapshot", pixels=surface.pixels)

    def draw_rect(target, color, rect, width=0):
        target.operations.append((color, Rect(rect), target.get_clip()))
        log.append(("rect", color, width))

    def frombuffer(pixels, size, mode):
        decoded.append((pixels, size, mode))
        return Surface(size, tag="snapshot", pixels=pixels)

    pygame = SimpleNamespace(
        Rect=Rect,
        transform=SimpleNamespace(scale=scale),
        draw=SimpleNamespace(rect=draw_rect),
        image=SimpleNamespace(frombuffer=frombuffer),
        display=SimpleNamespace(
            flip=lambda: log.append("flip"), update=lambda rects: log.append("update")
        ),
    )
    methods = source_nodes(
        "cyberpunk_designer/app.py",
        class_name="CyberpunkEditorApp",
        names={
            "_draw_runtime_preview",
            "_accept_runtime_frame",
            "_runtime_preview_status",
            "_handle_left_click",
        },
    )
    namespace = execute(
        methods,
        {
            "pygame": pygame,
            "_constants": SimpleNamespace(PALETTE=PALETTE),
            "time": SimpleNamespace(time=lambda: 10.0),
            "DBLCLICK_SEC": 0.4,
            "DBLCLICK_PX": 6,
        },
    )
    app = SimpleNamespace(
        logical_surface=Surface((640, 480), log=log),
        window=Surface((1280, 960), tag="window", log=log),
        layout=SimpleNamespace(canvas_rect=Rect(120, 38, 320, 260), width=640, height=480),
        font_small=Font(),
        _runtime_preview_surface=Surface(
            (256, 128), tag="snapshot", pixels=bytes(range(256)) * 128
        ),
        _runtime_preview_hitbox=None,
        _runtime_preview_state=None,
        _dirty=False,
        _force_full_redraw=False,
        _dirty_scenes={"existing-edit"},
        designer=SimpleNamespace(current_scene="main"),
        state=SimpleNamespace(
            selected_idx=None, selected=[], current_scene=lambda: SimpleNamespace(widgets=[])
        ),
        scale=2,
        vsync_enabled=True,
        show_help_overlay=True,
        clean_preview=False,
        sim_input_mode=False,
        _context_menu=None,
    )
    for name in (
        "_draw_runtime_preview",
        "_accept_runtime_frame",
        "_runtime_preview_status",
        "_handle_left_click",
    ):
        setattr(app, name, lambda *args, name=name: namespace[name](app, *args))
    return SimpleNamespace(app=app, pygame=pygame, log=log, scaled=scaled, decoded=decoded)


def pipeline(harness):
    render_cache = execute(
        source_nodes("cyberpunk_designer/perf.py", names={"RenderCache"}), {"deque": deque}
    )["RenderCache"]
    harness.app.render_cache = render_cache()
    namespace = {
        "pygame": harness.pygame,
        "PALETTE": PALETTE,
        "RenderCache": render_cache,
        "compute_dirty_rects": lambda layout, state, **kwargs: [
            Rect(0, 0, layout.width, layout.height) if kwargs["force_full"] else layout.canvas_rect
        ],
        "windowing": SimpleNamespace(
            hardware_accelerated_scale=lambda _: harness.log.append("scale-window")
        ),
    }
    draws = (
        "draw_toolbar",
        "draw_scene_tabs",
        "draw_palette",
        "draw_canvas",
        "draw_inspector",
        "draw_status",
        "draw_help_overlay",
        "draw_shortcuts_panel",
        "draw_icon_palette",
        "draw_template_manager",
        "draw_logic_editor",
        "draw_build_flash",
        "draw_context_menu",
        "draw_tooltip",
    )
    for name in draws:
        namespace[name] = lambda _, name=name: harness.log.append(name)
    return execute(
        source_nodes(
            "cyberpunk_designer/drawing/frame.py",
            names={"optimized_draw_frame", "smart_dirty_tracking"},
        ),
        namespace,
    )["optimized_draw_frame"]


@pytest.mark.parametrize(
    ("canvas", "caption"),
    [
        ((120, 38, 320, 260), "SIM SNAPSHOT | MOCK"),
        ((10, 20, 260, 144), "SIM SNAPSHOT | MOCK"),
        ((120, 38, 118, 80), "SIM SNAPSHOT | MOCK"),
        ((120, 38, 116, 80), "MOCK"),
        ((120, 38, 80, 60), "MOCK"),
        ((120, 38, 28, 17), "MOCK"),
        ((120, 38, 27, 100), None),
        ((120, 38, 100, 16), None),
        ((120, 38, 1, 1), None),
        ((120, 38, 0, 100), None),
        ((700, 38, 80, 60), None),
        ((610, 450, 100, 100), "MOCK"),
    ],
)
def test_preview_bounds_caption_aspect_and_immutable_pixels(harness, canvas, caption):
    app = harness.app
    app.layout.canvas_rect = Rect(canvas)
    original = (app._runtime_preview_surface.size, app._runtime_preview_surface.pixels)
    app._draw_runtime_preview()
    bounds = app.layout.canvas_rect.clip(app.logical_surface.get_rect())
    if caption is None:
        assert app._runtime_preview_hitbox is None and app.logical_surface.operations == []
    else:
        assert isinstance(app._runtime_preview_hitbox, Rect)
        assert bounds.contains(app._runtime_preview_hitbox)
        for _tag, rect, clip in app.logical_surface.operations:
            assert bounds.contains(rect) and bounds.contains(clip)
        labels = [tag for tag, _rect, _clip in app.logical_surface.operations if "MOCK" in tag]
        assert labels == [caption]
        image = next(
            rect for tag, rect, _clip in app.logical_surface.operations if tag == "snapshot"
        )
        assert image.width == 2 * image.height and image.width <= 256
        assert app._runtime_preview_hitbox.contains(image)
        assert harness.log[-1] == ("rect", "border", 1)
    assert original == (app._runtime_preview_surface.size, app._runtime_preview_surface.pixels)
    assert app.window.operations == [] and app._dirty_scenes == {"existing-edit"}


@pytest.mark.parametrize("window_size", [(200, 120), (148, 80), (140, 80), (640, 480), (1280, 960)])
def test_undersized_physical_window_clips_or_omits_in_logical_space(harness, window_size):
    app = harness.app
    app.window = Surface(window_size, tag="window")
    app._draw_runtime_preview()
    bounds = app.layout.canvas_rect.clip(app.window.get_rect()).clip(app.logical_surface.get_rect())
    if bounds.width < 28 or bounds.height < 17:
        assert app._runtime_preview_hitbox is None and app.logical_surface.operations == []
    else:
        assert bounds.contains(app._runtime_preview_hitbox)
        assert all(bounds.contains(rect) for _, rect, _ in app.logical_surface.operations)


def test_clip_restored_and_native_frame_not_resampled(harness):
    app = harness.app
    app.logical_surface.set_clip(Rect(130, 40, 280, 220))
    clip = app.logical_surface.get_clip()
    app._draw_runtime_preview()
    assert app.logical_surface.get_clip() == clip and harness.scaled == []
    assert clip.contains(app._runtime_preview_hitbox)


def test_clip_restored_when_drawing_fails(harness):
    app = harness.app
    clip = app.logical_surface.get_clip()

    def fail(*args):
        raise RuntimeError("TEST_ONLY inert blit failure")

    app.logical_surface.blit = fail
    with pytest.raises(RuntimeError, match="TEST_ONLY"):
        app._draw_runtime_preview()
    assert app.logical_surface.get_clip() == clip and app._runtime_preview_hitbox is None


@pytest.mark.parametrize("canvas_only", [False, True])
def test_preview_before_all_overlays_and_cached_as_part_of_frame(harness, canvas_only):
    app = harness.app
    draw = pipeline(harness)
    app._dirty = True
    app._force_full_redraw = not canvas_only
    draw(app)
    snapshot_index = harness.log.index(("blit", "snapshot"))
    assert harness.log.index("draw_canvas") < snapshot_index
    for name in (
        "draw_help_overlay",
        "draw_shortcuts_panel",
        "draw_icon_palette",
        "draw_template_manager",
        "draw_logic_editor",
        "draw_build_flash",
        "draw_context_menu",
        "draw_tooltip",
    ):
        assert snapshot_index < harness.log.index(name) < harness.log.index("scale-window")
    assert app._dirty is app._force_full_redraw is False
    hitbox, caption_calls = app._runtime_preview_hitbox, list(app.font_small.calls)
    harness.log.clear()
    draw(app)
    assert harness.log == [("blit", "window"), "flip"]
    assert app.font_small.calls == caption_calls and app._runtime_preview_hitbox == hitbox
    assert app._dirty_scenes == {"existing-edit"}


def test_legacy_app_without_optional_hook(harness):
    draw = pipeline(harness)
    del harness.app._draw_runtime_preview
    harness.app._dirty = True
    draw(harness.app)
    assert "draw_canvas" in harness.log and "draw_tooltip" in harness.log
    assert not any(
        isinstance(item, tuple) and item[:2] == ("blit", "snapshot") for item in harness.log
    )


def test_clean_preview_keeps_mock_caption_below_tooltip(harness):
    app = harness.app
    draw = pipeline(harness)
    app.clean_preview, app.show_help_overlay = True, False
    app._dirty = app._force_full_redraw = True
    draw(app)
    assert "draw_toolbar" not in harness.log and "draw_help_overlay" not in harness.log
    assert harness.log.index("draw_canvas") < harness.log.index(("blit", "SIM SNAPSHOT | MOCK"))
    assert harness.log.index(("blit", "snapshot")) < harness.log.index("draw_tooltip")


def test_shrinking_canvas_clears_hitbox_and_repaints_view_only(harness):
    app = harness.app
    draw = pipeline(harness)
    app._dirty = app._force_full_redraw = True
    draw(app)
    assert app._runtime_preview_hitbox is not None
    app.layout.canvas_rect = Rect(120, 38, 20, 20)
    app._dirty = app._force_full_redraw = True
    harness.log.clear()
    draw(app)
    assert app._runtime_preview_hitbox is None and ("blit", "snapshot") not in harness.log
    assert "draw_canvas" in harness.log and app._dirty_scenes == {"existing-edit"}


def test_frame_delivery_clear_and_status_repaint_are_view_only(harness):
    app = harness.app
    draw = pipeline(harness)
    frame = SimpleNamespace(width=256, height=128, pixels=bytes(range(256)) * 128)
    author = app.designer.__dict__.copy()

    def forbidden(*args):
        pytest.fail("view-only preview requested scene mutation/save")

    app._mark_dirty = app.save_json = app._maybe_autosave = forbidden
    app._accept_runtime_frame(frame, {"mock": True})
    assert harness.decoded == [
        (bytes(channel for gray in frame.pixels for channel in (gray,) * 3), (256, 128), "RGB")
    ]
    assert app._dirty and app._force_full_redraw and app._runtime_preview_hitbox is None
    draw(app)
    assert app._runtime_preview_hitbox is not None
    app._accept_runtime_frame(None, None)
    assert (
        app._runtime_preview_surface
        is app._runtime_preview_state
        is app._runtime_preview_hitbox
        is None
    )
    assert app._dirty and app._force_full_redraw
    harness.log.clear()
    draw(app)
    assert "draw_canvas" in harness.log and "draw_toolbar" in harness.log
    assert ("blit", "snapshot") not in harness.log
    assert app._runtime_preview_hitbox is None
    harness.log.clear()
    draw(app)
    assert harness.log == [("blit", "window"), "flip"]
    app._runtime_preview_status("completed (mock display)")
    assert app._dirty and app._force_full_redraw
    assert app._dirty_scenes == {"existing-edit"} and app.designer.__dict__ == author
    assert frame.pixels == bytes(range(256)) * 128


def test_missing_frame_clears_stale_hitbox_without_drawing(harness):
    app = harness.app
    app._runtime_preview_surface = None
    app._runtime_preview_hitbox = Rect(1, 1, 10, 10)
    app._draw_runtime_preview()
    assert app._runtime_preview_hitbox is None and harness.log == []


@pytest.mark.parametrize("sim_input", [False, True])
def test_double_click_in_preview_routes_through_normal_guard_without_edit(harness, sim_input):
    app, events = harness.app, []
    app._draw_runtime_preview()
    hitbox = app._runtime_preview_hitbox
    pos = (hitbox.x + 2, hitbox.y + 2)
    app.sim_input_mode = sim_input
    app._last_click_time, app._last_click_pos = 9.9, pos
    app._screen_to_logical = lambda p: (p[0] // 2, p[1] // 2)
    app._on_mouse_down = lambda p: events.append(("normal-modal-preview-guard", p))

    def forbidden(*args):
        pytest.fail("preview click reached widget edit/authored dirty shortcut")

    app._handle_double_click = app._mark_dirty = forbidden
    event = SimpleNamespace(pos=(pos[0] * 2, pos[1] * 2))
    app._handle_left_click(event)
    app._handle_left_click(event)
    assert events == [("normal-modal-preview-guard", pos)] * 2
    assert app._dirty and app._force_full_redraw
    assert app._last_click_pos == (-9999, -9999)
    assert app._dirty_scenes == {"existing-edit"}


def test_double_click_outside_preview_retains_widget_shortcut(harness):
    app, events = harness.app, []
    app._runtime_preview_hitbox = Rect(120, 38, 100, 100)
    app._screen_to_logical = lambda p: p
    app._last_click_time, app._last_click_pos = 9.9, (10, 10)
    app._handle_double_click = lambda p: events.append(("double", p))
    app._mark_dirty = lambda: events.append("authored-dirty")
    app._on_mouse_down = lambda p: pytest.fail("ordinary double click lost shortcut")
    app._handle_left_click(SimpleNamespace(pos=(10, 10)))
    assert events == [("double", (10, 10)), "authored-dirty"]


def test_context_menu_retains_dispatch_priority(harness):
    app, events = harness.app, []
    app._context_menu = {"visible": True}
    app._runtime_preview_hitbox = Rect(120, 38, 100, 100)
    app._screen_to_logical = lambda p: p
    app._click_context_menu = lambda p: events.append(("menu", p))
    app._mark_dirty = lambda: events.append("dirty")
    app._on_mouse_down = lambda p: pytest.fail("menu priority bypassed")
    app._handle_left_click(SimpleNamespace(pos=(122, 40)))
    assert events == [("menu", (122, 40)), "dirty"]


def test_editor_loop_has_no_post_composite_preview_draw():
    loop = source_nodes(
        "cyberpunk_designer/app.py", class_name="CyberpunkEditorApp", names={"_run_editor_loop"}
    )[0]
    calls = [
        node.func.attr
        for node in ast.walk(loop)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "_draw_runtime_preview" not in calls
    assert calls.count("_optimized_draw_frame") == 1
