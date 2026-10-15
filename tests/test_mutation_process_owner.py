"""Linux runtime contract for mutation_process_owner; run directly with unittest.

    /usr/bin/python3 -I -B tests/test_mutation_process_owner.py -v

Every run_owned call is in a fresh, single-threaded interpreter. The unittest
process never becomes a subreaper. Fixtures are inert and have finite lifetimes;
no mutmut, SDK, GUI, process-group signals, or global PID discovery is used.
Windows execution is explicitly source-only and skips the runtime tests.
"""

# Deliberately executable with stdlib unittest, including under python -O.
# ruff: noqa: PT009

from __future__ import annotations

import json
import os
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()
MODULE_FILE = ROOT / "tools" / "mutation_process_owner.py"
FIXTURE_LIFETIME = 5.0

# Only this fresh interpreter imports the supervisor. No helper threads or
# pre-existing children, and no SIGCHLD handler, are installed before run_owned.
HELPER = r"""
import dataclasses
import errno
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root, folder, command_json, config_json = sys.argv[1:]
sys.path.insert(0, root)
from tools import mutation_process_owner as owner

folder = Path(folder)
command = json.loads(command_json)
config = json.loads(config_json)
launches = []
forbidden_operations = []
chunks = []
callback_types = []
callback_calls = 0

def audit(event, args):
    if event in ('subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty'):
        launches.append(event)
    if event in ('os.kill', 'os.killpg'):
        forbidden_operations.append(event)
    if event in ('os.listdir', 'os.scandir') and args and not isinstance(args[0], int):
        if os.path.normpath(os.fsdecode(args[0])) == '/proc':
            forbidden_operations.append(event + ':/proc')

sys.addaudithook(audit)

def output(data):
    global callback_calls
    callback_calls += 1
    callback_types.append(type(data).__name__)
    if not isinstance(data, bytes):
        raise TypeError('run_owned output must be bytes')
    if config.get('output_error'):
        raise RuntimeError('intentional isolated output callback failure')
    chunks.append(data.hex())

patch = config.get('patch')
if patch == 'pidfd_open_missing':
    del os.pidfd_open
elif patch == 'pidfd_send_signal_missing':
    del signal.pidfd_send_signal
elif patch == 'P_PIDFD_missing':
    del os.P_PIDFD
elif patch == 'pidfd_open_enosys':
    def unavailable(*args, **kwargs):
        raise OSError(errno.ENOSYS, 'intentional pidfd capability failure')
    os.pidfd_open = unavailable

# Cover a module's direct imports as well as os/signal attribute lookups.
if patch:
    attr = {
        'pidfd_open_missing': 'pidfd_open',
        'pidfd_send_signal_missing': 'pidfd_send_signal',
        'P_PIDFD_missing': 'P_PIDFD',
        'pidfd_open_enosys': 'pidfd_open',
    }[patch]
    if hasattr(owner, attr):
        if patch == 'pidfd_open_enosys':
            setattr(owner, attr, unavailable)
        else:
            setattr(owner, attr, None)

deadline = config.get('deadline', 2.0)
if config.get('deadline_kind') == 'nan':
    deadline = math.nan
elif config.get('deadline_kind') == 'inf':
    deadline = math.inf

preexisting = None
preexisting_fd = None
if config.get('admission') == 'preexisting-child':
    preexisting = subprocess.Popen(
        [sys.executable, '-I', '-B', '-c', 'import time; time.sleep(0.5)'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    preexisting_fd = os.pidfd_open(preexisting.pid)
    stat = Path('/proc/%s/stat' % preexisting.pid).read_text()
    identity = '%s:%s' % (preexisting.pid, stat[stat.rfind(')') + 2:].split()[19])
    (folder / 'preexisting.pid').write_text(identity, encoding='ascii')
    launches.clear()  # The deliberately created admission control isn't a launch by owner.
if config.get('admission') == 'SIGCHLD-ignored':
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

started = time.monotonic()
result = {'chunks': chunks, 'callback_types': callback_types}
try:
    outcome = owner.run_owned(command, deadline_seconds=deadline, output=output)
    result['is_dataclass'] = dataclasses.is_dataclass(outcome)
    result['outcome'] = {name: getattr(outcome, name) for name in
        ('root_returncode', 'reason', 'reaped', 'tree_empty', 'stdout_eof')}
except BaseException as exc:
    result['exception'] = {'type': type(exc).__name__, 'message': str(exc),
                           'bases': [cls.__name__ for cls in type(exc).__mro__]}
if preexisting is not None:
    try:
        result['preexisting_returncode'] = preexisting.wait(timeout=2)
    finally:
        if preexisting.poll() is None:
            signal.pidfd_send_signal(preexisting_fd, signal.SIGKILL)
            preexisting.wait(timeout=2)
        os.close(preexisting_fd)
result.update(elapsed=time.monotonic() - started, launches=launches,
              callback_calls=callback_calls, forbidden_operations=forbidden_operations)
(folder / 'result.json').write_text(json.dumps(result), encoding='utf-8')
"""


