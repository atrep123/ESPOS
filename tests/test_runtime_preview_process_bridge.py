"""TEST_ONLY bridge: real Windows owned Python children, fake compiler/PGM/state.

Run only this file, --noconftest, with a fresh explicit TEST_ONLY basetemp after
MAIN freezes the wrapper. No app import, compiler, C runtime, device or GUI.
The real controller, wrapper, run_child and _WindowsJob implementations execute.
Only wrapper tool selection/environment/codegen/root and stage routing are stubbed.
Public tempfile placement is pinned inside the fresh fixture base; no environment
mapping is read/copied. No fixture directory is deleted by this test harness.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cyberpunk_designer.runtime_preview import RuntimePreview  # noqa: E402
from tools import espos_runtime_simulator as wrapper  # noqa: E402
from tools import simulator_process as process  # noqa: E402

pytestmark = [
    pytest.mark.skipif(os.name != "nt", reason="Actual Windows Job bridge only"),
    pytest.mark.timeout(60),
]

MARKER_WAIT = 20.0
CHILD_DEADLINE = 40.0
PGM = b"P5\n256 128\n255\n" + bytes([23]) * (256 * 128)
PUBLIC_SOURCES = (
    "cyberpunk_designer/runtime_preview.py",
    "tools/espos_runtime_simulator.py",
    "tools/simulator_process.py",
)

# Named inert scripts. The marker is emitted only after the real Windows Job's
# Python admission gate has launched this child. Parent PID is that exact gate;
# it is never discovered by enumeration. Both are observed through query handles.
INERT_STAGE = r"""import json, os, sys, time
from pathlib import Path

stage, marker_arg, release_arg, output_arg, copy_arg = sys.argv[1:]
assert stage in ("TEST_ONLY_compile", "TEST_ONLY_runtime")
marker, release = Path(marker_arg), Path(release_arg)
record = {"test_only": True, "stage": stage, "pid": os.getpid(), "root_pid": os.getppid()}
temporary = marker.with_suffix(".writing")
temporary.write_text(json.dumps(record), encoding="utf-8")
temporary.replace(marker)
deadline = time.monotonic() + 45.0
while not release.exists():
    if time.monotonic() >= deadline:
        raise SystemExit(91)
    time.sleep(0.01)
assert release.read_text(encoding="utf-8") == "TEST_ONLY_RELEASE"
if stage == "TEST_ONLY_runtime":
    pgm = b"P5\n256 128\n255\n" + bytes([23]) * (256 * 128)
    Path(output_arg).write_bytes(pgm)
    Path(copy_arg).write_bytes(pgm)
    state = {"runtime_simulation": True, "display_status": 0,
             "texts": ["TEST_ONLY_INERT_FAKE_FRAME".encode("utf-8").hex()],
             "test_only_inert_bridge": True}
    print(json.dumps(state), flush=True)
else:
    print("TEST_ONLY_INERT_COMPILE_COMPLETE", flush=True)
