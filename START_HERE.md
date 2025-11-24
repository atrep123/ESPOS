# 🎯 ESP32 OS - Jednoduchý Návod

## Co to je?

**Nástroj pro tvorbu UI pro ESP32** - máš Designer kde kreslíš rozhraní a Simulátor kde to hned vidíš běžet.

## Jak začít (3 kroky)

### 1️⃣ Ukliď projekt (jednou)

```bash
python cleanup_project.py
```

> Přesune testovací soubory do `test/` složky, aby ti nepřekážely.

### 2️⃣ Spusť Workspace

```bash
python esp32os_workspace.py
```

> Otevře se okno s tlačítky (tmavý VS Code režim).

### 3️⃣ Klikni na "🔗 Oba"

> Spustí se UI Designer i Simulátor vedle sebe.

## Co teď?

### V UI Designeru:

- Vytvoř nový widget (tlačítko, text, box...)
- Přesuň ho kam chceš
- Nastav barvy, velikost...
- Ulož projekt (`.json` soubor)

### V Simulátoru:

- Automaticky se zobrazí co jsi vytvořil v Designeru
- Vidíš jak to bude vypadat na ESP32

### Export na ESP32:

Když máš UI hotové:

```bash
python tools/ui_export_c_header.py projekt.json -o ui_screen.h
```

> Vytvoří C kód pro ESP32 firmware.

## Struktura (co kam patří)

```text
esp32os_workspace.py        ← START ZDE! (hlavní launcher)
ui_designer_pro.py          ← UI Designer (nebo použij workspace)
scripts/sim_run.py          ← Simulátor (nebo použij workspace)

design_tokens.py            ← Barvy, spacing, fonty
ui_themes.py                ← Témata (dark, light...)
ui_components.py            ← Hotové komponenty

tools/
  ui_export_c_header.py     ← Export do C kódu
  
examples/                   ← Ukázky (můžeš smazat)
test/                       ← Testy (nemusíš řešit)
```

## Řešení problémů

### "ModuleNotFoundError"

```bash
pip install pillow websockets reportlab watchdog
```

### Designer/Simulátor nejde spustit

Zkontroluj že jsi ve správné složce:

```bash
cd d:\ESPOS-main\ESPOS
python esp32os_workspace.py
```

### Chci jen Designer bez Simulátoru

V Workspace klikni jen na "🎨 UI Designer".

### Chci jen Simulátor

V Workspace klikni jen na "📱 Simulátor".

## Klávesové zkratky (v Designeru)

- `Ctrl+S` - Uložit
- `Ctrl+Z` - Zpět
- `Ctrl+Y` - Znovu
- `Delete` - Smazat widget
- `Ctrl+D` - Duplikovat widget
- Arrow keys - Posunout widget

## Co dál?

1. **Vytvoř jednoduchý projekt** - jedno tlačítko, jeden text
2. **Vyzkoušej export do C** - `python tools/ui_export_c_header.py`
3. **Podívej se do `examples/`** - jsou tam ukázky hotových UI

## Kontakt

Pokud něco nejde, podívej se do:

- `QUICK_START.md` - detailnější příkazy
- `PROJECT_OVERVIEW.md` - přehled celého projektu
- `docs/` - kompletní dokumentace

---

**💡 Tip:** Workspace je nejjednodušší způsob - jeden klik a máš vše najednou!
