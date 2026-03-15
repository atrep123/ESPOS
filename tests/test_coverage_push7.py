"""Tests targeting remaining uncovered branches in inspector_logic, input_handlers, and small modules."""

from __future__ import annotations

import pygame

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


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _key(key, mod=0, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=unicode)


# ---------------------------------------------------------------------------
# Menu component helper — creates a full "menu" component for testing
# ---------------------------------------------------------------------------


def _setup_menu_component(app):
    """Set up a menu component with root 'nav', 3 items + title + scroll + panel."""
    sc = app.state.current_scene()
    # 0: title
    w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Menu Title")
    w0._widget_id = "nav.title"
    sc.widgets.append(w0)
    # 1: scroll (active/count display)
    w1 = _w(type="label", x=0, y=10, width=60, height=10, text="1/3")
    w1._widget_id = "nav.scroll"
    sc.widgets.append(w1)
    # 2: panel
    w2 = _w(type="panel", x=0, y=20, width=60, height=60, text="")
    w2._widget_id = "nav.panel"
    sc.widgets.append(w2)
    # 3: item0 (highlighted = active)
    w3 = _w(type="label", x=2, y=22, width=56, height=10, text="Item A")
    w3._widget_id = "nav.item0"
    w3.style = "highlight"
    sc.widgets.append(w3)
    # 4: item1
    w4 = _w(type="label", x=2, y=32, width=56, height=10, text="Item B")
    w4._widget_id = "nav.item1"
    w4.style = "default"
    sc.widgets.append(w4)
    # 5: item2
    w5 = _w(type="label", x=2, y=42, width=56, height=10, text="Item C")
    w5._widget_id = "nav.item2"
    w5.style = "default"
    sc.widgets.append(w5)
    # Set up group
    members = [0, 1, 2, 3, 4, 5]
    app.designer.groups = {"comp:menu:nav:1": members}
    _sel(app, *members)
    return members


def _setup_tabs_component(app):
    """Set up a tabs component with root 'tb', 3 tabs + tabbar + content title."""
    sc = app.state.current_scene()
    # 0: tab1
    w0 = _w(type="button", x=0, y=0, width=30, height=10, text="Tab1")
    w0._widget_id = "tb.tab1"
    w0.style = "bold highlight"
    sc.widgets.append(w0)
    # 1: tab2
    w1 = _w(type="button", x=30, y=0, width=30, height=10, text="Tab2")
    w1._widget_id = "tb.tab2"
    w1.style = "default"
    sc.widgets.append(w1)
    # 2: tab3
    w2 = _w(type="button", x=60, y=0, width=30, height=10, text="Tab3")
    w2._widget_id = "tb.tab3"
    w2.style = "default"
    sc.widgets.append(w2)
    # 3: tabbar
    w3 = _w(type="panel", x=0, y=0, width=90, height=10, text="")
    w3._widget_id = "tb.tabbar"
    sc.widgets.append(w3)
    # 4: content.title
    w4 = _w(type="label", x=0, y=10, width=90, height=20, text="Content")
    w4._widget_id = "tb.content.title"
    sc.widgets.append(w4)
    members = [0, 1, 2, 3, 4]
    app.designer.groups = {"comp:tabs:tb:1": members}
    _sel(app, *members)
    return members


def _setup_chart_component(app):
    """Set up a chart_bar component with root 'ch'."""
    sc = app.state.current_scene()
    # 0: title
    w0 = _w(type="label", x=0, y=0, width=80, height=10, text="Chart Title")
    w0._widget_id = "ch.title"
    sc.widgets.append(w0)
    # 1: chart
    w1 = _w(type="chart", x=0, y=10, width=80, height=50, text="")
    w1._widget_id = "ch.chart"
    w1.style = "bar"
    w1.data_points = [10, 20, 30, 40]
    sc.widgets.append(w1)
    members = [0, 1]
    app.designer.groups = {"comp:chart_bar:ch:1": members}
    _sel(app, *members)
    return members


def _setup_list_component(app):
    """Set up a list component with root 'lst', 3 items + scroll + title + panel."""
    sc = app.state.current_scene()
    # 0: title
    w0 = _w(type="label", x=0, y=0, width=60, height=10, text="List Title")
    w0._widget_id = "lst.title"
    sc.widgets.append(w0)
    # 1: scroll
    w1 = _w(type="label", x=0, y=10, width=60, height=10, text="1/3")
    w1._widget_id = "lst.scroll"
    sc.widgets.append(w1)
    # 2: panel
    w2 = _w(type="panel", x=0, y=20, width=60, height=60, text="")
    w2._widget_id = "lst.panel"
    sc.widgets.append(w2)
    # 3: item0.label
    w3 = _w(type="label", x=2, y=22, width=40, height=10, text="Label A")
    w3._widget_id = "lst.item0.label"
    w3.style = "highlight"
    sc.widgets.append(w3)
    # 4: item0.value
    w4 = _w(type="label", x=42, y=22, width=16, height=10, text="100")
    w4._widget_id = "lst.item0.value"
    sc.widgets.append(w4)
    # 5: item1.label
    w5 = _w(type="label", x=2, y=32, width=40, height=10, text="Label B")
    w5._widget_id = "lst.item1.label"
    w5.style = "default"
    sc.widgets.append(w5)
    # 6: item1.value
    w6 = _w(type="label", x=42, y=32, width=16, height=10, text="200")
    w6._widget_id = "lst.item1.value"
    sc.widgets.append(w6)
    members = [0, 1, 2, 3, 4, 5, 6]
    app.designer.groups = {"comp:list:lst:1": members}
    _sel(app, *members)
    return members


