# ESPOS production UI task host driver

## Current native revalidation (2026-10-15, Prague)

The current public ESPOS headless C runner was rebuilt and executed with the
existing WinLibs GCC 16.1.0 on Windows. The complete native regression file
`tests/test_runtime_simulator.py` passed **12 tests**, with no failures or skips,
in 85.64 seconds. Evidence:
`C:/Sumilek-git/worker-patches/native_gray4_revalidation_20261014_v2.xml`.
All inputs were fresh synthetic scenes, not the authored design or UI kit.

This covers the actual production UI task, slider clamp/checkbox activation,
cold disconnected/error mock transport, app/visual-logic subscribers, numeric
menu/display/contrast/back transitions, and focus restoration/preservation.
Both returned state and emitted PGM framebuffer bytes were checked. The two
initial/default capture PNGs are lossless containers of the native PGM pixels,
not redrawn mock screenshots. No editor window or physical device was used.

The source-only editor/preview/pointer/toolbar integration separately passed
427 targeted tests (one native C inspection case was deliberately deselected).
Its ordinary input/state error API remains compatible for callers without a
cancellation Event; cancellable editor calls receive explicit cleanup outcomes.
The preview remains a one-shot **256x128** snapshot with permanently labelled
mock transport. It is not the promised interactive TabOS/Tab5 simulator.

These current native results supersede only the earlier statements that the
default/app runner had not been rebuilt after the seam and ingress changes.
The hot disconnect/error/reconnect verification then exposed a real native
status-contract defect: hot disconnect used the host-test error alias `-6`,
whereas initial configuration and the Python wire use `261`. The host adapter
now shares explicit simulator wire constants for both paths; no firmware or
test-stub header was modified. Both initial measurements retained their two
failures and artifacts; the expected wire value was not relaxed.

After the fix, all **6 actual hot native tests passed** in 57.69 seconds in
both default and app/logic modes. Controls use equal virtual-time schedules,
check that failed writes retain the last accepted pixels while values/logic
continue to update, and require reconnect to repaint current UI. Press/release/
tick ordering is also checked. Evidence:
`C:/Sumilek-git/worker-patches/TEST_ONLY-hot-native-20261015-main-fix-v2/results.xml`.
These are actual compiled C runs, with mock transport, not GUI or hardware tests.

Actual editor GUI integration, standalone packaging, Tab5/color renderer,
clean Windows startup and physical display/peripheral behavior remain separate
verification requirements.

Run from the repository root with an existing GCC and Python:

```powershell
python tools/espos_runtime_simulator.py main_scene.json --output frame.pgm --events 0,6,1,4
python tools/espos_runtime_simulator.py main_scene.json --output failed.pgm --display disconnected
python tools/espos_runtime_simulator.py main_scene.json --output app.pgm --app --events action:menu.item0:0,action:list.item0:0,1,1
python -m pytest -q tests/test_runtime_simulator.py
```

The shared `generate_ui_design_multi_pair` generates private C/H files. The
native executable includes production `services/ui/ui.c` and executes its
actual `ui_task`: geometry navigation, activation, integer/enum editors,
checkboxes, overlays, animation and production render/dirty-flush code remain
in C. There is no substitute Python widget renderer. PGM contains the bytes
accepted by the simulated SSD1363 transport, expanded from gray4 to gray8.

Numeric events retain firmware INPUT_ID / pressed=true behavior: A=0,
B/back=1, up=3, down=4, left=5, right=6, encoder press=8, hold=9, CW=10, CCW=11.
The initial frame is rendered before events. Each invocation is a fresh process.
Maximum 256 steps,
60-second compilation and 10-second execution limits; one compiler invocation.
Temporary builds use Python's system temporary-directory selection (TEMP on
Windows), with a unique `espos-runtime-` directory. Compiler TEMP/TMP point
inside that build directory; builds no longer force output into the checkout.

### Input and process isolation (2026-10-14)

Inputs are validated before compiler discovery or temporary-file creation.
Numeric events must be exact builtin integers, not booleans or coercible objects;
application events use the existing bounded ASCII action/command grammar only.
Button press/release, tick-only and hot display steps use the bounded grammar
below in both modes.
The app flag and display-state types are checked explicitly. Accepted input
sequences are detached copies, not a mutable caller-owned list.

