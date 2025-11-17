# ESP32OS – Přehled struktury projektu

Tento dokument má hlavně pomoci lidem/agentům rychle najít „kam co patří“, aniž by museli procházet desítky souborů v kořeni.

## 1. Nejčastěji používané nástroje

- `tools/dev_hub.py` – jednoduchý „command center“:
  - spustí UI Designer,
  - spustí simulátor (`sim_run.py`),
  - spustí self-check,
  - spustí ESP32 hardware bridge.
- `sim_run.py` – hlavní textový simulátor UI (RPC/UART/WebSocket, nahrávání, metriky).
- `ui_designer.py`, `ui_designer_pro.py`, `ui_designer_preview.py` – návrh UI a vizuální náhled.

## 2. Python nástroje – logické skupiny

**Simulátor + runtime nástroje**
- `sim_run.py` – simulátor.
- `esp32_sim_client.py` – Python klient pro RPC.
- `esp32_hardware_bridge.py` – bridge mezi ESP32 UART a simulátorem.
- `state_inspector.py` – inspektor stavu (nyní využívá RPC `get_state`).

**Designer / UI**
- `ui_designer.py`, `ui_designer_pro.py` – logika designeru.
- `ui_designer_preview.py` – vizuální náhled (drag & drop, zoom, export).
- `ui_themes.py`, `ui_components.py`, `ui_animations.py`, `ui_responsive.py` – témata, komponenty, animace, responsive layout.
- `ui_export_c.py`, `ui_export_c_header.py` – export do C kódu / hlaviček.

**Výkon a analýza**
- `performance_profiler.py` – pokročilý profiler (FPS, časy, alerts, anomálie).
- `analytics_dashboard.py` – webový dashboard/analytics.

**Další nástroje**
- `multi_window_manager.py` – více instancí simulátoru.
- `screenshot_capture.py` – screenshoty a záznam.
- `simctl.py` – jednoduchý CLI klient pro simulátor.

## 3. Firmware a C část

- `src/` – hlavní ESP32 firmware:
  - `src/main.c` – `app_main`, start služeb a UI.
  - `src/display/*` – ovladače displeje.
  - `src/kernel/*` – msgbus, timery.
  - `src/services/*` – služby: `ui`, `input`, `rpc`, `store`, `metrics` atd.
- `sim/main.c` – čistý C ASCII simulátor (`ui_core` bez ESP-IDF).

## 4. Testy

- Python testy v kořeni:
  - `test_*.py` – end-to-end a funkční testy (export, designer, simulátor, profiler).
  - `test/unit/*.py` – menší unit testy (klient, helpery, self-check).
- C testy:
  - `test/test_ui_core/test_ui_core.c` – Unity testy pro `ui_core`.
  - `test/test_ui_render_swbuf/test_ui_render_swbuf.c` – test SW framebuffer rendereru.

## 5. Dokumentace a mapy

- `docs/INDEX.md` – hlavní index dokumentace (propojuje README, QUICKSTART, SIMULATOR_README, atd.).
- `FILE_INDEX.md` – podrobný index souborů s počty řádků a účelem.
- `IMPLEMENTATION_SUMMARY.md` – souhrn implementace (moduly, funkce).
- `SIMULATOR_README.md`, `SIMULATOR_EXAMPLES.md`, `UI_DESIGNER_GUIDE.md` – uživatelská dokumentace.

## 6. Jak to „mentálně“ skládat dohromady

- **Návrh UI** – vše kolem designeru (`ui_designer_*`, `ui_themes`, `ui_components`, `ui_animations`, `ui_responsive`).
- **Simulace & běh** – `sim_run.py`, `esp32_sim_client.py`, `state_inspector.py`, `esp32_hardware_bridge.py`.
- **Firmware** – `src/` + generované C hlavičky z exportu.
- **Nástroje / Dev** – `tools/` (Dev Hub, self-check, CI skripty), `docs/`.

Pokud něco potřebuješ, je dobré začít:
- `tools/dev_hub.py` pro běžné úkony,
- `docs/INDEX.md` pro rychlý rozcestník,
- `FILE_INDEX.md` pokud hledáš konkrétní soubor / modul.

