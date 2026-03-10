"""Tests targeting remaining uncovered branches in input_handlers.py."""

from __future__ import annotations

import pygame

from cyberpunk_editor import CyberpunkEditorApp
from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CTRL = pygame.KMOD_CTRL
SHIFT = pygame.KMOD_SHIFT
ALT = pygame.KMOD_ALT


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, widgets=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===========================================================================
# on_mouse_down — inspector_commit_edit before toolbar (L683-684)
# ===========================================================================


class TestToolbarClick:
    """Cover toolbar hitbox click handlers."""

    def test_toolbar_action_click(self, tmp_path, monkeypatch):
        """Click toolbar button that matches an action (L695-696)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        tr = app.layout.toolbar_rect
        hit_rect = pygame.Rect(tr.x + 5, tr.y + 2, 40, 20)
        app.toolbar_hitboxes = [(hit_rect, "undo")]
        called = []
        app.toolbar_actions = [("Undo", lambda: called.append(True))]
        pos = (tr.x + 10, tr.y + 5)
        on_mouse_down(app, pos)
        assert called

    def test_toolbar_commit_edit_before(self, tmp_path, monkeypatch):
        """Inspector field commit before toolbar click (L683-684)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "new"
        app.state.inspector_raw_input = "new"
        tr = app.layout.toolbar_rect
        pos = (tr.x + 10, tr.y + 5)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — scene tab click (L731, L736, L742)
# ===========================================================================