Compiler/runtime children receive a freshly constructed allowlist environment.
Inherited credentials, proxies, Python import paths, compiler overrides and DLL
search paths are not copied. PATH contains only concrete compiler/Python parent
directories and fixed OS executable directories. Normal installed tool aliases
are resolved before validation; the selected concrete paths are used thereafter.

Windows runs use a private kill-on-close Job without breakaway permission. A
fixed Python gate admits the trusted command only after Job assignment. Both
output pipes are drained concurrently with a shared 1 MiB cap; deadline,
nonzero exit, output overflow or incomplete owned-process cleanup is a failure.
Only that run's Job is terminated, never a global name/PID search. Reader threads
must join before success. POSIX preserves the existing gray4 runner with an owned
process group; this does not prove ownership of descendants that create a new
session. POSIX runtime behavior has not been reverified in this Windows turn.

Private builds are removed only after rechecking their exact parent, basename
and filesystem identity. An uncertain cleanup leaves the build for review;
`SimulatorProcessError.retained_build` identifies it. CLI errors expose a fixed
diagnostic, not raw child output or the parent's environment.
Returned state explicitly includes
`simulation: {hardware_transport: "mock", display: <initial>,
initial_display: <initial>, final_display: <reported final>}`.
The legacy `display` field aliases the initial configuration. Final display
state is mapped from the child's bounded integer `display_status` and checked
against the last validated display event (or initial state when there are none).
This labels mock transport provenance, not physical device availability.

Observed: 409 wrapper/input/environment/process tests and 113 subtests passed.
The wrapper used a TEST_ONLY mocked compiler/C runtime; real process tests used
only inert Python children. No GCC/MSVC, native renderer, GUI or hardware was run
for this isolation change. The earlier production C/UI evidence below is not
a post-change revalidation. These controls are not a hostile-program sandbox.

Hardware is explicitly simulated. `connected` accepts pixel writes;
`disconnected` returns ESP_ERR_NOT_FOUND; `error` returns failure. Failed
transport never updates the captured frame. Existing host store stubs provide
in-memory configuration, not NVS persistence. No serial/network/device access.

## Boundaries and remaining seams

Default mode remains the isolated production UI service runner. Opt-in `--app`
uses Windows fibers to run unchanged production `ui_task`, `ui_app_task` and
`logic_task`, plus production `kernel/msgbus.c` and `ui_cmd.c`. The shim supplies
bounded FIFO queues and cooperative task creation/delay/receive primitives.
Tasks drain in UI/app/logic order. Queue publication yields to the scheduler;
blocked receives resume when a message arrives or virtual timeout expires.
Virtual startup advances 150 ms for the real app delay, then publishes a
10-ms-topic tick. Non-tick events retain the 50 ms settling policy; explicit
tick steps advance the scheduler in individual 10 ms intervals and publish ticks
after advancing the clock. This is
a reproducible scheduling policy, not ESP32 core/priority/timing emulation.
A 100000-step budget fails explicitly rather than hanging on cyclic logic.

Generated logic programs are consumed by the real logic service: the regression
checks boot and widget on_press actions update real widget text through the bus.
The app regression checks menu/display-list/contrast-editor/back transitions,
real prefix visibility and framebuffer changes, with zero drops. `action:id:value`
injects the firmware TOP_UI_ACTION topic; it does not call an invented screen
model. Numeric events still inject TOP_INPUT_BTN. JSON includes actual app screen
state, logic boot state, queue drops, scheduler steps and production widget text.
GPIO reads/writes use a shared simulated 64-pin array; no physical GPIO access.

### Public component CI policy

Full builds needing private TabOS SDK/applications are local-only. Public
component CI is not a substitute for that build, an editor window, or hardware.
The separate `native-runtime.yml` Windows 2022 / Python 3.12 job requires an
already installed ordinary x86_64 GCC; an absent compiler is a failure, not a
skip, and this workflow does not download a compiler or private SDK.

