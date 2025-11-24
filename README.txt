ESP32 OS UI TOOLKIT
===================

Visual UI Designer + Simulator + Export Tools pro ESP32

🚀 HLAVNÍ APLIKACE
==================

1. UI DESIGNER (Drag & Drop Editor)
   python run_designer.py
   
   - Vizuální editor s drag & drop
   - Dark mode interface
   - Real-time preview
   - Export do JSON/HTML/PNG/C

2. SIMULATOR (Visual Display)
   python run_simulator_gui.py
   
   - Vizuální okno s ESP32 displejem
   - Live preview z designeru
   - Dark mode interface
   - 128×64 nebo 320×240

3. WORKSPACE (Unified Launcher)
   python esp32os_workspace.py
   
   - Spustí obě aplikace najednou
   - Správa projektů
   - Unified dark theme

📦 ZÁVISLOSTI
=============

pip install pillow

⚙️ EXPORT DO C
==============

python tools/ui_export_c_header.py design.json -o ui.h

Vygeneruje C hlavičku pro ESP32 firmware.

🎨 DALŠÍ NÁSTROJE
=================

- ui_designer_pro.py - Rozšířená verze s animacemi
- design_tokens.py - Barvy a styling
- ui_models.py - Datové struktury

📁 STRUKTURA
============

/preview/          - GUI preview komponenty
/tools/            - Export a utility skripty
/src/              - ESP32 firmware (C)
/components/       - ESP32 komponenty
platformio.ini     - ESP32 build konfigurace
