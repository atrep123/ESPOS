# prop_frame.py — byte-exact MicroPython mirror of the prop LoRa wire format.
#
# PURPOSE (UIFlow2 Dial port, protocol-parity PoC)
# ------------------------------------------------
# This is the "hard 20%" of a Dial-side UIFlow2 port: the authenticated frame
# encoder. It produces the EXACT same bytes (and the exact same "FF <HEX>\n"
# UART line) that the C++ Dial firmware sends to its LoRa modem, so a UIFlow2
# MicroPython app could drive the existing C++ modem + DinMeter unchanged.
#
# Source of truth it mirrors, field for field:
#   - shared/protocol/prop_protocol.h   (C++ encodeFrame / encodeLedPayload / ...)
#   - shared/protocol/protocol.py       (Python reference, tested vs the C++ header)
#   - firmware/dial-tx/.../app_prop_tx.cpp  (SHARED_KEY, addressing, nonce, "FF " line)
#
# Parity is proven byte-for-byte by tests/test_uiflow_prop_frame_parity.py.
#
# MICROPYTHON NOTES
#   * Uses hashlib.sha256 from the MP core (present in UIFlow MicroPython >= 2.x).
#   * HMAC is HAND-ROLLED here on purpose. The MicroPython `hmac` stdlib module
#     relies on a .copy() method on the hash object that the M5 hashlib build
#     does not expose (AttributeError) -- so we never import `hmac`. We only
#     create fresh sha256() objects, which always works.
#   * All multi-byte integers are packed manually (big-endian, MSB first) to
#     avoid any `struct`-format portability differences between MP builds.

try:
    import hashlib  # CPython + most MicroPython builds
except ImportError:  # pragma: no cover - MP fallback
    import uhashlib as hashlib  # older MicroPython alias

try:
    import urandom as _urandom  # MicroPython

    def _default_rand32():
        return _urandom.getrandbits(32) & 0xFFFFFFFF
except ImportError:  # pragma: no cover - CPython fallback
    import os as _os

    def _default_rand32():
        b = _os.urandom(4)
        return (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]


# ---------------------------------------------------------------------------
# [1] WIRE CONSTANTS  (mirror prop_protocol.h)
# ---------------------------------------------------------------------------
MAGIC = 0x504C
VERSION = 2  # v2: 32-bit epoch in the top 32 bits of the nonce
HEADER_LENGTH = 20
MAC_LENGTH = 12  # HMAC-SHA256 truncated to 12 bytes (LoRa airtime)
MAX_PAYLOAD_LENGTH = 64
SHA256_BLOCK = 64

# FrameType (prop_protocol.h enum values)
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

# RemoteLed payload bits
REMOTE_LED_BIT_LED3 = 0x01
REMOTE_LED_BIT_LED5 = 0x02

VALID_FRAME_TYPES = (
    PING,
    STATUS,
    PREVIEW,
    FIRE,
    STOP,
    ACK,
    ERROR,
    PALETTE_SET,
    ARM,
    LED_COLOR_SET,
    REMOTE_LED,
)

LED_PAYLOAD_LENGTH = 13
REMOTE_LED_PAYLOAD_LENGTH = 2
PALETTE_HEADER_LENGTH = 3
MAX_PALETTE_COLORS = 8
MIN_RUNTIME_KEY_BYTES = 16
MAX_RUNTIME_KEY_BYTES = 64

# HMAC key material is provisioned out-of-band by /flash/prop_key.py.
# The runtime intentionally has no compiled prototype key and no implicit fallback.
# Dry-smoke bundles may mark ALLOW_PROTOTYPE_SHARED_KEY=True in prop_key.py, but they
# must still provide the key explicitly; production bundle verification rejects that
# marker before upload.


def _hex_nibble(ch):
    code = ord(ch)
    if 48 <= code <= 57:
        return code - 48
    if 65 <= code <= 70:
        return code - 55
    if 97 <= code <= 102:
        return code - 87
    raise ValueError("shared key hex contains a non-hex character")


def _key_from_hex(value):
    text = "".join(str(value).strip().replace(":", " ").split())
    if len(text) % 2:
        raise ValueError("shared key hex must have an even number of digits")
    out = bytearray()
    for index in range(0, len(text), 2):
        out.append((_hex_nibble(text[index]) << 4) | _hex_nibble(text[index + 1]))
    return bytes(out)


