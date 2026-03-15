"""Tests for cyberpunk_designer.selection_ops.propagation module.

Covers all 12 propagation functions: copy_style, paste_style,
propagate_border, propagate_style, clone_text, propagate_align,
propagate_colors, propagate_value, propagate_padding, propagate_margin,
propagate_appearance, propagate_text.
"""

from __future__ import annotations

from cyberpunk_designer.selection_ops import (
    clone_text,
    copy_style,
    paste_style,
    propagate_align,
    propagate_appearance,
    propagate_border,
    propagate_colors,
    propagate_margin,
    propagate_padding,
    propagate_style,
    propagate_text,
    propagate_value,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ===========================================================================
# copy_style / paste_style
# ===========================================================================


class TestCopyPasteStyle:
    def test_copy_and_paste(self, make_app):
        app = make_app()
        _add(
            app,
            style="bold",
            color_fg="#ff0000",
            color_bg="#00ff00",
            border=True,
            border_style="double",
            align="center",
            valign="top",
        )
        _add(app, style="default", color_fg="white", color_bg="black")
        _sel(app, 0)
        copy_style(app)
        _sel(app, 1)
        paste_style(app)
        w = _w(app, 1)
        assert w.style == "bold"
        assert w.color_fg == "#ff0000"
        assert w.color_bg == "#00ff00"
        assert w.border is True
        assert w.border_style == "double"
        assert w.align == "center"
        assert w.valign == "top"

    def test_copy_nothing_selected(self, make_app):
        app = make_app()
        _add(app)
        _sel(app)
        copy_style(app)  # no crash
        assert (
            not hasattr(app, "_style_clipboard")
            or app._style_clipboard is None
            or app._style_clipboard == {}
        )

    def test_paste_without_copy(self, make_app):
        app = make_app()
        _add(app, style="bold")
        _sel(app, 0)
        paste_style(app)  # no clipboard → no crash
        assert _w(app, 0).style == "bold"  # unchanged

    def test_paste_to_multiple(self, make_app):
        app = make_app()
        _add(app, style="bold", color_fg="red")
        _add(app, style="default")
        _add(app, style="default")
        _sel(app, 0)
        copy_style(app)
        _sel(app, 1, 2)
        paste_style(app)
        assert _w(app, 1).style == "bold"
        assert _w(app, 2).style == "bold"

    def test_paste_nothing_selected(self, make_app):
        app = make_app()
        _add(app, style="bold")
        _sel(app, 0)
        copy_style(app)
        _sel(app)  # empty selection
        paste_style(app)  # no crash


# ===========================================================================
# propagate_border
# ===========================================================================


class TestPropagateBorder:
    def test_copies_border_fields(self, make_app):
        app = make_app()
        _add(app, border=True, border_style="double")
        _add(app, border=False, border_style="single")
        _add(app, border=False, border_style="single")
        _sel(app, 0, 1, 2)
        propagate_border(app)
        assert _w(app, 1).border is True
        assert _w(app, 1).border_style == "double"
        assert _w(app, 2).border is True
        assert _w(app, 2).border_style == "double"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, border=True, border_style="double")
        _sel(app, 0)
        propagate_border(app)  # only 1 selected → noop

    def test_preserves_first_widget(self, make_app):
        app = make_app()
        _add(app, border=True, border_style="rounded")
        _add(app, border=False)
        _sel(app, 0, 1)
        propagate_border(app)
        assert _w(app, 0).border is True
        assert _w(app, 0).border_style == "rounded"


# ===========================================================================
# propagate_style
# ===========================================================================


class TestPropagateStyle:
    def test_copies_style(self, make_app):
        app = make_app()
        _add(app, style="bold")
        _add(app, style="default")
        _sel(app, 0, 1)
        propagate_style(app)
        assert _w(app, 1).style == "bold"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, style="bold")
        _sel(app, 0)
        propagate_style(app)

    def test_multiple_targets(self, make_app):
        app = make_app()
        _add(app, style="italic")
        _add(app, style="default")
        _add(app, style="default")
        _add(app, style="bold")
        _sel(app, 0, 1, 2, 3)
        propagate_style(app)
        for i in range(1, 4):
            assert _w(app, i).style == "italic"


# ===========================================================================
# clone_text
# ===========================================================================


class TestCloneText:
    def test_copies_text(self, make_app):
        app = make_app()
        _add(app, text="Source")
        _add(app, text="Other")
        _sel(app, 0, 1)
        clone_text(app)
        assert _w(app, 1).text == "Source"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, text="Source")
        _sel(app, 0)
        clone_text(app)

    def test_empty_text(self, make_app):
        app = make_app()
        _add(app, text="")
        _add(app, text="Hello")
        _sel(app, 0, 1)
        clone_text(app)
        assert _w(app, 1).text == ""


# ===========================================================================
# propagate_align
# ===========================================================================


