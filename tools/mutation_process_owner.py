"""Dedicated Linux mutation-process owner, including detached descendants.

No global PID scan or process-group kill. A subreaper adopts orphaned descendants;
only direct children verified through waitid(P_PIDFD) may receive a signal. Exit
requires both ECHILD and stdout EOF. An uncertain cleanup keeps ownership, never
authorizes reports. This does not sandbox hostile code or prevent supervisor
SIGKILL; it manages the ordinary public CI test tree.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import select
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from typing import Callable


class ScopeUnavailable(RuntimeError):
    """Required ownership primitives are unavailable; do not launch a fallback."""


@dataclass(frozen=True)
class Outcome:
    root_returncode: int | None
    reason: str
    reaped: int
    tree_empty: bool
    stdout_eof: bool


class _StdoutSink:
    """Bounded nonblocking sink, pumped by the ownership loop, not a thread."""

    LIMIT = 262_144

    def __init__(self, fd: int):
        self.fd = fd
        self.buffer = bytearray()

    def __call__(self, data: bytes) -> None:
        if len(self.buffer) + len(data) > self.LIMIT:
            raise BufferError("owned log buffer exceeds bound")
        self.buffer.extend(data)

    def flush(self) -> None:
        if not self.buffer:
            return
        try:
            written = os.write(self.fd, self.buffer)
        except BlockingIOError:
            return  # Temporary backpressure is not a process failure.
        if written == 0:
            raise OSError("log sink accepted no bytes")
        del self.buffer[:written]

    def can_accept(self) -> bool:
        return len(self.buffer) <= self.LIMIT - 65_536


def _waitable_children() -> bool:
    try:
        os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return False
    return True  # None means running children, not absence of children.


def _admit() -> ctypes.CDLL:
    if (
        sys.platform != "linux"
        or threading.active_count() != 1
        or not all(hasattr(os, name) for name in ("pidfd_open", "P_PIDFD", "WNOWAIT"))
        or not hasattr(signal, "pidfd_send_signal")
        or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL
        or _waitable_children()
    ):
        raise ScopeUnavailable("requires an isolated Linux owner with no existing children")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    libc.prctl.restype = ctypes.c_int
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.addressof(previous), 0, 0, 0) != 0 or previous.value != 0:
        raise ScopeUnavailable("dedicated subreaper admission unavailable")
    fd = os.pidfd_open(os.getpid())
    try:
        signal.pidfd_send_signal(fd, 0)
        try:
            os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            pass  # Our own process must not be an owned child.
        else:
            raise ScopeUnavailable("pidfd ownership check unavailable")
    finally:
        os.close(fd)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise ScopeUnavailable("subreaper activation failed")
    return libc


def _direct_children() -> list[int]:
    # This one owner's kernel-maintained child list, never /proc-wide discovery.
    path = f"/proc/{os.getpid()}/task/{os.getpid()}/children"
    with open(path, "rb") as stream:
        data = stream.read(65_537)
    if len(data) > 65_536:
        raise ScopeUnavailable("owned child list exceeds bound")
    values = data.split()
    if any(not value.isdigit() for value in values):
        raise ScopeUnavailable("invalid owned child list")
    return [int(value) for value in values]


def _child_fd(pid: int) -> int | None:
    try:
        fd = os.pidfd_open(pid)
    except ProcessLookupError:
        return None
    try:
        os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        os.close(fd)
        return None  # Recycled/non-child IDs can never become signal authority.
    except BaseException:
        os.close(fd)
        raise
    return fd


def _emergency_drain(children: dict[int, int], root: subprocess.Popen[bytes]) -> None:
    # Even an unexpected Python/IO exception may not abandon the owned tree.
    # PID descriptors plus kernel child ownership remain the only signal target.
    while _waitable_children():
        try:
            for pid in _direct_children():
                if pid not in children:
                    fd = _child_fd(pid)
                    if fd is not None:
                        children[pid] = fd
            for pid, fd in list(children.items()):
                info = os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG)
                if info is not None:
                    if pid == root.pid:
                        root.returncode = (
                            info.si_status if info.si_code == os.CLD_EXITED else -info.si_status
                        )
                    os.close(children.pop(pid))
                else:
                    try:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        except OSError:
            # Unknown ownership/cleanup cannot authorize return or reports.
            pass
        time.sleep(0.01)


def run_owned(
    command: list[str], *, deadline_seconds: float, output: Callable[[bytes], None]
) -> Outcome:
    """Run isolated, retaining ownership through reap/drain; callbacks must not block."""
    if (
        not command
        or any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command)
        or not math.isfinite(deadline_seconds)
        or not 0 < deadline_seconds <= 1020
        or not callable(output)
    ):
        raise ValueError("invalid owned process request")
    libc = _admit()
    reason = "natural"
    stop_at: float | None = None
    old_signals = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}

    def cancelled(_sig: int, _frame: object) -> None:
        nonlocal reason, stop_at
        if stop_at is None:
            reason, stop_at = "cancelled", time.monotonic()

    for sig in old_signals:
        signal.signal(sig, cancelled)
    children: dict[int, int] = {}
    root: subprocess.Popen[bytes] | None = None
    root_returncode: int | None = None
    reaped = 0
    eof = False
    launched_at = time.monotonic()
    pending_notice = False
    sink_failed = False
    selector = selectors.DefaultSelector()
    try:
        root = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
        root_fd = _child_fd(root.pid)
        if root_fd is None:
            raise ScopeUnavailable("created root ownership unavailable")
        children[root.pid] = root_fd
        assert root.stdout is not None
        os.set_blocking(root.stdout.fileno(), False)
        selector.register(root.stdout, selectors.EVENT_READ)
        while True:
            now = time.monotonic()
            if stop_at is None and now - launched_at >= deadline_seconds:
                reason, stop_at = "timeout", now
            if isinstance(output, _StdoutSink) and not sink_failed:
                if stop_at is not None:
                    output.buffer.clear()
                    sink_failed = True  # Drain discarded child output during cleanup.
                else:
                    try:
                        output.flush()
                    except OSError:
                        output.buffer.clear()
                        sink_failed = True
                        reason, stop_at = "output-error", now
            try:
                for pid in _direct_children():
                    if pid not in children:
                        fd = _child_fd(pid)
                        if fd is not None:
                            children[pid] = fd
                for pid, fd in list(children.items()):
                    info = os.waitid(os.P_PIDFD, fd, os.WEXITED | os.WNOHANG)
                    if info is not None:
                        code = info.si_status if info.si_code == os.CLD_EXITED else -info.si_status
                        if pid == root.pid:
                            root_returncode = root.returncode = code
                        reaped += 1
                        os.close(children.pop(pid))
                    elif stop_at is not None:
                        try:
                            signal.pidfd_send_signal(
                                fd, signal.SIGKILL if now - stop_at >= 1 else signal.SIGTERM
                            )
                        except ProcessLookupError:
                            pass
                empty = not children and not _waitable_children()
            except (OSError, ScopeUnavailable):
                empty = False
                if stop_at is None:
                    reason, stop_at = "scope-error", now
            for key, _ in selector.select(timeout=0.01):
                if isinstance(output, _StdoutSink) and not sink_failed and not output.can_accept():
                    time.sleep(0.01)  # A readable full pipe must not make a busy-spin loop.
                    continue  # Supervise deadlines while the bounded sink drains.
                try:
                    chunk = os.read(key.fileobj.fileno(), 65_536)
                except BlockingIOError:
                    continue
                if chunk:
                    if not sink_failed:
                        try:
                            output(chunk)
                        except Exception:
                            sink_failed = True
                            if stop_at is None:
                                reason, stop_at = "output-error", time.monotonic()
                else:
                    eof = True
                    selector.unregister(key.fileobj)
            sink_empty = not isinstance(output, _StdoutSink) or not output.buffer
            if empty and eof and sink_empty:
                return Outcome(root_returncode, reason, reaped, True, True)
            if stop_at is not None and now - stop_at >= 30 and not pending_notice:
                # No receipt/return while cleanup is uncertain. The outer CI
                # step may stop us; reports must not run without a receipt.
                pending_notice = True
                print(
                    "[owned-scope] cleanup pending; no emptiness receipt",
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        # Normal return only follows ECHILD+EOF. Never kill discovered siblings.
        if root is not None and _waitable_children():
            _emergency_drain(children, root)
        selector.close()
        if root is None:
            libc.prctl(36, 0, 0, 0, 0)
        elif not _waitable_children():
            if root.stdout is not None:
                root.stdout.close()
            libc.prctl(36, 0, 0, 0, 0)
        for sig, previous in old_signals.items():
            signal.signal(sig, previous)


def verify_receipt(path: str) -> bool:
    """An absent/unfinished owner receipt cannot authorize diagnostic jobs."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096:
                return False
            raw = os.read(fd, 4097)
        finally:
            os.close(fd)

        def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError("duplicate receipt field")
                result[key] = item
            return result

        value = json.loads(raw, object_pairs_hook=unique_fields)
        result = value["outcome"]
        return (
            set(value) == {"operation", "outcome"}
            and value["operation"] == "run"
            and set(result) == {"root_returncode", "reason", "reaped", "tree_empty", "stdout_eof"}
            and result["tree_empty"] is True
            and result["stdout_eof"] is True
            and type(result["reaped"]) is int
            and result["reaped"] >= 1
            and type(result["root_returncode"]) is int
            and result["reason"]
            in {"natural", "timeout", "cancelled", "output-error", "scope-error"}
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("run", "results", "html", "verify"))
    parser.add_argument("--deadline-seconds", type=float)
    parser.add_argument("--receipt-file", required=True)
    args = parser.parse_args()
    if args.operation == "verify":
        return 0 if verify_receipt(args.receipt_file) else 70
    if args.deadline_seconds is None:
        parser.error("deadline-seconds required for a process operation")
    try:
        # Reserve a fresh owner artifact BEFORE any child can run. Only the
        # supervisor writes its final receipt, after actual reaping and EOF.
        receipt_fd = os.open(
            args.receipt_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
    except OSError:
        return 70
    # Only the fixed installed public mutation module, not a caller command.
    command = [sys.executable, "-u", "-m", "mutmut", args.operation]
    if args.operation == "run":
        command.append("--no-progress")
    output_fd = sys.stdout.fileno()
    previous_blocking = os.get_blocking(output_fd)
    os.set_blocking(output_fd, False)

    def emit(data: bytes) -> None:
        # Only the final notice uses this function, AFTER owned tree drain.
        # Give a continuously draining pipe a short bounded readiness window.
        pending = memoryview(data)
        until = time.monotonic() + 1
        while pending:
            try:
                written = os.write(output_fd, pending)
            except BlockingIOError:
                remaining = until - time.monotonic()
                if remaining <= 0:
                    raise
                select.select([], [output_fd], [], min(0.05, remaining))
                continue
            if written == 0:
                raise OSError("log sink accepted no bytes")
            pending = pending[written:]

    try:
        try:
            outcome = run_owned(
                command, deadline_seconds=args.deadline_seconds, output=_StdoutSink(output_fd)
            )
        except (ValueError, ScopeUnavailable, OSError):
            print("[owned-scope] unavailable; no fallback launched", file=sys.stderr, flush=True)
            return 70
        receipt = json.dumps(
            {"operation": args.operation, "outcome": asdict(outcome)}, sort_keys=True
        ).encode()
        pending_receipt = memoryview(receipt)
        while pending_receipt:
            written = os.write(receipt_fd, pending_receipt)
            if written == 0:
                return 74
            pending_receipt = pending_receipt[written:]
        os.fsync(receipt_fd)
        try:
            emit(("\n[owned-scope] " + json.dumps(asdict(outcome), sort_keys=True) + "\n").encode())
        except OSError:
            return 74  # No trustworthy output receipt; reports must be skipped.
    finally:
        os.close(receipt_fd)
        os.set_blocking(output_fd, previous_blocking)
    if outcome.reason == "timeout":
        return 124
    if outcome.reason == "cancelled":
        return 130
    if outcome.reason != "natural":
        return 74
    if outcome.root_returncode is None:
        return 74
    return (
        outcome.root_returncode if outcome.root_returncode >= 0 else 128 - outcome.root_returncode
    )


if __name__ == "__main__":
    raise SystemExit(main())
