from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import encode_led_payload, parse_led_payload  # noqa: E402
from tools import preview_prop_tx as gui  # noqa: E402


GUI_CPP = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp"
GUI_THEME_H = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/ui_theme_dial_generated.h"
APP_CPP = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"

SAFE_CENTER = (120.0, 120.0)
SAFE_RADIUS = 120.0
BASE_COLOR_NAMES = (
    "BG_BASE",
    "RING_TRK",
    "SOCKET",
    "TEXT_HI",
    "TEXT_DIM",
    "P_GREEN",
    "P_AMBER",
    "P_RED",
    "ACCENT",
    "WHITE",
)


def _fixture_colors() -> list[tuple[int, int, int]]:
    payload = encode_led_payload(
        brightness=150,
        colors=[(255, 30, 30), (30, 220, 90), (40, 120, 255), (255, 180, 0)],
    )
    return parse_led_payload(payload)["colors"]


def real_state_views() -> dict[str, gui.View]:
    colors = _fixture_colors()
    return {
        "idle_action_preview": gui.View(
            action_label="PREVIEW",
            field_label="akce",
            status="ready",
            field_value="PREVIEW",
            colors=colors,
        ),
        "idle_action_arm": gui.View(
            action_label="ARM", field_label="akce", status="ready", field_value="ARM", colors=colors
        ),
        "idle_action_fire": gui.View(
            action_label="ODPAL",
            field_label="akce",
            status="ready",
            field_value="ODPAL",
            colors=colors,
        ),
        "armed_fire": gui.View(
            action_label="ODPAL",
            field_label="akce",
            status="ARM ready",
            field_value="ODPAL",
            armed=True,
            colors=colors,
        ),
        "idle_action_stop": gui.View(
            action_label="STOP",
            field_label="akce",
            status="ready",
            field_value="STOP",
            colors=colors,
        ),
        "waiting_for_contact": gui.View(
            action_label="ODPAL",
            field_label="akce",
            status="sent FIRE wait",
            field_value="ODPAL",
            awaiting_ack=True,
            colors=colors,
        ),
        "ack_contact": gui.View(
            action_label="PREVIEW",
            field_label="akce",
            status="ACK 42",
            field_value="PREVIEW",
            colors=colors,
        ),
        "fault_no_ack": gui.View(
            action_label="PING",
            field_label="akce",
            status="no ack",
            field_value="PING",
            colors=colors,
        ),
        "fault_error": gui.View(
            action_label="PING",
            field_label="akce",
            status="ERR BAD_FRAME",
            field_value="PING",
            colors=colors,
        ),
        "brightness_zero": gui.View(
            field_label="jas", status="ready", field_value="0%", brightness_percent=0, colors=colors
        ),
        "brightness_min_visible": gui.View(
            field_label="jas", status="ready", field_value="1%", brightness_percent=1, colors=colors
        ),
        "brightness_full": gui.View(
            field_label="jas",
            status="ready",
            field_value="100%",
            brightness_percent=100,
            colors=colors,
        ),
        "led_select": gui.View(
            field_label="LED",
            status="LED 3 BARVA",
            field_value="3",
            selected_led=2,
            selected_hue_degrees=240,
            colors=colors,
        ),
        "hue_min": gui.View(
            field_label="HUE",
            status="ready",
            field_value="0deg",
            selected_led=0,
            selected_hue_degrees=0,
            colors=colors,
        ),
        "hue_max": gui.View(
            field_label="HUE",
            status="ready",
            field_value="359deg",
            selected_led=3,
            selected_hue_degrees=359,
            brightness_percent=80,
            colors=colors,
        ),
        "palette_count_one": gui.View(
            field_label="BARVY",
            status="1 barva",
            field_value="1",
            palette_count=1,
            selected_led=0,
            colors=colors,
        ),
    }


def ops(frame: gui.RenderedFrame, role: str) -> list[gui.DrawOp]:
    return [op for op in frame.ops if op.role == role]


def one(frame: gui.RenderedFrame, role: str) -> gui.DrawOp:
    matches = ops(frame, role)
    assert len(matches) == 1, f"expected exactly one {role}, got {len(matches)}"
    return matches[0]


def circle_point(angle: float, radius: float) -> tuple[float, float]:
    radians = math.radians(angle)
    return (120.0 + radius * math.cos(radians), 120.0 + radius * math.sin(radians))


def firmware_int_circle_point(angle: float, radius: float) -> tuple[float, float]:
    x, y = circle_point(angle, radius)
    return (float(int(x)), float(int(y)))


def distance_from_safe_center(x: float, y: float) -> float:
    return math.hypot(x - SAFE_CENTER[0], y - SAFE_CENTER[1])