# Generated only inside each CLI test's private temporary CWD. The real CLI's
# fixed `python -u -m mutmut OPERATION` imports this inert module from that CWD.
CLI_FIXTURE = r"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

folder = Path.cwd()
config = json.loads((folder / 'cli-fixture.json').read_text())
stat = Path('/proc/%s/stat' % os.getpid()).read_text()
identity = '%s:%s' % (os.getpid(), stat[stat.rfind(')') + 2:].split()[19])
(folder / 'root.pid').write_text(identity, encoding='ascii')
receipt = folder / config['receipt']
observation = {'argv': sys.argv[1:], 'receipt_exists': receipt.is_file(),
               'receipt_size_at_launch': receipt.stat().st_size if receipt.is_file() else None}
(folder / 'cli-launch.json').write_text(json.dumps(observation))
scenario = config['scenario']
if scenario == 'natural':
    os.write(1, b'inert-fixed-operation\n')
    raise SystemExit(0)
if scenario == 'burst':
    signal.alarm(5)  # Bound even a blocking write if a broken owner stops reading.
    pending = memoryview(bytes(range(256)) * 512)  # Exactly 128 KiB, including binary bytes.
    while pending:
        pending = pending[os.write(1, pending):]
    raise SystemExit(0)

signal.signal(signal.SIGTERM, signal.SIG_IGN)
subprocess.Popen([sys.executable, '-I', '-B', config['test_file'], '--fixture',
                  str(folder), 'timeout', 'child'], start_new_session=True)
end = time.monotonic() + 1.5
while not (folder / 'grandchild.pid').exists():
    if time.monotonic() >= end:
        raise RuntimeError('inert CLI tree never became ready')
    time.sleep(0.005)
(folder / 'scope-ready').write_text('ready')
if scenario == 'detached-timeout':
    os.write(1, b'inert-root-exiting-zero\n')
    raise SystemExit(0)

# A finite, nonblocking producer: even a broken supervisor can't leave this
# fixture permanently blocked in os.write. Descendants are finite as well.
os.set_blocking(1, False)
end = time.monotonic() + 5.0
while time.monotonic() < end:
    try:
        os.write(1, b'inert-log-flood\n' * 8192)
    except BlockingIOError:
        time.sleep(0.005)
raise SystemExit(0)
"""

CLI_CAPABILITY_HELPER = r"""
import errno
import json
import os
from pathlib import Path
import runpy
import sys

module, audit_file, *arguments = sys.argv[1:]
launches = []
def audit(event, args):
    if event in ('subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty'):
        launches.append(event)
sys.addaudithook(audit)
def unavailable(*args, **kwargs):
    raise OSError(errno.ENOSYS, 'intentional CLI kernel capability failure')
os.pidfd_open = unavailable
sys.argv = [module, *arguments]
try:
    runpy.run_path(module, run_name='__main__')
finally:
    Path(audit_file).write_text(json.dumps(launches))
"""

CLI_VERIFY_HELPER = r"""
import json
import sys
sys.path.insert(0, sys.argv[1])
from tools import mutation_process_owner as owner
valid = owner.verify_receipt(sys.argv[2])
print(json.dumps({'valid': valid}))
raise SystemExit(0 if valid else 70)
"""


def _identity(pid: int) -> str | None:
    """Read only this fixture's PID, including starttime to reject PID reuse."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    except FileNotFoundError:
        return None
    # comm can contain spaces and closing parentheses; fields after its last ).
    fields = stat[stat.rfind(")") + 2 :].split()
    return f"{pid}:{fields[19]}"  # proc stat field 22: starttime


def _mark(folder: Path, name: str, text: str = "ready") -> None:
    # Runtime fixture artifacts only; never write repository sources.
    temporary = folder / f"{name}.{os.getpid()}.tmp"
    temporary.write_text(text, encoding="ascii")
    temporary.replace(folder / name)


