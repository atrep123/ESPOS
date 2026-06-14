from __future__ import annotations

import re
import sys
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol import protocol as proto  # noqa: E402
from shared.protocol.protocol import FrameType, PropFrame, ProtocolError  # noqa: E402

_SIM_SPEC = importlib.util.spec_from_file_location(
    "m5_preview_protocol_roundtrip", ROOT / "tools" / "preview_protocol_roundtrip.py"
)
assert _SIM_SPEC is not None and _SIM_SPEC.loader is not None
sim = importlib.util.module_from_spec(_SIM_SPEC)
sys.modules[_SIM_SPEC.name] = sim
_SIM_SPEC.loader.exec_module(sim)


PROTOCOL_H = ROOT / "shared/protocol/prop_protocol.h"
RUNTIME_KEY_H = ROOT / "shared/protocol/prop_runtime_key.h"
PROP_TX_CPP = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp"
PROP_TX_CONFIG_H = ROOT / "firmware/dial-tx/main/apps/app_prop_tx/prop_tx_config.h"
PROP_RX_CPP = ROOT / "firmware/din-rx/src/prop_rx.cpp"
PROP_RX_CONFIG_H = ROOT / "firmware/din-rx/src/prop_config.h"

FIXTURE_COLORS: tuple[sim.Rgb, ...] = (
    (0, 0, 0),
    (1, 2, 3),
    (254, 255, 128),
    (17, 34, 51),
)


def controller(
    frame_type: FrameType = FrameType.PREVIEW,
    *,
    brightness: int = 207,
    sequence: int = 10,
    nonce: int = 0x0102030405060708,
) -> sim.ControllerState:
    return sim.ControllerState(
        frame_type=frame_type,
        brightness=brightness,
        colors=FIXTURE_COLORS,
        sequence=sequence,
        nonce=nonce,
    )


def receiver_with_replay_base(
    sequence: int,
    *,
    nonce: int = 0x0102030405060708,
    replay_seen_mask: int = 0,
) -> sim.ReceiverState:
    return sim.ReceiverState(
        last_accepted_sequence=sequence,
        replay_epoch=(nonce >> 32) & 0xFFFFFFFF,
        replay_seen_mask=replay_seen_mask,
    )


def armed_receiver(
    *,
    arm_sequence: int = 10,
    nonce: int = 0x0102030405060708,
    now_ms: int = 1000,
) -> sim.ReceiverState:
    result = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.ARM, sequence=arm_sequence, nonce=nonce)),
        sim.ReceiverState(),
        now_ms=now_ms,
    )
    assert result.status == "ARMED"
    assert result.accepted is True
    return result.receiver_state


def _header_numeric_constants() -> dict[str, int]:
    text = PROTOCOL_H.read_text(encoding="utf-8")
    values: dict[str, int] = {}
    for name, expr in re.findall(r"constexpr\s+(?:[\w:]+|size_t)\s+(\w+)\s*=\s*([^;]+);", text):
        expr = expr.strip()
        if "FrameType::" in expr:
            continue
        tokens = [token.strip() for token in expr.split("+")]
        assert tokens and all(tokens), f"unsupported constexpr expression for {name}: {expr}"
        total = 0
        for token in tokens:
            if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", token):
                total += int(token, 0)
            else:
                assert token in values, f"unknown constexpr dependency {token} for {name}: {expr}"
                total += values[token]
        values[name] = total
    return values


def _header_frame_type_values() -> dict[str, int]:
    text = PROTOCOL_H.read_text(encoding="utf-8")
    block = re.search(r"enum class FrameType\s*:\s*uint8_t\s*\{(.*?)\};", text, re.S)
    assert block, "FrameType enum not found"
    return {
        name: int(value)
        for name, value in re.findall(r"\b(\w+)\s*=\s*(\d+)\s*,", block.group(1))
    }


