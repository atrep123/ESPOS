from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol import protocol as proto  # noqa: E402
from shared.protocol.protocol import FrameType, PropFrame, ProtocolError  # noqa: E402
from tools import preview_protocol_roundtrip as sim  # noqa: E402


PROTOCOL_H = ROOT / "shared/protocol/prop_protocol.h"
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


def _header_numeric_constants() -> dict[str, int]:
    text = PROTOCOL_H.read_text(encoding="utf-8")
    values: dict[str, int] = {}
    for name, expr in re.findall(r"constexpr\s+(?:[\w:]+|size_t)\s+(\w+)\s*=\s*([^;]+);", text):
        expr = expr.strip()
        if "FrameType::" in expr:
            continue
        assert re.fullmatch(r"[0-9A-Fa-fxX+\sA-Z_]+", expr), f"unsafe constexpr expression for {name}: {expr}"
        values[name] = int(eval(expr, {"__builtins__": {}}, values))
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
    # Addressing constants (PROP_KEY_ID/SOURCE/DESTINATION) moved into the Marlin-style
    # config headers; SHARED_KEY deliberately stays in the .cpp. Concatenate each firmware's
    # .cpp with its config header so the cross-check finds every constant wherever it now lives.
    tx_cpp = PROP_TX_CPP.read_text(encoding="utf-8") + "\n" + PROP_TX_CONFIG_H.read_text(encoding="utf-8")
    rx_cpp = PROP_RX_CPP.read_text(encoding="utf-8") + "\n" + PROP_RX_CONFIG_H.read_text(encoding="utf-8")

    assert sim.PROP_KEY_ID == _cpp_numeric_constant(tx_cpp, "PROP_KEY_ID")
    assert sim.PROP_KEY_ID == _cpp_numeric_constant(rx_cpp, "PROP_KEY_ID")
    assert sim.PROP_TX_SOURCE == _cpp_numeric_constant(tx_cpp, "PROP_SOURCE")
    assert sim.PROP_TX_DESTINATION == _cpp_numeric_constant(tx_cpp, "PROP_DESTINATION")
    assert sim.PROP_RX_SOURCE == _cpp_numeric_constant(rx_cpp, "PROP_SOURCE")
    assert sim.PROP_RX_DESTINATION == _cpp_numeric_constant(rx_cpp, "PROP_DESTINATION")
    assert sim.SHARED_KEY == _cpp_shared_key(tx_cpp) == _cpp_shared_key(rx_cpp)


@pytest.mark.parametrize(
    "frame_type,expected_status,expected_mode",
    [
        (FrameType.PING, "PING", sim.ReceiverMode.IDLE),
        (FrameType.STATUS, "PING", sim.ReceiverMode.IDLE),
        (FrameType.PREVIEW, "PREVIEW", sim.ReceiverMode.PREVIEW),
        (FrameType.FIRE, "FIRE", sim.ReceiverMode.FIRE),
        (FrameType.STOP, "STOP", sim.ReceiverMode.IDLE),
        (FrameType.ACK, "UNHANDLED", sim.ReceiverMode.IDLE),
        (FrameType.ERROR, "UNHANDLED", sim.ReceiverMode.IDLE),
    ],
)
def test_every_frame_type_roundtrips_through_sender_encode_and_receiver_decode(
    frame_type: FrameType,
    expected_status: str,
    expected_mode: sim.ReceiverMode,
) -> None:
    tx_state = controller(frame_type, brightness=255, sequence=42, nonce=0xAABBCCDDEEFF0011)
    encoded = sim.encode_controller_frame(tx_state)
    result = sim.receive_encoded_frame(encoded, sim.ReceiverState())

    assert result.status == expected_status
    assert result.accepted is True
    assert result.frame is not None
    assert result.frame.frame_type == frame_type
    assert result.frame.key_id == sim.PROP_KEY_ID
    assert result.frame.source == sim.PROP_TX_SOURCE
    assert result.frame.destination == sim.PROP_TX_DESTINATION
    assert result.frame.sequence == tx_state.sequence
    assert result.frame.nonce == tx_state.nonce
    assert result.receiver_state.mode == expected_mode
    assert result.receiver_state.last_accepted_sequence == tx_state.sequence

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
    "last_sequence,sequence,expected_status",
    [
        (10, 9, "STALE"),
        (10, 10, "DUP"),
    ],
)
def test_receiver_detects_stale_and_duplicate_sequences(
    last_sequence: int,
    sequence: int,
    expected_status: str,
) -> None:
    encoded = sim.encode_controller_frame(controller(sequence=sequence))
    receiver = sim.ReceiverState(last_accepted_sequence=last_sequence)

    result = sim.receive_encoded_frame(encoded, receiver)

    assert result.status == expected_status
    assert result.accepted is False
    assert result.receiver_state.last_accepted_sequence == last_sequence
    assert result.receiver_state.colors == receiver.colors


@pytest.mark.parametrize("payload", [b"", b"\x96", b"\x96" + bytes(range(11)), b"\x96" + bytes(range(13))])
def test_receiver_rejects_malformed_led_payloads_without_applying_them(payload: bytes) -> None:
    encoded = sim.encode_controller_frame(
        controller(FrameType.FIRE, sequence=11),
        payload=payload,
    )
    receiver = sim.ReceiverState(brightness=17, colors=sim.DEFAULT_COLORS)

    result = sim.receive_encoded_frame(encoded, receiver)

    assert result.status == "BAD PAYLOAD"
    assert result.accepted is False
    assert result.reconstructed is None
    assert result.receiver_state.brightness == 17
    assert result.receiver_state.colors == sim.DEFAULT_COLORS
    assert result.receiver_state.last_accepted_sequence == 11


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