Its five separately saved groups require at least 12 simulator, 6 hot-native,
1 native-preview, 5 process-bridge, and 52 process-control passing cases. A
nonzero pytest exit, missing required control, missing/duplicate JUnit case,
failure, error, or skip rejects the job. Only the first three groups execute
the C renderer; the bridge deliberately substitutes compiler/frame data and
the process controls use inert children. Their counts are not interchangeable
native-renderer evidence. Public input hashes are checked before and after.

General CI deselects the Windows-only hot-native and native-preview modules.
The existing Linux-safe default simulator cases remain there; Windows app
cases may be skipped in that Linux subset. Only the complete Windows job's
positive reports establish completion of all native groups. The job name
`Required Windows native runtime` does not itself enable branch protection.

The extracted workflow Python body was also executed locally on Windows with
the existing Python 3.12, pytest 9.0.3, and GCC 16.1.0. All five groups passed:
**76 cases, zero failures/errors/skips** (19 C-renderer/preview cases and 57
process/bridge controls). Scoped public input hashes and the workflow hash
were unchanged. Evidence:
`C:/Sumilek-git/worker-patches/TEST_ONLY-native-runtime-ci-main-20261015-v1/`.
This local invocation did not install the workflow's pinned test tools, execute
its GitHub runner steps, or test a private TabOS build, GUI, or device.

The host queue deletion shim is idempotent because production `bus_deinit()`
visits the same queue once per subscribed topic. This is a host cleanup
accommodation, not verification of production FreeRTOS queue cleanup.

### Production focus recovery and regression

The real app startup hides all roots before showing menu. Previously,
`UI_CMD_SET_PREFIX_VISIBLE` recovered focus only when a focused widget existed
and was not focusable. Hiding the last focusable root set focus to -1, and
showing the menu left it there. Primary applied the condition
`fw == NULL || !ui_nav_is_focusable(fw)` in `src/services/ui/ui.c`, allowing the
existing `ui_nav_first_focus(scene)` recovery when the menu reappears.

`test_app_roundtrip_via_input_ids_only`
checks menu -> display -> contrast -> Back -> Back using only numeric INPUT IDs
(`0,0,1,1`), with intermediate screen, visibility and framebuffer assertions.
It remains a normal regression with no action injection or xfail.
The separate action-injection subscriber/logic test remains unchanged.
Pre-fix reproduction: the initial Menu checkpoint passed; at INPUT IDs `[0]`,
expected Display screen 1 but observed Menu screen 0. The focused regression
reported `1 failed in 8.59s`. Primary owns the applied production change and
the post-fix six-test suite run; its result is reported separately.

This does not execute `app_main`, physical drivers, radio/metrics/input/RPC tasks
or NVS persistence. Selectable GPIO ingress and interactive Studio integration
remain pending. Bounded release/tick/hot display ingress is implemented in host source;
actual rebuilt default/app behavior remains unverified. No production source changes
were required for the scheduler/subscribers.

The driver uses the current SSD1363 256x128 gray4 production configuration.
ESPOS is the umbrella tooling environment; TabOS retains its Tab5 firmware
name. The first release scope is Tab5 and existing TabOS boards/infrastructure;
no repository merge, firmware rename or additional target is implied. Existing
ESPOS formats/profiles/IDs stay intact. Tab5/color requires its actual
renderer/driver adapter and integration; this result does not establish that
support. The generic scheduling/transport seam remains available. Physical
display correctness, timing, RF, sensors and persistence are unverified.

### Child/wrapper JSON seam correction (2026-10-14)

The C child previously emitted `simulation: true`, while the Python wrapper
rejected any child `simulation` field to protect its own structured provenance.
That mismatch made successful default/app child output fail in the wrapper.
The C child now emits the separate boolean `runtime_simulation: true`; the
wrapper requires that exact boolean and alone supplies `simulation` with
`hardware_transport: mock`, the requested initial state and reported final state.
Any child-owned `simulation`, `hardware_transport`, `initial_display` or
`final_display` field remains rejected, including otherwise well-formed output.

Regressions use the exact default and app JSON shapes, retain UTF-8 text decoding,
reject ambiguous runtime markers/forged provenance and handle empty output
explicitly. These are Python seam/fixture and C source-contract tests only.
Neither the compiler nor the C simulator executable was run for this correction;
an actual rebuilt default/app runtime check remains required.

### Bounded release/tick ingress (2026-10-14)

