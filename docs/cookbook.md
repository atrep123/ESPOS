# UI Designer Cookbook

- Export Demo:

```powershell
python ui_export_c.py
```

- Preview with Animations:

```powershell
python ui_designer_preview.py
```

- Generate Asset:

```powershell
python assets_pipeline.py import assets/icon.png icon_ok --format 1bpp --threshold 128 --out src/assets
```

- Build Firmware:

```powershell
pio run -e esp32-s3-devkitm-1
pio run -e esp32-s3-devkitm-1 -t upload
pio device monitor
```

Tips:
- Use `DISPLAY_COLOR_BITS` to match 1bpp/4bpp paths.
- Enable `SSD1363_USE_DEFAULT_INIT` only after validating on your panel.
- Dirty flush is auto-selected; keep animations small to reduce I2C traffic.
