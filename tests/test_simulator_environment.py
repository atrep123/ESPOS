"""Lexical contract tests; no compiler, filesystem fixtures or GUI needed."""

import os
import unittest
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

import pytest

from tools import simulator_environment as module


class UnreadableEnvironment(Mapping):
    def __getitem__(self, key):
        raise AssertionError("parent environment was read")

    def __iter__(self):
        raise AssertionError("parent environment was iterated")

    def __len__(self):
        raise AssertionError("parent environment was measured")


@contextmanager
def lexical_host(windows):
    """Exercise both lexical flavours without changing the real host OS."""
    path_type = PureWindowsPath if windows else PurePosixPath
    with patch.object(module, "_WINDOWS", windows), patch.object(module, "Path", path_type):
        yield path_type


class TestSimulatorEnvironment(unittest.TestCase):
    def setUp(self):
        environment_patch = patch.object(os, "environ", UnreadableEnvironment())
        environment_patch.start()
        self.addCleanup(environment_patch.stop)

    def test_exact_allowlist_and_no_parent_values(self):
        synthetic = {
            "TEST_ONLY_CREDENTIAL": "test-secret-only",
            "PATH": "test-parent-path-only",
            "CC": "test-compiler-only",
            "CXX": "test-cxx-only",
            "CPATH": "test-include-only",
            "HOME": "test-home-only",
            "LD_PRELOAD": "test-loader-only",
            "LD_LIBRARY_PATH": "test-library-only",
            "SSH_AUTH_SOCK": "test-ssh-only",
            "HTTP_PROXY": "test-proxy-only",
            "https_proxy": "test-lower-proxy-only",
            "GITHUB_PAT": "test-pat-only",
            "SYSTEMROOT": "test-systemroot-only",
            "WINDIR": "test-windir-only",
            "TEMP": "test-temp-only",
            "TMP": "test-tmp-only",
            "PYTHONPATH": "test-pythonpath-only",
            "PYTHONUTF8": "test-pythonutf8-only",
            "PYTHONDONTWRITEBYTECODE": "test-bytecode-only",
            "PYTHONIOENCODING": "test-encoding-only",
        }
        # Replace the mapping itself: never inspect or copy real environment values.
        with patch.object(os, "environ", synthetic):
            for windows in (True, False):
                with self.subTest(windows=windows), lexical_host(windows) as path:
                    root = "C:/explicit" if windows else "/explicit"
                    compiler = path(root) / "compiler/bin/gcc"
                    python = path(root) / "python/python"
                    temporary = path(root) / "private/job"
                    actual = module.build_environment(compiler, python, temporary)
                    expected = {
                        "PATH": (";" if windows else ":").join(
                            [
                                str(compiler.parent),
                                str(python.parent),
                                *(
                                    [str(path("C:/Windows/System32")), str(path("C:/Windows"))]
                                    if windows
                                    else ["/usr/bin", "/bin"]
                                ),
                            ]
                        ),
                        "TEMP": str(temporary),
                        "TMP": str(temporary),
                        "PYTHONUTF8": "1",
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONIOENCODING": "utf-8",
                    }
                    if windows:
                        expected.update(SYSTEMROOT="C:/Windows", WINDIR="C:/Windows")
                    assert actual == expected
                    assert set(synthetic.values()).isdisjoint(actual.values())

    def test_no_environment_or_filesystem_access_on_current_host(self):
        root = Path("C:/explicit") if os.name == "nt" else Path("/explicit")
        arguments = (root / "bin/gcc", root / "python/python", root / "private/job")
        with (
            patch.object(os, "environ", UnreadableEnvironment()),
            patch.object(Path, "resolve", side_effect=AssertionError("resolve called")),
            patch.object(Path, "stat", side_effect=AssertionError("stat called")),
            patch.object(Path, "lstat", side_effect=AssertionError("lstat called")),
            patch.object(Path, "is_symlink", side_effect=AssertionError("is_symlink called")),
            patch("builtins.open", side_effect=AssertionError("open called")),
        ):
            first = module.build_environment(*arguments)
            second = module.build_environment(*arguments)
            assert first == second
            assert first is not second
            first["PATH"] = "changed"
            assert first["PATH"] != second["PATH"]

    def test_path_deduplication_preserves_first_occurrence(self):
        cases = [
            (
                True,
                "C:/Tools/bin/gcc.exe",
                "c:/tools/BIN/python.exe",
                ["C:/Tools/bin", "C:/Windows/System32", "C:/Windows"],
            ),
            (
                True,
                "c:/WINDOWS/system32/gcc.exe",
                "C:/Windows/python.exe",
                ["c:/WINDOWS/system32", "C:/Windows"],
            ),
            (False, "/usr/bin/gcc", "/usr/bin/python", ["/usr/bin", "/bin"]),
            (False, "/bin/gcc", "/usr/bin/python", ["/bin", "/usr/bin"]),
            (
                False,
                "/Tools/bin/gcc",
                "/tools/bin/python",
                ["/Tools/bin", "/tools/bin", "/usr/bin", "/bin"],
            ),
        ]
        for windows, compiler, python, expected in cases:
            with self.subTest(compiler=compiler), lexical_host(windows) as path:
                temporary = path("C:/private/job" if windows else "/private/job")
                result = module.build_environment(path(compiler), path(python), temporary)
                assert result["PATH"].split(";" if windows else ":") == [
                    str(path(item)) for item in expected
                ]

    def test_rejects_invalid_paths_in_each_argument(self):
        cases = {
            True: [
                "relative/file",
                "C:relative/file",
                "/rooted/file",
                "C:/",
                "C:/safe/../file",
                "//server/share/file",
                "//?/C:/safe/file",
                "//./C:/safe/file",
                "C:/safe/file:stream",
                "C:/safe/NUL.txt",
                "C:/safe/NUL .txt",
                "C:/safe/COM\u00b9.txt",
                "C:/safe/CONOUT$",
                "C:/safe/file.",
                "C:/safe/file ",
                "C:/safe/*.exe",
                "C:/safe/a;injection",
                "C:/safe/a\nfile",
                "C:/safe/a\x00file",
                "C:/safe/a\x7ffile",
            ],
            False: [
                "relative/file",
                "/",
                "/safe/../file",
                "//server/share/file",
                "/safe/a:injection",
                "/safe/a\nfile",
                "/safe/a\x00file",
                "/safe/a\x7ffile",
            ],
        }
        for windows, invalids in cases.items():
            with lexical_host(windows) as path:
                root = path("C:/explicit" if windows else "/explicit")
                valid = [root / "bin/gcc", root / "python/python", root / "private/job"]
                for invalid in invalids:
                    for index in range(3):
                        with self.subTest(windows=windows, invalid=invalid, argument=index):
                            arguments = valid.copy()
                            arguments[index] = path(invalid)
                            with pytest.raises(ValueError, match=r"^(compiler|python|temporary) "):
                                module.build_environment(*arguments)
                for index in range(3):
                    arguments = valid.copy()
                    arguments[index] = str(arguments[index])
                    with self.subTest(windows=windows, argument=index), pytest.raises(TypeError):
                        module.build_environment(*arguments)

    def test_rejects_broad_temporary_directories(self):
        cases = {
            True: [
                "C:/",
                "C:/Users",
                "C:/Windows",
                "C:/Windows/Temp",
                "C:/Windows/System32",
                "C:/explicit",
                "C:/explicit/bin",
                "C:/explicit/python",
            ],
            False: [
                "/",
                "/tmp",  # noqa: S108 -- lexical rejection fixture, no I/O
                "/var/tmp",  # noqa: S108 -- lexical rejection fixture, no I/O
                "/usr/bin",
                "/bin",
                "/explicit",
                "/explicit/bin",
                "/explicit/python",
            ],
        }
        for windows, invalids in cases.items():
            with lexical_host(windows) as path:
                root = path("C:/explicit" if windows else "/explicit")
                for invalid in invalids:
                    with (
                        self.subTest(temporary=invalid),
                        pytest.raises(ValueError, match=r"^temporary "),
                    ):
                        module.build_environment(
                            root / "bin/gcc", root / "python/python", path(invalid)
                        )


if __name__ == "__main__":
    unittest.main()