Both default and `--app` accept the following ordered, comma-separated CLI steps.
The Python API takes an exact builtin list/tuple of exact builtin integers or
strings with the same meaning; numeric strings are CLI-only conveniences.

| Step | Meaning | Bounds |
| --- | --- | --- |
| `0` through `255` | Legacy button press, `TOP_INPUT_BTN`, `pressed=1` | Exact integer in Python; 1-3 ASCII digits in CLI |
| `button:<id>:press` | Explicit button press on the same production topic | Canonical decimal ID 0-255 |
| `button:<id>:release` | Button release on the same production topic, `pressed=0` | Canonical decimal ID 0-255 |
| `tick:<count>` | Advance virtual time without injecting a button | Canonical decimal 1-1000; each tick is 10 ms |
| `display:<state>` | Change the mock transport during the run and request a real UI repaint | Exact `connected`, `disconnected` or `error`; 50 ms / five ticks |
| `action:<id>:<value>` | Existing `TOP_UI_ACTION` injection (`--app` only) | ASCII ID `[A-Za-z0-9_.-]{1,31}`, 1-9 ASCII value digits |
| `cmd:<kind>:<id>:<value>` | Existing `TOP_UI_CMD` injection (`--app` only) | Kind 2, 3 or 20; same ID/value bounds |

Example ingress sequences (not executions verified in this change):
`button:0:press,tick:5,button:0:release,tick:100` or simply `tick:100`.
The total advance allowance is 6000 ticks (60 seconds), counting five ticks
for each non-tick event. Fixed startup offsets are outside this allowance.
At most 256 steps are allowed even if their total time fits. Repeated edges
are allowed and retain caller order; the host does not synthesize releases,
debounce, deduplicate edges or manufacture widget state.

Canonical button/tick numbers reject leading zeroes, signs, Unicode digits,
floats, whitespace, NULs and extra fields. Legacy numeric CLI inputs may use
leading zeroes within the three-digit bound (e.g. `000`). Empty CLI text is an
empty sequence; empty comma fields are errors, including trailing commas.
Arbitrary paths, executable names and commands cannot be ingress steps.
Validation happens before compiler discovery, path checks, generation, temporary
directory creation or child execution. The C runner separately parses the whole
bounded sequence before starting tasks or saving a frame.

Default mode delivers parsed edges to the existing `ui_task` receive shim. Its
numeric-only timestamps retain the first input at 100 ms and +50 ms thereafter.
Tick-only steps advance `esp_timer_set_mock_time` by 10 ms per receive iteration
and return through the existing UI timeout path, which owns flash/toast/animation
updates. The default receive shim retains its deterministic timeout policy;
it does not emulate FreeRTOS queue wait deadlines. A release is delivered to the
production task as a release; the UI's existing `pressed` condition decides
whether activation occurs.

App mode publishes press/release messages through the existing production bus
and UI/app/logic subscribers. Non-tick events preserve the previous input/drain,
aggregate tick publication and 50 ms scheduler advance. Each explicit tick
advances the existing scheduler by 10 ms, increments the tick counter, publishes
`TOP_TICK_10MS`, and drains the same tasks. There is no frontend screen model.
Frame-save failure now still stops app/UI/logic tasks and destroys the scheduler
and bus before returning exit code 3; it does not emit successful JSON.

`runtime_simulation: true` remains the exact required child boolean; `simulation`
remains wrapper-owned. Forged child transport provenance, malformed runtime
markers and invalid text encoding remain errors with owned build cleanup.

Evidence is Python contract/wrapper fixtures and C source-contract checks only.
The compiler and C runtime are mocked in wrapper tests. Tests cover edge/tick
boundaries, all 256 button IDs, all 1-1000 tick counts, combined time budgets,
strict types, malformed/path/command inputs, CLI ordering, validation before
compiler/filesystem work, display modes, confirmed/unconfirmed failure cleanup,
provenance rejection and source wiring in both modes. The final isolated run
passed 657 tests (no failures or skips); results are in
`C:/Sumilek-git/worker-patches/simulator-ingress-20261014-f00cae05945f4b29b53262c83e2a3600/run2/results.xml`.
Tests were copied to that evidence directory and run with a local pytest config,
repository conftest excluded, cache provider disabled and bytecode writes disabled.
All test fixtures remained under the same fresh evidence directory.
No GCC/MSVC, native C binary, GUI, firmware, SDK/Core/UI header inspection or
hardware execution was performed.
Actual default/app subscriber behavior, timeout/animation timing, framebuffer
results under disconnected/error transport and native cleanup remain unverified.

