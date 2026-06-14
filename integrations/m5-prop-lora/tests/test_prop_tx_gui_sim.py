from __future__ import annotations

import math
import re
import sys
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import encode_led_payload, parse_led_payload  # noqa: E402

_PREVIEW_SPEC = importlib.util.spec_from_file_location(
    "m5_preview_prop_tx", ROOT / "tools" / "preview_prop_tx.py"
)
assert _PREVIEW_SPEC is not None and _PREVIEW_SPEC.loader is not None
gui = importlib.util.module_from_spec(_PREVIEW_SPEC)
sys.modules[_PREVIEW_SPEC.name] = gui
_PREVIEW_SPEC.loader.exec_module(gui)


GUI_CPP = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/gui_prop_tx.cpp"
GUI_THEME_H = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/ui_theme_dial_generated.h"
APP_CPP = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"
ESPOS_ROOT = ROOT.parents[1]

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

COLOR_ANCHORS = {
    "BG_BASE": 0x14171D,
    "P_GREEN": 0x3FB36B,
    "P_AMBER": 0xFF8C00,
    "P_RED": 0xCC0000,
    "TEXT_HI": 0xE7E9ED,
    "TEXT_DIM": 0x767D89,
    "MODE_SETUP": 0x59C6DC,
    "WHITE": 0xFFFFFF,
    "mix_BG_AMBER_010": 0x2B221A,
    "mix_BG_AMBER_025": 0x4E3415,
    "mix_AMBER_BG_042": 0x9C5A0C,
    "mix_MODE_WHITE_018": 0x76D0E2,
    "mix_TEXTDIM_BG_035": 0x535963,
    "mix_RED_WHITE_042": 0xE16B6B,
    "mix_BG_WHITE_012": 0x303238,
}


_VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "espos_validate_design", ESPOS_ROOT / "tools" / "validate_design.py"
)
assert _VALIDATE_SPEC is not None and _VALIDATE_SPEC.loader is not None
_validate_design = importlib.util.module_from_spec(_VALIDATE_SPEC)
sys.modules[_VALIDATE_SPEC.name] = _validate_design
_VALIDATE_SPEC.loader.exec_module(_validate_design)


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


def test_dial_today_preview_has_no_setup_editor_scenes() -> None:
    scenes = gui.scenes()
    forbidden_name_fragments = ("edit", "palette")

    assert all(
        fragment not in name
        for name in scenes
        for fragment in forbidden_name_fragments
    )
    for name, view in scenes.items():
        assert view.armed or gui.is_command_mode(view), name
        assert (view.field_label or "").startswith("akce"), name
        assert view.action_label not in {"LED3", "LED5"}, name
        assert view.field_value not in {"LED3", "LED5"}, name
        assert not gui.is_palette_count(view), name

        frame = gui.render_frame(view)
        assert not ops(frame, "setup_grid"), name
        assert not ops(frame, "orb_lens"), name
        assert not ops(frame, "orb_subtext"), name
        assert not ops(frame, "led_leader"), name


def test_preview_writer_removes_stale_setup_editor_pngs(tmp_path, monkeypatch) -> None:
    fake_tool = tmp_path / "tools" / "preview_prop_tx.py"
    fake_tool.parent.mkdir(parents=True)
    out = tmp_path / "build" / "preview"
    out.mkdir(parents=True)
    stale = out / "07_edit_jas.png"
    stale.write_bytes(b"stale")

    monkeypatch.setattr(gui, "__file__", str(fake_tool))

    gui.main()

    assert not stale.exists()
    assert (out / "07_stop.png").is_file()


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


def assert_bbox_contains(container: gui.DrawOp, child: gui.DrawOp, pad: float = 0.0) -> None:
    assert container.bbox is not None and child.bbox is not None
    cl, ct, cr, cb = container.bbox
    il, it, ir, ib = child.bbox
    assert cl + pad <= il and ct + pad <= it and ir <= cr - pad and ib <= cb - pad, (
        container,
        child,
    )


def bbox_height(op: gui.DrawOp) -> float:
    assert op.bbox is not None
    return op.bbox[3] - op.bbox[1]


def bbox_width(op: gui.DrawOp) -> float:
    assert op.bbox is not None
    return op.bbox[2] - op.bbox[0]


