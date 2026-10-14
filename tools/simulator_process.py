"""Bounded trusted simulator children, not a sandbox or hardware attestation.

Windows admission happens only after a private non-breakaway Job owns the gated
Python root. POSIX preserves the existing compiler runner using one new process
group; it does not claim ownership of children that escape that group.
"""

from __future__ import annotations

import ctypes
import math
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

OUTPUT_LIMIT = 1024 * 1024
CLEANUP_SECONDS = 2.0
_GATE = (
    "import os,subprocess,sys; admitted=os.read(sys.stdin.fileno(),1); "
    "sys.exit(subprocess.call(sys.argv[1:],stdin=subprocess.DEVNULL) "
    "if admitted==b'x' else 125)"
)


class SimulatorProcessError(RuntimeError):
    """Fixed code plus bounded captured data; no parent environment reflection."""

    def __init__(self, code, *, stdout=b"", stderr=b"", cleanup_confirmed=None, returncode=None):
        super().__init__(code)
        self.stdout = stdout
        self.stderr = stderr
        self.cleanup_confirmed = cleanup_confirmed
        # Observed root status after cleanup, not a natural-completion claim.
        self.returncode = returncode


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    ownership: str
    owned_scope_empty: bool


class _WindowsJob:
    ownership = "windows-job"

    def __init__(self):
        from ctypes import wintypes as w

        class Basic(ctypes.Structure):
            _fields_ = [
                ("user", ctypes.c_int64),
                ("job", ctypes.c_int64),
                ("flags", w.DWORD),
                ("min", ctypes.c_size_t),
                ("max", ctypes.c_size_t),
                ("active", w.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class Limits(ctypes.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", ctypes.c_uint64 * 6),
                ("memory", ctypes.c_size_t * 4),
            ]

        class Accounting(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_int64)
                for name in ("user", "kernel", "period_user", "period_kernel")
            ]
            _fields_ += [(name, w.DWORD) for name in ("faults", "total", "active", "terminated")]

        self.accounting = Accounting
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, arguments, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            ("SetInformationJobObject", [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            ("AssignProcessToJobObject", [w.HANDLE, w.HANDLE], w.BOOL),
            (
                "QueryInformationJobObject",
                [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p],
                w.BOOL,
            ),
            ("TerminateJobObject", [w.HANDLE, w.UINT], w.BOOL),
            ("CloseHandle", [w.HANDLE], w.BOOL),
        ):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.kernel.CreateJobObjectW(None, None)
        self._check(self.handle)
        self.assigned = False
        limits = Limits()
        limits.basic.flags = 0x2000  # Kill-on-close, no breakaway flags.
        try:
            self._check(
                self.kernel.SetInformationJobObject(
                    self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
                )
            )
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _check(value):
        if not value:
            raise SimulatorProcessError("simulator-job-operation-failed")

    def attach(self, process):
        self._check(self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)))
        self.assigned = True

    def empty(self):
        if not self.assigned:
            return False
        if ctypes.sizeof(self.accounting) != 48 or self.accounting.active.offset != 40:
            raise SimulatorProcessError("simulator-job-accounting-abi")
        value = self.accounting()
        self._check(
            self.kernel.QueryInformationJobObject(
                self.handle, 1, ctypes.byref(value), ctypes.sizeof(value), None
            )
        )
        return value.active == 0

    def terminate(self, process):
        if self.assigned:
            self._check(self.kernel.TerminateJobObject(self.handle, 125))
        elif process.poll() is None:
            # Only the unreleased Popen root, not a discovered or unrelated PID.
            process.kill()

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            self._check(self.kernel.CloseHandle(handle))


