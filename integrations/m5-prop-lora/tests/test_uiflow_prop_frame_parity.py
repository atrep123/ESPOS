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
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "uiflow" / "dial"))
PROP_PROTOCOL_H = ROOT / "shared" / "protocol" / "prop_protocol.h"
TEST_KEY_HEX = "00112233445566778899aabbccddeeff"
sys.modules["prop_key"] = types.SimpleNamespace(
    SHARED_KEY_HEX=TEST_KEY_HEX,
    ALLOW_PROTOTYPE_SHARED_KEY=True,
)

from shared.protocol import protocol as proto  # noqa: E402
import prop_frame  # noqa: E402  (flat module, as it sits on the MicroPython device)


KEY = bytes.fromhex(TEST_KEY_HEX)
KEYS = {1: KEY}
PROVISIONED_KEY = bytes.fromhex("102132435465768798a9babbdcddedef")

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


def _load_prop_frame_with_prop_key(source: str):
    old_path = list(sys.path)
    old_prop_key = sys.modules.pop("prop_key", None)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "prop_key.py").write_text(source, encoding="utf-8")
        sys.path.insert(0, str(tmp_path))
        spec = importlib.util.spec_from_file_location(
            f"prop_frame_under_test_{id(source)}", ROOT / "uiflow" / "dial" / "prop_frame.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = old_path
            sys.modules.pop("prop_key", None)
            if old_prop_key is not None:
                sys.modules["prop_key"] = old_prop_key
        return module


def _load_prop_frame_without_prop_key():
    old_path = list(sys.path)
    old_prop_key = sys.modules.pop("prop_key", None)
    spec = importlib.util.spec_from_file_location(
        "prop_frame_without_prop_key", ROOT / "uiflow" / "dial" / "prop_frame.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        sys.modules.pop("prop_key", None)
        if old_prop_key is not None:
            sys.modules["prop_key"] = old_prop_key
    return module


class FrameParity(unittest.TestCase):
    def test_shared_key_matches(self):
        self.assertEqual(prop_frame.SHARED_KEY, KEY)

    def test_provisioned_prop_key_module_overrides_prototype_key(self):
        module = _load_prop_frame_with_prop_key(
            'SHARED_KEY_HEX = "102132435465768798a9babbdcddedef"\n'
        )

        self.assertEqual(module.SHARED_KEY, PROVISIONED_KEY)
        self.assertFalse(module.DRY_SMOKE_KEY_ACTIVE)
        frame = module.encode_frame(module.PING, 1, 0x11, 0x22, 1, 1)
        self.assertEqual(proto.decode_frame(frame, {1: PROVISIONED_KEY}).frame_type, proto.FrameType.PING)

    def test_prop_key_module_missing_key_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "did not provide SHARED_KEY"):
            _load_prop_frame_with_prop_key("# intentionally empty\n")

    def test_missing_prop_key_module_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "did not provide SHARED_KEY"):
            _load_prop_frame_without_prop_key()

    def test_prop_key_module_can_explicitly_allow_prototype_for_bench(self):
        module = _load_prop_frame_with_prop_key(
            'ALLOW_PROTOTYPE_SHARED_KEY = True\nSHARED_KEY_HEX = "00112233445566778899aabbccddeeff"\n'
        )

        self.assertEqual(module.SHARED_KEY, KEY)
        self.assertTrue(module.DRY_SMOKE_KEY_ACTIVE)

    def test_prop_key_module_requires_literal_bool_for_prototype_flag(self):
        with self.assertRaisesRegex(RuntimeError, "ALLOW_PROTOTYPE_SHARED_KEY must be True or False"):
            _load_prop_frame_with_prop_key(
                'ALLOW_PROTOTYPE_SHARED_KEY = "yes"\n'
                'SHARED_KEY_HEX = "00112233445566778899aabbccddeeff"\n'
            )

    def test_prop_key_module_rejects_prototype_key_without_explicit_bench_flag(self):
        with self.assertRaisesRegex(RuntimeError, "dry-smoke HMAC key"):
            _load_prop_frame_with_prop_key('SHARED_KEY_HEX = "00112233445566778899aabbccddeeff"\n')

    def test_prop_key_module_rejects_keys_longer_than_cxx_runtime_limit(self):
        with self.assertRaisesRegex(RuntimeError, "at most 64 bytes"):
            _load_prop_frame_with_prop_key(f'SHARED_KEY_HEX = "{"aa" * 65}"\n')

    def test_key_from_hex_rejects_malformed_input(self):
        for value, message in (
            ("123", "even number of digits"),
            ("12G4", "non-hex character"),
            ("00:11:22:3", "even number of digits"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, message):
                    prop_frame._key_from_hex(value)

    def test_explicit_key_override_uses_runtime_length_limits(self):
        with self.assertRaisesRegex(RuntimeError, "at least 16 bytes"):
            prop_frame.encode_frame(prop_frame.PING, 1, 0x11, 0x22, 1, 2, key=b"short")
        with self.assertRaisesRegex(RuntimeError, "at least 16 bytes"):
            prop_frame.PropSender(key=b"short")

    def test_prop_key_module_rejects_raw_shared_key_schema(self):
        with self.assertRaisesRegex(RuntimeError, "must not define SHARED_KEY"):
            _load_prop_frame_with_prop_key(
                'SHARED_KEY_HEX = "102132435465768798a9babbdcddedef"\n'
                'SHARED_KEY = bytes.fromhex("102132435465768798a9babbdcddedef")\n'
            )

    def test_prop_frame_source_has_no_compiled_prototype_key(self):
        source = (ROOT / "uiflow" / "dial" / "prop_frame.py").read_text(encoding="utf-8")

        self.assertIn("DRY_SMOKE_KEY_ACTIVE", source)
        self.assertNotIn("00112233445566778899aabbccddeeff", source)
        self.assertNotIn("_PROTOTYPE_KEY", source)
        self.assertNotIn("SHARED_KEY = bytes(", source)
        self.assertNotIn(TEST_KEY_HEX, source)

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

    def test_stop_line_uses_ack_tracked_send_path(self):
        s = prop_frame.PropSender(epoch=1, sequence=1, rand32=self._rng([2]))

        line = s.stop_line()

        self.assertTrue(line.startswith("SEND "))
        dec = proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), KEYS)
        self.assertEqual(dec.frame_type, proto.FrameType.STOP)

    def test_stop_lines_retry_same_ack_tracked_frame(self):
        s = prop_frame.PropSender(epoch=1, sequence=4, rand32=self._rng([2]))

        lines = s.stop_lines()

        self.assertEqual(len(lines), prop_frame.STOP_RETRY_COPIES)
        self.assertEqual(len(set(lines)), 1)
        self.assertTrue(all(line.startswith("SEND ") for line in lines))
        decoded = [
            proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), KEYS)
            for line in lines
        ]
        self.assertEqual(
            [frame.frame_type for frame in decoded],
            [proto.FrameType.STOP] * prop_frame.STOP_RETRY_COPIES,
        )
        self.assertEqual(decoded[0].sequence, decoded[1].sequence)
        self.assertEqual(decoded[1].sequence, decoded[2].sequence)
        self.assertEqual(decoded[0].nonce, decoded[1].nonce)
        self.assertEqual(decoded[1].nonce, decoded[2].nonce)
        self.assertEqual(s.sequence, 5)

    def test_arm_lines_repeat_one_authenticated_ff_frame(self):
        s = prop_frame.PropSender(epoch=1, sequence=7, rand32=self._rng([3]))

        lines = s.arm_lines()

        self.assertEqual(len(lines), prop_frame.ARM_BURST_COPIES)
        self.assertEqual(len(set(lines)), 1)
        self.assertTrue(all(line.startswith("FF ") for line in lines))
        dec = proto.decode_frame(bytes.fromhex(lines[0].split(" ", 1)[1].strip()), KEYS)
        self.assertEqual(dec.frame_type, proto.FrameType.ARM)
        self.assertEqual(dec.sequence, 7)
        self.assertEqual(s.sequence, 8)

    def test_remote_led_lines_repeat_remote_without_palette_preflight(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 127, 255), (255, 127, 0)]
        s = prop_frame.PropSender(epoch=1, sequence=20, rand32=self._rng([4, 5]))

        lines = s.remote_led_lines(prop_frame.REMOTE_LED_BIT_LED5, colors)

        self.assertEqual(len(lines), prop_frame.REMOTE_LED_BURST_COPIES)
        self.assertTrue(all(line.startswith("FF ") for line in lines))
        decoded = [
            proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), KEYS)
            for line in lines
        ]
        self.assertEqual(
            [frame.frame_type for frame in decoded],
            [proto.FrameType.REMOTE_LED] * prop_frame.REMOTE_LED_BURST_COPIES,
        )
        self.assertEqual(len(set(lines)), 1)
        self.assertEqual(proto.parse_remote_led(bytes(decoded[0].payload)), proto.REMOTE_LED_BIT_LED5)
        self.assertEqual(s.sequence, 21)


if __name__ == "__main__":
    unittest.main()