def _wait_marker(folder: Path, name: str, seconds: float = 1.5) -> None:
    deadline = time.monotonic() + seconds
    while not (folder / name).exists():
        if time.monotonic() >= deadline:
            raise RuntimeError(f"inert fixture did not create {name}")
        time.sleep(0.005)


def _fixture(folder: Path, scenario: str, role: str) -> int:
    """Explicitly inert process tree. All branches terminate within five seconds."""
    _mark(folder, f"{role}.pid", _identity(os.getpid()) or "")
    if scenario in ("timeout", "detached-timeout", "cancel", "output-error"):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

    def spawn(child_role: str) -> subprocess.Popen:
        return subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                str(THIS_FILE),
                "--fixture",
                str(folder),
                scenario,
                child_role,
            ],
            start_new_session=True,
        )

    if role == "control":
        deadline = time.monotonic() + FIXTURE_LIFETIME
        while not (folder / "release-control").exists():
            if time.monotonic() >= deadline:
                return 23
            time.sleep(0.01)
        _mark(folder, "control-survived")
        return 0
    if scenario == "zero":
        os.write(1, b"natural-zero\n")
        return 0
    if scenario == "nonzero":
        os.write(1, b"natural-nonzero\n")
        return 17
    if role == "root":
        spawn("child")
        _wait_marker(folder, "child.pid")
        if scenario in ("timeout", "detached-timeout", "cancel", "output-error"):
            _wait_marker(folder, "grandchild.pid")
        _mark(folder, "scope-ready")
        if scenario in ("retained", "stdout", "detached-timeout"):
            os.write(1, b"root-exiting\n")
            _mark(folder, "root-exiting")
            return 0
        if scenario == "output-error":
            os.write(1, b"trigger-callback-error\n")
    elif role == "child":
        if scenario in ("timeout", "detached-timeout", "cancel", "output-error"):
            spawn("grandchild")
            if scenario == "output-error":
                _wait_marker(folder, "scope-ready")
                time.sleep(0.15)
                # Exceed pipe capacity after the sink has failed. Cleanup must
                # keep reading instead of leaving a writer blocked on stdout.
                pending = memoryview(b"after-output-error\n" * 16_384)
                while pending:
                    written = os.write(1, pending)
                    pending = pending[written:]
                _mark(folder, "post-error-output-written")
        elif scenario == "retained":
            # Close inherited stdout: EOF alone must not prove an empty scope.
            os.close(1)
            os.close(2)
            time.sleep(0.65)
            _mark(folder, "child-finished")
            return 0
        elif scenario == "stdout":
            _wait_marker(folder, "root-exiting")
            time.sleep(0.2)
            os.write(1, b"late-descendant-output\x00\xff\n")
            _mark(folder, "child-finished")
            return 0
    time.sleep(FIXTURE_LIFETIME)
    return 0


LINUX = sys.platform == "linux"
PIDFD = all(
    (hasattr(os, "pidfd_open"), hasattr(os, "P_PIDFD"), hasattr(signal, "pidfd_send_signal"))
)


