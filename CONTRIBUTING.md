# Contributing

Repo je záměrně osekaný na “embedded OS UI” cestu (Pygame designer + export do C + firmware runtime).

## Setup

- Virtualenv: `python -m venv .venv` a aktivace (`.venv\\Scripts\\activate` / `source .venv/bin/activate`).
- Runtime deps: `python -m pip install -r requirements.txt`
- Dev deps (volitelné): `python -m pip install -r requirements-dev.txt`

## Běžné příkazy

- Designer: `python run_designer.py main_scene.json --profile esp32os_256x128_gray4`
- Export: `python tools/ui_export_c_header.py main_scene.json -o ui_scene_generated.h`
- Python testy: `python -m pytest -q`
- Firmware testy (host): `pio test -e native`
- Firmware build (bez HW): `pio run -e arduino_nano_esp32-nohw`
- Native preflight (Windows): `scripts/check_native_toolchain.ps1`

## Poznamky k native testum (Windows)

- `pio test -e native` potrebuje mit `gcc` v `PATH`.
- Pokud `gcc` chybi, `scripts/check_all_local.ps1` v tolerantnim rezimu native test preskoci a vypise varovani.