### Display disconnect/error/reconnect during a run (2026-10-14)

Both default and app mode now accept `display:connected`,
`display:disconnected` and `display:error` interleaved with numeric input,
button press/release, tick steps and supported app action/command events.
`--display` configures only the initial state. A reconnect uses
`display:connected`; `display:reconnect` is not an alias. Exact ASCII spelling
is required; types, whitespace, case variants, NULs, extra fields, paths and
commands are rejected before compiler/filesystem work. Each display event
consumes one of the 256 steps and five of the 6000 total advance ticks; existing
button/tick bounds remain unchanged. Duplicate state requests are allowed and
request a repaint too.

Example sequence, not a verified native execution:
`button:0:press,display:disconnected,tick:10,button:0:release,display:error,tick:5,display:connected`.

The C runner parses the entire sequence before tasks start. At each display
step it updates the existing driver's `sim_display_status`, which is read by
panel/configuration/frame/data operations. Disconnected returns
`ESP_ERR_NOT_FOUND`; error returns -1; connected returns `ESP_OK`. The existing
data-write guard keeps the last accepted captured frame unchanged during
transport failure. It does not clear the captured frame on disconnect/error.
No driver source change was needed for this live status seam.

Changing transport status alone would leave a stale frame: the production UI
clears its dirty region after a failed flush. The host therefore constructs the
existing supported `TOP_RPC_CALL` / `set_bg` message using the current
`store_get_conf().bg_rgb`. The existing in-memory store stub returns that color
and the production RPC handler writes back the same RGB, updates the same fill
level and requests `ui_dirty_full`. The actual production renderer flushes the
current widgets/focus/editor/scene through the driver. This is a same-color
repaint request, not a background/scene change or a synthetic widget model.
No arbitrary RPC ingress is exposed. In default mode the receive shim delivers
that message on the existing UI path and advances its clock using the ordinary
50 ms policy. In app mode the existing bus delivers it, the existing scheduler
drains subscribers, then five ordinary 10 ms virtual ticks are advanced and
published. Initial disconnected/error runs can likewise recover via a later
connected step; actual rebuilt behavior still requires verification.

The child JSON retains `runtime_simulation: true` and reports its actual final
mock-driver variable as integer `display_status` (0, 261, or -1). The wrapper
requires that exact builtin integer, derives `simulation.final_display` from
the reported value, and compares it with the last validated display event.
A missing, boolean, float, string, unknown or mismatched status fails; final
state is never filled in from the requested event sequence. Wrapper-owned
`simulation.initial_display` holds the configured initial value, and legacy
`simulation.display` remains its alias. Top-level child transport/provenance
fields and any duplicate JSON keys are rejected. This is mock runtime reporting,
not physical transport verification. Decode/process failures retain the existing
confirmed/unconfirmed owned-build cleanup rules.

Observed: 845 Python contract/wrapper fixture and C source-contract tests passed,
with no failures or skips. JUnit evidence, isolated fixture files, test copies
and before/after source snapshots are under
`C:/Sumilek-git/worker-patches/simulator-hot-display-20261014-712b496367764444ae08d94ba747ae7b`.
The wrapper compiler/C process was mocked. Tests cover hot ordering, all three
initial and final states in both modes, exact grammar/types, budgets, validation
before filesystem/compiler work, status/provenance/duplicate-key rejection,
cleanup, and C source links from ingress to live driver and production repaint.
Repository conftest was excluded, bytecode writes and pytest cache were disabled,
and fixtures were kept in the fresh evidence directory.

No production source was edited, no SDK/Core/IDF/UI header was inspected, and no
compiler/native C binary/GUI/hardware was executed. Actual native disconnect,
failed-frame retention, reconnect repaint, subscriber/timeout ordering, pixels
and cleanup remain unverified until an allowed future build/runtime check.
