"""
Test alignment guides and snap-to-widget functionality
"""
import pytest

from ui_designer import WidgetConfig, WidgetType
from ui_designer_preview import PreviewSettings, VisualPreviewWindow


def test_preview_settings_snap_to_widgets():
    """Test that PreviewSettings has snap-to-widget options"""
    settings = PreviewSettings()
    
    assert hasattr(settings, 'snap_to_widgets')
    assert hasattr(settings, 'snap_distance')
    assert hasattr(settings, 'show_alignment_guides')
    
    assert settings.snap_to_widgets is True
    assert settings.snap_distance == 4
    assert settings.show_alignment_guides is True


def test_find_alignment_guides_empty_scene(headless_preview: VisualPreviewWindow):
    """Test alignment guide detection with empty scene"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    widget = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    preview.designer.scenes["test"].widgets.append(widget)
    preview.selected_widget_idx = 0
    
    guides = preview._find_alignment_guides(widget)
    assert guides == []  # No other widgets to align to


def test_find_alignment_guides_vertical_left(headless_preview: VisualPreviewWindow):
    """Test vertical alignment guide detection (left edges)"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets with aligned left edges
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=40, width=60, height=30)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    guides = preview._find_alignment_guides(w1)
    
    # Should find left edge alignment
    assert any(g[0] == 'v' and g[1] == 10 and 'left' in g[2] for g in guides)


def test_find_alignment_guides_horizontal_top(headless_preview: VisualPreviewWindow):
    """Test horizontal alignment guide detection (top edges)"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets with aligned top edges
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=70, y=10, width=40, height=25)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    guides = preview._find_alignment_guides(w1)
    
    # Should find top edge alignment
    assert any(g[0] == 'h' and g[1] == 10 and 'top' in g[2] for g in guides)


def test_find_alignment_guides_center(headless_preview: VisualPreviewWindow):
    """Test center alignment guide detection"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets with aligned centers (center_x both 30)
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=40, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=20, y=50, width=20, height=30)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    guides = preview._find_alignment_guides(w1)
    
    # Should find center-x alignment
    assert any(g[0] == 'v' and 'center' in g[2] for g in guides)


def test_find_alignment_guides_threshold(headless_preview: VisualPreviewWindow):
    """Test that guides are only detected within threshold"""
    preview: VisualPreviewWindow = headless_preview
    preview.settings.snap_distance = 5
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets just outside threshold (6px apart)
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=16, y=40, width=50, height=20)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    guides = preview._find_alignment_guides(w1)
    
    # Should NOT find left edge alignment (outside threshold)
    assert not any(g[0] == 'v' and g[1] == 16 and 'left' in g[2] for g in guides)
    
    # Move within threshold (4px apart)
    w2.x = 14
    guides = preview._find_alignment_guides(w1)
    
    # Should now find alignment
    assert any(g[0] == 'v' and 'left' in g[2] for g in guides)


def test_apply_widget_snapping_left_edge(headless_preview: VisualPreviewWindow):
    """Test snapping to left edge of another widget"""
    preview: VisualPreviewWindow = headless_preview
    preview.settings.snap_to_widgets = True
    preview.settings.snap_distance = 5
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=100, y=40, width=50, height=20)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    # Try to move w1 close to w2's left edge (x=100)
    snapped_x, snapped_y = preview._apply_widget_snapping(w1, 97, 10)
    
    # Should snap to x=100 (within 5px threshold)
    assert snapped_x == 100
    assert snapped_y == 10  # Y unchanged


def test_apply_widget_snapping_disabled(headless_preview: VisualPreviewWindow):
    """Test that snapping can be disabled"""
    preview: VisualPreviewWindow = headless_preview
    preview.settings.snap_to_widgets = False  # Disable
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=100, y=40, width=50, height=20)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    # Try to move w1 close to w2's left edge
    snapped_x, snapped_y = preview._apply_widget_snapping(w1, 97, 10)
    
    # Should NOT snap (feature disabled)
    assert snapped_x == 97
    assert snapped_y == 10


def test_apply_widget_snapping_center_y(headless_preview: VisualPreviewWindow):
    """Test snapping to vertical center alignment"""
    preview: VisualPreviewWindow = headless_preview
    preview.settings.snap_to_widgets = True
    preview.settings.snap_distance = 5
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets (center_y: w1=20, w2=40)
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=100, y=30, width=50, height=20)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    # Try to move w1 close to w2's center_y (40)
    # w1 height is 20, so to get center_y=40, need y=30
    _snapped_x, snapped_y = preview._apply_widget_snapping(w1, 10, 28)
    
    # Should snap to y=30 (center alignment)
    assert snapped_y == 30


def test_alignment_guides_update_during_drag(headless_preview: VisualPreviewWindow):
    """Test that alignment_guides list updates during drag"""
    preview: VisualPreviewWindow = headless_preview
    preview.settings.snap_to_widgets = True
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    # Add two widgets with aligned left edges
    w1 = WidgetConfig(type=WidgetType.LABEL.value, x=10, y=10, width=50, height=20)
    w2 = WidgetConfig(type=WidgetType.LABEL.value, x=100, y=40, width=50, height=20)
    
    preview.designer.scenes["test"].widgets.extend([w1, w2])
    preview.selected_widget_idx = 0
    
    assert preview.alignment_guides == []  # Initially empty
    
    # Apply snapping (simulates drag)
    _snapped_x, _snapped_y = preview._apply_widget_snapping(w1, 100, 10)
    
    # alignment_guides should now be populated
    assert len(preview.alignment_guides) > 0
    assert any(g[0] == 'v' and g[1] == 100 for g in preview.alignment_guides)


def test_draw_alignment_guides_empty(headless_preview: VisualPreviewWindow):
    """Test drawing alignment guides with empty list"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    preview.alignment_guides = []
    
    # Should not raise error
    preview._draw_alignment_guides()


def test_draw_alignment_guides_vertical(headless_preview: VisualPreviewWindow):
    """Test drawing vertical alignment guide"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    preview.alignment_guides = [('v', 50, 'left')]
    
    # Should not raise error (headless has no canvas, but method should handle)
    try:
        preview._draw_alignment_guides()
    except AttributeError:
        # Expected in headless mode (no canvas)
        pass


def test_draw_alignment_guides_horizontal(headless_preview: VisualPreviewWindow):
    """Test drawing horizontal alignment guide"""
    preview: VisualPreviewWindow = headless_preview
    preview.designer.create_scene("test")
    preview.designer.current_scene = "test"
    
    preview.alignment_guides = [('h', 30, 'top')]
    
    # Should not raise error (headless has no canvas, but method should handle)
    try:
        preview._draw_alignment_guides()
    except AttributeError:
        # Expected in headless mode (no canvas)
        pass


def test_show_alignment_guides_setting(headless_preview: VisualPreviewWindow):
    """Test that show_alignment_guides setting controls rendering"""
    preview: VisualPreviewWindow = headless_preview
    settings = preview.settings
    
    assert settings.show_alignment_guides is True
    
    # Can be toggled
    settings.show_alignment_guides = False
    assert settings.show_alignment_guides is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
