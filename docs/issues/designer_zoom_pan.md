- Area: Designer
- Type: Enhancement
- Priority: P1

## Title
Designer: Zoom + Hand Pan (Ctrl+Wheel, Ctrl+±, Space+Drag)

## Summary
Add zoom and pan in the canvas to navigate larger scenes while keeping the model/export unchanged.

## Scope
- Zoom controls: Ctrl+MouseWheel, Ctrl+Plus, Ctrl+Minus, Ctrl+0 (reset).
- Pan: hold Space and drag.
- Persist zoom per session (optional), status bar shows current zoom.

## Acceptance Criteria
- Zooming/panning does not alter scene data or export sizing.
- Reset returns to 100% view; interactions remain smooth.

## Notes
- Respect existing scaling code paths and cache.
- Avoid heavy redraw; throttle wheel zoom.
