"""Extended tests for cyberpunk_designer/drawing/panels.py — targeting
uncovered lines to push coverage from 80% to 90%+."""

from __future__ import annotations

import time

from cyberpunk_designer.drawing.panels import draw_inspector, draw_palette, draw_status
from ui_designer import SceneConfig, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=24, height=16, text="w")
    defaults.update(kw)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(**defaults))
    return len(sc.widgets) - 1


# ---------------------------------------------------------------------------
# draw_palette — collapsed sections (line 83), widgets in list (line 113)
# ---------------------------------------------------------------------------


class TestDrawPalette:
    def test_basic(self, make_app):
        app = make_app()
        draw_palette(app)

    def test_with_widgets(self, make_app):
        """Palette shows widget list entries (line 113)."""
        app = make_app()
        _add(app, type="button", text="btn")
        _add(app, type="label", text="lbl")
        draw_palette(app)
        assert len(app.palette_widget_hitboxes) >= 2

    def test_with_selected_widget(self, make_app):
        """Selected widget gets highlight fill."""
        app = make_app()
        idx = _add(app, type="button", text="sel")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_palette(app)

    def test_collapsed_section(self, make_app):
        """Collapsed palette section skips items (line 83)."""
        app = make_app()
        # Collapse the first section if there are any
        if hasattr(app, "palette_sections") and app.palette_sections:
            sec_name = app.palette_sections[0][0]
            app.palette_collapsed = {sec_name}
        draw_palette(app)

    def test_hover_over_section_header(self, make_app):
        """Hover over section header (line 52)."""
        app = make_app()
        # First draw to get section hitboxes
        draw_palette(app)
        if app.palette_section_hitboxes:
            r = app.palette_section_hitboxes[0][0]
            app.pointer_pos = (r.centerx, r.centery)
            draw_palette(app)


# ---------------------------------------------------------------------------
# draw_inspector — editing, collapsed, layer drag
# ---------------------------------------------------------------------------


class TestDrawInspector:
    def test_basic(self, make_app):
        app = make_app()
        draw_inspector(app)

    def test_with_selected_widget(self, make_app):
        app = make_app()
        idx = _add(app, type="button", text="btn")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_inspector(app)
        assert len(app.inspector_hitboxes) > 0

    def test_editing_field(self, make_app):
        """Inspector in editing mode (lines 229-234)."""
        app = make_app()
        idx = _add(app, type="label", text="ed")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "new_text"
        draw_inspector(app)

    def test_collapsed_section(self, make_app):
        """Collapsed inspector section hides rows (line 191)."""
        app = make_app()
        idx = _add(app, type="label", text="col")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        # Collapse a section
        app.inspector_collapsed = {"Appearance"}
        draw_inspector(app)

    def test_layer_drag(self, make_app):
        """Layer drag highlight (lines 223-225)."""
        app = make_app()
        idx = _add(app, type="label", text="layer")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app._layer_drag_idx = 0
        draw_inspector(app)


# ---------------------------------------------------------------------------
# draw_status — various state branches
# ---------------------------------------------------------------------------


class TestDrawStatus:
    def test_basic(self, make_app):
        app = make_app()
        draw_status(app)

    def test_with_widgets(self, make_app):
        """Shows dimensions and widget count (lines 277-278)."""
        app = make_app()
        _add(app, type="label", text="w1")
        _add(app, type="button", text="w2")
        draw_status(app)

    def test_multi_scene(self, make_app):
        """Multiple scenes show scene index (lines 292-296)."""
        app = make_app()
        app.designer.scenes["second"] = SceneConfig(
            name="second",
            width=256,
            height=128,
            widgets=[],
        )
        draw_status(app)

    def test_mouse_over_canvas(self, make_app):
        """Mouse position on canvas (lines 303-311)."""
        app = make_app()
        _add(app, type="label", text="hov", x=40, y=32, width=40, height=24)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Place pointer over the widget
        app.pointer_pos = (sr.x + 50, sr.y + 40)
        draw_status(app)

    def test_selected_locked(self, make_app):
        """Selected locked widget shows [L] flag (line 322)."""
        app = make_app()
        idx = _add(app, type="label", text="lk", locked=True)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_status(app)

    def test_selected_hidden(self, make_app):
        """Selected hidden widget shows [H] flag (line 324)."""
        app = make_app()
        idx = _add(app, type="label", text="hid", visible=False)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_status(app)

    def test_selected_disabled(self, make_app):
        """Selected disabled widget shows [D] flag (line 326)."""
        app = make_app()
        idx = _add(app, type="label", text="dis", enabled=False)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_status(app)

    def test_selected_nondefault_style(self, make_app):
        """Selected widget with non-default style (line 329)."""
        app = make_app()
        idx = _add(app, type="label", text="styled", style="highlight")
        app.state.selected = [idx]
        app.state.selected_idx = idx
        draw_status(app)

    def test_multi_selected(self, make_app):
        """Multiple selection shows count."""
        app = make_app()
        _add(app, type="label", text="a")
        _add(app, type="label", text="b")
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        draw_status(app)

    def test_sim_input_mode(self, make_app):
        """Sim input mode shows focus info (lines 335-340)."""
        app = make_app()
        _add(app, type="button", text="btn")
        app.sim_input_mode = True
        app._ensure_focus()
        draw_status(app)

    def test_sim_input_mode_editing(self, make_app):
        """Sim input mode with value editing."""
        app = make_app()
        _add(app, type="slider", text="vol")
        app.sim_input_mode = True
        app._ensure_focus()
        app.focus_edit_value = True
        draw_status(app)

    def test_undo_redo_counts(self, make_app):
        """Undo/redo stack counts shown (lines 350-352)."""
        app = make_app()
        _add(app, type="label", text="w")
        app.state.selected = [0]
        app.state.selected_idx = 0
        # Push an undo state
        app.designer._save_state()
        draw_status(app)

    def test_dialog_message(self, make_app):
        """Dialog message shown (line 358)."""
        app = make_app()
        app.dialog_message = "Saved!"
        app._status_until_ts = time.time() + 10.0
        draw_status(app)

    def test_dirty_indicator(self, make_app):
        """Dirty file shows * prefix."""
        app = make_app()
        app._dirty = True
        draw_status(app)
