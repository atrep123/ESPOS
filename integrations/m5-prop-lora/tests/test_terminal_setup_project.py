import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.exists(), f"{relative_path} does not exist"
    return path.read_text(encoding="utf-8")


def terminal_guard_text() -> str:
    paths = [
        ROOT / "docs/terminal_architecture.md",
    ]
    terminal_root = ROOT / "firmware/sticks3-terminal"
    for path in terminal_root.rglob("*"):
        if path.is_file() and path.suffix in {".cpp", ".h", ".ini", ".md", ".py"}:
            parts = path.relative_to(terminal_root).parts
            if parts[0].startswith(".") or parts[0] in {"build"}:
                continue
            paths.append(path)
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(paths))


def test_sticks3_terminal_setup_project_files_exist() -> None:
    required = [
        "firmware/sticks3-terminal/platformio.ini",
        "firmware/sticks3-terminal/apply_release_flags.py",
        "firmware/sticks3-terminal/README.md",
        "firmware/sticks3-terminal/src/main.cpp",
        "firmware/sticks3-terminal/src/drivers/terminal_chain_encoder_driver.h",
        "firmware/sticks3-terminal/src/drivers/terminal_external_oled.h",
        "firmware/sticks3-terminal/src/drivers/terminal_fader_driver.h",
        "firmware/sticks3-terminal/src/drivers/terminal_switch_driver.h",
        "firmware/sticks3-terminal/src/terminal_config.h",
        "firmware/sticks3-terminal/src/terminal_control_surface.h",
        "firmware/sticks3-terminal/src/terminal_encoder_filter.h",
        "firmware/sticks3-terminal/src/terminal_external_display.h",
        "firmware/sticks3-terminal/src/terminal_fader_filter.h",
        "firmware/sticks3-terminal/src/terminal_app_logic.h",
        "firmware/sticks3-terminal/src/terminal_physical_tick.h",
        "firmware/sticks3-terminal/src/terminal_hardware_topology.h",
        "firmware/sticks3-terminal/src/terminal_setup.h",
        "firmware/sticks3-terminal/src/terminal_switch_debounce.h",
        "firmware/sticks3-terminal/src/terminal_switch_dispatch.h",
        "firmware/sticks3-terminal/src/terminal_switch_pipeline.h",
        "firmware/sticks3-terminal/src/terminal_switches.h",
        "firmware/sticks3-terminal/src/terminal_usb_link.h",
        "docs/terminal_architecture.md",
        "shared/terminal/terminal_color_definitions.h",
        "shared/terminal/terminal_setup_link.h",
        "shared/terminal/terminal_setup_apply.h",
        "shared/terminal/terminal_setup_receiver.h",
    ]
    for relative_path in required:
        assert (ROOT / relative_path).exists(), relative_path


def test_terminal_setup_link_contract_is_shared_and_host_tested() -> None:
    header = read("shared/terminal/terminal_setup_link.h")
    host_test = read("firmware/tests/test_terminal_setup_link.cpp")
    terminal_state = read("firmware/sticks3-terminal/src/terminal_setup.h")

    assert "namespace terminal_setup_link" in header
    assert "struct Lane" in header
    assert "struct SetupCommand" in header
    assert "requestId" in header
    assert "enum class CommandKind" in header
    assert "parseLine" in header
    assert "formatSetupLine" in header
    assert "formatSimFireLine" in header
    assert "formatResponseLine" in header
    assert "SETUP_OK" in header
    assert "SETUP_ERR" in header
    assert "parseLine" in host_test
    assert "parses setup request id" in host_test
    assert "formats SIM_FIRE line with request id" in host_test
    assert "SIM_FIRE 42" in host_test
    assert "formats request-scoped replies" in host_test
    assert "SETUP 42" in host_test
    assert "SETUP_OK 42" in host_test
    assert "rejects malformed setup lines" in host_test
    assert "parses named color setup line" in host_test
    assert "L4:368" in host_test
    assert "369" in host_test
    assert "formatSetupLine" in terminal_state
    assert "uploadLine(std::uint32_t requestId)" in terminal_state


def test_terminal_setup_apply_model_is_shared_and_host_tested() -> None:
    header = read("shared/terminal/terminal_setup_apply.h")
    colors = read("shared/terminal/terminal_color_definitions.h")
    host_test = read("firmware/tests/test_terminal_setup_apply.cpp")

    assert "namespace terminal_setup_apply" in header
    assert "terminal_color_definitions" in header
    assert "struct Rgb" in header
    assert "struct AppliedLane" in header
    assert "struct AppliedSetup" in header
    assert "percentToByte" in header
    assert "hueToRgb" in header
    assert "applySetupCommand" in header
    assert "onMask" in header
    assert "effectMask" in header
    assert "effectPreviewMask" in header
    assert "maps percent brightness to byte range" in host_test
    assert "maps hue to primary RGB colors" in host_test
    assert "named palette covers typical colors including white" in host_test
    assert "fire change mask includes off lanes selected for state inversion" in host_test
    assert "namespace terminal_color_definitions" in colors
    assert "COLOR_COUNT = 9" in colors
    assert "CERVENA" in colors
    assert "ORANZ" in colors
    assert "ZLUTA" in colors
    assert "ZELENA" in colors
    assert "TYRKYS" in colors
    assert "MODRA" in colors
    assert "FIALOVA" in colors
    assert "RUZOVA" in colors
    assert "BILA" in colors
    assert "NAMED_COLOR_CODE_BASE = 360" in colors
    assert "MAX_NAMED_COLOR_CODE" in colors
    assert "WHITE_WIRE_CODE = MAX_NAMED_COLOR_CODE" in colors


