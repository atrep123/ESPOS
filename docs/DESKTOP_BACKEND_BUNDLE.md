# Fixed desktop CodeGraph backend bundle

This is an independent packaging preparation for `tools/desktop_backend_entry.py`.
The main native file pipeline does not depend on it. No desktop application,
existing multipurpose sidecar, installer, firmware or device is changed here.

## Current verification boundary

On 2026-10-13, the actual standalone onedir bundle built and passed the verifier
CLI's seven checks. The build and verifier CLI exited naturally with code 0.
All seven backend children exited naturally: five successes with code 0 and two
expected malformed-request/unsupported-role failures with code 2. Every child
had empty stderr; the slowest completed in 0.172 seconds under the 12-second cap.
The final native process check found no remaining owned backend process.

The owned artifact directory is
`C:\Sumilek-git\worker-patches\backend-freeze-acadb7c75f0c4893b7c73adaeefb36bf`.
It contains `build.stdout.log`, `build.stderr.log`, `build.receipt.json`,
`frozen-verification.json`, `verifier-cli.receipt.json`, `bundle.manifest.json`
and `SHA256SUMS.txt`. The manifest records all 64 bundle files (23,430,535 bytes),
their SHA-256 hashes, source fingerprints, native-extension comparisons and the
observed child exit/stream/timing records. Both bundled grammar extensions match
the approved source `.pyd` files byte for byte. Build input hashes were unchanged
at the final audit. Sandbox CIM enumeration was unavailable; the independent
remaining-process check used native `Get-Process` instead.

The executable SHA-256 is
`8dc9f5bb191f0881d462c0ef62ceff3fa578855ca369669a69868450893bda6a`.
The manifest SHA-256 is
`f9e24fad3c8a6499b55db650d758675cd9e1dff41dd7fc58452781f0beb60a4d`.

The 28 focused verifier/transport/recipe tests and Ruff lint/format checks also
passed. Those tests use explicit `TEST_ONLY` source children and transport fault
fixtures, not fabricated executables. The earlier 44 real-parser entry tests
remain separate retained evidence; they were not rerun by this packaging task.

Main's latest integration report records 302 passed, 0 failed and 0 skipped,
including the real SDK component, source entry, frozen-checker fixtures and
SupplyChain checks. That report was supplied by main and was not rerun by this
source owner. It is separate from the actual frozen executable's seven observed
checks recorded above.

The build used global CPython 3.12.10 and PyInstaller 6.20.0, with the exact
approved build-only grammar site (`tree-sitter==0.26.0`, `tree-sitter-cpp==0.23.4`).
No packages were installed and no global configuration/cache was deleted or
changed; the builder cache was redirected into the owned scratch directory.
The first attempt with builder `-I` exited naturally before processing the spec
because that mode hid installed user-site Windows support modules. Its logs and
receipt remain in `backend-freeze-c9b1e81355124992a9990fc832c061f4`. Normal global
Python imported the existing modules, and the fresh second attempt succeeded.
The verifier CLI itself ran with `-I -B` and only standard-library dependencies.

## Recipe and dependencies

`tools/desktop_backend_freeze.spec` is a genuine PyInstaller **onedir** spec. Its
entry, package root and sibling parser/catalog come from this source checkout,
relative to the spec. When the builder cannot find both grammar packages, the
only additional build search root is the explicitly reviewed
`C:\Sumilek-git\worker-patches\espos-mcp-runtime-20261003\.venv\Lib\site-packages`.
The spec adds it to the build process and Analysis `pathex`, with no environment
override, runtime hook or external frozen-runtime search path. This hardcoded
directory is an optional convenience for this PC, not a portable release
expectation. CI/release builders should install their own hash-checked grammar
wheels into their build environment; normal dependency discovery bypasses this
local path. PyInstaller 6.20.0 logged its foreign-site `pathex` deprecation for
the local build; its warning says that route will become an error in version 7.
The normal installed-dependency route avoids that warning. Release tool pinning
and the separately owned CI workflow are outside this task.

The recipe checks the pinned parser versions from
`requirements-codegraph-win-py312.txt`, imports the actual native bindings, and
includes both `.pyd` extensions explicitly. It also collects C++ query resources.
The frozen runtime uses normal static package imports; no developer tooling root,
caller import, environment-selected Python, external parser or shell is involved.

The result is `espos_codegraph_backend/espos_codegraph_backend.exe` with its adjacent `_internal`
directory. Keep that directory intact, including the bundled Python runtime,
Tree-sitter extensions and their resolved native dependencies. The executable is
not a standalone file. Its name is deliberately distinct from the legacy full
`espos_sidecar`; it must never replace the general scene sidecar. `console=True`
preserves binary stdin/stdout. The owning
Windows process hides the console with `CREATE_NO_WINDOW`; a windowed/noconsole
build would remove streams required by the protocol. Onedir avoids the onefile
extraction subprocess and its different lifetime/cleanup contract.

For a later local build, select fresh owned output/work directories. This example
uses the existing global builder and optional approved dependency site, performs
no installation, and must not overwrite the legacy general scene sidecar. The
exact observed build arguments are retained in the successful build receipt.