class TestSceneTabClick:
    """Cover scene tab click handlers."""

    def test_tab_new_click(self, tmp_path, monkeypatch):
        """Click '+ New' tab button (L731, L736)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        # Enable scene tabs
        app.layout.scene_tabs_h = 20
        tabs_r = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(tabs_r.x + 5, tabs_r.y + 2, 40, 16)
        app.tab_hitboxes = [(hit_rect, -1, "+ New")]
        app.tab_close_hitboxes = []
        app.tab_scroll_hitboxes = []
        pos = (tabs_r.x + 10, tabs_r.y + 5)
        scenes_before = len(app.designer.scenes)
        on_mouse_down(app, pos)
        assert len(app.designer.scenes) >= scenes_before

    def test_tab_switch_click(self, tmp_path, monkeypatch):
        """Click existing scene tab to switch (L742)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        # Add a second scene
        app._add_new_scene()
        app._jump_to_scene(0)
        app.layout.scene_tabs_h = 20
        tabs_r = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(tabs_r.x + 50, tabs_r.y + 2, 40, 16)
        app.tab_hitboxes = [(hit_rect, 1, "scene_2")]
        app.tab_close_hitboxes = []
        app.tab_scroll_hitboxes = []
        pos = (tabs_r.x + 55, tabs_r.y + 5)
        on_mouse_down(app, pos)

    def test_tab_no_match_return(self, tmp_path, monkeypatch):
        """Click in tab bar but not on any tab — return (L731)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        app.layout.scene_tabs_h = 20
        tabs_r = app.layout.scene_tabs_rect
        app.tab_hitboxes = []
        app.tab_close_hitboxes = []
        app.tab_scroll_hitboxes = []
        pos = (tabs_r.x + 10, tabs_r.y + 5)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — palette section collapse (L736, L742, L756, L763-765, L772)
# ===========================================================================


class TestPaletteClick:
    """Cover palette click handlers."""

    def test_palette_section_uncollapse(self, tmp_path, monkeypatch):
        """Click collapsed palette section to expand (L742)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pr = app.layout.palette_rect
        cx = pr.x + pr.width // 2
        cy = pr.y + pr.height // 2
        hit_rect = pygame.Rect(cx - 20, cy - 8, 40, 16)
        app.palette_section_hitboxes = [(hit_rect, "Actions")]
        # Must be truthy to prevent _draw_palette from overwriting hitboxes
        dummy_rect = pygame.Rect(-9999, -9999, 1, 1)
        app.palette_hitboxes = [(dummy_rect, "dummy", False)]
        app.palette_widget_hitboxes = []
        coll = {"Actions"}
        app.palette_collapsed = coll
        pos = (cx, cy)
        on_mouse_down(app, pos)
        assert "Actions" not in coll

    def test_palette_action_click(self, tmp_path, monkeypatch):
        """Click palette action item (L756, L763-765)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pr = app.layout.palette_rect
        hit_rect = pygame.Rect(pr.x + 2, pr.y + 20, pr.width - 4, 16)
        called = []
        app.palette_section_hitboxes = []
        app.palette_hitboxes = [(hit_rect, "Undo", True)]
        app.palette_collapsed = set()
        app.palette_sections = [("Actions", [("Undo", lambda: called.append(True))])]
        app.palette_widget_hitboxes = []
        pos = (pr.x + 5, pr.y + 25)
        on_mouse_down(app, pos)

    def test_palette_no_match_return(self, tmp_path, monkeypatch):
        """Click in palette area but not on anything — return (L772)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pr = app.layout.palette_rect
        app.palette_section_hitboxes = []
        # Must be truthy to prevent _draw_palette
        dummy_rect = pygame.Rect(-9999, -9999, 1, 1)
        app.palette_hitboxes = [(dummy_rect, "dummy", False)]
        app.palette_widget_hitboxes = []
        pos = (pr.x + pr.width // 2, pr.y + pr.height // 2)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — inspector click (L787-921)
# ===========================================================================


class TestInspectorClick:
    """Cover inspector click handlers (section toggle, group, layer, toggle, editable)."""

    def _insp_pos(self, app, dy=5):
        ir = app.layout.inspector_rect
        return ir.x + 5, ir.y + dy

    def test_inspector_section_toggle_collapse(self, tmp_path, monkeypatch):
        """Click section header to collapse (L787, L793-794)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, ir.width - 4, 16)
        app.inspector_section_hitboxes = [(hit_rect, "Properties")]
        app.inspector_hitboxes = []
        app.inspector_collapsed = set()
        pos = self._insp_pos(app)
        on_mouse_down(app, pos)
        assert "Properties" in app.inspector_collapsed

    def test_inspector_section_toggle_expand(self, tmp_path, monkeypatch):
        """Click collapsed section header to expand."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, ir.width - 4, 16)
        app.inspector_section_hitboxes = [(hit_rect, "Properties")]
        app.inspector_hitboxes = []
        app.inspector_collapsed = {"Properties"}
        pos = self._insp_pos(app)
        on_mouse_down(app, pos)
        assert "Properties" not in app.inspector_collapsed

    def test_inspector_group_click(self, tmp_path, monkeypatch):
        """Click group row — select group members (L804-805, L808-809)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="label", x=0, y=0, width=60, height=10, text="A"))
        sc.widgets.append(_w(type="label", x=0, y=10, width=60, height=10, text="B"))
        app.designer.groups = {"mygroup": [0, 1]}
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 30, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "group:mygroup")]
        pos = (ir.x + 5, ir.y + 35)
        on_mouse_down(app, pos)
        assert set(app.state.selected) == {0, 1}

    def test_inspector_layer_click(self, tmp_path, monkeypatch):
        """Click layer row — select widget and start layer drag (L840-841, L848-849)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 50, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "layer:0")]
        pos = (ir.x + 5, ir.y + 55)
        on_mouse_down(app, pos)
        assert 0 in app.state.selected
        assert app._layer_drag_idx == 0

    def test_inspector_toggle_visible(self, tmp_path, monkeypatch):
        """Click 'visible' toggle — toggles widget visibility (L854-889)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "visible")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)
        # visible defaults to True, so toggle should set it to False
        assert sc.widgets[0].visible is False

    def test_inspector_toggle_checked_on_non_checkbox(self, tmp_path, monkeypatch):
        """Click 'checked' toggle on non-checkbox — nothing to toggle (L854, L857, L860-861, L865, L868)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "checked")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)
        # "checked" toggle skips non-checkbox widgets → "Nothing to toggle."

    def test_inspector_toggle_checked_on_checkbox(self, tmp_path, monkeypatch):
        """Click 'checked' toggle on checkbox — toggles (L865, L868, L875, L877-878, L881, L886, L889)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="checkbox", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "checked")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)

    def test_inspector_toggle_no_selection(self, tmp_path, monkeypatch):
        """Click toggle with no selection — set status (L843-844)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.state.selected = []
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "visible")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)

    def test_inspector_editable_start_edit(self, tmp_path, monkeypatch):
        """Click editable field — start editing (L911, L913, L921)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20, text="btn"))
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 90, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "text")]
        pos = (ir.x + 5, ir.y + 95)
        on_mouse_down(app, pos)
        assert app.state.inspector_selected_field == "text"

    def test_inspector_editable_same_field(self, tmp_path, monkeypatch):
        """Click same field already editing — no-op (L911)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20, text="btn"))
        _sel(app, 0)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "btn"
        app.state.inspector_raw_input = "btn"
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 90, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "text")]
        pos = (ir.x + 5, ir.y + 95)
        on_mouse_down(app, pos)

    def test_inspector_editable_commit_and_switch(self, tmp_path, monkeypatch):
        """Click different editable field while editing — commit+switch (L877-878, L913)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20, text="btn"))
        _sel(app, 0)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "new_text"
        app.state.inspector_raw_input = "new_text"
        ir = app.layout.inspector_rect
        # Two hitboxes: one for current field, one for new field
        hit_x = pygame.Rect(ir.x + 2, ir.y + 110, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_x, "x")]
        pos = (ir.x + 5, ir.y + 115)
        on_mouse_down(app, pos)
        assert app.state.inspector_selected_field == "x"

    def test_inspector_no_match_return(self, tmp_path, monkeypatch):
        """Click in inspector but no hitbox match — return (L881, L886)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        ir = app.layout.inspector_rect
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = []
        pos = (ir.x + 5, ir.y + 5)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — canvas bad scene_rect (L889)