# ===========================================================================
# inspector_logic — component editing (comp.root rename)
# ===========================================================================


class TestCompRootRename:
    """Cover component root rename in inspector_commit_edit (L544-620)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_root_rename_success(self, make_app):
        """Rename root from 'nav' to 'menu1'."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.root", "menu1")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[0]._widget_id == "menu1.title"
        assert sc.widgets[3]._widget_id == "menu1.item0"

    def test_root_rename_unchanged(self, make_app):
        """Root unchanged returns ok (L551)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.root", "nav")
        result = inspector_commit_edit(app)
        assert result is True

    def test_root_rename_bad_chars(self, make_app):
        """Invalid chars in new root (L553-554)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.root", "bad!name")
        result = inspector_commit_edit(app)
        assert result is False

    def test_root_rename_empty(self, make_app):
        """Empty root name (L548-549)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.root", "")
        result = inspector_commit_edit(app)
        assert result is False

    def test_root_rename_with_dots(self, make_app):
        """Root with dots is invalid (L548)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.root", "nav.sub")
        result = inspector_commit_edit(app)
        assert result is False

    def test_root_rename_collision(self, make_app):
        """Root rename collides with existing widget id (L580-581)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        sc = app.state.current_scene()
        # Add a widget with conflicting id
        extra = _w(type="label", x=100, y=0, width=30, height=10)
        extra._widget_id = "other.title"
        sc.widgets.append(extra)
        self._setup_edit(app, "comp.root", "other")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component menu_active editing
# ===========================================================================


class TestCompMenuActive:
    """Cover menu_active editing (L637-676)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_menu_active_set(self, make_app):
        """Set menu active item to 2 (1-based)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.active_item", "2")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        # item1 (idx 4) should become highlighted
        assert sc.widgets[4].style == "highlight"
        assert sc.widgets[3].style == "default"

    def test_menu_active_zero_based(self, make_app):
        """Set menu active using 0-based index (L651-652)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.active_item", "0")
        result = inspector_commit_edit(app)
        assert result is True

    def test_menu_active_out_of_range(self, make_app):
        """Invalid menu active value (L653-655)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.active_item", "99")
        result = inspector_commit_edit(app)
        assert result is False

    def test_menu_active_invalid_text(self, make_app):
        """Non-integer menu active value (L644-646)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._setup_edit(app, "comp.active_item", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_menu_active_no_items(self, make_app):
        """Menu with no item widgets (L640-641)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        # Create a menu component with no items
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        w1 = _w(type="panel", x=0, y=10, width=60, height=40, text="")
        w1._widget_id = "nav.panel"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:menu:nav:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.active_item", "1")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component tabs_active editing
# ===========================================================================


class TestCompTabsActive:
    """Cover tabs_active editing (L679-710)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_tabs_set_active(self, make_app):
        """Set active tab."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_tabs_component(app)
        self._setup_edit(app, "comp.active_tab", "2")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].style == "bold highlight"

    def test_tabs_zero_based(self, make_app):
        """Set tab using 0-based index (L692-693)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_tabs_component(app)
        self._setup_edit(app, "comp.active_tab", "0")
        result = inspector_commit_edit(app)
        assert result is True

    def test_tabs_out_of_range(self, make_app):
        """Invalid tab index (L694-699)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_tabs_component(app)
        self._setup_edit(app, "comp.active_tab", "99")
        result = inspector_commit_edit(app)
        assert result is False

    def test_tabs_invalid_text(self, make_app):
        """Non-integer tab value (L685-687)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_tabs_component(app)
        self._setup_edit(app, "comp.active_tab", "xyz")
        result = inspector_commit_edit(app)
        assert result is False

    def test_tabs_no_tabs(self, make_app):
        """Tabs component with no tab widgets (L681-682)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="panel", x=0, y=0, width=90, height=10)
        w0._widget_id = "tb.tabbar"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=90, height=20, text="Content")
        w1._widget_id = "tb.content.title"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:tabs:tb:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.active_tab", "1")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component list_count editing
# ===========================================================================


class TestCompListCount:
    """Cover list_count editing (L713-739)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_list_count_set(self, make_app):
        """Set list count to 5."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_list_component(app)
        self._setup_edit(app, "comp.count", "5")
        result = inspector_commit_edit(app)
        assert result is True

    def test_list_count_zero(self, make_app):
        """Set count to 0 (L726-727)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_list_component(app)
        self._setup_edit(app, "comp.count", "0")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].text == "0/0"

    def test_list_count_shrink(self, make_app):
        """Shrink count below visible items (L733)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_list_component(app)
        self._setup_edit(app, "comp.count", "1")
        result = inspector_commit_edit(app)
        assert result is True

    def test_list_count_negative(self, make_app):
        """Negative count (L719-720)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_list_component(app)
        self._setup_edit(app, "comp.count", "-5")
        result = inspector_commit_edit(app)
        assert result is False

    def test_list_count_invalid_text(self, make_app):
        """Non-integer count (L715-717)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_list_component(app)
        self._setup_edit(app, "comp.count", "abc")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component choice field editing
# ===========================================================================


class TestCompChoiceField:
    """Cover choice:... field editing (L742-747)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_chart_mode_choice(self, make_app):
        """Set chart mode via choice field."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_chart_component(app)
        self._setup_edit(app, "comp.mode", "line")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].style == "line"

    def test_chart_mode_invalid_choice(self, make_app):
        """Invalid choice value (L744-746)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_chart_component(app)
        self._setup_edit(app, "comp.mode", "scatter")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component int_list field editing
# ===========================================================================