@unittest.skipUnless(LINUX, "Windows/source-only: actual Linux ownership is unverified")
@unittest.skipUnless(PIDFD, "Linux runtime needs pidfd_open, pidfd_send_signal and P_PIDFD")
class _OwnerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MODULE_FILE.is_file():
            raise AssertionError(f"actual supervisor module is missing: {MODULE_FILE}")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="mutation-owner-test-")
        self.folder = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _command(self, scenario: str, role: str = "root") -> list[str]:
        return [
            sys.executable,
            "-I",
            "-B",
            str(THIS_FILE),
            "--fixture",
            str(self.folder),
            scenario,
            role,
        ]

    def _run(
        self,
        scenario: str = "zero",
        *,
        config: dict | None = None,
        command: list[str] | None = None,
        cancel: bool = False,
    ) -> dict:
        config = dict(config or {})
        child = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                HELPER,
                str(ROOT),
                str(self.folder),
                json.dumps(self._command(scenario) if command is None else command),
                json.dumps(config),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # child is a direct child created here; this stable fd is the only signal
        # target. The parent never uses numeric PID signals or becomes subreaper.
        child_fd = os.pidfd_open(child.pid)
        sent = 0
        try:
            if cancel:
                deadline = time.monotonic() + 3.0
                while not (self.folder / "scope-ready").exists():
                    if child.poll() is not None or time.monotonic() >= deadline:
                        break
                    time.sleep(0.005)
                self.assertTrue(
                    (self.folder / "scope-ready").exists(),
                    "cancel requires a known, running inert tree",
                )
                for _ in range(2):
                    signal.pidfd_send_signal(child_fd, signal.SIGTERM)
                    sent += 1
                    time.sleep(0.01)
            stdout, stderr = child.communicate(timeout=12.0)
        finally:
            if child.poll() is None:
                signal.pidfd_send_signal(child_fd, signal.SIGKILL)
                child.communicate(timeout=2.0)
                # Descendants have finite lifetimes; no unrelated process scans
                # or orphan/group kills are used even after a failed supervisor.
                time.sleep(FIXTURE_LIFETIME + 0.1)
            os.close(child_fd)
        self.assertEqual(
            child.returncode, 0, f"isolated helper failed: stdout={stdout!r}, stderr={stderr!r}"
        )
        receipt = self.folder / "result.json"
        self.assertTrue(receipt.is_file(), f"helper produced no result: {stderr!r}")
        result = json.loads(receipt.read_text(encoding="utf-8"))
        result["signals_sent"] = sent
        return result

    def _assert_outcome(self, result: dict, reason: str, reaped: int) -> dict:
        self.assertNotIn("exception", result, result.get("exception"))
        self.assertIs(result.get("is_dataclass"), True, "Outcome must be a dataclass")
        outcome = result["outcome"]
        self.assertEqual(outcome["reason"], reason, result)
        self.assertIs(outcome["tree_empty"], True, result)
        self.assertIs(outcome["stdout_eof"], True, result)
        self.assertIs(type(outcome["reaped"]), int)
        self.assertEqual(outcome["reaped"], reaped, result)
        self.assertEqual(
            result["forbidden_operations"],
            [],
            "supervisor used numeric PID signals or a global /proc scan",
        )
        self.assertTrue(all(kind == "bytes" for kind in result["callback_types"]), result)
        self._assert_reaped()
        return outcome

    def _assert_reaped(self) -> None:
        # Every PID comes from this test's private fixture directory. An existing
        # matching /proc entry, including a zombie, is a failed reaping assertion.
        for name in ("root", "child", "grandchild"):
            marker = self.folder / f"{name}.pid"
            if marker.exists():
                identity = marker.read_text(encoding="ascii")
                pid = int(identity.split(":", 1)[0])
                self.assertNotEqual(
                    _identity(pid), identity, f"{name} still exists (possibly zombie): {identity}"
                )

    def _assert_tree_created(self) -> None:
        for name in ("root", "child", "grandchild"):
            self.assertTrue(
                (self.folder / f"{name}.pid").exists(), f"test never created its {name}"
            )


