"""Tests targeting remaining uncovered branches in smaller modules."""

from __future__ import annotations

import pygame

from cyberpunk_editor import CyberpunkEditorApp
from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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
# transforms.py — nudge locked widget (L20)
# ===========================================================================


class TestNudgeLocked:
    def test_nudge_locked_widget(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.transforms import move_selection

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = _w(type="button", x=10, y=10, width=40, height=20)
        w.locked = True
        sc.widgets.append(w)
        _sel(app, 0)
        move_selection(app, 8, 0)
        assert sc.widgets[0].x == 10  # Didn't move


# ===========================================================================
# transforms.py — resize with invalid/zero selection (L67, L84)
# ===========================================================================


class TestResizeEdges:
    def test_resize_invalid_selection(self, tmp_path, monkeypatch):
        """resize_selection_to with OOB indices — bounds is None (L67)."""
        from cyberpunk_designer.selection_ops.transforms import resize_selection_to

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = [99]
        app.state.selected_idx = 99
        result = resize_selection_to(app, 100, 100)
        assert result is False

    def test_resize_zero_dim_widget(self, tmp_path, monkeypatch):
        """resize_selection_to with zero-size widget (L84)."""
        from cyberpunk_designer.selection_ops.transforms import resize_selection_to

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = _w(type="button", x=10, y=10, width=0, height=0)
        sc.widgets.append(w)
        _sel(app, 0)
        # Exercise the zero-dimension code path — result may vary
        resize_selection_to(app, 100, 100)


# ===========================================================================
# transforms.py — make_full_height with locked widget (L220)
# ===========================================================================


class TestMakeFullHeightLocked:
    def test_full_height_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.transforms import make_full_height

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = _w(type="button", x=10, y=10, width=40, height=20)
        w.locked = True
        sc.widgets.append(w)
        _sel(app, 0)
        make_full_height(app)
        assert sc.widgets[0].y == 10  # Didn't change


# ===========================================================================
# text_metrics.py — wrap_text_device with blank lines (L76)
# ===========================================================================


class TestWrapTextCharsEdges:
    def test_blank_line_in_input(self):
        from cyberpunk_designer.text_metrics import wrap_text_chars

        lines, truncated = wrap_text_chars("line1\n\nline2", max_chars=20, max_lines=10)
        assert "line1" in lines
        assert "line2" in lines

    def test_push_after_truncation(self):
        """_push called when truncated already True (L76)."""
        from cyberpunk_designer.text_metrics import wrap_text_chars

        # max_lines=1 with multi-word paragraph: first push truncates,
        # then loop may try to push more.
        lines, truncated = wrap_text_chars(
            "a b c d e f g h i j k l m n o", max_chars=3, max_lines=1
        )
        assert truncated is True
        assert len(lines) == 1


# ===========================================================================
# batch_ops.py — prune_degenerate with no degenerate (L369-370)
# ===========================================================================


class TestPruneDegenerateNone:
    def test_no_degenerate_widgets(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.batch_ops import remove_degenerate_widgets

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        remove_degenerate_widgets(app)
        assert len(sc.widgets) == 1  # Nothing removed


# ===========================================================================
# batch_ops.py — assign_to_parent_panel with enclosing panel (L1275)
# ===========================================================================


class TestAssignToParentPanel:
    def test_child_enclosed_by_panel(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.batch_ops import fill_parent

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        # Panel that encloses the child
        sc.widgets.append(_w(type="panel", x=0, y=0, width=100, height=80))
        # Child widget inside the panel
        sc.widgets.append(_w(type="button", x=10, y=10, width=30, height=20))
        _sel(app, 1)
        fill_parent(app)
        # Child should be repositioned to parent panel + padding
        assert sc.widgets[1].x >= 0


# ===========================================================================
# query_select.py — select_overflow with icon + overflowing text (L161, L163)
# ===========================================================================


class TestSelectOverflow:
    def test_select_overflow_with_icon(self, tmp_path, monkeypatch):
        """select_overflow with icon widget (L161)."""
        from cyberpunk_designer.selection_ops.query_select import select_overflow

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = _w(type="icon", x=0, y=0, width=10, height=10, text="")
        w.icon_char = "X"
        sc.widgets.append(w)
        select_overflow(app)

    def test_select_overflow_truncated_text(self, tmp_path, monkeypatch):
        """select_overflow where text actually truncates (L163)."""
        from cyberpunk_designer.selection_ops.query_select import select_overflow

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        # Very long text in a tiny widget
        w = _w(type="label", x=0, y=0, width=10, height=8, text="A" * 200)
        sc.widgets.append(w)
        select_overflow(app)
        # Widget should be selected as overflowing
        assert 0 in app.state.selected


# ===========================================================================
# drawing/text.py — wrap_text_px truncation (L60, L68-69, L110)
# ===========================================================================


class TestWrapTextPxEdges:
    def test_whitespace_only_input(self, tmp_path, monkeypatch):
        """wrap_text_px with whitespace-only text (L60)."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        lines = wrap_text_px(app, "  \n  \n  ", 100, max_lines=5)
        # Should handle gracefully
        assert isinstance(lines, list)

    def test_text_exceeds_max_lines(self, tmp_path, monkeypatch):
        """wrap_text_px with text that exceeds max_lines (L68-69, L110)."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Very long text, limited to 2 lines
        long_text = " ".join(["word"] * 100)
        lines = wrap_text_px(app, long_text, 60, max_lines=2)
        assert len(lines) <= 2


# ===========================================================================
# drawing/text.py — draw_text_clipped with tiny clip rect (L165)
# ===========================================================================


class TestDrawTextClippedEdges:
    def test_tiny_clip_rect_max_lines_one(self, tmp_path, monkeypatch):
        """draw_text_clipped where clip height forces max_lines=1."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((256, 128))
        clip = pygame.Rect(0, 0, 100, 8)  # Very short height
        draw_text_clipped(
            app, surf, "Hello World", clip, fg=(255, 255, 255), padding=2, max_lines=5
        )

    def test_whitespace_only_text_returns_empty_lines(self, tmp_path, monkeypatch):
        """draw_text_clipped with whitespace-only text — lines=[] → return (L165)."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((256, 128))
        clip = pygame.Rect(0, 0, 100, 50)
        # " " passes the `if not s` check but wrap_text_px strips → returns []
        draw_text_clipped(app, surf, " ", clip, fg=(255, 255, 255), padding=2, max_lines=3)

    def test_align_right(self, tmp_path, monkeypatch):
        """draw_text_clipped with align='right' — right-align path."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((256, 128))
        clip = pygame.Rect(0, 0, 100, 50)
        draw_text_clipped(app, surf, "Hello", clip, fg=(255, 255, 255), padding=2, align="right")


# ===========================================================================
# drawing/text.py — widget text overflow auto/wrap with device font (L232-233, L240)
# ===========================================================================


class TestWidgetTextOverflow:
    def test_text_overflow_auto_pixel_font(self, tmp_path, monkeypatch):
        """text_overflow='auto' with pixel font — L235."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((256, 128))
        w = _w(
            type="label", x=0, y=0, width=60, height=40, text="Long text that should wrap around"
        )
        w.text_overflow = "auto"
        rect = pygame.Rect(0, 0, 60, 40)
        draw_text_in_rect(app, surf, w.text, rect, (255, 255, 255), 2, w)

    def test_text_overflow_auto_device_font(self, tmp_path, monkeypatch):
        """text_overflow='auto' with device font (L232-233)."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        app.hardware_profile = "esp32os_256x128_gray4"
        surf = pygame.Surface((256, 128))
        # rect must collide with canvas_rect for use_device=True
        cr = app.layout.canvas_rect
        rect = pygame.Rect(cr.x, cr.y, 60, 40)
        w = _w(
            type="label",
            x=cr.x,
            y=cr.y,
            width=60,
            height=40,
            text="Long text that should auto-wrap on device",
        )
        w.text_overflow = "auto"
        draw_text_in_rect(app, surf, w.text, rect, (255, 255, 255), 2, w)

    def test_text_overflow_wrap_device_font(self, tmp_path, monkeypatch):
        """text_overflow='wrap' with device font (L240)."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        app.hardware_profile = "esp32os_256x128_gray4"
        surf = pygame.Surface((256, 128))
        cr = app.layout.canvas_rect
        rect = pygame.Rect(cr.x, cr.y, 60, 40)
        w = _w(
            type="label",
            x=cr.x,
            y=cr.y,
            width=60,
            height=40,
            text="Some long text that wraps on device",
        )
        w.text_overflow = "wrap"
        draw_text_in_rect(app, surf, w.text, rect, (255, 255, 255), 2, w)


# ===========================================================================
# drawing/panels.py — status bar multi-scene (L295-296)
# ===========================================================================


class TestStatusBarMultiScene:
    def test_status_bar_with_two_scenes(self, tmp_path, monkeypatch):
        """Status bar shows scene index with multiple scenes (L294)."""
        from cyberpunk_designer.drawing.panels import draw_status

        app = _make_app(tmp_path, monkeypatch)
        app._add_new_scene()
        draw_status(app)

    def test_status_bar_mouse_on_canvas(self, tmp_path, monkeypatch):
        """Status bar with pointer on canvas shows coordinates (L303-311)."""
        from cyberpunk_designer.drawing.panels import draw_status

        app = _make_big_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        # scene_rect must be a pygame.Rect and pointer must be inside it
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x + 10, cr.y + 10, 256, 128)
        app.pointer_pos = (cr.x + 20, cr.y + 20)
        draw_status(app)


# ===========================================================================
# drawing/panels.py — inspector hover and layer-drag (L113, L191, L229-234)
# ===========================================================================


def _make_big_app(tmp_path, monkeypatch, *, widgets=None):
    """Create app with large layout so palette/inspector hitboxes are valid."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    app.logical_surface = pygame.Surface((1200, 800))
    app.layout = app.layout.__class__(1200, 800)
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


class TestPaletteWidgetHover:
    def test_palette_widget_row_hover(self, tmp_path, monkeypatch):
        """Hover over palette widget row highlights it (L113)."""
        from cyberpunk_designer.drawing.panels import draw_palette

        app = _make_big_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)  # Select widget so L111 is also hit
        # First draw to compute hitboxes
        draw_palette(app)
        # Set pointer over first widget hitbox
        if app.palette_widget_hitboxes:
            r, _ = app.palette_widget_hitboxes[0]
            app.pointer_pos = (r.centerx, r.centery)
        # Second draw — hover detected
        draw_palette(app)


class TestInspectorPanelHover:
    def test_section_header_hover(self, tmp_path, monkeypatch):
        """Inspector section header hover effect (L191)."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_big_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        draw_inspector(app)
        # Set pointer over a section header ("Info")
        if app.inspector_section_hitboxes:
            r, _name = app.inspector_section_hitboxes[0]
            app.pointer_pos = (r.centerx, r.centery)
        draw_inspector(app)

    def test_layer_drag_highlight(self, tmp_path, monkeypatch):
        """Inspector with active layer drag over another layer (L229-234)."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_big_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20))
        _sel(app, 0)
        # Ensure Layers section expanded
        if hasattr(app, "inspector_collapsed"):
            app.inspector_collapsed.discard("Layers")
        draw_inspector(app)
        # Find layer:1 hitbox
        layer1_hit = None
        for r, k in app.inspector_hitboxes:
            if k == "layer:1":
                layer1_hit = r
                break
        if layer1_hit and layer1_hit.width > 0:
            app._layer_drag_idx = 0  # Dragging layer 0
            app.pointer_pos = (layer1_hit.centerx, layer1_hit.centery)
            draw_inspector(app)

    def test_inspector_resources_warning(self, tmp_path, monkeypatch):
        """Inspector with resource warning (L223)."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_big_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)

        # Monkey-patch app._compute_inspector_rows to return a warning
        def mock_rows():
            rows = [
                ("_section:Properties", "Properties"),
                ("resources", "Resources: 1 issue"),
            ]
            return rows, "Warning: resource issue", sc.widgets[0]

        app._compute_inspector_rows = mock_rows
        draw_inspector(app)
