"""Tests for cyberpunk_designer.selection_ops.creators module.

Covers all 13 creator functions: create_header_bar, create_nav_row,
create_form_pair, create_status_bar, create_toggle_group,
create_slider_with_label, create_gauge_panel, create_progress_section,
create_icon_button_row, create_card_layout, create_dashboard_grid,
create_split_layout, wrap_in_panel.
"""

from __future__ import annotations

from cyberpunk_designer.selection_ops import (
    create_card_layout,
    create_dashboard_grid,
    create_form_pair,
    create_gauge_panel,
    create_header_bar,
    create_icon_button_row,
    create_nav_row,
    create_progress_section,
    create_slider_with_label,
    create_split_layout,
    create_status_bar,
    create_toggle_group,
    wrap_in_panel,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    return app


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _widget_count(app):
    return len(app.state.current_scene().widgets)


# ===========================================================================
# create_header_bar
# ===========================================================================


class TestCreateHeaderBar:
    def test_creates_panel_and_label(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_header_bar(app)
        assert _widget_count(app) == 2
        assert _w(app, 0).type == "panel"
        assert _w(app, 1).type == "label"

    def test_header_full_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_header_bar(app)
        assert _w(app, 0).width == 256
        assert _w(app, 0).y == 0

    def test_header_label_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_header_bar(app)
        assert _w(app, 1).text == "Header"
        assert _w(app, 1).style == "bold"

    def test_updates_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_header_bar(app)
        assert app.state.selected == [0, 1]
        assert app.state.selected_idx == 0


# ===========================================================================
# create_nav_row
# ===========================================================================


class TestCreateNavRow:
    def test_creates_three_buttons(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_nav_row(app)
        assert _widget_count(app) == 3
        for i in range(3):
            assert _w(app, i).type == "button"

    def test_button_labels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_nav_row(app)
        texts = [_w(app, i).text for i in range(3)]
        assert texts == ["Back", "OK", "Next"]

    def test_buttons_at_scene_bottom(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_nav_row(app)
        for i in range(3):
            assert _w(app, i).y == 128 - 24

    def test_updates_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_nav_row(app)
        assert app.state.selected == [0, 1, 2]


# ===========================================================================
# create_form_pair
# ===========================================================================


class TestCreateFormPair:
    def test_creates_label_and_textbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_form_pair(app)
        assert _widget_count(app) == 2
        assert _w(app, 0).type == "label"
        assert _w(app, 1).type == "textbox"

    def test_label_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_form_pair(app)
        assert _w(app, 0).text == "Label:"

    def test_places_below_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=10, width=80, height=16)
        _sel(app, 0)
        y_before = _w(app, 0).y + _w(app, 0).height
        create_form_pair(app)
        # the textbox should be below the existing widget
        assert _w(app, 2).y > y_before

    def test_selection_points_to_textbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_form_pair(app)
        # selected_idx should be the textbox (index 1)
        assert app.state.selected_idx == 1


# ===========================================================================
# create_status_bar
# ===========================================================================


class TestCreateStatusBar:
    def test_creates_panel_and_label(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_status_bar(app)
        assert _widget_count(app) == 2
        assert _w(app, 0).type == "panel"
        assert _w(app, 1).type == "label"

    def test_at_scene_bottom(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_status_bar(app)
        bar_h = 16
        assert _w(app, 0).y == 128 - bar_h

    def test_status_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_status_bar(app)
        assert _w(app, 1).text == "Status: ready"

    def test_full_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_status_bar(app)
        assert _w(app, 0).width == 256


# ===========================================================================
# create_toggle_group
# ===========================================================================


class TestCreateToggleGroup:
    def test_creates_three_checkboxes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_toggle_group(app)
        assert _widget_count(app) == 3
        for i in range(3):
            assert _w(app, i).type == "checkbox"

    def test_checkbox_labels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_toggle_group(app)
        texts = [_w(app, i).text for i in range(3)]
        assert texts == ["Option A", "Option B", "Option C"]

    def test_first_checked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_toggle_group(app)
        assert _w(app, 0).checked is True
        assert _w(app, 1).checked is False
        assert _w(app, 2).checked is False

    def test_places_below_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=10, width=80, height=16)
        _sel(app, 0)
        create_toggle_group(app)
        # checkboxes should be below existing widget
        for i in range(1, 4):
            assert _w(app, i).y > 10


# ===========================================================================
# create_slider_with_label
# ===========================================================================


class TestCreateSliderWithLabel:
    def test_creates_three_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_slider_with_label(app)
        assert _widget_count(app) == 3
        assert _w(app, 0).type == "label"
        assert _w(app, 1).type == "slider"
        assert _w(app, 2).type == "label"

    def test_slider_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_slider_with_label(app)
        assert _w(app, 1).value == 50
        assert _w(app, 1).min_value == 0
        assert _w(app, 1).max_value == 100

    def test_label_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_slider_with_label(app)
        assert _w(app, 0).text == "Volume:"
        assert _w(app, 2).text == "50"

    def test_selection_on_slider(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_slider_with_label(app)
        assert app.state.selected_idx == 1


# ===========================================================================
# create_gauge_panel
# ===========================================================================


class TestCreateGaugePanel:
    def test_creates_panel_title_gauge(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_gauge_panel(app)
        assert _widget_count(app) == 3
        assert _w(app, 0).type == "panel"
        assert _w(app, 1).type == "label"
        assert _w(app, 2).type == "gauge"

    def test_gauge_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_gauge_panel(app)
        assert _w(app, 2).value == 70

    def test_title_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_gauge_panel(app)
        assert _w(app, 1).text == "Speed"

    def test_selection_on_gauge(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_gauge_panel(app)
        assert app.state.selected_idx == 2


# ===========================================================================
# create_progress_section
# ===========================================================================


class TestCreateProgressSection:
    def test_creates_label_and_progressbar(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_progress_section(app)
        assert _widget_count(app) == 2
        assert _w(app, 0).type == "label"
        assert _w(app, 1).type == "progressbar"

    def test_progressbar_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_progress_section(app)
        assert _w(app, 1).value == 65

    def test_label_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_progress_section(app)
        assert _w(app, 0).text == "Loading:"


# ===========================================================================
# create_icon_button_row
# ===========================================================================


class TestCreateIconButtonRow:
    def test_creates_four_buttons(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_icon_button_row(app)
        assert _widget_count(app) == 4
        for i in range(4):
            assert _w(app, i).type == "button"

    def test_buttons_are_square(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_icon_button_row(app)
        for i in range(4):
            assert _w(app, i).width == 24
            assert _w(app, i).height == 24


# ===========================================================================
# create_card_layout
# ===========================================================================


class TestCreateCardLayout:
    def test_creates_four_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_card_layout(app)
        assert _widget_count(app) == 4
        assert _w(app, 0).type == "panel"
        assert _w(app, 1).type == "label"  # title
        assert _w(app, 2).type == "panel"  # separator
        assert _w(app, 3).type == "label"  # body

    def test_card_title(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_card_layout(app)
        assert _w(app, 1).text == "Card Title"

    def test_card_body(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_card_layout(app)
        assert "Body content" in _w(app, 3).text


# ===========================================================================
# create_dashboard_grid
# ===========================================================================


class TestCreateDashboardGrid:
    def test_creates_twelve_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_dashboard_grid(app)
        # 2x2 grid, 3 widgets per cell
        assert _widget_count(app) == 12

    def test_cells_have_panel_label_gauge(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_dashboard_grid(app)
        for cell in range(4):
            base = cell * 3
            assert _w(app, base).type == "panel"
            assert _w(app, base + 1).type == "label"
            assert _w(app, base + 2).type == "gauge"

    def test_gauge_titles(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_dashboard_grid(app)
        titles = [_w(app, i * 3 + 1).text for i in range(4)]
        assert titles == ["Speed", "Temp", "RPM", "Batt"]


# ===========================================================================
# create_split_layout
# ===========================================================================


class TestCreateSplitLayout:
    def test_creates_four_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_split_layout(app)
        assert _widget_count(app) == 4
        # left panel, left label, right panel, right label
        assert _w(app, 0).type == "panel"
        assert _w(app, 1).type == "label"
        assert _w(app, 2).type == "panel"
        assert _w(app, 3).type == "label"

    def test_pane_labels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_split_layout(app)
        assert _w(app, 1).text == "Left Pane"
        assert _w(app, 3).text == "Right Pane"

    def test_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        create_split_layout(app)
        assert app.state.selected == [0, 1, 2, 3]


# ===========================================================================
# wrap_in_panel
# ===========================================================================


class TestWrapInPanel:
    def test_wraps_single_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=20, width=40, height=16)
        _sel(app, 0)
        wrap_in_panel(app)
        # Should have inserted a panel at index 0
        assert _widget_count(app) == 2
        assert _w(app, 0).type == "panel"
        # Original widget shifted to index 1
        assert _w(app, 1).type == "label"

    def test_panel_encloses_widget_with_padding(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from cyberpunk_designer.constants import GRID

        _add(app, x=20, y=20, width=40, height=16)
        _sel(app, 0)
        wrap_in_panel(app)
        panel = _w(app, 0)
        assert panel.x == 20 - GRID
        assert panel.y == 20 - GRID
        assert panel.width == 40 + GRID * 2
        assert panel.height == 16 + GRID * 2

    def test_wraps_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=30, height=10)
        _add(app, x=50, y=20, width=30, height=10)
        _sel(app, 0, 1)
        wrap_in_panel(app)
        assert _widget_count(app) == 3
        assert _w(app, 0).type == "panel"

    def test_empty_selection_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=30, height=10)
        _sel(app)
        wrap_in_panel(app)
        assert _widget_count(app) == 1  # no panel added

    def test_selection_updated_after_wrap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=30, height=10)
        _sel(app, 0)
        wrap_in_panel(app)
        # Panel at 0, original at 1 — both selected
        assert 0 in app.state.selected
        assert 1 in app.state.selected