# ===========================================================================


class TestCanvasClick:
    """Cover canvas click edge cases."""

    def test_canvas_bad_scene_rect(self, tmp_path, monkeypatch):
        """scene_rect is not a Rect — fall back to canvas_rect (L889)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.scene_rect = "not_a_rect"
        cr = app.layout.canvas_rect
        pos = (cr.x + 20, cr.y + 20)
        on_mouse_down(app, pos)

    def test_canvas_empty_box_select_start(self, tmp_path, monkeypatch):
        """Click empty canvas area — start box select (L911, L913)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 200, sr.y + 100)
        on_mouse_down(app, pos)
        assert app.state.box_select_start == pos


# ===========================================================================
# on_mouse_move — drag with bad scene_rect (L1105)
# ===========================================================================


class TestMouseMoveDragEdges:
    """Cover mouse move drag edge cases."""

    def test_drag_bad_scene_rect(self, tmp_path, monkeypatch):
        """Drag with non-Rect scene_rect (L1105)."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)
        assert app.state.dragging
        # Now break scene_rect
        app.scene_rect = "not_a_rect"
        app.pointer_down = True
        on_mouse_move(app, (sr.x + 40, sr.y + 30), (1, 0, 0))

    def test_drag_start_rect_none(self, tmp_path, monkeypatch):
        """Drag with drag_start_rect = None — early return (L1108)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app.state.dragging = True
        app.state.drag_start_rect = None
        app.state.drag_offset = (0, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        on_mouse_move(app, (sr.x + 40, sr.y + 30), (1, 0, 0))

    def test_drag_with_snap_enabled(self, tmp_path, monkeypatch):
        """Drag with snap enabled — covers snap paths (L1122, L1139-1140)."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        app.snap_enabled = True
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=8, y=8, width=40, height=20))
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 18)
        on_mouse_down(app, pos)
        assert app.state.dragging
        new_pos = (sr.x + 50, sr.y + 40)
        on_mouse_move(app, new_pos, (1, 0, 0))


# ===========================================================================
# on_mouse_move — resize (L1152-1209)
# ===========================================================================


class TestMouseMoveResizeEdges:
    """Cover mouse move resize edge cases."""

    def test_resize_bad_scene_rect(self, tmp_path, monkeypatch):
        """Resize with bad scene_rect — fallback (L1030)."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Click on resize handle
        handle_x = sr.x + 10 + 40 - 4
        handle_y = sr.y + 10 + 20 - 4
        on_mouse_down(app, (handle_x, handle_y))
        assert app.state.resizing
        # Now break scene_rect
        app.scene_rect = "not_a_rect"
        app.pointer_down = True
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))

    def test_resize_start_rect_none(self, tmp_path, monkeypatch):
        """Resize with resize_start_rect = None — early return (L1168)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app.state.resizing = True
        app.state.resize_anchor = "br"
        app.state.resize_start_rect = None
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))

    def test_resize_with_snap(self, tmp_path, monkeypatch):
        """Resize with snap enabled (L1172-1173, L1206-1209)."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        app.snap_enabled = True
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=8, y=8, width=40, height=24))
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        handle_x = sr.x + 8 + 40 - 4
        handle_y = sr.y + 8 + 24 - 4
        on_mouse_down(app, (handle_x, handle_y))
        assert app.state.resizing
        new_pos = (sr.x + 100, sr.y + 80)
        on_mouse_move(app, new_pos, (1, 0, 0))

    def test_resize_missing_drag_positions(self, tmp_path, monkeypatch):
        """Resize widget not in drag_start_positions — skip (L1152, L1154, L1190, L1192)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app.state.resizing = True
        app.state.resize_anchor = "br"
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        bounds = pygame.Rect(10, 10, 40, 20)
        app.state.resize_start_rect = bounds.copy()
        # Intentionally empty drag positions/sizes — widget idx 0 will be skipped
        app.state.drag_start_positions = {}
        app.state.drag_start_sizes = {}
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))

    def test_resize_multi_widget(self, tmp_path, monkeypatch):
        """Resize multiple widgets proportionally (L1185-1186)."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=8, y=8, width=40, height=20))
        sc.widgets.append(_w(type="button", x=56, y=8, width=40, height=20))
        _sel(app, 0, 1)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Click resize at bottom-right of bounding box
        handle_x = sr.x + 96 - 4
        handle_y = sr.y + 28 - 4
        on_mouse_down(app, (handle_x, handle_y))
        assert app.state.resizing
        new_pos = (sr.x + 140, sr.y + 56)
        on_mouse_move(app, new_pos, (1, 0, 0))


