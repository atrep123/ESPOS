"""Tests for focus_nav _ensure_sim_listmodel, _apply_sim_listmodel, _sim_try_scroll_list."""

from __future__ import annotations

from types import SimpleNamespace

from cyberpunk_designer.focus_nav import (
    _apply_sim_listmodel,
    _ensure_sim_listmodel,
    _find_by_widget_id,
    _sim_try_scroll_list,
    _SimListModel,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(wid: str, **kw) -> SimpleNamespace:
    """Create a mock widget with a _widget_id and common defaults."""
    defaults = dict(text="", value=0, enabled=True, visible=True, type="button", x=0, y=0)
    defaults.update(kw)
    defaults["_widget_id"] = wid
    return SimpleNamespace(**defaults)


def _scene(widgets: list) -> SimpleNamespace:
    return SimpleNamespace(widgets=widgets)


def _app(scene: SimpleNamespace) -> SimpleNamespace:
    """Create a mock app with state.current_scene() returning the given scene."""
    state = SimpleNamespace(current_scene=lambda: scene)
    app = SimpleNamespace(
        state=state,
        focus_idx=None,
        focus_edit_value=False,
        _sim_listmodels={},
        _sim_runtime_snapshot={},
    )
    app._set_selection = lambda sel, anchor_idx=None: None
    return app


# ---------------------------------------------------------------------------
# _ensure_sim_listmodel
# ---------------------------------------------------------------------------


class TestEnsureSimListmodel:
    def test_no_item_slots_returns_none(self):
        sc = _scene([_w("mylist.scroll", text="1/5")])
        app = _app(sc)
        assert _ensure_sim_listmodel(app, sc, "mylist") is None

    def test_basic_3_items_no_scroll(self):
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.item1", text="B"),
                _w("lst.item2", text="C"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m is not None
        assert m.count == 3
        assert m.active == 0
        assert m.offset == 0
        assert m.seed_labels == ["A", "B", "C"]
        assert m.has_value_cols is False

    def test_with_scroll_widget(self):
        sc = _scene(
            [
                _w("lst.item0", text="X"),
                _w("lst.item1", text="Y"),
                _w("lst.scroll", text="2/5"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m is not None
        assert m.count == 5
        assert m.active == 1  # "2/5" → a=2, parsed as a-1=1
        assert m.seed_labels == ["X", "Y"]
        assert m.has_value_cols is False

    def test_with_value_columns(self):
        sc = _scene(
            [
                _w("lst.item0"),
                _w("lst.item0.label", text="Name"),
                _w("lst.item0.value", text="42"),
                _w("lst.item1"),
                _w("lst.item1.label", text="Age"),
                _w("lst.item1.value", text="10"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m is not None
        assert m.count == 2
        assert m.has_value_cols is True
        assert m.seed_labels == ["Name", "Age"]
        assert m.seed_values == ["42", "10"]

    def test_cached_on_second_call(self):
        sc = _scene([_w("lst.item0", text="A")])
        app = _app(sc)
        m1 = _ensure_sim_listmodel(app, sc, "lst")
        m2 = _ensure_sim_listmodel(app, sc, "lst")
        assert m1 is m2

    def test_models_dict_created_if_missing(self):
        sc = _scene([_w("lst.item0", text="A")])
        app = SimpleNamespace(
            state=SimpleNamespace(current_scene=lambda: sc),
            focus_idx=None,
        )
        # no _sim_listmodels attr at all
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m is not None
        assert hasattr(app, "_sim_listmodels")

    def test_scroll_bad_text_defaults_to_visible(self):
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.item1", text="B"),
                _w("lst.scroll", text="garbage"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m is not None
        assert m.count == 2  # fallback = visible slots
        assert m.active == 0

    def test_scroll_zero_count_returns_model_with_zero(self):
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.scroll", text="1/0"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        # _parse_scroll_text returns None for b<=0, so fallback
        assert m is not None
        assert m.count == 1  # fallback = visible

    def test_active_clamped_to_count(self):
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.scroll", text="99/3"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        # _parse_scroll_text clamps a to b, so active = b-1 = 2
        assert m.active == 2

    def test_seed_labels_limited_to_min_visible_count(self):
        """If count > visible, seed_labels only has 'visible' entries."""
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.item1", text="B"),
                _w("lst.scroll", text="1/10"),
            ]
        )
        app = _app(sc)
        m = _ensure_sim_listmodel(app, sc, "lst")
        assert m.count == 10
        assert len(m.seed_labels) == 2  # min(visible=2, count=10)


# ---------------------------------------------------------------------------
# _apply_sim_listmodel
# ---------------------------------------------------------------------------


class TestApplySimListmodel:
    def test_scroll_text_updated(self):
        sc = _scene(
            [
                _w("lst.item0", text="A"),
                _w("lst.item1", text="B"),
                _w("lst.scroll", text="1/5"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(
            count=5, active=2, offset=1, seed_labels=["a", "b", "c", "d", "e"], seed_values=[]
        )
        _apply_sim_listmodel(app, sc, "lst", m, 2)
        assert sc.widgets[2].text == "3/5"  # active+1=3

    def test_scroll_text_zero_count(self):
        sc = _scene(
            [
                _w("lst.item0"),
                _w("lst.scroll", text="1/1"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(count=0, active=0, offset=0, seed_labels=[], seed_values=[])
        _apply_sim_listmodel(app, sc, "lst", m, 1)
        assert sc.widgets[1].text == "0/0"

    def test_item_enabled_visible_value_set(self):
        sc = _scene(
            [
                _w("lst.item0", text="old"),
                _w("lst.item1", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(
            count=5, active=0, offset=0, seed_labels=["A", "B", "C", "D", "E"], seed_values=[]
        )
        _apply_sim_listmodel(app, sc, "lst", m, 2)
        # slot 0 → abs_idx 0 → valid
        assert sc.widgets[0].enabled is True
        assert sc.widgets[0].visible is True
        assert sc.widgets[0].value == 0
        assert sc.widgets[0].text == "A"
        # slot 1 → abs_idx 1 → valid
        assert sc.widgets[1].value == 1
        assert sc.widgets[1].text == "B"

    def test_item_beyond_count_disabled(self):
        sc = _scene(
            [
                _w("lst.item0", text="old"),
                _w("lst.item1", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(count=1, active=0, offset=0, seed_labels=["A"], seed_values=[])
        _apply_sim_listmodel(app, sc, "lst", m, 2)
        # slot 0 → abs_idx 0 → valid
        assert sc.widgets[0].enabled is True
        assert sc.widgets[0].text == "A"
        # slot 1 → abs_idx 1 → out of range
        assert sc.widgets[1].enabled is False
        assert sc.widgets[1].value == 0

    def test_value_column_mode(self):
        sc = _scene(
            [
                _w("lst.item0"),
                _w("lst.item0.label", text="old"),
                _w("lst.item0.value", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(
            count=2,
            active=0,
            offset=0,
            seed_labels=["Name", "Age"],
            seed_values=["42", "10"],
            has_value_cols=True,
        )
        _apply_sim_listmodel(app, sc, "lst", m, 1)
        assert sc.widgets[1].text == "Name"
        assert sc.widgets[2].text == "42"

    def test_offset_applied(self):
        sc = _scene(
            [
                _w("lst.item0", text="old"),
                _w("lst.item1", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(
            count=5, active=2, offset=2, seed_labels=["a", "b", "c", "d", "e"], seed_values=[]
        )
        _apply_sim_listmodel(app, sc, "lst", m, 2)
        # slot 0 → abs_idx 2
        assert sc.widgets[0].text == "c"
        assert sc.widgets[0].value == 2
        # slot 1 → abs_idx 3
        assert sc.widgets[1].text == "d"
        assert sc.widgets[1].value == 3

    def test_no_scroll_widget_ok(self):
        """_apply_sim_listmodel should work fine without a scroll widget."""
        sc = _scene(
            [
                _w("lst.item0", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(count=1, active=0, offset=0, seed_labels=["X"], seed_values=[])
        _apply_sim_listmodel(app, sc, "lst", m, 1)
        assert sc.widgets[0].text == "X"

    def test_snapshot_saved(self):
        sc = _scene(
            [
                _w("lst.item0", text="orig", value=99, enabled=True, visible=True),
            ]
        )
        app = _app(sc)
        m = _SimListModel(count=1, active=0, offset=0, seed_labels=["New"], seed_values=[])
        _apply_sim_listmodel(app, sc, "lst", m, 1)
        snap = app._sim_runtime_snapshot.get("lst.item0")
        assert snap is not None
        assert snap.text == "orig"
        assert snap.value == 99

    def test_fallback_item_text(self):
        """Items beyond seed_labels get 'Item N' text."""
        sc = _scene(
            [
                _w("lst.item0", text="old"),
                _w("lst.item1", text="old"),
            ]
        )
        app = _app(sc)
        m = _SimListModel(count=5, active=3, offset=3, seed_labels=["a", "b"], seed_values=[])
        _apply_sim_listmodel(app, sc, "lst", m, 2)
        # slot 0 → abs_idx 3 → beyond seed, fallback "Item 4"
        assert sc.widgets[0].text == "Item 4"
        # slot 1 → abs_idx 4 → fallback "Item 5"
        assert sc.widgets[1].text == "Item 5"


# ---------------------------------------------------------------------------
# _sim_try_scroll_list
# ---------------------------------------------------------------------------


class TestSimTryScrollList:
    def _make_list_app(self, count: int, visible: int, scroll_text: str, focus_slot: int = 0):
        """Build an app with a list of visible item slots + scroll widget."""
        widgets = []
        for i in range(visible):
            widgets.append(_w(f"lst.item{i}", text=f"Item {i + 1}", y=i * 20))
        widgets.append(_w("lst.scroll", text=scroll_text))
        sc = _scene(widgets)
        app = _app(sc)
        app.focus_idx = focus_slot
        return app, sc

    def test_invalid_direction(self):
        app, sc = self._make_list_app(5, 3, "1/5")
        assert _sim_try_scroll_list(app, "left") is False

    def test_no_focus(self):
        app, sc = self._make_list_app(5, 3, "1/5")
        app.focus_idx = None
        assert _sim_try_scroll_list(app, "down") is False

    def test_focus_out_of_range(self):
        app, sc = self._make_list_app(5, 3, "1/5")
        app.focus_idx = 999
        assert _sim_try_scroll_list(app, "down") is False

    def test_focus_on_non_item_widget(self):
        """Focus on the scroll widget (not an item) → False."""
        app, sc = self._make_list_app(5, 3, "1/5")
        app.focus_idx = 3  # scroll widget index
        assert _sim_try_scroll_list(app, "down") is False

    def test_count_equals_visible_no_scroll(self):
        """No scrolling needed if count == visible."""
        app, sc = self._make_list_app(3, 3, "1/3", focus_slot=0)
        assert _sim_try_scroll_list(app, "down") is False

    def test_scroll_down_basic(self):
        app, sc = self._make_list_app(5, 2, "1/5", focus_slot=0)
        result = _sim_try_scroll_list(app, "down")
        assert result is True
        # After scroll down, active should have moved
        model = app._sim_listmodels.get("lst")
        assert model is not None
        assert model.active == 1

    def test_scroll_up_from_first_no_change(self):
        app, sc = self._make_list_app(5, 2, "1/5", focus_slot=0)
        result = _sim_try_scroll_list(app, "up")
        assert result is False

    def test_scroll_down_then_up(self):
        app, sc = self._make_list_app(5, 2, "1/5", focus_slot=0)
        # scroll down twice
        _sim_try_scroll_list(app, "down")
        # focus moves to slot for new active
        model = app._sim_listmodels["lst"]
        active_slot = model.active - model.offset
        app.focus_idx = _find_by_widget_id(sc, f"lst.item{active_slot}")
        _sim_try_scroll_list(app, "down")
        active_slot = model.active - model.offset
        app.focus_idx = _find_by_widget_id(sc, f"lst.item{active_slot}")

        assert model.active == 2
        # now scroll up
        result = _sim_try_scroll_list(app, "up")
        assert result is True
        assert model.active == 1

    def test_scroll_to_bottom(self):
        app, sc = self._make_list_app(4, 2, "1/4", focus_slot=0)
        model = None
        for _ in range(10):  # more than enough
            model = app._sim_listmodels.get("lst")
            if model and model.active == 3:
                break
            slot = 0
            if model:
                slot = min(model.active - model.offset, 1)
            app.focus_idx = _find_by_widget_id(sc, f"lst.item{max(0, slot)}")
            if not _sim_try_scroll_list(app, "down"):
                break
        assert model is not None
        assert model.active == 3

    def test_widget_without_widget_id(self):
        sc = _scene(
            [SimpleNamespace(text="", value=0, enabled=True, visible=True, type="button", x=0, y=0)]
        )
        app = _app(sc)
        app.focus_idx = 0
        assert _sim_try_scroll_list(app, "down") is False

    def test_focus_updates_after_scroll(self):
        """After scrolling, focus_idx should point to the correct item slot."""
        app, sc = self._make_list_app(5, 2, "1/5", focus_slot=0)
        _sim_try_scroll_list(app, "down")
        # set_focus was called; app.focus_idx should be updated
        # The new active_slot = model.active - model.offset
        model = app._sim_listmodels["lst"]
        expected_slot = model.active - model.offset
        expected_idx = _find_by_widget_id(sc, f"lst.item{expected_slot}")
        assert app.focus_idx == expected_idx
