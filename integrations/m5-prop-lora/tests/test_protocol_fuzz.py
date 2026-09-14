"""Deterministic fuzz tests for the frame parser (roadmap 4.1).

The receiver-side parser is the first thing untrusted radio bytes hit, so it
must never crash and never accept a tampered frame. Three properties are
pinned here with a SEEDED random stream (reproducible, CI-safe):

  1. decode_frame(random bytes) either raises ProtocolError or returns a
     frame -- it never raises anything else and never hangs.
  2. Any single-byte mutation of a valid authenticated frame is rejected
     (magic/version/length checks or MAC), or -- if it decodes -- decodes to
     the original frame (a mutation of ignorable bytes must not silently
     change the meaning; with HMAC over the full frame there are none).
  3. Truncations and extensions of a valid frame are always rejected.
"""

import random
import unittest

from shared.protocol.protocol import (
    FrameType,
    ProtocolError,
    PropFrame,
    decode_frame,
    encode_frame,
)

KEYS = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
SEED = 0x50524F50  # "PROP" -- fixed so every run fuzzes the same corpus
RANDOM_CASES = 5000
MAX_RANDOM_LENGTH = 96


def _valid_fire_frame() -> bytes:
    frame = PropFrame(
        frame_type=FrameType.FIRE,
        key_id=1,
        source=0x11,
        destination=0x22,
        sequence=1234,
        nonce=0xA1B2C3D4E5F60708,
        payload=bytes([1, 2, 3, 4]),
    )
    return encode_frame(frame, KEYS)


class RandomBytesFuzzTests(unittest.TestCase):
    def test_random_bytes_never_crash_and_never_authenticate(self):
        rng = random.Random(SEED)
        decoded_count = 0
        for _ in range(RANDOM_CASES):
            length = rng.randrange(0, MAX_RANDOM_LENGTH + 1)
            blob = bytes(rng.randrange(256) for _ in range(length))
            try:
                decode_frame(blob, KEYS)
            except ProtocolError:
                continue
            decoded_count += 1
        # A random blob forging a valid 12-byte truncated HMAC-SHA256 tag
        # (MAC_LENGTH) is ~2^-96 per attempt; any acceptance here means the
        # MAC gate is broken.
        self.assertEqual(decoded_count, 0)


class MutationFuzzTests(unittest.TestCase):
    def test_every_single_byte_mutation_is_rejected(self):
        rng = random.Random(SEED)
        encoded = _valid_fire_frame()
        original = decode_frame(encoded, KEYS)
        for index in range(len(encoded)):
            for _ in range(8):  # 8 random substitute values per position
                substitute = rng.randrange(256)
                if substitute == encoded[index]:
                    continue
                mutated = bytearray(encoded)
                mutated[index] = substitute
                with self.subTest(index=index, substitute=substitute):
                    try:
                        decoded = decode_frame(bytes(mutated), KEYS)
                    except ProtocolError:
                        continue
                    self.fail(
                        f"mutation at byte {index} ({encoded[index]:#04x}->"
                        f"{substitute:#04x}) was accepted as {decoded!r}"
                    )
        # Sanity: the unmutated frame still authenticates.
        self.assertEqual(decode_frame(encoded, KEYS), original)

    def test_truncations_and_extensions_are_rejected(self):
        encoded = _valid_fire_frame()
        for cut in range(len(encoded)):
            with self.subTest(kind="truncation", length=cut):
                with self.assertRaises(ProtocolError):
                    decode_frame(encoded[:cut], KEYS)
        for extra in (b"\x00", b"\xff", b"\x00\x00\x00\x00"):
            with self.subTest(kind="extension", extra=extra):
                with self.assertRaises(ProtocolError):
                    decode_frame(encoded + extra, KEYS)


if __name__ == "__main__":
    unittest.main()
