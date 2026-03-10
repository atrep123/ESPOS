"""Tests for UIDesigner internal pure-logic methods: diff, snap, responsive."""

from __future__ import annotations

from ui_designer import UIDesigner
from ui_models import WidgetConfig, _empty_constraints


def _designer(width: int = 256, height: int = 128) -> UIDesigner:
    d = UIDesigner(width=width, height=height)
    d.create_scene("main")
    return d


def _widget(
    wtype: str = "label", x: int = 0, y: int = 0, w: int = 40, h: int = 14, **kw
) -> WidgetConfig:
    return WidgetConfig(type=wtype, x=x, y=y, width=w, height=h, **kw)


# ===========================================================================
# _diff_states
# ===========================================================================


class TestDiffStates:
    def test_identical_states(self):
        d = _designer()
        w = _widget()
        d.scenes["main"].widgets.append(w)
        state = d._current_scene_state()
        diff = d._diff_states(state, state)
        assert diff["widgets"]["changed"] == []
        assert diff["widgets"]["added"] == []
        assert diff["widgets"]["removed"] == []

    def test_size_change_recorded(self):
        d = _designer()
        a = {"name": "main", "width": 256, "height": 128, "widgets": []}
        b = {"name": "main", "width": 320, "height": 240, "widgets": []}
        diff = d._diff_states(a, b)
        assert diff["size"]["a"] == (256, 128)
        assert diff["size"]["b"] == (320, 240)

    def test_widget_property_change_detected(self):
        d = _designer()
        wa = [{"type": "label", "x": 0, "y": 0, "width": 40, "height": 14, "text": "hello"}]
        wb = [{"type": "label", "x": 10, "y": 0, "width": 40, "height": 14, "text": "hello"}]
        a = {"name": "main", "width": 256, "height": 128, "widgets": wa}
        b = {"name": "main", "width": 256, "height": 128, "widgets": wb}
        diff = d._diff_states(a, b)
        assert len(diff["widgets"]["changed"]) == 1
        assert "x" in diff["widgets"]["changed"][0]["changes"]

    def test_widget_added(self):
        d = _designer()
        wa = [{"type": "label"}]
        wb = [{"type": "label"}, {"type": "button"}]
        a = {"name": "main", "width": 256, "height": 128, "widgets": wa}
        b = {"name": "main", "width": 256, "height": 128, "widgets": wb}
        diff = d._diff_states(a, b)
        assert diff["widgets"]["added"] == [1]

    def test_widget_removed(self):
        d = _designer()
        wa = [{"type": "label"}, {"type": "button"}, {"type": "box"}]
        wb = [{"type": "label"}]
        a = {"name": "main", "width": 256, "height": 128, "widgets": wa}
        b = {"name": "main", "width": 256, "height": 128, "widgets": wb}
        diff = d._diff_states(a, b)
        assert diff["widgets"]["removed"] == [1, 2]


# ===========================================================================
# _widget_diff_entry / _widget_diff_keys
# ===========================================================================


class TestWidgetDiffEntry:
    def test_no_changes(self):
        d = _designer()
        w = {"type": "label", "x": 0}
        assert d._widget_diff_entry(w, w, ["type", "x"]) == {}

    def test_detects_change(self):
        d = _designer()
        wa = {"type": "label", "x": 0}
        wb = {"type": "label", "x": 5}
        result = d._widget_diff_entry(wa, wb, ["type", "x"])
        assert "x" in result
        assert result["x"]["a"] == 0
        assert result["x"]["b"] == 5
        assert "type" not in result

    def test_keys_list_non_empty(self):
        d = _designer()
        keys = d._widget_diff_keys()
        assert len(keys) >= 15
        assert "type" in keys
        assert "x" in keys
        assert "visible" in keys


# ===========================================================================
# _collect_added_removed
# ===========================================================================


class TestCollectAddedRemoved:
    def test_no_change(self):
        d = _designer()
        diff = {"widgets": {"added": [], "removed": []}}
        d._collect_added_removed(diff, [1, 2, 3], [4, 5, 6], 3)
        assert diff["widgets"]["added"] == []
        assert diff["widgets"]["removed"] == []

    def test_added(self):
        d = _designer()
        diff = {"widgets": {"added": [], "removed": []}}
        d._collect_added_removed(diff, [1], [1, 2, 3], 1)
        assert diff["widgets"]["added"] == [1, 2]

    def test_removed(self):
        d = _designer()
        diff = {"widgets": {"added": [], "removed": []}}
        d._collect_added_removed(diff, [1, 2, 3], [1], 1)
        assert diff["widgets"]["removed"] == [1, 2]


# ===========================================================================
# _get_scene
# ===========================================================================


