- Area: Simulator
- Type: Enhancement
- Priority: P1

## Title
Simulator: Safe Shutdown + Exit Code Semantics (q)

## Summary
Add `q` to cleanly exit with code 0; maintain `--max-frames` precedence.

## Scope
- Key `q` exits loop; ensure threads/processes are terminated cleanly.

## Acceptance Criteria
- `q` → exit 0; `--max-frames` still exits 0 after N frames.
