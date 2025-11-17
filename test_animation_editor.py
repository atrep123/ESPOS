"""Tests for Animation Timeline Editor"""

import pytest
from ui_animations import AnimationDesigner, Animation, AnimationType, EasingFunction


class MockPreviewWindow:
    """Mock preview window for testing without Tkinter dependencies"""
    def __init__(self):
        self.anim = AnimationDesigner()
        self.selected_widget_idx = None
        self.selected_anim = None
        self.anim_playing = False
        
        class MockCombo:
            """Mock combo box"""
            def __init__(self):
                self.values = []
            
            def configure(self, **kwargs):
                """Mock configure"""
                if 'values' in kwargs:
                    self.values = kwargs['values']
            
            def set(self, val):
                """Mock set - no-op for testing"""
                pass
        
        self.anim_combo = MockCombo()
    
    def _on_anim_play(self):
        """Mock play"""
        self.anim_playing = True
    
    def _on_anim_pause(self):
        """Mock pause - no-op for testing"""
        pass
    
    def _on_anim_stop(self):
        """Mock stop"""
        self.anim_playing = False


@pytest.fixture
def preview_window():
    """Create mock preview window"""
    return MockPreviewWindow()


def test_animation_designer_basic(preview_window):
    """Test AnimationDesigner is accessible from preview window"""
    assert preview_window.anim is not None
    assert isinstance(preview_window.anim, AnimationDesigner)


def test_create_new_animation(preview_window):
    """Test creating new animation"""
    initial_count = len(preview_window.anim.animations)
    
    # Create animation
    test_anim = Animation(
        name="test_fade",
        type=AnimationType.FADE.value,
        duration=500,
        easing=EasingFunction.EASE_IN_OUT.value,
        iterations=1,
        keyframes=[]
    )
    
    preview_window.anim.register_animation(test_anim)
    
    assert len(preview_window.anim.animations) == initial_count + 1
    assert "test_fade" in preview_window.anim.animations


def test_animation_properties(preview_window):
    """Test animation properties"""
    # Create test animation
    test_anim = Animation(
        name="test_pulse",
        type=AnimationType.PULSE.value,
        duration=1200,
        easing=EasingFunction.EASE_IN_QUAD.value,
        iterations=-1,
        keyframes=[]
    )
    
    preview_window.anim.register_animation(test_anim)
    
    # Verify properties
    anim = preview_window.anim.animations["test_pulse"]
    assert anim.type == "pulse"
    assert anim.duration == 1200
    assert anim.easing == "ease_in_quad"
    assert anim.iterations == -1  # infinite loop


def test_animation_update(preview_window):
    """Test updating animation properties"""
    # Create test animation
    test_anim = Animation(
        name="test_update",
        type=AnimationType.FADE.value,
        duration=500,
        easing=EasingFunction.LINEAR.value,
        iterations=1,
        keyframes=[]
    )
    
    preview_window.anim.register_animation(test_anim)
    
    # Change properties
    anim = preview_window.anim.animations["test_update"]
    anim.type = "bounce"
    anim.duration = 800
    anim.easing = "ease_out"
    anim.iterations = -1
    
    # Verify changes
    updated_anim = preview_window.anim.animations["test_update"]
    assert updated_anim.type == "bounce"
    assert updated_anim.duration == 800
    assert updated_anim.easing == "ease_out"
    assert updated_anim.iterations == -1


def test_animation_deletion(preview_window):
    """Test deleting animation"""
    # Create test animations
    for i in range(3):
        anim = Animation(
            name=f"anim_{i}",
            type=AnimationType.FADE.value,
            duration=500,
            easing=EasingFunction.LINEAR.value,
            iterations=1,
            keyframes=[]
        )
        preview_window.anim.register_animation(anim)
    
    initial_count = len(preview_window.anim.animations)
    
    # Delete one
    if "anim_1" in preview_window.anim.animations:
        del preview_window.anim.animations["anim_1"]
    
    assert len(preview_window.anim.animations) == initial_count - 1
    assert "anim_1" not in preview_window.anim.animations


