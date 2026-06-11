"""Deterministic desktop model for the din-rx Prop RX renderer.

This is a data simulation, not firmware. It mirrors the rendering decisions in
``firmware/din-rx/src/prop_rx.cpp`` closely enough for pytest to catch drift in:

* the 4-pixel WS2812 output on Port B / G2 after power-budgeted brightness
* the small LovyanGFX status canvas text drawn by ``PropRxApp::render``
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import IntEnum
from pathlib import Path
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import FrameType, ProtocolError, parse_led_payload


Rgb = tuple[int, int, int]


LED_COUNT = 4
LED_PIN = 2
UART1_TX_PIN = 13
UART1_RX_PIN = 15
MODEM_BAUD = 115200
EFFECT_RENDER_MS = 20
LONG_PRESS_EXIT_MS = 900
SETTINGS_SAVE_DEBOUNCE_MS = 500
LED_CURRENT_BUDGET_MA = 220
WS2812_CHANNEL_MA = 20
WS2812_IDLE_MA = 1
PROP_KEY_ID = 1
PROP_SOURCE = 0x22
PROP_DESTINATION = 0x11

COLOR_BG = 0x101820
COLOR_PANEL = 0x1F3A3D
COLOR_TEXT = 0xE8FFF5
COLOR_MUTED = 0x7AA39B
COLOR_GOOD = 0x50D890
COLOR_WARN = 0xF7B267

DEFAULT_COLORS: tuple[Rgb, ...] = (
    (255, 0, 0),
    (255, 120, 0),
    (255, 255, 255),
    (30, 90, 255),
)


class EffectMode(IntEnum):
    IDLE = 0
    PREVIEW = 1
    FIRE = 2


class UiField(IntEnum):
    LED = 0
    ENABLED = 1
    DELAY = 2
    FADE_IN = 3
    HOLD = 4
    FADE_OUT = 5
    REPEAT = 6
    MASTER_BRIGHTNESS = 7
    PREVIEW = 8


@dataclass(frozen=True)
class LedTiming:
    enabled: int = 1
    delay_ms: int = 0
    fade_in_ms: int = 120
    hold_ms: int = 160
    fade_out_ms: int = 260


DEFAULT_TIMINGS: tuple[LedTiming, ...] = (
    LedTiming(1, 0, 120, 160, 260),
    LedTiming(1, 140, 120, 160, 260),
    LedTiming(1, 280, 120, 160, 260),
    LedTiming(1, 420, 120, 160, 260),
)


@dataclass(frozen=True)
class EffectSettings:
    master_brightness: int = 150
    dial_brightness: int = 150
    repeat: int = 0
    colors: tuple[Rgb, ...] = DEFAULT_COLORS
    led: tuple[LedTiming, ...] = DEFAULT_TIMINGS

    def __post_init__(self) -> None:
        if len(self.colors) != LED_COUNT:
            raise ValueError(f"expected {LED_COUNT} colors")
        if len(self.led) != LED_COUNT:
            raise ValueError(f"expected {LED_COUNT} timing records")
        normalized_colors = tuple(tuple(clamp_byte(c) for c in color) for color in self.colors)
        object.__setattr__(self, "colors", normalized_colors)
        object.__setattr__(self, "master_brightness", clamp_byte(self.master_brightness))
        object.__setattr__(self, "dial_brightness", clamp_byte(self.dial_brightness))
        object.__setattr__(self, "repeat", 1 if self.repeat else 0)


@dataclass(frozen=True)
class ReceiverState:
    settings: EffectSettings = field(default_factory=EffectSettings)
    mode: EffectMode = EffectMode.IDLE
    field: UiField = UiField.LED
    selected_led: int = 0
    last_status: str = "READY"

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_led", max(0, min(LED_COUNT - 1, int(self.selected_led))))
        object.__setattr__(self, "mode", EffectMode(self.mode))
        object.__setattr__(self, "field", UiField(self.field))


@dataclass(frozen=True)
class DisplayText:
    role: str
    text: str
    x: int
    y: int
    color: int
    background: int | None = None
    text_size: int = 1
    centered: bool = False


@dataclass(frozen=True)
class RenderedFrame:
    state: ReceiverState
    base_frame: tuple[Rgb, ...]
    budgeted_brightness: int
    ws2812_frame: tuple[Rgb, ...]
    display_ops: tuple[DisplayText, ...]
    display_lines: tuple[str, ...]

    @property
    def active_led_count(self) -> int:
        return sum(1 for color in self.ws2812_frame if any(color))


def clamp_byte(value: int) -> int:
    return max(0, min(255, int(value)))


def clamp_ms(value: int) -> int:
    return max(0, min(5000, int(value)))


def requested_brightness(settings: EffectSettings) -> int:
    return min(settings.dial_brightness, settings.master_brightness)


def budgeted_brightness(base_frame: Iterable[Rgb], settings: EffectSettings) -> int:
    frame = tuple(base_frame)
    channel_sum = sum(r + g + b for r, g, b in frame)
    brightness = requested_brightness(settings)
    if channel_sum == 0 or brightness == 0:
        return brightness

    current_times_255 = (
        LED_COUNT * WS2812_IDLE_MA * 255
        + channel_sum * WS2812_CHANNEL_MA * brightness // 255
    )
    budget_times_255 = LED_CURRENT_BUDGET_MA * 255
    if current_times_255 <= budget_times_255:
        return brightness

    scaled = brightness * budget_times_255 // current_times_255
    return max(1, min(brightness, scaled))


def scale_rgb(color: Rgb, brightness: int) -> Rgb:
    brightness = clamp_byte(brightness)
    return tuple(component * brightness // 255 for component in color)  # type: ignore[return-value]


def led_level_at(timing: LedTiming, elapsed_ms: int) -> int:
    if not timing.enabled or elapsed_ms < timing.delay_ms:
        return 0

    local = int(elapsed_ms) - timing.delay_ms
    if timing.fade_in_ms > 0 and local < timing.fade_in_ms:
        return min(255, local * 255 // timing.fade_in_ms)

    local -= timing.fade_in_ms
    if local < timing.hold_ms:
        return 255

    local -= timing.hold_ms
    if timing.fade_out_ms > 0 and local < timing.fade_out_ms:
        return 255 - min(255, local * 255 // timing.fade_out_ms)

    return 0


def effect_cycle_ms(settings: EffectSettings) -> int:
    cycle_ms = 0
    for timing in settings.led:
        if not timing.enabled:
            continue
        end_ms = timing.delay_ms + timing.fade_in_ms + timing.hold_ms + timing.fade_out_ms
        cycle_ms = max(cycle_ms, end_ms)
    return cycle_ms


def preview_base_frame(settings: EffectSettings) -> tuple[Rgb, ...]:
    frame: list[Rgb] = []
    for color, timing in zip(settings.colors, settings.led):
        frame.append(color if timing.enabled else (0, 0, 0))
    return tuple(frame)


def fire_base_frame(settings: EffectSettings, elapsed_ms: int) -> tuple[Rgb, ...]:
    cycle_ms = effect_cycle_ms(settings)
    if cycle_ms == 0:
        return ((0, 0, 0),) * LED_COUNT
    if settings.repeat:
        elapsed_ms %= cycle_ms
    elif elapsed_ms > cycle_ms:
        return ((0, 0, 0),) * LED_COUNT

    frame: list[Rgb] = []
    for color, timing in zip(settings.colors, settings.led):
        level = led_level_at(timing, elapsed_ms)
        frame.append(scale_rgb(color, level) if level else (0, 0, 0))
    return tuple(frame)


def ws2812_base_frame(state: ReceiverState, elapsed_ms: int = 0) -> tuple[Rgb, ...]:
    if state.mode == EffectMode.PREVIEW:
        return preview_base_frame(state.settings)
    if state.mode == EffectMode.FIRE:
        return fire_base_frame(state.settings, elapsed_ms)
    return ((0, 0, 0),) * LED_COUNT


def ws2812_frame_after_budget(state: ReceiverState, elapsed_ms: int = 0) -> tuple[tuple[Rgb, ...], int]:
    base = ws2812_base_frame(state, elapsed_ms)
    brightness = budgeted_brightness(base, state.settings)
    return tuple(scale_rgb(color, brightness) for color in base), brightness


def settings_from_led_payload(payload: bytes, settings: EffectSettings | None = None) -> EffectSettings:
    parsed = parse_led_payload(payload)
    base = settings or EffectSettings()
    return replace(
        base,
        dial_brightness=int(parsed["brightness"]),
        colors=tuple(parsed["colors"]),  # type: ignore[arg-type]
    )


def state_after_accepted_frame(
    frame_type: FrameType,
    payload: bytes = b"",
    state: ReceiverState | None = None,
) -> ReceiverState:
    base = state or ReceiverState()
    frame_type = FrameType(frame_type)

    if frame_type == FrameType.PREVIEW:
        settings = settings_from_led_payload(payload, base.settings)
        return replace(base, settings=settings, mode=EffectMode.PREVIEW, last_status="PREVIEW")
    if frame_type == FrameType.FIRE:
        settings = settings_from_led_payload(payload, base.settings)
        return replace(base, settings=settings, mode=EffectMode.FIRE, last_status="FIRE")
    if frame_type == FrameType.STOP:
        return replace(base, mode=EffectMode.IDLE, last_status="STOP")
    if frame_type in (FrameType.PING, FrameType.STATUS):
        return replace(base, last_status="PING")
    return replace(base, last_status="UNHANDLED")


def state_after_fault(status: str, state: ReceiverState | None = None) -> ReceiverState:
    return replace(state or ReceiverState(), last_status=status)


def field_name(field: UiField) -> str:
    return {
        UiField.LED: "LED",
        UiField.ENABLED: "enabled",
        UiField.DELAY: "delayMs",
        UiField.FADE_IN: "fadeInMs",
        UiField.HOLD: "holdMs",
        UiField.FADE_OUT: "fadeOutMs",
        UiField.REPEAT: "repeat",
        UiField.MASTER_BRIGHTNESS: "masterBrightness",
        UiField.PREVIEW: "preview",
    }[UiField(field)]


def field_value(state: ReceiverState) -> str:
    timing = state.settings.led[state.selected_led]
    field = state.field
    if field == UiField.LED:
        return str(state.selected_led + 1)
    if field == UiField.ENABLED:
        return "on" if timing.enabled else "off"
    if field == UiField.DELAY:
        return f"{timing.delay_ms}ms"
    if field == UiField.FADE_IN:
        return f"{timing.fade_in_ms}ms"
    if field == UiField.HOLD:
        return f"{timing.hold_ms}ms"
    if field == UiField.FADE_OUT:
        return f"{timing.fade_out_ms}ms"
    if field == UiField.REPEAT:
        return "on" if state.settings.repeat else "off"
    if field == UiField.MASTER_BRIGHTNESS:
        return str(state.settings.master_brightness)
    if field == UiField.PREVIEW:
        return "turn"
    raise ValueError(f"unknown field {field!r}")


def timing_line(state: ReceiverState) -> str:
    timing = state.settings.led[state.selected_led]
    return (
        f"L{state.selected_led + 1} "
        f"{'on' if timing.enabled else 'off'} "
        f"D{timing.delay_ms} FI{timing.fade_in_ms} H{timing.hold_ms} FO{timing.fade_out_ms}"
    )


def brightness_line(settings: EffectSettings) -> str:
    return (
        f"Dial {settings.dial_brightness}  "
        f"Master {settings.master_brightness}  "
        f"repeat {'on' if settings.repeat else 'off'}"
    )


def status_display_ops(state: ReceiverState) -> tuple[DisplayText, ...]:
    return (
        DisplayText("title", "Prop RX", 120, 6, COLOR_TEXT, COLOR_PANEL, text_size=2, centered=True),
        DisplayText("port", "Port B G2: 4 WS2812", 8, 34, COLOR_MUTED, COLOR_BG),
        DisplayText("uart", "UART1 115200 G13/G15", 8, 47, COLOR_MUTED, COLOR_BG),
        DisplayText("state_label", "State:", 8, 66, COLOR_GOOD, COLOR_BG),
        DisplayText("state", state.last_status, 56, 66, COLOR_TEXT, COLOR_BG),
        DisplayText("field_label", field_name(state.field), 8, 86, COLOR_WARN, COLOR_BG),
        DisplayText("field_value", field_value(state), 130, 86, COLOR_TEXT, COLOR_BG),
        DisplayText("timing", timing_line(state), 8, 104, COLOR_MUTED, COLOR_BG),
        DisplayText("brightness", brightness_line(state.settings), 8, 118, COLOR_MUTED, COLOR_BG),
        DisplayText("hint", "Short press field, hold exits", 8, 136, COLOR_MUTED, COLOR_BG),
    )


def status_display_lines(state: ReceiverState) -> tuple[str, ...]:
    return (
        "Prop RX",
        "Port B G2: 4 WS2812",
        "UART1 115200 G13/G15",
        f"State: {state.last_status}",
        f"{field_name(state.field)} {field_value(state)}",
        timing_line(state),
        brightness_line(state.settings),
        "Short press field, hold exits",
    )


def render_frame(state: ReceiverState | None = None, elapsed_ms: int = 0) -> RenderedFrame:
    state = state or ReceiverState()
    base = ws2812_base_frame(state, elapsed_ms)
    brightness = budgeted_brightness(base, state.settings)
    ws2812 = tuple(scale_rgb(color, brightness) for color in base)
    return RenderedFrame(
        state=state,
        base_frame=base,
        budgeted_brightness=brightness,
        ws2812_frame=ws2812,
        display_ops=status_display_ops(state),
        display_lines=status_display_lines(state),
    )


def scenes() -> dict[str, tuple[ReceiverState, int]]:
    from shared.protocol.protocol import encode_led_payload

    colors = [(255, 30, 30), (30, 220, 90), (40, 120, 255), (255, 180, 0)]
    payload = encode_led_payload(150, colors)
    return {
        "01_idle_ready": (ReceiverState(), 0),
        "02_accepted_preview": (state_after_accepted_frame(FrameType.PREVIEW, payload), 0),
        "03_accepted_fire_200ms": (state_after_accepted_frame(FrameType.FIRE, payload), 200),
        "04_accepted_stop": (state_after_accepted_frame(FrameType.STOP), 0),
        "05_fault_bad_mac": (state_after_fault("BAD MAC"), 0),
        "06_fault_bad_payload": (state_after_fault("BAD PAYLOAD"), 0),
    }


def main() -> None:
    for name, (state, elapsed_ms) in scenes().items():
        frame = render_frame(state, elapsed_ms)
        print(
            f"{name}: brightness={frame.budgeted_brightness} "
            f"active={frame.active_led_count} leds={frame.ws2812_frame} "
            f"display={frame.display_lines}"
        )


if __name__ == "__main__":
    try:
        main()
    except ProtocolError as exc:
        raise SystemExit(str(exc)) from exc