def test_terminal_setup_receiver_adapter_is_radio_free_and_host_tested() -> None:
    header = read("shared/terminal/terminal_setup_receiver.h")
    host_test = read("firmware/tests/test_terminal_setup_receiver.cpp")

    assert "namespace terminal_setup_receiver" in header
    assert "ReceiverCallbacks" in header
    assert "ReplyResult" in header
    assert "handleLine" in header
    assert "handleLineResult" in header
    assert "replyLine" in header
    assert "requestId" in header
    assert "terminal_setup_link::parseLine" in header
    assert "terminal_setup_apply::applySetupCommand" in header
    assert "SETUP_OK" in header
    assert "SETUP_ERR" in header
    assert "valid SETUP echoes request id" in host_test
    assert "valid SETUP applies named white on lane 3" in host_test
    assert "L3:368" in host_test
    assert "Rgb{255, 255, 255}" in host_test
    assert "malformed SETUP echoes request id without commit" in host_test
    assert "SETUP_OK 42" in host_test
    assert "SETUP_ERR 42" in host_test
    assert "SIM_FIRE uses only preview callback" in host_test
    assert "SIM_FIRE echoes request id" in host_test
    assert "unknown command returns ERR without callbacks" in host_test

    forbidden = [
        "propSerial",
        "FrameType",
        "encodeFrame",
        "SEND ",
        "FF ",
        "ACK ",
        "_lockoutSeq",
        "tryLocalFire",
        "triggerOdpal",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_din_rx_consumes_terminal_usb_setup_parser_without_radio_path() -> None:
    cpp = read("firmware/din-rx/src/prop_rx.cpp")
    ini = read("firmware/din-rx/platformio.ini")

    assert "-I../../shared/terminal" in ini
    assert '#include "terminal_setup_receiver.h"' in cpp
    assert "readUsbSetup()" in cpp
    assert "terminal_setup_receiver::handleLineResult" in cpp
    assert "terminal_setup_receiver::replyLine" in cpp
    assert "Serial.println(replyLine.c_str())" in cpp
    assert "readUsbSetup();" in cpp
    assert "_usbSetupLine" in cpp
    assert "_usbSetupOverflow" in cpp

    parser_section = cpp[
        cpp.index("void readUsbSetup()") : cpp.index("bool validateFrameRoute")
    ]
    forbidden = [
        "propSerial",
        "FrameType",
        "encodeFrame",
        "SEND ",
        "FF ",
        "ACK ",
        "_lockoutSeq",
        "tryLocalFire",
        "triggerOdpal",
    ]
    for needle in forbidden:
        assert needle not in parser_section, needle


def test_din_rx_terminal_setup_persists_single_blob_with_on_effect_masks() -> None:
    cpp = read("firmware/din-rx/src/prop_rx.cpp")

    assert "TERMINAL_SETUP_KEY" in cpp
    assert "PersistedTerminalSetup" in cpp
    assert "void loadTerminalSetupState()" in cpp
    assert "bool storeTerminalSetup(const terminal_setup_apply::AppliedSetup& setup)" in cpp
    assert "preferences.putBytes(TERMINAL_SETUP_KEY, &blob, sizeof(blob))" in cpp
    assert "loadTerminalSetupState();" in cpp

    load_section = cpp[
        cpp.index("void loadTerminalSetupState()") :
        cpp.index("bool storeTerminalSetup", cpp.index("void loadTerminalSetupState()"))
    ]
    assert "_led1On = (blob.onMask & (1U << 0)) != 0" in load_section
    assert "_led2On = (blob.onMask & (1U << 1)) != 0" in load_section
    assert "_led3RemoteOn = (blob.onMask & (1U << 2)) != 0" in load_section
    assert "_led5RemoteOn = (blob.onMask & (1U << 4)) != 0" in load_section
    assert "_terminalEffectMask = blob.effectMask & validMask" in load_section
    assert "_terminalPreviewMask = _terminalEffectMask" in load_section

    commit_start = cpp.index("bool commitTerminalSetup(const")
    commit_section = cpp[
        commit_start :
        cpp.index("bool previewTerminalSimFire", commit_start)
    ]
    assert "bool terminalSetupSafeToCommit() const" in cpp
    safe_section = cpp[
        cpp.index("bool terminalSetupSafeToCommit() const") :
        cpp.index("bool commitTerminalSetup", cpp.index("bool terminalSetupSafeToCommit() const"))
    ]
    assert "return !_lockout && !_masterOffInhibit && !_armed && !_odpalActive;" in safe_section
    assert "if (!terminalSetupSafeToCommit())" in commit_section
    assert commit_section.index("if (!terminalSetupSafeToCommit())") < commit_section.index("RenderColor oldColors")
    assert "const bool savedSetup = storeTerminalSetup(setup)" in commit_section
    assert "sendLedColorSet();" not in commit_section
    assert "sendPaletteSet();" not in commit_section
    assert "void sendPaletteSet()" in cpp
    palette_sync_section = cpp[
        cpp.index("void sendPaletteSet()") :
        cpp.index("// Immediate ack", cpp.index("void sendPaletteSet()"))
    ]
    assert "prop_protocol::FrameType::PaletteSet" in palette_sync_section
    assert "prop_protocol::encodePalettePayload(pal, f.payload)" in palette_sync_section
    assert "for (int i = 0; i < LED_COUNT; ++i)" in palette_sync_section
    assert "pal.colors.push_back" in palette_sync_section
    assert "propSerial.print(\"FF \");" in palette_sync_section
    assert "storeLedColors(false)" not in commit_section
    assert "storeLedBrightness()" not in commit_section


def test_din_rx_terminal_sim_fire_uses_preview_mask_without_live_fire_path() -> None:
    cpp = read("firmware/din-rx/src/prop_rx.cpp")

    assert "_terminalEffectMask = setup.effectMask" in cpp
    assert "_terminalPreviewMask = setup.effectPreviewMask" in cpp
    assert "_terminalPreviewUntilMs" in cpp
    assert "_terminalPreviewMask" in cpp

    preview_section = cpp[
        cpp.index("bool previewTerminalSimFire()") :
        cpp.index("#if DEBUG_HUD", cpp.index("bool previewTerminalSimFire()"))
    ]
    assert "_lockout || _masterOffInhibit" in preview_section
    assert "_armed || _odpalActive" in preview_section
    assert "_terminalPreviewUntilMs = 0" in preview_section
    assert 'setStatus("STOP")' in preview_section
    assert "_terminalPreviewUntilMs = millis() + PREVIEW_OVERLAY_MS" in preview_section
    assert "markLocalDirty()" in preview_section
    for needle in [
        "triggerOdpal",
        "tryLocalFire",
        "_lockoutSeq",
        "prop_protocol::decodeFrame",
        "FrameType::Fire",
    ]:
        assert needle not in preview_section, needle

    local_control = cpp[
        cpp.index("void applyLocalControl()") :
        cpp.index("void applyLocalControlIfIdle()")
    ]
    assert "_terminalPreviewUntilMs" in local_control
    assert "_terminalPreviewMask &" in local_control
    assert "localColor(i)" in local_control
    assert local_control.index("if (_masterOffInhibit)") < local_control.index("_terminalPreviewUntilMs != 0")


def test_din_rx_fire_respects_terminal_effect_mask_for_odpal_lane() -> None:
    cpp = read("firmware/din-rx/src/prop_rx.cpp")

    assert "TERMINAL_ODPAL_LANE = 3" in cpp
    assert "DEFAULT_TERMINAL_EFFECT_PREVIEW_MASK" in cpp
    assert "bool terminalEffectAllowsOdpal() const" in cpp
    allows_section = cpp[
        cpp.index("bool terminalEffectAllowsOdpal() const") :
        cpp.index("bool triggerOdpal()")
    ]
    assert "_terminalEffectMask & static_cast<std::uint8_t>(1U << TERMINAL_ODPAL_LANE)" in allows_section
    assert "_terminalPreviewMask" not in allows_section

    trigger_section = cpp[
        cpp.index("bool triggerOdpal()") :
        cpp.index("std::uint32_t odpalTotalMs() const")
    ]
    assert "if (!terminalEffectAllowsOdpal())" in trigger_section
    assert 'setStatus("ODPAL VYP")' in trigger_section
    assert "_terminalPreviewUntilMs = 0;" in trigger_section
    assert trigger_section.index("if (!terminalEffectAllowsOdpal())") < trigger_section.index("_odpalActive  = true")
    assert trigger_section.index("_terminalPreviewUntilMs = 0;") < trigger_section.index("_odpalStartMs = millis()")

    fire_section = cpp[
        cpp.index("if (frame.type == prop_protocol::FrameType::Fire)") :
        cpp.index("if (frame.type == prop_protocol::FrameType::Stop)")
    ]
    bad_payload_section = fire_section[
        fire_section.index("if (!applyLedPayload(frame.payload))") :
        fire_section.index("if (!triggerOdpal())")
    ]
    assert "_terminalPreviewUntilMs = 0;" in bad_payload_section
    assert "markLocalDirty();" in bad_payload_section
    assert bad_payload_section.index("_terminalPreviewUntilMs = 0;") < bad_payload_section.index('sendAckFrame(frame, "BAD_PAYLOAD")')
    assert "if (!triggerOdpal())" in fire_section
    assert 'sendAckFrame(frame, "NO_EFFECT")' in fire_section
    assert "scheduleFireAck(frame)" in fire_section
    no_effect_section = fire_section[
        fire_section.index("if (!triggerOdpal())") :
        fire_section.index("scheduleFireAck(frame)")
    ]
    assert 'sendAckFrame(frame, "NO_EFFECT")' in no_effect_section
    assert "return;" in no_effect_section
    assert "triggerOdpal();   // generic placeholder odpal" not in fire_section


def test_terminal_has_no_lora_c6_or_auth_sender_surface() -> None:
    combined = terminal_guard_text()

    forbidden = [
        "C6L",
        "LoRa",
        "prop_protocol",
        "prop_runtime_key",
        "FrameType",
        "HMAC",
        "PING",
        "STOP",
        "SEND ",
        "MODEM_UART",
        "PROP_SOURCE",
        "PROP_DESTINATION",
    ]
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_hardware_topology_matches_planned_control_surface() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_hardware_topology.h")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    host_test = read("firmware/tests/test_terminal_hardware_topology.cpp")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")
    hardware = read("docs/hardware.md")

    assert "namespace terminal_hardware_topology" in header
    assert "STICKS3_CONTROLLER_COUNT = 1" in header
    assert "CONTROL_LANE_COUNT = 5" in header
    assert "UNIT_FADER_COUNT = CONTROL_LANE_COUNT" in header
    assert "CHAIN_ENCODER_COUNT = CONTROL_LANE_COUNT" in header
    assert "MECHANICAL_SWITCH_COUNT = 2" in header
    assert "GROVE2USB_C_ADAPTER_COUNT = 2" in header
    assert "PAHUB_COUNT = 2" in header
    assert "EXTERNAL_OLED_COUNT = 1" in header
    assert "TERMINAL_HAS_LORA_MODULE = false" in header
    assert "PAHUB_CAN_ROUTE_ANALOG_FADERS = false" in header
    assert "GROVE2USB_ROLE_FINALIZED = false" in header
    assert "EXTERNAL_OLED_ROLE_FINALIZED = false" in header
    assert "LANE_CONTROLS_ARE_DIRECT_PHYSICAL_CONTROLS = true" in header
    assert "UNIT_FADERS_ARE_M5STACK_U123_B10K_SK6812 = true" in header
    assert "UNIT_FADER_SLIDER_OUTPUT_IS_ANALOG = true" in header
    assert "UNIT_FADER_RGB_OUTPUT_IS_SK6812_DATA = true" in header
    assert "UNIT_FADER_RGB_CONTROL_DEFERRED_FOR_FIRST_SLICE = true" in header
    assert "UNIT_FADER_RGB_LED_COUNT = 14" in header
    assert "STICKS3_HAT2_EXPOSES_TEN_GPIO_LABELS = true" in header
    assert "STICKS3_HAT2_G1_TO_G4_SHARE_INTERNAL_FUNCTIONS = true" in header
    assert "STICKS3_GROVE_G9_G10_RESERVED_FOR_REMAINING_TOPOLOGY = true" in header
    assert "STICKS3_G4_ADC_SMOKE_BUILDS_AND_UPLOADS = true" in header
    assert "STICKS3_G4_ADC_SMOKE_TRACKS_FADER_RANGE = true" in header
    assert "STICKS3_G4_ADC_SMOKE_ACCEPTED_AS_FADER_ADC = true" in header
    assert "STICKS3_G4_ADC_SMOKE_DIRECTION_IS_INVERTED = true" in header
    assert "UNIT_FADERS_HAVE_VERIFIED_SHARED_PIN_FOR_SLIDER_ONLY = true" in header
    assert "STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MIN = 0" in header
    assert "STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_MAX = 4095" in header
    assert "STICKS3_G4_ADC_SMOKE_OBSERVED_RAW_SPAN = 4095" in header
    assert "STICKS3_G4_ADC_SMOKE_PHYSICAL_BOTTOM_RAW = 4095" in header
    assert "STICKS3_G4_ADC_SMOKE_PHYSICAL_TOP_RAW = 0" in header
    assert "UNIT_FADERS_CAN_USE_FIVE_SAFE_DIRECT_STICKS3_ADC_WITH_REST_UNCHANGED = false" in header
    assert "UNIT_FADERS_REQUIRE_EXTERNAL_ADC_OR_VERIFIED_SHARED_PIN = true" in header
    assert "UNIT_FADERS_USE_PAHUB_PORTS_FOR_SIGNALS = false" in header
    assert "PAHUB_CAN_ROUTE_UNIT_FADER_RGB_DATA = false" in header
    assert "REQUIRED_FADER_ADC_COUNT_FOR_SLIDER_ONLY = 5" in header
    assert "SAFE_DIRECT_ADC_BUDGET_WITH_REST_UNCHANGED = 4" in header
    assert "PRIMARY_PAHUB_PORT_CHAIN_BRANCH = 0" in header
    assert "PRIMARY_PAHUB_PORT_POT5 = 1" in header
    assert "PRIMARY_PAHUB_PORT_POT4 = 2" in header
    assert "PRIMARY_PAHUB_PORT_EXTERNAL_DISPLAY = 3" in header
    assert "PRIMARY_PAHUB_PORT_SECONDARY_PAHUB = 5" in header
    assert "SECONDARY_PAHUB_PORT_POT3 = 2" in header
    assert "SECONDARY_PAHUB_PORT_POT2 = 3" in header
    assert "SECONDARY_PAHUB_PORT_POT1 = 4" in header
    assert "CHAIN_BRANCH_POSITION_ENCODER_LED5 = 0" in header
    assert "CHAIN_BRANCH_POSITION_ENCODER_LED1 = 4" in header
    assert "CHAIN_BRANCH_POSITION_UPLOAD_SWITCH = 5" in header
    assert "CHAIN_BRANCH_POSITION_SIM_FIRE_SWITCH = 6" in header
    assert "PHYSICAL_CHAIN_ORDER_IS_LED5_TO_LED1 = true" in header
    assert "LAST_CHAIN_SWITCH_IS_SIM_FIRE = true" in header
    assert '#include "terminal_hardware_topology.h"' in config
    assert "terminal_hardware_topology::CONTROL_LANE_COUNT" in config
    assert "planned hardware has one fader and one encoder per lane" in host_test
    assert "PaHUB is not allowed to route analog fader reads" in host_test
    assert "bench wiring uses primary and secondary PaHUB ports" in host_test
    assert "chain physical order is LED5 to LED1 then upload and sim-fire switch" in host_test
    assert "last chain switch is sim-fire" in host_test
    assert "fader modules are analog B10K with SK6812 RGB" in host_test
    assert "fader slider-only slice needs external ADC or verified shared pin" in host_test
    assert "G4 ADC smoke accepts G4 as shared fader ADC candidate" in host_test
    assert "Terminal hardware topology contract" in doc
    assert "Bench Wiring Snapshot 2026-06-14" in doc
    assert "Primary Pa.HUB port 0 carries the serial chain branch" in doc
    assert "Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch" in doc
    assert "Primary Pa.HUB port 5 goes to the secondary Pa.HUB v2.1" in doc
    assert "Pot1..Pot5 do not use Pa.HUB as their signal path" in doc
    assert "bare StickS3 direct" in doc
    assert "10-signal fader+RGB map is rejected" in doc
    assert "G1..G4` share internal" in doc
    assert "First fader slice is slider-only" in doc
    assert "Safe direct ADC budget is four candidates" in doc
    assert "G4 ADC smoke on 2026-06-14" in doc
    assert "tracked fader movement from raw 0 to 4095" in doc
    assert "verified shared-pin candidate" in doc
    assert "do not use IMU interrupt" in doc
    assert "Secondary Pa.HUB ports 2, 3, and 4 are reserved for now" in doc
    assert "LED1` through `LED5` remain stable" in doc
    assert "Pot1..Pot5 are M5Stack Unit Fader U123 modules" in doc
    assert "14x SK6812 programmable RGB LEDs" in doc
    assert "GND / 5V / RGB / Analog Input" in doc
    assert "must not be used as the final route for the analog slider output or the SK6812 RGB data line" in doc
    assert "5 Unit Faders" in doc
    assert "5 Chain Encoders" in doc
    assert "2 PaHUB" in doc
    assert "2 Grove2USB-C" in doc
    assert "Terminal has no radio module" in doc
    assert "Terminal hardware topology contract" in readme
    assert "Current bench wiring snapshot, 2026-06-14" in readme
    assert "Primary Pa.HUB port 0 is the serial chain branch" in readme
    assert "Pot1..Pot5 do not use Pa.HUB as their signal path" in readme
    assert "10-signal fader+RGB map is rejected" in readme
    assert "First fader slice is slider-only" in readme
    assert "Safe direct ADC budget is four candidates" in readme
    assert "G4 ADC smoke on 2026-06-14" in readme
    assert "tracked fader movement from raw 0 to 4095" in readme
    assert "verified shared-pin candidate" in readme
    assert "do not use IMU interrupt" in readme
    assert "physical encoder branch order is" in readme
    assert "Pot1..Pot5 are confirmed M5Stack Unit Fader U123 modules" in readme
    assert "Terminal has no radio module" in readme
    assert "M5StickS3 Terminal hardware status" in hardware
    assert "Current Terminal bench wiring snapshot, 2026-06-14" in hardware
    assert "Primary Pa.HUB port 0 is the serial branch" in hardware
    assert "Pot1..Pot5 do not use Pa.HUB as their signal path" in hardware
    assert "10-signal fader+RGB map is rejected" in hardware
    assert "First fader slice is slider-only" in hardware
    assert "Safe direct ADC budget is four candidates" in hardware
    assert "G4 ADC smoke on 2026-06-14" in hardware
    assert "tracked fader movement from raw 0 to 4095" in hardware
    assert "verified shared-pin candidate" in hardware
    assert "do not use IMU interrupt" in hardware
    assert "physical bottom is raw 4095" in hardware
    assert "rawMin greater than rawMax" in hardware
    assert "Pot1..Pot5 are confirmed M5Stack Unit Fader U123 modules" in hardware
    assert "Final backplane pin map is not confirmed" in hardware
    assert "external OLED controller and address are not confirmed" in hardware
    assert "Grove2USB-C role is not finalized" in hardware


