ESP32 OS UI TOOLKIT (ČISTÁ PYTHON VERZE)
Minimalistický UI Designer + nástroje pro export na ESP32 (bez demo scén & webového frontendu).

RYCHLÝ START:
python esp32os_workspace.py
	Spustí prostředí (Designer + případný simulátor pokud je k dispozici).

KLÍČOVÉ MODULY:
- ui_designer.py / ui_designer_pro.py – hlavní designer
- ui_models.py – datové struktury (WidgetConfig, SceneConfig…)
- design_tokens.py – barvy, typografie, spacing
- ui_themes.py – systém témat
- ui_components.py – základní komponenty
- tools/ui_export_c_header.py – export UI do C hlavičky pro firmware

TESTY:
Spusť kompletní testy:
python -m pytest test/

EXPORT NA ESP32:
python tools/ui_export_c_header.py vstup.json -o ui.h

DEPENDENCE (doporučeno):
pip install pillow reportlab watchdog

CO UŽ NENÍ SOUČÁSTÍ:
- examples/ (demo scény, ukázky)
- web_designer_frontend/ (browser / Tauri verze)
- PyInstaller build artefakty (.exe) – generují se lokálně, nejsou verzovány

POZNÁMKY:
- JSON může mít "scenes" jako dict nebo list (automaticky sjednoceno).
- Widget ID z JSON se mapuje na _widget_id interně.

Tento README byl zjednodušen: zaměřeno pouze na Python část a export.
