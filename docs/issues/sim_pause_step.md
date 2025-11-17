- Area: Simulator
- Type: Enhancement
- Priority: P2

## Title
Simulator: Pause/Resume ('p') and Single-Step ('n') controls

## Summary
Allow pausing the render loop and stepping frame-by-frame for inspection.

## Scope
- Key `p` toggles paused state; while paused, `n` renders one frame.
- Preserve input collection; paused loop does not advance time.

## Acceptance Criteria
- Works with `--max-frames`; clean exit codes unchanged.
- No impact when not used; no performance penalty when idle.
