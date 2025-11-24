# Přehled projektu ESP32 OS

## Co tento projekt dělá

**ESP32 OS** je komplexní vývojové prostředí pro tvorbu UI aplikací na mikrokontrolérech ESP32.

### Hlavní komponenty
1. **UI Designer** (`ui_designer_pro.py`)
   - Vizuální editor rozhraní (drag & drop)
   - Live preview
   - Export do C kódu pro ESP32
2. **Simulátor** (`scripts/sim_run.py`)
   - Testování UI bez hardware
   - WebSocket komunikace
   - Realtime preview
3. **Design System** (`design_tokens.py`, `ui_themes.py`)
   - Konzistentní barvy, spacing, fonty
   - Témata (dark, light, cyberpunk…)
   - Responsive layout
4. **Component Library** (`ui_components.py`)
   - Připravené komponenty
   - Dialogy, menu, karty, grafy…

## Aktuální stav projektu

### ✅ Co funguje dobře
- 419 testů (100 % úspěšnost)
- UI Designer s plnou funkcionalitou
- Export do C/HTML/SVG/ASCII
- Animační systém
- Responsive layout
- Build do `.exe` souboru

### 🛠️ Co by mohlo být lepší
- Některé moduly jsou stále velké (probíhá refaktoring)
- Chybí dokumentace pro některé moduly

## Nedávné vylepšení (Q4 2025)

### 🔭 Refaktoring preview modulu

Původní `ui_designer_preview.py` (6365 řádků) byl rozdělen do modulární struktury:

- `preview/settings.py` – konfigurace (42 řádků)
- `preview/rendering.py` – rendering helpery (87 řádků)
- `preview/animation_editor.py` – timeline editor (1256 řádků)
- `preview/widget_renderer.py` – vykreslování widgetů (310 řádků)
- `preview/event_handlers.py` – mouse/keyboard (155 řádků)
- `preview/overlays.py` – grid a guides (160 řádků)

**Celkem extrahováno:** ~2010 řádků do 6 modulů  
**Zbývá v hlavním souboru:** ~4355 řádků

Zpětná kompatibilita zachována.

## Technologie

- **Python 3.12**
- **Tkinter** (GUI)
- **WebSockets** (komunikace se simulátorem)
- **PyInstaller** (build exe)
- **Pytest** (testování)
- **ReportLab** (PDF export)
- **Pillow** (obrázky)

## Soubory podle důležitosti

### 🚫 Kritické (nedotýkat se bez testu)
- `ui_designer.py` – jádro aplikace
- `design_tokens.py` – celý design system
- `conftest.py` – konfigurace testů

### ⚠️ Důležité (opatrně upravovat)
- `ui_designer_pro.py` – hlavní vstupní bod
- `ui_themes.py`, `ui_components.py`, `ui_animations.py`
- `scripts/sim_run.py` – simulátor

### ✅ Bezpečně k úpravám
- `test_*.py` – testy (přidávat nové)
- `assets/` – obrázky, ikony
- `docs/` – dokumentace

## Plány do budoucna (roadmap)

Viz `docs/PROJECT_ROADMAP.md` – detailní plán na příštích několik měsíců.

**Priorita 1:** Refaktoring `ui_designer.py` (rozdělit na menší moduly)  
**Priorita 2:** GitHub Actions CI/CD  
**Priorita 3:** Bezpečnostní skenování (SARIF, SBOM)

## Rychlé metriky

```text
Řádky kódu:     ~50 000+
Testy:          419 (100 % pass rate)
Soubory:        ~150+
Python moduly:  ~80
Podporované platformy: ESP32-S3, native simulátor
```

## Kontakty & zdroje

- **Repo:** github.com/atrep123/ESPOS
- **Dokumentace:** `docs/README.md`
- **Rychlý start:** `QUICK_START.md`
- **Roadmap:** `docs/PROJECT_ROADMAP.md`

---

**Aktualizováno:** listopad 2025