def assert_horizontal_breathing_room(op: gui.DrawOp, left: float, right: float) -> None:
    assert op.bbox is not None
    actual_left, _, actual_right, _ = op.bbox
    assert actual_left >= left and actual_right <= right, op


def _int_bbox(op: gui.DrawOp, *, pad: int = 0) -> tuple[int, int, int, int]:
    assert op.bbox is not None
    left, top, right, bottom = op.bbox
    x = math.floor(left) - pad
    y = math.floor(top) - pad
    width = math.ceil(right) - math.floor(left) + pad * 2
    height = math.ceil(bottom) - math.floor(top) + pad * 2
    return x, y, width, height


def _m5_frame_as_espos_design(name: str, frame: gui.RenderedFrame) -> dict:
    widgets = []
    for index, op in enumerate(frame.ops):
        if op.bbox is None or op.role in {"screen", "setup_grid"}:
            continue
        if op.kind == "text":
            x, y, width, height = _int_bbox(op, pad=2)
            widgets.append(
                {
                    "type": "label",
                    "_widget_id": f"{op.role}_{index}",
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": max(12, height),
                    "text": op.text or "",
                    "color_fg": "#FFFFFF",
                    "color_bg": "#000000",
                }
            )
        elif op.kind == "rect":
            x, y, width, height = _int_bbox(op)
            widgets.append(
                {
                    "type": "panel",
                    "_widget_id": f"{op.role}_{index}",
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "visible": True,
                }
            )
    return {
        "scenes": {
            name: {
                "width": gui.SIZE,
                "height": gui.SIZE,
                "display_shape": "round",
                "round_safe_margin": 8,
                "widgets": widgets,
            }
        }
    }


def expected_palette_for(view: gui.View) -> set[int]:
    sc = gui.state_color(view)
    palette = {getattr(gui, name) for name in BASE_COLOR_NAMES}
    palette.add(0x0E1116)
    palette.add(gui.MODE_SETUP)  # SETUP mode caption + selection accent
    palette.add(gui.setup_caption_color())
    palette.add(gui.mix(gui.MODE_SETUP, gui.WHITE, 0.16))
    palette.add(gui.mix(gui.P_AMBER, gui.WHITE, 0.10))
    palette.add(gui.mix(gui.P_AMBER, gui.WHITE, 0.82))
    palette.add(gui.mix(gui.P_AMBER, gui.WHITE, 0.86))
    palette.add(gui.mix(gui.P_AMBER, gui.WHITE, 0.88))
    palette.add(gui.mix(gui.P_AMBER, gui.BG_BASE, 0.35))
    palette.add(gui.mix(gui.BG_BASE, gui.P_AMBER, 0.18))
    palette.add(gui.mix(gui.P_AMBER, gui.BG_BASE, 0.42))
    palette.add(gui.mix(gui.TEXT_DIM, gui.BG_BASE, 0.35))
    palette.add(gui.mix(gui.TEXT_DIM, gui.BG_BASE, 0.62))
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.42))
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.85))
    palette.add(gui.mix(gui.P_RED, gui.WHITE, 0.92))
    palette.add(gui.mix(gui.P_RED, gui.BG_BASE, 0.18))
    palette.add(gui.mix(gui.P_RED, gui.BG_BASE, 0.32))
    bg_tint = (
        0.25
        if (view.status or "").startswith("ACK ")
        else (0.10 if gui.is_command_mode(view) else 0.06)
    )
    bg_src = sc if gui.is_command_mode(view) else gui.MODE_SETUP
    palette.add(gui.P_RED if view.armed else gui.mix(gui.BG_BASE, bg_src, bg_tint))
    palette.add(gui.mix(gui.BG_BASE, gui.MODE_SETUP, 0.26))
    palette.add(gui.mix(gui.BG_BASE, sc, 0.18))
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


