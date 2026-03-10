"""Tests for ui_models.py helper functions and WidgetConfig dataclass."""

from ui_models import (
    BorderStyle,
    Scene,
    WidgetConfig,
    WidgetType,
    _coerce_bool_flag,
    _coerce_choice,
    _coerce_int,
    _make_baseline,
    _normalize_int_list,
)

# ── _normalize_int_list ──

class TestNormalizeIntList:
    def test_ints(self):
        assert _normalize_int_list([1, 2, 3]) == [1, 2, 3]

    def test_strings(self):
        assert _normalize_int_list(["10", "20"]) == [10, 20]

    def test_mixed(self):
        assert _normalize_int_list([1, "two", 3, None, "4"]) == [1, 3, 4]

    def test_empty(self):
        assert _normalize_int_list([]) == []

    def test_none(self):
        assert _normalize_int_list(None) == []

    def test_floats_truncated(self):
        assert _normalize_int_list([1.9, 2.1]) == [1, 2]

    def test_all_bad(self):
        assert _normalize_int_list(["a", "b", None]) == []


# ── _coerce_bool_flag ──

class TestCoerceBoolFlag:
    def test_none_returns_default_true(self):
        assert _coerce_bool_flag(None, True) is True

    def test_none_returns_default_false(self):
        assert _coerce_bool_flag(None, False) is False

    def test_string_true(self):
        assert _coerce_bool_flag("true", False) is True

    def test_string_yes(self):
        assert _coerce_bool_flag("YES", False) is True

    def test_string_on(self):
        assert _coerce_bool_flag("on", False) is True

    def test_string_1(self):
        assert _coerce_bool_flag("1", False) is True

    def test_string_false(self):
        assert _coerce_bool_flag("false", True) is False

    def test_string_no(self):
        assert _coerce_bool_flag("no", True) is False

    def test_string_off(self):
        assert _coerce_bool_flag("OFF", True) is False

    def test_string_0(self):
        assert _coerce_bool_flag("0", True) is False

    def test_bool_passthrough(self):
        assert _coerce_bool_flag(True, False) is True
        assert _coerce_bool_flag(False, True) is False

    def test_int_truthy(self):
        assert _coerce_bool_flag(1, False) is True
        assert _coerce_bool_flag(0, True) is False

    def test_random_string_truthy(self):
        # A non-empty string not in the recognized set is truthy via bool()
        assert _coerce_bool_flag("maybe", False) is True


# ── _coerce_choice ──

class TestCoerceChoice:
    def test_valid_choice(self):
        assert _coerce_choice("a", ["a", "b", "c"], "b") == "a"

    def test_invalid_choice(self):
        assert _coerce_choice("x", ["a", "b", "c"], "b") == "b"

    def test_none_returns_default(self):
        assert _coerce_choice(None, ["a", "b"], "a") == "a"

    def test_int_coerced_to_string(self):
        assert _coerce_choice(1, ["1", "2"], "2") == "1"


# ── _coerce_int ──

class TestCoerceInt:
    def test_int(self):
        assert _coerce_int(5) == 5

    def test_none(self):
        assert _coerce_int(None) == 0

    def test_string_number(self):
        assert _coerce_int(10) == 10

    def test_bad_value(self):
        assert _coerce_int("abc") == 0  # type: ignore[arg-type]


# ── _make_baseline ──

class TestMakeBaseline:
    def test_basic(self):
        b = _make_baseline(10, 20, 100, 50, 800, 600)
        assert b["x"] == 10
        assert b["y"] == 20
        assert b["width"] == 100
        assert b["height"] == 50
        assert b["bw"] == 800
        assert b["bh"] == 600

    def test_none_dimensions(self):
        b = _make_baseline(0, 0, None, None, None, None)
        assert b["width"] == 0
        assert b["height"] == 0
        assert b["bw"] == 0
        assert b["bh"] == 0


# ── WidgetType enum ──