def _cpp_frame_type_to_python_name(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


def _cpp_numeric_constant(text: str, name: str) -> int:
    match = re.search(rf"constexpr\s+[^=]+?\s+{name}\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;", text)
    assert match, f"{name} not found"
    return int(match.group(1), 0)


def _cpp_shared_key(text: str) -> bytes:
    match = re.search(r"SHARED_KEY\[\]\s*=\s*\{(.*?)\};", text, re.S)
    assert match, "SHARED_KEY not found"
    return bytes(int(token, 16) for token in re.findall(r"0x([0-9A-Fa-f]{2})", match.group(1)))


def test_protocol_py_constants_match_prop_protocol_h() -> None:
    constants = _header_numeric_constants()

    assert proto.MAGIC == constants["PROP_FRAME_MAGIC"]
    assert proto.VERSION == constants["PROP_PROTOCOL_VERSION"]
    assert proto.MAX_PAYLOAD_LENGTH == constants["MAX_PAYLOAD_LENGTH"]
    assert proto.LED_PAYLOAD_LENGTH == constants["LED_PAYLOAD_LENGTH"]
    assert proto.MAC_LENGTH == constants["MAC_LENGTH"]
    assert proto.HEADER_LENGTH == constants["HEADER_LENGTH"] == proto.HEADER.size
    assert proto.MAX_FRAME_LENGTH == constants["MAX_FRAME_LENGTH"]

    enum_values = _header_frame_type_values()
    for cpp_name, cpp_value in enum_values.items():
        py_name = _cpp_frame_type_to_python_name(cpp_name)
        assert py_name in FrameType.__members__, f"Python FrameType missing {py_name} for C++ {cpp_name}"
        assert FrameType[py_name].value == cpp_value


def test_roundtrip_sim_constants_match_sender_and_receiver_firmware() -> None:
    # Addressing constants (PROP_KEY_ID/SOURCE/DESTINATION) live in the Marlin-style
    # config headers. HMAC bytes are runtime-provisioned, so this test checks the
    # routing constants and provider shape, not source-embedded key equality.
    tx_cpp = PROP_TX_CPP.read_text(encoding="utf-8") + "\n" + PROP_TX_CONFIG_H.read_text(encoding="utf-8")
    rx_cpp = PROP_RX_CPP.read_text(encoding="utf-8") + "\n" + PROP_RX_CONFIG_H.read_text(encoding="utf-8")
    provider = RUNTIME_KEY_H.read_text(encoding="utf-8")

    assert sim.PROP_KEY_ID == _cpp_numeric_constant(tx_cpp, "PROP_KEY_ID")
    assert sim.PROP_KEY_ID == _cpp_numeric_constant(rx_cpp, "PROP_KEY_ID")
    assert sim.PROP_TX_SOURCE == _cpp_numeric_constant(tx_cpp, "PROP_SOURCE")
    assert sim.PROP_TX_DESTINATION == _cpp_numeric_constant(tx_cpp, "PROP_DESTINATION")
    assert sim.PROP_RX_SOURCE == _cpp_numeric_constant(rx_cpp, "PROP_SOURCE")
    assert sim.PROP_RX_DESTINATION == _cpp_numeric_constant(rx_cpp, "PROP_DESTINATION")
    assert "prop_runtime_key.h" in tx_cpp
    assert "prop_runtime_key.h" in rx_cpp
    assert "RuntimeKey" in provider
    assert "NVS_NAMESPACE" in provider
    assert "NVS_KEY" in provider
    assert "SHARED_KEY[]" not in tx_cpp
    assert "SHARED_KEY[]" not in rx_cpp
    assert "sizeof(SHARED_KEY)" not in tx_cpp
    assert "sizeof(SHARED_KEY)" not in rx_cpp


@pytest.mark.parametrize(
    "frame_type,expected_status,expected_mode,expected_accepted",
    [
        (FrameType.PING, "PING", sim.ReceiverMode.IDLE, True),
        (FrameType.STATUS, "PING", sim.ReceiverMode.IDLE, True),
        (FrameType.PREVIEW, "PREVIEW", sim.ReceiverMode.PREVIEW, True),
        (FrameType.FIRE, "NOT_ARMED", sim.ReceiverMode.IDLE, False),
        (FrameType.STOP, "STOP", sim.ReceiverMode.IDLE, True),
        (FrameType.ARM, "ARMED", sim.ReceiverMode.IDLE, True),
        (FrameType.ACK, "UNHANDLED", sim.ReceiverMode.IDLE, True),
        (FrameType.ERROR, "UNHANDLED", sim.ReceiverMode.IDLE, True),
    ],
)
def test_every_frame_type_roundtrips_through_sender_encode_and_receiver_decode(
    frame_type: FrameType,
    expected_status: str,
    expected_mode: sim.ReceiverMode,
    expected_accepted: bool,
) -> None:
    tx_state = controller(frame_type, brightness=255, sequence=42, nonce=0xAABBCCDDEEFF0011)
    encoded = sim.encode_controller_frame(tx_state)
    result = sim.receive_encoded_frame(encoded, sim.ReceiverState())

    assert result.status == expected_status
    assert result.accepted is expected_accepted
    assert result.frame is not None
    assert result.frame.frame_type == frame_type
    assert result.frame.key_id == sim.PROP_KEY_ID
    assert result.frame.source == sim.PROP_TX_SOURCE
    assert result.frame.destination == sim.PROP_TX_DESTINATION
    assert result.frame.sequence == tx_state.sequence
    assert result.frame.nonce == tx_state.nonce
    assert result.receiver_state.mode == expected_mode
    assert result.receiver_state.last_accepted_sequence == tx_state.sequence

    if not expected_accepted:
        assert result.reconstructed is None
        return

    if frame_type in sim.LED_FRAME_TYPES:
        assert result.frame.payload == sim.led_payload_from_controller(tx_state)
        assert result.reconstructed == sim.LedState(brightness=255, colors=FIXTURE_COLORS)
        assert result.receiver_state.brightness == tx_state.brightness
        assert result.receiver_state.colors == tx_state.colors
    else:
        assert result.frame.payload == b""
        assert result.reconstructed is None


@pytest.mark.parametrize(
    "brightness,colors",
    [
        (0, ((0, 0, 0), (0, 1, 2), (3, 4, 5), (6, 7, 8))),
        (255, ((255, 255, 255), (255, 0, 1), (2, 254, 3), (4, 5, 253))),
    ],
)
def test_roundtrip_preserves_byte_boundaries_without_truncation(
    brightness: int,
    colors: tuple[sim.Rgb, ...],
) -> None:
    tx_state = sim.ControllerState(
        frame_type=FrameType.PREVIEW,
        brightness=brightness,
        colors=colors,
        sequence=1,
        nonce=1,
    )

    result = sim.receive_encoded_frame(sim.encode_controller_frame(tx_state), sim.ReceiverState())

    assert result.status == "PREVIEW"
    assert result.reconstructed == sim.LedState(brightness=brightness, colors=colors)
    assert result.receiver_state.brightness == brightness
    assert result.receiver_state.colors == colors


@pytest.mark.parametrize(
    "override,expected_status",
    [
        ({"key_id": sim.PROP_KEY_ID + 1}, "BAD KEY"),
        ({"source": sim.PROP_TX_SOURCE + 1}, "BAD SRC"),
        ({"destination": sim.PROP_TX_DESTINATION + 1}, "BAD DST"),
    ],
)
def test_receiver_detects_validly_signed_route_rejects(
    override: dict[str, int],
    expected_status: str,
) -> None:
    encoded = sim.encode_controller_frame(controller(sequence=5), **override)

    result = sim.receive_encoded_frame(encoded, sim.ReceiverState())

    assert result.status == expected_status
    assert result.accepted is False
    assert result.receiver_state.last_accepted_sequence == 0


def test_receiver_detects_bad_mac_and_short_frames_without_accepting_them() -> None:
    encoded = bytearray(sim.encode_controller_frame(controller(sequence=5)))
    encoded[-1] ^= 0x01

    bad_mac = sim.receive_encoded_frame(bytes(encoded), sim.ReceiverState())
    short = sim.receive_encoded_frame(bytes(encoded[: proto.HEADER_LENGTH + proto.MAC_LENGTH - 1]), sim.ReceiverState())

    assert bad_mac.status == "BAD MAC"
    assert bad_mac.accepted is False
    assert bad_mac.frame is None
    assert bad_mac.receiver_state.last_accepted_sequence == 0
    assert short.status == "BAD MAC"
    assert short.accepted is False
    assert short.frame is None


@pytest.mark.parametrize(
    "last_sequence,replay_seen_mask,sequence,expected_status,expected_accepted",
    [
        (10, 0, 9, "PREVIEW", True),
        (10, 0x01, 9, "DUP", False),
        (10, 0, 10, "DUP", False),
        (50, 0, 17, "STALE", False),
    ],
)
def test_receiver_uses_firmware_replay_window_for_stale_duplicate_and_backfill_sequences(
    last_sequence: int,
    replay_seen_mask: int,
    sequence: int,
    expected_status: str,
    expected_accepted: bool,
) -> None:
    encoded = sim.encode_controller_frame(controller(sequence=sequence))
    receiver = receiver_with_replay_base(last_sequence, replay_seen_mask=replay_seen_mask)

    result = sim.receive_encoded_frame(encoded, receiver)

    assert result.status == expected_status
    assert result.accepted is expected_accepted
    assert result.receiver_state.last_accepted_sequence == last_sequence
    if expected_accepted:
        assert result.receiver_state.colors == FIXTURE_COLORS
    else:
        assert result.receiver_state.colors == receiver.colors


def test_receiver_resets_replay_window_on_new_epoch() -> None:
    receiver = receiver_with_replay_base(100, nonce=0x0102030400000000)
    encoded = sim.encode_controller_frame(controller(sequence=4, nonce=0x0203040500000001))

    result = sim.receive_encoded_frame(encoded, receiver)

    assert result.status == "PREVIEW"
    assert result.accepted is True
    assert result.receiver_state.last_accepted_sequence == 4
    assert result.receiver_state.replay_epoch == 0x02030405


def test_receiver_deduplicates_identical_fire_burst_copy_without_reapplying() -> None:
    state = controller(FrameType.FIRE, sequence=11, nonce=0x0102030405060708)
    encoded = sim.encode_controller_frame(state)
    first = sim.receive_encoded_frame(encoded, armed_receiver(arm_sequence=10, nonce=state.nonce))

    duplicate = sim.receive_encoded_frame(encoded, first.receiver_state)

    assert first.status == "FIRE"
    assert first.accepted is True
    assert first.receiver_state.mode == sim.ReceiverMode.FIRE
    assert duplicate.status == "DUP"
    assert duplicate.accepted is False
    assert duplicate.receiver_state.last_accepted_sequence == first.receiver_state.last_accepted_sequence
    assert duplicate.receiver_state.mode == first.receiver_state.mode
    assert duplicate.receiver_state.colors == first.receiver_state.colors


def test_receiver_rejects_fire_before_arm_and_requires_post_arm_sequence() -> None:
    fire = controller(FrameType.FIRE, sequence=11, nonce=0x0102030405060708)

    unarmed = sim.receive_encoded_frame(sim.encode_controller_frame(fire), sim.ReceiverState())
    same_sequence = sim.receive_encoded_frame(
        sim.encode_controller_frame(fire, sequence=10),
        armed_receiver(arm_sequence=10, nonce=fire.nonce),
    )
    accepted = sim.receive_encoded_frame(
        sim.encode_controller_frame(fire),
        armed_receiver(arm_sequence=10, nonce=fire.nonce),
    )
    second_fire = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.FIRE, sequence=12, nonce=fire.nonce)),
        accepted.receiver_state,
    )

    assert unarmed.status == "NOT_ARMED"
    assert unarmed.accepted is False
    assert same_sequence.status == "DUP"
    assert same_sequence.accepted is False
    assert accepted.status == "FIRE"
    assert accepted.accepted is True
    assert accepted.receiver_state.armed is False
    assert second_fire.status == "NOT_ARMED"
    assert second_fire.accepted is False


