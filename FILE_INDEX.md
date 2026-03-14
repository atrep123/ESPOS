# File Index (human + AI quick map)

## Top-level

- `README.md` — quick overview + common commands
- `AGENTS.md` — repo-wide working guide (except firmware)
- `CONTRIBUTING.md` — contribution guidelines
- `SECURITY.md` — security policy and reporting
- `IMPLEMENTATION_SUMMARY.md` — architecture/implementation overview
- `platformio.ini` — PlatformIO envs + auto-export hook
- `CMakeLists.txt` — ESP-IDF CMake project root
- `main_scene.json` — example "OS UI" design used for firmware demo
- `templates.json` — reusable scene/widget templates for the designer
- `constants.py` — shared Python constants (paths, limits)
- `design_tokens.py` — design token definitions (colors, spacing, fonts)
- `event_manager.py` — event bus / observer for designer
- `shared_undo_redo.py` — undo/redo stack shared across designer modules
- `pyproject.toml` — Python project metadata + tool config (ruff, mypy)
- `pyrightconfig.json` — Pyright type-checker settings
- `requirements.txt` / `requirements-dev.txt` — Python deps (runtime / dev)

## Designer (PC)

- `run_designer.py` — main entry point (pygame designer)
- `launcher.py` — alternative launcher / CLI wrapper
- `cyberpunk_editor.py` — top-level editor composition
- `cyberpunk_designer/` — pygame front-end package:
  - `app.py` — application class and main loop
  - `state.py` — global editor state
  - `drawing.py` — canvas rendering
  - `components.py` — widget component registry
  - `component_fields.py` — inspector field definitions per widget type
  - `component_insert.py` — widget insertion logic
  - `constants.py` — designer-specific constants
  - `fit_text.py` / `fit_widget.py` — auto-sizing helpers
  - `focus_nav.py` — focus / tab-navigation simulation
  - `font6x8.py` — 6×8 bitmap font for pixel-accurate preview
  - `input_handlers.py` — mouse/keyboard event dispatch
  - `inspector_logic.py` / `inspector_utils.py` — property inspector
  - `io_ops.py` — file I/O (save/load JSON)
  - `layout.py` / `layout_tools.py` — layout engine + helpers
  - `live_preview.py` — live preview integration
  - `perf.py` — performance monitoring
  - `reporting.py` — diagnostic reporting
  - `selection_ops.py` — multi-select, alignment, distribution
  - `text_metrics.py` — text measurement utilities
  - `windowing.py` — window/panel management
- `ui_designer.py` — core designer backend (scene model, ops, validation, import/export)
- `ui_models.py` — dataclasses / models shared by designer tooling
- `ui_template_manager.py` — template library load/apply

## Codegen / tooling

- `scripts/pio_generate_ui_design.py` — PlatformIO pre-build script (JSON → `src/ui_design.c|h`; optional `ESP32OS_UI_VALIDATE=1` pre-flight)
- `scripts/skip_hw_tests.py` — skip hardware-dependent tests in CI
- `tools/ui_codegen.py` — shared JSON → C/header codegen (used by scripts/tools)
- `tools/ui_export_c_header.py` — CLI header-only exporter (JSON → `.h`)
- `tools/validate_design.py` — design JSON validator (export/runtime compatibility)
- `tools/audit_designs.py` — sanity audit for design JSON files
- `tools/check_demo_scene_strict.py` — strict demo-scene validation
- `tools/generate_demo_scene.py` — generate demo scene JSON
- `tools/gen_icons.py` — icon asset generator (PNG → C arrays)
- `tools/clean_artifacts.py` — clean generated/build artifacts
- `tools/live_preview.py` — send design JSON to device over serial (optional)

## Scripts (CI / local checks)

- `scripts/check_all.ps1` / `scripts/check_all.sh` — CI check suite (lint, test, build)
- `scripts/check_all_local.ps1` / `scripts/check_all_local.sh` — local dev check suite
- `scripts/check_native_toolchain.ps1` / `scripts/check_native_toolchain.sh` — verify native build toolchain
- `scripts/check_native_policy_probe.ps1` — probe Windows code-signing / WDAC policy
- `scripts/check_native_policy_artifacts.ps1` — collect policy-blocked artifacts
- `scripts/check_native_policy_triage_csv.ps1` — triage CSV for policy blockers
- `scripts/generate_native_policy_allowlist_request.ps1` — generate WDAC allowlist request
- `scripts/list_native_whitelist_targets.ps1` — list binaries needing allowlist
- `scripts/burnin_native_policy.ps1` — burn-in test for native policy
- `scripts/summarize_native_policy_history.ps1` — summarize native policy history
- `scripts/triage_native_policy_blockers.ps1` — triage native policy blockers

## Schemas

- `schemas/ui_design.schema.json` — JSON Schema for design files (editor/IDE support)

