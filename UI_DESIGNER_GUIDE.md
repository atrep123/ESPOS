# UI Designer - Comprehensive Guide

## 🎨 Overview

Pokročilý vizuální návrháž UI pro ESP32 simulátor s podporou:
- **12 typů widgetů** (label, box, button, gauge, progressbar, checkbox, radiobutton, slider, textbox, panel, icon, chart)
- **5 border stylů** (single, double, rounded, bold, dashed)
- **Undo/Redo** s 50-level historií
- **Šablony widgetů** (6 předdefinovaných)
- **Grid & snap** pro přesné umístění
- **Auto-layout** (vertical, horizontal, grid)
- **Alignment tools** (left, right, top, bottom, center)
- **Distribution** (horizontal, vertical)
- **Multi-format export** (Python, JSON, HTML)

---

## 🚀 Quick Start

### Základní workflow

```powershell
# Spustit UI Designer
python ui_designer.py

# Vytvoř scénu
> new home_screen

# Přidej widgety
> add box 0 0 128 64
> add label 10 10 108 10 "ESP32 Dashboard"
> template button_primary 20 40
> template progress_bar 10 30

# Náhled
> preview

# Uložení
> save my_ui.json
> export my_ui.py
```

---

## 📦 Widget Types

### 1. Label
Text widget s alignmentem a styly.

```
> add label 10 10 100 10 "Hello ESP32"
> edit 0 align center
> edit 0 style bold
> edit 0 color_fg cyan
```

**Vlastnosti:**
- `text` - zobrazený text
- `align` - left, center, right
- `valign` - top, middle, bottom
- `style` - default, bold, inverse, highlight
- `color_fg`, `color_bg` - barvy

---

### 2. Box / Panel
Kontejner s borderem pro seskupování.

```
> add box 5 5 118 54
> edit 0 border_style double
> add panel 10 10 50 40
> edit 1 color_bg blue
```

**Border styly:**
- `single` - ┌─┐│└┘
- `double` - ╔═╗║╚╝
- `rounded` - ╭─╮│╰╯
- `bold` - ┏━┓┃┗┛
- `dashed` - ┄┆

---

### 3. Button
Interaktivní tlačítko.

```
> add button 20 30 40 12 "OK"
> edit 0 color_bg green
> edit 0 color_fg black
> edit 0 border_style rounded
> edit 0 align center
```

---

### 4. Progressbar
Horizontální progress indikátor.

```
> add progressbar 10 20 100 8
> edit 0 value 75
> edit 0 min_value 0
> edit 0 max_value 100
> edit 0 color_fg green
```

**Preview:**
```
┌──────────────────────────────────┐
│████████████████████░░░░░░░░░░░░░│
└──────────────────────────────────┘
```

---

### 5. Gauge
Vertikální měřič (sloupcový graf).

```
> add gauge 50 10 20 40
> edit 0 value 60
> edit 0 color_fg yellow
```

**Preview:**
```
┌────┐
│ █  │
│ █  │
│ █  │
│ █  │
│ ░  │
│ ░  │
└────┘
```

---

### 6. Checkbox
Zaškrtávací políčko.

```
> add checkbox 10 20 60 10 "Enable WiFi"
> edit 0 checked true
```

**Preview:**
```
☑ Enable WiFi
☐ Disabled option
```

---

### 7. Radiobutton
Radio button (podobný checkbox).

```
> add radiobutton 10 30 50 10 "Option A"
> edit 0 checked true
```

---

### 8. Slider
Posuvník s aktuální pozicí.

```
> add slider 10 40 100 8
> edit 0 value 50
> edit 0 min_value 0
> edit 0 max_value 100
```

**Preview:**
```
┌──────────────────────────────┐
│──────────────▓───────────────│
└──────────────────────────────┘
```

---

### 9. Chart
Sloupcový graf s datovými body.

```
> add chart 10 10 100 40
> edit 0 data_points "[10, 20, 15, 30, 25, 35]"
```

**Preview:**
```
┌────────────────┐
│    ▌           │
│    ▌    ▌   ▌ │
│ ▌  ▌ ▌  ▌ ▌ ▌ │
│ ▌  ▌ ▌  ▌ ▌ ▌ │
└────────────────┘
```

---

## 🎯 Templates

Předdefinované šablony pro rychlý start:

### title_label
```
> template title_label 0 0
```
Centrovaný nadpis (128x10, cyan, bold)

### button_primary
```
> template button_primary 20 30
```
Zelené tlačítko OK (40x12, rounded border)

### button_secondary
```
> template button_secondary 70 30
```
Červené tlačítko Cancel (40x12, rounded border)

### info_panel
```
> template info_panel 4 10
```
Modrý informační panel (120x50, double border)

### progress_bar
```
> template progress_bar 10 30
```
Zelený progress bar (100x8, 50% hodnota)

