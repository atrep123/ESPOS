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
- Native whitelist targets (Windows): `scripts/list_native_whitelist_targets.ps1`
- Native policy probe (Windows): `scripts/check_native_policy_probe.ps1`
- Native preflight (shell): `./scripts/check_native_toolchain.sh`
- Lokalni tolerant checks (Windows): `scripts/check_all_local.ps1 -Fast`
- Lokalni tolerant checks (shell): `./scripts/check_all_local.sh main_scene.json`

## Poznamky k native testum (Windows)

- `pio test -e native` potrebuje mit `gcc` v `PATH`.
- Doporucena instalace na Windows: `winget install -e --id MSYS2.MSYS2`, potom v MSYS2 shellu `pacman -S --needed mingw-w64-ucrt-x86_64-gcc` a pridat `C:\\msys64\\ucrt64\\bin` do `PATH`.
- Pokud `gcc` chybi, `scripts/check_all_local.ps1` v tolerantnim rezimu native test preskoci a vypise varovani.
- Pokud testy padaji na `WinError 4551`, jde o host App Control policy (ne regresi firmware); pouzij tolerant workflow (`scripts/check_all_local.ps1 -Fast`) nebo povol test binarky v `.pio\\build\\native`.
- `scripts/check_all.ps1 -AllowNativePolicyBlock` po opakovanem policy failu automaticky spusti kratky probe a vypise blokovane suites.
- Pri tom samem behu uklada JSON artefakt do `reports/native_policy_probe_auto.json` (prepsatelne parametrem `-NativePolicyProbeJson`).
- Kdyz probe neni potreba spustit, vytvori se placeholder JSON (`Triggered=false`) pro konzistentni reporting.
- Zaroven se appenduje JSONL historie do `reports/native_policy_probe_history.jsonl` (konfigurovatelne `-NativePolicyHistoryJsonl`).
- Rychly souhrn trendu vypises pomoci `scripts/summarize_native_policy_history.ps1`.
- Souhrn umi i frekvenci konkretnich blokovanych/transient suites napric historií.
- Soucasti souhrnu jsou i procentualni run-rate metriky pro rychle porovnani stability.
- Souhrn lze vyexportovat i do markdownu: `scripts/summarize_native_policy_history.ps1 -Last 30 -MarkdownOut reports/native_policy_summary.md`.
- Pro opakovany burn-in pouzij `scripts/burnin_native_policy.ps1 -Rounds 10 -DelaySeconds 2`.
- Burn-in umi po dobehu rovnou zapsat markdown souhrn (`-MarkdownSummaryPath`, default `reports/native_policy_summary.md`).
- Pokud ma burn-in failnout pri policy blokovani, pouzij `-FailOnPolicyBlock`.
- Pro audit/detail per-round probe reportu zapni `-ArchiveProbeSnapshots` (vystup do `reports/native_policy_snapshots`, lze zmenit `-ProbeSnapshotDir`).
- Retenci snapshots ridi `-MaxSnapshotFiles` (starsi probe JSON se automaticky maze).
- Pro rychly podklad pro App Control vyjimku pouzij `scripts/generate_native_policy_allowlist_request.ps1`.
- Pro vypsani konkretnich cest k binarkam pro whitelist pouzij `scripts/list_native_whitelist_targets.ps1`.
- Pro prehled, ktere suites jsou blokovane policy a ktere bezi, pouzij `scripts/check_native_policy_probe.ps1`.
- Probe umi retry per-suite: `scripts/check_native_policy_probe.ps1 -MaxAttemptsPerSuite 3 -DelaySeconds 2`.
- Pro cileny flaky-check jedne suite pouzij napr. `scripts/check_native_policy_probe.ps1 -Suites test_ui_render_swbuf -Rounds 5 -MaxAttemptsPerSuite 3 -DelaySeconds 1`.
- Pro CI/reporting lze vypsat JSON: `scripts/check_native_policy_probe.ps1 -JsonOut reports/native_policy_probe_latest.json`.
