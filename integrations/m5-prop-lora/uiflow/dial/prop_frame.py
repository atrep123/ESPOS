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
except ImportError:                       # pragma: no cover - MP fallback
    import uhashlib as hashlib            # older MicroPython alias

try:
    import urandom as _urandom            # MicroPython
    def _default_rand32():
        return _urandom.getrandbits(32) & 0xFFFFFFFF
except ImportError:                       # pragma: no cover - CPython fallback
    import os as _os
    def _default_rand32():
        b = _os.urandom(4)
        return (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]


# ---------------------------------------------------------------------------
# [1] WIRE CONSTANTS  (mirror prop_protocol.h)
# ---------------------------------------------------------------------------
MAGIC = 0x504C
VERSION = 2                 # v2: 32-bit epoch in the top 32 bits of the nonce
HEADER_LENGTH = 20
MAC_LENGTH = 12             # HMAC-SHA256 truncated to 12 bytes (LoRa airtime)
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

LED_PAYLOAD_LENGTH = 13
REMOTE_LED_PAYLOAD_LENGTH = 2
PALETTE_HEADER_LENGTH = 3
MAX_PALETTE_COLORS = 8

# The 16-byte HMAC secret baked into the C++ firmware (app_prop_tx.cpp SHARED_KEY).
# Kept here ONLY so the PoC is self-contained + testable. A real deployment would
# load this from secure storage, exactly like the firmware keeps it out of headers.
PROTOTYPE_SHARED_KEY = True
SHARED_KEY = bytes((
    0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF,
))

# Default frame addressing (prop_tx_config.h: PROP_KEY_ID / PROP_SOURCE / PROP_DESTINATION)
DEFAULT_KEY_ID = 1
DEFAULT_SOURCE = 0x11
DEFAULT_DESTINATION = 0x22

# Senders write a constant placeholder for the (receiver-ignored) brightness byte.
LED_PAYLOAD_BRIGHTNESS = 0xFF


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
def _u16(v):
    v &= 0xFFFF
    return bytes(((v >> 8) & 0xFF, v & 0xFF))


def _u32(v):
    v &= 0xFFFFFFFF
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _u64(v):
    v &= 0xFFFFFFFFFFFFFFFF
    return bytes((
        (v >> 56) & 0xFF, (v >> 48) & 0xFF, (v >> 40) & 0xFF, (v >> 32) & 0xFF,
        (v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF,
    ))


# ---------------------------------------------------------------------------
# [4] FRAME ENCODE  -- mirror encodeFrame()
# ---------------------------------------------------------------------------
def encode_frame(frame_type, key_id, source, destination, sequence, nonce,
                 payload=b"", key=SHARED_KEY):
    """Return the full on-air frame bytes: 20-byte header + payload + 12-byte MAC."""
    payload = bytes(payload)
    if len(payload) > MAX_PAYLOAD_LENGTH:
        raise ValueError("payload too long")
    body = (
        _u16(MAGIC)
        + bytes((VERSION, frame_type & 0xFF, key_id & 0xFF,
                 source & 0xFF, destination & 0xFF))
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
    out = bytearray((brightness & 0xFF,))
    for c in colors:
        out += bytes((c[0] & 0xFF, c[1] & 0xFF, c[2] & 0xFF))
    return bytes(out)


def encode_remote_led(mask):
    """2 bytes: [mask (LED3/LED5 bits only), reserved 0]. Reserved bits stripped."""
    return bytes((mask & (REMOTE_LED_BIT_LED3 | REMOTE_LED_BIT_LED5), 0x00))


def encode_palette_payload(palette_rev, fade, colors):
    """3-byte header [rev, fade&1, count] + count x RGB. 1..8 colours."""
    n = len(colors)
    if n < 1 or n > MAX_PALETTE_COLORS:
        raise ValueError("palette must have 1..8 colors")
    out = bytearray((palette_rev & 0xFF, 1 if fade else 0, n))
    for c in colors:
        out += bytes((c[0] & 0xFF, c[1] & 0xFF, c[2] & 0xFF))
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

    def __init__(self, key=SHARED_KEY, key_id=DEFAULT_KEY_ID,
                 source=DEFAULT_SOURCE, destination=DEFAULT_DESTINATION,
                 sequence=1, epoch=None, rand32=_default_rand32):
        self.key = bytes(key)
        self.key_id = key_id
        self.source = source
        self.destination = destination
        self.sequence = sequence
        self._rand32 = rand32
        if epoch is None:
            epoch = rand32() or 1     # nonzero: RX treats 0 as "no session yet"
        self.epoch = epoch & 0xFFFFFFFF

    def _next_nonce(self):
        return ((self.epoch & 0xFFFFFFFF) << 32) | (self._rand32() & 0xFFFFFFFF)

    def encode(self, frame_type, payload=b""):
        """Encode one frame, consuming a sequence number + a fresh nonce."""
        seq = self.sequence
        self.sequence = (self.sequence + 1) & 0xFFFFFFFF
        return encode_frame(frame_type, self.key_id, self.source,
                            self.destination, seq, self._next_nonce(),
                            payload, self.key)

    # Convenience builders returning a ready-to-write UART line ------------
    def preview_line(self, colors, brightness=LED_PAYLOAD_BRIGHTNESS):
        return ff_line(self.encode(PREVIEW, encode_led_payload(brightness, colors)))

    def fire_line(self, colors, brightness=LED_PAYLOAD_BRIGHTNESS):
        return send_line(self.encode(FIRE, encode_led_payload(brightness, colors)))

    def stop_line(self):
        return ff_line(self.encode(STOP))

    def arm_line(self):
        return ff_line(self.encode(ARM))

    def remote_led_line(self, mask):
        return ff_line(self.encode(REMOTE_LED, encode_remote_led(mask)))

    def palette_line(self, palette_rev, fade, colors, track_ack=True):
        frame = self.encode(PALETTE_SET, encode_palette_payload(palette_rev, fade, colors))
        return (send_line if track_ack else ff_line)(frame)