class TestWidgetType:
    def test_all_types(self):
        expected = {"label", "box", "button", "gauge", "progressbar",
                    "checkbox", "radiobutton", "slider", "textbox",
                    "panel", "icon", "chart"}
        values = {wt.value for wt in WidgetType}
        assert values == expected

    def test_label(self):
        assert WidgetType.LABEL.value == "label"


# ── BorderStyle enum ──

class TestBorderStyle:
    def test_all_styles(self):
        expected = {"none", "single", "double", "rounded", "bold", "dashed"}
        values = {bs.value for bs in BorderStyle}
        assert values == expected


# ── WidgetConfig ──

class TestWidgetConfig:
    def test_basic_creation(self):
        wc = WidgetConfig(type="label", x=10, y=20)
        assert wc.type == "label"
        assert wc.x == 10
        assert wc.y == 20

    def test_default_dimensions(self):
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc.width >= 1
        assert wc.height >= 1

    def test_color_bg_alias(self):
        wc = WidgetConfig(type="label", x=0, y=0, bg_color="red")
        assert wc.color_bg == "red"

    def test_text_color_alias(self):
        wc = WidgetConfig(type="label", x=0, y=0, text_color="green")
        assert wc.color_fg == "green"

    def test_color_alias(self):
        wc = WidgetConfig(type="label", x=0, y=0, color="blue")
        assert wc.color_fg == "blue"

    def test_int_color_alias(self):
        wc = WidgetConfig(type="label", x=0, y=0, bg_color=0xFF0000)
        assert wc.color_bg == "#ff0000"

    def test_bold_alias(self):
        wc = WidgetConfig(type="label", x=0, y=0, bold=True)
        assert wc.style == "bold"

    def test_text_overflow_default(self):
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc.text_overflow == "ellipsis"

    def test_text_overflow_invalid_falls_back(self):
        wc = WidgetConfig(type="label", x=0, y=0, text_overflow="bogus")
        assert wc.text_overflow == "ellipsis"

    def test_text_overflow_wrap(self):
        wc = WidgetConfig(type="label", x=0, y=0, text_overflow="wrap")
        assert wc.text_overflow == "wrap"

    def test_max_lines_none(self):
        wc = WidgetConfig(type="label", x=0, y=0, max_lines=None)
        assert wc.max_lines is None

    def test_max_lines_positive(self):
        wc = WidgetConfig(type="label", x=0, y=0, max_lines=3)
        assert wc.max_lines == 3

    def test_max_lines_zero_becomes_none(self):
        wc = WidgetConfig(type="label", x=0, y=0, max_lines=0)
        assert wc.max_lines is None

    def test_enum_type_normalized(self):
        wc = WidgetConfig(type=WidgetType.BUTTON, x=0, y=0)
        assert wc.type == "button"

    def test_width_property(self):
        wc = WidgetConfig(type="label", x=0, y=0, width=50, height=30)
        assert wc.width == 50
        assert wc.height == 30

    def test_negative_width_clamped(self):
        wc = WidgetConfig(type="label", x=0, y=0, width=-5)
        assert wc.width >= 1

    def test_locked_default(self):
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc.locked is False

    def test_state_overrides_default(self):
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc.state_overrides == {}

    def test_animations_default(self):
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc.animations == []

    def test_data_points_default(self):
        wc = WidgetConfig(type="chart", x=0, y=0)
        assert wc.data_points == []

    def test_text_overflow_empty_string_normalized(self):
        """Line 243: empty text_overflow → 'ellipsis'."""
        wc = WidgetConfig(type="label", x=0, y=0, text_overflow="")
        assert wc.text_overflow == "ellipsis"

    def test_max_lines_invalid_string_becomes_none(self):
        """Lines 257-258: non-numeric max_lines triggers except → None."""
        wc = WidgetConfig(type="label", x=0, y=0, max_lines="abc")
        assert wc.max_lines is None

    def test_non_enum_value_attr_type_normalized(self):
        """Lines 273-275: object with .value attribute (not Enum) is normalized."""
        class FakeType:
            value = "slider"
        wc = WidgetConfig(type=FakeType(), x=0, y=0)
        assert wc.type == "slider"

    def test_border_width_alias_sets_border(self):
        """Lines 308-310: border_width > 0 sets border=True."""
        wc = WidgetConfig(type="label", x=0, y=0, border_width=2)
        assert wc.border is True

    def test_border_width_zero_clears_border(self):
        """Lines 308-310: border_width=0 sets border=False."""
        wc = WidgetConfig(type="label", x=0, y=0, border_width=0)
        assert wc.border is False

    def test_default_width_label(self):
        """Lines 322-325: _default_width for label type."""
        wc = WidgetConfig(type="label", x=0, y=0, text="Hi")
        result = wc._default_width("label")
        assert result >= 1

    def test_default_width_button(self):
        """Lines 326-327: _default_width for button type."""
        wc = WidgetConfig(type="button", x=0, y=0, text="OK")
        result = wc._default_width("button")
        assert result >= 4

    def test_default_width_panel(self):
        """Lines 328-329: _default_width for panel type."""
        wc = WidgetConfig(type="panel", x=0, y=0)
        assert wc._default_width("panel") == 10

    def test_default_width_unknown(self):
        """Line 330: _default_width for unknown type."""
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc._default_width("custom") == 8

    def test_default_height_label_with_border(self):
        """Lines 333-334: _default_height for label with border."""
        wc = WidgetConfig(type="label", x=0, y=0, border=True)
        assert wc._default_height("label") == 3

    def test_default_height_label_without_border(self):
        """Line 334: _default_height for label without border."""
        wc = WidgetConfig(type="label", x=0, y=0, border=False)
        assert wc._default_height("label") == 1

    def test_default_height_button(self):
        """Lines 335-336: _default_height for button type."""
        wc = WidgetConfig(type="button", x=0, y=0)
        assert wc._default_height("button") == 3

    def test_default_height_panel(self):
        """Lines 337-338: _default_height for panel type."""
        wc = WidgetConfig(type="panel", x=0, y=0)
        assert wc._default_height("panel") == 6

    def test_default_height_unknown(self):
        """Line 339: _default_height for unknown type."""
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc._default_height("custom") == 3

    def test_to_color_str_none(self):
        """Line 279: _to_color_str with None returns None."""
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc._to_color_str(None) is None

    def test_to_color_str_int(self):
        """_to_color_str with int returns hex string."""
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc._to_color_str(0xFF0000) == "#ff0000"

    def test_to_color_str_string(self):
        """_to_color_str with string returns same string."""
        wc = WidgetConfig(type="label", x=0, y=0)
        assert wc._to_color_str("red") == "red"


# ── _coerce_bool_flag exception path ──

class TestCoerceBoolFlagException:
    def test_bool_raises_returns_default(self):
        """Lines 38-39: object whose __bool__ raises returns default."""
        class BadBool:
            def __bool__(self):
                raise ValueError("no bool")
        assert _coerce_bool_flag(BadBool(), True) is True
        assert _coerce_bool_flag(BadBool(), False) is False


# ── Scene backward-compat shim ──

class TestScene:
    def test_basic_creation(self):
        """Lines 391-401: Scene backward-compat shim."""
        s = Scene("main", 256, 128)
        assert s.name == "main"
        assert s.width == 256
        assert s.height == 128
        assert s.bg_color == "black"
        assert s.base_width == 256
        assert s.base_height == 128
        assert s.theme == "default"
        assert s.contrast_lock is True
        assert s.widgets == []

    def test_custom_bg_color(self):
        s = Scene("test", 128, 64, bg_color="white")
        assert s.bg_color == "white"

    def test_widgets_mutable(self):
        s = Scene("test", 128, 64)
        wc = WidgetConfig(type="label", x=0, y=0)
        s.widgets.append(wc)
        assert len(s.widgets) == 1