class TestPropagateAlign:
    def test_copies_align_and_valign(self, make_app):
        app = make_app()
        _add(app, align="center", valign="top")
        _add(app, align="left", valign="middle")
        _sel(app, 0, 1)
        propagate_align(app)
        assert _w(app, 1).align == "center"
        assert _w(app, 1).valign == "top"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, align="center")
        _sel(app, 0)
        propagate_align(app)

    def test_multiple_targets(self, make_app):
        app = make_app()
        _add(app, align="right", valign="bottom")
        _add(app, align="left", valign="top")
        _add(app, align="center", valign="middle")
        _sel(app, 0, 1, 2)
        propagate_align(app)
        for i in [1, 2]:
            assert _w(app, i).align == "right"
            assert _w(app, i).valign == "bottom"


# ===========================================================================
# propagate_colors
# ===========================================================================


class TestPropagateColors:
    def test_copies_fg_and_bg(self, make_app):
        app = make_app()
        _add(app, color_fg="#aabbcc", color_bg="#112233")
        _add(app, color_fg="white", color_bg="black")
        _sel(app, 0, 1)
        propagate_colors(app)
        assert _w(app, 1).color_fg == "#aabbcc"
        assert _w(app, 1).color_bg == "#112233"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, color_fg="red")
        _sel(app, 0)
        propagate_colors(app)


# ===========================================================================
# propagate_value
# ===========================================================================


class TestPropagateValue:
    def test_copies_value_and_range(self, make_app):
        app = make_app()
        _add(app, type="slider", value=42, min_value=10, max_value=200)
        _add(app, type="slider", value=0, min_value=0, max_value=100)
        _sel(app, 0, 1)
        propagate_value(app)
        assert _w(app, 1).value == 42
        assert _w(app, 1).min_value == 10
        assert _w(app, 1).max_value == 200

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, type="slider", value=42)
        _sel(app, 0)
        propagate_value(app)


# ===========================================================================
# propagate_padding
# ===========================================================================


class TestPropagatePadding:
    def test_copies_padding(self, make_app):
        app = make_app()
        _add(app, padding_x=5, padding_y=3)
        _add(app, padding_x=1, padding_y=0)
        _sel(app, 0, 1)
        propagate_padding(app)
        assert _w(app, 1).padding_x == 5
        assert _w(app, 1).padding_y == 3

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, padding_x=5)
        _sel(app, 0)
        propagate_padding(app)


# ===========================================================================
# propagate_margin
# ===========================================================================


class TestPropagateMargin:
    def test_copies_margin(self, make_app):
        app = make_app()
        _add(app, margin_x=4, margin_y=6)
        _add(app, margin_x=0, margin_y=0)
        _sel(app, 0, 1)
        propagate_margin(app)
        assert _w(app, 1).margin_x == 4
        assert _w(app, 1).margin_y == 6

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, margin_x=4)
        _sel(app, 0)
        propagate_margin(app)


# ===========================================================================
# propagate_appearance
# ===========================================================================


class TestPropagateAppearance:
    def test_copies_all_visual_props(self, make_app):
        app = make_app()
        _add(
            app,
            style="bold",
            color_fg="red",
            color_bg="blue",
            border=True,
            border_style="double",
            align="center",
            valign="top",
            padding_x=4,
            padding_y=2,
            margin_x=3,
            margin_y=1,
        )
        _add(app, style="default", color_fg="white", color_bg="black")
        _sel(app, 0, 1)
        propagate_appearance(app)
        w = _w(app, 1)
        assert w.style == "bold"
        assert w.color_fg == "red"
        assert w.color_bg == "blue"
        assert w.border is True
        assert w.border_style == "double"
        assert w.align == "center"
        assert w.valign == "top"
        assert w.padding_x == 4
        assert w.padding_y == 2
        assert w.margin_x == 3
        assert w.margin_y == 1

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, style="bold")
        _sel(app, 0)
        propagate_appearance(app)

    def test_multiple_targets(self, make_app):
        app = make_app()
        _add(app, style="bold", color_fg="red")
        _add(app, style="default")
        _add(app, style="default")
        _sel(app, 0, 1, 2)
        propagate_appearance(app)
        assert _w(app, 1).style == "bold"
        assert _w(app, 2).style == "bold"


# ===========================================================================
# propagate_text
# ===========================================================================


class TestPropagateText:
    def test_copies_text(self, make_app):
        app = make_app()
        _add(app, text="Hello World")
        _add(app, text="Other")
        _sel(app, 0, 1)
        propagate_text(app)
        assert _w(app, 1).text == "Hello World"

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, text="Hello")
        _sel(app, 0)
        propagate_text(app)

    def test_empty_text(self, make_app):
        app = make_app()
        _add(app, text="")
        _add(app, text="World")
        _sel(app, 0, 1)
        propagate_text(app)
        assert _w(app, 1).text == ""

    def test_multiple_targets(self, make_app):
        app = make_app()
        _add(app, text="ABC")
        _add(app, text="X")
        _add(app, text="Y")
        _add(app, text="Z")
        _sel(app, 0, 1, 2, 3)
        propagate_text(app)
        for i in [1, 2, 3]:
            assert _w(app, i).text == "ABC"
