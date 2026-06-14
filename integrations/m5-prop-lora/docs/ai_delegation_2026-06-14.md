# AI Delegation Handoff - 2026-06-14

Branch: `work/2026-06-14-three-device-stack`

Purpose: keep the current three-device M5/DinMeter work focused and reviewable.
This branch is for the M5 Dial odpalovac, M5StickS3 Terminal, and DinMeter
receiver/electronics path only. Do not use it for unrelated ESPOS UI refactors.

## Current System Truth

### 1. M5 Dial odpalovac

Role: radio fire controller.

Current constraints:
- Owns LoRa/C6 modem command flow and safety-state display.
- Does not own setup editing.
- Long press/back only reports `SETUP NA TERMINALU`.
- Active UI path is command-only.

Primary files:
- `firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp`
- `firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h`
- `firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp`
- `firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.h`
- `firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h`
- `tools/preview_prop_tx.py`
- `tests/test_prop_tx_gui_sim.py`
- `tests/test_project_sources.py`

Current render:
- `build/preview/01_ready_action.png`

### 2. M5StickS3 Terminal

Role: physical setup editor with five direct lanes.

Current constraints:
- No LoRa/C6 module.
- Five faders control brightness; 0 percent means normally off, above 0 percent
  means normally on.
- Five chain encoders step the named color palette.
- Encoder buttons toggle whether the lane changes state during fire.
- Upload switch sends setup over USB/Grove bridge.
- Second U206 switch sends the global SIM_FIRE preview command over the setup
  link.
- External OLED is lane-only and shows no status/menu text.
- Built-in M5StickS3 display is reserved for status feedback such as uploaded/problem.

Primary files:
- `firmware/sticks3-terminal/src/terminal_setup.h`
- `firmware/sticks3-terminal/src/terminal_external_display.h`
- `firmware/sticks3-terminal/src/terminal_physical_tick.h`
- `firmware/sticks3-terminal/src/terminal_control_surface.h`
- `firmware/sticks3-terminal/src/terminal_app_logic.h`
- `firmware/sticks3-terminal/src/main.cpp`
- `shared/terminal/terminal_setup_link.h`
- `shared/terminal/terminal_setup_receiver.h`
- `firmware/tests/test_terminal_*.cpp`
- `tests/test_terminal_setup_project.py`

Current external OLED format:

```text
1 CERVENA 000 J000 ZE
2 ZLUTA   045 J025 VN
3 ZELENA  120 J050 ZE
4 MODRA   240 J075 VN
5 CERVENA 359 J100 ZE
```

Current render:
- `build/preview/terminal_external_oled_128x64_x4.png`

### 3. DinMeter / rekvizita

Role: receiver-side safety authority and prop-side effect/electronics endpoint.

Current constraints:
- Receiver remains the authority for safety enforcement.
- Applies terminal setup only through validated USB setup receiver path.
- Handles preview/fire/stop and LED effect behavior.
- Display remains indication-oriented, not a setup editor.

Primary files:
- `firmware/din-rx/src/prop_rx.cpp`
- `tools/preview_din_rx_render.py`
- `tests/test_din_rx_led_sim.py`
- `tests/test_preview_render.py`
- `tests/test_sim_link_safety.py`
- `shared/protocol/prop_protocol.h`
- `shared/protocol/protocol.py`
- `shared/terminal/terminal_setup_apply.h`
- `shared/terminal/terminal_setup_receiver.h`

Current render:
- `build/preview_dinrx/main_preview.png`

## Essential Local Checks

Run these before claiming a change is ready:

```powershell
python integrations/m5-prop-lora/tools/preview_prop_tx.py
python integrations/m5-prop-lora/tools/preview_din_rx_render.py
python -m pytest integrations/m5-prop-lora/tests -q
& integrations\m5-prop-lora\tools\run_host_tests.ps1
```

For full repository confidence:

```powershell
python -m pytest -q
```

For Dial firmware compile:

```powershell
& C:\Users\atrep\esp\esp-idf-v5.1.3\export.ps1
idf.py -C integrations\m5-prop-lora\firmware\dial-tx build
```

