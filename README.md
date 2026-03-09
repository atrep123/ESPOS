# ESP32OS UI Toolkit

Repo je záměrně osekaný na “embedded OS UI” cestu:

- Pygame UI Designer (tvorba UI pro MCU bez dotyku)
- Export JSON → C (`UiScene`/`UiWidget` dle `src/ui_scene.h`)
- Firmware runtime pro SSD1363 (256×128, 4bpp gray), ovládání joystickem / enkodéry

## Designer

```powershell
python -m pip install -r requirements.txt
python run_designer.py main_scene.json --profile esp32os_256x128_gray4
```

Tip: `Ctrl+F` = Fit Text, `Ctrl+Shift+F` = Fit Widget, `F3` = overflow warnings, `F2` = input simulation mode (D-pad/encoder).

## Export do C (header)

```powershell
python tools/ui_export_c_header.py main_scene.json -o ui_scene_generated.h
```

Firmware můžeš buď:
- includnout `ui_scene_generated.h` a použít exportovanou `UiScene`, nebo
- nahradit demo `src/ui_design.c`/`src/ui_design.h` vlastním exportem (podle toho, jak to chceš integrovat).

## Runtime bindings (hodnotové editory)

Designer widgety mohou mít pole `runtime`, které se exportuje do `UiWidget.constraints_json`.
UI runtime pak umí jednoduché editory bez dotyku (A/encoder = edit, Up/Down = změna):

- `bind=contrast;kind=int;min=0;max=255;step=8`
- `bind=invert;kind=bool;values=off|on`
- `bind=col_offset;kind=int;min=0;max=16;step=1`

## PlatformIO build

```powershell
pio run -e arduino_nano_esp32-nohw
pio run -e esp32-s3-devkitm-1-nohw
```

Poznámka:
- PlatformIO verze jsou v repu připnuté záměrně kvůli reprodukovatelným buildům a stabilním `sdkconfig`.
- `pio test -e native` vyžaduje host C compiler dostupný v `PATH`.
- Na Windows to znamená mít v `PATH` `gcc` (napr. MSYS2/MinGW-w64). Pokud `gcc` chybí, `scripts/check_all_local.ps1` native testy přeskočí s varováním.
- Rychlá cesta na Windows: `winget install -e --id MSYS2.MSYS2`, pak v MSYS2 shellu `pacman -S --needed mingw-w64-ucrt-x86_64-gcc` a přidat `C:\msys64\ucrt64\bin` do `PATH`.
- Na Windows může lokální policy zablokovat některé ESP-IDF toolchain binárky.
- Pokud native testy padají na `WinError 4551`, problém je host policy (App Control), ne kód testu; použij `scripts/check_all_local.ps1 -Fast` (tolerant) nebo povol běh `.pio\\build\\native` test binárek.
- `scripts/check_all.ps1` v režimu `-AllowNativePolicyBlock` po opakovaném policy failu automaticky spustí krátký `check_native_policy_probe.ps1`, aby vypsal blokované suites.
- Ve stejném kroku uloží i JSON artefakt `reports/native_policy_probe_auto.json` (lze změnit přes `-NativePolicyProbeJson` nebo vypnout prázdnou hodnotou).
- Pokud se probe nespusti (zadny opakovany policy fail), zapise se placeholder JSON se stavem `Triggered=false`, aby artefakt existoval konzistentne po kazdem behu.
- Po kazdem behu s `-AllowNativePolicyBlock` se navic appendne JSONL historie do `reports/native_policy_probe_history.jsonl` (lze zmenit parametrem `-NativePolicyHistoryJsonl`).
- Pro rychlé vypsání konkrétních whitelist targetů použij `scripts/list_native_whitelist_targets.ps1`.
- Pro rozpad podle jednotlivých native suites (co je `PASSED` vs `POLICY_BLOCK`) použij `scripts/check_native_policy_probe.ps1`.
- Probe podporuje retry: `scripts/check_native_policy_probe.ps1 -MaxAttemptsPerSuite 3 -DelaySeconds 2`.
- Probe podporuje i cileny flaky-check: `scripts/check_native_policy_probe.ps1 -Suites test_ui_render_swbuf -Rounds 5 -MaxAttemptsPerSuite 3 -DelaySeconds 1`.
- Probe umi ulozit strojove citelny report: `scripts/check_native_policy_probe.ps1 -JsonOut reports/native_policy_probe_latest.json`.

## Quick checks

```powershell
scripts/check_all.ps1
scripts/check_all_local.ps1 -Fast
scripts/check_native_toolchain.ps1
scripts/list_native_whitelist_targets.ps1
scripts/check_native_policy_probe.ps1
```

```bash
./scripts/check_all_local.sh main_scene.json
./scripts/check_native_toolchain.sh
```

## Repo docs

- `AGENTS.md` (work guide)
- `FILE_INDEX.md` (project map)
- `IMPLEMENTATION_SUMMARY.md` (architecture)

## SSD1363 bring-up (volitelné)

- Debug přepínače: `src/user_config.h` (`SSD1363_I2C_SCAN_ON_BOOT`, `SSD1363_BOOT_TEST_PATTERN`).
- Pokud je obraz posunutý, dolaď `SSD1363_COL_OFFSET` a/nebo `SSD1363_INIT_DISPLAY_OFFSET` v `src/user_config.h`.
