from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import hmac
import struct


MAGIC = 0x504C
VERSION = 2  # v2: 32-bit epoch in the top 32 bits of the nonce (mirrors prop_protocol.h)
MAX_PAYLOAD_LENGTH = 64
REPLAY_WINDOW_BITS = 32
LED_PAYLOAD_LENGTH = 13
MAC_LENGTH = 12
HEADER = struct.Struct(">HBBBBBIQB")
HEADER_LENGTH = HEADER.size
MAX_FRAME_LENGTH = HEADER_LENGTH + MAX_PAYLOAD_LENGTH + MAC_LENGTH


class ProtocolError(ValueError):
    pass


class FrameType(IntEnum):
    PING = 1
    STATUS = 2
    PREVIEW = 3
    FIRE = 4
    STOP = 5
    ACK = 6
    ERROR = 7
    PALETTE_SET = 8
    ARM = 9
    LED_COLOR_SET = 10
    REMOTE_LED = 11
    PROP_ACTION = 12


@dataclass(frozen=True)
class PropFrame:
    frame_type: FrameType
    key_id: int
    source: int
    destination: int
    sequence: int
    nonce: int
    payload: bytes = b""


class FrameReplayWindow:
    """Mirror of the firmware receiver dedup/replay logic (safety_logic.h ReplayFilter /
    prop_rx.cpp classifyReplay): a single 32-bit sliding window keyed off the per-boot
    epoch (the top 32 bits of the nonce). Any different epoch (e.g. a Dial reboot) resets
    the window. ``classify(nonce, sequence)`` returns ``"new"`` (accept), ``"duplicate"``,
    or ``"stale"`` -- matching the receiver so the sim/tests model the real arm->fire flow.
    """

    def __init__(self) -> None:
        self._epoch: int | None = None
        self._base = 0
        self._mask = 0

    def classify(self, nonce: int, sequence: int) -> str:
        epoch = (int(nonce) >> 32) & 0xFFFFFFFF
        sequence = int(sequence) & 0xFFFFFFFF
        # Any different epoch is a fresh session -> reset the window and accept.
        if epoch != self._epoch:
            self._epoch = epoch
            self._base = sequence
            self._mask = 0
            return "new"
        if sequence > self._base:
            shift = sequence - self._base
            if shift > REPLAY_WINDOW_BITS:
                self._mask = 0
            elif shift == REPLAY_WINDOW_BITS:
                self._mask = 1 << (REPLAY_WINDOW_BITS - 1)
            else:
                self._mask = ((self._mask << shift) | (1 << (shift - 1))) & 0xFFFFFFFF
            self._base = sequence
            return "new"
        if sequence == self._base:
            return "duplicate"
        diff = self._base - sequence
        if diff > REPLAY_WINDOW_BITS:
            return "stale"
        seen_bit = 1 << (diff - 1)
        if self._mask & seen_bit:
            return "duplicate"
        self._mask |= seen_bit
        return "new"


def encode_frame(frame: PropFrame, keys: dict[int, bytes]) -> bytes:
    payload = bytes(frame.payload)
    if len(payload) > MAX_PAYLOAD_LENGTH:
        raise ProtocolError(f"payload exceeds {MAX_PAYLOAD_LENGTH} bytes")
    try:
        frame_type = FrameType(frame.frame_type)
    except ValueError as exc:
        raise ProtocolError("bad frame type") from exc
    key_id = _uint(frame.key_id, 0xFF, "key id")
    source = _uint(frame.source, 0xFF, "source")
    destination = _uint(frame.destination, 0xFF, "destination")
    sequence = _uint(frame.sequence, 0xFFFFFFFF, "sequence")
    nonce = _uint(frame.nonce, 0xFFFFFFFFFFFFFFFF, "nonce")
    key = _key_for(key_id, keys)
    body = HEADER.pack(
        MAGIC,
        VERSION,
        int(frame_type),
        key_id,
        source,
        destination,
        sequence,
        nonce,
        len(payload),
    ) + payload
    return body + _mac(body, key)


