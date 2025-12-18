# Implementation Summary (current “embedded OS UI” path)

## Goal

Build a non-touch UI stack for ESP32-S3 devices with a small display (SSD1363 256×128, 4bpp gray) driven by joystick/encoder inputs:

1) Design UI on PC (pygame designer)  
2) Export to embedded-friendly C (`UiScene`/`UiWidget`)  
3) Run on device with focus navigation + value editors

## Data flow

- **Design source:** JSON (see `main_scene.json`)
- **Schema:** `schemas/ui_design.schema.json` (IDE support) + `tools/validate_design.py` (sanity checks)
- **Export targets:**
  - `src/ui_design.c` + `src/ui_design.h` (generated automatically in PlatformIO builds)
  - Optional: header-only export via `tools/ui_export_c_header.py`
- **Firmware runtime:** consumes `UiScene` (`src/ui_scene.h`) and renders via `src/ui_render*.c`
  - For scrollable menus/lists, runtime can use a **virtualized list model** (absolute index + viewport) via `UI_CMD_LISTMODEL_*`.

## Key concepts

- **Widget ID:** `_widget_id` / `id` in JSON → `UiWidget.id`  
  Used for stable lookups (status bar fields, actions, bindings).

- **Runtime bindings / value editors:**  
  JSON `runtime` (or `constraints_json`) is exported into `UiWidget.constraints_json` and interpreted in firmware.  
  Example values:
  - `bind=contrast;kind=int;min=0;max=255;step=8`
  - `bind=invert;kind=bool;values=off|on`

- **No touchscreen:**  
  Interaction is focus-based (D‑pad/encoder). Navigation can be auto-computed from geometry.

## Firmware building blocks

- **Schema:** `src/ui_scene.h`
- **UI runtime service:** `src/services/ui/`
  - `ui.c/.h` — high-level UI orchestration (scene, focus, edit mode)
  - `ui_meta.c/.h` — runtime metadata/bindings helpers
  - `ui_bindings.c/.h` — value bindings/editors
  - `ui_listmodel.c/.h` — virtualized menu/list scrolling (offset/active + item label/value)
- **UI app layer:** `src/services/ui_app/` (screen stack + list population via `ui_cmd_listmodel_*`)
- **Rendering:** `src/ui_render*.c|h` (software buffer, primitives, clipping/blitting)
- **Navigation:** `src/ui_nav.c|h` (auto-nav + focus moves)
- **Display driver:** `src/display/ssd1363.c|h`

## PlatformIO environments

- `arduino_nano_esp32` / `esp32-s3-devkitm-1` — real hardware builds
- `*-nohw` — hardware-friendly variants (avoid upload timeouts when board is missing)
- `native` — host/native tests for UI core/render pieces