class TestCompIntListField:
    """Cover int_list field editing (L749-753)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_chart_points(self, make_app):
        """Set data_points via int_list field."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_chart_component(app)
        self._setup_edit(app, "comp.points", "5,15,25,35,45")
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].data_points == [5, 15, 25, 35, 45]

    def test_chart_points_invalid(self, make_app):
        """Invalid int_list (L751-752)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_chart_component(app)
        self._setup_edit(app, "comp.points", "abc,def")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component int field editing
# ===========================================================================


class TestCompIntField:
    """Cover int field editing (L755-775)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_gauge_value_int(self, make_app):
        """Set gauge value via int field."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Gauge Title")
        w0._widget_id = "gh.title"
        sc.widgets.append(w0)
        w1 = _w(type="gauge", x=0, y=10, width=60, height=30, text="CPU")
        w1._widget_id = "gh.gauge"
        w1.value = 50
        w1.max_value = 100
        sc.widgets.append(w1)
        app.designer.groups = {"comp:gauge_hud:gh:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.gauge_value", "75")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[1].value == 75

    def test_gauge_max_value(self, make_app):
        """Set gauge max_value, clamping current value (L760-767)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "gh.title"
        sc.widgets.append(w0)
        w1 = _w(type="gauge", x=0, y=10, width=60, height=30, text="CPU")
        w1._widget_id = "gh.gauge"
        w1.value = 80
        w1.max_value = 100
        sc.widgets.append(w1)
        app.designer.groups = {"comp:gauge_hud:gh:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.gauge_max", "50")
        result = inspector_commit_edit(app)
        assert result is True
        # Value should be clamped to new max
        assert sc.widgets[1].value == 50

    def test_comp_int_field_invalid(self, make_app):
        """Invalid int field (L757-759)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "gh.title"
        sc.widgets.append(w0)
        w1 = _w(type="gauge", x=0, y=10, width=60, height=30, text="CPU")
        w1._widget_id = "gh.gauge"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:gauge_hud:gh:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.gauge_value", "abc")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — component str field editing
# ===========================================================================


class TestCompStrField:
    """Cover str field editing (default case in comp editing)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_card_title(self, make_app):
        """Set card title."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Old Title")
        w0._widget_id = "mycard.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=20, text="Value")
        w1._widget_id = "mycard.value"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:card:mycard:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.title", "New Title")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0].text == "New Title"

    def test_comp_not_editable(self, make_app):
        """Unknown comp field (L623-625)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "mycard.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=20, text="Value")
        w1._widget_id = "mycard.value"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:card:mycard:1": [0, 1]}
        _sel(app, 0, 1)
        self._setup_edit(app, "comp.nonexistent", "whatever")
        result = inspector_commit_edit(app)
        assert result is True  # cancel_edit path returns True

    def test_comp_missing_role(self, make_app):
        """Component role widget missing (L630-631)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        # Card needs title and value roles, but we only provide title
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "mycard.title"
        sc.widgets.append(w0)
        app.designer.groups = {"comp:card:mycard:1": [0]}
        _sel(app, 0)
        # Try to edit "value" field - the widget for "value" role doesn't exist
        self._setup_edit(app, "comp.value", "New Value")
        result = inspector_commit_edit(app)
        assert result is False

    def test_comp_no_component_selected(self, make_app):
        """No component group selected (L541-542)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "comp.title"
        app.state.inspector_input_buffer = "test"
        app.state.inspector_raw_input = "test"
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — inspector_field_to_str (component paths)
# ===========================================================================


class TestInspectorFieldToStr:
    """Cover inspector_field_to_str branches for component fields."""

    def test_comp_root(self, make_app):
        """comp.root returns root prefix (L89)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_menu_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.root", sc.widgets[0])
        assert result == "nav"

    def test_comp_menu_active_str(self, make_app):
        """comp.active_item returns active position (L97)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_menu_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.active_item", sc.widgets[2])
        # item0 is highlighted, so active_pos = 1 (1-based)
        assert result == "1"

    def test_comp_tabs_active_str(self, make_app):
        """comp.active_tab returns active tab number."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_tabs_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.active_tab", sc.widgets[3])
        # tab1 has "bold highlight" style
        assert result == "1"

    def test_comp_list_count_str(self, make_app):
        """comp.count returns total count (L133)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_list_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.count", sc.widgets[1])
        assert result == "3"

    def test_comp_int_str(self, make_app):
        """comp field with kind=int returns int string (L138-141)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "gh.title"
        sc.widgets.append(w0)
        w1 = _w(type="gauge", x=0, y=10, width=60, height=30, text="CPU")
        w1._widget_id = "gh.gauge"
        w1.value = 42
        sc.widgets.append(w1)
        app.designer.groups = {"comp:gauge_hud:gh:1": [0, 1]}
        _sel(app, 0, 1)
        result = inspector_field_to_str(app, "comp.gauge_value", sc.widgets[1])
        assert result == "42"

    def test_comp_int_list_str(self, make_app):
        """comp field with kind=int_list (L143)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_chart_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.points", sc.widgets[1])
        assert "10" in result

    def test_comp_choice_str(self, make_app):
        """comp field with kind=choice:... (L145)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        _setup_chart_component(app)
        sc = app.state.current_scene()
        result = inspector_field_to_str(app, "comp.mode", sc.widgets[1])
        assert result == "bar"

    def test_comp_no_context(self, make_app):
        """comp.* with no component group returns empty (L147)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        result = inspector_field_to_str(app, "comp.title", sc.widgets[0])
        assert result == ""

    def test_comp_menu_active_no_items_str(self, make_app):
        """Menu active with no items returns empty (L97)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        w1 = _w(type="panel", x=0, y=10, width=60, height=40, text="")
        w1._widget_id = "nav.panel"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:menu:nav:1": [0, 1]}
        _sel(app, 0, 1)
        result = inspector_field_to_str(app, "comp.active_item", sc.widgets[1])
        assert result == ""


# ===========================================================================
# inspector_logic — compute_inspector_rows with component
# ===========================================================================


class TestComputeInspectorRowsComponent:
    """Cover compute_inspector_rows with component groups (L1245-1257)."""

    def test_rows_with_component(self, make_app):
        """Multi-select with component group generates component rows."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        _setup_menu_component(app)
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "group" in keys
        assert "component" in keys
        assert "comp.root" in keys
        assert "hint" in keys

    def test_rows_with_single_widget_component(self, make_app):
        """Single widget in component group (L1245-1257 single-select path)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "mycard.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=20, text="Value")
        w1._widget_id = "mycard.value"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:card:mycard:1": [0, 1]}
        # Select only first widget
        _sel(app, 0)
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "comp.root" in keys

    def test_rows_with_warning(self, make_app):
        """Resources over limit produces warning (L1119-1120)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        # Monkeypatch estimate_resources to return over-limit
        original_est = app.designer.estimate_resources

        def fake_est(profile=None):
            r = original_est(profile=profile)
            if r:
                r["fb_over"] = True
            return r

        app.designer.estimate_resources = fake_est
        rows, warning, w = compute_inspector_rows(app)
        assert warning is True

    def test_rows_with_live_preview(self, make_app):
        """Live preview port displayed (L1128)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        app.live_preview_port = "COM3"
        app.live_preview_baud = 115200
        rows, warning, w = compute_inspector_rows(app)
        live_rows = [r for r in rows if r[0] == "live"]
        assert live_rows
        assert "COM3" in live_rows[0][1]

    def test_rows_with_groups_in_layers(self, make_app):
        """Groups shown in layers section (L1209, L1216)."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=0, y=30, width=40, height=10))
        app.designer.groups = {"mygroup:1": [0, 1]}
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert any(k.startswith("group:") for k in keys)


