# Scripts Directory

## CI / Check Suites

| Script | Platform | Purpose |
|--------|----------|---------|
| `check_all.ps1` | Windows | Full CI check suite (lint, test, build, native policy diagnostics) |
| `check_all.sh` | Linux/macOS | Full CI check suite (lint, test, build) |
| `check_all_local.ps1` | Windows | Local dev check suite (calls `check_all.ps1` + strict artifact checks) |
| `check_all_local.sh` | Linux/macOS | Local dev check suite (calls `check_all.sh`) |

## Build / Codegen

| Script | Purpose |
|--------|---------|
| `pio_generate_ui_design.py` | PlatformIO pre-build hook: JSON → `src/ui_design.c\|h` |
| `skip_hw_tests.py` | PlatformIO extra script: skip hardware-dependent tests in CI |

## Native Toolchain

| Script | Purpose |
|--------|---------|
| `check_native_toolchain.ps1` | Verify GCC/PlatformIO are available (Windows) |
| `check_native_toolchain.sh` | Verify GCC/PlatformIO are available (Linux/macOS) |

## Windows WDAC / Native Policy

These scripts manage Windows App Control (WDAC) policy issues that block native test binary execution.

| Script | Called by CI? | Purpose |
|--------|:---:|---------|
| `check_native_policy_probe.ps1` | ✓ | Run native tests per-suite, detect WinError 4551 blocks, write JSON report |
| `summarize_native_policy_history.ps1` | ✓ | Compute block rates from history JSONL, output markdown + CSV |
| `check_native_policy_artifacts.ps1` | ✓ | Validate probe JSON, history, summary, and CSV artifacts exist |
| `check_native_policy_triage_csv.ps1` | ✓ | Validate triage/delta CSV column structure |
| `burnin_native_policy.ps1` | — | Run N rounds of full checks, then summarize + triage |
| `triage_native_policy_blockers.ps1` | — | Rank suites by block severity, compute delta trends |
| `generate_native_policy_allowlist_request.ps1` | — | Generate IT allow-list request (markdown) from probe JSON |
| `list_native_whitelist_targets.ps1` | — | List `.exe` files under `.pio/build/native/` for allow-listing |
