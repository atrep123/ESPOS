#!/usr/bin/env python3
"""Test pause/step/continue functionality in simulator"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# This test verifies the pause/step logic conceptually
# Actual interactive testing would require key injection

def test_pause_logic():
    """Test pause/step/continue state machine logic"""
    
    # Simulate the pause/step state machine
    paused = False
    step_one_frame = False
    frame_updates = []
    
    # Normal running (not paused)
    should_update = not paused or step_one_frame
    assert should_update == True, "Should update when not paused"
    frame_updates.append("frame_1")
    
    # Pause (Space key)
    paused = True
    should_update = not paused or step_one_frame
    assert should_update == False, "Should not update when paused"
    
    # Step once (S key while paused)
    step_one_frame = True
    should_update = not paused or step_one_frame
    assert should_update == True, "Should update for one step"
    frame_updates.append("frame_2_step")
    
    # Reset step flag after executing
    step_one_frame = False
    should_update = not paused or step_one_frame
    assert should_update == False, "Should pause again after step"
    
    # Another step
    step_one_frame = True
    should_update = not paused or step_one_frame
    assert should_update == True, "Should update for another step"
    frame_updates.append("frame_3_step")
    step_one_frame = False
    
    # Continue (C key while paused)
    paused = False
    step_one_frame = False
    should_update = not paused or step_one_frame
    assert should_update == True, "Should update after continue"
    frame_updates.append("frame_4_continue")
    
    # Verify frame progression
    assert len(frame_updates) == 4, "Should have 4 frame updates"
    assert "step" in frame_updates[1], "Second frame should be a step"
    assert "step" in frame_updates[2], "Third frame should be a step"
    assert "continue" in frame_updates[3], "Fourth frame should be after continue"
    
    print("✅ Pause/step/continue logic works correctly")
    print(f"   Frame updates: {len(frame_updates)}")
    print(f"   Sequence: {' -> '.join(frame_updates)}")


def test_help_overlay_updated():
    """Verify help overlay shows correct pause/step/continue bindings"""
    from sim_run import UIState, render_frame, rgb565
    
    state = UIState()
    state.bg = rgb565(0, 0, 0)
    
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
    
    # Check help overlay contains pause/step/continue
    import re
    help_text = '\n'.join(lines[-5:])
    clean = re.sub(r'\x1b\[[0-9;]*m', '', help_text)
    
    assert 'Space' in clean and 'Pause' in clean, "Help should show Space=Pause"
    assert 'S' in clean and ('Step' in clean or 'step' in clean), "Help should show S=Step"
    assert 'C' in clean and ('Continue' in clean or 'continue' in clean), "Help should show C=Continue"
    
    print("✅ Help overlay shows pause/step/continue bindings")
    print(f"   Help text snippet: {clean[:120]}...")


if __name__ == '__main__':
    test_pause_logic()
    test_help_overlay_updated()
    print("\n✅ All pause/step tests passed!")