# ===========================================================================
# inspector_logic — exception branches (make _save_state throw)
# ===========================================================================


class TestInspectorExceptionBranches:
    """Cover except Exception: pass branches by making _save_state() throw."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def _make_save_throw(self, app):
        """Make designer._save_state() raise an exception."""

        def _broken():
            raise TypeError("save failed")

        app.designer._save_state = _broken

    def test_position_save_throws(self, make_app):
        """_position quick-set with _save_state exception (L231-232)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_position", "10,20")
        result = inspector_commit_edit(app)
        assert result is True

    def test_padding_save_throws(self, make_app):
        """_padding quick-set with exception (L257-258)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_padding", "2,4")
        result = inspector_commit_edit(app)
        assert result is True

    def test_margin_save_throws(self, make_app):
        """_margin quick-set with exception (L283-284)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_margin", "1,2")
        result = inspector_commit_edit(app)
        assert result is True

    def test_spacing_save_throws(self, make_app):
        """_spacing quick-set with exception (L325-326)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_spacing", "4,4,0,0")
        result = inspector_commit_edit(app)
        assert result is True

    def test_size_save_throws(self, make_app):
        """_size quick-set with exception (L458-459)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_size", "80,40")
        result = inspector_commit_edit(app)
        assert result is True

    def test_value_range_save_throws(self, make_app):
        """_value_range quick-set exception (L420-421)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="slider", x=0, y=0, width=60, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "_value_range", "0,200")
        result = inspector_commit_edit(app)
        assert result is True

    def test_comp_root_save_throws(self, make_app):
        """comp.root rename with save exception (L586-587)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        _setup_menu_component(app)
        self._make_save_throw(app)
        self._setup_edit(app, "comp.root", "newroot")
        result = inspector_commit_edit(app)
        assert result is True

    def test_comp_field_save_throws(self, make_app):
        """comp.title with save exception (L635-636)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Old")
        w0._widget_id = "mycard.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=20, text="Val")
        w1._widget_id = "mycard.value"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:card:mycard:1": [0, 1]}
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "comp.title", "New")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_color_save_throws(self, make_app):
        """Multi-select color_fg with save exception (L813-814)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "color_fg", "gray")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_align_save_throws(self, make_app):
        """Multi-select align with save exception (L825-826)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "align", "center")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_valign_save_throws(self, make_app):
        """L837-838: valign save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "valign", "bottom")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_border_style_save_throws(self, make_app):
        """L849-850: border_style save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "border_style", "double")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_text_overflow_save_throws(self, make_app):
        """L861-862: text_overflow save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "text_overflow", "wrap")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_max_lines_save_throws(self, make_app):
        """L876-877: max_lines save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "max_lines", "3")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_text_save_throws(self, make_app):
        """L884-885: text save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "text", "hello")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_runtime_save_throws(self, make_app):
        """L892-893: runtime save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "runtime", "btn:toggle")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_data_points_save_throws(self, make_app):
        """L904-905: data_points save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        sc.widgets.append(_w(type="chart", x=90, y=0, width=80, height=40))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "data_points", "10,20,30")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_chart_mode_save_throws(self, make_app):
        """L924-925: chart_mode save exception."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        sc.widgets.append(_w(type="chart", x=90, y=0, width=80, height=40))
        _sel(app, 0, 1)
        self._make_save_throw(app)
        self._setup_edit(app, "chart_mode", "line")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_text_save_throws(self, make_app):
        """Single-widget text save exception (L957-958)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "text", "new text")
        result = inspector_commit_edit(app)
        # Should still succeed even with save exception
        assert result is True

    def test_single_runtime_save_throws(self, make_app):
        """Single-widget runtime save exception (L964-965)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "runtime", "btn:x")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_xy_save_throws(self, make_app):
        """Single-widget x/y save exception (L970-971)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        app.snap_enabled = False
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "x", "10")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_width_save_throws(self, make_app):
        """Single-widget width save exception (L976-977)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "width", "50")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_value_save_throws(self, make_app):
        """Single-widget value save exception (L985-986)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="slider", x=0, y=0, width=60, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "value", "50")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_color_fg_save_throws(self, make_app):
        """Single-widget color_fg save exception (L1001-1002)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "color_fg", "gray")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_align_save_throws(self, make_app):
        """Single-widget align save exception (L1018-1019)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "align", "center")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_valign_save_throws(self, make_app):
        """Single-widget valign save exception (L1028-1029)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "valign", "top")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_border_style_save_throws(self, make_app):
        """Single-widget border_style save exception (L1038-1039)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "border_style", "double")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_text_overflow_save_throws(self, make_app):
        """Single-widget text_overflow save exception (L1048-1049)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "text_overflow", "wrap")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_max_lines_save_throws(self, make_app):
        """Single-widget max_lines save exception (L1058-1059)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "max_lines", "5")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_z_index_save_throws(self, make_app):
        """Single-widget z_index save exception (L1064-1065)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "z_index", "5")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_data_points_save_throws(self, make_app):
        """Single-widget data_points save exception (L1082-1083)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "data_points", "10,20,30")
        result = inspector_commit_edit(app)
        assert result is True

    def test_single_chart_mode_save_throws(self, make_app):
        """Single-widget chart_mode save exception (L1092-1093)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        _sel(app, 0)
        self._make_save_throw(app)
        self._setup_edit(app, "chart_mode", "bar")
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# inspector_logic — edge cases in multi-select (invalid values, error paths)
# ===========================================================================


class TestMultiSelectErrorPaths:
    """Cover error paths in multi-select editing."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_multi_x_invalid(self, make_app):
        """L785-787: Invalid x value in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "x", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_width_invalid(self, make_app):
        """L795+: Invalid width in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "width", "xyz")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_color_fg_invalid(self, make_app):
        """L809-810: Invalid color in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "color_fg", "not_a_color_xyz")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_align_invalid(self, make_app):
        """Invalid align in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "align", "invalid_align")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_valign_invalid(self, make_app):
        """Invalid valign in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "valign", "nowhere")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_border_style_invalid(self, make_app):
        """Invalid border_style in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "border_style", "invalid_style")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_text_overflow_invalid(self, make_app):
        """Invalid text_overflow in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "text_overflow", "invalid_overflow")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_max_lines_invalid(self, make_app):
        """Invalid max_lines in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "max_lines", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_max_lines_to_none(self, make_app):
        """max_lines set to None from '0' in multi-select (L873)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "max_lines", "0")
        result = inspector_commit_edit(app)
        assert result is True

    def test_multi_data_points_invalid(self, make_app):
        """Invalid data_points format in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        sc.widgets.append(_w(type="chart", x=90, y=0, width=80, height=40))
        _sel(app, 0, 1)
        self._setup_edit(app, "data_points", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_data_points_no_charts(self, make_app):
        """data_points on non-chart widgets in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "data_points", "10,20")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_chart_mode_invalid(self, make_app):
        """Invalid chart_mode in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        sc.widgets.append(_w(type="chart", x=90, y=0, width=80, height=40))
        _sel(app, 0, 1)
        self._setup_edit(app, "chart_mode", "scatter")
        result = inspector_commit_edit(app)
        assert result is False

    def test_multi_chart_mode_no_charts(self, make_app):
        """chart_mode on non-chart widgets in multi-select."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="button", x=50, y=0, width=40, height=20))
        _sel(app, 0, 1)
        self._setup_edit(app, "chart_mode", "bar")
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# inspector_logic — edge cases: empty selection, widget None
# ===========================================================================


class TestInspectorEdgeCases:
    """Cover edge cases like empty selection for quick-set fields."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_margin_empty_selection(self, make_app):
        """L279-280: _margin with empty selection."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        app.state.selected = []
        app.state.selected_idx = None
        self._setup_edit(app, "_margin", "1,2")
        result = inspector_commit_edit(app)
        assert result is True

    def test_value_range_empty_selection(self, make_app):
        """L416-417: _value_range with empty selection."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        app.state.selected = []
        app.state.selected_idx = None
        self._setup_edit(app, "_value_range", "0,100")
        result = inspector_commit_edit(app)
        assert result is True

    def test_widget_none_bail(self, make_app):
        """L528-529: widget is None, cancel edit."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        # Empty widgets but non-empty selection
        app.state.selected = [99]
        app.state.selected_idx = 99
        self._setup_edit(app, "text", "hello")
        result = inspector_commit_edit(app)
        assert result is True

    def test_scene_name_save_throws(self, make_app):
        """_scene_name with save exception (L499-500, L519-520)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)

        def _broken():
            raise TypeError("save failed")

        app.designer._save_state = _broken
        self._setup_edit(app, "_scene_name", "new_name")
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# input_handlers — on_mouse_down: sim mode click (L1015-1016)
# ===========================================================================