def assert_bbox_inside_canvas(op: gui.DrawOp) -> None:
    if op.bbox is None:
        return
    left, top, right, bottom = op.bbox
    assert left >= -0.01, op
    assert top >= -0.01, op
    assert right <= gui.SIZE + 0.01, op
    assert bottom <= gui.SIZE + 0.01, op


def assert_bbox_inside_round_safe_area(op: gui.DrawOp) -> None:
    assert op.bbox is not None, op
    left, top, right, bottom = op.bbox
    for x, y in ((left, top), (right, top), (left, bottom), (right, bottom)):
        assert distance_from_safe_center(x, y) <= SAFE_RADIUS + 0.01, op


def assert_rects_disjoint(a: gui.DrawOp, b: gui.DrawOp) -> None:
    assert a.bbox is not None and b.bbox is not None
    al, at, ar, ab = a.bbox
    bl, bt, br, bb = b.bbox
    assert ar <= bl or br <= al or ab <= bt or bb <= at, (a, b)


def expected_palette_for(view: gui.View) -> set[int]:
    sc = gui.state_color(view)
    palette = {getattr(gui, name) for name in BASE_COLOR_NAMES}
    palette.add(0x0E1116)
    palette.add(gui.MODE_SETUP)  # SETUP mode caption + selection accent
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.42))
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.85))
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.92))
    bg_tint = (
        0.25
        if (view.status or "").startswith("ACK ")
        else (0.10 if gui.is_command_mode(view) else 0.06)
    )
    bg_src = sc if gui.is_command_mode(view) else gui.MODE_SETUP
    palette.add(gui.P_RED if view.armed else gui.mix(gui.BG_BASE, bg_src, bg_tint))
    palette.add(gui.mix(gui.BG_BASE, gui.MODE_SETUP, 0.26))
    palette.add(gui.mix(gui.BG_BASE, sc, 0.35))
    setup_orb_color = gui.setup_orb_color(view)
    for color in [gui.led_rgb(view, i) for i in range(4)]:
        palette.update(
            {
                color,
                gui.on_color(color),
                gui.mix(gui.BG_BASE, color, 0.18),
                gui.mix(gui.BG_BASE, color, 0.30),
                gui.mix(gui.BG_BASE, color, 0.34),
                gui.mix(color, gui.WHITE, 0.09),  # orb emissive core (outer)
                gui.mix(color, gui.WHITE, 0.16),  # orb emissive core (inner)
                gui.mix(color, gui.WHITE, 0.22),
                gui.mix(color, gui.BG_BASE, 0.30),
                gui.mix(color, gui.BG_BASE, 0.62),
            }
        )
    palette.update(
        {
            setup_orb_color,
            gui.on_color(setup_orb_color),
            gui.mix(gui.BG_BASE, setup_orb_color, 0.18),
            gui.mix(gui.BG_BASE, setup_orb_color, 0.34),
            gui.mix(setup_orb_color, gui.WHITE, 0.09),
            gui.mix(setup_orb_color, gui.WHITE, 0.16),
            gui.mix(setup_orb_color, gui.WHITE, 0.22),
        }
    )
    palette.add(gui.mix(gui.BG_BASE, gui.WHITE, 0.12))
    return palette


