#!/usr/bin/env python3
from state_inspector import StateInspector, StateSnapshot


class DummyInspector(StateInspector):
    """Subclass that bypasses real network and returns canned state."""

    def __init__(self):
        super().__init__(host="localhost", port=0)
        self._count = 0

    def send_command(self, method, params=None):  # type: ignore[override]
        if method != "get_state":
            return None
        self._count += 1
        return {
            "scene": 1,
            "bg_color": 0x1234,
            "buttons": {"A": True, "B": False},
            "fps": 55.5,
            "frame_count": self._count,
            "event_queue_size": 3,
            "render_time_ms": 12.5,
            "custom": {"note": "test"},
        }


def test_get_state_populates_snapshot_and_stats(tmp_path):
    insp = DummyInspector()
    snap = insp.get_state()
    assert isinstance(snap, StateSnapshot)
    assert snap.scene == 1
    assert snap.bg_color == 0x1234
    assert snap.button_states["A"] is True
    assert insp.stats["total_frames"] == 1

    # multiple calls should grow stats and history
    for _ in range(4):
        insp.get_state()
    assert insp.stats["total_frames"] == 5
    assert len(insp.get_recent_snapshots(10)) == 5

    # export should write a valid JSON file
    out = tmp_path / "state_history.json"
    insp.export_to_json(str(out))
    data = out.read_text(encoding="utf-8")
    assert '"snapshots"' in data
    assert '"statistics"' in data

