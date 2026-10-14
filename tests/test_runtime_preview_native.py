"""Actual headless native renderer through the production preview controller.

Synthetic scene and Python callbacks only: no editor window or device. The
compiler, C runner, PGM decoder and process owners are not replaced by mocks.
"""

from __future__ import annotations

import copy
import time

import pytest

from cyberpunk_designer.runtime_preview import RuntimePreview

pytestmark = pytest.mark.native_windows


def test_real_native_result_reaches_preview_after_owned_cleanup(tmp_path):
    source = {
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [
                    {
                        "type": "slider",
                        "id": "level",
                        "x": 10,
                        "y": 10,
                        "width": 90,
                        "height": 20,
                        "value": 4,
                        "min_value": 0,
                        "max_value": 6,
                    },
                    {
                        "type": "checkbox",
                        "id": "enabled",
                        "x": 10,
                        "y": 50,
                        "width": 90,
                        "height": 20,
                        "text": "Enabled",
                    },
                ],
            }
        }
    }
    original = copy.deepcopy(source)
    frames, statuses = [], []
    controller = RuntimePreview(
        on_frame=lambda frame, state: frames.append((frame, state)),
        on_status=statuses.append,
        workspace_parent=tmp_path,
    )
    assert controller.start(source, "native-synthetic", [0, 6, 6, 1, 4, 0])
    work = controller._work
    deadline = time.monotonic() + 80.0
    try:
        while controller.owns_work and time.monotonic() < deadline:
            controller.poll("native-synthetic")
            time.sleep(0.005)
        assert not controller.owns_work, "Native preview exceeded its bounded completion window"
        assert len(frames) == 1, statuses
        frame, state = frames[0]
        assert frame.width == 256 and frame.height == 128
        assert len(frame.pixels) == 256 * 128 and any(frame.pixels)
        assert state["runtime_simulation"] is True
        assert state["simulation"]["hardware_transport"] == "mock"
        assert state["widgets"][0]["value"] == 6
        assert state["widgets"][1]["checked"] == 1
        assert source == original
        assert work.cleanup_confirmed is True and not work.workspace.exists()
        assert not work.thread.is_alive()
        assert statuses[-1] == "completed (mock display)"
    finally:
        # Test teardown owns exactly this controller, never a global PID/name.
        controller.stop()
        if work.thread.is_alive():
            work.thread.join(timeout=8.0)
        controller.poll("native-synthetic")
