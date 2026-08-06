"""Tests for tools/run_host_tests.py -- the cross-platform C++ host test gate.

The runner is the CI entry point for the safety-critical off-target tests
(safety_logic / palette / led_payload), so its discovery and compile-command
behaviour are pinned here, and -- when a host compiler is available -- the
whole gate is exercised end to end.
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_host_tests  # noqa: E402


def _host_compiler_available() -> bool:
    try:
        run_host_tests.resolve_compiler()
    except FileNotFoundError:
        return False
    return True


class DiscoveryTests(unittest.TestCase):
    def test_discovers_known_safety_test_files_sorted(self):
        names = [p.name for p in run_host_tests.discover_tests()]
        self.assertEqual(names, sorted(names))
        self.assertIn("test_safety_logic.cpp", names)
        self.assertIn("test_palette.cpp", names)
        self.assertIn("test_led_payload.cpp", names)

    def test_discovery_ignores_non_test_sources(self, tmp_dir_name="_discovery_tmp"):
        tmp_dir = ROOT / "build" / tmp_dir_name
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            (tmp_dir / "helper.cpp").write_text("// not a test\n", encoding="utf-8")
            (tmp_dir / "test_b.cpp").write_text("// b\n", encoding="utf-8")
            (tmp_dir / "test_a.cpp").write_text("// a\n", encoding="utf-8")
            names = [p.name for p in run_host_tests.discover_tests(tmp_dir)]
            self.assertEqual(names, ["test_a.cpp", "test_b.cpp"])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class CompileCommandTests(unittest.TestCase):
    def test_command_pins_strict_flags_and_stub_include(self):
        cmd = run_host_tests.compile_command(
            "g++", Path("firmware/tests/test_x.cpp"), Path("out/test_x")
        )
        self.assertEqual(cmd[0], "g++")
        for flag in ("-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2"):
            self.assertIn(flag, cmd)
        include_index = cmd.index("-I")
        self.assertEqual(cmd[include_index + 1], str(run_host_tests.STUB_DIR))
        self.assertEqual(
            cmd[-3:],
            [str(Path("firmware/tests/test_x.cpp")), "-o", str(Path("out/test_x"))],
        )

    def test_missing_explicit_compiler_raises(self):
        with self.assertRaises(FileNotFoundError):
            run_host_tests.resolve_compiler("definitely-not-a-compiler-xyz")


@unittest.skipUnless(_host_compiler_available(), "no host C++ compiler on PATH")
class EndToEndTests(unittest.TestCase):
    def test_runner_passes_on_current_tree(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "run_host_tests.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("ALL HOST TESTS PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
