import unittest

from shared.protocol.protocol import (
    FrameReplayWindow,
    FrameType,
    ProtocolError,
    PropFrame,
    decode_frame,
    encode_frame,
    encode_led_payload,
    hex_to_bytes,
    parse_led_payload,
)


KEYS = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}


class ProtocolTests(unittest.TestCase):
    def test_round_trip_authenticated_frame(self):
        payload = bytes([10, 20, 30, 40])
        frame = PropFrame(
            frame_type=FrameType.PREVIEW,
            key_id=1,
            source=0x11,
            destination=0x22,
            sequence=42,
            nonce=0x0102030405060708,
            payload=payload,
        )

        encoded = encode_frame(frame, KEYS)
        decoded = decode_frame(encoded, KEYS)

        self.assertEqual(decoded, frame)

    def test_rejects_tampered_payload_mac(self):
        frame = PropFrame(
            frame_type=FrameType.FIRE,
            key_id=1,
            source=0x11,
            destination=0x22,
            sequence=43,
            nonce=0x1112131415161718,
            payload=b"LED",
        )
        encoded = bytearray(encode_frame(frame, KEYS))
        encoded[-13] ^= 0x55

        with self.assertRaisesRegex(ProtocolError, "MAC"):
            decode_frame(bytes(encoded), KEYS)

    def test_replay_window_mirrors_firmware_sliding_window(self):
        replay = FrameReplayWindow()
        # A nonce whose top 32 bits are the per-boot epoch (low bits unused here; the
        # sequence is a separate field, mirroring the firmware).
        epoch_a = 0xABCD1234 << 32

        # First frame of a session establishes the window.
        self.assertEqual(replay.classify(epoch_a, 100), "new")
        self.assertEqual(replay.classify(epoch_a, 100), "duplicate")
        self.assertEqual(replay.classify(epoch_a, 101), "new")       # advance
        self.assertEqual(replay.classify(epoch_a, 99), "new")        # in-window backfill: accept once
        self.assertEqual(replay.classify(epoch_a, 99), "duplicate")  # ...then a duplicate
        self.assertEqual(replay.classify(epoch_a, 50), "stale")      # diff 51 > 32-frame window

        # A new epoch (a Dial reboot) resets the window, so a low sequence is accepted
        # again -- the old per-source high-water model wrongly rejected this forever.
        epoch_b = 0x00990000 << 32
        self.assertEqual(replay.classify(epoch_b, 5), "new")

    def test_payload_length_limit_is_enforced(self):
        frame = PropFrame(
            frame_type=FrameType.PREVIEW,
            key_id=1,
            source=0x11,
            destination=0x22,
            sequence=44,
            nonce=0x2122232425262728,
            payload=bytes(range(65)),
        )

        with self.assertRaisesRegex(ProtocolError, "payload"):
            encode_frame(frame, KEYS)

    def test_hex_decoder_rejects_odd_length_uart_line(self):
        with self.assertRaisesRegex(ProtocolError, "hex"):
            hex_to_bytes("abc")

    def test_led_payload_encodes_brightness_and_four_rgb_values(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (16, 32, 48)]

        payload = encode_led_payload(brightness=150, colors=colors)
        parsed = parse_led_payload(payload)

        self.assertEqual(payload, bytes([150, 255, 0, 0, 0, 255, 0, 0, 0, 255, 16, 32, 48]))
        self.assertEqual(parsed["brightness"], 150)
        self.assertEqual(parsed["colors"], colors)


if __name__ == "__main__":
    unittest.main()
