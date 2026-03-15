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
- Python testy (paralelně): `python -m pytest -q -n auto` (vyžaduje pytest-xdist)
- Pokrytí kódu: `python -m pytest -q --cov=. --cov-report=term-missing:skip-covered --cov-fail-under=90`
- Mypy (strict — codegen): `python -m mypy --ignore-missing-imports tools/ui_codegen.py scripts/pio_generate_ui_design.py design_tokens.py shared_undo_redo.py event_manager.py constants.py`
- Mypy (advisory — designer): `python -m mypy --ignore-missing-imports ui_designer.py ui_models.py`
- Firmware testy (host): `pio test -e native`
- Firmware build (bez HW): `pio run -e arduino_nano_esp32-nohw`
- Native preflight (Windows): `scripts/check_native_toolchain.ps1`
- Native whitelist targets (Windows): `scripts/list_native_whitelist_targets.ps1`
- Native policy probe (Windows): `scripts/check_native_policy_probe.ps1`
- Native preflight (shell): `./scripts/check_native_toolchain.sh`
- Lokalni tolerant checks (Windows): `scripts/check_all_local.ps1 -Fast`
- Lokalni guardrail test subset (Windows): `scripts/check_all_local.ps1 -Guardrails`
	(stejny rychly designer-refactor subset jako v CI)
- Lokalni tolerant checks + strict artefakty (Windows): `scripts/check_all_local.ps1 -Fast -StrictArtifacts`
- Lokalni tolerant checks (shell): `./scripts/check_all_local.sh main_scene.json`
- Lokalni guardrail test subset (shell): `./scripts/check_all_local.sh --guardrails`
	(stejny rychly designer-refactor subset jako v CI)
- Lokalni strict artefakty + triage gate (shell): `./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-csv`
- Lokalni strict artefakty + delta triage gate (shell): `./scripts/check_all_local.sh main_scene.json --strict-artifacts --strict-triage-delta-csv`

## Environment proměnné

- `ESP32OS_TEMPLATES_PATH`: přesměruje cestu k `templates.json` (automaticky nastaveno v testech na tmp_path, aby nedošlo k mutaci trackovaného souboru).
- `ESP32OS_OVERFLOW_WARN`: `1`/`0` — zapne/vypne overflow warnings v designeru.

## CI pipeline

CI sestává ze dvou jobů:
- **Python (pytest)**: ruff lint + format, mypy (strict codegen + advisory designer), JSON validace, codegen freshness, guardrail testy, plný pytest s coverage (fail-under=90%).
- **Firmware (PlatformIO)**: native testy, ESP32-S3 build, Arduino Nano ESP32 build. PlatformIO je cachováno.

## Keyboard shortcuts

