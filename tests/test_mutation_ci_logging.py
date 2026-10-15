"""Stdlib-only public CI controls; source guards and actual Bash tests are separate.

TEST_ONLY console shims replace mutmut with inert output/exit controls in a fresh
temporary directory. The workflow's production script, limiter and tee pipeline
execute unchanged under Bash -e -o pipefail. No product imports or fixtures run.
Run directly with Python 3.12 -B; Linux/WSL shell controls need no pytest install.
"""

# ruff: noqa: PT009, PT027 -- Deliberate stdlib unittest; no pytest dependency in WSL.

from __future__ import annotations

import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
LOG_PATH = "${{ runner.temp }}/public-mutation-${{ github.run_id }}-${{ github.run_attempt }}"
UPLOAD = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1"
CAP = 5 * 1024 * 1024


def step(text, name):
    match = re.search(rf"(?ms)^      - name: {re.escape(name)}\n(.*?)(?=^      - |\Z)", text)
    if match is None:
        raise AssertionError(f"Missing step: {name}")
    return match[1]


def production_script(text):
    body = step(text, "Mutation testing (advisory)")
    return textwrap.dedent(body.split("        run: |\n", 1)[1])


def validate_source(text):
    mutation = step(text, "Mutation testing (advisory)")
    upload = step(text, "Upload mutation logs")
    assert "        if: matrix.python-version == '3.12'\n" in mutation
    assert "        continue-on-error: true\n" in mutation
    assert "        timeout-minutes: 20\n" in mutation
    assert "        shell: bash\n" in mutation
    assert "          PYTHONUNBUFFERED: '1'\n" in mutation
    assert f"          MUTATION_LOG_DIR: {LOG_PATH}\n" in mutation
    script = production_script(text)
    assert 'mkdir "$MUTATION_LOG_DIR"' in script
    assert "5 * 1024 * 1024 - len(marker)" in script
    assert 'statuses=("${PIPESTATUS[@]}")' in script
    assert '2>&1 | python -u -c "$bounded_output" | tee ' in script
    assert "python -u -m mutmut run --no-progress || run_status=$?" in script
    for command in ("results", "html"):
        assert f"timeout --signal=TERM --kill-after=5s 60s python -u -m mutmut {command}" in script
    assert 'if (( run_status != 0 )); then exit "$run_status"; fi' in script
    for command in ("run", "results", "html"):
        assert f"mutmut {command} pipeline exit: %s" in script
        assert f"mutmut {command} exit: %s" not in script
    assert "tail -" not in script and "|| true" not in script
    assert "matrix.python-version == '3.12' && always()" in upload
    assert UPLOAD in upload
    assert f"          path: {LOG_PATH}/*.log\n" in upload
    assert "          retention-days: 14\n" in upload
    assert "          if-no-files-found: warn\n" in upload