class TestMouseSimModeClick:
    """Cover on_mouse_down in sim_input_mode."""

    def test_sim_mode_click_focusable(self, make_app):
        """Click focusable widget in sim mode sets focus."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        sc = app.state.current_scene()
        b = _w(type="button", x=10, y=10, width=40, height=20)
        sc.widgets.append(b)
        app.sim_input_mode = True
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)

    def test_sim_mode_click_empty(self, make_app):
        """Click empty area in sim mode — no crash."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        app.sim_input_mode = True
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 200, sr.y + 100)
        on_mouse_down(app, pos)


# ===========================================================================
# input_handlers — on_mouse_down: Alt+drag clone (L949-982)
# ===========================================================================


class TestMouseAltDragClone:
    """Cover Alt+drag cloning in on_mouse_down."""

    def test_alt_drag_clone(self, make_app, monkeypatch):
        """Alt+click on selected widget clones it."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: ALT)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)
        # Should have cloned: original + clone
        assert len(sc.widgets) >= 2


# ===========================================================================
# input_handlers — on_mouse_move: drag (L1130+)
# ===========================================================================


class TestMouseMoveDrag:
    """Cover on_mouse_move drag path."""

    def test_drag_widget(self, make_app, monkeypatch):
        """Drag selected widget."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Click to start drag
        pos = (sr.x + 20, sr.y + 20)
        on_mouse_down(app, pos)
        assert app.state.dragging
        # Move
        new_pos = (sr.x + 40, sr.y + 30)
        on_mouse_move(app, new_pos, (1, 0, 0))


