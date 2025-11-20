# ESP32OS - Complete UI Development System

[![Tests](https://github.com/atrep123/ESPOS/actions/workflows/tests.yml/badge.svg)](https://github.com/atrep123/ESPOS/actions/workflows/tests.yml)
[![Release](https://github.com/atrep123/ESPOS/actions/workflows/release.yml/badge.svg)](https://github.com/atrep123/ESPOS/actions/workflows/release.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/atrep123/ESPOS/releases)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-complete-brightgreen.svg)](docs/)

🎨 Professional UI development system for ESP32 embedded displays with visual designer, simulator, and complete toolchain.

## ✨ Features

### 🖌️ UI Designer & Tools

- **Visual UI Designer** with drag-and-drop interface
- **Live Preview** with real-time rendering
- **Animation Editor** with keyframe timeline
- **Theme System** - Dark, Light, Dracula, Nord
- **Component Library** - 50+ pre-built components
- **Template Manager** - Reusable UI patterns
- **Icon Palette** - 50+ Material Design icons

### 🖥️ Simulator & Runtime

- **Python Simulator** with RPC support (JSON-RPC 2.0)
- **WebSocket Server** for remote UI viewing
- **Performance Profiler** with real-time analytics
- **Session Recording** and playback
- **Auto-sizing** terminal support
- **60-240 FPS** configurable refresh rate

### 📤 Export & Integration

- **C/C++ Code Generation** - Direct ESP32 integration
- **PDF Export** - Professional documentation
- **SVG Export** - Vector graphics with gradients/shadows
- **JSON/HTML** - Web preview and data exchange
- **PNG Rendering** - High-quality screenshots

### 🚀 Performance

- **LRU Cache** - Optimized rendering pipeline
- **Lazy Loading** - Efficient resource management
- **Substring Diff** - 70% I/O reduction
- **Type Safety** - Full type hints throughout
- **387 Tests** - Comprehensive test coverage

### 🤝 Collaborative Features

- **Web Designer** - Multi-user real-time collaboration
- **Conflict Resolution** - OT-inspired merge algorithm
- **Cursor Tracking** - See other users in real-time
- **Undo/Redo** - 50 levels with shared history

## 🚀 Quick Start

1. Generate demo UI artifacts

```powershell
python ui_export_c.py
```

Artifacts: `examples/ui_demo.json`, `examples/ui_demo.html`, `examples/ui_demo.png`, and `src/ui_design.h/.c`.

2. Configure display

- Edit `src/display_config.h` to set `DISPLAY_I2C_SDA_GPIO`, `DISPLAY_I2C_SCL_GPIO`, and `DISPLAY_I2C_ADDR`.
- Optional: set `DISPLAY_COLOR_BITS` to `1` or `4`.
- Optional: enable a conservative init with `#define SSD1363_USE_DEFAULT_INIT 1` (verify against your module datasheet).

3. Build and flash (PlatformIO)

```powershell
pio run -e esp32-s3-devkitm-1
pio run -e esp32-s3-devkitm-1 -t upload
pio device monitor
```

You should see a continuous demo render with performance logs.

## Project Map

- `src/` — ESP-IDF firmware (UI core, renderer, services, display config)
- `components/` — ESP-IDF komponenty (display/kernel/services/ui/...)
- `include/` — hlavičky pro firmware a klienta
- `sim/` — C část simulátoru (např. `sim/main.c`)
- Python nástroje a simulátor:
  - `run_sim.ps1`, `run_simulator.py`, `simctl.py`, `sim_run.py`
  - klient/bridge/inspector: `esp32_sim_client.py`, `esp32_hardware_bridge.py`, `state_inspector.py`
  - designér a ukázky: `ui_designer*.py`, `ui_components.py`, `ui_animations.py`, `ui_themes.py`, `ui_responsive.py`
  - exporty/preview: `ui_export_c.py`, `ui_designer_preview.py`, `ui_demo.*`, `showcase.*`, `dashboard_demo.*`
  - profilování/analytics: `performance_profiler.py`, `analytics_dashboard.py`, `profiler_enhanced.*`
- Testy a fixtury: `test/`, `test_*.py`, `test_*.json/html`
- Dokumentace: `README*.md`, `QUICKSTART.md`, `SIMULATOR_README.md`, `SIMULATOR_EXAMPLES.md`, `UI_DESIGNER_GUIDE.md`, `ADVANCED_FEATURES.md`, `FILE_INDEX.md`
- Konfigurace/prostředí: `platformio.ini`, `CMakeLists.txt`, `sdkconfig.*`, `.pio/`, `.venv/`, `.vscode/`, `.sim_config.json`, `sim_ports.json`

Tip: VS Code nyní skrývá běžné cache/fixtury v Exploreru (viz `.vscode/settings.json → files.exclude`).

## Dev Setup

Rychlá příprava prostředí s volitelnými závislostmi a dev nástroji:

```powershell
# vytvoří .venv, nainstaluje projekt s UI+HW+WEB+METRICS a dev nástroje
powershell -ExecutionPolicy Bypass -File .\scripts\dev_setup.ps1 -UI -HW -WEB -METRICS -Dev

# aktivace prostředí v aktuálním shellu
. .\.venv\Scripts\Activate.ps1

# běh testů (vyžaduje -Dev)
pytest -q
```

## Assets Pipeline (PNG → C)

Convert PNG to 1bpp/4bpp C arrays:

```powershell
python assets_pipeline.py import path/to/icon.png my_icon --format 1bpp --threshold 128 --out src/assets
```

Generates `src/assets/my_icon.h/.c` exposing `UiBitmap my_icon_bmp`.

## Visual Preview + Animations

Run the visual preview with animation controls:

```powershell
python ui_designer_preview.py
```

- Select an animation and press Play to preview on the selected widget.
- Use Refresh to redraw; **Export SVG** for professional-quality vector graphics.

### 🎨 Enhanced SVG Export (Issue #10)

Export your UI designs as professional-quality SVG files with advanced features:

**Features:**

- **Gradients**: Linear/radial gradients for smooth color transitions
- **Shadows**: Drop shadows and inner shadows for depth
- **Patterns**: Dot, line, and grid textures for backgrounds
- **Font Embedding**: Embed TTF/OTF fonts for perfect typography
- **Quality Presets**: Web Optimized, Print Quality, High Fidelity

**Usage:**

1. Click "🖼️ Export SVG" in the toolbar
2. Choose a preset or customize advanced options
3. Select scale (0.5x - 4.0x) for different resolutions
4. Export to `.svg` file

**Presets:**

- **Web Optimized**: Small file size, gradients enabled (perfect for web)
- **Print Quality**: Full features with shadows and patterns (professional printing)
- **High Fidelity**: Maximum quality with font embedding (archival quality)

See `ISSUE_10_IMPLEMENTATION.md` for technical details and examples.

## CI

GitHub Actions runs Python tests and builds firmware for ESP32-S3 on pushes/PRs.

## Performance Metrics

Firmware logs average flush time, FPS, and throughput every ~20 frames from `src/ui_demo.c`.

## Notes

- The SSD1363 init is template-based; finalize values per your display datasheet.
- Dirty-rect updates reduce I2C bandwidth; set `DISPLAY_COLOR_BITS` to match your panel format.
