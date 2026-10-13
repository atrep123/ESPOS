"""TEST_ONLY source-child and verifier boundary evidence; no fake frozen exe.

Set CODEGRAPH_PYTHON to the existing approved parser interpreter. Source fixtures
call the actual reviewed entry through the verifier's owned transport. They do
not call verify_executable and never emit frozenVerified=True as test evidence.
"""

import ast
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools import verify_frozen_desktop_backend as verifier

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "tools" / "desktop_backend_entry.py"
SPEC = ROOT / "tools" / "desktop_backend_freeze.spec"


@pytest.fixture(scope="module")
def test_only_python():
    value = os.environ.get("CODEGRAPH_PYTHON")
    if not value:
        pytest.skip("TEST_ONLY actual source fixture requires explicit CODEGRAPH_PYTHON")
    path = Path(value)
    assert path.is_absolute() and path.is_file()
    return str(path)


@pytest.fixture
def owned_children(monkeypatch):
    children = []
    original = subprocess.Popen

    def recorded(*args, **kwargs):
        assert kwargs["shell"] is False
        if os.name == "nt":
            assert kwargs["creationflags"] & subprocess.CREATE_NO_WINDOW
            assert kwargs["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW
            assert kwargs["startupinfo"].wShowWindow == subprocess.SW_HIDE
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(verifier.subprocess, "Popen", recorded)
    yield children
    assert all(child.poll() is not None for child in children), "Every owned child must be reaped"


def test_test_only_real_entry_parse_edit_sdk_and_failures(
    test_only_python, tmp_path, owned_children
):
    calls = []

    def test_only_exchange(payload, args):
        calls.append(args)
        return verifier._run_owned_child(
            (test_only_python, "-I", "-B", str(ENTRY), *args), payload, cwd=tmp_path
        )

    checks = verifier._verify_cases(test_only_exchange)
    assert checks == [
        "parse",
        "edit",
        "sdkParse",
        "sdkRegions",
        "constructSdk",
        "malformedRequest",
        "fixedRole",
    ]
    assert calls == [("codegraph-bundled",)] * 6 + [("catalog",)]
    assert len(owned_children) == 7 and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_test_only_combined_child_output_cap(test_only_python, tmp_path, owned_children, stream):
    # Authored synthetic I/O fixture, never an executable masquerading as the
    # backend. Its output is deliberately not accepted as a parser response.
    program = f"import sys; sys.{stream}.buffer.write(b'x' * (1024 * 1024 + 1))"
    with pytest.raises(verifier.VerificationError, match="output-limit"):
        verifier._run_owned_child((test_only_python, "-I", "-B", "-c", program), b"", cwd=tmp_path)
    assert len(owned_children) == 1


def test_test_only_stalled_child_deadline_cleanup(
    test_only_python, tmp_path, owned_children, monkeypatch
):
    assert verifier.DEADLINE_SECONDS == 12
    monkeypatch.setattr(verifier, "DEADLINE_SECONDS", 0.15)
    started = time.monotonic()
    with pytest.raises(verifier.VerificationError, match="child-deadline"):
        verifier._run_owned_child(
            (test_only_python, "-I", "-B", "-c", "import time; time.sleep(60)"), b"", cwd=tmp_path
        )
    assert time.monotonic() - started < 2
    assert len(owned_children) == 1


def test_oversize_request_never_spawns(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid request must not launch anything")

    monkeypatch.setattr(verifier.subprocess, "Popen", forbidden)
    with pytest.raises(verifier.VerificationError, match="request-limit"):
        verifier._run_owned_child(
            ("TEST_ONLY_NEVER_LAUNCH",), b"x" * (1024 * 1024 + 1), cwd=tmp_path
        )


def test_launch_error_hides_paths_and_has_no_retry(monkeypatch, tmp_path):
    calls = []

    def failed(*args, **kwargs):
        calls.append(args)
        raise OSError("SECRET_PATH and private operating system data")

    monkeypatch.setattr(verifier.subprocess, "Popen", failed)
    with pytest.raises(verifier.VerificationError, match="launch-failed") as caught:
        verifier._run_owned_child(("TEST_ONLY_NEVER_LAUNCH",), b"", cwd=tmp_path)
    assert len(calls) == 1 and "SECRET_PATH" not in str(caught.value)


def test_cli_refuses_interpreter_and_missing_stage_without_spawning(monkeypatch, capsys, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected executable must not launch")

    monkeypatch.setattr(verifier.subprocess, "Popen", forbidden)
    for path in ("relative.exe", sys.executable, str(tmp_path / "espos_codegraph_backend.exe")):
        assert verifier.main(["--exe", path]) == 1
        captured = capsys.readouterr()
        response = json.loads(captured.out)
        assert response == {"ok": False, "frozenVerified": False, "code": "staged-exe-required"}
        assert captured.err == ""


def test_legacy_full_sidecar_names_rejected_before_file_check(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Legacy sidecar must not be inspected or launched")

    monkeypatch.setattr(Path, "is_file", forbidden)
    monkeypatch.setattr(verifier.subprocess, "Popen", forbidden)
    for name in ("espos_sidecar.exe", "espos_sidecar-x86_64-pc-windows-msvc.exe"):
        with pytest.raises(verifier.VerificationError, match="staged-exe-required"):
            verifier._staged_executable(str(tmp_path / name))
    assert set(verifier._STAGED_NAMES) == {
        "espos_codegraph_backend.exe",
        "espos_codegraph_backend-x86_64-pc-windows-msvc.exe",
    }


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--help"],
        ["--exe"],
        ["--exe", "SECRET_PATH", "--python", "SECRET_PATH"],
        ["--tooling-root", "SECRET_PATH"],
    ],
)
def test_cli_exact_explicit_exe_argument_only(args, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Usage failure must not verify")

    monkeypatch.setattr(verifier, "verify_executable", forbidden)
    assert verifier.main(args) == 1
    captured = capsys.readouterr()
    assert "SECRET_PATH" not in captured.out and captured.err == ""
    assert json.loads(captured.out)["code"] == "usage-explicit-exe-required"


def test_cli_unexpected_error_is_safe_nonzero(monkeypatch, capsys):
    def failed(path):
        raise RuntimeError("SECRET_PATH/raw stderr")

    monkeypatch.setattr(verifier, "verify_executable", failed)
    assert verifier.main(["--exe", "SECRET_PATH"]) == 1
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out) == {
        "ok": False,
        "frozenVerified": False,
        "code": "verification-failed",
    }


@pytest.mark.parametrize(
    ("result", "code"),
    [
        ((0, b'{"ok":true}\n', b""), "exit-or-result-mismatch"),
        ((1, b'{"ok":false,"diagnostics":[]}\n', b""), "diagnostics"),
        ((1, b'{"ok":false}\n', b"SECRET_PATH/raw stderr"), "unexpected-stderr"),
        ((1, b'{"ok":false}\n{}\n', b""), "reply-frame"),
        ((1, b'{"ok":false}', b""), "reply-frame"),
        ((1, b'{"ok":false,"ok":false}\n', b""), "repeated-reply-key"),
        ((1, b'{"ok":false,"number":NaN}\n', b""), "nonfinite-reply"),
        ((1, b'{"ok":false,"sourceBase64":""}\n', b""), "partial-failure"),
        ((None, b'{"ok":false}\n', b""), "exit-or-result-mismatch"),
    ],
)
def test_test_only_bad_response_is_never_accepted(result, code):
    with pytest.raises(verifier.VerificationError, match=code) as caught:
        verifier._decode_reply(result, success=False)
    assert "SECRET_PATH" not in str(caught.value)


def test_test_only_suite_stops_at_first_bad_child():
    calls = []

    def failed(payload, args):
        calls.append(args)
        return 1, b'{"ok":false}\n', b"SECRET_PATH/raw stderr"

    with pytest.raises(verifier.VerificationError, match="unexpected-stderr"):
        verifier._verify_cases(failed)
    assert len(calls) == 1


def test_recipe_static_sources_extensions_and_stdio_onedir():
    # AST/source checks cover the authored recipe, not a PyInstaller build.
    source = SPEC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert {"tree_sitter._binding", "tree_sitter_cpp._binding"} <= imports
    calls = {
        node.func.id: node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"Analysis", "EXE", "COLLECT"}
    }
    analysis = {key.arg: key.value for key in calls["Analysis"].keywords}
    hidden = ast.literal_eval(analysis["hiddenimports"])
    assert {
        "tools.tabos_code_graph",
        "tools.tabos_sdk_node_catalog",
        "tree_sitter._binding",
        "tree_sitter_cpp._binding",
    } <= set(hidden)
    options = {key.arg: key.value for key in calls["EXE"].keywords}
    assert ast.literal_eval(options["console"]) is True
    assert ast.literal_eval(options["exclude_binaries"]) is True
    assert ast.literal_eval(options["contents_directory"]) == "_internal"
    assert ast.literal_eval(options["name"]) == "espos_codegraph_backend"
    collect_options = {key.arg: key.value for key in calls["COLLECT"].keywords}
    assert ast.literal_eval(collect_options["name"]) == "espos_codegraph_backend"
    assert "COLLECT" in calls and 'version("tree-sitter") != "0.26.0"' in source
    assert 'version("tree-sitter-cpp") != "0.23.4"' in source
    assert "subprocess" not in source and "os.environ" not in source
    assert "APPROVED_BUILD_SITE" in source and "pathex=build_pathex" in source
    assert ast.literal_eval(analysis["runtime_hooks"]) == []


@pytest.mark.parametrize(
    ("subsystem", "dll", "expected"),
    [
        (3, False, None),
        (2, False, "console-backend-required"),
        (3, True, "invalid-executable"),
    ],
)
def test_test_only_pe_header_bytes_refuse_gui_and_dll(subsystem, dll, expected):
    # TEST_ONLY in-memory header bytes, never a file, executable or launch target.
    dos = bytearray(64)
    dos[:2] = b"MZ"
    dos[60:64] = (64).to_bytes(4, "little")
    coff = bytearray(24)
    coff[:6] = b"PE\x00\x00\x64\x86"
    coff[20:22] = (70).to_bytes(2, "little")
    coff[22:24] = (2 | (0x2000 if dll else 0)).to_bytes(2, "little")
    optional = bytearray(70)
    optional[:2] = b"\x0b\x02"
    optional[68:70] = subsystem.to_bytes(2, "little")
    stream = io.BytesIO(dos + coff + optional)
    if expected:
        with pytest.raises(verifier.VerificationError, match=expected):
            verifier._check_console_pe(stream)
    else:
        verifier._check_console_pe(stream)