```powershell
$backendBuildRoot = Join-Path 'C:\Sumilek-git\worker-patches' ('backend-freeze-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backendBuildRoot -ErrorAction Stop | Out-Null
$backendDistRoot = Join-Path $backendBuildRoot 'dist'
$backendWorkRoot = Join-Path $backendBuildRoot 'work'
& 'C:\Users\atrep\AppData\Local\Programs\Python\Python312\python.exe' -B -m PyInstaller --distpath $backendDistRoot --workpath $backendWorkRoot 'C:\Sumilek-git\ESPOS-integration-20261001\tools\desktop_backend_freeze.spec'
if ($LASTEXITCODE -ne 0) { throw 'Backend freeze failed; inspect build output.' }
```

## Executable verifier

The verifier accepts exactly `--exe ABSOLUTE_PATH`. The operator must identify an
existing artifact in their owned staging directory. It does not discover, copy,
rename, build or replace executables. Accepted filenames are `espos_codegraph_backend.exe`
and `espos_codegraph_backend-x86_64-pc-windows-msvc.exe`. The legacy `espos_sidecar`
name is rejected. Windows x64 console PE header validation
rejects GUI images, DLLs and interpreter/script placeholders; it is not proof of ownership or signing.
Never supply a GUI application or rename another application to fit this check.

After a successful real build, explicitly verify the owned artifact in the same
PowerShell session, using the fresh directory selected above:

```powershell
$backendBuiltExe = Join-Path $backendDistRoot 'espos_codegraph_backend\espos_codegraph_backend.exe'
& 'C:\Users\atrep\AppData\Local\Programs\Python\Python312\python.exe' -I -B 'C:\Sumilek-git\ESPOS-integration-20261001\tools\verify_frozen_desktop_backend.py' --exe $backendBuiltExe
```

Each of at most seven sequential children has one 12-second deadline covering
stdin write, process execution and output drain, a combined 1 MiB stdout/stderr
cap, and a bounded 0.2-second termination/reap grace. There are no retries or
reader threads. Only the owned child is killed, and its pipes are closed. Windows
startup is hidden and `shell=False`. Stdin stays open after the newline, matching
the desktop lifetime. Any nonempty stderr is rejected and never printed.

Checks cover actual parse and token edit, stable node identity, source hashes,
UTF-8 BOM/CRLF/Unicode and opaque-byte preservation, explicit SDK profile,
SDK regions and typed label construction, repeated-key malformed request failure,
and rejection of the unsupported catalog CLI role. A successful JSON receipt
contains the executable SHA-256 (checked again after execution), check names,
each child's natural exit code, stream byte counts and elapsed time, and
`frozenVerified: true`. Failures
return nonzero with `frozenVerified: false` and a fixed diagnostic code, without
raw child output, paths or exception text. A receipt proves this staged backend's
representative behavior; it does not prove Tauri integration, offline installation,
signing, complete deployment assets, or SDK/hardware execution.

## Read-only desktop contract checked

The desktop's prepared fixed-role parser reference calls exactly
`Command.sidecar('binaries/espos_sidecar', ['codegraph-bundled'])`. It admits parse,
edit, regions, construct, sdkRegions and constructSdk, retaining bindings,
eventBindings and sdkProfile. `transport.ts` sends one newline-terminated JSON
frame and caps request/combined reply streams at 1 MiB; its default timeout is
40 seconds. The backend additionally enforces 64 KiB raw C++ input/output.
The production parser remains Unavailable; this recipe does not activate it.

The current desktop Cargo lock selects `tauri-plugin-shell` 2.3.5. Its cached
Rust source was checked read-only: `src/process/mod.rs` pipes stdin/stdout/stderr,
uses `CREATE_NO_WINDOW`, writes stdin without closing it, and reports line events
before termination. `src/commands.rs` checks configured external sidecars and
shell scopes. There is no `shell/process.rs` file under the desktop checkout;
the resolved dependency's process module is the corresponding implementation.

The desktop currently configures the legacy `binaries/espos_sidecar` as an external
binary. This recipe builds the separate `espos_codegraph_backend` artifact and
does not stage anything in the desktop. Future integration must review a distinct
backend role/path, target-triple naming and an onedir resource layout preserving
`_internal` beside that backend exe. The legacy full sidecar and its prepared
reference are untouched. Release/build-tool pinning, production parser activation,
package specification, installer integration and release/CI portability checks
are separate work. The local frozen run above does not establish those outcomes.
This source owner did not stage files or change the Git index. Main has added
the narrow `!tools/desktop_backend_freeze.spec` exception to the existing
`*.spec` ignore rule; the reviewed source recipe now appears in ordinary
`git status`. Main will include the valid recipe and hash-pinned grammar
requirements in its upcoming commit. Commit inclusion is main's responsibility
and is not claimed complete by this source owner. The independently verified
scratch bundle and its receipts remain separate from source staging, and no
artifact has been staged into the Tauri or legacy scene sidecar locations.