def test_receiver_rejects_fire_after_arm_ttl_or_epoch_mismatch() -> None:
    nonce = 0x0102030405060708
    armed = armed_receiver(arm_sequence=10, nonce=nonce, now_ms=1000)

    expired = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.FIRE, sequence=11, nonce=nonce)),
        armed,
        now_ms=1000 + sim.ARM_TTL_MS,
    )
    wrong_epoch = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.FIRE, sequence=11, nonce=0x0203040505060708)),
        armed,
        now_ms=1001,
    )

    assert expired.status == "NOT_ARMED"
    assert expired.accepted is False
    assert wrong_epoch.status == "NOT_ARMED"
    assert wrong_epoch.accepted is False


def test_stop_latch_blocks_old_arm_and_requires_fresh_rearm_before_fire() -> None:
    nonce = 0x0102030405060708
    armed = armed_receiver(arm_sequence=10, nonce=nonce)
    stopped = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.STOP, sequence=12, nonce=nonce)),
        armed,
    )
    old_arm = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.ARM, sequence=11, nonce=nonce)),
        stopped.receiver_state,
    )
    old_fire = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.FIRE, sequence=11, nonce=nonce)),
        stopped.receiver_state,
    )
    fresh_arm = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.ARM, sequence=13, nonce=nonce)),
        stopped.receiver_state,
    )
    fresh_fire = sim.receive_encoded_frame(
        sim.encode_controller_frame(controller(FrameType.FIRE, sequence=14, nonce=nonce)),
        fresh_arm.receiver_state,
    )

    assert stopped.status == "STOP"
    assert stopped.receiver_state.lockout is True
    assert old_arm.status == "LOCKOUT"
    assert old_arm.accepted is False
    assert old_fire.status == "NOT_ARMED"
    assert old_fire.accepted is False
    assert fresh_arm.status == "ARMED"
    assert fresh_arm.accepted is True
    assert fresh_fire.status == "FIRE"
    assert fresh_fire.accepted is True