class MutationProcessOwnerTests(_OwnerTestCase):
    def test_natural_zero(self) -> None:
        result = self._run()
        outcome = self._assert_outcome(result, "natural", 1)
        self.assertEqual(outcome["root_returncode"], 0)
        self.assertEqual(b"".join(bytes.fromhex(x) for x in result["chunks"]), b"natural-zero\n")

    def test_natural_nonzero(self) -> None:
        outcome = self._assert_outcome(self._run("nonzero"), "natural", 1)
        self.assertEqual(outcome["root_returncode"], 17)

    def test_root_zero_retains_new_session_child_until_natural_empty(self) -> None:
        result = self._run("retained")
        outcome = self._assert_outcome(result, "natural", 2)
        self.assertEqual(outcome["root_returncode"], 0)
        self.assertTrue(
            (self.folder / "child-finished").exists(),
            "root exit/EOF must not end supervision of a living child",
        )
        self.assertGreaterEqual(result["elapsed"], 0.6)

    def test_timeout_kills_and_reaps_new_session_child_and_grandchild(self) -> None:
        result = self._run("timeout", config={"deadline": 0.6})
        self._assert_tree_created()
        outcome = self._assert_outcome(result, "timeout", 3)
        self.assertLess(outcome["root_returncode"], 0)
        self.assertLess(result["elapsed"], 4.5, "finite natural expiry is not timeout cleanup")

    def test_inherited_stdout_is_drained_after_root_exit(self) -> None:
        result = self._run("stdout")
        outcome = self._assert_outcome(result, "natural", 2)
        self.assertEqual(outcome["root_returncode"], 0)
        self.assertTrue((self.folder / "child-finished").exists())
        self.assertEqual(
            b"".join(bytes.fromhex(x) for x in result["chunks"]),
            b"root-exiting\nlate-descendant-output\x00\xff\n",
        )

    def test_root_zero_is_preserved_while_adopted_tree_times_out(self) -> None:
        result = self._run("detached-timeout", config={"deadline": 0.6})
        self._assert_tree_created()
        outcome = self._assert_outcome(result, "timeout", 3)
        self.assertEqual(outcome["root_returncode"], 0)
        self.assertLess(result["elapsed"], 4.5)

    def test_repeated_sigterm_cancel_drains_actual_tree(self) -> None:
        result = self._run("cancel", config={"deadline": 4.0}, cancel=True)
        self._assert_tree_created()
        outcome = self._assert_outcome(result, "cancelled", 3)
        self.assertEqual(result["signals_sent"], 2)
        self.assertLess(outcome["root_returncode"], 0)
        self.assertLess(result["elapsed"], 4.0)

    def test_unrelated_direct_sibling_control_survives(self) -> None:
        control = subprocess.Popen(
            self._command("control", "control"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        control_fd = os.pidfd_open(control.pid)
        try:
            _wait_marker(self.folder, "control.pid")
            identity = (self.folder / "control.pid").read_text(encoding="ascii")
            result = self._run("timeout", config={"deadline": 0.6})
            self._assert_tree_created()
            self._assert_outcome(result, "timeout", 3)
            self.assertEqual(_identity(control.pid), identity)
            self.assertIsNone(control.poll(), "unrelated sibling was signaled/reaped")
            self.assertFalse(select.select([control_fd], [], [], 0)[0])
            _mark(self.folder, "release-control")
            self.assertEqual(control.wait(timeout=2.0), 0)
            self.assertTrue((self.folder / "control-survived").exists())
        finally:
            _mark(self.folder, "release-control")
            if control.poll() is None:
                try:
                    control.wait(timeout=FIXTURE_LIFETIME + 0.5)
                except subprocess.TimeoutExpired:
                    signal.pidfd_send_signal(control_fd, signal.SIGKILL)
                    control.wait(timeout=2.0)
            os.close(control_fd)

    def _rejected_before_launch(
        self, *, config: dict | None = None, command: list[str] | None = None
    ) -> None:
        result = self._run(config=config, command=command)
        self.assertIn("exception", result, "invalid/capability input must fail closed")
        self.assertTrue(
            set(result["exception"]["bases"])
            & {"ValueError", "TypeError", "RuntimeError", "OSError", "NotImplementedError"},
            result,
        )
        self.assertEqual(result["launches"], [], "failure happened after launch")
        self.assertEqual(result["forbidden_operations"], [])
        self.assertFalse((self.folder / "root.pid").exists())

    def test_empty_command_fails_before_launch(self) -> None:
        self._rejected_before_launch(command=[])

    def test_negative_deadline_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"deadline": -1.0})

    def test_nan_deadline_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"deadline_kind": "nan"})

    def test_infinite_deadline_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"deadline_kind": "inf"})

    def test_missing_pidfd_open_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"patch": "pidfd_open_missing"})

    def test_missing_pidfd_signal_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"patch": "pidfd_send_signal_missing"})

    def test_missing_p_pidfd_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"patch": "P_PIDFD_missing"})

    def test_kernel_pidfd_enosys_fails_before_launch(self) -> None:
        self._rejected_before_launch(config={"patch": "pidfd_open_enosys"})

    def test_preexisting_child_rejects_admission_and_survives(self) -> None:
        result = self._run(config={"admission": "preexisting-child"})
        self.assertEqual(result.get("exception", {}).get("type"), "ScopeUnavailable", result)
        self.assertEqual(result["launches"], [])
        self.assertEqual(result["forbidden_operations"], [])
        self.assertEqual(result["preexisting_returncode"], 0)
        self.assertFalse((self.folder / "root.pid").exists())
        identity = (self.folder / "preexisting.pid").read_text(encoding="ascii")
        self.assertNotEqual(_identity(int(identity.split(":", 1)[0])), identity)

    def test_sigchld_ignored_rejects_admission_before_launch(self) -> None:
        self._rejected_before_launch(config={"admission": "SIGCHLD-ignored"})

    def test_output_callback_failure_still_drains_actual_scope(self) -> None:
        result = self._run("output-error", config={"output_error": True})
        self._assert_tree_created()
        self._assert_outcome(result, "output-error", 3)
        self.assertGreater(result["callback_calls"], 0)
        self.assertLess(result["elapsed"], 4.5)