def _validate_shared_key(key, source):
    key = bytes(key)
    if len(key) < MIN_RUNTIME_KEY_BYTES:
        raise RuntimeError(f"{source} must provide at least 16 bytes of HMAC key material")
    if len(key) > MAX_RUNTIME_KEY_BYTES:
        raise RuntimeError(f"{source} must provide at most 64 bytes of HMAC key material")
    return key


def _is_known_dry_smoke_key(key):
    return key == bytes(range(0x00, 0x100, 0x11))[:16]


def _load_shared_key():
    try:
        import prop_key  # type: ignore
    except ImportError as exc:
        raise RuntimeError("prop_key.py did not provide SHARED_KEY or SHARED_KEY_HEX") from exc

    allow_prototype = getattr(prop_key, "ALLOW_PROTOTYPE_SHARED_KEY", False)
    if not isinstance(allow_prototype, bool):
        raise RuntimeError("prop_key.py ALLOW_PROTOTYPE_SHARED_KEY must be True or False")
    if hasattr(prop_key, "SHARED_KEY"):
        raise RuntimeError("prop_key.py must not define SHARED_KEY; use SHARED_KEY_HEX")
    key_hex = getattr(prop_key, "SHARED_KEY_HEX", None)
    if key_hex is None:
        raise RuntimeError("prop_key.py did not provide SHARED_KEY_HEX")
    key = _key_from_hex(key_hex)

    key = _validate_shared_key(key, "prop_key.py")
    if _is_known_dry_smoke_key(key) and not allow_prototype:
        raise RuntimeError(
            "prop_key.py uses the dry-smoke HMAC key without explicit ALLOW_PROTOTYPE_SHARED_KEY"
        )
    return key, allow_prototype


SHARED_KEY, DRY_SMOKE_KEY_ACTIVE = _load_shared_key()

# Default frame addressing (prop_tx_config.h: PROP_KEY_ID / PROP_SOURCE / PROP_DESTINATION)
DEFAULT_KEY_ID = 1
DEFAULT_SOURCE = 0x11
DEFAULT_DESTINATION = 0x22

# Senders write a constant placeholder for the (receiver-ignored) brightness byte.
LED_PAYLOAD_BRIGHTNESS = 0xFF

# Mirrors firmware/dial-tx/.../prop_tx_config.h: FF_REDUNDANCY and
# FF_JITTER_MIN_MS. The Python side keeps the line generation deterministic; callers
# that have a clock may sleep between the returned lines.
FIRE_BURST_COPIES = 3
FIRE_BURST_GAP_MS = 18
ARM_BURST_COPIES = 2
STOP_RETRY_COPIES = 3
STOP_RETRY_TIMEOUT_MS = 120
STOP_RETRY_GAP_MS = 20
REMOTE_LED_BURST_COPIES = 2


# ---------------------------------------------------------------------------
# [2] HMAC-SHA256 (hand-rolled, truncated)  -- mirrors hmacSha256Truncated()
# ---------------------------------------------------------------------------
def _sha256(data):
    return hashlib.sha256(bytes(data)).digest()


def _xor_pad(key, pad):
    out = bytearray(len(key))
    for i in range(len(key)):
        out[i] = key[i] ^ pad
    return bytes(out)


def hmac_sha256(key, msg):
    """Full 32-byte HMAC-SHA256(key, msg). Standard RFC 2104, no stdlib hmac."""
    key = bytes(key)
    if len(key) > SHA256_BLOCK:
        key = _sha256(key)
    if len(key) < SHA256_BLOCK:
        key = key + bytes(SHA256_BLOCK - len(key))
    inner = _sha256(_xor_pad(key, 0x36) + bytes(msg))
    return _sha256(_xor_pad(key, 0x5C) + inner)


def _mac(body, key):
    return hmac_sha256(key, body)[:MAC_LENGTH]


# ---------------------------------------------------------------------------
# [3] BIG-ENDIAN PACKING  -- mirror putU16/putU32/putU64
# ---------------------------------------------------------------------------
def _uint(v, max_value, name):
    v = int(v)
    if v < 0 or v > max_value:
        raise ValueError(f"{name} must be between 0 and {max_value}")
    return v


