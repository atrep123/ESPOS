# ESP32OS – Agent Guide

This file is for AI / tooling that upravuje tenhle projekt. Platí pro celý repozitář.

## Struktura projektu (pro rychlou orientaci)

- Python simulátor a nástroje:
  - `sim_run.py` – hlavní textový simulátor (RPC, UART, WebSocket, recording).
  - `esp32_sim_client.py` – Python klient pro RPC.
  - `esp32_hardware_bridge.py` – bridge mezi ESP32 (UART) a simulátorem.
  - `ui_designer.py`, `ui_designer_preview.py`, `ui_designer_pro.py` – návrh UI, vizuální editor.
  - `ui_themes.py`, `ui_components.py`, `ui_animations.py`, `ui_responsive.py` – advanced UI systémy.
  - `performance_profiler.py`, `analytics_dashboard.py` – profilování a analytika.
- C/ESP32 firmware:
  - `src/main.c` – ESP32 aplikace.
  - `src/display/*` – driver displeje.
  - `src/kernel/*` – msgbus, timery.
  - `src/services/*` – UI, input, metrics, RPC atd.
- Dokumentace / mapy:
  - `IMPLEMENTATION_SUMMARY.md` – přehled funkcí a modulů.
  - `FILE_INDEX.md` – index souborů (doporučeno číst před většími změnami).
  - `SIMULATOR_README.md`, `SIMULATOR_EXAMPLES.md`, `QUICKSTART.md` – uživatelská dokumentace.

## Styl a principy úprav

- Udržuj změny **lokální a minimální** – neměň API ani rozhraní, pokud to není nezbytné.
- Respektuj existující styl:
  - Python: PEP8, 4 mezery, funkční typové anotace tam, kde už existují.
  - C: klasický embedded styl, žádné C99 exotiky navíc proti tomu, co už projekt používá.
- Nepřidávej frameworky; používej standardní knihovnu nebo už existující závislosti (`requirements.txt`, `pyproject.toml`).
- Při refaktoringu vždy:
  - zachovej CLI rozhraní (`argparse` parametry),
  - zachovej existující JSON/RPC protokol a jejich klíče.

## Testování a ověřování

- Základní Python testy:
  - `pytest -q` v kořeni projektu.
  - Pro rychlé ověření konkrétních částí používej jednotlivé testy (např. `pytest -q test_ui_designer_pro.py`).
- Simulátor:
  - Manuálně: `python sim_run.py --rpc-port 8765 --auto-size` (nutné jen mimo CI).
- Nesahej na testy, které procházejí, pokud to není nutné – repo má poměrně bohaté integrační testy, opírej se o ně.

## Tipy pro práci agenta

- Před větší úpravou:
  - projdi `IMPLEMENTATION_SUMMARY.md` a `FILE_INDEX.md` pro kontext,
  - zkontroluj, jestli už neexistuje nástroj nebo helper, který daný problém řeší.
- Při přidávání funkcí:
  - preferuj přidání nové malé funkce / metody vedle souvisejícího kódu,
  - vyhýbej se „magickým“ globálům a skrytým side‑effectům.
- Při změnách GUI nástrojů (`ui_designer_*`):
  - drž callbacky a logiku v existujících třídách (např. `VisualPreviewWindow`),
  - u nových interakcí (drag/drop, klávesy) využij stávající vzory (_on_mouse_*, _on_*).

## Co nedělat

- Neměň build systém (CMake/ESP-IDF/PlatformIO) bez explicitního důvodu.
- Nepřidávej nové externí služby (DB, web servery) – projekt je cíleně „lightweight“.
- Neměň existující porty a protokol simulátoru, pokud není v zadání explicitně požadováno.

Tento soubor má usnadnit AI/agentům bezpečné a konzistentní úpravy kódu. Při pochybnostech preferuj nejmenší možnou změnu, která splní požadavek uživatele.

