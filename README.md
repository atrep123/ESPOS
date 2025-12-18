# ESP32OS UI Toolkit

Repo je záměrně osekaný na “embedded OS UI” cestu:

- Pygame UI Designer (tvorba UI pro MCU bez dotyku)
- Export JSON → C (`UiScene`/`UiWidget` dle `src/ui_scene.h`)
- Firmware runtime pro SSD1363 (256×128, 4bpp gray), ovládání joystickem / enkodéry

## Designer

```powershell
python -m pip install -r requirements.txt
python run_designer.py main_scene.json --profile esp32os_256x128_gray4
```

Tip: `Ctrl+F` = Fit Text, `Ctrl+Shift+F` = Fit Widget, `F3` = overflow warnings, `F2` = input simulation mode (D-pad/encoder).

## Export do C (header)

```powershell
python tools/ui_export_c_header.py main_scene.json -o ui_scene_generated.h
```

Firmware můžeš buď:
- includnout `ui_scene_generated.h` a použít exportovanou `UiScene`, nebo
- nahradit demo `src/ui_design.c`/`src/ui_design.h` vlastním exportem (podle toho, jak to chceš integrovat).

## Runtime bindings (hodnotové editory)

Designer widgety mohou mít pole `runtime`, které se exportuje do `UiWidget.constraints_json`.
UI runtime pak umí jednoduché editory bez dotyku (A/encoder = edit, Up/Down = změna):

- `bind=contrast;kind=int;min=0;max=255;step=8`
- `bind=invert;kind=bool;values=off|on`
- `bind=col_offset;kind=int;min=0;max=16;step=1`

## PlatformIO build

```powershell
pio run -e arduino_nano_esp32-nohw
pio run -e esp32-s3-devkitm-1-nohw
```

## Quick checks

```powershell
scripts/check_all.ps1
```

## Repo docs

- `AGENTS.md` (work guide)
- `FILE_INDEX.md` (project map)
- `IMPLEMENTATION_SUMMARY.md` (architecture)

## SSD1363 bring-up (volitelné)

- Debug přepínače: `src/user_config.h` (`SSD1363_I2C_SCAN_ON_BOOT`, `SSD1363_BOOT_TEST_PATTERN`).
- Pokud je obraz posunutý, dolaď `SSD1363_COL_OFFSET` a/nebo `SSD1363_INIT_DISPLAY_OFFSET` v `src/user_config.h`.
