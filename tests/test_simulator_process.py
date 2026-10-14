"""Trusted inert Python fixtures only; ownership assertions concern this run alone.

Run this file with --noconftest and a fresh TEST_ONLY_simulator_process_* basetemp.
No compiler, native simulator, UI, hardware, network or parent environment probe
belongs in these tests. POSIX metadata checks are not POSIX runtime evidence.
"""

from __future__ import annotations

import ast
import inspect
import os
import sys
import threading
import time
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools import simulator_process as runner


def _python(source: str) -> list[str]:
    return [sys.executable, "-I", "-S", "-B", "-c", source]


@pytest.fixture
def child_env(tmp_path: Path) -> dict[str, str]:
    """Deliberately literal Windows root; never copy/read os.environ values."""
    if os.name == "nt":
        return {
            "SystemRoot": r"C:\Windows",
            "WINDIR": r"C:\Windows",
            "PATH": rf"C:\Windows\System32;C:\Windows;{Path(sys.executable).parent}",
            "TEMP": str(tmp_path),
            "TMP": str(tmp_path),
        }
    return {"PATH": "/usr/bin:/bin", "TMPDIR": str(tmp_path)}


def _run(source: str, tmp_path: Path, child_env: dict[str, str], **options):
    return runner.run_child(
        _python(source),
        cwd=tmp_path,
        env=child_env,
        timeout=options.pop("timeout", 5.0),
        output_limit=options.pop("output_limit", 1024 * 1024),
        **options,
    )


def _assert_clean_error(error: runner.SimulatorProcessError, code: str, limit: int):
    assert str(error) == code
    assert isinstance(error.stdout, bytes)
    assert isinstance(error.stderr, bytes)
    assert len(error.stdout) + len(error.stderr) <= limit
    assert error.cleanup_confirmed is True


@pytest.mark.parametrize(
    ("source", "stdout", "stderr"),
    [
        ("pass", b"", b""),
        (
            "import os; os.write(1, b'OUT\\x00\\xff'); os.write(2, b'ERR\\x00\\xfe')",
            b"OUT\x00\xff",
            b"ERR\x00\xfe",
        ),
    ],
)
def test_natural_exit_captures_bytes_and_returns_frozen_result(
    tmp_path, child_env, source, stdout, stderr
):
    result = _run(source, tmp_path, child_env)
    assert isinstance(result, runner.ProcessResult)
    assert result.returncode == 0
    assert result.stdout == stdout
    assert result.stderr == stderr
    assert result.ownership == ("windows-job" if os.name == "nt" else "posix-process-group")
    assert result.owned_scope_empty is True
    with pytest.raises(FrozenInstanceError):
        result.returncode = 9


def test_nonzero_exit_captures_both_streams(tmp_path, child_env):
    source = "import os,sys; os.write(1,b'nonzero-out'); os.write(2,b'nonzero-err'); sys.exit(7)"
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run(source, tmp_path, child_env)
    _assert_clean_error(caught.value, "simulator-child-failed", 1024 * 1024)
    assert caught.value.returncode == 7
    assert caught.value.stdout == b"nonzero-out"
    assert caught.value.stderr == b"nonzero-err"


def test_simultaneous_pipe_pressure_drains_without_deadlock(tmp_path, child_env):
    # Each pipe receives more than a typical pipe buffer, concurrently.
    source = (
        "import os,threading\n"
        "def emit(fd, value):\n"
        "    for _ in range(64):\n"
        "        block = value * 4096\n"
        "        while block:\n"
        "            block = block[os.write(fd, block):]\n"
        "a=threading.Thread(target=emit,args=(1,b'O'))\n"
        "b=threading.Thread(target=emit,args=(2,b'E'))\n"
        "a.start(); b.start(); a.join(); b.join()\n"
    )
    started = time.monotonic()
    result = _run(source, tmp_path, child_env, output_limit=512 * 1024)
    assert time.monotonic() - started < 8.0
    assert result.stdout == b"O" * (256 * 1024)
    assert result.stderr == b"E" * (256 * 1024)
    assert result.owned_scope_empty is True


