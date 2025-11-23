╔══════════════════════════════════════════════════════════════╗
║                        ESP32 OS                              ║
║               UI Designer & Simulator Suite                  ║
╚══════════════════════════════════════════════════════════════╝

HLAVNÍ APLIKACE:
═══════════════════════════════════════════════════════════════

  ui_designer_pro.exe     - Hlavní UI Designer (pokud existuje)
  ui_designer.py          - UI Designer (Python verze)
  ui_designer_preview.py  - UI Designer s live preview
  modern_ui.py            - Moderní UI toolkit

RYCHLÝ START:
═══════════════════════════════════════════════════════════════

  1. Spustit UI Designer:
     python ui_designer_pro.py
     
  2. Spustit simulátor:
     python scripts/sim_run.py --rpc-port 8765
     
  3. Spustit všechny servery:
     powershell scripts/start_servers.ps1

SLOŽKY:
═══════════════════════════════════════════════════════════════

  /scripts    - Spouštěcí skripty (run, start, launch)
  /tests      - Pytest testy (419 testů)
  /tools      - Pomocné nástroje (export, profiler, analytics)
  /docs       - Dokumentace (README, guides, roadmaps)
  /examples   - Demo soubory a ukázky
  /build      - Build konfigurace a výstupy
  
  /src        - ESP32 C/C++ zdrojové kódy
  /components - ESP32 komponenty
  /web        - Web designer frontend
  /assets     - Ikony, fonty, témata

PLATFORMIO (ESP32):
═══════════════════════════════════════════════════════════════

  platformio.ini - PlatformIO konfigurace
  /src          - Hlavní ESP32 kód
  /components   - Hardware komponenty
  /.pio         - PlatformIO build cache

KONFIGURACE:
═══════════════════════════════════════════════════════════════

  .sim_config.json        - Konfigurace simulátoru
  sdkconfig.esp32-*       - ESP32 SDK konfigurace
  build/requirements.txt  - Python dependencies

DOKUMENTACE:
═══════════════════════════════════════════════════════════════

  docs/README.md          - Hlavní dokumentace
  docs/QUICKSTART.md      - Rychlý úvod
  docs/SIMULATOR_README.md - Návod pro simulátor
  docs/PROJECT_ROADMAP.md - Plán projektu

═══════════════════════════════════════════════════════════════
Pro více informací viz docs/README.md