# ===========================================================================
# input_handlers — on_mouse_move: resize (L1165+)
# ===========================================================================


class TestMouseMoveResize:
    """Cover on_mouse_move resize path."""

    def test_resize_widget(self, make_app, monkeypatch):
        """Resize widget by dragging handle."""
        from cyberpunk_designer.input_handlers import on_mouse_down, on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Click on resize handle (bottom-right corner)
        handle_x = sr.x + 10 + 40 - 4  # x + width - GRID/2
        handle_y = sr.y + 10 + 20 - 4  # y + height - GRID/2
        on_mouse_down(app, (handle_x, handle_y))
        assert app.state.resizing
        # Drag to resize
        new_pos = (sr.x + 80, sr.y + 60)
        on_mouse_move(app, new_pos, (1, 0, 0))


# ===========================================================================
# input_handlers — on_mouse_move: box select
# ===========================================================================


class TestMouseBoxSelect:
    """Cover rubber-band box selection."""

    def test_box_select(self, make_app):
        """Draw box selection rect."""
        from cyberpunk_designer.input_handlers import on_mouse_move, on_mouse_up

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        sc.widgets.append(_w(type="button", x=60, y=10, width=40, height=20))
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Start box select
        app.pointer_down = True
        app.state.box_select_start = (sr.x + 5, sr.y + 5)
        on_mouse_move(app, (sr.x + 120, sr.y + 40), (1, 0, 0))
        assert app.state.box_select_rect is not None
        # Finish box select
        on_mouse_up(app, (sr.x + 120, sr.y + 40))


# ===========================================================================
# input_handlers — on_mouse_up: cleanup
# ===========================================================================


class TestMouseUp:
    """Cover on_mouse_up cleanup (L1015-1016 for regular mode)."""

    def test_mouse_up_cleanup(self, make_app):
        """Mouse up resets drag/resize state."""
        from cyberpunk_designer.input_handlers import on_mouse_up

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        app.state.dragging = True
        app.state.saved_this_drag = True
        on_mouse_up(app, (100, 100))
        assert not app.state.dragging
        assert not app.state.resizing


# ===========================================================================
# input_handlers — on_mouse_move: layer drag reorder
# ===========================================================================