## Firmware (ESP-IDF / PlatformIO)

### Core

- `src/AGENTS.md` — firmware-only coding rules
- `src/CMakeLists.txt` — ESP-IDF component CMake
- `src/main.c` — entry point (`app_main`), SPIFFS init, service startup, `system_shutdown()` for graceful teardown
- `src/ui_scene.h` — UI schema (`UiWidget`, `UiScene`, `UiWidgetType` enum)
- `src/ui_design.c`, `src/ui_design.h` — **generated** demo design (do not edit)
- `src/display_config.h` — display hardware configuration
- `src/input_config.h` — input hardware configuration
- `src/user_config.h` — user-level configuration

### Display

- `src/display/ssd1363.c|h` — SSD1363 I2C OLED driver (256×128, 4bpp gray)
- `src/ui_render.c|h` — framebuffer rendering primitives
- `src/ui_render_swbuf.c|h` — software-buffered renderer (dirty-region tracking)

### UI system

- `src/services/ui/ui.c|h` — UI service (scene management, event loop, `ui_start`/`ui_stop`)
- `src/services/ui/ui_core.c|h` — widget tree, state, selection
- `src/services/ui/ui_components.c|h` — widget-type rendering (label, button, gauge…)
- `src/services/ui/ui_meta.c|h` — widget metadata & constraints (suffix, prefix, precision, scale)
- `src/services/ui/ui_bindings.c|h` — runtime value bindings (thread-safe, NVS-backed)
- `src/services/ui/ui_listmodel.c|h` — virtualized list/menu scrolling (viewport + items)
- `src/ui_nav.c|h` — focus navigation (D-pad/encoder, auto-nav)

### Fonts & icons

- `src/ui_font_6x8.c|h` — built-in 6×8 bitmap font
- `src/icons.c|h` — icon assets (16px)
- `src/icons_24.c|h` — icon assets (24px)
- `src/icons_registry.c|h` — icon lookup registry
- `src/ui_demo_icons.c|h` — demo icon display helpers
- `src/ui_demo.c|h` — demo scene helpers

### Kernel

- `src/kernel/msgbus.c|h` — inter-service message bus (`bus_init`, `bus_deinit`)
- `src/kernel/timers.c|h` — software timer management (`kernel_start_ticker`, `kernel_stop_ticker`)

### Services

Each service follows a start/stop lifecycle: `*_start()` creates a FreeRTOS task, `*_stop()` deletes it.

- `src/services/input/` — button/encoder input service (`input_start`, `input_stop`)
- `src/services/rpc/` — external RPC interface (`rpc_start`, `rpc_stop`)
- `src/services/store/` — persistent configuration, NVS/SPIFFS (`store_init`, `store_deinit`)
- `src/services/metrics/` — runtime performance metrics (`metrics_start`, `metrics_stop`)
- `src/services/ui_app/` — application-level UI logic (`ui_app_start`, `ui_app_stop`)

## Tests (C — PlatformIO native)

- `test/stubs/` — test stubs and mocks for firmware modules
- `test/test_chart/` — chart widget tests
- `test/test_gauge/` — gauge widget tests
- `test/test_icon/` — icon rendering tests
- `test/test_input/` — input service tests
- `test/test_metrics/` — metrics service tests
- `test/test_msgbus/` — message bus tests
- `test/test_rpc/` — RPC service tests
- `test/test_seesaw/` — seesaw driver tests
- `test/test_store/` — store/config persistence tests
- `test/test_ui_app/` — UI app layer tests
- `test/test_ui_bindings/` — runtime value binding tests
- `test/test_ui_border/` — border rendering tests
- `test/test_ui_cmd/` — UI command dispatch tests
- `test/test_ui_components/` — widget rendering + prefix visibility tests
- `test/test_ui_core/` — widget tree / state tests
- `test/test_ui_dirty/` — dirty-region tracking tests
- `test/test_ui_dither/` — dithering tests
- `test/test_ui_font/` — font rendering tests
- `test/test_ui_format/` — text formatting tests
- `test/test_ui_helpers/` — UI helper function tests
- `test/test_ui_listmodel/` — list/menu model tests
- `test/test_ui_meta/` — metadata & constraints tests
- `test/test_ui_nav/` — focus navigation tests
- `test/test_ui_rect/` — rectangle utility tests
- `test/test_ui_render/` — render primitive tests
- `test/test_ui_render_swbuf/` — software buffer renderer tests
- `test/test_ui_render_text/` — text rendering tests
- `test/test_ui_render_widgets/` — widget rendering pipeline tests
- `test/test_ui_scene_util/` — scene utility tests
- `test/test_ui_text_layout/` — text layout tests
- `test/test_ui_widget_style/` — widget style tests

## Tests (Python)

- `tests/` — Python unit tests (designer, codegen, validation, end-to-end)
