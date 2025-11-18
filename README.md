# ESP32OS UI Designer + Firmware Demo

[![CI/CD Pipeline](https://github.com/atrep123/ESPOS/actions/workflows/ci.yml/badge.svg)](https://github.com/atrep123/ESPOS/actions/workflows/ci.yml)

This workspace contains:
- Python UI Designer, Themes, Animations, Responsive Layout
- Exporter to JSON/HTML/PNG and C headers/sources
- ESP-IDF firmware demo with software framebuffer, dirty-rect flush, and SSD1363 driver

## Quick Start

1) Generate demo UI artifacts

```powershell
python ui_export_c.py
```

Artifacts: `examples/ui_demo.json`, `examples/ui_demo.html`, `examples/ui_demo.png`, and `src/ui_design.h/.c`.

2) Configure display
- Edit `src/display_config.h` to set `DISPLAY_I2C_SDA_GPIO`, `DISPLAY_I2C_SCL_GPIO`, and `DISPLAY_I2C_ADDR`.
- Optional: set `DISPLAY_COLOR_BITS` to `1` or `4`.
- Optional: enable a conservative init with `#define SSD1363_USE_DEFAULT_INIT 1` (verify against your module datasheet).

3) Build and flash (PlatformIO)

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
- Use Refresh to redraw; Export PNG to snapshot.

## CI

GitHub Actions runs Python tests and builds firmware for ESP32-S3 on pushes/PRs.

## Performance Metrics

Firmware logs average flush time, FPS, and throughput every ~20 frames from `src/ui_demo.c`.

## Notes

- The SSD1363 init is template-based; finalize values per your display datasheet.
- Dirty-rect updates reduce I2C bandwidth; set `DISPLAY_COLOR_BITS` to match your panel format.
