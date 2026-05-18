# ESP32OS UI Toolkit
> **English summary** — full docs below are in Czech.

Embedded "OS UI" toolkit for ESP32-S3 with an SSD1363 OLED display (256×128, 4-bit grayscale). The pipeline:

1. **Pygame Designer** — visual scene editor on PC (`run_designer.py`)
2. **JSON scene** — `main_scene.json` is the source of truth
3. **C code-gen** — JSON → `UiScene`/`UiWidget` structs (auto-generated `src/ui_design.c|h`)
4. **Firmware runtime** — focus-based navigation (D-pad / encoder), value editors via `runtime` bindings

### Quick start

```bash
# Install Python deps
python -m pip install -r requirements.txt

# Launch the visual designer
python run_designer.py main_scene.json --profile esp32os_256x128_gray4

# Export to C header
python tools/ui_export_c_header.py main_scene.json -o ui_scene_generated.h

# Integrated build/flash (PlatformIO is a bundled dependency — see
# requirements.txt; no separate toolchain install). Regenerates codegen
# from the design, then drives the REAL `pio run`:
python tools/build.py check                 # verify the toolchain
python tools/build.py build                 # build reference board firmware
python tools/build.py build m5stickc-plus   # build a specific registry board
python tools/build.py flash --port COM5     # build + real upload to hardware

# (equivalent low-level PlatformIO build, no hardware)
pio run -e esp32-s3-devkitm-1-nohw

# Lint & test
python -m ruff check .
python -m pytest -q --ignore=output
```

### Widget types

label, button, panel, box, textbox, checkbox, radiobutton, progressbar, slider, gauge, toggle, list, chart, icon — see the table below for details.

### Key directories

| Path | Purpose |
|------|---------|
| `cyberpunk_designer/` | Pygame-based visual scene editor |
| `ui_models.py` / `ui_designer.py` | Core data model & persistence |
| `tools/` | Export & validation utilities |
| `src/` | ESP32 firmware (C, PlatformIO) |
| `schemas/` | JSON schema for design files |
| `espos_mcp/` | MCP server exposing the toolkit to any MCP client |
| `tests/` | Python test suite (pytest) |

### MCP server (drive espos from an automation/agent layer)