@pytest.mark.parametrize("name,view", real_state_views().items())
def test_real_prop_tx_states_render_raw_240_canvas_with_required_elements(
    name: str, view: gui.View
) -> None:
    frame = gui.render_frame(view)

    assert frame.image.size == (240, 240)
    if view.armed:
        assert one(frame, "screen").color == gui.P_RED
        assert one(frame, "armed_outer_ring").color == gui.WHITE
        assert one(frame, "armed_pulse_ring").color == gui.mix(gui.P_RED, gui.WHITE, 0.42)
        assert one(frame, "armed_state_text").text == "ARMED"
        assert one(frame, "armed_live_text").text == "READY"
        assert one(frame, "armed_fire_text").text == "ODPAL"
        assert len(ops(frame, "armed_chip")) == 4
        assert not ops(frame, "brightness_track")
        assert not ops(frame, "mode_caption")
        assert not ops(frame, "led_socket")
        return

    sc = gui.state_color(view)
    ack = (view.status or "").startswith("ACK ")
    bg_tint = 0.25 if ack else (0.10 if gui.is_command_mode(view) else 0.06)
    bg_src = sc if gui.is_command_mode(view) else gui.MODE_SETUP
    assert one(frame, "screen").color == gui.mix(gui.BG_BASE, bg_src, bg_tint)
    assert one(frame, "brightness_track")
    assert one(frame, "mode_caption").text == (
        "PRIKAZ" if gui.is_command_mode(view) else "NASTAVENI"
    )
    assert not ops(frame, "status_text")
    slot_count = max(1, min(8, view.palette_count))
    assert len(ops(frame, "led_socket")) == slot_count
    assert len(ops(frame, "led_lens")) == slot_count

    if gui.is_command_mode(view):
        assert len(ops(frame, "command_ring")) == 4
        assert {op.color for op in ops(frame, "command_ring")} == {gui.state_color(view)}
        assert not ops(frame, "orb_lens")
        assert len(ops(frame, "led_selection")) == 1
        if view.awaiting_ack:
            assert one(frame, "wait_track")
            assert one(frame, "wait_sweep").color == gui.state_color(view)
            assert one(frame, "command_state_text").text == "WAIT"
            assert one(frame, "command_state_subtext").text == "ACK"
            assert not ops(frame, "command_text")
        elif ack:
            assert one(frame, "command_state_text").text == "ACK"
            assert not ops(frame, "command_text")
        elif (view.status or "") in ("no ack", "timeout"):
            assert one(frame, "command_state_text").text == "NO ACK"
            assert not ops(frame, "command_text")
        else:
            assert one(frame, "command_text").text == view.action_label
            if view.action_label == "ODPAL":
                assert one(frame, "fire_locked_text").text == "LOCK"
                assert {op.color for op in ops(frame, "command_ring")} == {gui.P_AMBER}
    else:
        expected_orb = gui.setup_orb_color(view)
        assert one(frame, "orb_lens").color == expected_orb
        assert one(frame, "orb_selection").color == gui.MODE_SETUP
        assert one(frame, "orb_text").text in {
            str(view.selected_led + 1),
            f"{view.brightness_percent}%",
            f"{view.selected_hue_degrees}\N{DEGREE SIGN}",
        }
        assert len(ops(frame, "led_selection")) == 1
        assert len(ops(frame, "setup_grid")) > 0
        assert not ops(frame, "command_ring")


@pytest.mark.parametrize("name,view", real_state_views().items())
def test_draws_stay_inside_canvas_and_round_safe_area(name: str, view: gui.View) -> None:
    frame = gui.render_frame(view)

    for op in frame.ops:
        assert_bbox_inside_canvas(op)
        if op.role in {"screen", "setup_grid"}:
            continue
        if op.kind in {"circle", "ring"}:
            assert op.center is not None and op.outer_radius is not None
            assert distance_from_safe_center(*op.center) + op.outer_radius <= SAFE_RADIUS + 0.01, op
        elif op.kind == "line":
            assert op.points is not None and op.width is not None
            for x, y in op.points:
                assert distance_from_safe_center(x, y) + op.width / 2 <= SAFE_RADIUS + 0.01, op
        elif op.kind == "text":
            assert_bbox_inside_round_safe_area(op)


@pytest.mark.parametrize("name,view", real_state_views().items())
def test_render_uses_only_declared_palette_and_deterministic_led_colors(
    name: str, view: gui.View
) -> None:
    frame = gui.render_frame(view)
    allowed = expected_palette_for(view)
    unexpected = [
        (op.role, op.color) for op in frame.ops if op.color is not None and op.color not in allowed
    ]
    assert unexpected == []


@pytest.mark.parametrize(
    "brightness,expected_sweep,expect_indicator",
    [
        (0, 0.0, False),
        (1, 8.0, True),
        (59, 207.68, True),
        (100, 352.0, True),
        (255, 352.0, True),
    ],
)
def test_brightness_arc_angle_matches_encoded_percent(
    brightness: int, expected_sweep: float, expect_indicator: bool
) -> None:
    view = gui.View(field_label="jas", brightness_percent=brightness, colors=_fixture_colors())
    frame = gui.render_frame(view)
    indicators = ops(frame, "brightness_value")

    if not expect_indicator:
        assert indicators == []
        assert ops(frame, "brightness_cap") == []
        return

    indicator = one(frame, "brightness_value")
    assert indicator.angles == pytest.approx((gui.TOP, gui.TOP + expected_sweep), abs=0.01)

    caps = ops(frame, "brightness_cap")
    assert len(caps) == 2
    for cap, angle in zip(caps, indicator.angles):
        assert cap.center == pytest.approx(firmware_int_circle_point(angle, gui.RING_CAP), abs=0.01)


def test_led_arc_uses_lovyangfx_clockwise_angle_convention() -> None:
    view = gui.View(field_label="LED", selected_led=2, colors=_fixture_colors())
    frame = gui.render_frame(view)
    lenses = sorted(ops(frame, "led_lens"), key=lambda op: op.index)

    for index, (lens, angle) in enumerate(zip(lenses, gui.LED_ANGLES)):
        assert lens.center == pytest.approx(circle_point(angle, gui.LED_R), abs=0.75)
        assert lens.index == index

    assert lenses[0].center[0] < lenses[1].center[0] < lenses[2].center[0] < lenses[3].center[0]
    assert lenses[0].center[1] < lenses[1].center[1]
    assert lenses[3].center[1] < lenses[2].center[1]