def _byte(v, name):
    return _uint(v, 0xFF, name)


def _u16(v):
    v = _uint(v, 0xFFFF, "uint16")
    return bytes(((v >> 8) & 0xFF, v & 0xFF))


def _u32(v):
    v = _uint(v, 0xFFFFFFFF, "uint32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _u64(v):
    v = _uint(v, 0xFFFFFFFFFFFFFFFF, "uint64")
    return bytes(
        (
            (v >> 56) & 0xFF,
            (v >> 48) & 0xFF,
            (v >> 40) & 0xFF,
            (v >> 32) & 0xFF,
            (v >> 24) & 0xFF,
            (v >> 16) & 0xFF,
            (v >> 8) & 0xFF,
            v & 0xFF,
        )
    )


# ---------------------------------------------------------------------------
# [4] FRAME ENCODE  -- mirror encodeFrame()
# ---------------------------------------------------------------------------
def encode_frame(
    frame_type, key_id, source, destination, sequence, nonce, payload=b"", key=SHARED_KEY
):
    """Return the full on-air frame bytes: 20-byte header + payload + 12-byte MAC."""
    key = _validate_shared_key(key, "explicit key")
    payload = bytes(payload)
    if len(payload) > MAX_PAYLOAD_LENGTH:
        raise ValueError("payload too long")
    frame_type = int(frame_type)
    if frame_type not in VALID_FRAME_TYPES:
        raise ValueError("bad frame type")
    key_id = _byte(key_id, "key id")
    source = _byte(source, "source")
    destination = _byte(destination, "destination")
    sequence = _uint(sequence, 0xFFFFFFFF, "sequence")
    nonce = _uint(nonce, 0xFFFFFFFFFFFFFFFF, "nonce")
    body = (
        _u16(MAGIC)
        + bytes((VERSION, frame_type, key_id, source, destination))
        + _u32(sequence)
        + _u64(nonce)
        + bytes((len(payload),))
        + payload
    )
    return body + _mac(body, key)


# ---------------------------------------------------------------------------
# [5] PAYLOAD ENCODERS  -- mirror encodeLedPayload / encodeRemoteLedPayload / encodePalettePayload
# ---------------------------------------------------------------------------
def encode_led_payload(brightness, colors):
    """13 bytes: brightness + 4x RGB. `colors` must be exactly four (r,g,b)."""
    if len(colors) != 4:
        raise ValueError("exactly four LED colors required")
    out = bytearray((_byte(brightness, "brightness"),))
    for index, c in enumerate(colors, 1):
        if len(c) != 3:
            raise ValueError(f"LED {index} color must be RGB")
        out += bytes(
            (
                _byte(c[0], "LED color"),
                _byte(c[1], "LED color"),
                _byte(c[2], "LED color"),
            )
        )
    return bytes(out)


def encode_remote_led(mask):
    """2 bytes: [mask (LED3/LED5 bits only), reserved 0]. Reserved bits stripped."""
    mask = _byte(mask, "remote LED mask")
    return bytes((mask & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5), 0x00))


def encode_palette_payload(palette_rev, fade, colors):
    """3-byte header [rev, fade&1, count] + count x RGB. 1..8 colours."""
    n = len(colors)
    if n < 1 or n > MAX_PALETTE_COLORS:
        raise ValueError("palette must have 1..8 colors")
    out = bytearray((_byte(palette_rev, "palette rev"), 1 if fade else 0, n))
    for index, c in enumerate(colors, 1):
        if len(c) != 3:
            raise ValueError(f"palette color {index} must be RGB")
        out += bytes(
            (
                _byte(c[0], "palette color"),
                _byte(c[1], "palette color"),
                _byte(c[2], "palette color"),
            )
        )
    return bytes(out)


# ---------------------------------------------------------------------------
# [6] HEX + UART LINE  -- mirror bytesToHex() + the "FF "/"SEND " line builders
# ---------------------------------------------------------------------------
def to_hex(data):
    """Uppercase hex, matching bytesToHex() / protocol.bytes_to_hex()."""
    return "".join("%02X" % b for b in data)


def ff_line(frame_bytes):
    """Fire-and-forget UART line (Preview/Fire/Stop/Arm/RemoteLed): 'FF <HEX>\\n'."""
    return "FF " + to_hex(frame_bytes) + "\n"