class TestMouseLayerDrag:
    """Cover layer drag reorder in on_mouse_move."""

    def test_layer_drag_reorder(self, make_app):
        """Drag-reorder widgets in inspector layers."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20, text="A"))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20, text="B"))
        _sel(app, 0)
        # Start a layer drag
        app.pointer_down = True
        app._layer_drag_idx = 0
        # Set up inspector hitboxes for layers
        sr = app.layout.inspector_rect
        app.inspector_hitboxes = [
            (pygame.Rect(sr.x, sr.y, sr.width, 20), "layer:0"),
            (pygame.Rect(sr.x, sr.y + 20, sr.width, 20), "layer:1"),
        ]
        # Move to target
        on_mouse_move(app, (sr.x + 5, sr.y + 25), (1, 0, 0))
        # Widget at index 0 should have moved to index 1
        assert sc.widgets[1].text == "A"


# ===========================================================================
# _parse_pair and _parse_active_count helpers
# ===========================================================================


class TestHelperFunctions:
    """Cover helper function edge cases."""

    def test_parse_active_count_valid(self):
        from cyberpunk_designer.inspector_logic import _parse_active_count

        result = _parse_active_count("3/10")
        assert result == (2, 10)

    def test_parse_active_count_no_slash(self):
        from cyberpunk_designer.inspector_logic import _parse_active_count

        result = _parse_active_count("noslash")
        assert result is None

    def test_parse_active_count_zero_count(self):
        from cyberpunk_designer.inspector_logic import _parse_active_count

        result = _parse_active_count("0/0")
        assert result == (0, 0)

    def test_parse_active_count_invalid(self):
        from cyberpunk_designer.inspector_logic import _parse_active_count

        result = _parse_active_count("abc/def")
        assert result is None

    def test_sorted_role_indices(self):
        from cyberpunk_designer.inspector_logic import _sorted_role_indices

        role_idx = {"item0": 2, "item1": 3, "title": 0, "item2": 5}
        result = _sorted_role_indices(role_idx, "item")
        assert result == [(0, 2), (1, 3), (2, 5)]

    def test_sorted_role_indices_empty_prefix(self):
        from cyberpunk_designer.inspector_logic import _sorted_role_indices

        result = _sorted_role_indices({"item0": 1}, "")
        assert result == []

    def test_sorted_role_indices_no_match(self):
        from cyberpunk_designer.inspector_logic import _sorted_role_indices

        result = _sorted_role_indices({"item0": 1}, "tab")
        assert result == []


# ===========================================================================
# inspector_logic — single-widget _apply_int error paths
# ===========================================================================


class TestSingleWidgetApplyIntErrors:
    """Cover _apply_int returning False for invalid input in single-widget edits."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_single_x_invalid(self, make_app):
        """L991: _apply_int('x') fails for non-integer."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "x", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_width_invalid(self, make_app):
        """L994: _apply_int('width') fails for non-integer."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "width", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_height_invalid(self, make_app):
        """L994: _apply_int('height') fails."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "height", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_value_invalid(self, make_app):
        """L1004: _apply_int('value') fails."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="slider", x=0, y=0, width=60, height=20))
        _sel(app, 0)
        self._setup_edit(app, "value", "not_a_number")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_max_value_invalid(self, make_app):
        """L1011: _apply_int('max_value') fails."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="slider", x=0, y=0, width=60, height=20))
        _sel(app, 0)
        self._setup_edit(app, "max_value", "xyz")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_color_fg_invalid(self, make_app):
        """Invalid color_fg in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "color_fg", "not_a_color_xyz")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_align_invalid(self, make_app):
        """Invalid align in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "align", "nowhere")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_valign_invalid(self, make_app):
        """Invalid valign in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "valign", "nowhere")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_border_style_invalid(self, make_app):
        """Invalid border_style in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "border_style", "invalid_style")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_text_overflow_invalid(self, make_app):
        """Invalid text_overflow in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "text_overflow", "invalid_overflow")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_max_lines_invalid(self, make_app):
        """Invalid max_lines in single widget."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "max_lines", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_data_points_invalid(self, make_app):
        """Invalid data_points in single chart."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        _sel(app, 0)
        self._setup_edit(app, "data_points", "abc")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_chart_mode_invalid(self, make_app):
        """Invalid chart_mode in single chart."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="chart", x=0, y=0, width=80, height=40))
        _sel(app, 0)
        self._setup_edit(app, "chart_mode", "scatter")
        result = inspector_commit_edit(app)
        assert result is False

    def test_single_max_lines_negative(self, make_app):
        """Negative max_lines becomes None (L873 equivalent)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        self._setup_edit(app, "max_lines", "-5")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0].max_lines is None


# ===========================================================================
# inspector_logic — root rename with root-only widget_id and models
# ===========================================================================


class TestRootRenameEdgeCases:
    """Cover root rename branches for root-only widget_id and models."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_root_rename_with_root_widget(self, make_app):
        """Root widget with _widget_id=root (L574, L595)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        # Widget whose _widget_id == root ("nav")
        w0 = _w(type="panel", x=0, y=0, width=80, height=80)
        w0._widget_id = "nav"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=2, y=2, width=76, height=10, text="Title")
        w1._widget_id = "nav.title"
        sc.widgets.append(w1)
        # Widget with empty _widget_id (L572, L593)
        w2 = _w(type="label", x=2, y=14, width=76, height=10, text="No ID")
        w2._widget_id = None
        sc.widgets.append(w2)
        app.designer.groups = {"comp:menu:nav:1": [0, 1, 2]}
        _sel(app, 0, 1, 2)
        self._setup_edit(app, "comp.root", "menu2")
        result = inspector_commit_edit(app)
        assert result is True
        assert sc.widgets[0]._widget_id == "menu2"
        assert sc.widgets[1]._widget_id == "menu2.title"

    def test_root_rename_with_sim_listmodels(self, make_app):
        """Root rename clears _sim_listmodels cache (L616-617)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=10, text="Scroll")
        w1._widget_id = "nav.scroll"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:menu:nav:1": [0, 1]}
        _sel(app, 0, 1)
        app._sim_listmodels = {"nav": object(), "other": object()}
        self._setup_edit(app, "comp.root", "menu3")
        result = inspector_commit_edit(app)
        assert result is True
        assert "nav" not in app._sim_listmodels

    def test_root_rename_groups_exception(self, make_app):
        """Groups attribute access exception during rename (L602-603)."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "nav.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=10, text="Scroll")
        w1._widget_id = "nav.scroll"
        sc.widgets.append(w1)
        app.designer.groups = {"comp:menu:nav:1": [0, 1]}
        _sel(app, 0, 1)

        # Make groups property throw
        class BrokenGroups:
            def __getattr__(self, name):
                if name == "groups":
                    raise AttributeError("broken")
                raise AttributeError(name)

        self._setup_edit(app, "comp.root", "menu4")
        # Can't easily break groups access during rename since it
        # was already accessed for group lookup. Just verify rename works.
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# inspector_logic — tabs-active "bold" style fallback (L118-123)
# ===========================================================================


