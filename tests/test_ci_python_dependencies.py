"""Public CI dependency/readonly regression; no SDK, compiler or live MCP calls."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
INSTALL = (
    "python -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt"
)
PREFLIGHT = "Verify public MCP and parser dependencies (readonly)"


def _job(text):
    match = re.search(r"(?ms)^  python:\n(.*?)(?=^  \w[\w-]*:|\Z)", text)
    assert match is not None, "Python job is required"
    return match[1]


def _step(job, name):
    match = re.search(rf"(?ms)^      - name: {re.escape(name)}\n(.*?)(?=^      - |\Z)", job)
    assert match is not None, f"Missing required dependency step: {name}"
    assert not re.search(r"(?m)^        (?:if|continue-on-error):", match[1])
    return match[1]


def _readonly_script(text):
    step = _step(_job(text), PREFLIGHT)
    match = re.search(r"(?ms)^          python -B - <<'PY'\n(.*?)^          PY\s*$", step)
    assert match is not None, "Readonly preflight must use the matrix Python with -B"
    return textwrap.dedent(match[1])


def _validate(text):
    job = _job(text)
    assert not re.search(r"(?m)^    (?:if|continue-on-error):", job)
    assert "python-version: ['3.10', '3.12']" in job
    environment = re.search(r"(?ms)^    env:\n(.*?)(?=^    \S|\Z)", job)
    assert environment is not None
    assert re.search(r"(?m)^      PYTHONDONTWRITEBYTECODE: ['\"]1['\"]\s*$", environment[1])
    install = _step(job, "Install dependencies")
    assert INSTALL in [line.strip() for line in install.splitlines()]
    assert "--no-deps" not in install and "||" not in install
    assert "requirements-codegraph-win-py312.txt" not in install
    preflight = _step(job, PREFLIGHT)
    assert "python -m pip check" in [line.strip() for line in preflight.splitlines()]
    assert "||" not in preflight
    assert job.index("- name: Install dependencies") < job.index(f"- name: {PREFLIGHT}")
    assert job.index(f"- name: {PREFLIGHT}") < job.index("- name: Run tests")
    script = _readonly_script(text)
    nodes = list(ast.walk(ast.parse(script)))
    imports = {node.module for node in nodes if isinstance(node, ast.ImportFrom)}
    assert {"mcp.server.fastmcp", "pydantic", "tree_sitter"} <= imports
    assert any(
        isinstance(node, ast.Import) and any(item.name == "tree_sitter_cpp" for item in node.names)
        for node in nodes
    )
    assert "assert sys.dont_write_bytecode" in script
    assert "parser.parse(b'int public_dummy() { return 0; }')" in script
    assert "not tree.root_node.has_error" in script
    pytest_commands = re.findall(r"(?m)^\s+(python[^\n]*-m pytest[^\n]*)$", job)
    assert len(pytest_commands) == 3
    assert all(command.startswith("python -B -m pytest ") for command in pytest_commands)
    assert "-n 2 --maxprocesses 2" in pytest_commands[1]
    assert "--cov-fail-under=80" in pytest_commands[1]


def test_public_ci_installs_dependencies_before_readonly_tests():
    _validate(WORKFLOW.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (" -r requirements-mcp.txt", ""),
        (INSTALL, f"echo '{INSTALL}'"),
        ("python -m pip check", "echo python -m pip check"),
        ("python -B -m pytest", "python -m pytest"),
        ("PYTHONDONTWRITEBYTECODE: '1'", "PYTHONDONTWRITEBYTECODE: '0'"),
        (f"- name: {PREFLIGHT}\n", f"- name: {PREFLIGHT}\n        if: false\n"),
        (
            "- name: Install dependencies\n",
            "- name: Install dependencies\n        continue-on-error: true\n",
        ),
        (" -r requirements-mcp.txt", " --no-deps -r requirements-mcp.txt"),
    ],
)
def test_dependency_or_readonly_gate_regressions_are_rejected(old, new):
    current = WORKFLOW.read_text(encoding="utf-8")
    assert old in current
    with pytest.raises(AssertionError):
        _validate(current.replace(old, new, 1))


def test_job_bytecode_environment_reaches_actual_xdist_workers(tmp_path):
    """Exercise worker and nested Python inheritance without a product test suite."""
    current = WORKFLOW.read_text(encoding="utf-8")
    _validate(current)
    worker = tmp_path / "test_worker_readonly.py"
    worker.write_text(
        textwrap.dedent("""\
        import os
        import subprocess
        import sys
        from pathlib import Path

        def test_worker_readonly():
            assert sys.dont_write_bytecode
            assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'
            worker_id = os.environ['PYTEST_XDIST_WORKER']
            assert worker_id in {'gw0', 'gw1'}
            subprocess.run(
                [sys.executable, '-c', 'import sys; assert sys.dont_write_bytecode'],
                check=True, timeout=15,
            )
            Path(__file__).with_name(worker_id + '.marker').write_text('readonly')
        """),
        encoding="utf-8",
    )
    config = tmp_path / "pytest.ini"
    config.write_text("[pytest]\n", encoding="utf-8")
    child_temp = tmp_path / "xdist-temp"
    assert not child_temp.exists(), "Nested worker temp must be a fresh owned path"
    # Preserve only named OS paths; do not pass inherited credentials or project
    # configuration into this independent nested test process.
    environment = {
        key: os.environ[key]
        for key in (
            "SystemRoot",
            "WINDIR",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "TEMP",
            "TMP",
            "HOME",
        )
        if key in os.environ
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-n",
            "2",
            "--maxprocesses",
            "2",
            "--dist=each",
            "--basetemp",
            str(child_temp),
            "-p",
            "xdist.plugin",
            "-p",
            "no:cacheprovider",
            "--confcutdir",
            str(tmp_path),
            "-c",
            str(config),
            str(worker),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in tmp_path.glob("*.marker")} == {"gw0.marker", "gw1.marker"}