@pytest.mark.parametrize("payload", [b"", b"\x96", b"\x96" + bytes(range(11)), b"\x96" + bytes(range(13))])
def test_receiver_rejects_malformed_led_payloads_without_applying_them(payload: bytes) -> None:
    encoded = sim.encode_controller_frame(
        controller(FrameType.FIRE, sequence=11),
        payload=payload,
    )
    receiver = armed_receiver(arm_sequence=10)
    receiver = sim.ReceiverState(
        brightness=17,
        colors=sim.DEFAULT_COLORS,
        last_accepted_sequence=receiver.last_accepted_sequence,
        replay_epoch=receiver.replay_epoch,
        replay_seen_mask=receiver.replay_seen_mask,
        armed=receiver.armed,
        arm_epoch=receiver.arm_epoch,
        arm_sequence=receiver.arm_sequence,
        arm_expiry_ms=receiver.arm_expiry_ms,
        now_ms=receiver.now_ms,
    )

    result = sim.receive_encoded_frame(encoded, receiver)

    assert result.status == "BAD PAYLOAD"
    assert result.accepted is False
    assert result.reconstructed is None
    assert result.receiver_state.brightness == 17
    assert result.receiver_state.colors == sim.DEFAULT_COLORS
    assert result.receiver_state.last_accepted_sequence == 11
    assert result.receiver_state.armed is False