### gauge_half
```
> template gauge_half 50 20
```
Žlutý gauge (40x20, 75% hodnota)

---

## 🔧 Advanced Features

### Undo / Redo

```
> add label 10 10 50 10 "Test"
> move 0 10 5
> undo              # Vrátí move
> redo              # Znovu aplikuje move
```

**Historie:** 50 úrovní undo/redo

---

### Grid & Snap

```
> grid on           # Zapne grid overlay
> snap on           # Snap pozice na grid (4px)
> preview grid      # Náhled s gridem

> add label 13 17 50 10 "Test"
# Automaticky snapne na (12, 16)
```

---

### Auto-Layout

**Vertical layout:**
```
> add label 0 0 100 10 "Item 1"
> add label 0 0 100 10 "Item 2"
> add label 0 0 100 10 "Item 3"
> layout vertical 8
```

Result: Widgety uspořádány vertikálně se spacingem 8px

**Horizontal layout:**
```
> layout horizontal 10
```

**Grid layout:**
```
> layout grid 4
```

---

### Alignment Tools

**Zarovnat na levou hranu:**
```
> add box 10 10 50 20
> add box 25 40 50 20
> add box 15 70 50 20
> align left 0 1 2
```

**Dostupné alignmenty:**
- `left` - zarovnat vlevo
- `right` - zarovnat vpravo
- `top` - zarovnat nahoru
- `bottom` - zarovnat dolů
- `center_h` - centrovat horizontálně
- `center_v` - centrovat vertikálně

---

### Distribution

Rovnoměrně rozložit widgety:

```
> add box 10 10 30 20
> add box 60 10 30 20
> add box 110 10 30 20
> distribute horizontal 0 1 2
```

---

### Clone Widget

```
> add button 20 20 40 12 "Button 1"
> clone 0 50 0       # Klonuje s offsetem (50, 0)
> clone 0 0 20       # Další klon s offsetem (0, 20)
```

---

### Edit Properties

```
> edit 0 text "New Text"
> edit 0 value 85
> edit 0 border_style double
> edit 0 color_fg cyan
> edit 0 color_bg blue
> edit 0 align center
> edit 0 valign top
> edit 0 z_index 10
> edit 0 checked true
> edit 0 enabled false
> edit 0 visible true
```

**Všechny vlastnosti:**
- Základní: `x`, `y`, `width`, `height`
- Text: `text`, `align` (left/center/right), `valign` (top/middle/bottom)
- Vzhled: `color_fg`, `color_bg`, `style`, `border`, `border_style`
- Hodnoty: `value`, `min_value`, `max_value`
- Stavy: `checked`, `enabled`, `visible`
- Layout: `z_index`, `padding_x`, `padding_y`, `margin_x`, `margin_y`
- Speciální: `icon_char`, `data_points`

---

## 💾 Export Formáty

### 1. JSON (uložení projektu)

```
> save my_design.json
```

**Formát:**
```json
{
  "width": 128,
  "height": 64,
  "scenes": {
    "home_screen": {
      "name": "home_screen",
      "width": 128,
      "height": 64,
      "bg_color": "black",
      "widgets": [
        {
          "type": "label",
          "x": 10,
          "y": 10,
          "width": 108,
          "height": 10,
          "text": "ESP32 Dashboard",
          "border": false
        }
      ]
    }
  }
}
```

---

### 2. Python Code

```
> export my_ui.py
```

**Generovaný kód:**
```python
# Auto-generated by UI Designer
# Scene: home_screen
# Generated: 2024-11-16 14:30:00

from dataclasses import dataclass
from typing import List


@dataclass
class Widget:
    type: str
    x: int
    y: int
    width: int
    height: int
    text: str = ''
    style: str = 'default'
    color_fg: str = 'white'
    color_bg: str = 'black'
    border: bool = True
    align: str = 'left'


def create_home_screen_scene() -> List[Widget]:
    """Create home_screen scene widgets"""
    return [
        Widget(
            type='box',
            x=0,
            y=0,
            width=128,
            height=64,
            border=True,
        ),
        Widget(
            type='label',
            x=10,
            y=10,
            width=108,
            height=10,
            text='ESP32 Dashboard',
            border=False,
            align='center',
        ),
    ]


if __name__ == '__main__':
    widgets = create_home_screen_scene()
    print(f'Created {len(widgets)} widgets for home_screen scene')
```

---

### 3. HTML Preview

```
> export preview.html html
```

Vygeneruje HTML soubor s ASCII preview pro viewing v browseru.

---

## 🎓 Complete Example

### Dashboard s kompletním UI

