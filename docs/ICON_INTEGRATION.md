# Icon Integration Guide

This document explains how to use the Material Icons in ESP32OS across the Designer, simulator, and firmware.

## Overview
- Icons are defined in Python metadata (`ui_icons.py`) and mapped to ASCII for the simulator (`sim_icon_support.py`).
- The UI exporter (`ui_export_c.py`) emits icon references into C headers/sources for firmware builds.
- The renderer in firmware consumes packed 1bpp icon data via `display_draw_icon`.

## Picking Icons in Python
Use the `ui_icons` helpers to discover icons, categories, and symbols:

```python
from ui_icons import MATERIAL_ICONS, get_icon_by_name, get_icon_by_symbol, get_icons_by_category

icon = get_icon_by_name("Home")
print(icon["symbol"])  # e.g. "mi_home_24px"
```

- `name`: human-readable label shown in tools.
- `symbol`: C symbol base (e.g., `mi_home_24px`).
- `size_16` / `size_24`: concrete C symbols for the 16px / 24px variants.

## Simulator ASCII Mapping
For text-mode simulation, each icon has an ASCII/Unicode fallback:

```python
from sim_icon_support import get_icon_ascii
print(get_icon_ascii("mi_home_24px"))  # ⌂
```

This enables quick UI prototyping in terminals without bitmap rendering.

## Exporting to C for Firmware
Use the exporter to generate `src/ui_design.h` and `src/ui_design.c` from a scene:

```powershell
# Example (PowerShell)
python .\ui_export_c.py --preset esp32_oled_128x64_1bpp --base-name ui_design --icon-size 16
```

Key details:
- `--icon-size` controls which icon variant is referenced (16 or 24 pixels).
- The generated C lists widgets; icons appear as `const icon_t* icon` and `icon_name` fields.
- Icon symbols referenced are emitted as `extern const icon_t mi_...;` guarded by `#if HAVE_ICONS`.

## Rendering in Firmware
The software-buffer renderer exposes an icon draw helper:

```c
#include "ui_render_swbuf.h"
#include "icons.h"

extern const icon_t mi_home_24px; // provided by icon assets

void draw_example(display_t* d) {
    // Draw at x=10, y=8, not inverted
    display_draw_icon(d, &mi_home_24px, 10, 8, false);
}
```

Notes:
- `display_draw_icon(display_t *d, const icon_t *icon, int16_t x, int16_t y, bool invert)` expects MSB-first packed 1bpp data.
- Include the icon assets (`icons.h`/`icons.c`) matching your chosen size. Ensure `HAVE_ICONS` is set accordingly.

## Command-line Helper
Use the CLI to explore icons quickly:

```powershell
python .\icon_tool.py stats
python .\icon_tool.py list --category navigation
python .\icon_tool.py show --symbol mi_home_24px
```

## Troubleshooting
- If a symbol prints `?` in the simulator, verify the mapping in `sim_icon_support.py`.
- If firmware linking fails on missing `icon_t` symbols, confirm you built the icon asset sources and set `HAVE_ICONS`.
