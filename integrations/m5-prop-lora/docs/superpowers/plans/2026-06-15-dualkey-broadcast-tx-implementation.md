# DualKey Broadcast TX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new Chain DualKey + Unit C6L broadcast controller for blue LED set-state and one-shot barrel effect.

**Architecture:** Add a compact `PropAction` frame to the shared protocol, gate DinMeter broadcast acceptance to that one frame type, and add a new PlatformIO `firmware/dualkey-tx` project that sends no-ACK broadcast frames through the existing C6L UART modem. The receiver remains the action authority and suppresses duplicate events through the existing replay window.

**Tech Stack:** C++17/Arduino PlatformIO, shared `prop_protocol`, pytest parity tests, host C++ tests through `tools/run_host_tests.ps1`.

---

### Task 1: Shared Protocol PropAction

**Files:**
- Modify: `integrations/m5-prop-lora/shared/protocol/prop_protocol.h`
- Modify: `integrations/m5-prop-lora/shared/protocol/protocol.py`
- Test: `integrations/m5-prop-lora/tests/test_protocol.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert `FrameType.PROP_ACTION == 12`, `encode_prop_action_payload(1, 1, 7)` returns six bytes, reserved action/value ranges are rejected, and C++ constants are mirrored by Python.

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest integrations/m5-prop-lora/tests/test_protocol.py -q`
Expected: failures for missing `PROP_ACTION` and missing payload helpers.

- [ ] **Step 3: Implement protocol helpers**

Add `FrameType::PropAction = 12`, `PROP_ACTION_BLUE_SET = 1`, `PROP_ACTION_BARREL_EFFECT = 2`, `PROP_ACTION_PAYLOAD_LENGTH = 6`, and C++/Python encode/parse helpers with payload layout `[action, value, event_id:u32be]`.

- [ ] **Step 4: Run protocol tests**

Run: `python -m pytest integrations/m5-prop-lora/tests/test_protocol.py -q`
Expected: pass.

### Task 2: DinMeter Broadcast Action Receiver

**Files:**
- Modify: `integrations/m5-prop-lora/firmware/din-rx/src/prop_rx.cpp`
- Test: `integrations/m5-prop-lora/tests/test_project_sources.py`

- [ ] **Step 1: Write failing source-guard tests**

Add tests proving `PropAction` accepts `destination == 0xFF` while legacy frames still require `destination == PROP_SOURCE`, and that the handler parses `parsePropActionPayload`.

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest integrations/m5-prop-lora/tests/test_project_sources.py -q`
Expected: failures for absent broadcast gate and absent handler.

- [ ] **Step 3: Implement receiver gate and handler**

Allow broadcast only when `frame.type == FrameType::PropAction`. Add handler after `RemoteLed` and before safety ARM/FIRE. `BLUE_SET` sets the existing blue/default lane state directly. `BARREL_EFFECT` calls the existing local/barrel fire path once. Duplicate replay drops naturally before the handler.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest integrations/m5-prop-lora/tests/test_project_sources.py -q`
Expected: pass.

### Task 3: DualKey TX Firmware

**Files:**
- Create: `integrations/m5-prop-lora/firmware/dualkey-tx/platformio.ini`
- Create: `integrations/m5-prop-lora/firmware/dualkey-tx/src/main.cpp`
- Create: `integrations/m5-prop-lora/firmware/dualkey-tx/src/dualkey_tx_logic.h`
- Test: `integrations/m5-prop-lora/firmware/tests/test_dualkey_tx_logic.cpp`
- Test: `integrations/m5-prop-lora/tests/test_dualkey_tx_project.py`

- [ ] **Step 1: Write failing tests**

Add a host C++ test for button edge behavior and a Python source test that verifies no palette/setup frames are emitted, `FF ` is used, and C147 pins match M5 docs.

- [ ] **Step 2: Run failing tests**

Run: `powershell -ExecutionPolicy Bypass -File integrations/m5-prop-lora/tools/run_host_tests.ps1`
Run: `python -m pytest integrations/m5-prop-lora/tests/test_dualkey_tx_project.py -q`
Expected: failures for missing firmware files and missing logic.

- [ ] **Step 3: Implement firmware**

Create `DualKeyTxLogic` with debounce/edge detection and two events: `BlueSet` and `BarrelEffect`. In `main.cpp`, read C147 keys G0/G17, use UART2 on G5/G6 by default, encode `PropAction` frames to `destination = 0xFF`, and send `FF <hex>\n` to C6L.

- [ ] **Step 4: Run focused tests and build**

Run: `powershell -ExecutionPolicy Bypass -File integrations/m5-prop-lora/tools/run_host_tests.ps1`
Run: `python -m pytest integrations/m5-prop-lora/tests/test_dualkey_tx_project.py -q`
Run: `pio run -d integrations/m5-prop-lora/firmware/dualkey-tx -e chain-dualkey-c147`
Expected: pass/build success.

### Task 4: Regression

**Files:**
- Existing tests and firmware build scripts.

- [ ] **Step 1: Run Python tests**

Run: `python -m pytest integrations/m5-prop-lora/tests -q`
Expected: pass.

- [ ] **Step 2: Run host C++ tests**

Run: `powershell -ExecutionPolicy Bypass -File integrations/m5-prop-lora/tools/run_host_tests.ps1`
Expected: pass.

- [ ] **Step 3: Run key firmware builds**

Run: `pio run -d integrations/m5-prop-lora/firmware/c6l-modem -e m5stack-c6l`
Run: `pio run -d integrations/m5-prop-lora/firmware/din-rx -e esp32-s3-devkitc-1`
Run: `pio run -d integrations/m5-prop-lora/firmware/dualkey-tx -e chain-dualkey-c147`
Expected: build success.