def test_dial_keeps_lora_fire_and_loses_setup_ownership() -> None:
    doc = read("docs/terminal_architecture.md")
    app_header = read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h")
    app_cpp = read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
    config = read("firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h")
    uiflow_main = read("uiflow/dial/main.py")

    assert "Dial remains the radio fire controller" in doc
    assert "Dial does not own setup editing" in doc
    assert "Terminal has no radio module" in doc
    assert "Terminal owns setup editing" in doc
    assert "DinMeter remains the receiver-side safety authority" in doc
    assert "DIAL_SETUP_EDITOR_ENABLED" in config
    assert "false;  // Terminal owns setup editing; Dial stays fire-focused." in config
    uiflow_hold = uiflow_main[
        uiflow_main.index("def on_hold():") :
        uiflow_main.index("# ---------------------------------------------------------------------------", uiflow_main.index("def on_hold():"))
    ]
    assert 'set_status("SETUP NA TERMINALU", MODE_SETUP)' in uiflow_hold
    assert "MODE_SETUP_" not in uiflow_hold
    assert "palette_line" not in uiflow_hold
    assert "SETUP via long-press BACK" not in app_header
    assert "COMMAND<->SETUP" not in app_cpp
    assert "commits colours on leaving SETUP" not in app_cpp
    toggle_section = app_cpp[
        app_cpp.index("void PropTx::_toggle_mode()") :
        app_cpp.index("void PropTx::_handle_back()")
    ]
    assert '_set_status("SETUP NA TERMINALU")' in toggle_section
    assert "DIAL_SETUP_EDITOR_ENABLED" not in toggle_section
    assert "_data.mode" not in toggle_section
    assert "MODE_SETUP" not in toggle_section


def test_legacy_controller_doc_marks_terminal_setup_transition() -> None:
    doc = read("docs/M5_PROP_CONTROLLER.md")

    assert "2026-06-13 transition note" in doc
    assert "Terminal owns setup editing" in doc
    assert "Dial remains" in doc
    assert "receiver-side safety authority" in doc
    assert "ODPAL VYP" in doc
    assert "NO_EFFECT" in doc
    assert "nevznikne zadny deferred `FIRE` ACK" in doc


def test_five_lane_control_model_is_explicit() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_setup.h")

    assert "LANE_COUNT = 5" in header
    assert "setBrightness" in header
    assert "rotateHue" in header
    assert "paletteStepsFromEncoderDelta" in header
    assert "defaultLanes" in header
    assert "toggleOn" in header
    assert "setEffectLed" in header
    assert "commitAccepted" in header
    assert "commitRejected" in header
    assert "uploadDraft_" in header
    assert "simulateFire" in header
    assert "largeDisplayLine" in header
    assert "oledDisplayLine" in header
    assert "NAVIGATION" not in header
    assert "nextPage" not in header


def test_terminal_physical_control_surface_is_edge_based_and_radio_free() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_control_surface.h")
    host_test = read("firmware/tests/test_terminal_control_surface.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")

    assert "namespace terminal_control_surface" in header
    assert "struct LaneInput" in header
    assert "struct ControlSnapshot" in header
    assert "class ControlSurface" in header
    assert "apply(const ControlSnapshot&" in header
    assert "primeEdges" in header
    assert "sliderPercent" in header
    assert "encoderDelta" in header
    assert "encoderPressed" in header
    assert "effectPressed" in header
    assert "previousPressed_" in header
    assert "previousEffectPressed_" in header
    assert "encoder press toggles effect without changing power" in host_test
    assert "effect select rising edge toggles participation only" in host_test
    assert "effect select edges are independent per lane" in host_test
    assert "primed held encoder press does not toggle until release and repress" in host_test
    assert "empty snapshot does not dirty setup" in host_test
    assert '#include "terminal_control_surface.h"' in main
    assert "pollDirectControls" in main
    assert "primeDirectControls" in main
    assert "g_controls.primeEdges(snapshot)" in main

    forbidden = [
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
        "FIRE",
        "propSerial",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_fader_filter_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_fader_filter.h")
    host_test = read("firmware/tests/test_terminal_fader_filter.cpp")
    driver = read("firmware/sticks3-terminal/src/drivers/terminal_fader_driver.h")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_fader_filter" in header
    assert "RAW_SAMPLE_MISSING" in header
    assert "struct FaderCalibration" in header
    assert "class FaderFilter" in header
    assert "rawToPercent" in header
    assert "span == 0" in header
    assert "reverseSpan" in header
    assert "prime(std::size_t lane" in header
    assert "lockUntilPickup" in header
    assert "update(std::size_t lane" in header
    assert "reset()" in header
    assert "lastPercent_" in header
    assert "pickupPercent_" in header
    assert "raw to percent clamps and rounds" in host_test
    assert "inverted raw maps high raw to low brightness" in host_test
    assert "FaderCalibration calibration{4095, 0, 1}" in host_test
    assert "first valid sample always publishes" in host_test
    assert "missing sample does not overwrite last value" in host_test
    assert "deadband suppresses small percent jitter" in host_test
    assert "lanes filter independently" in host_test
    assert "reset makes next sample publish again" in host_test
    assert "prime records position without publishing" in host_test
    assert "lock until pickup suppresses rollback mismatch" in host_test
    assert "zero deadband follows changed percent only" in host_test
    assert "invalid lane is no-op" in host_test
    assert "terminal_fader_filter::FaderFilter" in driver
    assert "RAW_SAMPLE_MISSING" in driver
    assert "FADER_RAW_MIN" in config
    assert "FADER_RAW_MAX" in config
    assert "FADER_DEADBAND_PERCENT" in config
    assert "FADER_RAW_MIN != FADER_RAW_MAX" in config
    assert "fader raw calibration must have non-zero span" in config
    assert "fader filter" in doc
    assert "rawMin greater than rawMax" in doc
    assert "physical bottom is raw 4095" in doc
    assert "fader filter" in readme
    assert "rawMin greater than rawMax" in readme
    assert "physical bottom is raw 4095" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "analogRead",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_FIRE",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_encoder_filter_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_encoder_filter.h")
    host_test = read("firmware/tests/test_terminal_encoder_filter.cpp")
    driver = read("firmware/sticks3-terminal/src/drivers/terminal_chain_encoder_driver.h")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_encoder_filter" in header
    assert "ENCODER_POSITION_MISSING" in header
    assert "struct EncoderCalibration" in header
    assert "struct EncoderSample" in header
    assert "class EncoderFilter" in header
    assert "prime(std::size_t lane" in header
    assert "update(std::size_t lane" in header
    assert "reset()" in header
    assert "lastPosition_" in header
    assert "first absolute position primes without delta" in host_test
    assert "detent scale converts signed movement to degrees" in host_test
    assert "missing position does not create delta but passes buttons" in host_test
    assert "lanes track positions independently" in host_test
    assert "reset makes next position prime again" in host_test
    assert "invalid lane returns noop input" in host_test
    assert "prime with missing position does not block first valid delta" in host_test
    assert "button levels pass through without movement" in host_test
    assert "terminal_encoder_filter::EncoderFilter" in driver
    assert "ENCODER_POSITION_MISSING" in driver
    assert "ENCODER_DEGREES_PER_DETENT" in config
    assert "encoder filter" in doc
    assert "encoder filter" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "analogRead",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_FIRE",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_oled_lines_have_fixed_small_display_budget() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_setup.h")
    host_test = read("firmware/tests/test_terminal_setup.cpp")

    assert "OLED_LINE_MAX_CHARS = 21" in header
    assert "oledDisplayLine" in header
    assert "OLED operator summary fits 128x64 text budget" in host_test
    assert "OLED operator summary shows color brightness power and effect" in host_test