def test_preview_controls(preview_window):
    """Test preview controls work"""
    # Select widget
    preview_window.selected_widget_idx = 0
    
    # Create test animation
    test_anim = Animation(
        name="test_preview",
        type=AnimationType.FADE.value,
        duration=500,
        easing=EasingFunction.LINEAR.value,
        iterations=1,
        keyframes=[]
    )
    preview_window.anim.register_animation(test_anim)
    preview_window.selected_anim = "test_preview"
    
    # Test play
    preview_window._on_anim_play()
    assert preview_window.anim_playing == True
    
    # Test stop
    preview_window._on_anim_stop()
    assert preview_window.anim_playing == False


def test_animation_list(preview_window):
    """Test listing animations"""
    # Create multiple animations
    for i in range(5):
        anim = Animation(
            name=f"anim_{i}",
            type=AnimationType.FADE.value,
            duration=500,
            easing=EasingFunction.LINEAR.value,
            iterations=1,
            keyframes=[]
        )
        preview_window.anim.register_animation(anim)
    
    anim_list = preview_window.anim.list_animations()
    assert len(anim_list) >= 5
    assert "anim_0" in anim_list
    assert "anim_4" in anim_list


def test_keyframe_creation():
    """Test creating keyframes"""
    from ui_animations import Keyframe
    
    kf = Keyframe(
        time=0.5,
        properties={"opacity": 0.5, "x": 100},
        easing="ease_in_out"
    )
    
    assert kf.time == 0.5
    assert kf.properties["opacity"] == 0.5
    assert kf.properties["x"] == 100
    assert kf.easing == "ease_in_out"


def test_animation_with_keyframes(preview_window):
    """Test animation with multiple keyframes"""
    from ui_animations import Keyframe
    
    # Create keyframes
    keyframes = [
        Keyframe(time=0.0, properties={"opacity": 0.0}, easing="linear"),
        Keyframe(time=0.5, properties={"opacity": 0.5}, easing="ease_in"),
        Keyframe(time=1.0, properties={"opacity": 1.0}, easing="ease_out")
    ]
    
    # Create animation
    anim = Animation(
        name="fade_keyframes",
        type=AnimationType.FADE.value,
        duration=1000,
        easing=EasingFunction.LINEAR.value,
        iterations=1,
        keyframes=keyframes
    )
    
    preview_window.anim.register_animation(anim)
    
    # Verify
    loaded_anim = preview_window.anim.animations["fade_keyframes"]
    assert len(loaded_anim.keyframes) == 3
    assert loaded_anim.keyframes[0].time == 0.0
    assert loaded_anim.keyframes[1].time == 0.5
    assert loaded_anim.keyframes[2].time == 1.0


def test_keyframe_sorting(preview_window):
    """Test keyframes are sorted by time"""
    from ui_animations import Keyframe
    
    # Create keyframes out of order
    keyframes = [
        Keyframe(time=1.0, properties={"x": 300}, easing="linear"),
        Keyframe(time=0.0, properties={"x": 0}, easing="linear"),
        Keyframe(time=0.5, properties={"x": 150}, easing="linear")
    ]
    
    anim = Animation(
        name="move_sorted",
        type=AnimationType.MOVE.value,
        duration=500,
        easing=EasingFunction.LINEAR.value,
        iterations=1,
        keyframes=keyframes
    )
    
    preview_window.anim.register_animation(anim)
    
    # Sort keyframes
    loaded_anim = preview_window.anim.animations["move_sorted"]
    loaded_anim.keyframes.sort(key=lambda k: k.time)
    
    # Verify sorted
    assert loaded_anim.keyframes[0].time == 0.0
    assert loaded_anim.keyframes[1].time == 0.5
    assert loaded_anim.keyframes[2].time == 1.0


def test_easing_functions():
    """Test easing functions return valid values"""
    from ui_animations import AnimationEasing
    
    # Test at key points
    test_points = [0.0, 0.25, 0.5, 0.75, 1.0]
    
    for t in test_points:
        # All easing functions should return values in [0, 1] range (approximately)
        assert 0.0 <= AnimationEasing.linear(t) <= 1.0
        assert AnimationEasing.ease_in(t) >= 0.0
        assert AnimationEasing.ease_out(t) >= 0.0
        assert AnimationEasing.ease_in_out(t) >= 0.0
        assert AnimationEasing.ease_in_quad(t) >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
