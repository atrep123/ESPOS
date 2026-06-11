"""Unit tests for uiflow/dial/prop_state.py -- the Dial app's pure persistence logic.

prop_state.py decides WHAT the UIFlow Dial persists across a reboot (the tuned
palette + the sequence high-water) with no hardware/NVS imports, so it is fully
testable on CPython -- the same split prop_frame.py uses. main.py supplies the thin
esp32.NVS read/write (verify-on-device); the maths/codec proven here is the part
that must be correct for colours to survive a power-cycle and for the monotonic
frame sequence to never go backwards (which would let the receiver reject frames).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "uiflow" / "dial"))

import prop_state as ps  # noqa: E402  (flat module, as it sits on the device)


class PaletteCodecTest(unittest.TestCase):
    def test_roundtrip_factory_palette(self):
        # DEFAULT_HUES from prop_tx_config.h / main.py -- includes values > 255.
        hues = [0, 120, 240, 210, 60]
        blob = ps.hues_to_blob(hues)
        self.assertEqual(len(blob), len(hues) * 2)          # 2 bytes per hue
        self.assertEqual(ps.blob_to_hues(blob, len(hues)), hues)

    def test_values_above_255_survive(self):
        # 1-byte packing would clip 300/359 -> the bug this codec exists to avoid.
        hues = [300, 359, 256, 7, 180]
        self.assertEqual(ps.blob_to_hues(ps.hues_to_blob(hues), 5), hues)

    def test_normalised_to_0_359(self):
        # Values >=360 wrap; the encoder masks to 16 bits, decoder mods 360.
        self.assertEqual(ps.blob_to_hues(ps.hues_to_blob([360, 725]), 2), [0, 5])

    def test_missing_or_short_blob_returns_none(self):
        self.assertIsNone(ps.blob_to_hues(None, 5))
        self.assertIsNone(ps.blob_to_hues(b"", 5))
        self.assertIsNone(ps.blob_to_hues(ps.hues_to_blob([1, 2, 3]), 5))  # 3 < 5

    def test_extra_trailing_bytes_ignored(self):
        blob = ps.hues_to_blob([10, 20, 30, 40, 50]) + b"\xff\xff"
        self.assertEqual(ps.blob_to_hues(blob, 5), [10, 20, 30, 40, 50])


class SequenceReservationTest(unittest.TestCase):
    def test_resume_first_boot(self):
        # No saved reservation -> start at 1 (matches PropSender's default).
        self.assertEqual(ps.seq_resume_from(0), 1)
        self.assertEqual(ps.seq_resume_from(None), 1)
        self.assertEqual(ps.seq_resume_from("garbage"), 1)
        self.assertEqual(ps.seq_resume_from(-5), 1)

    def test_resume_past_reservation(self):
        # Resume one past the last RESERVED high-water -> never reuse a number.
        self.assertEqual(ps.seq_resume_from(64), 65)
        self.assertEqual(ps.seq_resume_from(1280), 1281)

    def test_reservation_written_only_at_boundary(self):
        # Inside the block: no write. At/over the reservation: claim a new block.
        new, write = ps.seq_next_reservation(10, 64, block=64)
        self.assertFalse(write)
        self.assertEqual(new, 64)

        new, write = ps.seq_next_reservation(64, 64, block=64)
        self.assertTrue(write)
        self.assertEqual(new, 64 + 64)

    def test_no_number_is_ever_reused_across_reboots(self):
        """Simulate run -> reboot -> run and assert sequence strictly increases and
        never repeats, with one NVS write per block (flash-wear budget honoured)."""
        block = 64
        nvs_seq = 0          # what's persisted under the "seq" key
        writes = 0
        used = []

        for _boot in range(4):
            seq = ps.seq_resume_from(nvs_seq)         # boot: resume past reservation
            reserved = seq
            for _frame in range(100):                 # send 100 frames this session
                used.append(seq)
                seq += 1
                reserved, should_write = ps.seq_next_reservation(seq, reserved, block)
                if should_write:
                    nvs_seq = reserved                # persist the new high-water
                    writes += 1
            # power lost here: nvs_seq holds the last reservation, ahead of `seq`

        self.assertEqual(len(used), len(set(used)), "a sequence number was reused")
        self.assertEqual(used, sorted(used), "sequence went backwards")
        # 100 frames/boot over 4 boots, 1 write per 64 -> far fewer writes than frames
        self.assertLess(writes, len(used), "too many NVS writes (flash wear)")


if __name__ == "__main__":
    unittest.main()