class MutationProcessOwnerCliTests(_OwnerTestCase):
    def _prepare_cli(self, scenario: str = "natural", receipt: str = "owned-receipt.json") -> Path:
        # Dynamic inert console fixtures are test artifacts, never repo edits.
        (self.folder / "mutmut.py").write_text(CLI_FIXTURE, encoding="utf-8")
        (self.folder / "cli-fixture.json").write_text(
            json.dumps({"scenario": scenario, "receipt": receipt, "test_file": str(THIS_FILE)}),
            encoding="utf-8",
        )
        return self.folder / receipt

    def _cli(
        self,
        arguments: list[str],
        *,
        sink: str = "read",
        capability_failure: bool = False,
        verify_function: bool = False,
        timeout: float = 4.0,
    ) -> dict:
        command = [sys.executable, "-I", "-B", str(MODULE_FILE), *arguments]
        if capability_failure:
            command = [
                sys.executable,
                "-I",
                "-B",
                "-c",
                CLI_CAPABILITY_HELPER,
                str(MODULE_FILE),
                str(self.folder / "cli-audit.json"),
                *arguments,
            ]
        if verify_function:
            command = [
                sys.executable,
                "-I",
                "-B",
                "-c",
                CLI_VERIFY_HELPER,
                str(ROOT),
                arguments[-1],
            ]
        started = time.monotonic()
        child = subprocess.Popen(
            command,
            cwd=self.folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        child_fd = os.pidfd_open(child.pid)
        timed_out = False
        stdout = stderr = b""
        try:
            if sink == "closed":
                child.stdout.close()
                child.stdout = None
            try:
                if sink == "unread":
                    # Do not consume one byte until the owner has exited.
                    child.wait(timeout=timeout)
                stdout, stderr = child.communicate(timeout=timeout)
                stdout = stdout or b""
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            if child.poll() is None:
                signal.pidfd_send_signal(child_fd, signal.SIGKILL)
                stdout, stderr = child.communicate(timeout=2)
                stdout = stdout or b""
                if (self.folder / "root.pid").exists():
                    time.sleep(FIXTURE_LIFETIME + 0.1)
            os.close(child_fd)
        return {
            "returncode": child.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed": time.monotonic() - started,
            "timed_out": timed_out,
        }

    def _operation(self, receipt: Path, operation: str = "run", deadline: str = "2") -> list[str]:
        return [operation, "--receipt-file", str(receipt), "--deadline-seconds", deadline]

    def _verify(
        self,
        receipt: Path,
        expected: int = 70,
        *,
        timeout: float = 4.0,
        verify_function: bool = False,
    ) -> None:
        result = self._cli(
            ["verify", "--receipt-file", str(receipt)],
            timeout=timeout,
            verify_function=verify_function,
        )
        self.assertFalse(result["timed_out"], f"receipt verification hung: {result}")
        self.assertEqual(result["returncode"], expected, result)

    def _read_receipt(self, receipt: Path, reason: str, reaped: int) -> dict:
        value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(set(value), {"operation", "outcome"})
        outcome = value["outcome"]
        self.assertEqual(outcome["reason"], reason)
        self.assertIs(outcome["tree_empty"], True)
        self.assertIs(outcome["stdout_eof"], True)
        self.assertEqual(outcome["reaped"], reaped)
        self._assert_reaped()
        return value

    @staticmethod
    def _valid_receipt() -> dict:
        # A verifier input, not a claim that this invented input is runtime proof.
        return {
            "operation": "run",
            "outcome": {
                "root_returncode": 0,
                "reason": "natural",
                "reaped": 1,
                "tree_empty": True,
                "stdout_eof": True,
            },
        }

    def test_cli_fixed_operations_run_results_html(self) -> None:
        for operation in ("run", "results", "html"):
            with self.subTest(operation=operation):
                receipt = self._prepare_cli(receipt=f"{operation}.json")
                result = self._cli(self._operation(receipt, operation))
                self.assertFalse(result["timed_out"], result)
                self.assertEqual(result["returncode"], 0, result)
                value = self._read_receipt(receipt, "natural", 1)
                self.assertEqual(value["operation"], operation)
                launch = json.loads((self.folder / "cli-launch.json").read_text())
                expected_argv = [operation, "--no-progress"] if operation == "run" else [operation]
                self.assertEqual(launch["argv"], expected_argv)
                self.assertIs(launch["receipt_exists"], True)
                self.assertEqual(launch["receipt_size_at_launch"], 0)
                self._verify(receipt, 0 if operation == "run" else 70)

    def test_cli_root_zero_detached_timeout_receipt_and_124(self) -> None:
        receipt = self._prepare_cli("detached-timeout")
        result = self._cli(self._operation(receipt, deadline="0.6"))
        self.assertFalse(result["timed_out"], result)
        self.assertEqual(result["returncode"], 124, result)
        self._assert_tree_created()
        value = self._read_receipt(receipt, "timeout", 3)
        self.assertEqual(value["outcome"]["root_returncode"], 0)
        self.assertLess(result["elapsed"], 4.0)
        self._verify(receipt, 0)

    def test_cli_128_kib_burst_continuously_drained_preserves_bytes_three_trials(self) -> None:
        payload = bytes(range(256)) * 512
        for trial in range(3):
            with self.subTest(trial=trial + 1):
                receipt = self._prepare_cli("burst", receipt=f"burst-{trial}.json")
                # communicate drains the CLI pipe continuously from launch;
                # no sleep/wait-before-read or fake output callback is involved.
                result = self._cli(self._operation(receipt))
                self.assertFalse(result["timed_out"], result)
                self.assertEqual(result["returncode"], 0, result)
                value = self._read_receipt(receipt, "natural", 1)
                self.assertEqual(value["outcome"]["root_returncode"], 0)
                self.assertEqual(result["stdout"][: len(payload)], payload)
                suffix = result["stdout"][len(payload) :]
                self.assertTrue(suffix.startswith(b"\n[owned-scope] "), suffix)
                self.assertEqual(json.loads(suffix[len(b"\n[owned-scope] ") :]), value["outcome"])
                self._verify(receipt, 0)

    def test_cli_existing_receipt_is_not_overwritten_and_no_child_runs(self) -> None:
        receipt = self._prepare_cli()
        original = b"unrelated existing receipt\n"
        receipt.write_bytes(original)
        identity = receipt.stat().st_ino
        result = self._cli(self._operation(receipt))
        self.assertFalse(result["timed_out"], result)
        self.assertEqual(result["returncode"], 70, result)
        self.assertEqual(receipt.read_bytes(), original)
        self.assertEqual(receipt.stat().st_ino, identity)
        self.assertFalse((self.folder / "root.pid").exists())
        self.assertFalse((self.folder / "cli-launch.json").exists())

    def test_cli_process_operations_require_receipt_and_deadline(self) -> None:
        receipt = self._prepare_cli()
        for operation in ("run", "results", "html"):
            for missing in ("receipt", "deadline"):
                with self.subTest(operation=operation, missing=missing):
                    arguments = [operation]
                    arguments += (
                        ["--deadline-seconds", "2"]
                        if missing == "receipt"
                        else ["--receipt-file", str(receipt)]
                    )
                    result = self._cli(arguments)
                    self.assertFalse(result["timed_out"], result)
                    self.assertEqual(result["returncode"], 2, result)
                    self.assertFalse(receipt.exists())
                    self.assertFalse((self.folder / "root.pid").exists())

    def test_cli_unknown_operation_cannot_launch(self) -> None:
        receipt = self._prepare_cli()
        result = self._cli(self._operation(receipt, "diagnose"))
        self.assertEqual(result["returncode"], 2, result)
        self.assertFalse(receipt.exists())
        self.assertFalse((self.folder / "root.pid").exists())

    def test_cli_unavailable_receipt_parent_cannot_launch(self) -> None:
        self._prepare_cli()
        receipt = self.folder / "absent-parent" / "receipt.json"
        result = self._cli(self._operation(receipt))
        self.assertEqual(result["returncode"], 70, result)
        self.assertFalse(receipt.exists())
        self.assertFalse((self.folder / "root.pid").exists())

    def test_cli_unknown_kernel_capability_leaves_empty_lease_without_launch(self) -> None:
        receipt = self._prepare_cli()
        result = self._cli(self._operation(receipt), capability_failure=True)
        self.assertFalse(result["timed_out"], result)
        self.assertEqual(result["returncode"], 70, result)
        self.assertEqual(receipt.read_bytes(), b"")
        self.assertEqual(json.loads((self.folder / "cli-audit.json").read_text()), [])
        self.assertFalse((self.folder / "root.pid").exists())
        self._verify(receipt)

    def test_cli_verify_absent_unfinished_and_malformed_receipts(self) -> None:
        receipt = self.folder / "verify.json"
        self._verify(receipt)
        for raw in (b"", b"unfinished", b"{", b"null", b"[]", b"{}", b"x" * 4097):
            with self.subTest(raw=raw[:32]):
                receipt.write_bytes(raw)
                self._verify(receipt)
                self.assertEqual(receipt.read_bytes(), raw)

    def test_cli_verify_rejects_dirty_outcome_fields(self) -> None:
        receipt = self.folder / "dirty.json"
        changes = [
            ("tree_empty", False),
            ("stdout_eof", False),
            ("tree_empty", 1),
            ("stdout_eof", "true"),
            ("reaped", 0),
            ("reaped", -1),
            ("reaped", True),
            ("root_returncode", None),
            ("root_returncode", True),
            ("reason", "unproven"),
            ("reason", []),
        ]
        for name, dirty in changes:
            with self.subTest(field=name, dirty=dirty):
                value = self._valid_receipt()
                value["outcome"][name] = dirty
                receipt.write_text(json.dumps(value), encoding="utf-8")
                self._verify(receipt)
        for name in self._valid_receipt()["outcome"]:
            with self.subTest(missing=name):
                value = self._valid_receipt()
                del value["outcome"][name]
                receipt.write_text(json.dumps(value), encoding="utf-8")
                self._verify(receipt)
        for change in ("operation", "outer-extra", "outcome-extra"):
            with self.subTest(change=change):
                value = self._valid_receipt()
                if change == "operation":
                    value["operation"] = "results"
                elif change == "outer-extra":
                    value["untrusted"] = True
                else:
                    value["outcome"]["untrusted"] = True
                receipt.write_text(json.dumps(value), encoding="utf-8")
                self._verify(receipt)
        self.assertFalse((self.folder / "root.pid").exists())

    def test_cli_verify_rejects_hardlinked_receipt(self) -> None:
        receipt = self.folder / "original.json"
        receipt.write_text(json.dumps(self._valid_receipt()), encoding="utf-8")
        self._verify(receipt, 0)
        linked = self.folder / "linked.json"
        os.link(receipt, linked)
        self._verify(receipt)
        self._verify(linked)
        self.assertEqual(receipt.stat().st_nlink, 2)

    def test_cli_verify_rejects_duplicate_json_fields(self) -> None:
        receipt = self.folder / "duplicates.json"
        valid = json.dumps(self._valid_receipt())
        duplicates = [
            valid.replace('"operation": "run"', '"operation": "run", "operation": "run"'),
            valid.replace('"tree_empty": true', '"tree_empty": false, "tree_empty": true'),
            valid.replace('"stdout_eof": true', '"stdout_eof": true, "stdout_eof": true'),
            valid.replace('"root_returncode": 0', '"root_returncode": 0, "root_returncode": 0'),
            '{"operation":"run","outcome":'
            + json.dumps(self._valid_receipt()["outcome"])
            + ',"outcome":'
            + json.dumps(self._valid_receipt()["outcome"])
            + "}",
        ]
        for raw in duplicates:
            with self.subTest(raw=raw):
                receipt.write_text(raw, encoding="utf-8")
                self._verify(receipt)
                self.assertEqual(receipt.read_text(encoding="utf-8"), raw)

    def test_cli_verify_rejects_symlink_and_directory(self) -> None:
        receipt = self.folder / "regular.json"
        receipt.write_text(json.dumps(self._valid_receipt()), encoding="utf-8")
        linked = self.folder / "symlink.json"
        linked.symlink_to(receipt)
        self._verify(linked)
        self._verify(self.folder)

    def test_cli_verify_fifo_without_writer_rejects_without_blocking(self) -> None:
        fifo = self.folder / "receipt.fifo"
        os.mkfifo(fifo, 0o600)
        self._verify(fifo, timeout=1.0)
        self._verify(fifo, timeout=1.0, verify_function=True)

    def test_cli_unread_stdout_flood_deadline_receipt_and_reaps(self) -> None:
        receipt = self._prepare_cli("flood")
        result = self._cli(self._operation(receipt, deadline="0.6"), sink="unread")
        self.assertFalse(result["timed_out"], f"log backpressure stalled owner: {result}")
        self.assertEqual(result["returncode"], 74, result)
        self._assert_tree_created()
        self._read_receipt(receipt, "timeout", 3)
        self.assertLess(result["elapsed"], 3.0)
        self.assertNotIn(b"[owned-scope]", result["stdout"], "full log is not output proof")

    def test_cli_closed_stdout_flood_returns_74_and_reaps(self) -> None:
        receipt = self._prepare_cli("flood")
        result = self._cli(self._operation(receipt, deadline="3"), sink="closed")
        self.assertFalse(result["timed_out"], result)
        self.assertEqual(result["returncode"], 74, result)
        self._assert_tree_created()
        self._read_receipt(receipt, "output-error", 3)
        self.assertLess(result["elapsed"], 3.0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fixture":
        raise SystemExit(_fixture(Path(sys.argv[2]), sys.argv[3], sys.argv[4]))
    unittest.main()
