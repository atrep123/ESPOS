# ESP32OS – Agent Guide (simulátor v `sim/`)

Tento soubor platí pro `sim/` – C ASCII simulátor a Python moduly v `sim/modules`.

## C simulátor (`sim/main.c`)

- Simulátor je malý C program, který:
  - používá `ui_core` ze `src/services/ui/ui_core.h`,
  - mapuje 256×128 displej do ASCII mřížky,
  - vykresluje scény a stav podobně jako reálný firmware.
- Upravuj ho tak, aby:
  - zůstal *čistě uživatelský nástroj* – nevyžaduje ESP-IDF, jen standardní C knihovnu,
  - chování bylo co nejbližší reálnému UI (`ui_state_t`, scény, barvy).

### Styl

- Drž se stejného stylu jako v `src/`:
  - 4 mezery, `static` pro interní funkce,
  - žádné globální proměnné navíc, pokud to není nutné.
- Zachovej rozdělení na:
  - pomocné funkce (barvy, vstup z klávesnice),
  - `render_frame_sim`,
  - `main` smyčku.

## Python scaffolding (`sim/modules/*`)

- `sim/modules/renderer.py` je *scaffolding* pro budoucí refaktor `sim_run.py`.
- Při práci s ním:
  - udrž API jednoduché (`start()`, `stop()`, konstruktor s `port`/`width`/`height`),
  - neměň signatury, dokud není potřeba refaktor v `sim_run.py`.

## Integrace s ostatními částmi

- C simulátor (`sim/main.c`) by měl zůstávat nezávislý na Python části (`sim_run.py`), sdílí jen UI logiku přes `ui_core`.
- Pokud přidáváš novou vlastnost do `ui_state_t` nebo `ui_core`, ujisti se, že:
  - reálný firmware (`src/services/ui/ui.c`) s tím počítá,
  - případně doplníš zobrazení i v `sim/main.c` (ASCII verze).

