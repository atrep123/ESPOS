"""Tests for Animation C Code Export"""

import shutil
import tempfile
from pathlib import Path

import pytest

from animation_export_c import AnimationExporter
from ui_animations import Animation, AnimationType, EasingFunction, Keyframe


@pytest.fixture
def temp_dir():
    """Create temporary directory for exports"""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def sample_animation():
    """Create sample animation with keyframes"""
    anim = Animation(
        name="test_fade",
        type=AnimationType.FADE.value,
        duration=500,
        delay=0,
        iterations=1,
        easing=EasingFunction.EASE_IN_OUT.value,
        keyframes=[
            Keyframe(time=0.0, properties={'opacity': 0}, easing='linear'),
            Keyframe(time=1.0, properties={'opacity': 255}, easing='linear')
        ]
    )
    return anim


def test_exporter_creation():
    """Test AnimationExporter instantiation"""
    exporter = AnimationExporter()
    assert exporter is not None
    assert len(exporter.animations) == 0


def test_add_animation(sample_animation):
    """Test adding animation to exporter"""
    exporter = AnimationExporter()
    exporter.add_animation(sample_animation)
    
    assert len(exporter.animations) == 1
    assert exporter.animations[0].name == "test_fade"


def test_sanitize_name():
    """Test C identifier sanitization"""
    exporter = AnimationExporter()
    
    assert exporter._sanitize_name("simple") == "simple"
    assert exporter._sanitize_name("Fade In") == "fade_in"
    assert exporter._sanitize_name("slide-left") == "slide_left"
    assert exporter._sanitize_name("test__anim") == "test_anim"
    assert exporter._sanitize_name("123test") == "anim_123test"
    assert exporter._sanitize_name("my@anim#1") == "my_anim_1"


def test_generate_header(sample_animation):
    """Test header file generation"""
    exporter = AnimationExporter()
    exporter.add_animation(sample_animation)
    
    header = exporter.generate_header("test.h")
    
    # Check header guards
    assert "#ifndef TEST_H" in header
    assert "#define TEST_H" in header
    assert "#endif /* TEST_H */" in header
    
    # Check includes
    assert "#include <stdint.h>" in header
    assert "#include <stdbool.h>" in header
    
    # Check animation type enum
    assert "typedef enum {" in header
    assert "UI_ANIM_FADE" in header
    assert "} ui_animation_type_t;" in header
    
    # Check easing enum
    assert "UI_EASING_EASE_IN_OUT" in header
    assert "} ui_easing_t;" in header
    
    # Check structures
    assert "typedef struct {" in header
    assert "ui_keyframe_t" in header
    assert "ui_animation_t" in header
    assert "ui_animation_player_t" in header
    
    # Check forward declaration
    assert "extern const ui_animation_t anim_test_fade;" in header
    
    # Check API functions
    assert "void ui_animation_player_init" in header
    assert "void ui_animation_player_start" in header
    assert "bool ui_animation_player_update" in header
    assert "float ui_easing_evaluate" in header


def test_generate_implementation(sample_animation):
    """Test implementation file generation"""
    exporter = AnimationExporter()
    exporter.add_animation(sample_animation)
    
    impl = exporter.generate_implementation("test.c")
    
    # Check header include
    assert '#include "test.h"' in impl
    assert '#include <string.h>' in impl
    
    # Check keyframe array
    assert "static const ui_keyframe_t keyframes_test_fade[]" in impl
    assert "{0.0f," in impl
    assert "{1.0f," in impl
    
    # Check animation struct
    assert "const ui_animation_t anim_test_fade = {" in impl
    assert '.name = "test_fade"' in impl
    assert ".type = UI_ANIM_FADE" in impl
    assert ".duration_ms = 500" in impl
    assert ".easing = UI_EASING_EASE_IN_OUT" in impl
    assert ".keyframes = keyframes_test_fade" in impl
    assert ".keyframe_count = 2" in impl
    
    # Check easing function
    assert "float ui_easing_evaluate(ui_easing_t easing, float t)" in impl
    assert "case UI_EASING_LINEAR:" in impl
    assert "return t;" in impl
    
    # Check player functions
    assert "void ui_animation_player_init" in impl
    assert "void ui_animation_player_start" in impl
    assert "bool ui_animation_player_update" in impl
    assert "float ui_animation_player_get_progress" in impl


