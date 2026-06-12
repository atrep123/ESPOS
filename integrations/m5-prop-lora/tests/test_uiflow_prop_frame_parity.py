"""Byte-exact parity: uiflow/dial/prop_frame.py  vs  shared/protocol/protocol.py.

prop_frame.py is the MicroPython encoder for a UIFlow2 Dial port. protocol.py is the
Python reference, itself proven byte-identical to the C++ prop_protocol.h by
test_protocol_roundtrip_sim.py. So if prop_frame matches protocol.py here, it matches
the C++ firmware -- and the existing C++ modem + DinMeter would accept its frames
unchanged. The decode_frame round-trips additionally exercise the real receiver-side
HMAC verifier against our hand-rolled HMAC.
"""

from __future__ import annotations

import hashlib
import hmac as std_hmac
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "uiflow" / "dial"))
PROP_PROTOCOL_H = ROOT / "shared" / "protocol" / "prop_protocol.h"

from shared.protocol import protocol as proto  # noqa: E402
import prop_frame  # noqa: E402  (flat module, as it sits on the MicroPython device)


KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
KEYS = {1: KEY}

ALL_TYPES = [
    prop_frame.PING,
    prop_frame.STATUS,
    prop_frame.PREVIEW,
    prop_frame.FIRE,
    prop_frame.STOP,
    prop_frame.ACK,
    prop_frame.ERROR,
    prop_frame.PALETTE_SET,
    prop_frame.ARM,
    prop_frame.LED_COLOR_SET,
    prop_frame.REMOTE_LED,
]

LED_COLORS = [(0, 0, 0), (1, 2, 3), (254, 255, 128), (17, 34, 51)]


def _vectors():
    """(frame_type, key_id, source, destination, sequence, nonce, payload) tuples."""
    led = proto.encode_led_payload(0xFF, LED_COLORS)
    remote = proto.encode_remote_led(prop_frame.REMOTE_LED_BIT_LED3)
    pal1 = proto.encode_palette_payload(7, True, [(10, 20, 30)])
    pal8 = proto.encode_palette_payload(
        255, False, [(i, (i * 2) & 0xFF, (i * 3) & 0xFF) for i in range(8)]
    )
    vecs = []
    # every frame type, empty payload, mid-range addressing
    for t in ALL_TYPES:
        vecs.append((t, 1, 0x11, 0x22, 42, 0x0102030405060708, b""))
    # realistic payload-bearing frames
    vecs.append((prop_frame.PREVIEW, 1, 0x11, 0x22, 1, (0xABCD1234 << 32) | 0x99, led))
    vecs.append((prop_frame.FIRE, 1, 0x11, 0x22, 2, (0xABCD1234 << 32) | 0x9A, led))
    vecs.append((prop_frame.REMOTE_LED, 1, 0x11, 0x22, 3, 7, remote))
    vecs.append((prop_frame.PALETTE_SET, 1, 0x11, 0x22, 4, 8, pal1))
    vecs.append((prop_frame.PALETTE_SET, 1, 0x11, 0x22, 5, 9, pal8))
    # edge values: min/max sequence + nonce, empty + max payload
    vecs.append((prop_frame.PING, 1, 0, 0, 0, 0, b""))
    vecs.append((prop_frame.STOP, 1, 0xFF, 0xFF, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, b""))
    vecs.append((prop_frame.STATUS, 1, 0x11, 0x22, 123456, 0x00000001_00000000, bytes(range(64))))
    return vecs


def _ref(v):
    t, key_id, src, dst, seq, nonce, payload = v
    frame = proto.PropFrame(
        frame_type=proto.FrameType(t),
        key_id=key_id,
        source=src,
        destination=dst,
        sequence=seq,
        nonce=nonce,
        payload=payload,
    )
    return proto.encode_frame(frame, KEYS)


def _mine(v):
    t, key_id, src, dst, seq, nonce, payload = v
    return prop_frame.encode_frame(t, key_id, src, dst, seq, nonce, payload, KEY)