def test_palette_color_math_has_literal_anchors() -> None:
    assert gui.BG_BASE == COLOR_ANCHORS["BG_BASE"]
    assert gui.P_GREEN == COLOR_ANCHORS["P_GREEN"]
    assert gui.P_AMBER == COLOR_ANCHORS["P_AMBER"]
    assert gui.P_RED == COLOR_ANCHORS["P_RED"]
    assert gui.TEXT_HI == COLOR_ANCHORS["TEXT_HI"]
    assert gui.TEXT_DIM == COLOR_ANCHORS["TEXT_DIM"]
    assert gui.MODE_SETUP == COLOR_ANCHORS["MODE_SETUP"]
    assert gui.WHITE == COLOR_ANCHORS["WHITE"]

    assert gui.mix(gui.BG_BASE, gui.P_AMBER, 0.10) == COLOR_ANCHORS["mix_BG_AMBER_010"]
    assert gui.mix(gui.BG_BASE, gui.P_AMBER, 0.25) == COLOR_ANCHORS["mix_BG_AMBER_025"]
    assert gui.mix(gui.P_AMBER, gui.BG_BASE, 0.42) == COLOR_ANCHORS["mix_AMBER_BG_042"]
    assert gui.mix(gui.MODE_SETUP, gui.WHITE, 0.18) == COLOR_ANCHORS["mix_MODE_WHITE_018"]
    assert gui.mix(gui.TEXT_DIM, gui.BG_BASE, 0.35) == COLOR_ANCHORS["mix_TEXTDIM_BG_035"]
    assert gui.mix(gui.P_RED, gui.WHITE, 0.42) == COLOR_ANCHORS["mix_RED_WHITE_042"]
    assert gui.mix(gui.BG_BASE, gui.WHITE, 0.12) == COLOR_ANCHORS["mix_BG_WHITE_012"]

    assert gui.state_color(gui.scenes()["01_ready_action"]) == gui.TEXT_DIM
    assert gui.state_color(gui.scenes()["04_wait_ack"]) == gui.P_AMBER
    assert gui.state_color(gui.scenes()["06_no_ack"]) == gui.P_AMBER
    assert gui.state_color(gui.scenes()["03_armed"]) == gui.P_RED