@pytest.mark.parametrize(
    "source",
    [
        "import os; os.write(1,b'O'*131072)",
        "import os; os.write(2,b'E'*131072)",
        # Each individual stream fits; their combined size exceeds the cap.
        "import os; os.write(1,b'O'*3072); os.write(2,b'E'*3072)",
        (
            "import os,threading\n"
            "def flood(fd):\n"
            "    while True:\n"
            "        os.write(fd,b'X'*4096)\n"
            "a=threading.Thread(target=flood,args=(1,))\n"
            "b=threading.Thread(target=flood,args=(2,))\n"
            "a.start(); b.start(); a.join(); b.join()\n"
        ),
    ],
    ids=["stdout", "stderr", "combined", "concurrent-continuous"],
)
def test_output_cap_is_combined_and_cleanup_is_confirmed(tmp_path, child_env, source):
    started = time.monotonic()
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run(source, tmp_path, child_env, output_limit=4096)
    _assert_clean_error(caught.value, "simulator-output-limit", 4096)
    assert len(caught.value.stdout) + len(caught.value.stderr) == 4096
    assert time.monotonic() - started < 8.0


def test_short_deadline_terminates_inert_sleep_fixture(tmp_path, child_env):
    started = time.monotonic()
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run("import time; time.sleep(30)", tmp_path, child_env, timeout=0.1)
    _assert_clean_error(caught.value, "simulator-timeout", 1024 * 1024)
    # This is a generous cleanup bound, not a claim about scheduling precision.
    assert time.monotonic() - started < 6.0


def test_already_cancelled_request_never_constructs_owner_or_spawns(
    tmp_path, child_env, monkeypatch
):
    token = threading.Event()
    token.set()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("pre-cancelled request started owned work")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    monkeypatch.setattr(runner, "_WindowsJob" if os.name == "nt" else "_PosixGroup", forbidden)
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run("raise AssertionError('must not execute')", tmp_path, child_env, cancel_event=token)
    _assert_clean_error(caught.value, "simulator-cancelled", 1024 * 1024)
    assert caught.value.returncode is None
    assert calls == []


@pytest.mark.parametrize("close_fails", [False, True])
def test_cancellation_during_owner_construction_closes_unused_scope(
    tmp_path, child_env, monkeypatch, close_fails
):
    token = threading.Event()
    events = []

    class ObservedUnusedScope:
        def __init__(self):
            events.append("constructed")
            token.set()

        def close(self):
            events.append("closed")
            if close_fails:
                raise runner.SimulatorProcessError("TEST_ONLY-close-uncertain")

    def forbidden_popen(*args, **kwargs):
        raise AssertionError("cancelled owner released a payload")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden_popen)
    monkeypatch.setattr(
        runner, "_WindowsJob" if os.name == "nt" else "_PosixGroup", ObservedUnusedScope
    )
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run("pass", tmp_path, child_env, cancel_event=token)
    assert str(caught.value) == "simulator-cancelled"
    assert caught.value.cleanup_confirmed is (None if close_fails else True)
    assert caught.value.returncode is None
    assert events == ["constructed", "closed"]


def test_cancellation_stops_its_inert_child_and_confirms_cleanup(tmp_path, child_env):
    token = threading.Event()
    marker = tmp_path / "TEST_ONLY_cancellable_child_started"
    observed = []

    def cancel_after_start():
        deadline = time.monotonic() + 4.0
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.005)
        observed.append(marker.exists())
        token.set()

    request = threading.Thread(target=cancel_after_start)
    request.start()
    try:
        with pytest.raises(runner.SimulatorProcessError) as caught:
            _run(
                "from pathlib import Path; import time; "
                f"Path({str(marker)!r}).write_bytes(b'TEST_ONLY'); time.sleep(30)",
                tmp_path,
                child_env,
                timeout=6.0,
                cancel_event=token,
            )
    finally:
        request.join(timeout=5.0)
    assert not request.is_alive() and observed == [True]
    _assert_clean_error(caught.value, "simulator-cancelled", 1024 * 1024)
    assert caught.value.returncode is not None
    assert marker.read_bytes() == b"TEST_ONLY"


