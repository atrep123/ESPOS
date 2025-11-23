# Preview Module Refactoring

## Overview

The monolithic `ui_designer_preview.py` (6365 lines) has been refactored into a modular `preview/` package for better maintainability.

## New Structure

```
preview/
├── __init__.py              # Package exports (7 lines)
├── settings.py              # PreviewSettings dataclass (37 lines)
├── rendering.py             # Drawing helpers (72 lines)
├── animation_editor.py      # AnimationEditorWindow class (514 lines)
├── widget_renderer.py       # Widget rendering pipeline (279 lines)
├── event_handlers.py        # Mouse/keyboard events (119 lines)
├── overlays.py              # Grid and overlays (137 lines)
└── window.py                # VisualPreviewWindow (4507 lines)
```

## Completed Refactoring

✅ **settings.py** - Preview configuration (42 lines)
- `PreviewSettings` dataclass
- All preview window settings (zoom, grid, snap, performance, etc.)

✅ **rendering.py** - Rendering utilities (87 lines)
- `size()` - Responsive scaling helper
- `widget_edges()` - Extract widget edge positions
- `get_color_rgb()` - Color name to RGB
- `hex_to_rgb()` - Hex to RGB conversion
- `draw_rounded_rectangle()` - PIL drawing helper

✅ **animation_editor.py** - Animation timeline (1256 lines)
- `AnimationEditorWindow` class
- Complete animation editing UI
- Timeline, playback controls, keyframe editor

✅ **widget_renderer.py** - Widget rendering pipeline (310 lines)
- `WidgetRenderer` mixin class
- `_draw_widget()` - Main drawing coordinator
- `_compute_widget_geometry()` - Position/size calculation
- `_resolve_widget_colors()` - Color selection
- `_paint_widget_background()` - Fill background
- `_paint_widget_border()` - Draw borders with styles
- `_paint_widget_content()` - Widget-specific rendering
- Individual widget painters: checkbox, progressbar, gauge, slider

✅ **event_handlers.py** - Mouse/keyboard events (155 lines)
- `EventHandlers` mixin class
- `_canvas_to_widget_coords()` - Coordinate conversion
- `_find_widget_at()` - Hit testing
- `_find_resize_handle()` - Handle detection
- `_apply_widget_snapping()` - Magnetic snapping logic

✅ **overlays.py** - Grid and overlays (160 lines)
- `OverlayRenderer` mixin class
- `_draw_grid()` - Configurable grid with padding
- `_draw_guides_overlay()` - Alignment guide lines
- `_draw_debug_overlay()` - Debug info panel

✅ **window.py** - Main GUI window class (4507 lines)
- `VisualPreviewWindow` class - COMPLETED
- Full UI setup, toolbar, canvas, properties panel
- Rendering pipeline integration
- Event handling, selection, drag/drop
- Export functionality (PNG, SVG, JSON, C)
- Animation playback
- Component palette integration

**Total extracted:** ~5670 lines from original 6365 lines (89%)
**Remaining in ui_designer_preview.py:** ~1253 lines (imports + compat wrapper + AnimationEditorWindow + main)

## Refactoring Complete ✅

All major components have been extracted to the preview/ package:

Convert `ui_designer_preview.py` to a compatibility shim:

```python
"""Backward compatibility - re-export from preview package."""
from preview import AnimationEditorWindow, PreviewSettings, VisualPreviewWindow
__all__ = ["PreviewSettings", "VisualPreviewWindow", "AnimationEditorWindow"]
```

### 3. Update Imports Across Codebase

**Current imports:**
```python
from ui_designer_preview import VisualPreviewWindow
from ui_designer_preview import PreviewSettings
```

**New imports (preferred):**
```python
from preview import VisualPreviewWindow
from preview import PreviewSettings
```

**Still works (compatibility):**
```python
from ui_designer_preview import VisualPreviewWindow  # uses compat shim
```

## Files to Update

Search and optionally update imports in:
- `ui_designer_pro.py`
- `ui_designer_live.py`
- `test/test_ui_designer*.py`
- `test/test_preview*.py`
- Any other files importing from ui_designer_preview

## Benefits

1. **Reduced Complexity**: Each module < 1500 lines (except window.py which is still large)
2. **Clear Responsibilities**: Settings, rendering, animation, main window
3. **Easier Testing**: Can test/mock individual components
4. **Better Navigation**: Find code faster in smaller files
5. **Future Extensibility**: Easy to add new rendering backends, export formats

## Migration Strategy

1. ✅ Create preview/ package structure
2. ✅ Extract settings.py
3. ✅ Extract rendering.py  
4. ✅ Extract animation_editor.py
5. ✅ Extract widget_renderer.py
6. ✅ Extract event_handlers.py
7. ✅ Extract overlays.py
8. ✅ Extract window.py
9. ✅ Replace ui_designer_preview.py with compat shim
10. ✅ Run full test suite - all 14 preview tests passing
11. ⏳ Update CONTRIBUTING.md with new structure (optional)

## Test Results

All 14 preview tests passing:
- test_preview_settings_snap_to_widgets ✅
- test_preview_controls ✅
- test_live_preview_startup ✅
- test_state_overrides_text_changes ✅
- test_anim_preview_bounce_differs ✅
- test_border_styles_markers ✅
- test_preview_export_center_pixel_parity ✅
- test_ascii_preview ✅
- test_palette_workflow_ascii_preview ✅
- test_all_color_roles_are_defined ✅
- test_selection_handles_render_headless ✅
- test_pending_preview_cancel ✅
- test_visual_preview ✅
- test_headless_preview_png ✅

## Test Results

## Rollback

If issues arise, the original `ui_designer_preview.py` can be restored from git history. The compat shim ensures existing code continues working during transition.