def decode_frame(encoded: bytes, keys: dict[int, bytes]) -> PropFrame:
    if len(encoded) < HEADER_LENGTH + MAC_LENGTH:
        raise ProtocolError("frame too short")
    if len(encoded) > MAX_FRAME_LENGTH:
        raise ProtocolError("frame too long")
    body = encoded[:-MAC_LENGTH]
    supplied_mac = encoded[-MAC_LENGTH:]
    magic, version, frame_type, key_id, source, destination, sequence, nonce, payload_len = HEADER.unpack(
        body[:HEADER_LENGTH]
    )
    if magic != MAGIC:
        raise ProtocolError("bad magic")
    if version != VERSION:
        raise ProtocolError("bad version")
    if payload_len > MAX_PAYLOAD_LENGTH:
        raise ProtocolError("payload too long")
    expected_len = HEADER_LENGTH + payload_len
    if len(body) != expected_len:
        raise ProtocolError("payload length mismatch")
    key = _key_for(key_id, keys)
    expected_mac = _mac(body, key)
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise ProtocolError("bad MAC")
    try:
        decoded_type = FrameType(frame_type)
    except ValueError as exc:
        raise ProtocolError("bad frame type") from exc
    return PropFrame(
        frame_type=decoded_type,
        key_id=key_id,
        source=source,
        destination=destination,
        sequence=sequence,
        nonce=nonce,
        payload=body[HEADER_LENGTH:],
    )


def bytes_to_hex(data: bytes) -> str:
    return data.hex().upper()


def hex_to_bytes(text: str) -> bytes:
    clean = text.strip()
    if len(clean) % 2:
        raise ProtocolError("hex text has odd length")
    try:
        return bytes.fromhex(clean)
    except ValueError as exc:
        raise ProtocolError("invalid hex text") from exc


def encode_led_payload(brightness: int, colors: list[tuple[int, int, int]]) -> bytes:
    if len(colors) != 4:
        raise ProtocolError("exactly four LED colors are required")
    values = [_byte(brightness, "brightness")]
    for index, color in enumerate(colors, start=1):
        if len(color) != 3:
            raise ProtocolError(f"LED {index} color must be RGB")
        values.extend(_byte(component, f"LED {index} color") for component in color)
    return bytes(values)


def parse_led_payload(payload: bytes) -> dict[str, object]:
    if len(payload) != LED_PAYLOAD_LENGTH:
        raise ProtocolError(f"LED payload must be {LED_PAYLOAD_LENGTH} bytes")
    colors = []
    for offset in range(1, LED_PAYLOAD_LENGTH, 3):
        colors.append(tuple(payload[offset:offset + 3]))
    return {"brightness": payload[0], "colors": colors}


# RemoteLed (FrameType 11): ON-only 2-byte LED bitmask, mirrors prop_protocol.h. Reserved bits
# are stripped on both encode and parse. Separate from encode/parse_led_payload by design.
REMOTE_LED_PAYLOAD_LENGTH = 2
REMOTE_LED_BIT_LED3 = 0x01
REMOTE_LED_BIT_LED5 = 0x02


def encode_remote_led(mask: int) -> bytes:
    mask = _byte(mask, "remote LED mask") & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5)
    return bytes((mask, 0x00))  # byte 1 reserved


def parse_remote_led(payload: bytes) -> int:
    if len(payload) != REMOTE_LED_PAYLOAD_LENGTH:
        raise ProtocolError(f"remote LED payload must be {REMOTE_LED_PAYLOAD_LENGTH} bytes")
    return payload[0] & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5)


PROP_ACTION_PAYLOAD_LENGTH = 6
PROP_ACTION_BLUE_SET = 1
PROP_ACTION_BARREL_EFFECT = 2


def _prop_action_value_valid(action: int, value: int) -> bool:
    if action == PROP_ACTION_BLUE_SET:
        return value in (0, 1)
    if action == PROP_ACTION_BARREL_EFFECT:
        return value == 0
    return False