class FrameParity(unittest.TestCase):
    def test_shared_key_matches(self):
        self.assertEqual(prop_frame.SHARED_KEY, KEY)

    def test_encode_frame_byte_exact(self):
        for v in _vectors():
            with self.subTest(vector=v[:6]):
                self.assertEqual(_mine(v), _ref(v))

    def test_decode_accepts_our_frames(self):
        # The receiver-side verifier (same HMAC) must accept every frame we encode.
        for v in _vectors():
            t, key_id, src, dst, seq, nonce, payload = v
            dec = proto.decode_frame(_mine(v), KEYS)  # raises ProtocolError on bad MAC
            self.assertEqual(int(dec.frame_type), t)
            self.assertEqual(dec.sequence, seq)
            self.assertEqual(dec.nonce, nonce)
            self.assertEqual(bytes(dec.payload), payload)

    def test_max_payload_and_overflow(self):
        ok = _mine((prop_frame.STATUS, 1, 0x11, 0x22, 1, 1, bytes(64)))
        self.assertEqual(proto.decode_frame(ok, KEYS).payload, bytes(64))
        with self.assertRaises(ValueError):
            prop_frame.encode_frame(prop_frame.STATUS, 1, 0x11, 0x22, 1, 1, bytes(65), KEY)

    def test_encode_frame_rejects_out_of_range_header_fields(self):
        cases = [
            ("frame_type", dict(frame_type=0)),
            ("frame_type", dict(frame_type=255)),
            ("key_id", dict(key_id=-1)),
            ("key_id", dict(key_id=256)),
            ("source", dict(source=-1)),
            ("source", dict(source=256)),
            ("destination", dict(destination=-1)),
            ("destination", dict(destination=256)),
            ("sequence", dict(sequence=-1)),
            ("sequence", dict(sequence=0x1_0000_0000)),
            ("nonce", dict(nonce=-1)),
            ("nonce", dict(nonce=0x1_0000_0000_0000_0000)),
        ]
        base = {
            "frame_type": prop_frame.PING,
            "key_id": 1,
            "source": 0x11,
            "destination": 0x22,
            "sequence": 1,
            "nonce": 1,
            "payload": b"",
            "key": KEY,
        }
        for name, override in cases:
            with self.subTest(name=name, override=override):
                values = dict(base, **override)
                with self.assertRaises(ValueError):
                    prop_frame.encode_frame(**values)


class HmacParity(unittest.TestCase):
    def test_handrolled_hmac_matches_stdlib(self):
        for msg in [
            b"",
            b"\x00",
            b"abc",
            bytes(range(64)),
            bytes(range(200)),
            b"x" * 64,
            b"y" * 65,
        ]:
            with self.subTest(n=len(msg)):
                self.assertEqual(
                    prop_frame.hmac_sha256(KEY, msg),
                    std_hmac.new(KEY, msg, hashlib.sha256).digest(),
                )

    def test_mac_is_truncated_to_12(self):
        body = _mine((prop_frame.PING, 1, 0x11, 0x22, 1, 1, b""))[: prop_frame.HEADER_LENGTH]
        mac = prop_frame._mac(body, KEY)
        self.assertEqual(len(mac), prop_frame.MAC_LENGTH)
        self.assertEqual(mac, std_hmac.new(KEY, body, hashlib.sha256).digest()[:12])


class PayloadParity(unittest.TestCase):
    def test_led_payload(self):
        self.assertEqual(
            prop_frame.encode_led_payload(0xFF, LED_COLORS),
            proto.encode_led_payload(0xFF, LED_COLORS),
        )

    def test_led_payload_rejects_bad_byte_ranges_and_shapes(self):
        bad_cases = [
            dict(brightness=-1, colors=LED_COLORS),
            dict(brightness=256, colors=LED_COLORS),
            dict(brightness=0, colors=[(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11)]),
            dict(brightness=0, colors=[(1, 2, 3), (4, 5, 6), (7, 8, 9), (-1, 0, 0)]),
            dict(brightness=0, colors=[(1, 2, 3), (4, 5, 6), (7, 8, 9), (256, 0, 0)]),
        ]
        for case in bad_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    prop_frame.encode_led_payload(**case)

    def test_remote_led_strips_reserved_bits(self):
        for m in [0x00, 0x01, 0x02, 0x03, 0x04, 0x80, 0xFF]:
            with self.subTest(mask=m):
                self.assertEqual(prop_frame.encode_remote_led(m), proto.encode_remote_led(m))

    def test_remote_led_rejects_out_of_byte_range_mask(self):
        for mask in (-1, 256):
            with self.subTest(mask=mask):
                with self.assertRaises(ValueError):
                    prop_frame.encode_remote_led(mask)

    def test_palette_payload(self):
        for n in (1, 2, 8):
            colors = [(i, (i * 7) & 0xFF, (i * 13) & 0xFF) for i in range(n)]
            for fade in (False, True):
                for rev in (0, 1, 255):
                    with self.subTest(n=n, fade=fade, rev=rev):
                        self.assertEqual(
                            prop_frame.encode_palette_payload(rev, fade, colors),
                            proto.encode_palette_payload(rev, fade, colors),
                        )

    def test_palette_payload_rejects_bad_byte_ranges_and_shapes(self):
        bad_cases = [
            dict(palette_rev=-1, fade=False, colors=[(1, 2, 3)]),
            dict(palette_rev=256, fade=False, colors=[(1, 2, 3)]),
            dict(palette_rev=1, fade=False, colors=[(1, 2)]),
            dict(palette_rev=1, fade=False, colors=[(-1, 2, 3)]),
            dict(palette_rev=1, fade=False, colors=[(256, 2, 3)]),
        ]
        for case in bad_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    prop_frame.encode_palette_payload(**case)


