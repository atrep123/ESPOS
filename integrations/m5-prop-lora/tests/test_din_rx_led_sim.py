from __future__ import annotations

import re
import sys
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import FrameType, encode_led_payload, parse_led_payload  # noqa: E402

_SIM_SPEC = importlib.util.spec_from_file_location(
    "m5_preview_din_rx", ROOT / "tools" / "preview_din_rx.py"
)
assert _SIM_SPEC is not None and _SIM_SPEC.loader is not None
sim = importlib.util.module_from_spec(_SIM_SPEC)
sys.modules[_SIM_SPEC.name] = sim
_SIM_SPEC.loader.exec_module(sim)


PROP_RX_CPP = ROOT / "firmware/din-rx/src/prop_rx.cpp"
PROP_RX_H = ROOT / "firmware/din-rx/src/prop_rx.h"
MAIN_CPP = ROOT / "firmware/din-rx/src/main.cpp"
VIEW_CPP = ROOT / "firmware/din-rx/src/view/view.cpp"
PROTOCOL_H = ROOT / "shared/protocol/prop_protocol.h"


FIXTURE_COLORS: tuple[sim.Rgb, ...] = (
    (255, 30, 30),
    (30, 220, 90),
    (40, 120, 255),
    (255, 180, 0),
)


def fixture_payload(brightness: int = 150, colors: tuple[sim.Rgb, ...] = FIXTURE_COLORS) -> bytes:
    return encode_led_payload(brightness, list(colors))


def independent_requested_brightness(settings: sim.EffectSettings) -> int:
    return min(settings.dial_brightness, settings.master_brightness)