@pytest.mark.skipif(os.name != "nt", reason="requires the real Windows admission gate")
def test_cancel_before_windows_admission_never_executes_payload(tmp_path, child_env, monkeypatch):
    token = threading.Event()
    events = []
    original = runner._WindowsJob
    marker = tmp_path / "TEST_ONLY_cancelled_payload_must_not_run"

    class CancelAtAdmission(original):
        def attach(self, process):
            super().attach(process)
            events.append("attached")
            token.set()

        def terminate(self, process):
            events.append("terminate-owned-job")
            return super().terminate(process)

        def close(self):
            events.append(("empty-before-close", self.empty()))
            return super().close()

    monkeypatch.setattr(runner, "_WindowsJob", CancelAtAdmission)
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run(
            f"from pathlib import Path; Path({str(marker)!r}).write_bytes(b'TEST_ONLY')",
            tmp_path,
            child_env,
            cancel_event=token,
        )
    _assert_clean_error(caught.value, "simulator-cancelled", 1024 * 1024)
    assert events == ["attached", "terminate-owned-job", ("empty-before-close", True)]
    assert not marker.exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"command": []},
        {"command": "python"},
        {"command": iter([sys.executable])},
        {"command": ["relative-python", "-c", "pass"]},
        {"command": [sys.executable, 1]},
        {"command": [sys.executable, "bad\x00argument"]},
        {"command": [b"python"]},
        {"timeout": 0},
        {"timeout": -1},
        {"timeout": 60.1},
        {"timeout": float("nan")},
        {"timeout": float("inf")},
        {"timeout": float("-inf")},
        {"timeout": True},
        {"timeout": "1"},
        {"output_limit": 0},
        {"output_limit": -1},
        {"output_limit": 1024 * 1024 + 1},
        {"output_limit": True},
        {"output_limit": 1.5},
        {"env": None},
        {"env": []},
        {"env": {"TEST_ONLY": 1}},
        {"env": {1: "TEST_ONLY"}},
        {"env": {"BAD=KEY": "TEST_ONLY"}},
        {"env": {"TEST_ONLY": "bad\x00value"}},
        {"env": {"bad\x00key": "TEST_ONLY"}},
        {"cwd": Path("relative-workdir")},
        {"cwd": None},
        {"cancel_event": True},
        {"cancel_event": object()},
        {"cancel_event": lambda: True},
    ],
    ids=[
        "empty-command",
        "string-command",
        "iterator-command",
        "relative-executable",
        "integer-argument",
        "nul-argument",
        "bytes-executable",
        "zero-timeout",
        "negative-timeout",
        "excess-timeout",
        "nan-timeout",
        "infinite-timeout",
        "negative-infinite-timeout",
        "bool-timeout",
        "string-timeout",
        "zero-limit",
        "negative-limit",
        "excess-limit",
        "bool-limit",
        "float-limit",
        "none-env",
        "list-env",
        "integer-env-value",
        "integer-env-key",
        "equals-env-key",
        "nul-env-value",
        "nul-env-key",
        "relative-cwd",
        "none-cwd",
        "bool-cancel-event",
        "unknown-cancel-event",
        "callback-not-cancel-event",
    ],
)
def test_invalid_options_rejected_before_popen(tmp_path, child_env, monkeypatch, changes):
    calls = []

    def forbidden_popen(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("invalid options reached Popen")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden_popen)
    options = {
        "command": _python("pass"),
        "cwd": tmp_path,
        "env": child_env,
        "timeout": 5.0,
        "output_limit": 4096,
    }
    options.update(changes)
    try:
        with pytest.raises((TypeError, ValueError)):
            runner.run_child(**options)
    finally:
        assert calls == [], "invalid options reached Popen"


@pytest.mark.skipif(os.name != "nt", reason="requires a real Windows Job")
@pytest.mark.parametrize("wait_for_descendant", [True, False], ids=["parent-waits", "parent-exits"])
def test_windows_job_kills_its_created_inert_descendant(
    tmp_path, child_env, monkeypatch, wait_for_descendant
):
    events = []
    job_type = runner._WindowsJob

    class ObservedJob(job_type):
        def attach(self, process):
            super().attach(process)
            events.append("attached")

        def terminate(self, process):
            events.append("terminate-owned-job")
            return super().terminate(process)

        def close(self):
            if self.assigned:
                # Query this exact Job handle, never enumerate host processes.
                events.append(("empty-before-close", self.empty()))
            return super().close()

    monkeypatch.setattr(runner, "_WindowsJob", ObservedJob)
    marker = tmp_path / "TEST_ONLY_descendant_started"
    descendant = (
        "from pathlib import Path; import time; "
        f"Path({str(marker)!r}).write_bytes(b'TEST_ONLY'); time.sleep(30)"
    )
    source = (
        "import subprocess,sys\n"
        f"child=subprocess.Popen([sys.executable,'-I','-S','-B','-c',{descendant!r}])\n"
    )
    if wait_for_descendant:
        source += "child.wait()\n"
    started = time.monotonic()
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run(source, tmp_path, child_env, timeout=3.0)
    _assert_clean_error(caught.value, "simulator-timeout", 1024 * 1024)
    assert marker.read_bytes() == b"TEST_ONLY"
    assert events == ["attached", "terminate-owned-job", ("empty-before-close", True)]
    assert time.monotonic() - started < 8.0