def test_export_to_files(sample_animation, temp_dir):
    """Test exporting to actual files"""
    exporter = AnimationExporter()
    exporter.add_animation(sample_animation)
    
    header_file, impl_file = exporter.export_to_files(temp_dir, "exported")
    
    # Check files exist
    assert header_file.exists()
    assert impl_file.exists()
    assert header_file.name == "exported.h"
    assert impl_file.name == "exported.c"
    
    # Check file contents
    header_content = header_file.read_text()
    impl_content = impl_file.read_text()
    
    assert "ui_animation_t" in header_content
    assert "anim_test_fade" in impl_content


def test_multiple_animations(temp_dir):
    """Test exporting multiple animations"""
    exporter = AnimationExporter()
    
    # Add multiple animations
    for i in range(3):
        anim = Animation(
            name=f"anim_{i}",
            type=AnimationType.FADE.value,
            duration=500 + i * 100,
            delay=0,
            iterations=1,
            easing=EasingFunction.LINEAR.value,
            keyframes=[]
        )
        exporter.add_animation(anim)
    
    header_file, impl_file = exporter.export_to_files(temp_dir)
    
    impl_content = impl_file.read_text()
    
    # Check all animations exported
    assert "anim_anim_0" in impl_content
    assert "anim_anim_1" in impl_content
    assert "anim_anim_2" in impl_content
    assert ".duration_ms = 500" in impl_content
    assert ".duration_ms = 600" in impl_content
    assert ".duration_ms = 700" in impl_content


def test_keyframe_properties():
    """Test keyframe properties are correctly exported"""
    anim = Animation(
        name="complex",
        type=AnimationType.MOVE.value,
        duration=1000,
        delay=0,
        iterations=1,
        easing=EasingFunction.EASE_OUT.value,
        keyframes=[
            Keyframe(time=0.0, properties={'x': 0, 'y': 0, 'opacity': 255}, easing='ease_in'),
            Keyframe(time=0.5, properties={'x': 50, 'y': 25, 'opacity': 200}, easing='ease_out'),
            Keyframe(time=1.0, properties={'x': 100, 'y': 50, 'opacity': 255}, easing='linear')
        ]
    )
    
    exporter = AnimationExporter()
    exporter.add_animation(anim)
    
    impl = exporter.generate_implementation()
    
    # Check keyframe data
    assert "{0.0f, 0, 0, 0, 0, 255, 0, UI_EASING_EASE_IN}" in impl
    assert "{0.5f, 50, 25, 0, 0, 200, 0, UI_EASING_EASE_OUT}" in impl
    assert "{1.0f, 100, 50, 0, 0, 255, 0, UI_EASING_LINEAR}" in impl


def test_infinite_loop_animation():
    """Test animation with infinite loop (iterations=-1)"""
    anim = Animation(
        name="infinite",
        type=AnimationType.PULSE.value,
        duration=800,
        delay=0,
        iterations=-1,  # Infinite
        easing=EasingFunction.EASE_IN_OUT.value,
        keyframes=[]
    )
    
    exporter = AnimationExporter()
    exporter.add_animation(anim)
    
    impl = exporter.generate_implementation()
    
    assert ".iterations = -1" in impl


def test_animation_with_delay():
    """Test animation with delay"""
    anim = Animation(
        name="delayed",
        type=AnimationType.FADE.value,
        duration=500,
        delay=200,
        iterations=1,
        easing=EasingFunction.LINEAR.value,
        keyframes=[]
    )
    
    exporter = AnimationExporter()
    exporter.add_animation(anim)
    
    impl = exporter.generate_implementation()
    
    assert ".delay_ms = 200" in impl


def test_empty_keyframes():
    """Test animation without keyframes"""
    anim = Animation(
        name="no_keyframes",
        type=AnimationType.FADE.value,
        duration=500,
        delay=0,
        iterations=1,
        easing=EasingFunction.LINEAR.value,
        keyframes=[]
    )
    
    exporter = AnimationExporter()
    exporter.add_animation(anim)
    
    impl = exporter.generate_implementation()
    
    assert ".keyframes = NULL" in impl
    assert ".keyframe_count = 0" in impl


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
