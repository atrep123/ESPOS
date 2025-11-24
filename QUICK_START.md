# Rychlý start

## Nejrychlejší cesta k funkčnímu UI Designeru

### 1. Spusť Workspace (doporučeno)

```bash
python esp32os_workspace.py
```

**Co to dělá:**

- Otevře jednoduchou aplikaci s tlačítky
- Klikni na „🔗 Oba“ – spustí Designer i Simulátor vedle sebe
- „⟳ Restart“ rychle oba procesy ukončí a znovu spustí (čisté prostředí)
- „■ Stop“ vše korektně ukončí
- Vytvoříš UI v Designeru a okamžitě ho vidíš v Simulátoru

### 2. Nebo spusť ručně

```bash
# Designer
python ui_designer_pro.py

# Simulátor (v druhém terminálu)
python scripts/sim_run.py --rpc-port 8765
```

## První spuštění (jednou)

```bash
# Přesune testovací soubory do složky test/
python cleanup_project.py
```

## Základní příkazy

### Testování

```bash
# Všechny testy
python -m pytest test/

# Jen rychlé testy
python -m pytest test/ -m "not slow"
```

### Formátování kódu

```bash
# Automatické formátování
black .

# Kontrola chyb
ruff check .

# Oprava chyb automaticky
ruff check --fix .
```

### (Volitelné) starší build EXE

Projekt teď běží čistě v Pythonu (doporučeno). Pokud chceš experimentovat s buildem:

```bash
pyinstaller build/ui_designer_pro.spec --clean
```

## Struktura projektu (kam co patří)

```text
ESPOS/
  ui_designer_pro.py        – hlavní aplikace (tady začni)
  ui_designer.py            – jádro editoru
  design_tokens.py          – barvy, spacing, fonty
  ui_themes.py              – témata
  ui_components.py          – komponenty (tlačítka, dialogy…)
  ui_animations.py          – animace

  scripts/                  – spouštěcí skripty
    sim_run.py              – simulátor

  tools/                    – pomocné nástroje
    ui_export_c_header.py   – export do C kódu

  test_*.py                 – testy
  examples/                 – ukázkové soubory
  assets/                   – ikony, fonty
  build/                    – build konfigurace (PyInstaller spec)
```

## Co dělat když…

### …chci přidat nový widget typ

1. Otevři `ui_designer.py`
2. Přidej do `WidgetType` enum (řádek ~127)
3. Přidej vykreslování do `render_*` funkcí

### …chci změnit barvy/spacing

1. Otevři `design_tokens.py`
2. Uprav `ColorTokens` nebo `SpacingTokens`

### …jsem pokazil něco a testy nejdou

```bash
# Zjisti, co je rozbité
python -m pytest -v --tb=short --maxfail=5

# Vrátit změny v gitu
git status
git checkout -- <soubor>
```

### …chci novou funkcionalitu

1. Napiš test v `test_*.py`
2. Implementuj v příslušném souboru
3. Spusť testy: `python -m pytest`

### …chci upravit mřížku (grid) v Preview

V okně Preview (ovladače „Pad %“ a „Min px“ na horní liště) nastavíš okrajovou mezeru mřížky.
Hodnoty se ukládají do dočasného nastavení a přežijí další spuštění.

- `Pad %` – procento velikosti kroku mřížky použité jako odsazení od okraje.
- `Min px` – minimální počet pixelů odsazení (přebije malé procento).

Při vysokém kontrastu (HC UI) se mřížka přepne na světlejší barvu.

## Debug režim

```python
# V ui_designer_pro.py na začátku přidej:
import os
os.environ["ESP32OS_DEBUG"] = "1"
```

## Časté problémy

### Import errors při testech

✔ Ošetřeno v `conftest.py` (přidává scripts/ a tools/ do cesty).

### PyInstaller build selhává

✔ Zkontroluj `build/ui_designer_pro.spec` – musí obsahovat všechny moduly.

### Tkinter nefunguje

✔ Nastav `ESP32OS_HEADLESS=1` pro testování bez GUI.

---

**Tip:** Když si nevíš rady, podívej se do složky `docs/` nebo spusť testy – často ukazují, jak věci používat.