class SourceOnlyGuards(unittest.TestCase):
    def test_public_advisory_owned_logs_and_always_upload(self):
        validate_source(WORKFLOW.read_text(encoding="utf-8"))

    def test_source_regressions_are_rejected_separately_from_shell_evidence(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for before, after in (
            ("timeout-minutes: 20", "timeout-minutes: 40"),
            ("continue-on-error: true\n        timeout-minutes: 20", "timeout-minutes: 20"),
            ("PYTHONUNBUFFERED: '1'", "PYTHONUNBUFFERED: '0'"),
            ('statuses=("${PIPESTATUS[@]}")', "statuses=(0)"),
            ("--kill-after=5s 60s", "--kill-after=5s 600s"),
            ("&& always()", "&& success()"),
            (f"path: {LOG_PATH}/*.log", "path: ${{ github.workspace }}/"),
            (UPLOAD, "actions/upload-artifact@v7"),
        ):
            with self.subTest(regression=before):
                self.assertIn(before, text)
                with self.assertRaises(AssertionError):
                    validate_source(text.replace(before, after))


# This generated executable cannot invoke a real campaign: only these exact
# TEST_ONLY commands are accepted. -c delegates solely the production limiter.
CONSOLE = r"""
import os
import sys
import time
from pathlib import Path

assert os.environ.get("TEST_ONLY_MUTATION_CONSOLE") == "inert"
assert "PUBLIC_CI_PARENT_CONTEXT" not in os.environ
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if name == "timeout":
    assert args[:3] == ["--signal=TERM", "--kill-after=5s", "60s"]
    assert args[3:6] == ["python", "-u", "-m"] and args[6] == "mutmut"
    os.execv(os.environ["TEST_ONLY_REAL_TIMEOUT"],
             ["timeout", "--signal=TERM", "--kill-after=0.2s", "0.5s", *args[3:]])
if name == "tee":
    if args[-1].endswith("run.log"):
        sys.stdout.buffer.write(sys.stdin.buffer.read())
        raise SystemExit(23)
    os.execv(os.environ["TEST_ONLY_REAL_TEE"], ["tee", *args])
assert name == "python" and args[0] == "-u"
assert os.environ["PYTHONUNBUFFERED"] == "1"
if args[1] == "-c":
    assert len(args) == 3
    if os.environ.get("TEST_ONLY_LIMITER_FAIL") == "1":
        sys.stdin.buffer.read()
        raise SystemExit(13)
    os.execv(sys.executable, [sys.executable, "-u", "-B", *args[1:]])
assert args[1:3] == ["-m", "mutmut"]
command = args[3]
assert command in {"run", "results", "html"}
assert args[4:] == (["--no-progress"] if command == "run" else [])
with open("TEST_ONLY-calls.log", "a", encoding="utf-8") as calls:
    calls.write(command + "\n")
os.write(1, ("TEST_ONLY " + command + " stdout ").encode())
os.write(2, ("TEST_ONLY " + command + " stderr\n").encode())
if command == "run" and os.environ.get("TEST_ONLY_FLOOD") == "1":
    for _ in range(96):
        sys.stdout.buffer.write(b"X" * 65536)
    sys.stdout.buffer.flush()
    os.write(2, b"TEST_ONLY flood fully drained\n")
if os.environ.get("TEST_ONLY_BLOCK") == command:
    deadline = time.monotonic() + 10
    while not Path("TEST_ONLY-release").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
raise SystemExit(int(os.environ.get("TEST_ONLY_EXIT_" + command.upper(), "0")))
"""


@unittest.skipUnless(os.name == "posix", "Actual Bash controls require Linux/WSL")
class ActualBashControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = shutil.which("bash", path=os.defpath)
        cls.timeout = shutil.which("timeout", path=os.defpath)
        cls.tee = shutil.which("tee", path=os.defpath)
        if not all((cls.bash, cls.timeout, cls.tee)):
            raise unittest.SkipTest("Existing Bash, GNU timeout and tee are required; no installs")
        cls.script = production_script(WORKFLOW.read_text(encoding="utf-8"))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="TEST_ONLY-mutation-ci-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "TEST_ONLY-bin"
        self.bin.mkdir()
        self.logs = self.root / "public-mutation-control"
        self.console("python")
        self.console("timeout")
        previous_context = os.environ.get("PUBLIC_CI_PARENT_CONTEXT")
        os.environ["PUBLIC_CI_PARENT_CONTEXT"] = "synthetic-parent-only"

        def restore_parent_context():
            if previous_context is None:
                os.environ.pop("PUBLIC_CI_PARENT_CONTEXT", None)
            else:
                os.environ["PUBLIC_CI_PARENT_CONTEXT"] = previous_context

        self.addCleanup(restore_parent_context)
        # Fixed fields only, no ambient credentials/config forwarded. The
        # running interpreter supplies its own shared-library directory; hosted
        # setup-python binaries need it even when the parent environment is cut.
        self.environment = {
            "PATH": str(self.bin) + os.pathsep + os.defpath,
            "LD_LIBRARY_PATH": str(Path(sys.executable).resolve().parent.parent / "lib"),
            "LANG": "C.UTF-8",
            "MUTATION_LOG_DIR": str(self.logs),
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TEST_ONLY_MUTATION_CONSOLE": "inert",
            "TEST_ONLY_REAL_TIMEOUT": self.timeout,
            "TEST_ONLY_REAL_TEE": self.tee,
        }

    def console(self, name):
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(CONSOLE), encoding="utf-8")
        path.chmod(0o700)

    def launch(self, **controls):
        return subprocess.Popen(
            [self.bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", self.script],
            cwd=self.root,
            env=self.environment | controls,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    @staticmethod
    def stop(process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        process.communicate(timeout=5)

    def run_control(self, **controls):
        process = self.launch(**controls)
        try:
            output, _ = process.communicate(timeout=8)
            return process.returncode, output
        finally:
            self.stop(process)

    def log(self, name):
        return (self.logs / name).read_bytes()

    def calls(self):
        return (self.root / "TEST_ONLY-calls.log").read_text(encoding="utf-8").splitlines()

    def test_zero_exit_streams_and_retains_both_output_channels(self):
        status, output = self.run_control()
        self.assertEqual(status, 0)
        self.assertEqual(self.calls(), ["run", "results", "html"])
        for name in ("run", "results", "html"):
            self.assertIn(f"TEST_ONLY {name} stdout ".encode(), output)
            self.assertIn(f"TEST_ONLY {name} stderr\n".encode(), self.log(name + ".log"))
        self.assertIn(b"mutmut run pipeline exit: 0", self.log("status.log"))

    def test_runner_failure_survives_successful_diagnostics(self):
        status, _ = self.run_control(TEST_ONLY_EXIT_RUN="7")
        self.assertEqual(status, 7)
        self.assertEqual(self.calls(), ["run", "results", "html"])
        self.assertIn(b"mutmut run pipeline exit: 7", self.log("status.log"))

    def test_runner_failure_survives_failed_and_timed_out_diagnostics(self):
        status, _ = self.run_control(
            TEST_ONLY_EXIT_RUN="7", TEST_ONLY_BLOCK="results", TEST_ONLY_EXIT_HTML="2"
        )
        self.assertEqual(status, 7)
        self.assertIn(b"mutmut results pipeline exit: 124", self.log("status.log"))
        self.assertIn(b"mutmut html pipeline exit: 2", self.log("status.log"))
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_report_failure_does_not_claim_success(self):
        status, _ = self.run_control(TEST_ONLY_EXIT_RESULTS="9")
        self.assertEqual(status, 9)
        self.assertIn(b"mutmut run pipeline exit: 0", self.log("status.log"))
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_report_timeout_is_bounded_and_html_is_still_attempted(self):
        status, _ = self.run_control(TEST_ONLY_BLOCK="results")
        self.assertEqual(status, 124)
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_html_failure_is_visible(self):
        status, _ = self.run_control(TEST_ONLY_EXIT_HTML="11")
        self.assertEqual(status, 11)
        self.assertIn(b"mutmut html pipeline exit: 11", self.log("status.log"))

    def test_tee_failure_cannot_hide_runner_failure(self):
        self.console("tee")
        status, _ = self.run_control(TEST_ONLY_EXIT_RUN="7")
        self.assertEqual(status, 7)
        self.assertIn(b"mutmut run pipeline exit: 7", self.log("status.log"))
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_tee_failure_is_nonzero_even_when_runner_succeeds(self):
        self.console("tee")
        status, _ = self.run_control()
        self.assertEqual(status, 23)
        self.assertIn(b"mutmut run pipeline exit: 23", self.log("status.log"))

    def test_limiter_failure_cannot_hide_runner_failure(self):
        status, _ = self.run_control(TEST_ONLY_EXIT_RUN="7", TEST_ONLY_LIMITER_FAIL="1")
        self.assertEqual(status, 7)
        self.assertIn(b"mutmut run pipeline exit: 7", self.log("status.log"))
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_limiter_failure_is_nonzero_even_when_runner_succeeds(self):
        status, _ = self.run_control(TEST_ONLY_LIMITER_FAIL="1")
        self.assertEqual(status, 13)
        self.assertIn(b"mutmut run pipeline exit: 13", self.log("status.log"))

    def test_log_cap_drains_without_breaking_runner(self):
        status, output = self.run_control(TEST_ONLY_FLOOD="1")
        self.assertEqual(status, 0)
        log = self.log("run.log")
        self.assertEqual(len(log), CAP)
        self.assertIn(b"TEST_ONLY run stdout ", log)
        self.assertIn(b"TEST_ONLY run stderr\n", log)
        self.assertEqual(log.count(b"[mutation log capped"), 1)
        self.assertNotIn(b"TEST_ONLY flood fully drained", output)
        self.assertEqual(self.calls(), ["run", "results", "html"])

    def test_live_partial_output_and_interruption_keep_evidence(self):
        process = self.launch(TEST_ONLY_BLOCK="run")
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                output = b""
                deadline = time.monotonic() + 4
                while b"TEST_ONLY run stderr\n" not in output:
                    self.assertLess(time.monotonic(), deadline, "Output was buffered until exit")
                    for key, _ in selector.select(timeout=0.1):
                        output += os.read(key.fileobj.fileno(), 65536)
            self.assertIsNone(process.poll(), "Control must still be running")
            deadline = time.monotonic() + 1
            while b"TEST_ONLY run stderr\n" not in self.log("run.log"):
                self.assertLess(time.monotonic(), deadline, "Live evidence was not retained")
                time.sleep(0.01)
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b"TEST_ONLY run stdout ", self.log("run.log"))
            self.assertIn(b"TEST_ONLY run stderr\n", self.log("run.log"))
            self.assertNotIn(b"mutmut run pipeline exit: 0", self.log("status.log"))
            self.assertEqual(self.calls(), ["run"])
        finally:
            self.stop(process)


if __name__ == "__main__":
    unittest.main(verbosity=2)
