#!/usr/bin/env python3
"""Test help overlay feature in simulator"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_run import render_frame, UIState, rgb565


def test_help_overlay_render():
    """Test that help overlay renders without errors"""
    state = UIState()
    state.bg = rgb565(0, 0, 0)
    
    # Test with help overlay enabled
    lines = render_frame(
        state=state,
        frame_num=1,
        fps=60.0,
        width=100,
        height=24,
        use_unicode=True,
        use_color=True,
        compute_ms=1.0,
        sleep_ms=15.0,
        util=0.05,
        hud=False,
        help_overlay=True,
        input_src='kbd'
    )
    
    assert len(lines) > 0, "Should render lines"
    
    # Check that help overlay is appended (should find help box borders)
    has_help_border = any('─' in line or '-' in line for line in lines[-5:])
    assert has_help_border, "Should have help overlay border in last few lines"
    
    # Test with help overlay disabled
    lines_no_help = render_frame(
        state=state,
        frame_num=1,
        fps=60.0,
        width=100,
        height=24,
        use_unicode=True,
        use_color=True,
        compute_ms=1.0,
        sleep_ms=15.0,
        util=0.05,
        hud=False,
        help_overlay=False,
        input_src='kbd'
    )
    
    assert len(lines_no_help) < len(lines), "Help overlay should add lines"
    
    print("✅ Help overlay renders correctly")
    print(f"   Lines with overlay: {len(lines)}")
    print(f"   Lines without overlay: {len(lines_no_help)}")
    print(f"   Added {len(lines) - len(lines_no_help)} lines")
    
    # Print last few lines to verify content
    print("\nLast 5 lines with help overlay:")
    for line in lines[-5:]:
        # Strip ANSI codes for display
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
        print(f"   {clean[:80]}")


if __name__ == '__main__':
    test_help_overlay_render()
    print("\n✅ All help overlay tests passed!")
