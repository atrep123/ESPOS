"""Deterministic tx->rx protocol round-trip model for Prop LoRa frames.

This is a data simulation, not firmware. It mirrors the M5Dial prop-tx frame
encoding and din-rx validation path closely enough for pytest to catch drift in
the shared wire protocol before a bad frame changes downstream LED/display
output.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import (  # noqa: E402
    FrameType,
    PropFrame,
    ProtocolError,
    bytes_to_hex,
    decode_frame,
    encode_frame,
    encode_led_payload,
    hex_to_bytes,
    parse_led_payload,
)


Rgb = tuple[int, int, int]

PROP_KEY_ID = 1
PROP_TX_SOURCE = 0x11
PROP_TX_DESTINATION = 0x22
PROP_RX_SOURCE = 0x22
PROP_RX_DESTINATION = 0x11
SHARED_KEY = bytes(
    [
        0x00,
        0x11,
        0x22,
        0x33,
        0x44,
        0x55,
        0x66,
        0x77,
        0x88,
        0x99,
        0xAA,
        0xBB,
        0xCC,
        0xDD,
        0xEE,
        0xFF,
    ]
)

DEFAULT_COLORS: tuple[Rgb, ...] = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (16, 32, 48),
)
LED_FRAME_TYPES = frozenset((FrameType.PREVIEW, FrameType.FIRE))


class ReceiverMode(IntEnum):
    IDLE = 0
    PREVIEW = 1
    FIRE = 2


@dataclass(frozen=True)
class LedState:
    brightness: int
    colors: tuple[Rgb, ...]


@dataclass(frozen=True)
class ControllerState:
    frame_type: FrameType = FrameType.PREVIEW
    brightness: int = 150
    colors: tuple[Rgb, ...] = DEFAULT_COLORS
    sequence: int = 1
    nonce: int = 0x0102030405060708

    def led_payload(self) -> bytes:
        return encode_led_payload(self.brightness, list(self.colors))


@dataclass(frozen=True)
class ReceiverState:
    brightness: int = 150
    colors: tuple[Rgb, ...] = DEFAULT_COLORS
    mode: ReceiverMode = ReceiverMode.IDLE
    last_status: str = "READY"
    last_accepted_sequence: int = 0


@dataclass(frozen=True)
class RoundTripResult:
    status: str
    accepted: bool
    receiver_state: ReceiverState
    frame: PropFrame | None = None
    reconstructed: LedState | None = None


def led_payload_from_controller(state: ControllerState) -> bytes:
    return state.led_payload()


def encode_controller_frame(
    state: ControllerState,
    *,
    frame_type: FrameType | None = None,
    key_id: int | None = None,
    source: int | None = None,
    destination: int | None = None,
    sequence: int | None = None,
    nonce: int | None = None,
    payload: bytes | None = None,
) -> bytes:
    frame_type = FrameType(state.frame_type if frame_type is None else frame_type)
    frame_key_id = PROP_KEY_ID if key_id is None else key_id
    frame_payload = _payload_for_frame(state, frame_type, payload)
    frame = PropFrame(
        frame_type=frame_type,
        key_id=frame_key_id,
        source=PROP_TX_SOURCE if source is None else source,
        destination=PROP_TX_DESTINATION if destination is None else destination,
        sequence=state.sequence if sequence is None else sequence,
        nonce=state.nonce if nonce is None else nonce,
        payload=frame_payload,
    )
    return encode_frame(frame, {frame_key_id: SHARED_KEY})


def encode_controller_line(state: ControllerState, **overrides: object) -> str:
    encoded = encode_controller_frame(state, **overrides)
    return f"SEND {bytes_to_hex(encoded)}\n"


def extract_send_line_frame(line: str) -> bytes:
    stripped = line.strip()
    if not stripped.startswith("SEND "):
        raise ProtocolError("expected SEND line")
    return hex_to_bytes(stripped[5:].strip())


def make_rx_line(encoded: bytes, *, rssi: int = -42, snr: int = 9) -> str:
    return f"RX {rssi} {snr} {bytes_to_hex(encoded)}"


def receive_rx_line(line: str, receiver: ReceiverState | None = None) -> RoundTripResult:
    receiver = receiver or ReceiverState()
    stripped = line.strip()
    if not stripped:
        return _reject(receiver, receiver.last_status)

    if not stripped.upper().startswith("RX "):
        return _reject(receiver, "UNKNOWN")

    try:
        encoded = _extract_frame_hex(stripped)
    except ProtocolError:
        return _reject(receiver, "BAD RX")
    return receive_encoded_frame(encoded, receiver)


def receive_encoded_frame(encoded: bytes, receiver: ReceiverState | None = None) -> RoundTripResult:
    receiver = receiver or ReceiverState()
    try:
        frame = _decode_like_receiver_firmware(bytes(encoded))
    except ProtocolError:
        return _reject(receiver, "BAD MAC")

    route_status = _route_reject_status(frame)
    if route_status is not None:
        return _reject(receiver, route_status, frame)

    replay_state = _classify_replay(receiver, frame.sequence)
    if replay_state == "stale":
        return _reject(receiver, "STALE", frame)
    if replay_state == "duplicate":
        return _reject(receiver, "DUP", frame)

    remembered = replace(receiver, last_accepted_sequence=frame.sequence)

    if frame.frame_type in LED_FRAME_TYPES:
        return _apply_led_frame(frame, remembered)
    if frame.frame_type == FrameType.STOP:
        state = replace(remembered, mode=ReceiverMode.IDLE, last_status="STOP")
        return RoundTripResult("STOP", True, state, frame)
    if frame.frame_type in (FrameType.PING, FrameType.STATUS):
        state = replace(remembered, last_status="PING")
        return RoundTripResult("PING", True, state, frame)

    state = replace(remembered, last_status="UNHANDLED")
    return RoundTripResult("UNHANDLED", True, state, frame)


def _payload_for_frame(state: ControllerState, frame_type: FrameType, payload: bytes | None) -> bytes:
    if payload is not None:
        return bytes(payload)
    if frame_type in LED_FRAME_TYPES:
        return state.led_payload()
    return b""


def _extract_frame_hex(line: str) -> bytes:
    first = line.find(" ")
    second = line.find(" ", first + 1) if first >= 0 else -1
    third = line.find(" ", second + 1) if second >= 0 else -1
    if third < 0:
        raise ProtocolError("RX line missing frame hex")
    return hex_to_bytes(line[third + 1 :].strip())


def _decode_like_receiver_firmware(encoded: bytes) -> PropFrame:
    key_id = encoded[4] if len(encoded) > 4 else PROP_KEY_ID
    return decode_frame(encoded, {key_id: SHARED_KEY})


def _route_reject_status(frame: PropFrame) -> str | None:
    if frame.key_id != PROP_KEY_ID:
        return "BAD KEY"
    if frame.source != PROP_RX_DESTINATION:
        return "BAD SRC"
    if frame.destination != PROP_RX_SOURCE:
        return "BAD DST"
    return None


def _classify_replay(receiver: ReceiverState, sequence: int) -> str:
    if receiver.last_accepted_sequence == 0 or sequence > receiver.last_accepted_sequence:
        return "new"
    if sequence == receiver.last_accepted_sequence:
        return "duplicate"
    return "stale"


def _apply_led_frame(frame: PropFrame, receiver: ReceiverState) -> RoundTripResult:
    try:
        parsed = parse_led_payload(frame.payload)
    except ProtocolError:
        return _reject(receiver, "BAD PAYLOAD", frame)

    reconstructed = LedState(
        brightness=int(parsed["brightness"]),
        colors=tuple(parsed["colors"]),  # type: ignore[arg-type]
    )
    mode = ReceiverMode.PREVIEW if frame.frame_type == FrameType.PREVIEW else ReceiverMode.FIRE
    status = "PREVIEW" if frame.frame_type == FrameType.PREVIEW else "FIRE"
    state = replace(
        receiver,
        brightness=reconstructed.brightness,
        colors=reconstructed.colors,
        mode=mode,
        last_status=status,
    )
    return RoundTripResult(status, True, state, frame, reconstructed)


def _reject(receiver: ReceiverState, status: str, frame: PropFrame | None = None) -> RoundTripResult:
    return RoundTripResult(status, False, replace(receiver, last_status=status), frame)


def scenes() -> dict[str, tuple[ControllerState, ReceiverState]]:
    return {
        "01_preview": (ControllerState(FrameType.PREVIEW), ReceiverState()),
        "02_fire": (ControllerState(FrameType.FIRE, sequence=2), ReceiverState()),
        "03_stop": (ControllerState(FrameType.STOP, sequence=3), ReceiverState()),
        "04_ping": (ControllerState(FrameType.PING, sequence=4), ReceiverState()),
        "05_duplicate": (ControllerState(FrameType.PREVIEW, sequence=4), ReceiverState(last_accepted_sequence=4)),
    }


def main() -> None:
    for name, (tx_state, rx_state) in scenes().items():
        encoded = encode_controller_frame(tx_state)
        result = receive_encoded_frame(encoded, rx_state)
        print(
            f"{name}: type={tx_state.frame_type.name} seq={tx_state.sequence} "
            f"status={result.status} accepted={result.accepted} "
            f"state={result.reconstructed}"
        )


if __name__ == "__main__":
    main()
