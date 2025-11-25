# 🇨🇿 Návod k použití Image Tools

Praktický průvodce pro převod obrázků a fontů do C kódu pro ESPOS.

## 🚀 Rychlý start

### 1. Jednoduchý převod ikony PNG → C kód

```python
from PIL import Image
from tools.image_dithering import image_to_xbm

# Načti PNG ikonu (16x16 nebo 32x32 px)
img = Image.open("icons/wifi.png").convert("L")  # převeď na šedotón
pixels = list(img.getdata())
width, height = img.size

# Převeď na 1bpp s ditheragem
w, h, bitmap = image_to_xbm(
    [pixels[i:i+width] for i in range(0, len(pixels), width)],
    width, height,
    dither_method="floyd-steinberg"  # nejlepší kvalita
)

# Vygeneruj C kód
print(f"static const uint8_t wifi_icon[] = {{")
for i, byte in enumerate(bitmap):
    if i % 12 == 0:
        print("    ", end="")
    print(f"0x{byte:02x}", end=", " if i < len(bitmap)-1 else "")
    if (i+1) % 12 == 0:
        print()
print("\n};")
```

**Výstup:**
```c
static const uint8_t wifi_icon[] = {
    0x00, 0xa4, 0xda, 0xff, 0x40, 0x49, 0xb5, 0xfa,
    0x00, 0x94, 0xea, 0xff, 0x20, 0xa1, 0x5a, 0xed,
    // ... další byty
};
```

---

### 2. Více ikon najednou (s úsporou paměti 30-50%)

```python
from PIL import Image
from tools.xbmp_dedup import XBMPManager

# Vytvoř správce s automatickou deduplikací
xbmp = XBMPManager(default_dither="floyd-steinberg")

# Přidej všechny ikony ze složky
from pathlib import Path
for icon_path in Path("ui/icons").glob("*.png"):
    img = Image.open(icon_path).resize((16, 16)).convert("L")
    xbmp.add_icon_from_pil(img)  # automaticky deduplikuje

# Vygeneruj C kód (duplicity sdílí stejné pole)
c_code = xbmp.generate_c_code()
print(c_code)

# Ulož do souboru
Path("components/ui/icons.h").write_text(c_code)
```

**Výhody:**
- ✅ Automatická deduplikace (stejné ikony = jedno pole v paměti)
- ✅ Úspora 30-50% Flash paměti
- ✅ MD5 hash kontrola
- ✅ Komentáře s rozměry a velikostí

---

### 3. Vykreslení textu (BDF fonty)

```python
from tools.bdf_font import BDFFont
from tools.bdf_font_export import export_font_subset

# Načti BDF font (např. z X11 nebo Unifont)
font = BDFFont.load("fonts/terminus-12.bdf")

# Vykresli text do bitmappy
text = "Hello ESPOS!"
width, height, bitmap = font.render_text(text, spacing=1)

# Export pouze použitých znaků (úspora paměti)
c_code = export_font_subset(font, text, "hello_font")
print(c_code)
```

**Export obsahuje:**
- Struktury `BdfGlyph` a `BdfFont`
- Pouze znaky použité v textu (ne celý font!)
- Optimalizované bitmap pole
- Metadata (width, height, baseline)

---

### 4. Bitmap efekty

```python
from tools.xbm_utils import (
    xbm_pixelate,    # mosaic efekt
    xbm_scale,       # zvětšení 2x, 3x, ...
    xbm_rotate_90,   # rotace o 90°
    xbm_invert,      # inverze barev
    xbm_to_ascii     # ASCII art preview
)

# Načti bitmap (z předchozího kroku)
width, height, bitmap = image_to_xbm(pixels, 32, 32)

# Pixelate efekt (mosaic)
pixelated = xbm_pixelate(bitmap, width, height, pixel_size=4)

# Zvětšení 2x
scaled, new_w, new_h = xbm_scale(bitmap, width, height, scale_x=2, scale_y=2)

# Rotace o 90° doprava
rotated, rot_w, rot_h = xbm_rotate_90(bitmap, width, height)

# Inverze (bílá ↔ černá)
inverted = xbm_invert(bitmap, width, height)

# Zobraz ASCII preview
print(xbm_to_ascii(bitmap, width, height))
```

---

## 📋 Typické scénáře

### Scénář A: Ikony pro UI menu