@pytest.mark.parametrize("name,view", real_state_views().items())
def test_real_prop_tx_states_render_raw_240_canvas_with_required_elements(
    name: str, view: gui.View
) -> None:
    frame = gui.render_frame(view)

    assert frame.image.size == (240, 240)
    if view.armed:
        assert one(frame, "screen").color == gui.BG_BASE
        assert not ops(frame, "armed_outer_ring")
        assert not ops(frame, "armed_pulse_ring")
        assert not ops(frame, "armed_danger_text")
        assert one(frame, "armed_live_plate").color == gui.P_RED
        assert one(frame, "armed_cancel_plate").color == gui.TEXT_HI
        assert one(frame, "armed_state_text").text == "ARMED"
        assert bbox_height(one(frame, "armed_state_text")) >= 26.0
        assert_bbox_contains(
            one(frame, "armed_live_plate"), one(frame, "armed_state_text"), pad=3.0
        )
        assert not ops(frame, "armed_live_text")
        assert not ops(frame, "armed_fire_text")
        assert one(frame, "armed_cancel_prompt_text").text == "PRESS"
        assert one(frame, "armed_cancel_text").text == "STOP"
        assert one(frame, "armed_cancel_subtext").text == "TO DISARM"
        assert bbox_height(one(frame, "armed_cancel_prompt_text")) >= 18.0
        assert bbox_height(one(frame, "armed_cancel_text")) >= 34.0
        assert bbox_height(one(frame, "armed_cancel_subtext")) >= 13.0
        assert_bbox_contains(
            one(frame, "armed_cancel_plate"), one(frame, "armed_cancel_prompt_text"), pad=4.0
        )
        assert_bbox_contains(
            one(frame, "armed_cancel_plate"), one(frame, "armed_cancel_text"), pad=4.0
        )
        assert_bbox_contains(
            one(frame, "armed_cancel_plate"), one(frame, "armed_cancel_subtext"), pad=4.0
        )
        assert not ops(frame, "armed_chip")
        assert not ops(frame, "armed_chip_rim")
        assert not ops(frame, "armed_chip_label")
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
        "PŘÍKAZ" if gui.is_command_mode(view) else "NASTAVENÍ"
    )
    assert not ops(frame, "status_text")
    slot_count = max(1, min(8, view.palette_count))
    transient_command_state = gui.is_command_mode(view) and (
        view.awaiting_ack or ack or (view.status or "") in ("no ack", "timeout")
    )
    expected_slots = 0 if transient_command_state else slot_count
    assert len(ops(frame, "led_socket")) == expected_slots
    assert len(ops(frame, "led_lens")) == expected_slots

    if gui.is_command_mode(view):
        assert len(ops(frame, "command_ring")) == 4
        assert {op.color for op in ops(frame, "command_ring")} == {gui.state_color(view)}
        assert not ops(frame, "orb_lens")
        assert len(ops(frame, "led_selection")) == (0 if transient_command_state else 1)
        if view.awaiting_ack:
            assert gui.state_color(view) == gui.P_AMBER
            assert one(frame, "wait_track")
            assert one(frame, "wait_sweep").color == gui.state_color(view)
            assert one(frame, "command_sent_text").text == "TX SENT"
            assert one(frame, "command_state_text").text == "WAIT ACK"
            assert one(frame, "command_state_badge").color == gui.mix(
                gui.P_AMBER, gui.BG_BASE, 0.42
            )
            assert one(frame, "command_safe_text").text == "DO NOT PRESS"
            assert not ops(frame, "command_safe_badge")
            assert bbox_height(one(frame, "command_safe_text")) >= 13.0
            assert bbox_height(one(frame, "command_state_text")) >= 22.0
            assert_bbox_contains(
                one(frame, "command_state_badge"), one(frame, "command_state_text"), pad=4.0
            )
            assert_bbox_contains(
                one(frame, "command_state_badge"), one(frame, "command_safe_text"), pad=8.0
            )
            assert "FIRE" not in {op.text for op in frame.ops if op.text}
            assert not ops(frame, "command_text")
            assert not [op for op in frame.ops if op.color == gui.P_RED]
        elif ack:
            assert len(ops(frame, "ack_check")) == 1
            assert len(ops(frame, "ack_check_highlight")) == 1
            assert not ops(frame, "command_state_text")
            assert not ops(frame, "command_ack_badge")
            assert not ops(frame, "command_text")
            assert not ops(frame, "command_chevron")
        elif (view.status or "") in ("no ack", "timeout"):
            assert one(frame, "command_state_text").text == "NO ACK"
            assert one(frame, "command_state_text").color == gui.TEXT_HI
            assert one(frame, "command_state_badge").color == gui.mix(
                gui.P_AMBER, gui.BG_BASE, 0.42
            )
            assert one(frame, "command_safe_text").text == "CHECK LINK"
            assert bbox_height(one(frame, "command_safe_text")) >= 14.0
            assert_bbox_contains(
                one(frame, "command_state_badge"), one(frame, "command_safe_text"), pad=4.0
            )
            assert not ops(frame, "command_chevron")
            assert not ops(frame, "no_ack_x")
            assert bbox_width(one(frame, "command_state_badge")) >= 132.0
            assert_bbox_contains(
                one(frame, "command_state_badge"), one(frame, "command_state_text"), pad=5.0
            )
            assert not ops(frame, "command_text")
        else:
            expected_command_text = (
                "FIRE LOCKED"
                if view.action_label == "ODPAL"
                else ("NO FIRE" if view.action_label == "PREVIEW" else view.action_label)
            )
            assert one(frame, "command_text").text == expected_command_text
            if view.action_label == "PREVIEW":
                assert gui.state_color(view) == gui.TEXT_DIM
                assert {op.color for op in ops(frame, "command_ring")} == {gui.TEXT_DIM}
                assert one(frame, "command_preview_badge").text == "OUTPUT OFF"
                assert bbox_height(one(frame, "command_text")) >= 28.0
                assert_horizontal_breathing_room(one(frame, "command_text"), left=30.0, right=210.0)
                assert bbox_height(one(frame, "command_preview_badge")) >= 15.0
                assert bbox_width(one(frame, "command_preview_badge_plate")) >= 168.0
                assert_bbox_contains(
                    one(frame, "command_preview_badge_plate"),
                    one(frame, "command_preview_badge"),
                    pad=4.0,
                )
                assert not ops(frame, "command_chevron")
            if view.action_label == "ODPAL":
                assert gui.state_color(view) == gui.TEXT_DIM
                assert one(frame, "fire_locked_badge").color == gui.TEXT_DIM
                assert one(frame, "fire_locked_text").text == "ARM REQUIRED"
                assert bbox_height(one(frame, "command_text")) >= 18.0
                assert bbox_height(one(frame, "fire_locked_text")) >= 15.0
                assert bbox_width(one(frame, "fire_locked_badge")) >= 168.0
                assert_bbox_contains(
                    one(frame, "fire_locked_badge"), one(frame, "fire_locked_text"), pad=4.0
                )
                assert {op.color for op in ops(frame, "command_ring")} == {gui.TEXT_DIM}
                assert not ops(frame, "command_chevron")
            if view.action_label == "STOP":
                assert gui.state_color(view) == gui.TEXT_DIM
                assert one(frame, "command_stop_badge").text == "OUTPUT OFF"
                assert bbox_height(one(frame, "command_stop_badge")) >= 15.0
                assert_bbox_contains(
                    one(frame, "command_stop_badge_plate"),
                    one(frame, "command_stop_badge"),
                    pad=4.0,
                )
                assert {op.color for op in ops(frame, "command_ring")} == {gui.TEXT_DIM}
                assert not ops(frame, "command_chevron")
    else:
        expected_orb = gui.setup_orb_color(view)
        assert one(frame, "orb_lens").color == expected_orb
        assert one(frame, "orb_selection").color == gui.MODE_SETUP
        assert one(frame, "orb_text").text in {
            str(view.selected_led + 1),
            f"{view.brightness_percent}%",
            f"{view.selected_hue_degrees}\N{DEGREE SIGN}",
        }
        if gui.is_palette_count(view):
            assert one(frame, "orb_text").text == str(view.palette_count)
        assert one(frame, "orb_subtext").text == gui.field_caption(view)
        assert bbox_height(one(frame, "orb_subtext")) >= 9.0
        assert_bbox_contains(one(frame, "orb_lens"), one(frame, "orb_subtext"), pad=2.0)
        assert len(ops(frame, "led_selection")) == 1
        assert {op.color for op in ops(frame, "led_selection")} == {gui.ACCENT}
        assert len(ops(frame, "setup_grid")) > 0
        assert not ops(frame, "command_ring")

    if (view.status or "") in ("no ack", "timeout"):
        assert bbox_height(one(frame, "command_state_text")) >= 20.0


