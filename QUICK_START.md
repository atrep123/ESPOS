# ESP32 OS UI Toolkit - Quick Start

## 🚀 Rychlé spuštění (3 možnosti)

### 1. Interaktivní launcher (nejjednodušší)
```powershell
python launcher.py
```
Zobrazí menu:
- **1** = UI Designer
- **2** = Simulator GUI  
- **3** = Workspace (oboje)
- **0** = Konec

### 2. Jednotlivé aplikace

**UI Designer** (vizuální editor):
```powershell
python run_designer.py
```

**Simulator GUI** (okno s displejem):
```powershell
python run_simulator_gui.py
```

**Workspace** (Designer + Simulator dohromady):
```powershell
python esp32os_workspace.py
```

### 3. Pokročilé (původní nástroje)

Designer s vlastním rozlišením:
```powershell
python ui_designer_pro.py --width 320 --height 240
```

Terminálový simulátor:
```powershell
python scripts/sim_run.py --rpc-port 8765
```

## 📦 Instalace (jednou)

```powershell
pip install pillow
```

**Volitelné** (pro PDF export a hot-reload):
```powershell
pip install reportlab watchdog
```

## 💡 Typický workflow

1. **Spusť Designer**
   ```powershell
   python run_designer.py
   ```

2. **Vytvoř UI**
   - Přidej widgety z levého panelu (Label, Button, Checkbox...)
   - Přetáhni na pozici (drag & drop)
   - Změň velikost za úchyty
   - Nastav vlastnosti (text, barvy...) double-clickem

3. **Ulož projekt**
   - `Ctrl+S` → uloží jako JSON

4. **Exportuj do C**
   ```powershell
   python tools/ui_export_c_header.py muj_design.json -o output/ui.h
   ```

5. **Přidej do firmware**
   - Zkopíruj `output/ui.h` do `src/`
   - Include v `main.c`
   - Build: PlatformIO → Upload

## 🎨 Ovládání UI Designeru

| Akce | Klávesa/Myš |
|------|-------------|
| Přesun widgetu | Drag myší |
| Změna velikosti | Drag handle (rohy/okraje) |
| Editace vlastností | Double-click |
| Uložit | Ctrl+S |
| Smazat | Delete |
| Posun po pixelech | Šipky ←↑→↓ |
| Export menu | File → Export |

## 📺 3 hlavní aplikace

### 🎨 UI Designer (`run_designer.py`)
**Účel**: Vizuální drag & drop editor  
**Funkce**:
- Palette widgetů (label, button, slider...)
- Properties panel
- Grid & snap
- Export: JSON, PNG, HTML, C header

### 📟 Simulator GUI (`run_simulator_gui.py`)
**Účel**: Okno s vizualizací ESP32 displeje  
**Funkce**:
- Live preview scény (128×64 nebo 320×240)
- Dark mode interface
- Reset/Pause tlačítka
- Škálované 4× pro lepší viditelnost

### 🏢 Workspace (`esp32os_workspace.py`)
**Účel**: Spustí oboje najednou  
**Funkce**:
- Unified launcher
- Správa portů (RPC 8765)
- Auto-start nastavení
- Historie projektů (`.esp32os_workspace.json`)

## 📁 Struktura projektu

```
ESPOS/
├── launcher.py              # Quick menu (START HERE)
├── run_designer.py          # UI Designer starter
├── run_simulator_gui.py     # Simulator GUI starter
├── esp32os_workspace.py     # Workspace (oboje)
├── requirements.txt         # Závislosti
│
├── preview/
│   └── window.py           # Designer GUI (dark theme)
│
├── tools/
│   └── ui_export_c_header.py  # C export tool
│
├── src/                     # ESP32 firmware (C/C++)
├── output/                  # Exporty (JSON, PNG, H...)
└── assets/                  # Ikony, fonty
```

## 🎨 Dark Mode

Všechny 3 aplikace mají dark theme automaticky:
- Pozadí: `#2b2b2b`
- Text: `#ffffff`
- Aktivní prvky: `#007ACC` (modrá)
- Pole: `#1a1a1a` (tmavší)

## ❓ Řešení problémů

### Okno se neotevře
1. Zkontroluj Python 3.x s tkinter:
   ```powershell
   python -m tkinter
   ```
2. Použij `Alt+Tab` pro přepnutí oken
3. Zkontroluj Task Manager

### Import error: PIL/Pillow
```powershell
pip install pillow
```

### Simulátor se nespustí
- Port 8765 obsazený? Změň v Workspace → Nastavení
- Zkontroluj, že `scripts/sim_run.py` existuje

### Designer je prázdný
- Počkej 2-3 sekundy na načtení
- Přidej widget z levého panelu
- Zkus `File → New` pro čistý projekt

## 🔧 Pokročilé

### Konfigurace Workspace
`.esp32os_workspace.json`:
```json
{
  "designer_width": 128,
  "designer_height": 64,
  "simulator_port": 8765,
  "auto_start_simulator": true,
  "recent_projects": ["projekt1.json", ...]
}
```

### Export parametry
```powershell
# PNG s vlastní škálou
python tools/ui_export_c_header.py design.json --png-scale 8 -o ui.h

# Jen PNG bez C
python tools/ui_export_c_header.py design.json --png-only
```

### Grid nastavení
V Preview okně:
- **Pad %** – mezera kolem mřížky (%)
- **Min px** – minimální mezera (px)

---

**Tip**: Začni s `python launcher.py` → zvol **1** pro Designer → vytvoř pár widgetů → `Ctrl+S` pro uložení!
