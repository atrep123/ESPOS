# 🎨 Integrace Image Tools do UI Designeru

Návod, jak používat bitmap ikony a fonty v ESPOS UI Designeru.

## 📦 Co bylo přidáno

### Nové soubory:
- `ui_designer_image_tools.py` - Integrace image tools do UI Designeru
- `examples/image_tools_demo.py` - Praktické příklady použití
- `docs/NAVOD_CZ.md` - Kompletní český návod

### Rozšíření UI Designeru:
- **Icon Palette** má nové tlačítko **"Export Bitmap"**
- Automaticky hledá PNG ikony v `assets/icons/`
- Floyd-Steinberg dithering pro nejlepší kvalitu
- Deduplikace ikon (30-50% úspora paměti)

---

## 🚀 Použití v UI Designeru

### 1. Příprava PNG ikon

```bash
# Vytvoř složku pro ikony
mkdir -p assets/icons

# Přidej PNG ikony (16x16 nebo 24x24 px)
# Pojmenuj je podle Material Icons symbolů
cp wifi_icon.png assets/icons/mi_network_wifi_24px.png
cp battery.png assets/icons/mi_battery_full_24px.png
cp home.png assets/icons/mi_home_24px.png
```

### 2. Otevři UI Designer

```bash
python run_designer.py
```

### 3. Icon Palette

1. **Menu → Tools → Icon Palette** (nebo `F7`)
2. **Vyber ikonu** ze seznamu (např. "WiFi")
3. Klikni **"Export Bitmap"**

**Co se stane:**
- ✅ Designer automaticky najde `assets/icons/mi_network_wifi_24px.png`
- ✅ Zeptá se na velikost (16x16 nebo 24x24)
- ✅ Aplikuje Floyd-Steinberg dithering
- ✅ Vygeneruje C header soubor
- ✅ Uloží do `output/icon_wifi_16x16.h`

**Pokud PNG chybí:**
- Designer nabídne ASCII fallback export
- Můžeš dodat PNG později

---

## 🔧 Použití z Pythonu

### Export více ikon najednou

```python
from ui_designer_image_tools import IconBitmapExporter
from pathlib import Path

# Vytvoř exporter s automatickou deduplikací
exporter = IconBitmapExporter()

# Přidej všechny ikony ze složky
for icon_file in Path("assets/icons").glob("*.png"):
    name = icon_file.stem  # např. "mi_home_24px"
    exporter.add_icon_from_file(str(icon_file), name, size=16)

# Vygeneruj C header
exporter.export_to_header("output/ui_icons.h")

# Statistiky
stats = exporter.get_stats()
print(f"Celkem ikon: {stats['total_icons']}")
print(f"Unikátních bitmap: {stats['unique_bitmaps']}")
print(f"Úspora paměti: {stats['memory_saved_percent']}%")
```

**Výstup v `ui_icons.h`:**
```c
#pragma once
#include <stdint.h>

/* Icon bitmaps (XBM format, deduplicated) */
static const unsigned char icon_bitmap_abc123[] = {
    0x00, 0xa4, 0xda, 0xff, 0x40, 0x49, 0xb5, 0xfa,
    // ... bitmap data
}; /* 16x16, 32 bytes */

// Reference definice
#define ICON_MI_HOME_24PX icon_bitmap_abc123
#define ICON_MI_WIFI_24PX icon_bitmap_def456
```

---

### Export BDF fontu

```python
from ui_designer_image_tools import FontExporter

# Načti BDF font
font_exporter = FontExporter()
font_exporter.load_font("fonts/terminus-12.bdf", "terminus")

# Export pouze znaků, které potřebuješ (úspora paměti!)
menu_text = "Home Settings WiFi Battery"
font_exporter.export_font_subset(
    "terminus", 
    menu_text,
    "output/ui_font.h"
)
```

---

## 📁 Struktura projektu