# ===========================================================================
# on_mouse_move — tab drag (L1077-1078)
# ===========================================================================


class TestMouseMoveTabDrag:
    """Cover tab drag reorder."""

    def test_tab_drag(self, tmp_path, monkeypatch):
        """Drag scene tab to reorder (L1077-1078)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        app._add_new_scene()
        app._jump_to_scene(0)
        app.pointer_down = True
        app._tab_drag_idx = 0
        app._tab_drag_name = list(app.designer.scenes.keys())[0]
        app.layout.scene_tabs_h = 20
        tabs_r = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(tabs_r.x + 50, tabs_r.y + 2, 40, 16)
        app.tab_hitboxes = [(hit_rect, 1, list(app.designer.scenes.keys())[1])]
        pos = (tabs_r.x + 55, tabs_r.y + 5)
        on_mouse_move(app, pos, (1, 0, 0))


# ===========================================================================
# on_mouse_up — exception paths (L1015-1016)
# ===========================================================================


class TestMouseUpEdges:
    """Cover mouse up exception paths."""

    def test_mouse_up_clear_guides_exception(self, tmp_path, monkeypatch):
        """clear_active_guides exception (L1015-1016)."""
        from cyberpunk_designer import layout_tools
        from cyberpunk_designer.input_handlers import on_mouse_up

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(layout_tools, "clear_active_guides", lambda a: (_ for _ in ()).throw(RuntimeError("broken")))
        on_mouse_up(app, (100, 100))
        assert not app.state.dragging


# ===========================================================================
# inspector_logic — remaining 50 miss targets
# ===========================================================================


class TestInspectorRemaining:
    """Cover remaining inspector_logic miss lines not in push7."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_parse_pair_none(self, tmp_path, monkeypatch):
        """_parse_pair with single value returns None (L22)."""
        from cyberpunk_designer.inspector_logic import _parse_pair
        assert _parse_pair("abc") is None

    def test_multi_text_save_throws(self, tmp_path, monkeypatch):
        """Multi-select text edit where save throws (L766-767)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20, text="a"))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20, text="b"))
        _sel(app, 0, 1)
        monkeypatch.setattr(app.designer, "_save_state", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        self._setup_edit(app, "text", "new_text")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0].text == "new_text"

    def test_multi_runtime_save_throws(self, tmp_path, monkeypatch):
        """Multi-select runtime edit where save throws (L773-774)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        monkeypatch.setattr(app.designer, "_save_state", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        self._setup_edit(app, "runtime", "store.val")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_x_move_selection(self, tmp_path, monkeypatch):
        """Multi-select x/y edit (L790, L802)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        sc.widgets.append(_w(type="button", x=60, y=10, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "x", "20")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_width_resize(self, tmp_path, monkeypatch):
        """Multi-select width edit (L802)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        sc.widgets.append(_w(type="button", x=60, y=10, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "width", "50")
        result = inspector_commit_edit(app)
        assert result is True

    def test_comp_int_field_exception(self, tmp_path, monkeypatch):
        """Component int field where int() throws (L140-141)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w0 = _w(type="gauge", x=0, y=0, width=80, height=40)
        w0._widget_id = "gh.gauge"
        w0.value = None  # Will cause issues on int()
        sc.widgets.append(w0)
        app.designer.groups = {"comp:gauge_hud:gh:1": [0]}
        _sel(app, 0)
        result = inspector_field_to_str(app, "comp.value", sc.widgets[0])
        # Should handle gracefully
        assert isinstance(result, str)

    def test_inspector_draw_before_hitboxes(self, tmp_path, monkeypatch):
        """inspector_hitboxes is None — triggers draw (L787)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        ir = app.layout.inspector_rect
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = None
        pos = (ir.x + 5, ir.y + 5)
        on_mouse_down(app, pos)

    def test_single_z_index_valid(self, tmp_path, monkeypatch):
        """Single-widget z_index edit (covers z_index path)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "z_index", "5")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0].z_index == 5

    def test_single_z_index_invalid(self, tmp_path, monkeypatch):
        """Single-widget z_index invalid (covers L1011)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "z_index", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_comp_root_rename_with_empty_wid(self, tmp_path, monkeypatch):
        """Root rename: widget with empty _widget_id (L572, L578, L593)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        # Widget with None _widget_id
        w1 = _w(type="label", x=0, y=10, width=60, height=10, text="No ID")
        w1._widget_id = None
        sc.widgets.append(w1)
        # Widget whose _widget_id doesn't match root pattern
        w2 = _w(type="label", x=0, y=20, width=60, height=10, text="Other")
        w2._widget_id = "other.thing"
        sc.widgets.append(w2)
        app.designer.groups = {"comp:menu:nav:1": [0, 1, 2]}
        _sel(app, 0, 1, 2)
        self._setup_edit(app, "comp.root", "newroot")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0]._widget_id == "newroot.title"

    def test_comp_rename_groups_rekey(self, tmp_path, monkeypatch):
        """Root rename updates group key (L602-603 path)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=10, text="Scroll")
        w1._widget_id = "nav.scroll"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:menu:nav:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.root", "newroot2")
        result = inspector_commit_edit(app)
        assert result is True
        # Old key should be gone, new key present
        assert "comp:menu:nav:1" not in app.designer.groups
        assert "comp:menu:newroot2:1" in app.designer.groups

    def test_comp_field_to_str_quick_set(self, tmp_path, monkeypatch):
        """inspector_field_to_str for quick-set fields (L80-81)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20, text="test"))
        _sel(app, 0)
        # Quick-set fields like _position, _size — check  coverage
        result = inspector_field_to_str(app, "_position", sc.widgets[0])
        assert isinstance(result, str)

    def test_compute_rows_group_continue(self, tmp_path, monkeypatch):
        """compute_inspector_rows: group with <2 valid members (L1295)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        # Group with only 1 member — should be skipped
        app.designer.groups = {"comp:menu:nav:1": [0]}
        app.state.selected = []
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        # Group should NOT appear since it has < 2 valid members
        assert not any(k.startswith("group:comp:menu") for k in keys)

    def test_compute_rows_group_member_out_of_range(self, tmp_path, monkeypatch):
        """compute_inspector_rows: group member index out of range (L1309)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20))
        # Group with valid + out-of-range member
        app.designer.groups = {"mygroup": [0, 1, 99]}
        app.state.selected = []
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert any(k.startswith("group:mygroup") for k in keys)


# ===========================================================================
# on_mouse_down — toggle with OOB selection (L854, L865)
# ===========================================================================


class TestInspectorToggleEdges:
    """Cover toggle edge cases: OOB idx, checked with mixed selection."""

    def test_toggle_with_oob_idx(self, tmp_path, monkeypatch):
        """Toggle 'visible' with out-of-range index in selection (L854, L865)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        # Select valid + out-of-range
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "visible")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)

    def test_toggle_checked_mixed_selection(self, tmp_path, monkeypatch):
        """Toggle 'checked' with mixed checkbox+non-checkbox (L865, L868)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="checkbox", x=10, y=10, width=40, height=20))
        sc.widgets.append(_w(type="button", x=60, y=10, width=40, height=20))
        _sel(app, 0, 1)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "checked")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)

    def test_toggle_save_state_exception(self, tmp_path, monkeypatch):
        """Toggle where _save_state throws (L848-849)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        monkeypatch.setattr(app.designer, "_save_state", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "border")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — inspector with commit-before paths (L793, L804, L840, L878)