def test_armed_frame_has_no_ambiguous_channel_chips() -> None:
    view = real_state_views()["armed_fire"]

    frame = gui.render_frame(view)

    assert not ops(frame, "armed_chip_label")
    assert not ops(frame, "armed_chip")
    assert not ops(frame, "armed_chip_rim")


def test_palette_count_screen_displays_count_not_selected_led_index() -> None:
    view = gui.View(
        field_label="BARVY",
        status="6 barev",
        field_value="6",
        palette_count=6,
        selected_led=4,
        colors=[
            (255, 30, 30),
            (30, 220, 90),
            (40, 120, 255),
            (255, 180, 0),
            (200, 40, 255),
            (0, 220, 220),
        ],
    )

    frame = gui.render_frame(view)

    assert one(frame, "orb_text").text == "6"
    assert one(frame, "orb_text").text != str(view.selected_led + 1)


def test_fire_locked_command_keeps_text_away_from_round_edges() -> None:
    view = gui.scenes()["02_action_fire"]

    frame = gui.render_frame(view)

    assert_horizontal_breathing_room(one(frame, "command_text"), left=30.0, right=210.0)
    assert_horizontal_breathing_room(one(frame, "fire_locked_badge"), left=36.0, right=204.0)


def test_wait_ack_status_panel_keeps_round_edge_breathing_room() -> None:
    view = gui.scenes()["04_wait_ack"]

    frame = gui.render_frame(view)

    assert_horizontal_breathing_room(one(frame, "command_state_badge"), left=30.0, right=210.0)
    assert_horizontal_breathing_room(one(frame, "command_safe_text"), left=47.0, right=193.0)


def test_ack_confirmation_uses_checkmark_without_text_label() -> None:
    frame = gui.render_frame(gui.scenes()["05_ack"])

    assert len(ops(frame, "ack_check")) == 1
    assert len(ops(frame, "ack_check_highlight")) == 1
    assert not ops(frame, "command_state_text")
    assert not ops(frame, "command_ack_badge")