"""


def wait_until(predicate, description, seconds=MARKER_WAIT):
    deadline = time.monotonic() + seconds
    pulse = threading.Event()
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("TEST_ONLY deadline: " + description)
        pulse.wait(0.01)  # Poll scheduling only; readiness is an explicit marker.


class ProcessWitness:
    """Read-only handles to the two exact marker PIDs, opened while alive."""

    def __init__(self, pid):
        self.pid = pid
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, arguments, result in (
            ("OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ("WaitForSingleObject", [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            (
                "GetExitCodeProcess",
                [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
            ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
        ):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        # SYNCHRONIZE + QUERY_LIMITED_INFORMATION; no termination rights.
        self.handle = self.kernel.OpenProcess(0x101000, False, pid)
        if not self.handle:
            raise AssertionError("Cannot observe the explicit TEST_ONLY child/root")
        try:
            assert self.kernel.WaitForSingleObject(self.handle, 0) == 258  # WAIT_TIMEOUT/alive
        except BaseException:
            self.close()
            raise

    def exited(self):
        assert self.kernel.WaitForSingleObject(self.handle, 0) == 0  # WAIT_OBJECT_0
        code = wintypes.DWORD()
        assert self.kernel.GetExitCodeProcess(self.handle, ctypes.byref(code))
        assert code.value != 259  # STILL_ACTIVE
        return code.value

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            assert self.kernel.CloseHandle(handle)


@pytest.fixture(scope="module", autouse=True)
def provenance(tmp_path_factory):
    base = tmp_path_factory.getbasetemp()
    before = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PUBLIC_SOURCES
    }
    job_class = process._WindowsJob
    yield
    after = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PUBLIC_SOURCES
    }
    (base / "source-provenance.json").write_text(
        json.dumps({"before": before, "after": after, "unchanged": before == after}, indent=2),
        encoding="utf-8",
    )
    assert before == after, "Public bridge source changed during independent verification"
    assert process._WindowsJob is job_class, "Windows owner implementation was replaced"


class Bridge:
    def __init__(self, base, monkeypatch, *, mocked_uncertainty=False):
        self.base = base
        self.key = "TEST_ONLY_document_A"
        self.frames, self.statuses, self.records, self.witnesses = [], [], [], {}
        self.mocked_uncertainty = mocked_uncertainty
        self.mock_marker = threading.Event()
        self.python = Path(sys.executable).resolve(strict=True)
        self.private = base / "owned-temp"
        self.snapshots = base / "snapshots"
        self.empty_root = base / "TEST_ONLY_empty_public_root"
        for directory in (self.private, self.snapshots, self.empty_root):
            directory.mkdir()
        for stage in ("compile", "runtime"):
            self.script(stage).write_text(INERT_STAGE, encoding="utf-8")

        # Placement only, not a fake allocator/cleanup/process implementation.
        # tempfile does not consult the parent environment once this is explicit.
        monkeypatch.setattr(tempfile, "tempdir", str(self.private))
        monkeypatch.setattr(wrapper, "ROOT", self.empty_root)
        monkeypatch.setattr(wrapper.shutil, "which", self.compiler)
        monkeypatch.setattr(wrapper, "build_environment", self.environment)
        monkeypatch.setattr(wrapper, "generate_ui_design_multi_pair", self.codegen)
        monkeypatch.setattr(wrapper, "run_child", self.route)
        self.controller = RuntimePreview(
            on_frame=self.deliver,
            on_status=self.statuses.append,
            runner=wrapper.run,
            workspace_parent=self.snapshots,
        )
        self.work = None

    def script(self, stage):
        return self.base / ("TEST_ONLY_" + stage + "_stage.py")

    def marker(self, stage):
        return self.base / ("TEST_ONLY_" + stage + "_owned.json")

    def release(self, stage):
        self.base.joinpath("TEST_ONLY_" + stage + "_release").write_text(
            "TEST_ONLY_RELEASE", encoding="utf-8"
        )

    def compiler(self, name):
        assert name == "gcc"
        return str(self.python)  # Only a selection placeholder; GNU args never execute.

    def environment(self, compiler, python, build):
        assert compiler == python == self.python
        assert build.is_relative_to(self.private)
        # Entire literal/explicit whitelist; no parent mapping/config/auth read.
        return {
            "SystemRoot": r"C:\Windows",
            "WINDIR": r"C:\Windows",
            "PATH": rf"C:\Windows\System32;C:\Windows;{self.python.parent}",
            "TEMP": str(build),
            "TMP": str(build),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def codegen(self, scene, **options):
        assert scene.is_relative_to(self.snapshots)
        # No UI code generator, headers, SDK or native source is evaluated.
        return "TEST_ONLY inert generated placeholder", "TEST_ONLY inert header placeholder"

    def route(self, requested, *, cwd, env, timeout, cancel_event):
        assert cwd.is_relative_to(self.private)
        assert env == self.environment(self.python, self.python, cwd)
        if requested[0] == str(self.python) and "-std=gnu11" in requested:
            stage = "compile"
            assert timeout == 60
            output = self.base / "TEST_ONLY_unused_compile_output"
        else:
            assert requested[0] == str(cwd / "runtime.exe")
            assert timeout == 10 and requested[2] == "0"
            stage = "runtime"
            output = Path(requested[1])
            assert output.is_relative_to(self.snapshots)
        if self.mocked_uncertainty:
            # Separate classification control: no real child/Job is started.
            (cwd / "TEST_ONLY_mocked_inflight_partial").write_bytes(b"TEST_ONLY partial")
            self.mock_marker.set()
            raise RuntimeError("TEST_ONLY mocked unexpected in-flight error")
        command = [
            str(self.python),
            "-I",
            "-S",
            "-B",
            str(self.script(stage)),
            "TEST_ONLY_" + stage,
            str(self.marker(stage)),
            str(self.base / ("TEST_ONLY_" + stage + "_release")),
            str(output),
            str(self.base / "TEST_ONLY_fake_frame_copy.pgm"),
        ]
        # Only these named inert commands execute. Forty seconds gives marker
        # controls room under host load; the real runner's <=60s bound remains.
        try:
            result = process.run_child(
                command, cwd=cwd, env=env, timeout=CHILD_DEADLINE, cancel_event=cancel_event
            )
        except process.SimulatorProcessError as error:
            self.records.append(
                {
                    "stage": stage,
                    "real_owned_python": True,
                    "error": str(error),
                    "cleanup_confirmed": error.cleanup_confirmed,
                    "returncode": error.returncode,
                }
            )
            raise
        self.records.append(
            {
                "stage": stage,
                "real_owned_python": True,
                "natural": True,
                "ownership": result.ownership,
                "owned_scope_empty": result.owned_scope_empty,
                "returncode": result.returncode,
            }
        )
        return result

    def deliver(self, frame, state):
        if frame is not None:
            assert not self.controller.owns_work
            assert len(self.records) == 2
            assert all(
                record.get("natural") is True and record["owned_scope_empty"] is True
                for record in self.records
            )
            self.confirm_exited("compile", natural=True)
            self.confirm_exited("runtime", natural=True)
        self.frames.append((frame, state))

    def start(self):
        assert self.controller.start(
            {"scenes": {"main": {"width": 256, "height": 128, "widgets": []}}}, self.key
        )
        self.work = self.controller._work
        assert self.work is not None

    def await_owned(self, stage):
        wait_until(lambda: self.marker(stage).exists(), stage + " owned admission marker")
        marker = json.loads(self.marker(stage).read_text(encoding="utf-8"))
        assert marker["test_only"] is True and marker["stage"] == "TEST_ONLY_" + stage
        assert type(marker["pid"]) is type(marker["root_pid"]) is int
        assert marker["pid"] > 0 and marker["root_pid"] > 0
        assert marker["pid"] != marker["root_pid"]
        observed = []
        try:
            for pid in (marker["pid"], marker["root_pid"]):
                observed.append(ProcessWitness(pid))
        finally:
            self.witnesses[stage] = observed
        assert self.frames == [] and self.controller.owns_work

    def confirm_exited(self, stage, *, natural):
        assert len(self.witnesses[stage]) == 2
        codes = [witness.exited() for witness in self.witnesses[stage]]
        record = next(record for record in self.records if record["stage"] == stage)
        assert codes[1] == record["returncode"]  # Exact retained gate/root handle.
        if natural:
            assert codes == [0, 0]
            assert record["ownership"] == "windows-job" and record["owned_scope_empty"] is True
        else:
            assert record["error"] == "simulator-cancelled"
            assert record["cleanup_confirmed"] is True and record["returncode"] is not None
        record["independent_marker_pid_exit_codes"] = codes

    def poll_closed(self):
        def closed():
            self.controller.poll(self.key)
            if self.work.observed and self.controller.owns_work:
                raise AssertionError("TEST_ONLY real cancellation cleanup remained unconfirmed")
            return not self.controller.owns_work

        wait_until(closed, "controller-owned worker join and confirmed cleanup")
        assert not self.work.thread.is_alive()
        assert self.work.cleanup_confirmed is True
        assert self.work.workspace is not None and not self.work.workspace.exists()
        assert list(self.private.iterdir()) == []

    def finish_fixture(self):
        # No directory removal or broad PID/name termination, including on failure.
        # Cancellation and cleanup remain the actual owner's responsibility.
        status_before_teardown = self.controller.status
        delivered = [
            {
                "width": frame.width,
                "height": frame.height,
                "pixels_sha256": hashlib.sha256(frame.pixels).hexdigest(),
                "state": state,
            }
            for frame, state in self.frames
            if frame is not None
        ]
        self.controller.stop()
        if self.work is not None:
            self.work.thread.join(timeout=55)
        evidence = {
            "scope": "actual Windows inert-process bridge; compiler/frame/state TEST_ONLY",
            "mocked_uncertainty": self.mocked_uncertainty,
            "records": self.records,
            "status_before_teardown": status_before_teardown,
            "status": self.controller.status,
            "delivered_test_only_frames": delivered,
            "ownership_retained": self.controller.owns_work,
            "retained_paths": [str(path) for path in self.controller.retained_paths],
        }
        (self.base / "bridge-evidence.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )
        for witnesses in self.witnesses.values():
            for witness in witnesses:
                witness.close()
        if self.work is not None:
            assert not self.work.thread.is_alive(), "TEST_ONLY worker exceeded teardown deadline"


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    instance = Bridge(tmp_path, monkeypatch)
    try:
        yield instance
    finally:
        instance.finish_fixture()


def test_actual_owned_bridge_natural_completion_delivers_only_fake_frame(bridge):
    bridge.start()
    bridge.await_owned("compile")
    assert not bridge.controller.start({"scenes": {"main": {}}}, bridge.key)
    bridge.release("compile")
    bridge.await_owned("runtime")
    bridge.confirm_exited("compile", natural=True)
    assert bridge.frames == []
    bridge.release("runtime")
    bridge.poll_closed()
    assert len(bridge.frames) == 1
    frame, state = bridge.frames[0]
    assert (frame.width, frame.height, frame.pixels) == (256, 128, PGM.split(b"\n", 3)[3])
    assert state["test_only_inert_bridge"] is True
    assert state["texts"] == ["TEST_ONLY_INERT_FAKE_FRAME"]
    assert state["simulation"]["hardware_transport"] == "mock"
    assert (bridge.base / "TEST_ONLY_fake_frame_copy.pgm").read_bytes() == PGM


@pytest.mark.parametrize("stage", ["compile", "runtime"])
def test_actual_owned_compile_or_runtime_cancel_has_no_frame_and_cleans_snapshot(bridge, stage):
    bridge.start()
    bridge.await_owned("compile")
    if stage == "runtime":
        bridge.release("compile")
        bridge.await_owned("runtime")
        bridge.confirm_exited("compile", natural=True)
    bridge.controller.stop()
    assert bridge.work.cancel.is_set() and bridge.controller.owns_work
    bridge.poll_closed()
    bridge.confirm_exited(stage, natural=False)
    assert bridge.frames == [] and bridge.controller.status == "stopped"
    assert len(bridge.records) == (1 if stage == "compile" else 2)


def test_actual_owned_document_switch_cancels_runtime_without_stale_delivery(bridge):
    bridge.start()
    bridge.await_owned("compile")
    bridge.release("compile")
    bridge.await_owned("runtime")
    bridge.confirm_exited("compile", natural=True)
    bridge.key = "TEST_ONLY_document_B"
    bridge.controller.sync_document(bridge.key)
    assert bridge.work.cancel.is_set() and bridge.controller.owns_work
    assert not bridge.controller.start({"scenes": {"main": {}}}, bridge.key)
    bridge.poll_closed()
    bridge.confirm_exited("runtime", natural=False)
    assert bridge.frames == []
    for _ in range(3):
        bridge.controller.poll(bridge.key)
    assert len(bridge.records) == 2 and bridge.frames == []


def test_mocked_inflight_uncertainty_is_retained_not_real_termination(tmp_path, monkeypatch):
    bridge = Bridge(tmp_path, monkeypatch, mocked_uncertainty=True)
    try:
        bridge.start()
        assert bridge.mock_marker.wait(timeout=MARKER_WAIT)
        wait_until(lambda: not bridge.work.thread.is_alive(), "mocked uncertainty worker return")
        bridge.controller.poll(bridge.key)
        assert bridge.controller.owns_work and bridge.work.cleanup_confirmed is None
        assert bridge.work.workspace.exists()
        assert (bridge.work.workspace / "scene.json").exists()
        retained_build = Path(bridge.work.retained_build)
        assert (retained_build / "TEST_ONLY_mocked_inflight_partial").exists()
        assert bridge.frames == bridge.records == [] and bridge.witnesses == {}
        assert bridge.controller.status.startswith("cleanup-uncertain")
        for _ in range(3):
            bridge.controller.stop()
            bridge.controller.poll(bridge.key)
            assert not bridge.controller.start({"scenes": {"main": {}}}, bridge.key)
        assert bridge.controller.owns_work and retained_build.exists()
    finally:
        bridge.finish_fixture()