class TestGetScene:
    def test_by_name(self):
        d = _designer()
        sc = d._get_scene("main")
        assert sc is not None
        assert sc.name == "main"

    def test_none_returns_current(self):
        d = _designer()
        sc = d._get_scene(None)
        assert sc is not None
        assert sc.name == "main"

    def test_nonexistent_returns_none(self):
        d = _designer()
        assert d._get_scene("does_not_exist") is None


# ===========================================================================
# _coerce_groups
# ===========================================================================


class TestCoerceGroups:
    def test_valid_groups(self):
        d = _designer()
        d.scenes["main"].widgets = [_widget(), _widget(), _widget()]
        result = d._coerce_groups({"grp1": [0, 1, 2]})
        assert result == {"grp1": [0, 1, 2]}

    def test_non_dict_returns_empty(self):
        d = _designer()
        assert d._coerce_groups("not a dict") == {}
        assert d._coerce_groups(42) == {}
        assert d._coerce_groups(None) == {}

    def test_out_of_range_indices_filtered(self):
        d = _designer()
        d.scenes["main"].widgets = [_widget(), _widget()]
        result = d._coerce_groups({"g": [0, 1, 99, -1]})
        assert result == {"g": [0, 1]}

    def test_duplicate_indices_deduped(self):
        d = _designer()
        d.scenes["main"].widgets = [_widget(), _widget()]
        result = d._coerce_groups({"g": [0, 0, 1, 1]})
        assert result == {"g": [0, 1]}

    def test_empty_group_removed(self):
        d = _designer()
        d.scenes["main"].widgets = [_widget()]
        result = d._coerce_groups({"g": [99]})
        assert result == {}

    def test_non_list_members_skipped(self):
        d = _designer()
        d.scenes["main"].widgets = [_widget()]
        result = d._coerce_groups({"g": "not a list", "h": [0]})
        assert "g" not in result
        assert result == {"h": [0]}

    def test_no_current_scene(self):
        d = UIDesigner()
        d.current_scene = None
        assert d._coerce_groups({"g": [0]}) == {}


# ===========================================================================
# _update_snap_tolerance
# ===========================================================================


class TestUpdateSnapTolerance:
    def test_default(self):
        d = _designer()
        assert 1 <= d.snap_tolerance <= 3

    def test_small_grid(self):
        d = _designer()
        d.grid_size = 2
        d._update_snap_tolerance()
        assert d.snap_tolerance == 1

    def test_large_grid(self):
        d = _designer()
        d.grid_size = 16
        d._update_snap_tolerance()
        assert d.snap_tolerance == 3

    def test_zero_grid(self):
        d = _designer()
        d.grid_size = 0
        d._update_snap_tolerance()
        assert d.snap_tolerance >= 1


# ===========================================================================
# _axis_candidates_x / _axis_candidates_y
# ===========================================================================


