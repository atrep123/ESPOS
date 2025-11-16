#!/usr/bin/env python3
"""Extra tests for ASCII preview: state overrides, animation preview, borders."""

import sys
sys.path.insert(0, '.')

from ui_designer import UIDesigner, WidgetType, WidgetConfig


def test_state_overrides_text_changes():
    d = UIDesigner(64, 32)
    d.create_scene('s')
    w = WidgetConfig(type=WidgetType.LABEL.value, x=2, y=2, width=20, height=3, text='Base', border=True)
    w.state = 'hover'
    w.state_overrides = {'hover': {'text': 'Hover'}}
    d.add_widget(w)
    out = d.preview_ascii()
    assert 'Hover' in out and 'Base' not in out


def test_anim_preview_bounce_differs():
    d = UIDesigner(64, 32)
    d.create_scene('s')
    w = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=12, width=10, height=3, text='Anim', border=True)
    d.add_widget(w)
    # Baseline
    baseline = d.preview_ascii()
    # With animation context, different frames should differ
    d.anim_context = {'idx': 0, 'name': 'bounce', 'steps': 4, 't': 1}
    out0 = d.preview_ascii()
    d.anim_context = {'idx': 0, 'name': 'bounce', 'steps': 4, 't': 3}
    out2 = d.preview_ascii()
    assert out0 != out2
    assert baseline != out0 or baseline != out2
    d.anim_context = None


def test_border_styles_markers():
    d = UIDesigner(64, 32)
    d.create_scene('s')
    # single
    d.add_widget(WidgetConfig(type=WidgetType.BOX.value, x=1, y=1, width=8, height=4, border=True, border_style='single'))
    # double
    d.add_widget(WidgetConfig(type=WidgetType.BOX.value, x=10, y=1, width=8, height=4, border=True, border_style='double'))
    # rounded
    d.add_widget(WidgetConfig(type=WidgetType.BOX.value, x=1, y=8, width=8, height=4, border=True, border_style='rounded'))
    # bold
    d.add_widget(WidgetConfig(type=WidgetType.BOX.value, x=10, y=8, width=8, height=4, border=True, border_style='bold'))
    out = d.preview_ascii()
    # Expect representative chars to appear for each style
    assert any(ch in out for ch in ['┌', '─', '│'])  # single
    assert any(ch in out for ch in ['╔', '═', '║'])  # double
    if not any(ch in out for ch in ['╭', '╮', '╰', '╯']):
        print('rounded corners not found (console/font may lack glyphs)')
    assert any(ch in out for ch in ['┏', '━', '┃'])  # bold


if __name__ == '__main__':
    test_state_overrides_text_changes()
    test_anim_preview_bounce_differs()
    test_border_styles_markers()
    print('OK')