```python
from pathlib import Path
from PIL import Image
from tools.xbmp_dedup import XBMPManager

# 1. Připrav ikony (16x16 px, PNG/SVG → PNG)
# 2. Načti a deduplikuj
xbmp = XBMPManager()
icons = ["wifi", "battery", "settings", "home", "back"]

for icon_name in icons:
    img = Image.open(f"assets/{icon_name}.png").resize((16,16)).convert("L")
    xbmp.add_icon_from_pil(img)

# 3. Generuj C kód
c_header = f"""
#pragma once
#include <stdint.h>

{xbmp.generate_c_code()}

// Reference na ikony
#define ICON_WIFI     icon_bitmap_0
#define ICON_BATTERY  icon_bitmap_1
// ... (podle pořadí přidání)
"""

Path("components/ui/menu_icons.h").write_text(c_header)
```

**Použití v C:**
```c
#include "menu_icons.h"

void draw_menu() {
    display_draw_bitmap(10, 10, ICON_WIFI, 16, 16);
    display_draw_bitmap(30, 10, ICON_BATTERY, 16, 16);
}
```

---

### Scénář B: Vlastní font pro displej

```python
from tools.bdf_font import BDFFont
from tools.bdf_font_export import export_font_to_c

# 1. Stáhni BDF font (např. z https://github.com/fcambus/spleen)
# 2. Načti
font = BDFFont.load("fonts/spleen-8x16.bdf")

# 3. Export CELÉHO fontu (všechny znaky)
c_code_full = export_font_to_c(font, "spleen_8x16")

# NEBO export pouze ASCII (úspora paměti)
ascii_chars = "".join(chr(i) for i in range(32, 127))
from tools.bdf_font_export import export_font_subset
c_code_ascii = export_font_subset(font, ascii_chars, "spleen_ascii")

Path("components/ui/font.h").write_text(c_code_ascii)
```

**Použití v C:**
```c
#include "font.h"

void draw_text(const char* text) {
    int x = 0;
    for (const char* p = text; *p; p++) {
        const BdfGlyph* glyph = get_glyph(*p);
        if (glyph) {
            display_draw_bitmap(x, 0, glyph->bitmap, glyph->width, glyph->height);
            x += glyph->dwidth;
        }
    }
}
```

---

### Scénář C: Logo firmy s ditheragem

```python
from PIL import Image
from tools.image_dithering import image_to_xbm

# Načti logo (může být barevné, velké)
logo = Image.open("assets/logo.png")
logo = logo.resize((128, 64)).convert("L")  # resize na displej
pixels = list(logo.getdata())

# Převeď s různými dithering metodami
methods = ["floyd-steinberg", "atkinson", "ordered", "threshold"]

for method in methods:
    w, h, bitmap = image_to_xbm(
        [pixels[i:i+128] for i in range(0, len(pixels), 128)],
        128, 64,
        dither_method=method
    )
    
    # Ulož preview
    from tools.xbm_utils import xbm_to_ascii
    ascii_art = xbm_to_ascii(bitmap, w, h)
    Path(f"output/logo_{method}.txt").write_text(ascii_art)
    
    # Vygeneruj C kód
    c_code = f"static const uint8_t logo_{method}[] = {{\n"
    for i, byte in enumerate(bitmap):
        if i % 16 == 0:
            c_code += "    "
        c_code += f"0x{byte:02x}"
        if i < len(bitmap) - 1:
            c_code += ", "
        if (i + 1) % 16 == 0:
            c_code += "\n"
    c_code += "\n};"
    
    Path(f"output/logo_{method}.c").write_text(c_code)

# Vyber nejlepší metodu podle vizuálního preview
```

**Porovnání metod:**
- **floyd-steinberg**: Nejlepší kvalita, nejpomalejší (~1ms)
- **atkinson**: Mac-style, měkčí, rychlejší
- **ordered**: Nejrychlejší, pattern-based, dobré pro textury
- **threshold**: Jednoduchý cutoff, nejrychlejší, ostrý

---

## 🛠️ Kde získat BDF fonty?

### Zdroje BDF fontů:

1. **X11 Fonts** (classic, monospace):
   ```bash
   # Na Linuxu
   sudo apt-get install xfonts-base xfonts-75dpi xfonts-100dpi
   # Fonts v: /usr/share/fonts/X11/misc/*.bdf
   ```

2. **GNU Unifont** (všechny Unicode znaky):
   - URL: http://unifoundry.com/unifont/
   - 16x16 bitmap font s ~65000 glyphů

3. **Spleen** (retro, čitelné):
   - URL: https://github.com/fcambus/spleen
   - Velikosti: 5x8, 6x12, 8x16, 12x24, 16x32, 32x64