`espos_mcp/` is a [Model Context Protocol](https://modelcontextprotocol.io)
server (stdio transport, built on the official `mcp` Python SDK) that exposes
the **real** toolkit — scene/widget CRUD, the events/rules logic model, the
board registry, the schema validator, C/SVG export, and the integrated
PlatformIO build/flash — as well-typed tools. Every tool is a thin wrapper
over a genuine espos library function; nothing is simulated.

```bash
# Install the optional MCP dependency (separate from core requirements.txt)
python -m pip install -r requirements-mcp.txt

# Inspect the tool inventory (no server loop)
python -m espos_mcp --list-tools

# Run the server (an MCP client spawns this and talks to it over stdio)
python -m espos_mcp
```

Tools: `list_scenes`, `get_scene`, `add_scene`, `delete_scene`, `add_widget`,
`set_widget`, `delete_widget`, `set_widget_event`, `add_rule`, `list_boards`,
`set_board`, `validate_design`, `export_c`, `export_svg_scene`,
`toolchain_status`, `build`, `flash`. Each operates on a design JSON path
argument (default `main_scene.json`); mutations are schema-validated with the
real validator and written atomically.

Point any MCP client at it with this generic config (Šumílek is one such
client — configure it on the client side; espos stays generic and never
couples to it):

```jsonc
{
  "mcpServers": {
    "espos": {
      "command": "python",
      "args": ["-m", "espos_mcp"],
      // Run from the espos repo root (or an absolute path to it) so the
      // server resolves designs and the bundled toolchain correctly.
      "cwd": "/absolute/path/to/espos"
    }
  }
}
```

If `python` is not the interpreter that has the deps, use its absolute path
(e.g. the project venv's `python`/`python.exe`) as `command`.

---
Repo je záměrně osekaný na “embedded OS UI” cestu:

- Pygame UI Designer (tvorba UI pro MCU bez dotyku)
- Export JSON → C (`UiScene`/`UiWidget` dle `src/ui_scene.h`)
- Firmware runtime pro SSD1363 (256×128, 4bpp gray), ovládání joystickem / enkodéry

## Typy widgetů

| Widget | Popis | Klíčové vlastnosti |
|--------|-------|--------------------|
| `label` | Textový popisek | `text`, `align`, `valign` |
| `button` | Tlačítko s textem | `text`, fokusovatelné |
| `panel` | Kontejner/pozadí | `border`, `border_style` |
| `box` | Dekorativní rámeček | alias pro panel |
| `textbox` | Editovatelné textové pole | `text`, podtržení |
| `checkbox` | Zaškrtávací políčko | `checked` (bool) |
| `radiobutton` | Přepínač (radio) | `checked` (bool) |
| `progressbar` | Ukazatel průběhu | `value`, `min_value`, `max_value` |
| `slider` | Posuvník pro nastavení hodnoty | `value`, `min_value`, `max_value` |
| `gauge` | Kruhový/obloukový ukazatel | `value`, `min_value`, `max_value` |
| `toggle` | Přepínač (on/off) | `checked` (bool), `text` |
| `list` | Scrollovatelný seznam | `items`, `value` (aktivní index) |
| `chart` | Sloupcový/čárový graf | `data_points`, `chart_mode` (bar/line) |
| `icon` | Ikona s textem | `text` (znak/kód ikony) |

## Designer

```powershell
python -m pip install -r requirements.txt
python run_designer.py main_scene.json --profile esp32os_256x128_gray4
```

Tip: `Ctrl+F` = Fit Text, `Ctrl+Shift+F` = Fit Widget, `F3` = overflow warnings, `F2` = input simulation mode (D-pad/encoder), `Ctrl+/` = quick-ref panel, `Tpl` toolbar button = template picker.

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

### Integrovaný build/flash (jedna aplikace)

PlatformIO je **bundlovaná závislost** projektu (`requirements.txt`,
`platformio>=6.1,<7`) — žádná samostatná instalace toolchainu. Tím je
„kompilátor je součást aplikace“ doslova pravda. `tools/build.py` je
knihovna + CLI, která: (a) přegeneruje `src/ui_design.{c,h}` ze scény
stejným `tools.ui_codegen` jako pio pre-script, (b) spustí **skutečné**
`python -m platformio run -e <env>` a vrátí cestu k firmwaru + RAM/Flash
využití, (c) `flash` = build + reálné `-t upload` (port auto-detekce přes
`pio device list`).

```powershell
python tools/build.py check                  # ověří toolchain (pio)
python tools/build.py boards                 # board id -> pio env mapa
python tools/build.py build                  # referenční deska
python tools/build.py build m5stamp-c6lora   # konkrétní deska z boards.json
python tools/build.py flash --port COM5      # build + reálný upload
```

Mapování `board id -> pio env` jde přes `board_registry` (každá deska má
generovaný `[env:board-<id>]`); bez argumentu se použije referenční
`esp32-s3-devkitm-1-nohw`. Tlačítka **Build** a **Flash** v designeru
(toolbar) spouští totéž a streamují reálný pio výstup do modálního okna
(`B` = build, `F` = flash, `Esc` = zavřít).

> **Flash bez hardwaru:** příkaz na upload je reálný a reálně se spustí;
> bez připojené ESP32 zhavaruje korektně (žádný fake úspěch) a je
> označen `UNVERIFIED-ON-HARDWARE`. Na připojeném hardwaru provede
> skutečný flash.

### Env proměnné pro build hook

| Proměnná | Default | Popis |
|----------|---------|-------|
| `ESP32OS_PIO_UI_EXPORT` | `1` | `0` = vypne generování `ui_design.c/h` |
| `ESP32OS_UI_JSON` | `main_scene.json` | Cesta ke vstupnímu design JSON |
| `ESP32OS_UI_SCENE` | `main` | Název scény v JSON |
| `ESP32OS_UI_VALIDATE` | `0` | `1` = před generováním spustí `validate_design.py`; při ERROR zastaví build |

### Graceful shutdown

`system_shutdown()` v `src/main.c` zastaví všechny služby v opačném pořadí startu:

```
ui_app_stop → ui_stop → metrics_stop → rpc_stop → input_stop
→ kernel_stop_ticker → bus_deinit → store_deinit
```

Spouští se přes RPC (UART, řádkové příkazy přes `rpc_parse_line`).
`app_main` je vlastníkem životního cyklu: po startu odebírá `TOP_RPC_CALL`
a reaguje na dva příkazy:

- `reboot` → `system_shutdown()` a poté `esp_restart()`
- `shutdown` → `system_shutdown()` a poté `esp_deep_sleep_start()` (deep
  sleep bez wake source = řízené vypnutí do externího resetu)

Subscriber běží přes message bus (fan-out do vlastní fronty), takže
koexistuje s případným dalším konzumentem `TOP_RPC_CALL` (např. UI RPC
dispatcher).

Poznámka:
- PlatformIO verze jsou v repu připnuté záměrně kvůli reprodukovatelným buildům a stabilním `sdkconfig`.
- `pio test -e native` vyžaduje host C compiler dostupný v `PATH`.
- Na Windows to znamená mít v `PATH` `gcc` (napr. MSYS2/MinGW-w64). Pokud `gcc` chybí, `scripts/check_all_local.ps1` native testy přeskočí s varováním.
- Rychlá cesta na Windows: `winget install -e --id MSYS2.MSYS2`, pak v MSYS2 shellu `pacman -S --needed mingw-w64-ucrt-x86_64-gcc` a přidat `C:\msys64\ucrt64\bin` do `PATH`.
- Na Windows může lokální policy zablokovat některé ESP-IDF toolchain binárky.
- Pokud native testy padají na `WinError 4551`, problém je host policy (App Control), ne kód testu; použij `scripts/check_all_local.ps1 -Fast` (tolerant) nebo povol běh `.pio\\build\\native` test binárek.
- Pokud chces i po tolerant runu tvrde overit report artefakty, pouzij `scripts/check_all_local.ps1 -Fast -StrictArtifacts`.
- Ve strict rezimu lze volitelne gateovat i triage CSV: `-StrictTriageCsv` (a delta navic `-StrictTriageDeltaCsv -NativePolicyTriageDeltaCsv ...`).
- `scripts/check_all.ps1` v režimu `-AllowNativePolicyBlock` po opakovaném policy failu automaticky spustí krátký `check_native_policy_probe.ps1`, aby vypsal blokované suites.
- Ve stejném kroku uloží i JSON artefakt `reports/native_policy_probe_auto.json` (lze změnit přes `-NativePolicyProbeJson` nebo vypnout prázdnou hodnotou).
- Pokud se probe nespusti (zadny opakovany policy fail), zapise se placeholder JSON se stavem `Triggered=false`, aby artefakt existoval konzistentne po kazdem behu.
- Po kazdem behu s `-AllowNativePolicyBlock` se navic appendne JSONL historie do `reports/native_policy_probe_history.jsonl` (lze zmenit parametrem `-NativePolicyHistoryJsonl`).
- Ve stejnem rezimu se po appendu historie provede i CSV smoke-check exportu (`reports/native_policy_history.smoke.csv`).
- Rychly trend/report z historie vypises pres `scripts/summarize_native_policy_history.ps1`.
- Summary navic ukazuje frekvenci konkretnich blokovanych/transient suites (pokud jsou v historii dostupne).
- Summary vypisuje i procentualni run-rate metriky (triggered/policy/transient/failure).
- Pro sdileni reportu lze exportovat markdown: `scripts/summarize_native_policy_history.ps1 -Last 30 -MarkdownOut reports/native_policy_summary.md`.
- Pro analyzu v tabulkach lze exportovat CSV: `scripts/summarize_native_policy_history.ps1 -CsvOut reports/native_policy_history.csv`.
- Burn-in vice kol overis pres `scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2`.
- Burn-in po dobehu automaticky vygeneruje i markdown report (`reports/native_policy_summary.md`), lze zmenit parametrem `-MarkdownSummaryPath`.
- Burn-in po dobehu automaticky vygeneruje i CSV report (`reports/native_policy_history.csv`), lze zmenit parametrem `-CsvSummaryPath`.
- Burn-in po dobehu automaticky vygeneruje i triage report (`reports/native_policy_triage.md`), prioritu/ranking lze upravit pres `-TriageTop`.
- Burn-in po dobehu automaticky vygeneruje i triage CSV (`reports/native_policy_triage.csv`), cestu lze zmenit pres `-TriageCsvPath`.
- Volitelne lze generovat i samostatny delta CSV (`-TriageDeltaCsvPath`) pro cisty ingest trendu.
- Volitelne lze zapnout i delta trend v triage (`-TriageDeltaWindow N`), ktery porovna poslednich `N` behu proti predchozim `N`.
- Pro fokus jen na regrese lze pridat `-TriageOnlyWorsening` (vyzaduje `-TriageDeltaWindow > 0`).
- Pro export cele delta sady (misto Top N) pouzij `-TriageIncludeAllDeltaRows` (vyzaduje `-TriageDeltaWindow > 0`).
- Pro odfiltrovani malych zmen pouzij `-TriageMinAbsDeltaScore N` (vyzaduje `-TriageDeltaWindow > 0`).
- Razeni delta trendu nastav pres `-TriageDeltaSortBy abs-delta|delta|suite`.
- Burn-in na konci automaticky spousti `check_native_policy_artifacts.ps1` (s md/csv gate podle nastaveni); vypnout lze `-SkipArtifactCheck`.
- Burn-in po triage kroku automaticky spousti i `check_native_policy_triage_csv.ps1`; vypnout lze `-SkipTriageCsvCheck`.
- Triage krok lze vypnout prepinacem `-SkipTriage`.
- Pro prisny gate (selhat pri POLICY_BLOCK) pouzij `scripts/burnin_native_policy.ps1 -Rounds 10 -FailOnPolicyBlock`.
- Pro uchovani detailu kazdeho kola zapni archivaci snapshotu: `scripts/burnin_native_policy.ps1 -Rounds 10 -ArchiveProbeSnapshots` (default slozka `reports/native_policy_snapshots`).
- Pocet ulozenych snapshotu lze omezit pres `-MaxSnapshotFiles` (default 50), starsi soubory se automaticky promazou.
- Pro pripravu podkladu pro IT/App Control pouzij `scripts/generate_native_policy_allowlist_request.ps1` (vystup: `reports/native_policy_allowlist_request.md`).
- Konzistenci policy artefaktu overis jednim krokem: `scripts/check_native_policy_artifacts.ps1 -RequireMarkdown -RequireCsv`.
- Tentyz checker umi i triage CSV: `scripts/check_native_policy_artifacts.ps1 -TriageCsv reports/native_policy_triage.csv -RequireTriageCsv` (a volitelne `-TriageDeltaCsv ... -RequireTriageDeltaCsv`).
- Konzistenci triage CSV overis jednim krokem: `scripts/check_native_policy_triage_csv.ps1 -RequireCombined` (a volitelne `-DeltaCsv ... -RequireDelta`).
- Priority suites pro allow-list eskalaci vytahnes skriptem: `scripts/triage_native_policy_blockers.ps1 -Top 5`.
- Trend zhorseni/zlepseni mezi okny ziskas pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5`.
- Jen zhorseni mezi okny ziskas pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -OnlyWorsening`.
- Vsechny delta radky (nejen Top N) ziskas pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -IncludeAllDeltaRows`.
- Jen vyrazne zmeny (napr. abs(delta) >= 2) ziskas pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -MinAbsDeltaScore 2`.
- Razeni podle samotneho delta score ziskas pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaSortBy delta`.
- Triage data pro dashboard exportuj pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -CsvOut reports/native_policy_triage.csv`.
- Samostatny delta dataset exportuj pres `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaCsvOut reports/native_policy_triage_delta.csv`.
- Pro rychlé vypsání konkrétních whitelist targetů použij `scripts/list_native_whitelist_targets.ps1`.
- Pro rozpad podle jednotlivých native suites (co je `PASSED` vs `POLICY_BLOCK`) použij `scripts/check_native_policy_probe.ps1`.
- Probe podporuje retry: `scripts/check_native_policy_probe.ps1 -MaxAttemptsPerSuite 3 -DelaySeconds 2`.
- Probe podporuje i cileny flaky-check: `scripts/check_native_policy_probe.ps1 -Suites test_ui_render_swbuf -Rounds 5 -MaxAttemptsPerSuite 3 -DelaySeconds 1`.
- Probe umi ulozit strojove citelny report: `scripts/check_native_policy_probe.ps1 -JsonOut reports/native_policy_probe_latest.json`.

## Quick checks

```powershell
scripts/check_all.ps1
scripts/check_all_local.ps1 -Fast
scripts/check_all_local.ps1 -Guardrails
# Guardrails run the same fast designer-refactor subset as CI.
scripts/check_all_local.ps1 -Fast -StrictArtifacts
scripts/check_all_local.ps1 -Fast -StrictArtifacts -StrictTriageCsv
scripts/check_all_local.ps1 -Fast -StrictArtifacts -StrictTriageDeltaCsv
scripts/check_all_local.ps1 -Fast -StrictArtifacts -StrictTriageCsv -NativePolicyTriageCsv reports/native_policy_triage.csv
scripts/check_all_local.ps1 -Fast -StrictArtifacts -StrictTriageDeltaCsv -NativePolicyTriageDeltaCsv reports/native_policy_triage_delta.only.csv
scripts/check_native_toolchain.ps1
scripts/list_native_whitelist_targets.ps1
scripts/check_native_policy_probe.ps1
scripts/check_native_policy_artifacts.ps1 -RequireMarkdown -RequireCsv
scripts/check_native_policy_artifacts.ps1 -RequireMarkdown -RequireCsv -RequireTriageCsv -RequireTriageDeltaCsv
# Note: check_native_policy_artifacts.ps1 also rejects explicitly empty -TriageCsv/-TriageDeltaCsv values.
scripts/check_native_policy_triage_csv.ps1 -RequireCombined
scripts/check_native_policy_triage_csv.ps1 -RequireDelta
# Note: explicitly empty -CombinedCsv/-DeltaCsv values are rejected; omit the parameter instead.
scripts/triage_native_policy_blockers.ps1 -Top 5
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -OnlyWorsening
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -IncludeAllDeltaRows
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -MinAbsDeltaScore 2
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaSortBy delta
scripts/triage_native_policy_blockers.ps1 -Top 5 -CsvOut reports/native_policy_triage.csv
scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaCsvOut reports/native_policy_triage_delta.csv
scripts/burnin_native_policy.ps1 -Rounds 1 -SkipPython -TriageCsvPath "" -TriageDeltaCsvPath reports/native_policy_triage_delta.only.csv -TriageDeltaWindow 5
```

```bash
./scripts/check_all_local.sh main_scene.json
./scripts/check_all_local.sh --guardrails
# Guardrails run the same fast designer-refactor subset as CI.
./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-csv
./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-delta-csv
./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-csv --native-policy-triage-csv reports/native_policy_triage.csv
./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-delta-csv --native-policy-triage-delta-csv reports/native_policy_triage_delta.only.csv
./scripts/check_native_toolchain.sh
```

## Repo docs

- `AGENTS.md` (work guide)
- `FILE_INDEX.md` (project map)
- `IMPLEMENTATION_SUMMARY.md` (architecture)

## SSD1363 bring-up (volitelné)

- Debug přepínače: `src/user_config.h` (`SSD1363_I2C_SCAN_ON_BOOT`, `SSD1363_BOOT_TEST_PATTERN`).
- Pokud je obraz posunutý, dolaď `SSD1363_COL_OFFSET` a/nebo `SSD1363_INIT_DISPLAY_OFFSET` v `src/user_config.h`.