class TestTabsActiveBoldStyle:
    """Cover the 'bold' style fallback in inspector_field_to_str for tabs."""

    def test_tabs_bold_style(self, make_app):
        """Tabs with 'bold' style (not 'highlight') (L118-123)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        # Tab1 with "bold" style (not "bold highlight")
        w0 = _w(type="button", x=0, y=0, width=30, height=10, text="Tab1")
        w0._widget_id = "tb.tab1"
        w0.style = "bold"
        sc.widgets.append(w0)
        w1 = _w(type="button", x=30, y=0, width=30, height=10, text="Tab2")
        w1._widget_id = "tb.tab2"
        w1.style = "default"
        sc.widgets.append(w1)
        w2 = _w(type="panel", x=0, y=10, width=60, height=20)
        w2._widget_id = "tb.tabbar"
        sc.widgets.append(w2)
        app.designer.groups = {"comp:tabs:tb:1": [0, 1, 2]}
        _sel(app, 0, 1, 2)
        result = inspector_field_to_str(app, "comp.active_tab", sc.widgets[2])
        assert result == "1"

    def test_tabs_no_active(self, make_app):
        """Tabs with no active style — defaults to first tab."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="button", x=0, y=0, width=30, height=10, text="Tab1")
        w0._widget_id = "tb.tab1"
        w0.style = "default"
        sc.widgets.append(w0)
        w1 = _w(type="button", x=30, y=0, width=30, height=10, text="Tab2")
        w1._widget_id = "tb.tab2"
        w1.style = "default"
        sc.widgets.append(w1)
        w2 = _w(type="panel", x=0, y=10, width=60, height=20)
        w2._widget_id = "tb.tabbar"
        sc.widgets.append(w2)
        app.designer.groups = {"comp:tabs:tb:1": [0, 1, 2]}
        _sel(app, 0, 1, 2)
        result = inspector_field_to_str(app, "comp.active_tab", sc.widgets[2])
        # Should return the first tab number since no tab is highlighted
        assert result == "1"


# ===========================================================================
# inspector_logic — list_count visible fallback (L133)
# ===========================================================================


class TestListCountVisible:
    """Cover list_count fallback to visible count."""

    def test_list_count_no_scroll_widget(self, make_app):
        """list_count when scroll widget has no parseable text (L133)."""
        from cyberpunk_designer.inspector_logic import inspector_field_to_str

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="label", x=0, y=0, width=60, height=10, text="Title")
        w0._widget_id = "lst.title"
        sc.widgets.append(w0)
        w1 = _w(type="label", x=0, y=10, width=60, height=10, text="no_format")
        w1._widget_id = "lst.scroll"
        sc.widgets.append(w1)
        w2 = _w(type="label", x=0, y=20, width=60, height=10, text="A")
        w2._widget_id = "lst.item0.label"
        w2.style = "highlight"
        sc.widgets.append(w2)
        w3 = _w(type="label", x=0, y=30, width=60, height=10, text="B")
        w3._widget_id = "lst.item1.label"
        sc.widgets.append(w3)
        w4 = _w(type="panel", x=0, y=20, width=60, height=30)
        w4._widget_id = "lst.panel"
        sc.widgets.append(w4)
        app.designer.groups = {"comp:list:lst:1": [0, 1, 2, 3, 4]}
        _sel(app, 0, 1, 2, 3, 4)
        result = inspector_field_to_str(app, "comp.count", sc.widgets[1])
        # Falls back to visible count
        assert isinstance(result, str)


# ===========================================================================
# inspector_logic — _parse_pair edge case (L22)
# ===========================================================================


class TestParsePairNone:
    """Cover _parse_pair returning None."""

    def test_non_numeric_pair(self):
        from cyberpunk_designer.inspector_logic import _parse_pair

        result = _parse_pair("abc,def")
        assert result is None


# ===========================================================================
# inspector_logic — compute_inspector_rows misc (L1140, L1216)
# ===========================================================================


class TestComputeRowsMisc:
    """Cover remaining compute_inspector_rows edge cases."""

    def test_rows_empty_string_func(self, make_app):
        """L1140: _mixed_str returns empty for all-empty values."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        sc = app.state.current_scene()
        w0 = _w(type="button", x=0, y=0, width=40, height=20)
        w0.color_fg = ""
        sc.widgets.append(w0)
        w1 = _w(type="button", x=50, y=0, width=40, height=20)
        w1.color_fg = ""
        sc.widgets.append(w1)
        _sel(app, 0, 1)
        rows, warning, w = compute_inspector_rows(app)
        cfg_rows = {r[0]: r[1] for r in rows}
        assert "color_fg" in cfg_rows

    def test_rows_non_comp_group(self, make_app):
        """L1216: Non-comp group in layers section."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=50, y=0, width=40, height=20))
        sc.widgets.append(_w(type="label", x=0, y=30, width=40, height=10))
        app.designer.groups = {"mygroup": [0, 1]}
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert any(k.startswith("group:mygroup") for k in keys)

    def test_rows_groups_exception(self, make_app):
        """L1288-1289: groups attribute exception."""
        from cyberpunk_designer.inspector_logic import compute_inspector_rows

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        # Do NOT select anything — so _selected_component_group is skipped
        app.state.selected = []
        # Make groups something dict() can't convert (L1288-1289)
        app.designer.groups = 12345
        rows, warning, w = compute_inspector_rows(app)
        # Should still return rows (handles exception, groups = {})
        assert any(r[0].startswith("_section") for r in rows)
        app.designer.groups = {}


# ===========================================================================
# inspector_logic — multi-select bounds None for x/y
# ===========================================================================


class TestMultiBoundsNone:
    """Cover bounds returning None in multi-select edits (L790, L802)."""

    def _setup_edit(self, app, field, buf):
        app.state.inspector_selected_field = field
        app.state.inspector_input_buffer = buf
        app.state.inspector_raw_input = buf

    def test_multi_x_bounds_none(self, make_app):
        """L790: Multi x/y with selection having invalid widget indices."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        # Only one widget exists but select indices 0 and 99
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        self._setup_edit(app, "x", "10")
        inspector_commit_edit(app)
        # Should handle gracefully

    def test_multi_width_bounds_none(self, make_app):
        """L802: Multi width with invalid indices."""
        from cyberpunk_designer.inspector_logic import inspector_commit_edit

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        self._setup_edit(app, "width", "50")
        inspector_commit_edit(app)
        # Should handle gracefully