def send_line(frame_bytes):
    """Ack-tracked UART line (the C++ 'SEND ' path): 'SEND <HEX>\\n'."""
    return "SEND " + to_hex(frame_bytes) + "\n"


# ---------------------------------------------------------------------------
# [7] STATEFUL SENDER  -- mirrors the Dial's sequence++ + make_session_nonce()
# ---------------------------------------------------------------------------
class PropSender:
    """Mirrors the Dial's per-frame bookkeeping so a UIFlow app stays a one-liner.

    sequence is a monotonic counter (the firmware persists it in NVS); nonce is
    (epoch << 32) | rand32, where epoch is a per-boot nonzero random 32-bit value
    (app_prop_tx.cpp make_session_nonce + the per-boot RANDOM epoch).
    """

    def __init__(
        self,
        key=SHARED_KEY,
        key_id=DEFAULT_KEY_ID,
        source=DEFAULT_SOURCE,
        destination=DEFAULT_DESTINATION,
        sequence=1,
        epoch=None,
        rand32=_default_rand32,
    ):
        self.key = _validate_shared_key(key, "explicit key")
        self.key_id = key_id
        self.source = source
        self.destination = destination
        self.sequence = sequence
        self._rand32 = rand32
        if epoch is None:
            epoch = rand32() or 1  # nonzero: RX treats 0 as "no session yet"
        self.epoch = epoch & 0xFFFFFFFF

    def _next_nonce(self):
        return ((self.epoch & 0xFFFFFFFF) << 32) | (self._rand32() & 0xFFFFFFFF)

    def encode(self, frame_type, payload=b""):
        """Encode one frame, consuming a sequence number + a fresh nonce."""
        seq = self.sequence
        self.sequence = (self.sequence + 1) & 0xFFFFFFFF
        return encode_frame(
            frame_type,
            self.key_id,
            self.source,
            self.destination,
            seq,
            self._next_nonce(),
            payload,
            self.key,
        )

    # Convenience builders returning a ready-to-write UART line ------------
    def preview_line(self, colors, brightness=LED_PAYLOAD_BRIGHTNESS):
        return ff_line(self.encode(PREVIEW, encode_led_payload(brightness, colors)))

    def fire_line(self, colors, brightness=LED_PAYLOAD_BRIGHTNESS):
        """Legacy ack-tracked FIRE line. Production firmware uses fire_burst_lines()."""
        return send_line(self.encode(FIRE, encode_led_payload(brightness, colors)))

    def fire_burst_lines(self, colors, copies=FIRE_BURST_COPIES, brightness=LED_PAYLOAD_BRIGHTNESS):
        copies = int(copies)
        if copies < 1:
            raise ValueError("fire burst copies must be >= 1")
        line = ff_line(self.encode(FIRE, encode_led_payload(brightness, colors)))
        return [line for _ in range(copies)]

    def stop_line(self):
        return send_line(self.encode(STOP))

    def stop_lines(self, copies=STOP_RETRY_COPIES):
        copies = int(copies)
        if copies < 1:
            raise ValueError("stop retry copies must be >= 1")
        line = self.stop_line()
        return [line for _ in range(copies)]

    def arm_line(self):
        return ff_line(self.encode(ARM))

    def arm_lines(self, copies=ARM_BURST_COPIES):
        copies = int(copies)
        if copies < 1:
            raise ValueError("arm burst copies must be >= 1")
        line = self.arm_line()
        return [line for _ in range(copies)]

    def remote_led_line(self, mask):
        return ff_line(self.encode(REMOTE_LED, encode_remote_led(mask)))

    def remote_led_lines(
        self,
        mask,
        colors=None,
        palette_rev=1,
        fade=False,
        copies=REMOTE_LED_BURST_COPIES,
    ):
        copies = int(copies)
        if copies < 1:
            raise ValueError("remote LED burst copies must be >= 1")
        line = self.remote_led_line(mask)
        return [line for _ in range(copies)]

    def palette_line(self, palette_rev, fade, colors, track_ack=True):
        frame = self.encode(PALETTE_SET, encode_palette_payload(palette_rev, fade, colors))
        return (send_line if track_ack else ff_line)(frame)