@pytest.mark.parametrize("scene", ["04_wait_ack", "06_no_ack"])
def test_orange_status_panels_use_single_clear_stack(scene: str) -> None:
    frame = gui.render_frame(gui.scenes()[scene])

    assert len(ops(frame, "command_state_badge")) == 1
    assert not ops(frame, "command_safe_badge")

    panel = one(frame, "command_state_badge")
    title = one(frame, "command_state_text")
    detail = one(frame, "command_safe_text")
    assert panel.bbox is not None and title.bbox is not None and detail.bbox is not None
    assert_bbox_contains(panel, title, pad=8.0)
    assert_bbox_contains(panel, detail, pad=8.0)
    assert detail.bbox[1] >= title.bbox[3] + 8.0


def test_visible_czech_ui_labels_use_diacritics() -> None:
    command_frame = gui.render_frame(gui.scenes()["01_ready_action"])

    assert one(command_frame, "mode_caption").text == "PŘÍKAZ"

    forbidden = {"PRIKAZ", "NASTAVENI", "ODSTIN"}
    rendered = {
        op.text
        for frame in (command_frame,)
        for op in frame.ops
        if op.kind == "text"
    }
    assert rendered.isdisjoint(forbidden)


@pytest.mark.parametrize("name,view", gui.scenes().items())
def test_prominent_text_keeps_horizontal_round_edge_margin(name: str, view: gui.View) -> None:
    frame = gui.render_frame(view)
    prominent_roles = {
        "command_text",
        "command_state_text",
        "armed_state_text",
        "armed_cancel_text",
    }

    for op in frame.ops:
        if op.role not in prominent_roles:
            continue
        assert_horizontal_breathing_room(op, left=30.0, right=210.0)
        assert bbox_width(op) <= 180.0


@pytest.mark.parametrize("name,view", gui.scenes().items())
def test_setup_orb_subtext_keeps_inner_bottom_padding(name: str, view: gui.View) -> None:
    if gui.is_command_mode(view) or view.armed:
        return

    frame = gui.render_frame(view)
    orb = one(frame, "orb_lens")
    subtext = one(frame, "orb_subtext")

    assert orb.bbox is not None and subtext.bbox is not None
    assert orb.bbox[3] - subtext.bbox[3] >= 8.0


@pytest.mark.parametrize("name,view", gui.scenes().items())
def test_setup_orb_text_keeps_circular_lens_clearance(name: str, view: gui.View) -> None:
    if gui.is_command_mode(view) or view.armed:
        return

    frame = gui.render_frame(view)
    orb = one(frame, "orb_lens")
    assert orb.bbox is not None
    cx = (orb.bbox[0] + orb.bbox[2]) / 2.0
    cy = (orb.bbox[1] + orb.bbox[3]) / 2.0
    radius = (orb.bbox[2] - orb.bbox[0]) / 2.0

    for role in ("orb_text", "orb_subtext"):
        text = one(frame, role)
        assert text.bbox is not None
        left, top, right, bottom = text.bbox
        max_corner_distance = max(
            math.hypot(x - cx, y - cy)
            for x, y in ((left, top), (right, top), (left, bottom), (right, bottom))
        )
        assert max_corner_distance <= radius - 2.0, text


@pytest.mark.parametrize("field_label", ["jas", "LED", "HUE", "BARVY"])
def test_setup_orb_uses_neutral_tuning_color_instead_of_selected_led_color(
    field_label: str,
) -> None:
    view = gui.View(
        field_label=field_label,
        selected_led=1,
        selected_hue_degrees=120,
        palette_count=4,
        colors=_fixture_colors(),
    )

    frame = gui.render_frame(view)

    assert one(frame, "orb_lens").color == gui.mix(gui.MODE_SETUP, gui.WHITE, 0.18)
    assert one(frame, "orb_lens").color != gui.led_rgb(view, view.selected_led)