@pytest.mark.parametrize("name,view", real_state_views().items())
def test_critical_text_does_not_overlap_leds_or_centerpiece(name: str, view: gui.View) -> None:
    frame = gui.render_frame(view)
    text_roles = (
        ["armed_state_text", "armed_live_text", "armed_fire_text"]
        if view.armed
        else ["mode_caption"]
    )
    if not view.armed:
        text_roles.append(
            "command_text"
            if gui.is_command_mode(view) and ops(frame, "command_text")
            else "orb_text"
        )

    text_ops = [one(frame, role) for role in text_roles if ops(frame, role)]
    for first, second in zip(text_ops, text_ops[1:]):
        assert_rects_disjoint(first, second)

    for text in text_ops:
        for led in ops(frame, "led_socket"):
            assert_rects_disjoint(text, led)

    centrepieces = [] if gui.is_command_mode(view) else ops(frame, "orb_selection")
    for centrepiece in centrepieces:
        for led in ops(frame, "led_socket"):
            assert_rects_disjoint(centrepiece, led)


def _cpp_int_constant(text: str, name: str) -> int:
    match = re.search(rf"{name}\s*=\s*(\d+)", text)
    assert match, f"{name} not found"
    return int(match.group(1))


def _cpp_hex_constant(text: str, name: str) -> int:
    match = re.search(rf"{name}\s*=\s*0x([0-9A-Fa-f]+)", text)
    assert match, f"{name} not found"
    return int(match.group(1), 16)


def test_preview_constants_match_firmware_gui_source() -> None:
    # Theme colours (BG_BASE/SEL_ACCENT/COL_WHITE/...) now live in the generated theme header;
    # the geometry (CX/RING_OUT/...) stays in gui_prop_tx.cpp. Cross-check against both.
    cpp = GUI_CPP.read_text(encoding="utf-8") + "\n" + GUI_THEME_H.read_text(encoding="utf-8")

    for name in (
        "BG_BASE",
        "RING_TRK",
        "SOCKET",
        "TEXT_HI",
        "TEXT_DIM",
        "P_GREEN",
        "P_AMBER",
        "P_RED",
    ):
        assert getattr(gui, name) == _cpp_hex_constant(cpp, name)
    assert gui.ACCENT == _cpp_hex_constant(cpp, "SEL_ACCENT")
    assert gui.WHITE == _cpp_hex_constant(cpp, "COL_WHITE")

    assert gui.SIZE == _cpp_int_constant(cpp, "CX") * 2
    for name in ("RING_OUT", "RING_IN", "RING_CAP", "ORB_R", "LED_R"):
        assert getattr(gui, name) == _cpp_int_constant(cpp, name)

    angle_match = re.search(r"LED_ANGLES\[4\]\s*=\s*\{([^}]+)\}", cpp)
    assert angle_match
    cpp_angles = [float(item.replace("f", "")) for item in angle_match.group(1).split(",")]
    assert gui.LED_ANGLES == cpp_angles

    header = (ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.h").read_text(
        encoding="utf-8"
    )
    # View::colors initializer spans multiple lines: `colors = {{ {r,g,b}, ... }};`
    init = re.search(r"colors\s*=\s*\{\{(.+?)\}\}\s*;", header, re.DOTALL)
    assert init, "View::colors initializer not found in gui_prop_tx.h"
    default_colors = [
        tuple(map(int, triplet))
        for triplet in re.findall(r"\{(\d+),\s*(\d+),\s*(\d+)\}", init.group(1))
    ]
    assert gui.View().colors == default_colors


def test_simulation_states_cover_app_actions_fields_statuses_and_protocol_led_payload() -> None:
    app = APP_CPP.read_text(encoding="utf-8")
    views = real_state_views()

    for action in ("PREVIEW", "ARM", "FIRE", "STOP", "PING"):
        assert f"ACTION_{action}" in app
        assert any(
            view.action_label == ("ODPAL" if action == "FIRE" else action)
            for view in views.values()
        )

    assert {view.field_label for view in views.values()} >= {"akce", "jas", "LED", "HUE", "BARVY"}
    assert {"ready", "ARM ready", "sent FIRE wait", "ACK 42", "no ack", "ERR BAD_FRAME"} <= {
        view.status for view in views.values()
    }

    payload = encode_led_payload(150, _fixture_colors())
    assert len(payload) == 13
    assert parse_led_payload(payload)["colors"] == _fixture_colors()