## Claude Opus Delegation

Use Claude Opus for code-path review, race/safety reasoning, and implementation
suggestions. Do not give it API keys. Run it read-only: inspect, cite, and
propose patches; do not edit files or run mutating commands. Prefer narrow
prompts with an explicit file scope.

Example:

```powershell
npx @anthropic-ai/claude-code --model opus --permission-mode plan -p "Review this branch for the three-device M5 stack. Focus only on Dial command-only flow, Terminal setup editor/OLED readability, and DinMeter setup receiver safety. Return blockers first, cite files, and do not edit files or run mutating commands."
```

Good Claude tasks:
- Check Dial setup/editor removal did not break arm/fire/stop flow.
- Check Terminal upload/revert logic for stale ACKs and in-flight edits.
- Check DinMeter setup receiver atomicity and safety fail-closed behavior.
- Propose small focused patches with tests, but leave edits to Codex.

Avoid:
- Broad repo-wide refactors.
- Generated dependency churn.
- Any prompt that includes concrete secrets.

## Gemini Delegation

Use Gemini for visual/design review and independent text review through existing
repo scripts. Do not commit `.gemini_api_key`; use environment or local ignored
key file only.

Visual review:

```powershell
cd integrations\m5-prop-lora
python tools/preview_prop_tx.py
python tools/preview_terminal_oled.py
python tools/gemini_jury.py --dir build/preview --image contact.png --device "M5 Dial (round 240x240)" --per 20 --workers 3
python tools/preview_din_rx_render.py
python tools/gemini_jury.py --dir build/preview --image terminal_external_oled_128x64_x4.png --device "M5StickS3 Terminal OLED" --per 20 --workers 3
python tools/gemini_jury.py --dir build/preview_dinrx --image contact.png --device "M5 DinMeter (240x135)" --per 20 --workers 3
```

Text/code review:

```powershell
cd integrations\m5-prop-lora
python tools/gemini_code_review.py --out build/reviews/gemini_code_review.md `
  --target firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp `
  --target firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h `
  --target firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp `
  --target firmware/sticks3-terminal/src `
  --target firmware/din-rx/src/prop_rx.cpp `
  --target firmware/din-rx/src/prop_config.h `
  --target shared/protocol `
  --target shared/terminal `
  --target uiflow/dial `
  --target tools/gemini_jury.py `
  --target tools/gemini_dinrx_review.py `
  --target tools/gemini_code_review.py `
  --target docs/first_upload_runbook.md `
  --max-chars 500000
```

Good Gemini tasks:
- Detect unsafe/ambiguous safety-state screens.
- Detect text collisions or edge clipping in renders.
- Review docs/runbooks for missing acceptance gates.
- Review artifact/offline workflow assumptions.

Avoid:
- Asking Gemini to be source of truth for hardware safety.
- Accepting visual approval when local tests or receiver safety checks fail.

## Current Review Split

Claude Opus should own:
- C++/MicroPython logic review.
- Race conditions, stale ACK handling, revert semantics.
- Test design for deterministic behavior.

Gemini should own:
- Render clarity and safety-state ambiguity.
- Operator-facing language/readability.
- Independent review of docs and acceptance checklist.

Figma should own:
- Read-only visual inspection only until a Figma file/node is explicitly provided
  or mutation is explicitly approved.
- Generated contact sheets are the source of visual truth for now; do not mutate
  Figma files from this branch.

Codex should own:
- Applying patches.
- Running deterministic tests/builds.
- Keeping branch scope small and preserving user changes.

## Do Not Mix Into This Branch

- General ESPOS UI styling unrelated to the M5/DinMeter stack.
- Secrets, real API keys, or runtime HMAC keys.
- Hardware pin finalization unless verified on bench.
- Push to `main`.

## Next Useful Work

1. Re-run Gemini visual jury after the OLED readability change.
2. Ask Claude Opus for a focused safety/code review of Terminal upload and DinMeter receiver setup apply.
3. Convert useful findings into one patch at a time with tests first.
4. Prepare first-upload checklist per device after the code review is clean.