def test_firmware_renderer_keeps_safety_visuals_in_parity_with_preview() -> None:
    cpp = GUI_CPP.read_text(encoding="utf-8")

    assert "is_locked_fire_choice(view) || is_preview_choice(view) || is_stop_choice(view)" in cpp
    assert "size_t utf8_glyph_len" in cpp
    assert 'drawTrackedTopCenterText(_canvas, command ? "PŘÍKAZ" : "NASTAVENÍ", CX, 36, 4.0f)' in cpp
    assert 'return "ODSTÍN";' in cpp
    assert 'drawTopCenterText(canvas, "FIRE LOCKED", cx, cy - 36)' in cpp
    assert 'drawTopCenterText(canvas, "ARM REQUIRED", cx, cy + 15)' in cpp
    assert 'drawTopCenterText(canvas, "STOP", cx, cy - 39)' in cpp
    assert 'drawTopCenterText(canvas, "NO FIRE", cx, cy - 40)' in cpp
    assert "fillRoundRect(cx - 32, cy + 19, 64, 30, 12" not in cpp
    assert 'drawTopCenterText(canvas, "ACK", cx, cy + 22)' not in cpp
    assert cpp.count('drawTopCenterText(canvas, "OUTPUT OFF", cx, cy + 18)') == 2
    assert "canvas->setTextSize(1.52f);" in cpp
    assert "canvas->setTextSize(0.54f);" in cpp
    assert "canvas->setTextSize(0.70f);" in cpp
    assert "canvas->setTextSize(0.74f);" in cpp
    assert 'drawTrackedTopCenterText(canvas, "DO NOT PRESS", cx, cy + 30, 0.5f)' in cpp
    assert 'drawTrackedTopCenterText(canvas, "CHECK LINK", cx, cy + 25, 1.0f)' in cpp
    assert "SEL_ACCENT" in cpp
    assert 'strcmp(variant, "ack") != 0' in cpp
    assert 'strcmp(variant, "no_ack") != 0' in cpp
    assert "transient_command_state ? 0 : static_cast<int>(view.colors.size())" in cpp
    assert "float span = count > 5 ? 110.0f : (count - 1) * 24.0f;" in cpp
    assert "fillRoundRect(cx - 90, cy - 28, 180, 84, 18" in cpp
    assert "fillRoundRect(cx - 78, cy + 30, 156, 32, 13" not in cpp
    assert "fillRoundRect(cx - 84, cy + 8, 168, 38, 16" in cpp
    assert cpp.count("fillRoundRect(cx - 86, cy + 15, 172, 34, 16") == 2
    assert 'drawTopCenterText(canvas, "OUTPUT OFF", cx, cy + 22)' not in cpp
    assert "uint32_t setup_orb_color()" in cpp
    assert "uint32_t orb_col = setup_orb_color();" in cpp
    assert "ORB_R + 20" in cpp
    assert "drawCenteredText(canvas, label, cx, cy - 9);" in cpp
    assert "drawTrackedTopCenterText(_canvas, field_caption(view), CX, ORB_CY + 14, 1.2f)" in cpp
    assert 'drawTopCenterText(canvas, "ARMED", CX, 50)' in cpp
    assert '"FIRE READY"' not in cpp
    assert 'drawTrackedTopCenterText(canvas, "PRESS", CX, 114, 0.6f)' in cpp
    assert 'drawTrackedTopCenterText(canvas, "STOP", CX, 136, 0.0f)' in cpp
    assert 'drawTrackedTopCenterText(canvas, "TO DISARM", CX, 181, 0.6f)' in cpp


@pytest.mark.parametrize(
    "status",
    [
        "KEY MISSING",
        "BAD ACK",
        "RX IGNORED",
        "BLOKOVANO",
        "ZAMITNUTO",
        "FF BUSY",
        "FF DUTY",
        "PAL ENC FAIL",
        "nvs err",
    ],
)
def test_preview_status_classifier_matches_firmware_faults(status: str) -> None:
    view = gui.View(action_label="PING", field_label="akce", status=status, field_value="PING")

    frame = gui.render_frame(view)

    assert gui.state_color(view) == gui.P_RED
    assert {op.color for op in ops(frame, "command_ring")} == {gui.P_RED}


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


@pytest.mark.parametrize("name,view", gui.scenes().items())
def test_m5_dial_preview_passes_espos_round_safe_area_rules(
    name: str, view: gui.View
) -> None:
    frame = gui.render_frame(view)
    design = _m5_frame_as_espos_design(name, frame)

    issues = _validate_design.validate_data(
        design,
        file_label="m5_dial_preview",
        warnings_as_errors=False,
        strict_critical=True,
    )

    assert [i.message for i in issues if "round safe area" in i.message] == []


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
