# File Index (human + AI quick map)

## Top-level

- `README.md` — quick overview + common commands
- `AGENTS.md` — repo-wide working guide (except firmware)
- `platformio.ini` — PlatformIO envs + auto-export hook
- `main_scene.json` — example “OS UI” design used for firmware demo
- `templates.json` — reusable scene/widget templates for the designer

## Designer (PC)

- `run_designer.py` — main entry point (pygame designer)
- `cyberpunk_designer/` — pygame front-end (widgets, inspector, navigation)
- `ui_designer.py` — core designer backend (scene model, ops, validation, import/export)
- `ui_models.py` — dataclasses / models shared by designer tooling
- `ui_template_manager.py` — template library load/apply

## Codegen / tooling

- `scripts/pio_generate_ui_design.py` — PlatformIO pre-build script (JSON → `src/ui_design.c|h`)
- `tools/ui_codegen.py` — shared JSON → C/header codegen (used by scripts/tools)
- `tools/ui_export_c_header.py` — CLI header-only exporter (JSON → `.h`)
- `tools/validate_design.py` — design JSON validator (export/runtime compatibility)
- `tools/audit_designs.py` — sanity audit for design JSON files
- `tools/live_preview.py` — send design JSON to device over serial (optional)

## Schemas

- `schemas/ui_design.schema.json` — JSON Schema for design files (editor/IDE support)

## Firmware (ESP-IDF / PlatformIO)

- `src/services/ui/ui_listmodel.c`, `src/services/ui/ui_listmodel.h` - virtualized menu/list scrolling (viewport + item label/value)
- `src/services/ui_app/` - UI app layer (screen stack + list population)
- `src/AGENTS.md` — firmware-only coding rules
- `src/ui_scene.h` — UI schema (`UiWidget`, `UiScene`) shared by exporter/runtime
- `src/ui_design.c`, `src/ui_design.h` — generated demo design
- `src/services/ui/` — UI runtime (core state, bindings/meta, rendering glue)
- `src/ui_render*.c|h` — renderer backends (software buffer, primitives)
- `src/ui_nav.c|h` — focus navigation (auto-nav)
- `src/display/ssd1363.c|h` — SSD1363 display driver (256×128, 4bpp gray)
- `src/services/input/` — input service (joystick/encoders)

## Tests

- `test/test_ui_listmodel/` - native tests for scrollable list/menu model
- `tests/` — Python unit tests (designer/tooling)
- `test/` — PlatformIO native test harness and stubs