def encode_prop_action_payload(action: int, value: int, event_id: int) -> bytes:
    action = _byte(action, "prop action")
    value = _byte(value, "prop action value")
    event_id = _uint(event_id, 0xFFFFFFFF, "event id")
    if not _prop_action_value_valid(action, value):
        if action == PROP_ACTION_BLUE_SET:
            raise ProtocolError("blue set value must be 0 or 1")
        raise ProtocolError("prop action is not supported")
    return bytes((action, value)) + struct.pack(">I", event_id)


def parse_prop_action_payload(payload: bytes) -> dict[str, int]:
    if len(payload) != PROP_ACTION_PAYLOAD_LENGTH:
        raise ProtocolError(f"prop action payload must be {PROP_ACTION_PAYLOAD_LENGTH} bytes")
    action = payload[0]
    value = payload[1]
    event_id = struct.unpack(">I", payload[2:6])[0]
    if not _prop_action_value_valid(action, value):
        if action == PROP_ACTION_BLUE_SET:
            raise ProtocolError("blue set value must be 0 or 1")
        raise ProtocolError("prop action is not supported")
    return {"action": action, "value": value, "event_id": event_id}


# PaletteSet (FrameType 8): byte-identical mirror of prop_protocol.h encodePalettePayload /
# parsePalettePayload. Payload = 3-byte header [paletteRev, fade&1, count] followed by `count`
# RGB triples. 1..8 colours; count 0 or >8 is rejected; width must be exactly 3 + 3*count.
# Bit 0 of the fade byte is the only meaningful bit -- reserved bits are stripped on BOTH ends.
MAX_PALETTE_COLORS = 8
PALETTE_HEADER_LENGTH = 3


def encode_palette_payload(
    palette_rev: int,
    fade: bool,
    colors: list[tuple[int, int, int]],
) -> bytes:
    if not 1 <= len(colors) <= MAX_PALETTE_COLORS:
        raise ProtocolError(f"palette must have 1..{MAX_PALETTE_COLORS} colors")
    values = [
        _byte(palette_rev, "palette rev"),
        1 if fade else 0,  # only bit 0 is meaningful; reserved bits stay 0
        len(colors),
    ]
    for index, color in enumerate(colors, start=1):
        if len(color) != 3:
            raise ProtocolError(f"palette color {index} must be RGB")
        values.extend(_byte(component, f"palette color {index}") for component in color)
    return bytes(values)


def parse_palette_payload(payload: bytes) -> dict[str, object]:
    if len(payload) < PALETTE_HEADER_LENGTH:
        raise ProtocolError(f"palette payload must be at least {PALETTE_HEADER_LENGTH} bytes")
    count = payload[2]
    if count == 0 or count > MAX_PALETTE_COLORS:
        raise ProtocolError(f"palette count must be 1..{MAX_PALETTE_COLORS}")
    if len(payload) != PALETTE_HEADER_LENGTH + 3 * count:
        raise ProtocolError("palette payload length mismatch")
    colors = []
    for i in range(count):
        offset = PALETTE_HEADER_LENGTH + 3 * i
        colors.append(tuple(payload[offset:offset + 3]))
    return {
        "palette_rev": payload[0],
        "fade": (payload[1] & 0x01) != 0,  # strip reserved bits, mirror C++
        "colors": colors,
    }


def _key_for(key_id: int, keys: dict[int, bytes]) -> bytes:
    key = keys.get(key_id)
    if key is None:
        raise ProtocolError("unknown key id")
    if len(key) < 16:
        raise ProtocolError("key must be at least 16 bytes")
    return key


def _mac(body: bytes, key: bytes) -> bytes:
    return hmac.new(key, body, hashlib.sha256).digest()[:MAC_LENGTH]


def _byte(value: int, name: str) -> int:
    value = int(value)
    if value < 0 or value > 0xFF:
        raise ProtocolError(f"{name} must fit in one byte")
    return value


def _uint(value: int, max_value: int, name: str) -> int:
    value = int(value)
    if value < 0 or value > max_value:
        raise ProtocolError(f"{name} must be between 0 and {max_value}")
    return value