def independent_scale_rgb(color: sim.Rgb, brightness: int) -> sim.Rgb:
    return tuple(component * brightness // 255 for component in color)  # type: ignore[return-value]


def display_text(frame: sim.RenderedFrame, role: str) -> str:
    matches = [op.text for op in frame.display_ops if op.role == role]
    assert len(matches) == 1
    return matches[0]


def _cpp_int_constant(text: str, name: str) -> int:
    match = re.search(rf"{name}\s*=\s*(\d+)", text)
    assert match, f"{name} not found"
    return int(match.group(1))


def _cpp_hex_constant(text: str, name: str) -> int:
    match = re.search(rf"{name}\s*=\s*0x([0-9A-Fa-f]+)", text)
    assert match, f"{name} not found"
    return int(match.group(1), 16)


def _cpp_string_assignments(text: str, name: str) -> set[str]:
    return set(re.findall(rf'{name}\s*=\s*"([^"]+)"', text))


def _extract_default_colors(text: str) -> tuple[sim.Rgb, ...]:
    match = re.search(r"colors\[LED_COUNT\]\[3\]\s*=\s*\{(.*?)\};", text, re.S)
    assert match
    return tuple(
        tuple(map(int, item))
        for item in re.findall(r"(\d+),\s*(\d+),\s*(\d+)", match.group(1))
    )


def _extract_default_timings(text: str) -> tuple[sim.LedTiming, ...]:
    block = re.search(r"LedTiming led\[LED_COUNT\]\s*=\s*\{(.*?)\};", text, re.S)
    assert block
    return tuple(
        sim.LedTiming(*map(int, item))
        for item in re.findall(r"\{(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\}", block.group(1))
    )


def test_idle_state_renders_no_ws2812_light_and_ready_status() -> None:
    frame = sim.render_frame(sim.ReceiverState())

    assert frame.base_frame == ((0, 0, 0),) * sim.LED_COUNT
    assert frame.ws2812_frame == ((0, 0, 0),) * sim.LED_COUNT
    assert frame.budgeted_brightness == 150
    assert frame.active_led_count == 0
    assert frame.display_lines == (
        "Prop RX",
        "Port B G2: 4 WS2812",
        "UART1 115200 G13/G15",
        "State: READY",
        "LED 1",
        "L1 on D0 FI120 H160 FO260",
        "Dial 150  Master 150  repeat off",
        "Short press field, hold exits",
    )


def test_accepted_preview_payload_renders_all_enabled_led_colors_after_budget() -> None:
    state = sim.state_after_accepted_frame(FrameType.PREVIEW, fixture_payload())
    frame = sim.render_frame(state)

    expected_budget = 150
    expected_ws2812 = tuple(independent_scale_rgb(color, expected_budget) for color in FIXTURE_COLORS)

    assert parse_led_payload(fixture_payload()) == {"brightness": 150, "colors": list(FIXTURE_COLORS)}
    assert frame.base_frame == FIXTURE_COLORS
    assert frame.budgeted_brightness == expected_budget == 150
    assert frame.ws2812_frame == expected_ws2812
    assert frame.active_led_count == 4
    assert display_text(frame, "state") == "PREVIEW"
    assert display_text(frame, "brightness") == "Dial 150  Master 150  repeat off"


def test_fire_effect_renders_timed_sequence_before_budgeting() -> None:
    state = sim.state_after_accepted_frame(FrameType.FIRE, fixture_payload())
    frame = sim.render_frame(state, elapsed_ms=200)

    expected_base = (
        FIXTURE_COLORS[0],
        independent_scale_rgb(FIXTURE_COLORS[1], 127),
        (0, 0, 0),
        (0, 0, 0),
    )
    expected_budget = 150

    assert sim.led_level_at(state.settings.led[0], 200) == 255
    assert sim.led_level_at(state.settings.led[1], 200) == 127
    assert frame.base_frame == expected_base
    assert frame.ws2812_frame == tuple(independent_scale_rgb(color, expected_budget) for color in expected_base)
    assert frame.active_led_count == 2
    assert display_text(frame, "state") == "FIRE"


def test_stop_and_fault_states_keep_ws2812_output_dark_but_status_distinct() -> None:
    stop = sim.render_frame(sim.state_after_accepted_frame(FrameType.STOP))
    bad_mac = sim.render_frame(sim.state_after_fault("BAD MAC"))
    bad_payload = sim.render_frame(sim.state_after_fault("BAD PAYLOAD"))

    assert stop.ws2812_frame == ((0, 0, 0),) * sim.LED_COUNT
    assert bad_mac.ws2812_frame == ((0, 0, 0),) * sim.LED_COUNT
    assert bad_payload.ws2812_frame == ((0, 0, 0),) * sim.LED_COUNT
    assert display_text(stop, "state") == "STOP"
    assert display_text(bad_mac, "state") == "BAD MAC"
    assert display_text(bad_payload, "state") == "BAD PAYLOAD"


def test_idle_accepted_and_fault_render_signatures_are_distinct() -> None:
    idle = sim.render_frame(sim.ReceiverState())
    accepted = sim.render_frame(sim.state_after_accepted_frame(FrameType.PREVIEW, fixture_payload()))
    fault = sim.render_frame(sim.state_after_fault("BAD MAC"))

    signatures = {
        "idle": (idle.ws2812_frame, idle.display_lines),
        "accepted": (accepted.ws2812_frame, accepted.display_lines),
        "fault": (fault.ws2812_frame, fault.display_lines),
    }
    assert len(set(signatures.values())) == len(signatures)


def test_power_budget_reduces_full_white_frame_and_final_rgb_stays_in_range() -> None:
    colors = ((255, 255, 255),) * sim.LED_COUNT
    settings = sim.EffectSettings(master_brightness=255, dial_brightness=255, colors=colors)
    state = sim.ReceiverState(settings=settings, mode=sim.EffectMode.PREVIEW, last_status="PREVIEW")
    frame = sim.render_frame(state)

    assert frame.budgeted_brightness == 229
    assert frame.ws2812_frame == ((229, 229, 229),) * sim.LED_COUNT
    assert frame.active_led_count == 4
    for color in frame.ws2812_frame:
        assert all(0 <= component <= 255 for component in color)


@pytest.mark.parametrize(
    "base_frame,settings,expected_budget",
    [
        (((0, 0, 0),) * sim.LED_COUNT, sim.EffectSettings(), 150),
        (FIXTURE_COLORS, sim.EffectSettings(colors=FIXTURE_COLORS), 150),
        (
            ((255, 255, 255),) * sim.LED_COUNT,
            sim.EffectSettings(255, 255, 0, ((255, 255, 255),) * 4),
            229,
        ),
        (
            ((255, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)),
            sim.EffectSettings(master_brightness=40),
            40,
        ),
        (
            ((255, 255, 255),) * sim.LED_COUNT,
            sim.EffectSettings(master_brightness=0, dial_brightness=255),
            0,
        ),
    ],
)
def test_budgeted_brightness_matches_literal_current_limit_examples(
    base_frame: tuple[sim.Rgb, ...],
    settings: sim.EffectSettings,
    expected_budget: int,
) -> None:
    assert sim.budgeted_brightness(base_frame, settings) == expected_budget


@pytest.mark.parametrize(
    "elapsed_ms,levels",
    [
        (0, (0, 0, 0, 0)),
        (119, (252, 0, 0, 0)),
        (120, (255, 0, 0, 0)),
        (200, (255, 127, 0, 0)),
        (420, (118, 255, 255, 0)),
        (699, (0, 0, 119, 255)),
    ],
)
def test_led_level_timeline_matches_firmware_integer_fades(elapsed_ms: int, levels: tuple[int, ...]) -> None:
    settings = sim.EffectSettings()
    assert tuple(sim.led_level_at(timing, elapsed_ms) for timing in settings.led) == levels


def test_repeat_fire_wraps_at_effect_cycle() -> None:
    payload = fixture_payload()
    state = sim.state_after_accepted_frame(FrameType.FIRE, payload)
    repeating = replace(state, settings=replace(state.settings, repeat=1))

    cycle = sim.effect_cycle_ms(repeating.settings)
    assert cycle == 960
    assert sim.render_frame(repeating, elapsed_ms=cycle + 200).base_frame == sim.render_frame(
        repeating, elapsed_ms=200
    ).base_frame
    assert sim.render_frame(state, elapsed_ms=cycle + 1).base_frame == ((0, 0, 0),) * sim.LED_COUNT


@pytest.mark.parametrize(
    "field,selected_led,settings,expected_label,expected_value,expected_timing,expected_brightness",
    [
        (
            sim.UiField.LED,
            2,
            sim.EffectSettings(),
            "LED",
            "3",
            "L3 on D280 FI120 H160 FO260",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.ENABLED,
            1,
            sim.EffectSettings(led=(sim.DEFAULT_TIMINGS[0], sim.LedTiming(0, 140, 120, 160, 260), *sim.DEFAULT_TIMINGS[2:])),
            "enabled",
            "off",
            "L2 off D140 FI120 H160 FO260",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.DELAY,
            0,
            sim.EffectSettings(led=(sim.LedTiming(1, 25, 120, 160, 260), *sim.DEFAULT_TIMINGS[1:])),
            "delayMs",
            "25ms",
            "L1 on D25 FI120 H160 FO260",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.FADE_IN,
            0,
            sim.EffectSettings(led=(sim.LedTiming(1, 0, 145, 160, 260), *sim.DEFAULT_TIMINGS[1:])),
            "fadeInMs",
            "145ms",
            "L1 on D0 FI145 H160 FO260",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.HOLD,
            0,
            sim.EffectSettings(led=(sim.LedTiming(1, 0, 120, 185, 260), *sim.DEFAULT_TIMINGS[1:])),
            "holdMs",
            "185ms",
            "L1 on D0 FI120 H185 FO260",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.FADE_OUT,
            0,
            sim.EffectSettings(led=(sim.LedTiming(1, 0, 120, 160, 285), *sim.DEFAULT_TIMINGS[1:])),
            "fadeOutMs",
            "285ms",
            "L1 on D0 FI120 H160 FO285",
            "Dial 150  Master 150  repeat off",
        ),
        (
            sim.UiField.REPEAT,
            0,
            sim.EffectSettings(repeat=1),
            "repeat",
            "on",
            "L1 on D0 FI120 H160 FO260",
            "Dial 150  Master 150  repeat on",
        ),
        (
            sim.UiField.MASTER_BRIGHTNESS,
            0,
            sim.EffectSettings(master_brightness=95, dial_brightness=175),
            "masterBrightness",
            "95",
            "L1 on D0 FI120 H160 FO260",
            "Dial 175  Master 95  repeat off",
        ),
        (
            sim.UiField.PREVIEW,
            0,
            sim.EffectSettings(),
            "preview",
            "turn",
            "L1 on D0 FI120 H160 FO260",
            "Dial 150  Master 150  repeat off",
        ),
    ],
)
def test_status_display_text_matches_firmware_field_and_brightness_lines(
    field: sim.UiField,
    selected_led: int,
    settings: sim.EffectSettings,
    expected_label: str,
    expected_value: str,
    expected_timing: str,
    expected_brightness: str,
) -> None:
    state = sim.ReceiverState(settings=settings, field=field, selected_led=selected_led, last_status="PREVIEW")
    frame = sim.render_frame(state)

    assert display_text(frame, "field_label") == expected_label
    assert display_text(frame, "field_value") == expected_value
    assert display_text(frame, "timing") == expected_timing
    assert display_text(frame, "brightness") == expected_brightness


def test_status_display_draw_ops_keep_exact_canvas_text_positions_and_colors() -> None:
    frame = sim.render_frame(sim.ReceiverState())
    expected = {
        "title": ("Prop RX", 120, 6, sim.COLOR_TEXT, sim.COLOR_PANEL, 2, True),
        "port": ("Port B G2: 4 WS2812", 8, 34, sim.COLOR_MUTED, sim.COLOR_BG, 1, False),
        "uart": ("UART1 115200 G13/G15", 8, 47, sim.COLOR_MUTED, sim.COLOR_BG, 1, False),
        "state_label": ("State:", 8, 66, sim.COLOR_GOOD, sim.COLOR_BG, 1, False),
        "state": ("READY", 56, 66, sim.COLOR_TEXT, sim.COLOR_BG, 1, False),
        "field_label": ("LED", 8, 86, sim.COLOR_WARN, sim.COLOR_BG, 1, False),
        "field_value": ("1", 130, 86, sim.COLOR_TEXT, sim.COLOR_BG, 1, False),
        "hint": ("Short press field, hold exits", 8, 136, sim.COLOR_MUTED, sim.COLOR_BG, 1, False),
    }

    for op in frame.display_ops:
        if op.role in expected:
            assert (op.text, op.x, op.y, op.color, op.background, op.text_size, op.centered) == expected[op.role]


@pytest.mark.parametrize("name,state_elapsed", sim.scenes().items())
def test_all_builtin_scenes_are_headless_deterministic_and_rgb_safe(
    name: str,
    state_elapsed: tuple[sim.ReceiverState, int],
) -> None:
    state, elapsed_ms = state_elapsed
    first = sim.render_frame(state, elapsed_ms)
    second = sim.render_frame(state, elapsed_ms)

    assert first == second, name
    assert len(first.ws2812_frame) == sim.LED_COUNT
    assert len(first.display_ops) == 10
    for color in first.ws2812_frame:
        assert len(color) == 3
        assert all(0 <= component <= 255 for component in color)


def test_current_dinmeter_led_hardware_contract_matches_firmware_source() -> None:
    cpp = PROP_RX_CPP.read_text(encoding="utf-8")
    config = (ROOT / "firmware/din-rx/src/prop_config.h").read_text(encoding="utf-8")

    assert "constexpr int LED_COUNT = 5;" in config
    assert "constexpr int LED_STRIP_MAX = 30;" in config
    assert "constexpr bool PROP_IO_XIAO_UART_ENABLED = true;" in config
    assert "constexpr int           PROP_IO_UART_TX_PIN = 2;" in config
    assert "constexpr int           PROP_IO_UART_RX_PIN = 1;" in config
    assert "constexpr std::uint8_t  XIAO_BARREL_WS2812_COUNT = 18;" in config
    assert "constexpr std::uint8_t  XIAO_STATUS_LED_COUNT    = 4;" in config
    assert "XIAO_STATUS_LED_CHANNELS[XIAO_STATUS_LED_COUNT]" in config
    default_presets_match = re.search(r"DEFAULT_LED_PRESET_IDX\[LED_COUNT\]\s*=\s*\{([^}]+)\}", config)
    assert default_presets_match
    default_presets = [int(value.strip()) for value in default_presets_match.group(1).split(",")]
    assert default_presets[0] == 1  # Slot 1 / button 1 is green.
    assert default_presets[1] == 0  # Slot 3 / button 2 is red.
    assert default_presets[2] == 0  # Slot 4 / switch is red.
    assert default_presets[3] == 2  # Slot 2 / odpal indicator is blue.
    assert default_presets[4] == 0  # Barrel lane / 18x WS2812 is red.
    status_channels = config.split("XIAO_STATUS_LED_CHANNELS", 1)[1].split("};", 1)[0]
    assert "LED_ROLE_BUTTON1" in status_channels
    assert "LED_ROLE_BUTTON2" in status_channels
    assert "LED_ROLE_SWITCH" in status_channels
    assert "LED_ROLE_ODPAL" in status_channels
    assert "LED_ROLE_BARREL" not in status_channels
    status_role_order = re.findall(r"LED_ROLE_[A-Z0-9_]+", status_channels)
    assert status_role_order == [
        "LED_ROLE_BUTTON1",
        "LED_ROLE_ODPAL",
        "LED_ROLE_BUTTON2",
        "LED_ROLE_SWITCH",
    ]
    assert "constexpr std::uint8_t LED_ORDER[LED_COUNT] = {0, 2, 3, 4, 1};" in config
    order_match = re.search(r"LED_ORDER\[LED_COUNT\]\s*=\s*\{([^}]+)\}", config)
    assert order_match
    order = [int(value.strip()) for value in order_match.group(1).split(",")]
    assert sorted(order) == list(range(5))

    assert '#include "prop_xiao_link.h"' in cpp
    assert "HardwareSerial propIoSerial(2);" in cpp
    assert "beginXiaoPropIo();" in cpp
    assert "readXiaoPropIo();" in cpp
    assert "LOCAL_FIRE_RETRIGGER_MIN_MS" in config
    assert "acceptLocalFirePulse" in cpp
    assert "bool firePulse = parsed.input.index == 3 && parsed.input.active;" in cpp
    assert "applyLocalInputLevels(_xiaoSwitch, _xiaoBtn1, _xiaoBtn2, _xiaoFire, firePulse, \"xiao\")" in cpp
    assert "applyLocalInputLevels(_xiaoSwitch, _xiaoBtn1, _xiaoBtn2, _xiaoFire, false, \"xiao\")" in cpp
    assert "applyLocalInputLevels(sw, b1, b2, b3, false, \"bb\")" in cpp
    input_levels_body = cpp.split("void applyLocalInputLevels", 1)[1].split("void tickByteButton", 1)[0]
    assert "const bool fireEdge = b3 && !_bbPrev3;" in input_levels_body
    assert "const bool fireRequest = firePulse || fireEdge;" in input_levels_body
    assert "if (fireRequest && acceptLocalFirePulse(millis()))" in input_levels_body
    btn2_branch = re.search(r"if \(b2Edge\)\s*\{([^}]+)\}", input_levels_body)
    assert btn2_branch
    assert "_led2On = !_led2On" in btn2_branch.group(1)
    assert "_led3RemoteOn = !_led3RemoteOn" not in btn2_branch.group(1)
    assert "sendXiaoOutputFrame(scaled)" in cpp
    assert "formatStat4Line(status)" in cpp
    assert "frame[LED_ROLE_BARREL]" in cpp
    assert "formatBarrelRedLine(barrel)" in cpp
    assert "formatBarrelOffLine()" in cpp
    assert "nextXiaoPingSeq()" in cpp
    assert "_xiaoPingSeq >= prop_xiao_link::MAX_SEQUENCE ? 1" in cpp
    assert "xiaoFresh = xiaoLinkOk(hbNow)" in cpp
    assert "currentXiaoLinkOk" in cpp
    assert "_xiaoLinkOkVisible" in cpp
    assert "markXiaoOutputMissing()" in cpp
    assert '"NO_XIAO"' in cpp
    assert 'xiaoOutputReady(millis()) ? "NO_EFFECT" : "NO_XIAO"' in cpp
    assert cpp.index("beginXiaoPropIo();") < cpp.index("int sda = I2C_SDA_PIN")

    # Legacy bench fallback remains compiled, but production mode must not be the
    # Port-B I2C ByteButton/NeoDriver path.
    assert "seesaw_NeoPixel pixels(LED_STRIP_MAX, NEODRIVER_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800, &Wire1)" in cpp
    assert "pixels.updateLength(LED_COUNT)" in cpp
    assert "const int phys = (i < LED_COUNT) ? LED_ORDER[i] : i;" in cpp
    assert "pixels.setPixelColor(phys, c.r, c.g, c.b, 0)" in cpp
    assert "#include <Adafruit_NeoPixel" not in cpp
    assert "Adafruit_NeoPixel pixels(" not in cpp
    assert "constexpr int LED_PIN" not in cpp


def test_xiao_d2_local_fire_is_lockout_only_not_lora_arm_gated() -> None:
    cpp = PROP_RX_CPP.read_text(encoding="utf-8")
    local_fire = cpp.split("void tryLocalFire()", 1)[1].split("bool terminalEffectAllowsOdpal", 1)[0]

    assert "if (_lockout)" in local_fire
    assert 'setStatus("STOP")' in local_fire
    assert "triggerOdpal();" in local_fire
    assert "_armed" not in local_fire
    assert "fireWouldArm" not in local_fire

    arm_handler = cpp.split("if (frame.type == prop_protocol::FrameType::Arm)", 1)[1].split(
        "if (frame.type == prop_protocol::FrameType::Fire)",
        1,
    )[0]
    stop_handler = cpp.split("if (frame.type == prop_protocol::FrameType::Stop)", 1)[1].split(
        "if (frame.type == prop_protocol::FrameType::Ping",
        1,
    )[0]
    assert "_lockout = false" in arm_handler
    assert "_lockout = true" in stop_handler


def test_dinmeter_hrana_odpal_curve_is_full_on_at_trigger_start() -> None:
    cpp = PROP_RX_CPP.read_text(encoding="utf-8")
    curve_body = cpp.split("static float curveShape", 1)[1].split("RenderColor odpalColor", 1)[0]

    assert curve_body.index("if (curve == 0) return 1.0f;") < curve_body.index("if (p <= 0.0f) return 0.0f;")


def test_current_dinmeter_display_source_is_indication_not_legacy_setup_editor() -> None:
    cpp = PROP_RX_CPP.read_text(encoding="utf-8")

    for literal in (
        "TERMINAL_SETUP_MAGIC",
        "TERMINAL_SETUP_KEY",
        "LED 1",
        "SPINAC",
        "ODPAL",
        "LED 5",
        "SETUP BUSY",
        "SETUP ERR",
    ):
        assert literal in cpp

    assert "DINMETER_LOCAL_SETUP_EDITOR_ENABLED" in cpp
    assert "if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)" in cpp


def test_legacy_preview_sim_is_not_current_dinmeter_firmware_parity() -> None:
    cpp = PROP_RX_CPP.read_text(encoding="utf-8")

    assert sim.LED_COUNT == 4
    assert "constexpr int LED_COUNT = 5;" in (ROOT / "firmware/din-rx/src/prop_config.h").read_text(
        encoding="utf-8"
    )
    assert "seesaw_NeoPixel pixels" in cpp
    assert "Adafruit_NeoPixel pixels(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800)" not in cpp


def test_protocol_constants_and_payload_contract_match_receiver_sim() -> None:
    protocol_h = PROTOCOL_H.read_text(encoding="utf-8")

    assert "LED_PAYLOAD_LENGTH = 13" in protocol_h
    assert "FrameType::Preview" in protocol_h
    assert "FrameType::Fire" in protocol_h
    assert fixture_payload() == bytes([150, 255, 30, 30, 30, 220, 90, 40, 120, 255, 255, 180, 0])
    state = sim.state_after_accepted_frame(FrameType.PREVIEW, fixture_payload())
    assert state.settings.dial_brightness == 150
    assert state.settings.colors == FIXTURE_COLORS


def test_din_rx_entrypoint_boots_straight_into_real_prop_rx_not_stub() -> None:
    header = PROP_RX_H.read_text(encoding="utf-8")
    main = MAIN_CPP.read_text(encoding="utf-8")

    # main.cpp boots straight into the receiver: the old factory-launcher view_create/view_update
    # indirection was removed this session. setup() shows a brief boot logo, loop() runs the real
    # prop_rx_run(&ft) -- never a stub / factory menu.
    assert "void prop_rx_run(FactoryTest* ft);" in header
    assert "show_boot_logo(&ft);" in main
    assert "prop_rx_run(&ft);" in main
    assert "view_create" not in main  # the factory-launcher indirection is gone