@pytest.mark.skipif(os.name != "nt", reason="requires a real Windows Job")
@pytest.mark.parametrize("parent_exits", [False, True], ids=["root-active", "root-exited"])
def test_cancellation_stops_owned_descendant_even_after_root_exit(
    tmp_path, child_env, monkeypatch, parent_exits
):
    token = threading.Event()
    roots, events, observed = [], [], []
    popen, job_type = runner.subprocess.Popen, runner._WindowsJob
    marker = tmp_path / "TEST_ONLY_cancellable_descendant_started"

    def observe_popen(*args, **kwargs):
        root = popen(*args, **kwargs)
        roots.append(root)
        return root

    class ObservedJob(job_type):
        def terminate(self, process):
            events.append("terminate-owned-job")
            return super().terminate(process)

        def close(self):
            events.append(("empty-before-close", self.empty()))
            return super().close()

    def cancel_after_descendant():
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            if marker.exists() and roots and (not parent_exits or roots[0].poll() is not None):
                observed.append(True)
                break
            time.sleep(0.005)
        else:
            observed.append(False)
        token.set()

    monkeypatch.setattr(runner.subprocess, "Popen", observe_popen)
    monkeypatch.setattr(runner, "_WindowsJob", ObservedJob)
    descendant = (
        "from pathlib import Path; import time; "
        f"Path({str(marker)!r}).write_bytes(b'TEST_ONLY'); time.sleep(30)"
    )
    source = (
        "import subprocess,sys\n"
        f"child=subprocess.Popen([sys.executable,'-I','-S','-B','-c',{descendant!r}])\n"
        + ("" if parent_exits else "child.wait()\n")
    )
    request = threading.Thread(target=cancel_after_descendant)
    request.start()
    try:
        with pytest.raises(runner.SimulatorProcessError) as caught:
            _run(source, tmp_path, child_env, timeout=6.0, cancel_event=token)
    finally:
        request.join(timeout=5.0)
    assert not request.is_alive() and observed == [True]
    _assert_clean_error(caught.value, "simulator-cancelled", 1024 * 1024)
    assert marker.read_bytes() == b"TEST_ONLY"
    assert len(roots) == 1 and roots[0].poll() is not None
    if parent_exits:
        # Exit 0 of the root alone must not release a still-live owned child.
        assert caught.value.returncode == 0
    assert events == ["terminate-owned-job", ("empty-before-close", True)]


@pytest.mark.skipif(os.name != "nt", reason="requires the real Windows admission gate")
def test_windows_assignment_failure_never_releases_gate_or_runs_payload(
    tmp_path, child_env, monkeypatch
):
    marker = tmp_path / "TEST_ONLY_payload_must_never_run"
    roots = []
    gate_writes = []
    popen = runner.subprocess.Popen

    class ObservedStdin:
        def __init__(self, stream):
            self.stream = stream

        def write(self, value):
            gate_writes.append(value)
            return self.stream.write(value)

        def close(self):
            return self.stream.close()

    def observe_popen(*args, **kwargs):
        process = popen(*args, **kwargs)
        process.stdin = ObservedStdin(process.stdin)
        return process

    def fail_attach(self, process):
        roots.append(process)
        raise runner.SimulatorProcessError("TEST_ONLY-assignment-failed")

    monkeypatch.setattr(runner.subprocess, "Popen", observe_popen)
    monkeypatch.setattr(runner._WindowsJob, "attach", fail_attach)
    source = f"from pathlib import Path; Path({str(marker)!r}).write_bytes(b'TEST_ONLY')"
    with pytest.raises(runner.SimulatorProcessError) as caught:
        _run(source, tmp_path, child_env)
    assert str(caught.value) == "TEST_ONLY-assignment-failed"
    assert len(roots) == 1
    assert roots[0].poll() is not None
    assert gate_writes == []
    assert not marker.exists()
    assert caught.value.stdout == b""
    assert caught.value.stderr == b""


def test_posix_ownership_is_only_source_metadata_not_host_execution():
    # Parse source rather than constructing a group or mocking the host OS.
    tree = ast.parse(inspect.getsource(runner._PosixGroup))
    assignments = [
        node
        for node in tree.body[0].body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "ownership" for target in node.targets
        )
    ]
    assert len(assignments) == 1
    assert ast.literal_eval(assignments[0].value) == "posix-process-group"
