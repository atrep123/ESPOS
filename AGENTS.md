# ESP32OS — Agent Guide (repo root)

This guide applies to everything in the repo **except** `src/` (firmware), which has its own `src/AGENTS.md` that takes precedence.

## What this repo is (current focus)

Embedded, non-touch “OS UI” pipeline:

- **Designer (PC, pygame):** create UI scenes in JSON
- **Export:** JSON → C (`UiScene`/`UiWidget` from `src/ui_scene.h`)
- **Firmware runtime:** SSD1363 (256×128, 4bpp gray), focus navigation (D‑pad/encoder), value editors via `runtime` bindings

## Quick commands

- Install deps: `python -m pip install -r requirements.txt -r requirements-dev.txt`
- Run designer: `python run_designer.py main_scene.json --profile esp32os_256x128_gray4`
- Python checks: `python -m ruff check .` and `python -m pytest -q`
- Validate design JSON: `python tools/validate_design.py main_scene.json`
- PlatformIO (no hardware): `pio run -e arduino_nano_esp32-nohw` / `pio run -e esp32-s3-devkitm-1-nohw`

## Generated files policy

- `src/ui_design.c` and `src/ui_design.h` are **generated**.
  - Update `main_scene.json` (or your design JSON), not the generated C.
  - PlatformIO builds auto-generate these via `scripts/pio_generate_ui_design.py`.

## Where to change things

- UI JSON schema (source of truth): `main_scene.json` + `ui_designer.py`/`ui_models.py`
- Pygame designer UI: `cyberpunk_designer/`
- Export/codegen tools:
  - PlatformIO hook: `scripts/pio_generate_ui_design.py`
  - Standalone header export: `tools/ui_export_c_header.py`
  - Shared generator: `tools/ui_codegen.py`
- Firmware UI schema/runtime:
  - Schema: `src/ui_scene.h`
  - Runtime: `src/services/ui/` and `src/ui_render*.c`

## Workflow notes (AI-friendly)

- Prefer small, reviewable commits: keep “refactor” separate from “behavior changes”.
- Avoid duplicating logic across exporters; share parsing/mapping in one module.
- Keep outputs deterministic: stable ordering and “write only on change” for generators.