class TestAxisCandidates:
    def _bounds(self, x=0, y=0, w=40, h=14):
        return {
            "left": x,
            "right": x + w,
            "top": y,
            "bottom": y + h,
            "cx": x + w // 2,
            "cy": y + h // 2,
        }

    def test_x_edges_only(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        s = self._bounds(0, 0, 40, 14)
        o = self._bounds(50, 0, 40, 14)
        cands = d._axis_candidates_x(s, o)
        assert len(cands) == 2  # left-to-left, right-to-right

    def test_x_edges_and_centers(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = True
        s = self._bounds()
        o = self._bounds(50, 0, 40, 14)
        cands = d._axis_candidates_x(s, o)
        assert len(cands) == 3  # left, right, center

    def test_x_centers_only(self):
        d = _designer()
        d.snap_edges = False
        d.snap_centers = True
        s = self._bounds()
        o = self._bounds(50, 0, 40, 14)
        cands = d._axis_candidates_x(s, o)
        assert len(cands) == 1

    def test_x_no_snap(self):
        d = _designer()
        d.snap_edges = False
        d.snap_centers = False
        s = self._bounds()
        o = self._bounds(50, 0, 40, 14)
        cands = d._axis_candidates_x(s, o)
        assert len(cands) == 0

    def test_y_edges_only(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        s = self._bounds()
        o = self._bounds(0, 50, 40, 14)
        cands = d._axis_candidates_y(s, o)
        assert len(cands) == 2

    def test_y_edges_and_centers(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = True
        s = self._bounds()
        o = self._bounds(0, 50, 40, 14)
        cands = d._axis_candidates_y(s, o)
        assert len(cands) == 3

    def test_axis_dispatch_x(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        s = self._bounds()
        o = self._bounds(50, 0, 40, 14)
        assert len(d._axis_candidates(s, o, "x")) == 2

    def test_axis_dispatch_y(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        s = self._bounds()
        o = self._bounds(0, 50, 40, 14)
        assert len(d._axis_candidates(s, o, "y")) == 2


# ===========================================================================
# _best_for_axis
# ===========================================================================


class TestBestForAxis:
    def _bounds(self, x=0, y=0, w=40, h=14):
        return {
            "left": x,
            "right": x + w,
            "top": y,
            "bottom": y + h,
            "cx": x + w // 2,
            "cy": y + h // 2,
        }

    def test_within_tolerance_matches(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        d.snap_tolerance = 5
        s = self._bounds(0, 0, 40, 14)
        o = self._bounds(3, 0, 40, 14)  # delta = 3 (within tolerance 5)
        delta, line = d._best_for_axis(s, o, None, None, "x")
        assert delta is not None
        assert abs(delta) <= 5

    def test_outside_tolerance_no_match(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = False
        d.snap_tolerance = 1
        s = self._bounds(0, 0, 40, 14)
        o = self._bounds(100, 0, 40, 14)  # delta = 100 (way outside)
        delta, line = d._best_for_axis(s, o, None, None, "x")
        assert delta is None

    def test_closer_candidate_wins(self):
        d = _designer()
        d.snap_edges = True
        d.snap_centers = True
        d.snap_tolerance = 10
        s = self._bounds(0, 0, 40, 14)
        # First result with delta 5
        delta1, line1 = d._best_for_axis(s, self._bounds(5, 0, 40, 14), None, None, "x")
        # Second result with delta 2
        delta2, line2 = d._best_for_axis(s, self._bounds(2, 0, 40, 14), delta1, line1, "x")
        assert abs(delta2) <= abs(delta1)


# ===========================================================================
# _find_best_snaps
# ===========================================================================


class TestFindBestSnaps:
    def test_no_other_widgets(self):
        d = _designer()
        w = _widget(x=10, y=10)
        d.scenes["main"].widgets = [w]
        bounds = d._widget_bounds(w, 10, 10)
        dx, dy, vline, hline = d._find_best_snaps(w, d.scenes["main"], bounds)
        assert dx is None
        assert dy is None

    def test_snaps_to_nearby_widget(self):
        d = _designer()
        d.snap_edges = True
        d.snap_tolerance = 5
        w1 = _widget(x=0, y=0, w=40, h=14)
        w2 = _widget(x=2, y=0, w=40, h=14)  # left edge offset by 2
        d.scenes["main"].widgets = [w1, w2]
        bounds = d._widget_bounds(w2, 2, 0)
        dx, dy, vline, hline = d._find_best_snaps(w2, d.scenes["main"], bounds)
        # Should find snap to w1's left edge (delta -2)
        assert dx is not None
        assert abs(dx) <= 5

    def test_skips_self(self):
        d = _designer()
        d.snap_tolerance = 100
        w = _widget(x=0, y=0)
        d.scenes["main"].widgets = [w]
        bounds = d._widget_bounds(w, 0, 0)
        dx, dy, _, _ = d._find_best_snaps(w, d.scenes["main"], bounds)
        assert dx is None


# ===========================================================================
# _align_axis
# ===========================================================================


class TestAlignAxis:
    def test_left(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "left", False)
        assert pos == 10
        assert scale is False

    def test_top(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "top", False)
        assert pos == 10

    def test_right(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "right", False)
        assert pos == 60  # 10 + 50

    def test_bottom(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "bottom", False)
        assert pos == 60

    def test_center(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "center", False)
        assert pos == 35  # 10 + 50/2

    def test_middle(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "middle", False)
        assert pos == 35

    def test_stretch(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "stretch", False)
        assert pos == 10
        assert scale is True

    def test_unknown_anchor(self):
        d = _designer()
        pos, scale = d._align_axis(10, 50, "unknown", False)
        assert pos == 10
        assert scale is False


# ===========================================================================
# _responsive_size
# ===========================================================================


class TestResponsiveSize:
    def test_no_scaling(self):
        d = _designer()
        b = {"width": 40, "height": 14}
        w, h = d._responsive_size(b, False, False, 2.0, 2.0)
        assert w == 40
        assert h == 14

    def test_scale_x(self):
        d = _designer()
        b = {"width": 40, "height": 14}
        w, h = d._responsive_size(b, True, False, 2.0, 2.0)
        assert w == 80
        assert h == 14

    def test_scale_y(self):
        d = _designer()
        b = {"width": 40, "height": 14}
        w, h = d._responsive_size(b, False, True, 2.0, 3.0)
        assert w == 40
        assert h == 42

    def test_scale_both(self):
        d = _designer()
        b = {"width": 40, "height": 14}
        w, h = d._responsive_size(b, True, True, 2.0, 3.0)
        assert w == 80
        assert h == 42


# ===========================================================================
# _clamp_responsive
# ===========================================================================


class TestClampResponsive:
    def test_within_bounds(self):
        d = _designer()
        sc = d.scenes["main"]
        x, y, w, h = d._clamp_responsive(sc, 10, 10, 40, 14)
        assert (x, y, w, h) == (10, 10, 40, 14)

    def test_negative_clamped(self):
        d = _designer()
        sc = d.scenes["main"]
        x, y, w, h = d._clamp_responsive(sc, -5, -10, 40, 14)
        assert x == 0
        assert y == 0

    def test_exceeds_scene_clamped(self):
        d = _designer()
        sc = d.scenes["main"]  # 256x128
        x, y, w, h = d._clamp_responsive(sc, 300, 200, 400, 300)
        assert x == 255
        assert y == 127
        assert w == 256
        assert h == 128

    def test_min_dimensions(self):
        d = _designer()
        sc = d.scenes["main"]
        x, y, w, h = d._clamp_responsive(sc, 0, 0, 0, 0)
        assert w >= 1
        assert h >= 1


# ===========================================================================
# _responsive_position
# ===========================================================================


class TestResponsivePosition:
    def test_left_top(self):
        d = _designer()
        c = {"ax": "left", "ay": "top", "sx": False, "sy": False}
        b = {"x": 10, "y": 20, "width": 40, "height": 14}
        nx, ny, sx, sy = d._responsive_position(c, b, 100, 50)
        assert nx == 10
        assert ny == 20
        assert sx is False
        assert sy is False

    def test_right_bottom(self):
        d = _designer()
        c = {"ax": "right", "ay": "bottom", "sx": False, "sy": False}
        b = {"x": 10, "y": 20, "width": 40, "height": 14}
        nx, ny, sx, sy = d._responsive_position(c, b, 100, 50)
        assert nx == 110
        assert ny == 70

    def test_center_center(self):
        d = _designer()
        c = {"ax": "center", "ay": "center", "sx": False, "sy": False}
        b = {"x": 10, "y": 20, "width": 40, "height": 14}
        nx, ny, sx, sy = d._responsive_position(c, b, 100, 50)
        assert nx == 60  # 10 + 100/2
        assert ny == 45  # 20 + 50/2


# ===========================================================================
# _current_scene_state
# ===========================================================================


class TestCurrentSceneState:
    def test_returns_dict(self):
        d = _designer()
        d.scenes["main"].widgets.append(_widget())
        state = d._current_scene_state()
        assert state is not None
        assert state["name"] == "main"
        assert state["width"] == 256
        assert state["height"] == 128
        assert len(state["widgets"]) == 1

    def test_no_scene_returns_none(self):
        d = UIDesigner()
        d.current_scene = None
        assert d._current_scene_state() is None

    def test_missing_scene_returns_none(self):
        d = UIDesigner()
        d.current_scene = "nonexistent"
        assert d._current_scene_state() is None


# ===========================================================================
# _set_default_constraints
# ===========================================================================


class TestSetDefaultConstraints:
    def test_sets_all_defaults(self):
        d = _designer()
        w = _widget()
        w.constraints = _empty_constraints()
        d._set_default_constraints(w)
        assert w.constraints["ax"] == "left"
        assert w.constraints["ay"] == "top"
        assert w.constraints["sx"] is False
        assert w.constraints["sy"] is False
        assert w.constraints["mx"] == 0
        assert w.constraints["my"] == 0
        assert w.constraints["mr"] == 0
        assert w.constraints["mb"] == 0

    def test_does_not_overwrite_existing(self):
        d = _designer()
        w = _widget()
        w.constraints = _empty_constraints()
        w.constraints["ax"] = "right"
        w.constraints["sx"] = True
        d._set_default_constraints(w)
        assert w.constraints["ax"] == "right"  # preserved
        assert w.constraints["sx"] is True  # preserved
        assert w.constraints["ay"] == "top"  # filled in


# ===========================================================================
# _resolve_scene
# ===========================================================================


class TestResolveScene:
    def test_by_name(self):
        d = _designer()
        sc = d._resolve_scene("main")
        assert sc is not None
        assert sc.name == "main"

    def test_none_uses_current(self):
        d = _designer()
        assert d._resolve_scene(None) is not None

    def test_empty_scene_name(self):
        d = UIDesigner()
        d.current_scene = ""
        assert d._resolve_scene(None) is None


# ===========================================================================
# _responsive_base_dims
# ===========================================================================


class TestResponsiveBaseDims:
    def test_uses_base_if_set(self):
        d = _designer()
        sc = d.scenes["main"]
        sc.base_width = 128
        sc.base_height = 64
        assert d._responsive_base_dims(sc) == (128, 64)

    def test_falls_back_to_actual(self):
        d = _designer()
        sc = d.scenes["main"]
        sc.base_width = 0
        sc.base_height = 0
        assert d._responsive_base_dims(sc) == (256, 128)