@pytest.mark.parametrize("line", ["RX only-two-fields", "RX -42 9 XYZ", "RX -42 9 0"])
def test_receiver_detects_bad_rx_lines_before_decode(line: str) -> None:
    result = sim.receive_rx_line(line, sim.ReceiverState())

    assert result.status == "BAD RX"
    assert result.accepted is False
    assert result.frame is None


def test_modem_line_roundtrip_uses_sender_hex_and_receiver_rx_prefix() -> None:
    tx_state = controller(FrameType.PREVIEW, sequence=77, nonce=0x1111222233334444)
    send_line = sim.encode_controller_line(tx_state)
    assert send_line.startswith("SEND ")
    assert send_line.endswith("\n")

    encoded = sim.extract_send_line_frame(send_line)
    rx_line = sim.make_rx_line(encoded, rssi=-57, snr=8)
    result = sim.receive_rx_line(rx_line, sim.ReceiverState())

    assert result.status == "PREVIEW"
    assert result.reconstructed == sim.LedState(tx_state.brightness, tx_state.colors)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"key_id": -1},
        {"key_id": 256},
        {"source": -1},
        {"source": 256},
        {"destination": -1},
        {"destination": 256},
        {"sequence": -1},
        {"sequence": 2**32},
        {"nonce": -1},
        {"nonce": 2**64},
    ],
)
def test_frame_encoder_rejects_out_of_range_fields_instead_of_truncating(kwargs: dict[str, int]) -> None:
    with pytest.raises(ProtocolError):
        sim.encode_controller_frame(controller(sequence=1, nonce=1), **kwargs)


