#!/usr/bin/env python3
"""Test HUD feature in simulator"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_run import render_frame, UIState, rgb565


def test_hud_render():
    """Test that HUD renders with FPS and timing metrics"""
    state = UIState()
    state.bg = rgb565(0, 0, 0)
    
    # Test with HUD enabled
    lines = render_frame(
        state=state,
        frame_num=42,
        fps=119.5,
        width=100,
        height=24,
        use_unicode=True,
        use_color=True,
        compute_ms=2.3,
        sleep_ms=5.9,
        util=0.28,
        hud=True,
        help_overlay=False,
        input_src='gamepad'
    )
    
    assert len(lines) > 0, "Should render lines"
    
    # Check that HUD line contains expected metrics
    import re
    hud_line = None
    for line in lines[:5]:  # HUD should be near top
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        if 'HUD' in clean and 'FPS' in clean:
            hud_line = clean
            break
    
    assert hud_line is not None, "Should find HUD line near top"
    assert '119.5' in hud_line or '119' in hud_line, "Should show FPS"
    assert '2.3' in hud_line or '2.' in hud_line, "Should show compute_ms"
    assert '5.9' in hud_line or '5.' in hud_line, "Should show sleep_ms"
    assert '28' in hud_line or '0.28' in hud_line, "Should show util (28%)"
    assert 'gamepad' in hud_line, "Should show input source"
    
    print("✅ HUD renders correctly")
    print(f"   Total lines: {len(lines)}")
    print(f"   HUD line: {hud_line[:100]}")
    
    # Test with HUD disabled
    lines_no_hud = render_frame(
        state=state,
        frame_num=42,
        fps=119.5,
        width=100,
        height=24,
        use_unicode=True,
        use_color=True,
        compute_ms=2.3,
        sleep_ms=5.9,
        util=0.28,
        hud=False,
        help_overlay=False,
        input_src='kbd'
    )
    
    assert len(lines_no_hud) < len(lines), "HUD should add lines"
    assert len(lines) - len(lines_no_hud) == 1, "HUD should add exactly 1 line"
    
    # Verify no HUD in disabled version
    hud_found = False
    for line in lines_no_hud[:5]:
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        if 'HUD' in clean and 'FPS' in clean:
            hud_found = True
    
    assert not hud_found, "Should not find HUD when disabled"
    
    print("✅ HUD toggle works correctly")
    print(f"   Lines with HUD: {len(lines)}")
    print(f"   Lines without HUD: {len(lines_no_hud)}")


if __name__ == '__main__':
    test_hud_render()
    print("\n✅ All HUD tests passed!")
