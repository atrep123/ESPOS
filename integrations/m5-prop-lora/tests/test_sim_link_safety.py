from __future__ import annotations

import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.protocol.protocol import FrameType, PropFrame  # noqa: E402
from tools import sim_link as sim  # noqa: E402


def _frame(frame_type: FrameType, *, epoch: int, sequence: int) -> PropFrame:
    return PropFrame(
        frame_type=frame_type,
        key_id=sim.KEY_ID,
        source=sim.DIAL_ADDR,
        destination=sim.DIN_RX_ADDR,
        sequence=sequence,
        nonce=(epoch << 32) | sequence,
        payload=b"",
    )


def _receiver() -> tuple[sim.EventLoop, sim.Receiver]:
    loop = sim.EventLoop()
    receiver = sim.Receiver(loop, random.Random(7), sim.SimConfig(), modem=None)
    receiver.fire_records = {}
    return loop, receiver


def test_receiver_stop_fence_blocks_lower_sequence_new_epoch_arm_fire_replay():
    _loop, receiver = _receiver()
    live_epoch = 0x22222222
    replayed_epoch = 0x11111111

    receiver.on_modem_frame(_frame(FrameType.ARM, epoch=live_epoch, sequence=999), band="espnow")
    assert receiver.armed is True

    receiver.on_modem_frame(_frame(FrameType.STOP, epoch=live_epoch, sequence=1000), band="espnow")
    assert receiver.stop_latched is True
    assert receiver.armed is False
    assert receiver.lockout_seq == 1000

    receiver.on_modem_frame(
        _frame(FrameType.ARM, epoch=replayed_epoch, sequence=100), band="espnow"
    )
    assert receiver.stop_latched is True
    assert receiver.armed is False

    receiver.fire_records[101] = sim.FireRecord(sequence=101, nonce=0, start_ms=0)
    receiver.on_modem_frame(
        _frame(FrameType.FIRE, epoch=replayed_epoch, sequence=101), band="espnow"
    )

    assert receiver.fire_records[101].delivered_count == 0


def test_receiver_post_stop_arm_must_postdate_stop_fence():
    _loop, receiver = _receiver()
    live_epoch = 0x33333333

    receiver.on_modem_frame(_frame(FrameType.STOP, epoch=live_epoch, sequence=1000), band="espnow")
    receiver.on_modem_frame(_frame(FrameType.ARM, epoch=live_epoch, sequence=1001), band="espnow")

    assert receiver.stop_latched is False
    assert receiver.armed is True
    assert receiver.arm_epoch == live_epoch
    assert receiver.arm_seq == 1001

    receiver.fire_records[1002] = sim.FireRecord(sequence=1002, nonce=0, start_ms=0)
    receiver.on_modem_frame(_frame(FrameType.FIRE, epoch=live_epoch, sequence=1002), band="espnow")

    assert receiver.fire_records[1002].delivered_count == 1