@pytest.mark.parametrize(
    "brightness,colors",
    [
        (-1, FIXTURE_COLORS),
        (256, FIXTURE_COLORS),
        (1, FIXTURE_COLORS[:3]),
        (1, (*FIXTURE_COLORS[:3], (0, 0))),
        (1, (*FIXTURE_COLORS[:3], (0, 0, 256))),
        (1, (*FIXTURE_COLORS[:3], (0, 0, -1))),
    ],
)
def test_led_payload_encoder_rejects_out_of_range_values_instead_of_truncating(
    brightness: int,
    colors: tuple[tuple[int, ...], ...],
) -> None:
    with pytest.raises(ProtocolError):
        sim.ControllerState(
            frame_type=FrameType.PREVIEW,
            brightness=brightness,
            colors=colors,  # type: ignore[arg-type]
            sequence=1,
            nonce=1,
        ).led_payload()


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", 256),
        ("destination", 256),
        ("sequence", 2**32),
        ("nonce", 2**64),
    ],
)
def test_shared_protocol_encode_frame_reports_range_errors_as_protocol_errors(field: str, value: int) -> None:
    frame = PropFrame(
        frame_type=FrameType.PING,
        key_id=sim.PROP_KEY_ID,
        source=sim.PROP_TX_SOURCE,
        destination=sim.PROP_TX_DESTINATION,
        sequence=1,
        nonce=1,
    )
    frame = PropFrame(**{**frame.__dict__, field: value})

    with pytest.raises(ProtocolError):
        proto.encode_frame(frame, {sim.PROP_KEY_ID: sim.SHARED_KEY})


def test_palette_payload_constants_mirror_prop_protocol_h() -> None:
    # PaletteSet parity slot: the Python PaletteSet helpers must stay byte-identical to the
    # C++ encodePalettePayload/parsePalettePayload in prop_protocol.h.
    constants = _header_numeric_constants()
    assert proto.MAX_PALETTE_COLORS == constants["MAX_PALETTE_COLORS"]
    assert proto.PALETTE_HEADER_LENGTH == constants["PALETTE_HEADER_LENGTH"]
    assert int(FrameType.PALETTE_SET) == _header_frame_type_values()["PaletteSet"]


def test_palette_payload_roundtrips_byte_identically_to_cpp_layout() -> None:
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    encoded = proto.encode_palette_payload(7, True, colors)
    # Mirrors prop_protocol.h: header [rev, fade&1, count] then count RGB triples.
    assert encoded == bytes([7, 1, 3, 255, 0, 0, 0, 255, 0, 0, 0, 255])
    assert proto.parse_palette_payload(encoded) == {
        "palette_rev": 7,
        "fade": True,
        "colors": colors,
    }

    # Max width is PALETTE_HEADER_LENGTH + 3*MAX_PALETTE_COLORS.
    full = proto.encode_palette_payload(0, False, [(i, i, i) for i in range(proto.MAX_PALETTE_COLORS)])
    assert len(full) == proto.PALETTE_HEADER_LENGTH + 3 * proto.MAX_PALETTE_COLORS


def test_palette_parse_strips_reserved_fade_bits_like_cpp() -> None:
    # C++ reads fade as (payload[1] & 0x01); every other bit is reserved and ignored.
    assert proto.parse_palette_payload(bytes([1, 0xFE, 1, 9, 9, 9]))["fade"] is False
    assert proto.parse_palette_payload(bytes([1, 0xFF, 1, 9, 9, 9]))["fade"] is True


@pytest.mark.parametrize(
    "payload",
    [
        bytes([1, 0, 0]),                       # count == 0 (C++ rejects)
        bytes([1, 0, 9]) + bytes(27),           # count > MAX_PALETTE_COLORS
        bytes([1, 0]),                          # shorter than PALETTE_HEADER_LENGTH
        bytes([1, 0, 2, 1, 2, 3]),              # width mismatch (count 2 needs 6 colour bytes)
    ],
)
def test_palette_parse_rejects_bad_payloads_like_cpp(payload: bytes) -> None:
    with pytest.raises(ProtocolError):
        proto.parse_palette_payload(payload)


@pytest.mark.parametrize(
    "colors",
    [
        [],                                          # empty (C++ rejects colors.empty())
        [(0, 0, 0)] * (proto.MAX_PALETTE_COLORS + 1),  # exceeds MAX_PALETTE_COLORS
        [(0, 0)],                                    # not an RGB triple
    ],
)
def test_palette_encode_rejects_bad_color_lists(colors: list) -> None:
    with pytest.raises(ProtocolError):
        proto.encode_palette_payload(1, False, colors)