```powershell
python ui_designer.py

# Vytvoř scénu
> new dashboard

# Hlavní kontejner
> add panel 0 0 128 64
> edit 0 border_style double
> edit 0 color_bg blue

# Nadpis
> template title_label 0 2
> edit 1 text "ESP32 System Monitor"

# CPU Gauge
> add label 10 15 30 8 "CPU:"
> edit 2 border false
> add gauge 45 15 20 35
> edit 3 value 65
> edit 3 color_fg yellow

# Memory Progressbar
> add label 10 55 30 8 "RAM:"
> edit 4 border false
> add progressbar 45 55 70 8
> edit 5 value 42
> edit 5 color_fg green

# WiFi Status
> add checkbox 75 20 45 8 "WiFi"
> edit 6 checked true

# Tlačítka
> template button_primary 10 40
> edit 7 text "Start"
> template button_secondary 70 40
> edit 8 text "Stop"

# Náhled
> preview

# Export
> save dashboard.json
> export dashboard.py
> export dashboard_preview.html html
```

**ASCII Preview:**
```
╔══════════════════════════════════════════════════════════════╗
║              ESP32 System Monitor                            ║
║                                                              ║
║  CPU:        ┌────┐     ☑ WiFi                              ║
║              │ █  │                                          ║
║              │ █  │                                          ║
║              │ █  │     ╭────────╮       ╭────────╮         ║
║              │ █  │     │ Start  │       │  Stop  │         ║
║              │ █  │     ╰────────╯       ╰────────╯         ║
║              │ ░  │                                          ║
║              │ ░  │                                          ║
║              └────┘                                          ║
║                                                              ║
║  RAM:  ┌────────────────────────────────────────┐           ║
║        │████████████████░░░░░░░░░░░░░░░░░░░░░░░░│           ║
║        └────────────────────────────────────────┘           ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🔍 Command Reference

### Scene Management
- `new <name>` - Vytvoř scénu
- `scenes` - Seznam scén
- `switch <name>` - Přepni scénu
- `list` - Seznam widgetů

### Widget Operations
- `add <type> <x> <y> <w> <h> [text]` - Přidej widget
- `template <name> <x> <y>` - Z šablony
- `clone <idx> [dx] [dy]` - Klonuj
- `move <idx> <dx> <dy>` - Posuň
- `resize <idx> <dw> <dh>` - Změň velikost
- `delete <idx>` - Smaž
- `edit <idx> <prop> <val>` - Edituj vlastnost

### Advanced
- `undo` / `redo` - Historie
- `grid on|off` - Grid
- `snap on|off` - Snap
- `layout <type> [spacing]` - Auto-layout
- `align <type> <ids...>` - Zarovnání
- `distribute <dir> <ids...>` - Distribuce

### Export
- `save <file>` - JSON
- `export <file>` - Python
- `export <file> html` - HTML
- `preview [grid]` - ASCII náhled

### Help
- `help` - Všechny příkazy
- `help <cmd>` - Detail příkazu
- `widgets` - Typy widgetů
- `templates` - Šablony

---

## 🎨 Tips & Tricks

### 1. Rychlé prototypování
```
> template info_panel 4 4
> template title_label 0 8
> template button_primary 20 45
> template button_secondary 70 45
> layout vertical 5
```

### 2. Zarovnání buttonů
```
> add button 20 40 40 12 "OK"
> add button 70 40 40 12 "Cancel"
> align top 0 1        # Stejná výška
```

### 3. Symetrické rozložení
```
> add box 10 20 30 20
> add box 50 20 30 20
> add box 90 20 30 20
> distribute horizontal 0 1 2
```

### 4. Z-index layering
```
> add panel 0 0 128 64      # Pozadí
> edit 0 z_index 0
> add label 10 10 108 10    # Popředí
> edit 1 z_index 10
```

### 5. Grid workflow
```
> grid on
> snap on
# Všechny widgety automaticky snapnou na 4px grid
```

---

## 📊 Statistics

**Supported Features:**
- ✅ 12 widget typů
- ✅ 5 border stylů
- ✅ 6 předdefinovaných šablon
- ✅ Undo/Redo (50 levels)
- ✅ Grid & Snap
- ✅ Auto-layout (3 typy)
- ✅ Alignment (6 typů)
- ✅ Distribution (2 směry)
- ✅ Multi-format export (JSON, Python, HTML)
- ✅ Clone & Edit
- ✅ Property editor (25+ vlastností)

**Code Size:** ~800 lines Python

---

## 🚀 Next Steps

Po vytvoření UI v designeru:

1. **Export Python kódu**
   ```
   > export my_ui.py
   ```

2. **Integrace do simulátoru**
   ```python
   from my_ui import create_dashboard_scene
   
   widgets = create_dashboard_scene()
   # Použij ve scéně
   ```

3. **Testování**
   ```powershell
   python sim_run.py --scene my_ui
   ```

4. **Deploy na ESP32**
   - Convert widgets → C structs
   - Render na OLED display
   - Bind na button events

---

**Happy designing! 🎨**
