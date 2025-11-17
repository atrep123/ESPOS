- Area: Designer
- Type: Enhancement
- Priority: P1

## Title
Designer: Magnetic Guides Overlay (drag/resize alignment)

## Summary
Show magnetic alignment guides while dragging or resizing widgets, aligning to sibling edges/centers and grid.

## Scope
- Draw temporary guides on-canvas during drag/resize.
- Support edge and center alignment to visible siblings and grid lines.
- Toggle via toolbar: "Guides" (default ON if grid/snap is enabled; otherwise OFF).

## Acceptance Criteria
- Dragging/resizing shows guides when within snap tolerance.
- No change to existing snapping logic or exported scene.
- Guides toggle hides guides without changing snapping behavior.

## Notes
- Keep O(1) per frame rendering; compute only nearest candidates.
- Follow existing preview rendering helpers and style; no new deps.