Complete reference: [`docs/KEYBOARD_SHORTCUTS.md`](docs/KEYBOARD_SHORTCUTS.md). In-app: press **F1** (help overlay) or **Ctrl+/** (quick-ref panel).

## Poznamky k native testum (Windows)

- `pio test -e native` potrebuje mit `gcc` v `PATH`.
- Doporucena instalace na Windows: `winget install -e --id MSYS2.MSYS2`, potom v MSYS2 shellu `pacman -S --needed mingw-w64-ucrt-x86_64-gcc` a pridat `C:\\msys64\\ucrt64\\bin` do `PATH`.
- Pokud `gcc` chybi, `scripts/check_all_local.ps1` v tolerantnim rezimu native test preskoci a vypise varovani.
- Pokud testy padaji na `WinError 4551`, jde o host App Control policy (ne regresi firmware); pouzij tolerant workflow (`scripts/check_all_local.ps1 -Fast`) nebo povol test binarky v `.pio\\build\\native`.
- Kdyz potrebujes po tolerant runu tvrde overit reporty, pouzij `scripts/check_all_local.ps1 -Fast -StrictArtifacts`.
- Ve strict modu lze volitelne vyzadovat i triage CSV pres `-StrictTriageCsv` (pokud nezadas `-NativePolicyTriageCsv`, pouzije se default `reports/native_policy_triage.csv`) a delta pres `-StrictTriageDeltaCsv` (pokud nezadas `-NativePolicyTriageDeltaCsv`, pouzije se default `reports/native_policy_triage_delta.only.csv`).
- Pozor: explicitni cesty `-NativePolicyTriageCsv`/`-NativePolicyTriageDeltaCsv` vyzaduji odpovidajici flag `-StrictTriageCsv`/`-StrictTriageDeltaCsv` (jinak wrapper failne hned na argument validation).
- Stejne i v shell wrapperu: `--native-policy-triage-csv` vyzaduje `--strict-triage-csv` a `--native-policy-triage-delta-csv` vyzaduje `--strict-triage-delta-csv`.
- `scripts/check_all.ps1 -AllowNativePolicyBlock` po opakovanem policy failu automaticky spusti kratky probe a vypise blokovane suites.
- Pri tom samem behu uklada JSON artefakt do `reports/native_policy_probe_auto.json` (prepsatelne parametrem `-NativePolicyProbeJson`).
- Kdyz probe neni potreba spustit, vytvori se placeholder JSON (`Triggered=false`) pro konzistentni reporting.
- Zaroven se appenduje JSONL historie do `reports/native_policy_probe_history.jsonl` (konfigurovatelne `-NativePolicyHistoryJsonl`).
- Ve stejnem rezimu se po appendu provede i CSV smoke-check exportu do `reports/native_policy_history.smoke.csv`.
- Rychly souhrn trendu vypises pomoci `scripts/summarize_native_policy_history.ps1`.
- Souhrn umi i frekvenci konkretnich blokovanych/transient suites napric historií.
- Soucasti souhrnu jsou i procentualni run-rate metriky pro rychle porovnani stability.
- Souhrn lze vyexportovat i do markdownu: `scripts/summarize_native_policy_history.ps1 -Last 30 -MarkdownOut reports/native_policy_summary.md`.
- Pro dalsi zpracovani lze exportovat i CSV: `scripts/summarize_native_policy_history.ps1 -CsvOut reports/native_policy_history.csv`.
- Pro opakovany burn-in pouzij `scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2`.
- Burn-in umi po dobehu rovnou zapsat markdown souhrn (`-MarkdownSummaryPath`, default `reports/native_policy_summary.md`).
- Burn-in umi po dobehu zapsat i CSV souhrn (`-CsvSummaryPath`, default `reports/native_policy_history.csv`).
- Burn-in umi po dobehu zapsat i triage report (`-TriageReportPath`, default `reports/native_policy_triage.md`, top pres `-TriageTop`).
- Burn-in umi po dobehu zapsat i triage CSV (`-TriageCsvPath`, default `reports/native_policy_triage.csv`).
- Burn-in umi zapsat i oddeleny delta CSV (`-TriageDeltaCsvPath`) pro trend-only ingest.
- Delta-only export (`-TriageCsvPath ""` + `-TriageDeltaCsvPath ...`) vyzaduje i `-TriageDeltaWindow > 0`.
- Burn-in umi predat i delta trend triage (`-TriageDeltaWindow N`) pro porovnani poslednich/predchozich `N` behu.
- Burn-in umi omezit delta vystup jen na zhorseni (`-TriageOnlyWorsening`, vyzaduje `-TriageDeltaWindow > 0`).
- Burn-in umi exportovat celou delta sadu bez Top limitu (`-TriageIncludeAllDeltaRows`, vyzaduje `-TriageDeltaWindow > 0`).
- Burn-in umi filtrovat jen vyrazne zmeny pres `-TriageMinAbsDeltaScore N` (vyzaduje `-TriageDeltaWindow > 0`).
- Burn-in umi menit razeni delta vystupu pres `-TriageDeltaSortBy abs-delta|delta|suite`.
- Burn-in po dobehu standardne spousti i `check_native_policy_artifacts.ps1`; lze vypnout prepinacem `-SkipArtifactCheck`.
- Burn-in po triage kroku standardne spousti i `check_native_policy_triage_csv.ps1`; lze vypnout `-SkipTriageCsvCheck`.
- Triage krok lze vypnout prepinacem `-SkipTriage`.
- `-SkipTriage` nelze kombinovat s explicitnimi triage parametry (`-Triage*`, `-SkipTriageCsvCheck`) - wrapper failne hned pri argument validation.
- Pokud ma burn-in failnout pri policy blokovani, pouzij `-FailOnPolicyBlock`.
- Pro audit/detail per-round probe reportu zapni `-ArchiveProbeSnapshots` (vystup do `reports/native_policy_snapshots`, lze zmenit `-ProbeSnapshotDir`).
- Retenci snapshots ridi `-MaxSnapshotFiles` (starsi probe JSON se automaticky maze).
- Pro rychly podklad pro App Control vyjimku pouzij `scripts/generate_native_policy_allowlist_request.ps1`.
- Pro vypsani konkretnich cest k binarkam pro whitelist pouzij `scripts/list_native_whitelist_targets.ps1`.
- Pro prehled, ktere suites jsou blokovane policy a ktere bezi, pouzij `scripts/check_native_policy_probe.ps1`.
- Probe umi retry per-suite: `scripts/check_native_policy_probe.ps1 -MaxAttemptsPerSuite 3 -DelaySeconds 2`.
- Pro cileny flaky-check jedne suite pouzij napr. `scripts/check_native_policy_probe.ps1 -Suites test_ui_render_swbuf -Rounds 5 -MaxAttemptsPerSuite 3 -DelaySeconds 1`.
- Pro CI/reporting lze vypsat JSON: `scripts/check_native_policy_probe.ps1 -JsonOut reports/native_policy_probe_latest.json`.
- Konzistenci cele sady artefaktu (`json`, `jsonl`, `md`, `csv`) overis skript `scripts/check_native_policy_artifacts.ps1 -RequireMarkdown -RequireCsv`.
- Stejny checker umi validovat i triage CSV (`-TriageCsv ... -RequireTriageCsv`, volitelne `-TriageDeltaCsv ... -RequireTriageDeltaCsv`; pri `-RequireTriageCsv/-RequireTriageDeltaCsv` bez cesty pouzije default report cesty).
- Stejny checker failne na explicitne prazdne cesty (`-TriageCsv ""` / `-TriageDeltaCsv ""`); kdyz cestu nechces zadavat, parametr vynech.
- Prioritizaci suites pro App Control whitelist z historie pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5`.
- Delta trend (zlepseni/zhorseni mezi dvema okny) pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5`.
- Jen zhorseni mezi okny pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -OnlyWorsening`.
- Celou delta sadu pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -IncludeAllDeltaRows`.
- Delta filtr podle absolutni hodnoty pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -MinAbsDeltaScore 2`.
- Razeni podle samotneho delta score pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaSortBy delta`.
- CSV export pro dalsi automatizaci pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -CsvOut reports/native_policy_triage.csv`.
- Oddeleny delta CSV pripravi `scripts/triage_native_policy_blockers.ps1 -Top 5 -DeltaWindow 5 -DeltaCsvOut reports/native_policy_triage_delta.csv`.
- Konzistenci triage CSV overi `scripts/check_native_policy_triage_csv.ps1 -RequireCombined` (a volitelne `-DeltaCsv ... -RequireDelta`).
- Triage CSV checker vyzaduje cil (`-RequireCombined`/`-RequireDelta` nebo explicitni `-CombinedCsv`/`-DeltaCsv`); prazdne spusteni failne.
- Triage CSV checker stejne tak failne i na explicitne prazdne cesty (`-CombinedCsv ""` / `-DeltaCsv ""`); kdyz nechces cestu zadavat, parametr vynech.