4. **Fixed** (programmers' font):
   - Součást X11, různé velikosti
   - Např. `6x13.bdf`, `7x14.bdf`, `9x15.bdf`

### Konverze TTF → BDF:

```bash
# Nainstaluj otf2bdf
sudo apt-get install otf2bdf  # Linux
brew install otf2bdf          # macOS

# Převeď TTF na BDF
otf2bdf -p 12 -r 72 myfont.ttf -o myfont-12.bdf
```

---

## 📊 Performance tips

### Dithering rychlost (64x64 obrázek):

| Metoda          | Čas    | Kvalita |
|-----------------|--------|---------|
| threshold       | ~0.1ms | ★☆☆☆☆   |
| ordered (Bayer) | ~0.3ms | ★★★☆☆   |
| atkinson        | ~0.8ms | ★★★★☆   |
| floyd-steinberg | ~1.0ms | ★★★★★   |

### BDF rendering:

- **30,000+ renders/sec** pro krátké texty ("ABC")
- **Subsetting**: úspora ~20% paměti (export jen použitých znaků)

### XBMP deduplikace:

- **Typická úspora**: 30-50% Flash paměti
- **Instant**: MD5 hash kontrola
- **Best practice**: Použij pro všechny ikony stejné velikosti (např. 16x16)

---

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'tools'"

**Řešení:**
```bash
# Spusť jako modul z root složky projektu
cd D:\ESPOS-main\ESPOS
python -m examples.image_tools_demo
```

### Problem: Pixelate efekt vrací prázdnou bitmapu

**Důvod:** Checkerboard pattern (50/50 bílá/černá) → většinové hlasování = 50% → prázdno

**Řešení:** Použij pixelate jen na obrázky s gradientem nebo jasným vzorem:
```python
# ❌ Špatně: checkerboard
pixels = [[((x+y) % 2) * 255 for x in range(16)] for y in range(16)]

# ✅ Dobře: gradient
pixels = [[int(x * 255 / 16) for x in range(16)] for _ in range(16)]
```

### Problem: Font rendering vrací prázdnou bitmapu

**Kontrola:**
```python
font = BDFFont.load("myfont.bdf")

# Zkontroluj, že font má glyphs
print(f"Glyphs: {len(font.glyphs)}")  # mělo by být > 0

# Vyzkoušej známý znak
if ord('A') in font.glyphs:
    w, h, bmp = font.render_text("A")
    from tools.xbm_utils import xbm_to_ascii
    print(xbm_to_ascii(bmp, w, h))
else:
    print("Font nemá znak 'A'!")
```

---

## 💡 Best Practices

### 1. Příprava ikon:

- ✅ Resize na cílovou velikost PŘED ditheragem
- ✅ Použij stejné rozměry pro všechny ikony (16x16 nebo 32x32)
- ✅ Převeď na grayscale (`convert("L")`)
- ✅ Optimalizuj kontrast před ditheragem

### 2. Volba dithering metody:

- **UI ikony**: `floyd-steinberg` (nejlepší kvalita)
- **Velké obrázky**: `atkinson` (kompromis rychlost/kvalita)
- **Textury/vzory**: `ordered` (nejrychlejší, pattern-based)
- **Čárové grafiky**: `threshold` (ostrý cutoff)

### 3. Font export:

- ✅ Použij **subsetting** pro production (export jen použitých znaků)
- ✅ Pro debug použij **full export** (všechny znaky)
- ✅ Vyber font s baseline metadata pro správné zarovnání

### 4. Paměťová optimalizace:

- ✅ Vždy použij **XBMP deduplikaci** pro ikony
- ✅ Pro fonty použij **subsetting** (20% úspora)
- ✅ Sdílej bitmappy mezi instancemi (`static const`)

---

## 🎓 Další zdroje

- **Kompletní dokumentace**: `docs/IMAGE_TOOLS_README.md`
- **Příklady kódu**: `examples/image_tools_demo.py`
- **Testy**: `test_dithering_integration.py`, `test_bdf_font.py`, `test_xbm_utils.py`
- **Source code**: `tools/image_dithering.py`, `tools/bdf_font.py`, `tools/xbm_utils.py`

---

## 📞 Podpora

**Otázky?** Spusť demo příklady:
```bash
python -m examples.image_tools_demo
```

**Reportování bugů:** Vytvoř issue na GitHubu s:
- Verze Pythonu (`python --version`)
- Verze Pillow (`pip show Pillow`)
- Minimální reprodukční příklad
- Očekávané vs. skutečné chování

---

**Verze:** 1.0  
**Datum:** 25. listopadu 2025  
**Autor:** ESPOS Image Tools Team  