```
ESPOS/
├── assets/
│   └── icons/              # PNG ikony (16x16, 24x24)
│       ├── mi_home_24px.png
│       ├── mi_wifi_24px.png
│       └── mi_battery_24px.png
│
├── fonts/                  # BDF fonty
│   ├── terminus-12.bdf
│   └── spleen-8x16.bdf
│
├── tools/
│   ├── image_dithering.py  # Floyd-Steinberg dithering
│   ├── xbmp_dedup.py       # Deduplikace ikon
│   ├── bdf_font.py         # BDF parser
│   ├── bdf_font_export.py  # Font export
│   └── xbm_utils.py        # Bitmap utilities
│
├── ui_designer_image_tools.py  # Integrace do UI Designeru
├── ui_designer_preview.py      # UI Designer + Icon Palette
│
├── examples/
│   └── image_tools_demo.py     # Praktické příklady
│
└── docs/
    ├── NAVOD_CZ.md             # Český návod
    └── IMAGE_TOOLS_README.md   # Kompletní dokumentace
```

---

## 🎬 Workflow: Od návrhu k C kódu

### Scénář: Menu s ikonami

**1. Vytvoř UI v Designeru**
```python
python run_designer.py
# Přidej widgety, rozmísti ikony
# Ulož jako ui_menu.json
```

**2. Export ikon pro embedded**
```python
from ui_designer_image_tools import cli_export_icons

cli_export_icons(
    icon_dir="assets/icons",
    output_file="components/ui/menu_icons.h",
    size=16
)
```

**3. Použij v C kódu**
```c
#include "menu_icons.h"

void draw_menu_item(const char* text, int x, int y, const unsigned char* icon) {
    // Vykresli ikonu (16x16)
    display_draw_bitmap(x, y, icon, 16, 16);
    
    // Vykresli text vedle
    display_draw_text(x + 20, y + 4, text);
}

void draw_main_menu() {
    draw_menu_item("Home", 10, 10, ICON_MI_HOME_24PX);
    draw_menu_item("WiFi", 10, 30, ICON_MI_WIFI_24PX);
    draw_menu_item("Battery", 10, 50, ICON_MI_BATTERY_24PX);
}
```

---

## 🛠️ CLI Commands

### Export ikon z příkazové řádky

```bash
# Export všech PNG ikon z assets/icons na 16x16
python -c "from ui_designer_image_tools import cli_export_icons; \
           cli_export_icons('assets/icons', 'output/icons.h', 16)"

# Výstup:
# [OK] Exported 12 icons to output/icons.h
#      Unique bitmaps: 8
#      Memory saved: 33%
```

### Export fontu

```bash
# Export celého fontu (ASCII printable)
python -c "from ui_designer_image_tools import cli_export_font; \
           cli_export_font('fonts/terminus-12.bdf', 'output/font.h')"

# Export pouze použitých znaků (úspora paměti)
python -c "from ui_designer_image_tools import cli_export_font; \
           cli_export_font('fonts/terminus-12.bdf', 'output/font.h', 'Hello World')"
```

---

## 📚 Další informace

### Dokumentace:
- **Český návod**: `docs/NAVOD_CZ.md`
- **Kompletní docs**: `docs/IMAGE_TOOLS_README.md`
- **Demo příklady**: `examples/image_tools_demo.py`

### Spusť demo:
```bash
python -m examples.image_tools_demo
```

### Najdi BDF fonty:
```python
from ui_designer_image_tools import find_bdf_fonts

fonts = find_bdf_fonts()
for font in fonts:
    print(font)
```

### Zdoje BDF fontů:
- **X11 Fonts**: `/usr/share/fonts/X11/misc/` (Linux)
- **GNU Unifont**: http://unifoundry.com/unifont/
- **Spleen**: https://github.com/fcambus/spleen
- **TTF → BDF**: `otf2bdf -p 12 myfont.ttf -o myfont.bdf`

---

## ✅ Hotovo!

Nyní máš plně integrované bitmap nástroje v UI Designeru:

1. ✅ **Icon Palette** s "Export Bitmap" tlačítkem
2. ✅ Floyd-Steinberg dithering (nejlepší kvalita)
3. ✅ Automatická deduplikace (30-50% úspora)
4. ✅ BDF font support
5. ✅ CLI příkazy pro automatizaci
6. ✅ Kompletní dokumentace v češtině

**Next steps:**
- Přidej PNG ikony do `assets/icons/`
- Vyzkoušej export v Icon Palette
- Integruj C header do embedded projektu
