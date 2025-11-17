- Area: Simulator
- Type: Enhancement
- Priority: P1

## Title
Simulator: Toggleable Help Overlay (h, --show-help)

## Summary
Add a small overlay with key shortcuts and controls; toggled at runtime and via CLI.

## Scope
- Key `h` toggles overlay; CLI `--show-help` starts with overlay on.
- Non-intrusive ANSI overlay line(s) without breaking rendering diff.

## Acceptance Criteria
- `--max-frames` runs still exit with 0; `h` toggles help; no perf regression.