class HexAndLineParity(unittest.TestCase):
    def test_to_hex_uppercase(self):
        for raw in [b"", b"\x00\x0f\xa0", bytes(range(256))]:
            self.assertEqual(prop_frame.to_hex(raw), proto.bytes_to_hex(raw))

    def test_ff_and_send_line_format(self):
        frame = _mine((prop_frame.PREVIEW, 1, 0x11, 0x22, 1, 2, b""))
        expect_hex = proto.bytes_to_hex(frame)
        self.assertEqual(prop_frame.ff_line(frame), "FF " + expect_hex + "\n")
        self.assertEqual(prop_frame.send_line(frame), "SEND " + expect_hex + "\n")
        # round-trip the hex straight off the wire line back through the verifier
        hex_on_wire = prop_frame.ff_line(frame)[3:-1]
        self.assertEqual(
            proto.decode_frame(bytes.fromhex(hex_on_wire), KEYS).frame_type, proto.FrameType.PREVIEW
        )

    def test_max_wire_lines_fit_cpp_host_rx_line_budget(self):
        header = PROP_PROTOCOL_H.read_text(encoding="utf-8")
        self.assertIn("MAX_HOST_RX_LINE_LENGTH", header)
        max_host_line = proto.MAX_FRAME_LENGTH * 2 + 16 + 1
        frame = _mine(
            (
                prop_frame.STATUS,
                1,
                0xFF,
                0xFF,
                0xFFFFFFFF,
                0xFFFFFFFFFFFFFFFF,
                bytes(range(prop_frame.MAX_PAYLOAD_LENGTH)),
            )
        )

        self.assertEqual(len(frame), proto.MAX_FRAME_LENGTH)
        self.assertLessEqual(len(prop_frame.ff_line(frame)), max_host_line)
        self.assertLessEqual(len(prop_frame.send_line(frame)), max_host_line)


class SenderParity(unittest.TestCase):
    def _rng(self, values):
        box = {"i": 0}

        def _next():
            v = values[box["i"] % len(values)]
            box["i"] += 1
            return v

        return _next

    def test_nonce_composition_and_sequence(self):
        s = prop_frame.PropSender(
            epoch=0xABCD0001, sequence=5, rand32=self._rng([0x11111111, 0x22222222])
        )
        dec = proto.decode_frame(s.encode(prop_frame.STOP), KEYS)
        self.assertEqual(dec.sequence, 5)
        self.assertEqual(dec.nonce, (0xABCD0001 << 32) | 0x11111111)
        self.assertEqual(s.sequence, 6)
        self.assertEqual(int(dec.frame_type), prop_frame.STOP)

    def test_auto_epoch_is_nonzero(self):
        # first rand32 (0) is consumed for the epoch -> must be forced nonzero (1)
        s = prop_frame.PropSender(epoch=None, rand32=self._rng([0, 0x55555555]))
        self.assertEqual(s.epoch, 1)
        dec = proto.decode_frame(s.encode(prop_frame.PING), KEYS)
        self.assertEqual(dec.nonce, (1 << 32) | 0x55555555)

    def test_preview_line_decodes_to_real_colors(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        s = prop_frame.PropSender(epoch=0x00000001, sequence=1, rand32=self._rng([0xDEADBEEF]))
        line = s.preview_line(colors)
        self.assertTrue(line.startswith("FF ") and line.endswith("\n"))
        dec = proto.decode_frame(bytes.fromhex(line[3:-1]), KEYS)
        self.assertEqual(dec.frame_type, proto.FrameType.PREVIEW)
        self.assertEqual(proto.parse_led_payload(bytes(dec.payload))["colors"], colors)

    def test_fire_burst_repeats_one_authenticated_ff_frame(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        s = prop_frame.PropSender(epoch=0xABCD0001, sequence=10, rand32=self._rng([0xCAFEBABE]))

        lines = s.fire_burst_lines(colors, copies=3)

        self.assertEqual(len(lines), 3)
        self.assertEqual(len(set(lines)), 1)
        self.assertTrue(all(line.startswith("FF ") and line.endswith("\n") for line in lines))
        dec = proto.decode_frame(bytes.fromhex(lines[0][3:-1]), KEYS)
        self.assertEqual(dec.frame_type, proto.FrameType.FIRE)
        self.assertEqual(dec.sequence, 10)
        self.assertEqual(dec.nonce, (0xABCD0001 << 32) | 0xCAFEBABE)
        self.assertEqual(proto.parse_led_payload(bytes(dec.payload))["colors"], colors)
        self.assertEqual(s.sequence, 11)

    def test_fire_burst_rejects_zero_copies(self):
        s = prop_frame.PropSender(epoch=1, sequence=1, rand32=self._rng([1]))

        with self.assertRaises(ValueError):
            s.fire_burst_lines(LED_COLORS, copies=0)


if __name__ == "__main__":
    unittest.main()