# ===========================================================================


class TestInspectorCommitBefore:
    """Cover inspector commit-edit-before paths with bad edits."""

    def test_group_click_with_pending_bad_edit(self, tmp_path, monkeypatch):
        """Group click with bad inspector edit pending (L793-794)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20))
        _sel(app, 0)
        # Set up a pending edit that will fail on commit
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "not_a_number"
        app.state.inspector_raw_input = "not_a_number"
        app.designer.groups = {"grp": [0, 1]}
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 30, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "group:grp")]
        pos = (ir.x + 5, ir.y + 35)
        on_mouse_down(app, pos)

    def test_layer_click_with_pending_bad_edit(self, tmp_path, monkeypatch):
        """Layer click with bad inspector edit pending (L804-805)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "abc"
        app.state.inspector_raw_input = "abc"
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 50, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "layer:0")]
        pos = (ir.x + 5, ir.y + 55)
        on_mouse_down(app, pos)

    def test_toggle_with_pending_bad_edit(self, tmp_path, monkeypatch):
        """Toggle click with bad inspector edit pending (L840-841)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "abc"
        app.state.inspector_raw_input = "abc"
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 70, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "visible")]
        pos = (ir.x + 5, ir.y + 75)
        on_mouse_down(app, pos)

    def test_editable_different_field_bad_edit(self, tmp_path, monkeypatch):
        """Click different editable field with bad edit pending (L878)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "not_number"
        app.state.inspector_raw_input = "not_number"
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 90, ir.width - 4, 16)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "y")]
        pos = (ir.x + 5, ir.y + 95)
        on_mouse_down(app, pos)

    def test_inspector_no_match_with_hitboxes(self, tmp_path, monkeypatch):
        """Inspector hitboxes set but none match click — return (L886)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        ir = app.layout.inspector_rect
        # Non-matching hitbox (off-screen)
        dummy = pygame.Rect(-9999, -9999, 1, 1)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(dummy, "text")]
        pos = (ir.x + ir.width // 2, ir.y + ir.height // 2)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — canvas click: Ctrl, locked, empty selection (L911-921)
# ===========================================================================


class TestCanvasClickEdges:
    """Cover canvas click edge cases (Ctrl, locked, empty return)."""

    def test_canvas_click_ctrl_held(self, tmp_path, monkeypatch):
        """Canvas click with Ctrl — early return (L913)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: CTRL)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)

    def test_canvas_click_locked_widget(self, tmp_path, monkeypatch):
        """Canvas click on locked widget — early return (L921)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        w = _w(type="button", x=10, y=10, width=40, height=20)
        w.locked = True
        sc.widgets.append(w)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)

    def test_canvas_click_empty_after_deselect(self, tmp_path, monkeypatch):
        """Canvas click on empty area starts box select (L911)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Click somewhere with no widgets
        pos = (sr.x + 200, sr.y + 100)
        on_mouse_down(app, pos)
        assert app.state.box_select_start is not None

    def test_canvas_save_state_exception(self, tmp_path, monkeypatch):
        """Canvas drag save state exception (L990-991)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        monkeypatch.setattr(app.designer, "_save_state", lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_move — edge cases (L1030, L1077-1078, L1152, L1154)
# ===========================================================================


class TestMouseMoveMore:
    """Cover remaining mouse move edge cases."""

    def test_move_bad_scene_rect_resize(self, tmp_path, monkeypatch):
        """Mouse move with bad scene_rect in non-drag/non-resize path (L1030)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app.state.dragging = False
        app.state.resizing = False
        app.scene_rect = "bad"
        sr = app.layout.canvas_rect
        on_mouse_move(app, (sr.x + 50, sr.y + 50), (1, 0, 0))

    def test_layer_drag_parse_exception(self, tmp_path, monkeypatch):
        """Layer drag with unparseable layer index — exception (L1077-1078)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app._layer_drag_idx = 0
        ir = app.layout.inspector_rect
        # Layer hitbox with unparseable index
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 30, ir.width - 4, 16)
        app.inspector_hitboxes = [(hit_rect, "layer:abc")]
        pos = (ir.x + 5, ir.y + 35)
        on_mouse_move(app, pos, (1, 0, 0))

    def test_resize_with_oob_widget(self, tmp_path, monkeypatch):
        """Resize with widget idx out of range (L1152, L1154, L1192)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.state.selected = [0, 99]  # idx 99 is OOB
        app.state.selected_idx = 0
        app.pointer_down = True
        app.state.resizing = True
        app.state.resize_anchor = "br"
        bounds = pygame.Rect(10, 10, 40, 20)
        app.state.resize_start_rect = bounds.copy()
        app.state.drag_start_positions = {0: (10, 10), 99: (50, 10)}
        app.state.drag_start_sizes = {0: (40, 20), 99: (40, 20)}
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))

    def test_resize_clear_guides_exception(self, tmp_path, monkeypatch):
        """Resize where clear_active_guides throws (L1164-1165)."""
        from cyberpunk_designer import layout_tools
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        handle_x = sr.x + 10 + 40 - 4
        handle_y = sr.y + 10 + 20 - 4
        on_mouse_down(app, (handle_x, handle_y))
        assert app.state.resizing
        monkeypatch.setattr(layout_tools, "clear_active_guides", lambda a: (_ for _ in ()).throw(RuntimeError("broken")))
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))

    def test_resize_sx_sy_exception(self, tmp_path, monkeypatch):
        """Resize where sx/sy calculation throws (L1185-1186)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.pointer_down = True
        app.state.resizing = True
        app.state.resize_anchor = "br"
        # Use a zero-size start rect to trigger division issues
        bounds = pygame.Rect(10, 10, 0, 0)
        app.state.resize_start_rect = bounds.copy()
        app.state.drag_start_positions = {0: (10, 10)}
        app.state.drag_start_sizes = {0: (40, 20)}
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        on_mouse_move(app, (sr.x + 80, sr.y + 60), (1, 0, 0))