class _PosixGroup:
    ownership = "posix-process-group"

    def __init__(self):
        self.group = None

    def attach(self, process):
        # start_new_session created this exact group before exec. No PID scan.
        self.group = process.pid

    def empty(self):
        try:
            os.killpg(self.group, 0)
            return False
        except ProcessLookupError:
            return True

    def terminate(self, process):
        try:
            os.killpg(self.group, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def close(self):
        pass


def run_child(
    command,
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    output_limit: int = OUTPUT_LIMIT,
    cancel_event: threading.Event | None = None,
) -> ProcessResult:
    """Run an already trusted compiler/runtime command, with no shell or stdin.

    Source/command selection belongs to the simulator. Timeout/overflow/failure
    never becomes success. Only this run's owned Job/process group is terminated.
    Cancellation is latched by the caller's Event; it never transfers process
    ownership. A cancellation error only confirms cleanup after the same root,
    owned-scope and reader checks as every other failure. An already-set Event
    prevents process creation and reports confirmed no-child cleanup.
    """
    if (
        type(command) not in (list, tuple)
        or not command
        or any(type(arg) not in (str, Path) and not isinstance(arg, Path) for arg in command)
        or any("\0" in str(arg) for arg in command)
        or not Path(command[0]).is_absolute()
        or type(timeout) not in (int, float)
        or not math.isfinite(timeout)
        or not 0 < timeout <= 60
        or type(output_limit) is not int
        or not 0 < output_limit <= OUTPUT_LIMIT
        or type(env) is not dict
        or (cancel_event is not None and type(cancel_event) is not threading.Event)
        or any(type(key) is not str or type(value) is not str for key, value in env.items())
        or any(not key or "=" in key or "\0" in key or "\0" in value for key, value in env.items())
    ):
        raise ValueError("simulator-child-options-invalid")
    cwd = Path(cwd)
    if not cwd.is_absolute() or "\0" in str(cwd):
        raise ValueError("simulator-cwd-absolute-required")
    if cancel_event is not None and cancel_event.is_set():
        raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)
    scope = _WindowsJob() if os.name == "nt" else _PosixGroup()
    process = None
    readers = []
    chunks = {"stdout": [], "stderr": []}
    lock = threading.Lock()
    stopped = threading.Event()
    stored = 0
    reader_failed = False
    failure = None
    cleanup_confirmed = None
    started = time.monotonic()

    def check_cancel():
        if cancel_event is not None and cancel_event.is_set():
            raise SimulatorProcessError("simulator-cancelled")

    def read(stream, name):
        nonlocal stored, reader_failed
        try:
            while block := stream.read(16384):
                with lock:
                    keep = min(len(block), output_limit - stored)
                    if keep:
                        chunks[name].append(block[:keep])
                        stored += keep
                    if keep != len(block):
                        stopped.set()
        except (OSError, ValueError):
            reader_failed = True
            stopped.set()
        finally:
            stream.close()

    try:
        # A request may arrive during owner construction; do not create a root
        # after it. The finally block still closes the unused scope.
        check_cancel()
        options = dict(
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            close_fds=True,
            shell=False,
        )
        if os.name == "nt":
            process = subprocess.Popen(
                [sys.executable, "-I", "-S", "-B", "-c", _GATE, *map(str, command)],
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                **options,
            )
        else:
            process = subprocess.Popen(
                list(map(str, command)), stdin=subprocess.DEVNULL, start_new_session=True, **options
            )
        scope.attach(process)
        for name in ("stdout", "stderr"):
            thread = threading.Thread(target=read, args=(getattr(process, name), name), daemon=True)
            readers.append(thread)
            thread.start()
        check_cancel()
        if os.name == "nt":
            process.stdin.write(b"x")
            process.stdin.close()
        while process.poll() is None or not scope.empty() or any(t.is_alive() for t in readers):
            check_cancel()
            if stopped.is_set():
                raise SimulatorProcessError(
                    "simulator-reader-failed" if reader_failed else "simulator-output-limit"
                )
            if time.monotonic() - started >= timeout:
                raise SimulatorProcessError("simulator-timeout")
            time.sleep(0.005)
        check_cancel()
        if stopped.is_set():
            raise SimulatorProcessError(
                "simulator-reader-failed" if reader_failed else "simulator-output-limit"
            )
        if process.returncode != 0:
            raise SimulatorProcessError("simulator-child-failed")
        cleanup_confirmed = True
    except BaseException as error:
        failure = error
    finally:
        if (
            process is None
            and isinstance(failure, SimulatorProcessError)
            and str(failure) == "simulator-cancelled"
        ):
            cleanup_confirmed = True
        if process is not None and cleanup_confirmed is not True:
            try:
                scope.terminate(process)
                process.wait(timeout=CLEANUP_SECONDS)
                deadline = time.monotonic() + CLEANUP_SECONDS
                while not scope.empty() and time.monotonic() < deadline:
                    time.sleep(0.005)
                cleanup_confirmed = scope.empty()
            except (OSError, subprocess.TimeoutExpired, SimulatorProcessError):
                cleanup_confirmed = None
        try:
            scope.close()
        except SimulatorProcessError:
            cleanup_confirmed = None
            if failure is None:
                failure = SimulatorProcessError("simulator-job-close-failed")
        for thread in readers:
            thread.join(timeout=CLEANUP_SECONDS)
        if any(thread.is_alive() for thread in readers):
            cleanup_confirmed = None
            if failure is None:
                failure = SimulatorProcessError("simulator-reader-not-joined")
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            for name in ("stdout", "stderr"):
                stream = getattr(process, name)
                if stream is not None and not any(thread.is_alive() for thread in readers):
                    stream.close()
    stdout, stderr = (b"".join(chunks[name]) for name in ("stdout", "stderr"))
    if failure is not None:
        if isinstance(failure, (KeyboardInterrupt, SystemExit)):
            raise failure
        code = (
            str(failure)
            if isinstance(failure, SimulatorProcessError)
            else "simulator-launch-failed"
        )
        raise SimulatorProcessError(
            code,
            stdout=stdout,
            stderr=stderr,
            cleanup_confirmed=cleanup_confirmed,
            returncode=None if process is None else process.returncode,
        ) from None
    return ProcessResult(process.returncode, stdout, stderr, scope.ownership, True)
