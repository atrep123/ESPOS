"""Actual public E headless C integration, mock gray4 display transport only.

Existing GCC, wrapper and owned runner execute; nothing is mocked or installed.
No desktop/app GUI, private SDK/Core/IDF/UI header inspection or hardware proof.
Run this file only, Python 3.12 -I -X utf8 -B, explicit repo sys.path,
--noconftest, a fresh TEST_ONLY basetemp and --tb=no. Failed artifacts are kept.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.native_windows

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import espos_runtime_simulator as simulator  # noqa: E402

STATUS = {"connected": 0, "disconnected": 0x105, "error": -1}
INPUTS = [0, 6, 1, 4, 0]
# Every non-tick ingress step consumes five virtual ticks in the real runner.
# Replace transport steps with tick:5 in the connected reference, preserving
# order, total advance and the final 100-tick transient-settling interval.
REFERENCE = ["tick:100", "tick:5", *INPUTS, "tick:100", "tick:5", "tick:100"]
PGM_HEADER = b"P5\n256 128\n255\n"


def source_hashes():
    # Opaque hashes only: no native C/header text is read or interpreted here.
    names = (
        "ui_render",
        "ui_render_swbuf",
        "ui_render_text",
        "ui_render_widgets",
        "ui_nav",
        "ui_font_6x8",
        "ui_border",
        "ui_dither",
        "ui_text_layout",
        "ui_widget_style",
        "ui_rect",
        "ui_format",
        "icons",
        "icons_24",
        "icons_registry",
    )
    paths = [ROOT / "src" / (name + ".c") for name in names]
    paths += list((ROOT / "src/services/ui").glob("*.c"))
    paths += list((ROOT / "tools/native_simulator").glob("*.c"))
    paths += [
        ROOT / name
        for name in (
            "tools/espos_runtime_simulator.py",
            "tools/simulator_process.py",
            "tools/simulator_contract.py",
            "tools/simulator_environment.py",
            "tools/ui_codegen.py",
            "src/kernel/msgbus.c",
            "src/services/ui_app/ui_app_logic.c",
            "test/stubs/store_stub.c",
            "test/stubs/esp_err_stub.c",
        )
    ]
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }


class NativeRuns:
    def __init__(self, base, monkeypatch):
        assert sys.version_info[:2] == (3, 12), "Python 3.12 required, no skip"
        assert os.name == "nt", "Windows app scheduler required, no skip"
        self.base = base
        self.builds = base / "private-builds"
        self.builds.mkdir()
        # Explicit placement only: the real allocator and guarded cleanup remain.
        # Do not read or copy the parent environment/configuration.
        monkeypatch.setattr(tempfile, "tempdir", str(self.builds))
        self.original_child = simulator.run_child
        self.receipts = []
        self.active = None
        self.control_cache = {}
        monkeypatch.setattr(simulator, "run_child", self.observe_actual_child)

    def observe_actual_child(self, command, **options):
        phase = "compile" if options["timeout"] == 60 else "runtime"
        assert options["timeout"] == (60 if phase == "compile" else 10)
        assert Path(options["cwd"]).is_relative_to(self.builds)
        try:
            result = self.original_child(command, **options)
        except simulator.SimulatorProcessError as error:
            # Never reflect stdout/stderr, compiler diagnostics or header text.
            self.receipts.append(
                {
                    "phase": phase,
                    "error": str(error),
                    "cleanup_confirmed": error.cleanup_confirmed,
                    "returncode": error.returncode,
                }
            )
            raise
        receipt = {
            "phase": phase,
            "returncode": result.returncode,
            "ownership": result.ownership,
            "owned_scope_empty": result.owned_scope_empty,
            "timeout": options["timeout"],
        }
        if phase == "compile":
            receipt["compiler"] = str(command[0])
        else:
            # This is the actual native child's JSON, before wrapper decoding.
            child = json.loads(result.stdout.decode("utf-8").strip().splitlines()[-1])
            receipt["actual_child_json"] = child
            (self.active / "actual-child.json").write_text(
                json.dumps(child, indent=2), encoding="utf-8"
            )
        self.receipts.append(receipt)
        return result

    def run(self, name, events, *, app, observe_rejected_status=False):
        directory = self.base / name
        directory.mkdir()
        self.active, self.receipts = directory, []
        scene = directory / "synthetic-scene.json"
        widgets = [
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
                "type": "button",
                "id": "trigger",
                "x": 10,
                "y": 50,
                "width": 90,
                "height": 20,
                "text": "Activate",
                "events": {
                    "on_press": [
                        {"type": "set_widget", "widget": "marker", "prop": "value", "value": 7},
                        {
                            "type": "set_widget",
                            "widget": "marker",
                            "prop": "text",
                            "text": "pressed",
                        },
                    ]
                },
            },
            {
                "type": "label",
                "id": "marker",
                "x": 120,
                "y": 10,
                "width": 110,
                "height": 20,
                "text": "cold",
                "value": 0,
            },
        ]
        rules = [
            {
                "trigger": {"type": "boot"},
                "actions": [
                    {"type": "set_widget", "widget": "marker", "prop": "text", "text": "booted"},
                ],
            }
        ]
        scene.write_text(
            json.dumps(
                {
                    "scenes": {
                        "main": {
                            "width": 256,
                            "height": 128,
                            "bg_color": "black",
                            "widgets": widgets,
                            "rules": rules,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        output = directory / "actual-frame.pgm"
        (directory / "ingress.json").write_text(
            json.dumps(
                {
                    "events": events,
                    "app": app,
                    "scope": "actual public headless native C; mock gray4 transport",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        started = time.monotonic()
        validation_error = None
        try:
            state = simulator.run(scene, output, events, app=app)
        except ValueError as error:
            # Keep the wrapper's contract failure visible, but finish independent
            # pixel/reconnect controls before asserting it. No fake state/status.
            if not (
                observe_rejected_status
                and str(error) == "Simulator runtime must report a bounded integer display_status"
                and len(self.receipts) == 2
                and "actual_child_json" in self.receipts[-1]
            ):
                raise
            state = None
            validation_error = str(error)
        except BaseException:
            (directory / "failure.json").write_text(
                json.dumps(
                    {"receipts": self.receipts, "seconds": time.monotonic() - started}, indent=2
                ),
                encoding="utf-8",
            )
            raise
        assert len(self.receipts) == 2
        assert all(
            receipt["ownership"] == "windows-job"
            and receipt["owned_scope_empty"] is True
            and receipt["returncode"] == 0
            for receipt in self.receipts
        )
        child = self.receipts[-1]["actual_child_json"]
        assert child["runtime_simulation"] is True
        if state is not None:
            assert state["display_status"] == child["display_status"]
            assert (
                state["simulation"]["final_display"]
                == {
                    0: "connected",
                    0x105: "disconnected",
                    -1: "error",
                }[child["display_status"]]
            )
        data = output.read_bytes()
        assert data.startswith(PGM_HEADER) and len(data) == len(PGM_HEADER) + 256 * 128
        (directory / "result.json").write_text(
            json.dumps(
                {
                    "state": state,
                    "validation_error": validation_error,
                    "frame_sha256": hashlib.sha256(data).hexdigest(),
                    "receipts": self.receipts,
                    "seconds": time.monotonic() - started,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        assert list(self.builds.iterdir()) == [], "Proven native build cleanup required"
        return state, data

    def controls(self, app):
        if app not in self.control_cache:
            mode = "app" if app else "default"
            initial = self.run(mode + "-accepted-control", ["tick:100"], app=app)
            connected = self.run(mode + "-settled-connected-control", REFERENCE, app=app)
            assert initial[0]["widgets"][0]["value"] == 4
            assert connected[0]["widgets"][0]["value"] == 6
            assert initial[1] != connected[1], "Control must show a real pixel change"
            check_logic(initial[0], app=app, pressed=False)
            check_logic(connected[0], app=app, pressed=True)
            self.control_cache[app] = initial, connected
        return self.control_cache[app]


def check_logic(state, *, app, pressed, raw=False):
    if app:
        assert state["logic_booted"] == 1 and state["bus_drops"] == 0
        assert 0 < state["scheduler_steps"] < 100000
        assert state["widgets"][2]["value"] == (7 if pressed else 0)
        text = state["texts"][2]
        if raw:
            text = bytes.fromhex(text).decode("utf-8")
        assert text == ("pressed" if pressed else "booted")
    else:
        assert state["widgets"][2]["value"] == 0


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    base = tmp_path_factory.getbasetemp()
    assert base.parent.name.startswith("TEST_ONLY-hot-native-"), "Explicit owned output required"
    before = source_hashes()
    patch = pytest.MonkeyPatch()
    runs = NativeRuns(base, patch)
    try:
        yield runs
    finally:
        patch.undo()
        after = source_hashes()
        (base.parent / "source-provenance.json").write_text(
            json.dumps({"before": before, "after": after, "unchanged": before == after}, indent=2),
            encoding="utf-8",
        )
        assert before == after, "Public wrapper/C inputs changed during verification"


@pytest.mark.parametrize("app", [False, True], ids=["default", "app"])
@pytest.mark.parametrize("failure", ["disconnected", "error"])
def test_actual_hot_failure_retains_pixels_then_reconnect_repaints(native, app, failure):
    initial, reference = native.controls(app)
    mode = "app" if app else "default"
    failed_events = ["tick:100", "display:" + failure, *INPUTS, "tick:100"]
    failed_state, failed_frame = native.run(
        mode + "-" + failure, failed_events, app=app, observe_rejected_status=True
    )
    child = native.receipts[-1]["actual_child_json"]
    assert child["widgets"][0]["value"] == 6
    check_logic(child, app=app, pressed=True, raw=True)
    # The last accepted prefix was settled tick:100, before hot failure.
    assert failed_frame == initial[1], "Failed writes changed last accepted pixels"
    assert failed_frame != reference[1], "Failure control must retain visibly older pixels"
    reconnected_state, reconnected_frame = native.run(
        mode + "-" + failure + "-reconnected",
        [*failed_events, "display:connected", "tick:100"],
        app=app,
    )
    assert reconnected_state["display_status"] == STATUS["connected"]
    assert reconnected_state["widgets"][0]["value"] == 6
    check_logic(reconnected_state, app=app, pressed=True)
    assert reconnected_frame == reference[1], "Equal-time settled reconnect must repaint current UI"
    assert reconnected_frame != failed_frame
    assert child["display_status"] == STATUS[failure], (
        "Native child/wrapper status contract mismatch"
    )
    assert failed_state is not None, "Wrapper rejected actual native final status"
    assert failed_state["display_status"] == STATUS[failure]
    assert failed_state["simulation"]["initial_display"] == "connected"
    assert failed_state["simulation"]["final_display"] == failure


@pytest.mark.parametrize("app", [False, True], ids=["default", "app"])
def test_actual_release_tick_order_does_not_synthesize_press(native, app):
    mode = "app" if app else "default"
    # Equal 120-tick totals; release-before-press must not enter the value editor.
    before, before_frame = native.run(
        mode + "-release-without-press",
        ["tick:5", "button:0:release", "tick:5", 6, "tick:100"],
        app=app,
    )
    after, after_frame = native.run(
        mode + "-press-then-release", [0, "tick:5", "button:0:release", 6, "tick:100"], app=app
    )
    assert before["display_status"] == after["display_status"] == STATUS["connected"]
    assert before["widgets"][0]["value"] == 4
    assert after["widgets"][0]["value"] == 6
    check_logic(before, app=app, pressed=False)
    check_logic(after, app=app, pressed=False)
    assert before_frame != after_frame, "Actual value edit must affect captured pixels"