def test_terminal_external_display_frame_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_external_display.h")
    host_test = read("firmware/tests/test_terminal_external_display.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")

    assert "namespace terminal_external_display" in header
    assert "DISPLAY_ROW_COUNT = terminal_setup::LANE_COUNT" in header
    assert "OLED_WIDTH_PX = 128" in header
    assert "OLED_HEIGHT_PX = 64" in header
    assert "OLED_FONT_WIDTH_PX = 6" in header
    assert "OLED_ROW_HEIGHT_PX = 12" in header
    assert "COLOR_TEXT_MAX_CHARS = 7" in header
    assert "BRIGHTNESS_TEXT_MAX_CHARS = 4" in header
    assert "EFFECT_TEXT_CHARS = 3" in header
    assert "struct DisplayRect" in header
    assert "struct DisplayRowPlan" in header
    assert "struct DisplayRenderPlan" in header
    assert "struct DisplayRow" in header
    assert "struct DisplayFrame" in header
    assert "operator==" in header
    assert "renderPlan" in header
    assert "makeFrame" in header
    assert "color field must fit its 42px display slot" in header
    assert "effect text must fit the right status box" in header
    assert "display rows must fit 64px OLED height" in header
    assert "side controls keep two pixel outer gutter" in host_test
    assert "effect state uses inverted text without frame" in host_test
    assert "lane number box keeps extra right and bottom padding" in host_test
    assert "row grid is balanced and text baselines are aligned" in host_test
    assert ".resize(" not in header
    assert "five framed operator rows expose color brightness and effect" in host_test
    assert "rows fit framed display field budgets" in host_test
    assert "render plan fits 128x64 pixel budget" in host_test
    assert "effect state uses inverted text without frame" in host_test
    assert "frame equality detects visible lane value changes" in host_test
    assert "frame omits status and menu text" in host_test
    assert '#include "terminal_external_display.h"' in main
    assert "renderExternalDisplay" in main
    assert "renderExternalDisplayIfChanged" in main
    poll_direct_start = main.index("void pollDirectControls()")
    poll_direct_controls = main[poll_direct_start : main.index("bool uploadInFlight()", poll_direct_start)]
    assert "g_controls.apply(snapshot, g_setup)" in poll_direct_controls
    assert "renderExternalDisplayIfChanged()" in poll_direct_controls
    assert "drawStatusPanel()" not in poll_direct_controls

    forbidden = [
        "M5.Display",
        "Arduino.h",
        "M5Unified",
        "String",
        "millis",
        "digitalRead",
        "pinMode",
        "delay",
        "Serial",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "PING",
        "STOP",
        "SEND ",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_upload_commit_reverts_on_problem() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_setup.h")
    host_test = read("firmware/tests/test_terminal_setup.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    app_logic = read("firmware/sticks3-terminal/src/terminal_app_logic.h")

    assert "draft_ = saved_" in header
    assert "Status::Uploaded" in header
    assert "Status::Problem" in header
    assert "NAHRANO" in header
    assert "PROBLEM" in header
    assert "UPLOAD_ACK_TIMEOUT_MS" in config
    assert "USB_LINE_MAX" in config
    assert "physical edits during upload do not commit unsent values" in host_test
    assert "problem status stays latched after post-reject edit" in host_test
    assert "upload line remains snapshot while uploading" in host_test
    assert "SIM_FIRE ignored during upload keeps snapshot" in host_test
    assert "lockFadersToDraft" in app_logic
    assert "action.lockFadersToDraft = true" in app_logic
    assert "pollUploadTimeout" in main
    assert "g_faders.lockToDraft(g_setup)" in main
    assert "setup.commitRejected()" in app_logic
    assert "status_ != Status::Problem" in header


def test_terminal_usb_setup_link_is_exact_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_usb_link.h")
    host_test = read("firmware/tests/test_terminal_usb_link.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    app_logic = read("firmware/sticks3-terminal/src/terminal_app_logic.h")

    assert "namespace terminal_usb_link" in header
    assert "enum class UploadEvent" in header
    assert "enum class RequestKind" in header
    assert "class UsbSetupLink" in header
    assert "beginUpload" in header
    assert "beginSimFire" in header
    assert "requestKind()" in header
    assert "requestId()" in header
    assert "nextRequestId_" in header
    assert "push" in header
    assert "pollTimeout" in header
    assert "SETUP_OK" in header
    assert "SETUP_ERR" in header
    assert "accepts matching request-scoped replies only" in host_test
    assert "SETUP_OK 999" in host_test
    assert "sim-fire request accepts scoped replies only" in host_test
    assert "SETUP_OK 1" in host_test
    assert "SETUP_ERR 2" in host_test
    assert "ignores noisy USB lines while upload is pending" in host_test
    assert "rejects on timeout after grace window" in host_test
    assert "rejects overlong lines" in host_test
    assert '#include "terminal_usb_link.h"' in main
    assert "terminal_usb_link::UsbSetupLink g_usbLink" in main
    assert "link.beginUpload" in app_logic
    assert "handleUsbEvent" in main
    assert "startsWith" not in main
    assert "g_usbLine" not in main

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_switch_edges_are_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_switches.h")
    host_test = read("firmware/tests/test_terminal_switches.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    pipeline = read("firmware/sticks3-terminal/src/terminal_switch_pipeline.h")

    assert "namespace terminal_switches" in header
    assert "struct SwitchSnapshot" in header
    assert "struct SwitchEvents" in header
    assert "class SwitchEdgeTracker" in header
    assert "update(const SwitchSnapshot&" in header
    assert "prime(const SwitchSnapshot&" in header
    assert "previousUploadPressed_" in header
    assert "previousSimFirePressed_" in header
    assert "upload switch fires once per press" in host_test
    assert "simulate switch fires once per press" in host_test
    assert "release and repress emits new events" in host_test
    assert "simultaneous switches emit both events" in host_test
    assert "boot-held switches are primed without events" in host_test
    assert "boot-held sim-fire needs release and repress" in host_test
    assert "boot-held upload needs release and repress" in host_test
    assert "boot prime with idle switches preserves first real press" in host_test
    assert "boot-held both release upload then repress upload emits only upload" in host_test
    assert "terminal_switches::SwitchEdgeTracker edges_" in pipeline
    assert "edges_.prime(debouncer_.stable())" in pipeline
    assert "edges_.update(stable)" in pipeline
    assert '#include "terminal_switch_pipeline.h"' in main
    assert "terminal_switch_pipeline::SwitchPipeline g_switchPipeline" in main
    assert "primeSwitches" in main
    assert "primeDirectControls" in main
    assert "terminal_switches::SwitchSnapshot readSwitches()" in main
    assert "g_switchPipeline.prime(readSwitches(), millis())" in main
    setup_section = main[main.index("void setup()") : main.index("void loop()")]
    assert setup_section.index("g_switchDriver.begin()") < setup_section.index("primeSwitches()")
    assert setup_section.index("g_encoders.begin()") < setup_section.index("primeDirectControls()")
    assert setup_section.index("primeSwitches()") < setup_section.index("primeDirectControls()")
    assert "pollSwitches()" not in setup_section
    assert "g_switches" not in main
    assert "g_uploadSwitchWasPressed" not in main
    assert "g_simFireSwitchWasPressed" not in main

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_switch_debounce_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_switch_debounce.h")
    host_test = read("firmware/tests/test_terminal_switch_debounce.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    pipeline = read("firmware/sticks3-terminal/src/terminal_switch_pipeline.h")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_switch_debounce" in header
    assert "class SwitchDebouncer" in header
    assert "explicit SwitchDebouncer(std::uint32_t" in header
    assert "prime(const terminal_switches::SwitchSnapshot&" in header
    assert "update(const terminal_switches::SwitchSnapshot&" in header
    assert "stable() const" in header
    assert "press bounce waits for stable debounce window" in host_test
    assert "release bounce waits for stable debounce window" in host_test
    assert "upload and sim-fire debounce independently" in host_test
    assert "prime keeps boot-held switch stable without transition" in host_test
    assert "zero debounce follows raw immediately" in host_test
    assert "millis rollover keeps debounce window" in host_test
    assert "SWITCH_DEBOUNCE_MS" in config
    assert "TERMINAL_SWITCH_DEBOUNCE_MS" in config
    assert "terminal_switch_debounce::SwitchDebouncer debouncer_" in pipeline
    assert "debouncer_.prime(raw, nowMs)" in pipeline
    assert "debouncer_.update(raw, nowMs)" in pipeline
    assert "terminal_switches::SwitchSnapshot readSwitches()" in main
    assert "g_switchPipeline.prime(readSwitches(), millis())" in main
    assert "g_switchPipeline.update(readSwitches(), millis(), uploadInFlight())" in main
    assert "g_switchDebouncer" not in main
    assert "switch debounce" in doc
    assert "switch debounce" in readme
    assert "-DTERMINAL_SWITCH_DEBOUNCE_MS=<ms>" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_FIRE",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_switch_dispatch_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_switch_dispatch.h")
    host_test = read("firmware/tests/test_terminal_switch_dispatch.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    pipeline = read("firmware/sticks3-terminal/src/terminal_switch_pipeline.h")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_switch_dispatch" in header
    assert "enum class SwitchAction" in header
    assert "None" in header
    assert "Upload" in header
    assert "SimFire" in header
    assert "chooseAction" in header
    assert "const terminal_switches::SwitchEvents&" in header
    assert "bool uploadInFlight" in header
    assert "simultaneous switches prefer upload" in host_test
    assert "upload in flight suppresses switch actions" in host_test
    assert "sim fire held through upload completion needs release and repress" in host_test
    assert "idle switch events select no action" in host_test
    assert '#include "terminal_switch_dispatch.h"' in main
    assert "terminal_switch_dispatch::chooseAction" in pipeline
    assert "terminal_switch_dispatch::SwitchAction" in main
    assert "if (events.upload)" not in main
    assert "if (events.simFire)" not in main
    assert "switch dispatch" in doc
    assert "switch dispatch" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_FIRE",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_switch_pipeline_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_switch_pipeline.h")
    host_test = read("firmware/tests/test_terminal_switch_pipeline.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_switch_pipeline" in header
    assert "class SwitchPipeline" in header
    assert "explicit SwitchPipeline(std::uint32_t" in header
    assert "prime(const terminal_switches::SwitchSnapshot&" in header
    assert "update(const terminal_switches::SwitchSnapshot&" in header
    assert "bool uploadInFlight" in header
    assert "terminal_switch_debounce::SwitchDebouncer" in header
    assert "terminal_switches::SwitchEdgeTracker" in header
    assert "terminal_switch_dispatch::chooseAction" in header
    assert "boot-held switches do not dispatch until release and repress" in host_test
    assert "bounce does not dispatch before stable window" in host_test
    assert "sim fire held while upload in flight needs release and repress" in host_test
    assert "upload held while upload in flight needs release and repress" in host_test
    assert "simultaneous debounced press prefers upload" in host_test
    assert '#include "terminal_switch_pipeline.h"' in main
    assert "terminal_switch_pipeline::SwitchPipeline g_switchPipeline" in main
    assert "terminal_switches::SwitchSnapshot readSwitches()" in main
    assert "g_switchPipeline.prime(readSwitches(), millis())" in main
    assert "g_switchPipeline.update(readSwitches(), millis(), uploadInFlight())" in main
    assert "g_switchDebouncer" not in main
    assert "g_switches.update" not in main
    assert "switch pipeline" in doc
    assert "switch pipeline" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "String",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "SETUP",
        "SIM_FIRE",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_source_remains_menu_navigation_free() -> None:
    src_root = ROOT / "firmware/sticks3-terminal/src"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(src_root.rglob("*.*"))
        if path.suffix in {".cpp", ".h"}
    )

    forbidden = [
        "UiPage",
        "nextPage",
        "previousPage",
        "currentPage",
        "pageIndex",
        "selectedLane",
        "focus",
        "Focus",
        "NAVIGATION",
    ]
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_hardware_driver_stubs_are_safe_noop_boundaries() -> None:
    faders = read("firmware/sticks3-terminal/src/drivers/terminal_fader_driver.h")
    encoders = read("firmware/sticks3-terminal/src/drivers/terminal_chain_encoder_driver.h")
    oled = read("firmware/sticks3-terminal/src/drivers/terminal_external_oled.h")
    host_test = read("firmware/tests/test_terminal_hardware_drivers.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")

    assert "namespace terminal_fader_driver" in faders
    assert "class FaderRawReader" in faders
    assert "class MissingFaderRawReader" in faders
    assert "class ArduinoAdcFaderRawReader" in faders
    assert "class FaderDriver" in faders
    assert "class ConfiguredFaderDriver" in faders
    assert "readRaw(std::size_t lane)" in faders
    assert "analogRead" in faders
    assert "#if defined(ARDUINO) && TERMINAL_FADER_ADC_ENABLED" in faders
    assert "#include <Arduino.h>" in faders
    assert "#define TERMINAL_FADER_HAS_ARDUINO_ADC 1" in faders
    assert "#define TERMINAL_FADER_HAS_ARDUINO_ADC 0" in faders
    assert "if (!terminal_config::FADER_ADC_ENABLED) {" in faders
    assert "for (std::size_t lane = 0; lane < terminal_config::FADER_ADC_PINS.size(); ++lane)" in faders
    assert "pinMode(terminal_config::FADER_ADC_PINS[lane], INPUT)" in faders
    assert "lane >= terminal_config::FADER_ADC_PINS.size()" in faders
    assert "analogRead(terminal_config::FADER_ADC_PINS[lane])" in faders
    assert "using ConfiguredFaderRawReader = ArduinoAdcFaderRawReader" in faders
    assert "using ConfiguredFaderRawReader = MissingFaderRawReader" in faders
    assert "read(ControlSnapshot&" in faders
    assert "lockToDraft" in faders
    assert "available()" in faders
    assert "SLIDER_UNCHANGED" in faders
    assert "namespace terminal_chain_encoder_driver" in encoders
    assert "class ChainEncoderRawReader" in encoders
    assert "class MissingChainEncoderRawReader" in encoders
    assert "class M5ChainEncoderRawReader" in encoders
    assert "class ChainEncoderDriver" in encoders
    assert "class ConfiguredChainEncoderDriver" in encoders
    assert "readSample(std::size_t lane)" in encoders
    assert "terminal_encoder_filter::EncoderSample" in encoders
    assert "CHAIN_ENCODER_IDS" in encoders
    assert "chainEncoderIdForLane" in encoders
    assert "chainEncoderIdForLane(lane)" in encoders
    assert "static_cast<uint8_t>(lane + 1)" not in encoders
    assert "static_cast<std::uint8_t>(lane + 1)" not in encoders
    assert "filter_.prime(lane" in encoders
    assert "filter_.update(lane" in encoders
    assert "getEncoderIncValue" in encoders
    assert "getEncoderButtonPressStatus" in encoders
    assert "CHAIN_BUTTON_PRESS_SINGLE" in encoders
    assert "CHAIN_BUTTON_PRESS_LONG" in encoders
    assert "CHAIN_BUTTON_REPORT_MODE" in encoders
    assert "setEncoderABDirect" in encoders
    assert "ENCODER_AB" in encoders
    assert "CHAIN_ENCODER_QUERY_TIMEOUT_MS = 20" in encoders
    assert "CHAIN_KEY_QUERY_TIMEOUT_MS = 20" in encoders
    assert "struct ChainPressEdges" in encoders
    assert "classifyChainPress" in encoders
    assert "sawSinglePress || sawLongPress" in encoders
    assert "getEncoderIncValue(id, &increment, CHAIN_ENCODER_QUERY_TIMEOUT_MS)" in encoders
    assert "incrementOk ? static_cast<int>(increment) : 0" in encoders
    assert "makeChainEncoderIncrementSample(reportedIncrement, singlePressed, effectPressed)" in encoders
    assert "if (chain_.getEncoderValue(id, &position, 10) != CHAIN_OK)" not in encoders
    assert "singlePressed || (buttonOk && buttonStatus != 0)" not in encoders
    assert "available()" in encoders
    assert "CHAIN_RX_PIN" in encoders
    assert "CHAIN_TX_PIN" in encoders
    assert "M5Chain" in encoders
    assert "encoderDelta = 0" in encoders
    assert "encoderPressed = false" in encoders
    assert "effectPressed = false" in encoders
    assert "namespace terminal_external_oled" in oled
    assert "class ExternalOledSink" in oled
    assert "class MissingExternalOledSink" in oled
    assert "class M5GfxExternalOledSink" in oled
    assert "class ExternalOledDriver" in oled
    assert "class ConfiguredExternalOledDriver" in oled
    assert "terminal_external_display::DisplayRenderPlan" in oled
    assert "terminal_external_display::renderPlan()" in oled
    assert "case '#': return hash;" in oled
    assert "TERMINAL_EXTERNAL_OLED_ENABLED" in oled
    assert "draw(const terminal_external_display::DisplayFrame&" in oled
    assert "if (frame == lastFrame_)" in oled
    assert "cachedPages_" in oled
    assert "pageCached_" in oled
    assert "resetPageCacheToClearedDisplay()" in oled
    assert "invalidatePageCache()" in oled

    ssd1309_start = oled.index("class Ssd1309ExternalOledSink")
    ssd1309_draw = oled[
        oled.index("bool draw(const terminal_external_display::DisplayRenderPlan& plan", ssd1309_start) :
        oled.index("   private:", ssd1309_start)
    ]
    assert "clearOled()" not in ssd1309_draw
    assert "const OledPages pages = renderFrameBuffer(plan, frame)" in ssd1309_draw
    assert "pageCached_[page] && cachedPages_[page] == pages[page]" in ssd1309_draw
    assert "writeOledPageBuffer(page, pages[page])" in ssd1309_draw
    assert "fader stub leaves brightness unchanged" in host_test
    assert "fake fader raw reader publishes changed raw sample" in host_test
    assert "fader begin primes current raw without changing brightness" in host_test
    assert "fader lock to draft suppresses mismatch until pickup" in host_test
    assert "chain encoder stub leaves color on and effect state unchanged" in host_test
    assert "fake chain encoder raw reader publishes movement and buttons" in host_test
    assert "chain encoder begin primes current position without publishing delta" in host_test
    assert "chain encoder driver preserves slider input" in host_test
    assert "chain encoder single press classifies as effect toggle" in host_test
    assert "chain encoder long press also classifies as effect toggle" in host_test
    assert "chain encoder sample factory keeps press edges exclusive" in host_test
    assert "chain encoder sample factory preserves buttons when position missing" in host_test
    assert "chain encoder IDs map physical LED5 to logical LED1" in host_test
    assert "chain encoder disabled bus reports unavailable" in host_test
    assert "external OLED stub rejects display frame without IO cache" in host_test
    assert "fake external OLED sink receives render plan and frame" in host_test
    assert "unchanged external OLED frame skips IO draw" in host_test
    assert "unavailable external OLED sink does not cache frame without IO draw" in host_test
    assert "failed external OLED draw is retried instead of cached" in host_test
    assert '#include "drivers/terminal_fader_driver.h"' in main
    assert "terminal_fader_driver::ConfiguredFaderDriver g_faders" in main
    assert '#include "drivers/terminal_chain_encoder_driver.h"' in main
    assert "terminal_chain_encoder_driver::ConfiguredChainEncoderDriver g_encoders" in main
    assert '#include "drivers/terminal_external_oled.h"' in main
    assert "terminal_external_oled::ConfiguredExternalOledDriver g_externalOled" in main
    assert "g_faders.read(snapshot)" in main
    assert "g_encoders.read(snapshot)" in main
    assert "g_externalOled.draw(nextFrame)" in main
    assert "runOledI2cScanSmoke()" in main
    assert "runOledI2cScanPass" in main
    assert "TERMINAL_EXTERNAL_OLED_DRAW_SMOKE" in main
    assert "runExternalOledDrawSmoke" in main
    assert "OLED_DRAW_SMOKE START" in main
    assert "OLED_DRAW_SMOKE SELECT_PAHUB" in main
    assert "OLED_DRAW_SMOKE DRAWN address=0x%02X channel=%u" in main
    assert "SSD1306" in main
    assert "SSD1309" in main
    assert "OLED_DRAW_SMOKE ALL_ON_BOOT" in main
    assert "OLED_DRAW_SMOKE STABLE_TEXT" in main
    assert "OLED_DRAW_SMOKE HEARTBEAT stable" in main
    assert "runExternalOledDrawSmoke(true)" in main
    assert "runExternalOledDrawSmoke(!g_oledAllOnBootShown)" not in main
    assert "0xA1" in main
    assert "0xC8" in main
    assert "initOledSsd1309Laskakit" in main
    assert "setOledAllPixelsOn" in main
    assert "OLED_I2C_SCAN START" in main
    assert "FOUND 0x%02X" in main
    assert "\"MUX\" : \"DOWNSTREAM\"" in main
    assert "OLED_I2C_SCAN EXPECTED_FOUND %u" in main
    assert "OLED_I2C_SCAN DONE count=%u downstream=%u expected=0x%02X freq=%u" in main
    assert "scanI2cBus" in main
    assert "selectPahubChannel" in main
    assert "deselectPahub" in main
    assert "OLED_I2C_SCAN_PAHUB START" in main
    assert "OLED_I2C_SCAN_PAHUB CHANNEL %u SELECT err=%u" in main
    assert "OLED_I2C_SCAN_PAHUB CHANNEL %u DONE count=%u downstream=%u" in main
    assert "OLED_I2C_SCAN_PAHUB CHANNEL %u DOWNSTREAM_EMPTY" in main
    assert "runOledI2cScanPass(bus, 100000)" in main
    assert "pollOledI2cScanSmoke" in main
    assert "g_lastI2cScanMs" in main
    assert "millis() - g_lastI2cScanMs < 3000" in main
    assert "if (!terminal_config::EXTERNAL_OLED_I2C_SCAN_SMOKE)" in main
    assert "terminal_config::EXTERNAL_OLED_I2C_SCAN_SMOKE" in main
    assert "terminal_config::EXTERNAL_OLED_I2C_PORT == 1 ? Wire1 : Wire" in main
    assert "bus.begin(terminal_config::EXTERNAL_OLED_SDA_PIN" in main

    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    platformio = read("firmware/sticks3-terminal/platformio.ini")
    assert "TERMINAL_CHAIN_RX_PIN" in config
    assert "TERMINAL_CHAIN_TX_PIN" in config
    assert "TERMINAL_CHAIN_BAUD" in config
    assert "TERMINAL_REQUIRE_CHAIN_UART" in config
    assert "TERMINAL_FADER_ADC_ENABLED" in config
    assert "TERMINAL_FADER_LANE1_ADC_PIN" in config
    assert "TERMINAL_FADER_LANE5_ADC_PIN" in config
    assert "FADER_ADC_ENABLED" in config
    assert "FADER_ADC_PINS" in config
    assert "CHAIN_RX_PIN" in config
    assert "CHAIN_TX_PIN" in config
    assert "CHAIN_UART_CONFIGURED" in config
    assert "CHAIN_UART_REQUIRED" in config
    assert "CHAIN_BAUD" in config
    assert "static_assert(!CHAIN_UART_REQUIRED || CHAIN_UART_CONFIGURED" in config
    assert "chain UART RX/TX pins must not share a configured pin" in config
    assert "TERMINAL_EXTERNAL_OLED_ENABLED" in config
    assert "TERMINAL_EXTERNAL_OLED_SDA_PIN" in config
    assert "TERMINAL_EXTERNAL_OLED_SCL_PIN" in config
    assert "TERMINAL_EXTERNAL_OLED_I2C_ADDRESS" in config
    assert "TERMINAL_EXTERNAL_OLED_I2C_PORT" in config
    assert "TERMINAL_EXTERNAL_OLED_I2C_FREQ" in config
    assert "TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2" in config
    assert "TERMINAL_EXTERNAL_OLED_I2C_SCAN_SMOKE" in config
    assert "TERMINAL_EXTERNAL_OLED_DRAW_SMOKE" in config
    assert "TERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS" in config
    assert "TERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL" in config
    assert "TERMINAL_I2C_SCAN_PAHUB_CHANNELS" in config
    assert "TERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED" in config
    assert "EXTERNAL_OLED_ENABLED" in config
    assert "EXTERNAL_OLED_I2C_SCAN_SMOKE" in config
    assert "EXTERNAL_OLED_DRAW_SMOKE" in config
    assert "EXTERNAL_OLED_PAHUB_ADDRESS" in config
    assert "EXTERNAL_OLED_PAHUB_CHANNEL" in config
    assert "I2C_SCAN_PAHUB_CHANNELS" in config
    assert "EXTERNAL_OLED_I2C_CONFIGURED" in config
    assert "EXTERNAL_OLED_DRIVER_M5UNITGLASS2" in config
    assert "EXTERNAL_OLED_LIVE_SINK_CONFIRMED" in config
    assert "external OLED I2C scan smoke must not enable the display sink" in config
    assert "external OLED draw smoke must not enable the display sink" in config
    assert "external OLED draw smoke requires SDA/SCL pins" in config
    assert "external OLED enabled requires an explicit supported driver selection" in config
    assert "external OLED live sink requires bench confirmation" in config
    assert "external OLED I2C scan requires SDA/SCL pins" in config
    assert "PaHUB channel scan requires the I2C scan smoke environment" in config
    assert "external OLED SDA/SCL pins must be configured when OLED is enabled" in config
    assert "external OLED SDA/SCL pins must not share a configured pin" in config
    assert "activePin(" in config
    assert "configuredPinsAreUnique()" in config
    assert "configured shared Grove pins require explicit PaHUB routing" in config
    assert "lib_ldf_mode = deep" in platformio
    assert "m5stack/M5GFX" in platformio
    assert "m5stack/M5Chain" in platformio
    assert "[env:sticks3-terminal-live-debug]" in platformio
    assert "-DTERMINAL_LIVE_DEBUG=1" in platformio
    assert "TERMINAL_LIVE_DEBUG" in config
    assert "TERMINAL_LIVE_DEBUG" in main
    assert "TERMINAL_LIVE_INPUT" in main
    assert "TERMINAL_CHAIN_RAW" in encoders
    assert "[env:sticks3-terminal-chain-uart-smoke]" in platformio
    assert "extends = env:sticks3-terminal" in platformio
    assert "-DTERMINAL_CHAIN_UART_SMOKE=1" in platformio
    assert "-DTERMINAL_CHAIN_RX_PIN=10" in platformio
    assert "-DTERMINAL_CHAIN_TX_PIN=9" in platformio
    assert "-DTERMINAL_REQUIRE_CHAIN_UART=1" in platformio
    assert "-DTERMINAL_CHAIN_UART_SELECT_PAHUB=1" in platformio
    assert "-DTERMINAL_CHAIN_PAHUB_ADDRESS=0x70" in platformio
    assert "-DTERMINAL_CHAIN_PAHUB_CHANNEL=0" in platformio
    assert "[env:sticks3-terminal-oled-i2c-scan-smoke]" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_I2C_SCAN_SMOKE=1" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_SDA_PIN=1" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_SCL_PIN=2" in platformio
    assert "[env:sticks3-terminal-grove-i2c-scan-smoke]" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_SDA_PIN=9" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_SCL_PIN=10" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_I2C_ADDRESS=0x70" in platformio
    assert "-DTERMINAL_I2C_SCAN_PAHUB_CHANNELS=1" in platformio
    assert "[env:sticks3-terminal-oled-draw-smoke]" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_DRAW_SMOKE=1" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_I2C_ADDRESS=0x3C" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS=0x70" in platformio
    assert "-DTERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL=3" in platformio
    oled_env = platformio[platformio.index("[env:sticks3-terminal-oled-i2c-scan-smoke]") :]
    assert "extends = env:sticks3-terminal" in oled_env
    assert "${env:sticks3-terminal.build_flags}" in oled_env
    assert "build_unflags =" in oled_env
    assert "-DTERMINAL_EXTERNAL_OLED_ENABLED=1" in oled_env
    assert "-DTERMINAL_EXTERNAL_OLED_DRIVER_SSD1309=1" in oled_env
    assert "-DTERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED=1" in oled_env
    assert "-DTERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2=1" not in oled_env
    grove_env = platformio[platformio.index("[env:sticks3-terminal-grove-i2c-scan-smoke]") :]
    assert "extends = env:sticks3-terminal" in grove_env
    assert "build_unflags =" in grove_env
    assert "-DTERMINAL_EXTERNAL_OLED_ENABLED=1" in grove_env
    assert "-DTERMINAL_EXTERNAL_OLED_DRIVER_SSD1309=1" in grove_env
    assert "-DTERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED=1" in grove_env
    assert "-DTERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2=1" not in grove_env

    readme = read("firmware/sticks3-terminal/README.md")
    assert "TERMINAL_REQUIRE_CHAIN_UART=1" in readme
    assert "sticks3-terminal-chain-uart-smoke" in readme
    assert "sticks3-terminal-oled-i2c-scan-smoke" in readme
    assert "sticks3-terminal-grove-i2c-scan-smoke" in readme
    assert "sticks3-terminal-oled-draw-smoke" in readme
    assert "G9/G10" in readme
    assert "0x70" in readme
    assert "0x3C" in readme
    assert "Pa.HUB port 3" in readme
    assert "SSD1309" in readme
    assert "ALL_ON_BOOT" in readme
    assert "0xA1/0xC8" in readme
    assert "Pa.HUB channels" in readme
    assert "OLED_I2C_SCAN FOUND" in readme
    assert "OLED_I2C_SCAN EXPECTED_FOUND 1" in readme
    assert "tools/read_com.py" in readme
    assert "USB serial diagnostics, not setup-link protocol traffic" in readme
    assert "TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2=1" in readme
    assert "TERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED=1" in readme
    assert "LaskaKit 2.42" in readme

    forbidden = [
        "Serial.println",
        "Serial.print",
        "Serial.write",
        "Serial.read",
        "M5.Display",
        "prop_protocol",
        "terminal_app_logic",
        "terminal_usb_link",
        "TerminalSetupState&",
        "TerminalAction",
        "beginUpload",
        "commitAccepted",
        "commitRejected",
        "simulateFire",
        "FrameType",
        "HMAC",
        "LoRa",
        "C6L",
        "SEND ",
        "STOP",
        'Serial.println("SIM_FIRE")',
    ]
    encoders_without_live_debug = re.sub(
        r"#if TERMINAL_LIVE_DEBUG.*?#endif",
        "",
        encoders,
        flags=re.S,
    )
    combined = "\n".join([faders, encoders_without_live_debug, oled, host_test])
    for needle in forbidden:
        if needle in {"TerminalSetupState&"}:
            assert needle not in oled, needle
        else:
            assert needle not in combined, needle


def test_terminal_chain_uart_smoke_reads_encoders_and_u206_keys() -> None:
    main = read("firmware/sticks3-terminal/src/main.cpp")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    platformio = read("firmware/sticks3-terminal/platformio.ini")

    assert "TERMINAL_CHAIN_UART_SMOKE" in config
    assert "CHAIN_UART_SMOKE" in config
    assert "chain UART smoke requires RX/TX pins" in config
    assert "TERMINAL_CHAIN_UART_SMOKE" in main
    assert "CHAIN_UART_SMOKE START" in main
    assert "CHAIN_UART_SMOKE CONNECTED" in main
    assert "CHAIN_UART_SMOKE NO_DEVICE" in main
    assert "CHAIN_UART_SMOKE TRY_SWAPPED" in main
    assert "CHAIN_UART_SMOKE CONNECTED_SWAPPED" in main
    assert "CHAIN_UART_SMOKE DEVICE_COUNT" in main
    assert "CHAIN_UART_SMOKE %s id=%u" in main
    assert "ENC_CHANGE" in main
    assert "KEY_CHANGE" in main
    assert "POLL_CHANGE" in main
    assert "getEncoderABDirect" in main
    assert "resetEncoderIncValue" in main
    assert "getEncoderValue" in main
    assert "getEncoderIncValue" in main
    assert "getEncoderButtonStatus" in main
    assert "getEncoderButtonPressStatus" in main
    assert "getKeyButtonStatus" in main
    assert "getKeyButtonPressStatus" in main
    assert "CHAIN_BUTTON_PRESS_SINGLE" in main
    assert "CHAIN_BUTTON_PRESS_LONG" in main
    assert "CHAIN_BUTTON_REPORT_MODE" in main
    assert "expected_encoders=5 expected_keys=2" in main
    assert "-DTERMINAL_CHAIN_UART_SMOKE=1" in platformio


def test_terminal_live_build_enables_bench_chain_and_external_oled() -> None:
    platformio = read("firmware/sticks3-terminal/platformio.ini")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    encoders = read("firmware/sticks3-terminal/src/drivers/terminal_chain_encoder_driver.h")
    oled = read("firmware/sticks3-terminal/src/drivers/terminal_external_oled.h")
    main = read("firmware/sticks3-terminal/src/main.cpp")

    live_env = platformio[: platformio.index("[env:sticks3-terminal-chain-uart-smoke]")]
    for needle in [
        "-DTERMINAL_CHAIN_RX_PIN=10",
        "-DTERMINAL_CHAIN_TX_PIN=9",
        "-DTERMINAL_REQUIRE_CHAIN_UART=1",
        "-DTERMINAL_CHAIN_UART_SELECT_PAHUB=1",
        "-DTERMINAL_CHAIN_PAHUB_ADDRESS=0x70",
        "-DTERMINAL_CHAIN_PAHUB_CHANNEL=0",
        "-DTERMINAL_EXTERNAL_OLED_ENABLED=1",
        "-DTERMINAL_EXTERNAL_OLED_DRIVER_SSD1309=1",
        "-DTERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED=1",
        "-DTERMINAL_EXTERNAL_OLED_SELECT_PAHUB=1",
        "-DTERMINAL_EXTERNAL_OLED_SDA_PIN=9",
        "-DTERMINAL_EXTERNAL_OLED_SCL_PIN=10",
        "-DTERMINAL_EXTERNAL_OLED_I2C_ADDRESS=0x3C",
        "-DTERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS=0x70",
        "-DTERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL=3",
    ]:
        assert needle in live_env, needle

    assert "TERMINAL_EXTERNAL_OLED_DRIVER_SSD1309" in config
    assert "TERMINAL_EXTERNAL_OLED_SELECT_PAHUB" in config
    assert "EXTERNAL_OLED_DRIVER_SSD1309" in config
    assert "EXTERNAL_OLED_SELECT_PAHUB" in config
    assert "configured shared Grove pins require explicit PaHUB routing" in config
    assert "configuredPinsShareAllowed" in config

    assert "terminal_grove_route.h" in encoders
    assert "selectChainPahub" in encoders
    assert "CHAIN_KEY_UPLOAD_ID" in encoders
    assert "CHAIN_KEY_SIM_FIRE_ID" in encoders
    assert "getKeyButtonStatus(CHAIN_KEY_UPLOAD_ID" in encoders
    assert "getKeyButtonStatus(CHAIN_KEY_SIM_FIRE_ID" in encoders
    assert "readSwitches(terminal_switches::SwitchSnapshot&" in encoders

    assert "class Ssd1309ExternalOledSink" in oled
    assert "TERMINAL_EXTERNAL_OLED_HAS_SSD1309" in oled
    assert "selectExternalOledPahub" in oled
    assert "initOledSsd1309" in oled
    assert "drawText" in oled
    assert "fillRect(pages, plan.effectBox)" in oled
    assert "drawRect(pages, plan.effectBox)" not in oled
    assert "OLED_DRAW_SMOKE" not in oled

    assert "terminal_switches::SwitchSnapshot readSwitches()" in main
    assert "g_encoders.readSwitches(snapshot)" in main
    assert "renderExternalDisplayIfChanged();" in main[main.index("void loop()") :]
    assert "renderExternalDisplay();\n        drawStatusPanel();" not in main[main.index("void loop()") :]


def test_terminal_bench_checklist_requires_five_chain_encoder_proof() -> None:
    checklist = read("docs/bench_test_checklist.md")

    for needle in [
        "Chain Encoder final-pin proof",
        "TERMINAL_REQUIRE_CHAIN_UART=1",
        "lanes 1..5",
        "CW and CCW",
        "only that lane",
        "encoder button toggles only that lane fire-change marker",
        "last U206 switch emits one SIM_FIRE preview edge",
        "double-click remains ignored",
        "SETUP_OK <request_id>",
        "CHAIN_ENCODER_IDS = {5, 4, 3, 2, 1}",
    ]:
        assert needle in checklist


def test_terminal_fader_adc_arduino_branch_is_host_compiled() -> None:
    arduino_stub = read("firmware/tests/stubs/Arduino.h")
    adc_test = read("firmware/tests/test_terminal_fader_adc_arduino_stub.cpp")

    assert "#define INPUT" in arduino_stub
    assert "void pinMode(int pin, int mode)" in arduino_stub
    assert "int analogRead(int pin)" in arduino_stub
    assert "#define ARDUINO 1" in adc_test
    assert "#define TERMINAL_FADER_ADC_ENABLED 1" in adc_test
    assert "#define TERMINAL_FADER_LANE1_ADC_PIN 11" in adc_test
    assert "#define TERMINAL_FADER_LANE5_ADC_PIN 15" in adc_test
    assert "static_assert(std::is_same<terminal_fader_driver::ConfiguredFaderRawReader, terminal_fader_driver::ArduinoAdcFaderRawReader>::value" in adc_test
    assert "pinMode calls five lane pins as INPUT" in adc_test
    assert "analogRead follows lane pin mapping" in adc_test
    assert "invalid lane returns missing sample" in adc_test


def test_terminal_switch_driver_arduino_branch_is_host_compiled() -> None:
    arduino_stub = read("firmware/tests/stubs/Arduino.h")
    switch_test = read("firmware/tests/test_terminal_switch_driver_arduino_stub.cpp")
    default_switch_test = read("firmware/tests/test_terminal_switch_driver_default_arduino_stub.cpp")

    assert "#define INPUT_PULLUP" in arduino_stub
    assert "#define LOW" in arduino_stub
    assert "#define HIGH" in arduino_stub
    assert "int digitalRead(int pin)" in arduino_stub
    assert "#define TERMINAL_UPLOAD_SWITCH_PIN 21" in switch_test
    assert "#define TERMINAL_SIM_FIRE_SWITCH_PIN 22" in switch_test
    assert "pinMode configures both switches as INPUT_PULLUP" in switch_test
    assert "LOW reads as pressed and HIGH reads as released" in switch_test
    assert "simultaneous LOW reads both switches pressed" in switch_test
    assert "negative pins stay unconfigured and unpressed" in default_switch_test


def test_terminal_usb_setup_roundtrip_is_host_tested() -> None:
    host_test = read("firmware/tests/test_terminal_usb_setup_roundtrip.cpp")

    assert '#include "../sticks3-terminal/src/terminal_app_logic.h"' in host_test
    assert '#include "../../shared/terminal/terminal_setup_receiver.h"' in host_test
    assert "upload SETUP line commits through receiver reply" in host_test
    assert "receiver SETUP_ERR rolls terminal back to problem" in host_test
    assert "SIM_FIRE preview uses receiver callback without setup commit" in host_test
    assert "SIM_FIRE rejection rolls terminal to problem" in host_test
    assert "late SETUP_OK after timeout cannot commit" in host_test
    assert "terminal_usb_link::UsbSetupLink" in host_test
    assert "terminal_setup_receiver::handleLineResult" in host_test
    assert "terminal_app_logic::handleUploadEvent" in host_test


def test_terminal_switch_driver_owns_active_low_pin_io() -> None:
    driver = read("firmware/sticks3-terminal/src/drivers/terminal_switch_driver.h")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    production_main = main[: main.index("#else", main.index("#if !TERMINAL_G4_ADC_SMOKE"))]
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_switch_driver" in driver
    assert '#include "../terminal_config.h"' in driver
    assert '#include "../terminal_switches.h"' in driver
    assert '#include "terminal_config.h"' not in driver
    assert '#include "terminal_switches.h"' not in driver
    assert "class SwitchDriver" in driver
    assert "begin()" in driver
    assert "read() const" in driver
    assert "terminal_switches::SwitchSnapshot" in driver
    assert "terminal_config::UPLOAD_SWITCH_PIN" in driver
    assert "terminal_config::SIM_FIRE_SWITCH_PIN" in driver
    assert "INPUT_PULLUP" in driver
    assert "digitalRead" in driver
    assert "LOW" in driver
    assert "pin >= 0" in driver
    assert '#include "drivers/terminal_switch_driver.h"' in main
    assert "terminal_switch_driver::SwitchDriver g_switchDriver" in main
    assert "g_switchDriver.begin()" in main
    assert "g_switchDriver.read()" in main
    assert "configureSwitchPins" not in main
    assert "readActiveLowSwitch" not in main
    assert "pinMode(" not in production_main
    assert "digitalRead(" not in production_main
    assert "SwitchDriver" in doc
    assert "switch driver" in readme

    forbidden = [
        "Serial",
        "M5.Display",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "LoRa",
        "C6L",
        "SEND ",
        "STOP",
        'Serial.println("SIM_FIRE")',
    ]
    for needle in forbidden:
        assert needle not in driver, needle


def test_terminal_app_logic_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_app_logic.h")
    host_test = read("firmware/tests/test_terminal_app_logic.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "namespace terminal_app_logic" in header
    assert "struct TerminalAction" in header
    assert "drainUsbInput" in header
    assert "sendLine" in header
    assert "redraw" in header
    assert "uploadBusy" in header
    assert "uploadInFlight" in header
    assert "canStartUpload" in header
    assert "requestUpload" in header
    assert "startUploadAfterUsbDrain" in header
    assert "requestSimFire" in header
    assert "handleUploadEvent" in header
    assert "SIM_FIRE" in header
    assert "upload request emits setup line and starts in-flight" in host_test
    assert "upload request ignored while upload is already in flight" in host_test
    assert "sim-fire emits line only while idle" in host_test
    assert "sim-fire blocked when setup-only upload state" in host_test
    assert "sim-fire blocked when link-only upload state" in host_test
    assert "upload request blocked when setup-only upload state" in host_test
    assert "upload request blocked when link-only upload state" in host_test
    assert "accepted upload commits sent snapshot" in host_test
    assert "rejected upload reverts draft" in host_test
    assert "second upload gets new request id" in host_test
    assert "stale accepted from link-only upload clears link without commit" in host_test
    assert "stale rejected from link-only upload clears link without rollback" in host_test
    assert "none upload event is no-op" in host_test
    assert "sim-fire accepted clears link without committing setup" in host_test
    assert "sim-fire rejected marks problem without rolling back draft" in host_test
    assert '#include "terminal_app_logic.h"' in main
    assert "performTerminalAction" in main
    assert "terminal_app_logic::startUploadAfterUsbDrain" in main
    assert "terminal_app_logic::requestSimFire" in main
    assert "terminal_app_logic::handleUploadEvent" in main
    assert "terminal_app_logic::uploadInFlight" in main
    assert "setup.uploadLine(requestId)" in header
    assert "g_setup.beginUpload" not in main
    assert "g_setup.commitAccepted" not in main
    assert "g_setup.commitRejected" not in main
    assert "g_setup.simulateFire" not in main
    assert "g_usbLink.beginUpload" not in main
    assert "g_usbLink.finishUpload" not in main
    assert "app logic" in doc
    assert "app logic" in readme

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_physical_tick_is_pure_and_host_tested() -> None:
    header = read("firmware/sticks3-terminal/src/terminal_physical_tick.h")
    host_test = read("firmware/tests/test_terminal_physical_tick.cpp")
    main = read("firmware/sticks3-terminal/src/main.cpp")

    assert "namespace terminal_physical_tick" in header
    assert "struct PhysicalTickResult" in header
    assert "runPhysicalTick" in header
    assert "ControlSnapshot" in header
    assert "SwitchAction" in header
    assert "makeFrame" in header
    assert "canStartUpload" in header
    assert "startUploadAfterUsbDrain" in header
    assert "requestSimFire" in header
    assert "drainedUsbBeforeUpload" in header
    assert "same-tick physical edits are uploaded and shown on OLED" in host_test
    assert "SwitchAction::Upload" in host_test
    for needle in [
        "L1:361,12,1,1",
        "L2:364,34,1,1",
        "L3:364,56,1,1",
        "L4:367,78,1,1",
        "L5:366,99,1,0",
        '"ORANZ", 12, "12%", true, true, "ODP"',
        '"TYRKYS", 34, "34%", true, true, "ODP"',
        '"TYRKYS", 56, "56%", true, true, "ODP"',
        '"RUZOVA", 78, "78%", true, true, "ODP"',
        '"FIALOVA", 99, "99%", true, false, "---"',
        "same-tick sim-fire is blocked by dirty draft but still shows fresh OLED draft",
    ]:
        assert needle in host_test, needle
    assert '#include "terminal_physical_tick.h"' in main
    assert "terminal_physical_tick::runPhysicalTick" in main
    assert "pollPhysicalTick" in main
    loop_section = main[main.index("void loop()") :]
    assert loop_section.index("pollPhysicalTick();") < loop_section.index("pollUploadTimeout();")
    assert loop_section.index("pollPhysicalTick();") < loop_section.index("pollUsbSetupAcks();")

    forbidden = [
        "Arduino.h",
        "M5Unified",
        "Serial",
        "M5.Display",
        "digitalRead",
        "pinMode",
        "LoRa",
        "prop_protocol",
        "FrameType",
        "HMAC",
        "SEND ",
        "STOP",
    ]
    combined = header + "\n" + host_test
    for needle in forbidden:
        assert needle not in combined, needle


def test_terminal_status_panel_uses_m5_display_only_as_secondary() -> None:
    main = read("firmware/sticks3-terminal/src/main.cpp")
    setup = read("firmware/sticks3-terminal/src/terminal_setup.h")

    assert "drawStatusPanel" in main
    assert "NAHRANO" in main
    assert "PROBLEM" in main
    assert "M5.Display.fillScreen" in main
    assert "renderExternalDisplay" in main
    assert "TFT_DARKGREEN" in main
    assert "TFT_RED" in main

    status_background = main[main.index("std::uint16_t statusBackground") : main.index("void drawStatusPanel()")]
    status_panel = main[main.index("void drawStatusPanel()") : main.index("bool renderExternalDisplay()")]
    for needle in [
        "M5.Display.fillScreen(statusBackground(g_setup.status()))",
        "M5.Display.setTextColor(TFT_WHITE, statusBackground(g_setup.status()))",
        "M5.Display.setTextDatum(top_left)",
        "M5.Display.setTextSize(2)",
        "M5.Display.setCursor(6, 8)",
        'M5.Display.println("TERMINAL")',
        "M5.Display.setTextSize(3)",
        "M5.Display.setCursor(6, 36)",
        "M5.Display.println(g_setup.statusText())",
    ]:
        assert needle in status_panel, needle
    assert status_panel.count("M5.Display.println(") == 2
    assert status_panel.count("M5.Display.setTextSize(") == 2
    assert status_panel.count("M5.Display.setCursor(") == 2
    uploaded_case = status_background[
        status_background.index("case terminal_setup::Status::Uploaded:") :
        status_background.index("case terminal_setup::Status::Problem:")
    ]
    problem_case = status_background[
        status_background.index("case terminal_setup::Status::Problem:") :
        status_background.index("case terminal_setup::Status::Uploading:")
    ]
    assert "return TFT_DARKGREEN;" in uploaded_case
    assert "return TFT_RED;" in problem_case

    status_text = setup[setup.index("const char* statusText() const") : setup.index("std::string largeDisplayLine")]
    values = re.findall(r'return "([^"]+)";', status_text)
    assert {"PRIPRAVEN", "ZMENY", "NAHRAVAM", "NAHRANO", "PROBLEM", "SIM FIRE"} <= set(values)
    assert all(len(value) <= 9 for value in values)
    assert "large display" not in status_panel.lower()
    for needle in [
        "largeDisplayLine",
        "oledDisplayLine",
        "terminal_external_display",
        "DisplayRenderPlan",
        "DisplayFrame",
        "g_externalFrame",
        "g_externalOled",
        "for (std::size_t lane",
        "draftLane(",
        "savedLane(",
        "LED ",
        "L1 ",
        "BAR",
        "JAS",
        "ZAP",
        "VYP",
        "MENU",
        "drawString",
        "printf",
        "M5.Display.print(",
    ]:
        assert needle not in status_panel, needle


def test_upload_and_sim_fire_switches_drive_usb_setup_link() -> None:
    main = read("firmware/sticks3-terminal/src/main.cpp")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")
    driver = read("firmware/sticks3-terminal/src/drivers/terminal_switch_driver.h")

    assert "UPLOAD_SWITCH_PIN" in config
    assert "SIM_FIRE_SWITCH_PIN" in config
    assert "TERMINAL_UPLOAD_SWITCH_PIN" in config
    assert "TERMINAL_SIM_FIRE_SWITCH_PIN" in config
    assert "upload and sim-fire switches must not share a configured pin" in config
    assert "INPUT_PULLUP" in driver
    assert "digitalRead" in driver
    assert "terminal_switches::SwitchSnapshot readSwitches()" in main
    assert "g_switchPipeline.update(readSwitches(), millis(), uploadInFlight())" in main
    assert "requestUpload" in main
    assert "terminal_app_logic::startUploadAfterUsbDrain" in main
    assert "terminal_app_logic::requestSimFire" in main
    assert "terminal_app_logic::handleUploadEvent" in main
    assert "Serial.println(action.line.c_str())" in main
    assert '"SIM_FIRE"' in read("firmware/sticks3-terminal/src/terminal_app_logic.h")
    assert "uploadInFlight()" in main
    assert "pollUsbSetupAcks" in main
    assert "handleUsbEvent" in main
    assert "readStringUntil" not in main
    assert "static_assert" in main

    upload_section = main[main.index("void requestUpload()") : main.index("void requestSimFire()")]
    sim_section = main[main.index("void requestSimFire()") : main.index("void pollSwitches()")]
    assert "if (!terminal_app_logic::canStartUpload(g_setup, g_usbLink))" in upload_section
    assert "if (uploadInFlight())" in sim_section


def test_terminal_upload_drains_stale_ack_and_times_out_before_late_ack() -> None:
    main = read("firmware/sticks3-terminal/src/main.cpp")
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "drainUsbSetupInput" in main
    drain_section = main[main.index("void drainUsbSetupInput()") : main.index("bool uploadInFlight();")]
    assert "Serial.available()" in drain_section
    assert "Serial.read()" in drain_section

    upload_section = main[main.index("void requestUpload()") : main.index("void requestSimFire()")]
    assert "terminal_app_logic::canStartUpload" in upload_section
    assert "terminal_app_logic::startUploadAfterUsbDrain" in upload_section
    assert upload_section.index("drainUsbSetupInput();") < upload_section.index("terminal_app_logic::startUploadAfterUsbDrain")
    action_section = main[main.index("void performTerminalAction") : main.index("void pollSwitches()")]
    assert action_section.index("drainUsbSetupInput();") < action_section.index("Serial.println(action.line.c_str())")

    loop_section = main[main.index("void loop()") :]
    assert loop_section.index("pollUploadTimeout();") < loop_section.index("pollUsbSetupAcks();")
    assert "stale setup replies" in doc
    assert "mismatched request id" in doc
    assert "late ACK" in readme
    assert "wrong request id" in readme


def test_platformio_matches_usb_setup_scope() -> None:
    text = read("firmware/sticks3-terminal/platformio.ini")
    main = read("firmware/sticks3-terminal/src/main.cpp")
    config = read("firmware/sticks3-terminal/src/terminal_config.h")

    assert "[env:sticks3-terminal]" in text
    assert "framework = arduino" in text
    assert "board = esp32-s3-devkitc-1" in text
    assert "m5stack/M5Unified" in text
    assert "m5stack/M5GFX" in text
    assert "-DARDUINO_USB_MODE=1" in text
    assert "-DARDUINO_USB_CDC_ON_BOOT=1" in text
    assert "[env:sticks3-terminal-g4-adc-smoke]" in text
    assert "-DTERMINAL_G4_ADC_SMOKE=1" in text
    assert "ARDUINO_USB_MODE" in main
    assert "ARDUINO_USB_CDC_ON_BOOT" in main
    assert "USB setup link requires USB CDC on boot" in main
    assert "#if !TERMINAL_G4_ADC_SMOKE" in main
    assert "G4_ADC_SMOKE_PIN = 4" in main
    assert "G4_ADC_SMOKE START pin=4 phase=before_m5_begin" in main
    assert "G4_ADC_SMOKE phase=after_m5_begin" in main
    assert "M5.update()" in main[main.index("G4_ADC_SMOKE_PIN = 4") :]
    assert "USB_SETUP_BAUD > 0" in config
    assert "USB_LINE_MAX >= sizeof(\"SETUP_ERR 9999\") - 1" in config
    assert "UPLOAD_ACK_TIMEOUT_MS > 0" in config
    assert "SWITCH_DEBOUNCE_MS <= 1000" in config
    assert "-I../../shared/protocol" not in text


def test_build_helper_requires_terminal_project_in_release_mode() -> None:
    text = read("tools/build.ps1")

    assert 'Invoke-PlatformIOBuild -Target "sticks3-terminal"' in text
    assert "required in CI/release mode" in text
    assert "$script:HadFailure = $true" in text


def test_readme_documents_physical_controls_without_menu_navigation() -> None:
    text = read("firmware/sticks3-terminal/README.md")

    assert "5 sliders" in text
    assert "5 encoders" in text
    assert "no menu navigation" in text
    assert "upload switch" in text
    assert "last physical U206 switch drives SIM_FIRE preview" in text
    assert "USB setup link" in text
    assert "Dial remains" in text


def test_terminal_docs_track_current_slice_and_open_hardware_drivers() -> None:
    doc = read("docs/terminal_architecture.md")
    readme = read("firmware/sticks3-terminal/README.md")

    assert "Current Terminal Implementation" in doc
    assert "ControlSurface" in doc
    assert "external display formatter" in doc
    assert "upload snapshot" in doc
    assert "OLED pixel budget" in doc
    assert "`DisplayRenderPlan` targets a 128x64 OLED pixel budget" in doc
    assert "exactly five framed" in doc
    assert "brightness or `VYP`" in doc
    assert "`ODP`/`---` fire-change" in doc
    assert "large external display is lane-only" in doc
    assert "no title, status, menu, page, or" in doc
    assert "Open Hardware Drivers" in doc
    assert "Hardware Stub Contracts" in doc
    assert "`SETUP_OK <request_id>` / `SETUP_ERR <request_id>`" in doc
    assert "Switch Edge Model" in doc
    assert "active-low" in doc
    assert "Holding a switch must not repeat" in doc
    assert "UPLOAD_ACK_TIMEOUT_MS = 1500" in doc
    assert "USB_LINE_MAX = 160" in doc
    assert "Bench Wiring Snapshot 2026-06-14" in doc
    assert "Primary Pa.HUB port 1 is reserved for now" in doc
    assert "Primary Pa.HUB port 2 is reserved for now" in doc
    assert "Primary Pa.HUB port 3 is the external 2.4 inch display branch" in doc
    assert "Secondary Pa.HUB ports 2, 3, and 4 are reserved" in doc
    assert "The second U206 switch is the global SIM_FIRE preview switch" in doc
    assert "Do not use the rejected direct RGB map" in doc
    assert "Choose the fifth slider ADC strategy before real fader upload" in doc
    assert "overflow" in doc
    assert "sliderPercent" in doc
    assert "encoderDelta" in doc
    assert "effectPressed" in doc
    assert "Fader brightness 0 means the lane is normally off" in doc
    assert "Encoder button toggles whether that lane changes state during fire" in doc
    assert "final physical source for `effectPressed` is still open" not in doc
    assert "Fader brightness 0 means the lane is normally off" in readme
    assert "Encoder button toggles whether that lane changes state during fire" in readme
    assert "one framed row per LED" in readme
    assert "brightness or `VYP`" in readme
    assert "`ODP` or `---`" in readme
    assert "final physical mapping for this edge is still open" not in readme
    assert "ExternalOledDriver" in doc
    assert "fader driver" in doc
    assert "chain encoder driver" in doc
    assert "external OLED driver" in doc
    assert "External OLED driver is disabled by default" in doc
    assert "OLED I2C scan smoke" in doc
    assert "OLED I2C scan smoke is the first hardware step before any LaskaKit sink" in doc
    assert "compile `sticks3-terminal-oled-i2c-scan-smoke` with actual SDA/SCL pins" in doc
    assert "`OLED_I2C_SCAN FOUND 0x..` over USB" in doc
    assert "only then decide whether the panel is M5UnitGLASS2-compatible or needs its own sink" in doc
    assert "Controller, bus address, and pins are hardware bring-up checks" in doc
    assert "must not change the" in doc
    assert "lane-only display contract" in doc
    assert "Grove2USB-C role" in doc
    assert "Hardware bring-up checklist" in readme
    assert "control surface mapper" in readme
    assert "external display formatter" in readme
    assert "`DisplayRenderPlan` is fixed at five framed rows" in readme
    assert "lane number box, color label, brightness text" in readme
    assert "Status and menu text stay on the built-in M5StickS3 status panel" in readme
    assert "Built-in M5StickS3 status panel never mirrors lane rows" in readme
    assert "External OLED is disabled by default and remains a safe no-op" in readme
    assert "Run the OLED I2C scan smoke before enabling a display sink" in readme
    assert "record `OLED_I2C_SCAN FOUND 0x..`, `OLED_I2C_SCAN EXPECTED_FOUND 1`, and" in readme
    assert "`OLED_I2C_SCAN DONE count=..` before enabling any display sink" in readme
    assert "TERMINAL_EXTERNAL_OLED_ENABLED=1" in readme
    assert "TERMINAL_EXTERNAL_OLED_SDA_PIN" in readme
    assert "TERMINAL_EXTERNAL_OLED_SCL_PIN" in readme
    assert "Controller, bus address, and pins are hardware bring-up checks" in readme
    assert "1 CERVENA 100% ---" in readme
    assert "4 BILA    VYP  ODP" in readme
    assert "Switch edge bring-up" in readme
    assert "Hold switch: no repeated command" in readme
    assert "Switch boot priming" in doc
    assert "Switch held while Terminal boots" in readme
    assert "no action is queued" in readme
    assert "UPLOAD_ACK_TIMEOUT_MS = 1500" in readme
    assert "USB_LINE_MAX = 160" in readme
    assert "Current bench wiring snapshot, 2026-06-14" in readme
    assert "Primary Pa.HUB port 5 goes to the secondary Pa.HUB v2.1" in readme
    assert "The first U206 uploads the staged values" in readme
    assert "The second U206 is the global SIM_FIRE preview switch" in readme
    assert "Rejected direct fader+RGB map" in readme
    assert "Use an external ADC/mux or explicitly verified shared pin strategy before real fader upload" in readme


def test_top_level_docs_mark_terminal_setup_transition() -> None:
    readme = read("README.md")
    build = read("BUILD.md")
    hardware = read("docs/hardware.md")
    bench = read("docs/bench_test_checklist.md")

    for text in (readme, build, hardware, bench):
        normalized = " ".join(text.split())
        assert "M5StickS3 Terminal" in text
        assert "Terminal owns setup editing" in normalized
        assert "Terminal has no radio module" in normalized
        assert "Dial remains the radio fire controller" in normalized
        assert "DinMeter remains the receiver-side safety authority" in normalized
        assert "setup persistence owner" in normalized
        assert "LED execution/indication surface" in normalized

    assert "firmware/sticks3-terminal" in readme
    assert "shared/terminal" in readme
    assert "| **sticks3-terminal** | M5StickS3 Terminal" in readme
    assert "PlatformIO + host `g++` tests" in readme
    assert "pio run -d firmware/sticks3-terminal -e sticks3-terminal" in build
    assert "sticks3-terminal-oled-i2c-scan-smoke uses dummy G1/G2 pins" in build
    assert "sticks3-terminal-g4-adc-smoke" in build
    assert "sticks3-terminal-grove-i2c-scan-smoke" in build
    assert "G9/G10" in build
    assert "0x70" in build
    assert "G4 tracked fader movement from raw 0 to" in build
    assert "physical bottom is raw 4095" in build
    assert "TERMINAL_FADER_RAW_MIN=4095" in build
    assert "TERMINAL_FADER_RAW_MAX=0" in build
    assert "TERMINAL_EXTERNAL_OLED_SDA_PIN" in build
    assert "TERMINAL_EXTERNAL_OLED_SCL_PIN" in build
    assert "CI-equivalent local gate from the ESPOS repo root" in build
    assert "python -m pytest -q --tb=short tests" in build
    assert "python tools/uiflow_dial_offline.py verify --bundle build/m5_uiflow_dial_offline" in build
    assert "sudo apt-get install g++" in build
    assert "xcode-select --install" in build
    assert "SETUP <request_id>" in bench
    assert "SETUP_OK <request_id>" in bench
    assert "SETUP_ERR <request_id>" in bench
    assert "Wire the Terminal bench snapshot exactly" in bench
    assert "Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch" in bench
    assert "primary port 5 to the secondary Pa.HUB" in bench
    assert "Primary ports 1/2 and secondary ports 2/3/4 are" in bench
    assert "reserved for now and must not be used for Pot1..Pot5 signal reads" in bench
    assert "Treat LED1..LED5 as logical lane names" in bench
    assert "last U206 switch emits one SIM_FIRE preview edge" in bench
    assert "Pot1..Pot5 are M5Stack Unit Fader U123 modules" in bench
    assert "Do not expect Pa.HUB to read slider position or drive fader LEDs" in bench
    assert "First fader slice is slider-only" in bench
    assert "leave Unit Fader SK6812 LEDs" in bench
    assert "Do not use the rejected bare StickS3 fader+RGB map" in bench
    assert "Official StickS3 docs mark `G1..G4` as shared internal" in bench
    assert "Choose and document the fifth slider ADC strategy before real fader upload" in bench
    assert "G4 ADC smoke on 2026-06-14" in bench
    assert "tracked fader" in bench
    assert "raw 0 and raw 4095 endpoints" in bench
    assert "verified shared-pin candidate" in bench
    assert "physical bottom is raw 4095" in bench
    assert "rawMin greater than rawMax" in bench
    assert "Flash `sticks3-terminal-oled-i2c-scan-smoke` with real SDA/SCL pins" in bench
    assert "sticks3-terminal-grove-i2c-scan-smoke" in bench
    assert "SDA G9, SCL G10" in bench
    assert "0x70" in bench
    assert "record `OLED_I2C_SCAN FOUND`, `OLED_I2C_SCAN EXPECTED_FOUND 1`, and" in bench
    assert "`OLED_I2C_SCAN DONE`, then decide M5UnitGLASS2-compatible vs dedicated sink" in bench
    assert "decide M5UnitGLASS2-compatible vs dedicated sink" in bench
    assert "sticks3-terminal-oled-i2c-scan-smoke" in hardware
    assert "OLED_I2C_SCAN FOUND" in hardware
    assert "OLED_I2C_SCAN DONE" in hardware
    assert "tools/read_com.py" in hardware
    assert "Change at least two physical lane values" in bench
    assert "DinMeter may already have committed" in bench
    assert "SIM_FIRE leaves Terminal draft/saved state unchanged" in bench
    assert "second U206 switch is the global SIM_FIRE preview switch" in hardware


def test_active_docs_do_not_assign_setup_editing_to_dial_or_dinmeter() -> None:
    active_docs = [
        "README.md",
        "BUILD.md",
        "docs/M5_PROP_CONTROLLER.md",
        "docs/bench_test_checklist.md",
        "docs/control_architecture.md",
        "docs/dinmeter_effect_ui.md",
    ]
    forbidden = [
        "UI na DinMeteru",
        "Barvy / Čas / Jas",
        "Obousměrná synchronizace barev",
        "On the Dial, set a custom palette",
        "navolí barvy/efekt",
        "Dial posílá jen barvy + FIRE trigger",
        "SETUP LED/HUE/JAS",
        "SETUP (tune)",
        "LED → HUE → JAS",
        "Dial owns per-LED COLOUR",
        "set hue",
        "control hue",
        "lane hue",
        "chain encoders control hue",
        "direct physical lanes for hue",
    ]

    for relative_path in active_docs:
        text = read(relative_path)
        for needle in forbidden:
            assert needle not in text, f"{relative_path} still contains stale setup ownership: {needle}"


def test_first_upload_runbook_covers_dial_terminal_and_prop_electronics() -> None:
    runbook = read("docs/first_upload_runbook.md")
    build = read("BUILD.md")
    readme = read("README.md")
    checklist = read("docs/bench_test_checklist.md")
    flash = read("tools/flash.ps1")
    preflight = read("tools/first_upload_preflight.py")

    for needle in [
        "First Upload Runbook",
        "Odpalovac / Dial",
        "M5StickS3 Terminal USB setup editor",
        "Prop electronics",
        "Do not connect live pyro or actuator outputs",
        "python -m esptool version",
        "python -m mpremote --help",
        "python tools/first_upload_preflight.py --out build/first_upload_preflight.md",
        "idf.py` is not on PATH",
        "`pio device list` currently shows only `COM1`",
        "<DIAL_COM>",
        "<TERMINAL_COM>",
        "<DIN_COM>",
        "<MODEM_DIAL_COM>",
        "<MODEM_PROP_COM>",
        "Runtime HMAC Key Preflight",
        "m5stack-c6l",
        "PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1",
        "Dial NVS partition is `0x9000` size `0x6000`",
        "derive the actual `data,nvs` offset/size",
        "prop_key_receipt.template.json",
        "`PENDING_HARDWARE` receipt blocks positive acceptance",
        "-DryRun",
        "tools/flash.ps1 -Target c6l-modem",
        "tools/flash.ps1 -Target din-rx",
        "tools/flash.ps1 -Target sticks3-terminal",
        "tools/flash.ps1 -Target dial-tx",
        "SETUP_OK <request_id>",
        "SETUP_ERR <request_id>",
        "SIM_FIRE <request_id>",
    ]:
        assert needle in runbook, needle

    assert "docs/first_upload_runbook.md" in build
    assert "docs/first_upload_runbook.md" in readme
    assert "docs/first_upload_runbook.md" in checklist
    assert 'ValidateSet("dial-tx", "din-rx", "c6l-modem", "sticks3-terminal")' in flash
    assert '"sticks3-terminal"' in flash
    assert "[switch]$DryRun" in flash
    assert "DRY RUN:" in flash
    assert "DRY RUN: idf.py -p $Port flash" in flash
    for needle in [
        "First Upload Preflight",
        "Gemini key source",
        "Claude Code via npx",
        "pio device list",
        "Dry-run Flash Commands",
        "PENDING_HARDWARE",
        "<DIAL_COM>",
        "<TERMINAL_COM>",
        "<DIN_COM>",
    ]:
        assert needle in preflight, needle


def test_terminal_external_oled_preview_tool_renders_review_png() -> None:
    import importlib.util

    tool = ROOT / "tools" / "preview_terminal_oled.py"
    spec = importlib.util.spec_from_file_location("preview_terminal_oled", tool)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    image = module.render_terminal_oled()

    assert image.mode == "RGB"
    assert image.size == (512, 256)
    assert len(image.getcolors(maxcolors=image.width * image.height)) > 2
    assert module.ROWS[0].color == "CERVENA"
    assert module.ROWS[0].label == "100%"
    assert module.ROWS[1].effect_label == "ODP"
    assert module.ROWS[3].label == "VYP"
    assert module.ROWS[4].color == "MODRA"


def test_terminal_external_oled_preview_has_espos_pixel_guardrails() -> None:
    import importlib.util

    tool = ROOT / "tools" / "preview_terminal_oled.py"
    spec = importlib.util.spec_from_file_location("preview_terminal_oled", tool)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    image = module.render_terminal_oled()
    colors = image.getcolors(maxcolors=image.width * image.height)
    assert colors is not None
    assert len(colors) <= 6
    assert "GLYPHS_5X7" in tool.read_text(encoding="utf-8")

    scale = module.SCALE
    bright_threshold = 220
    for index, row in enumerate(module.ROWS):
        y0 = (module.ROW_START + index * module.ROW_H) * scale
        y1 = y0 + module.ROW_H * scale
        x0 = 101 * scale
        x1 = 124 * scale
        bright_pixels = 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixel = image.getpixel((x, y))
                if min(pixel) >= bright_threshold:
                    bright_pixels += 1
        if row.effect:
            assert 1800 <= bright_pixels <= 3200
        else:
            assert bright_pixels <= 700
