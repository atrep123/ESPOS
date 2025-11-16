# ESP32OS UI Designer + Firmware Demo

This workspace contains:
- Python UI Designer, Themes, Animations, Responsive Layout
- Exporter to JSON/HTML/PNG and C headers/sources
- ESP-IDF firmware demo with software framebuffer, dirty-rect flush, and SSD1363 driver

## Quick Start

1) Generate demo UI artifacts

```powershell
python ui_export_c.py
```

Artifacts: `ui_demo.json`, `ui_demo.html`, `ui_demo.png`, and `src/ui_design.h/.c`.

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
