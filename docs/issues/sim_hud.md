- Area: Simulator
- Type: Enhancement
- Priority: P1

## Title
Simulator: On-screen HUD (FPS/compute_ms/sleep_ms/frame) (F10, --hud)

## Summary
Provide a minimal HUD line with key runtime metrics; toggle at runtime and via CLI.

## Scope
- Key `F10` toggles HUD; CLI `--hud` starts with HUD on.
- Display: FPS, compute_ms, sleep_ms, frame index.

## Acceptance Criteria
- HUD is unobtrusive and compatible with diff-based ANSI rendering.
- No crash with `--max-frames`; no visible regression when off.
