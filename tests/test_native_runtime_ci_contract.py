"""Source/mutation controls for public native CI, never compiler/process/GUI runs.

Synthetic JUnit is TEST_ONLY verifier input, not actual native runtime evidence.
"""

from __future__ import annotations

import ast
import re
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.check_supply_chain import validate_workflow_text

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/native-runtime.yml"
ACTIONS = (
    "actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10",
    "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
)
FILES = (
    "test_runtime_simulator.py",
    "test_runtime_simulator_hot_native.py",
    "test_runtime_preview_native.py",
    "test_runtime_preview_process_bridge.py",
    "test_simulator_process.py",
)
FLOORS = (12, 6, 1, 5, 52)


def inline_python(text):
    match = re.search(r"\$script = @'\n(.*?)\n          '@", text, re.S)
    assert match, "Required isolated source CLI missing"
    return textwrap.dedent(match[1])


def definitions(text):
    # Only definition loading. __main__ is false: no compiler lookup, native
    # invocation, public C reads, environment inspection or real pytest groups.
    namespace = {"__name__": "TEST_ONLY_ci_contract"}
    exec(compile(inline_python(text), "TEST_ONLY_native_ci.py", "exec"), namespace)  # noqa: S102 -- trusted checked-in definitions; never __main__
    return namespace


def validate_source(text):
    assert "name: Required Windows native runtime" in text
    assert "runs-on: windows-2022" in text
    assert "timeout-minutes: 20" in text
    assert "python-version: '3.12'" in text
    assert "PYTHONDONTWRITEBYTECODE: '1'" in text
    job_env = re.search(r"(?ms)^    env:\n(.*?)(?=^    \S)", text)
    assert job_env is not None
    # runner is unavailable in jobs.<job_id>.env. Resolve the named private
    # directory on the runner and export it for later steps, not at job parse.
    assert "runner." not in job_env[1] and "env." not in job_env[1]
    assert "NATIVE_CI_OUTPUT_NAME: TEST_ONLY-native-runtime-ci-" in job_env[1]
    assert "$output = Join-Path $env:RUNNER_TEMP $env:NATIVE_CI_OUTPUT_NAME" in text
    assert (
        "('NATIVE_CI_OUTPUT=' + $output) | Out-File -LiteralPath $env:GITHUB_ENV "
        "-Encoding utf8 -Append"
    ) in text
    assert "permissions:\n  contents: read\n\njobs:" in text
    assert "persist-credentials: false" in text
    assert tuple(re.findall(r"(?m)^\s+-?\s*uses:\s*(\S+)", text)) == ACTIONS
    assert "  push:\n    branches: [main, master, codex/dodelavky-20260927]" in text
    assert "  pull_request:\n    branches: [main, master]" in text
    assert not re.search(r"(?m)^\s+(?:paths|paths-ignore):", text)
    assert re.findall(r"(?m)^\s+if:\s*(.*)$", text) == ["always()"]
    for forbidden in (
        "continue-on-error",
        "pull_request_target",
        "workflow_run:",
        "secrets.",
        "GITHUB_TOKEN",
        "id-token:",
        "|| true",
        "--collect-only",
        "--ignore=",
        "-k ",
        "-m native_windows",
        "setup-msys2",
        "choco install",
        "winget install",
        "pacman ",
        "app_desktop.exe",
        "full42",
        "privateSDK",
    ):
        assert forbidden not in text
    assert "@('pytest==9.0.3', 'pytest-timeout==2.4.0')" in text
    assert text.count("pip install") == 1
    assert "python -I -B -m pip install -r $manifest" in text
    assert "'test-tools.txt'" in text
    assert "Get-Command gcc -CommandType Application" in text
    assert "'C:/msys64/ucrt64/bin/gcc.exe', 'C:/msys64/mingw64/bin/gcc.exe'" in text
    for check in (
        "$item.FullName --version",
        "$item.FullName -dumpmachine",
        "[IO.FileAttributes]::ReparsePoint",
        "$item.Attributes -band [IO.FileAttributes]::ReparsePoint",
        "$ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint",
        "$ancestor = $item.Directory",
        "$ancestor = $ancestor.Parent",
        "Required preinstalled GCC absent; no skip or installation",
        "$env:GITHUB_PATH",
        "python -I -X utf8 -B -c $script",
        '"$env:GITHUB_WORKSPACE" "$env:NATIVE_CI_OUTPUT"',
        "path: ${{ runner.temp }}/${{ env.NATIVE_CI_OUTPUT_NAME }}/",
        "if-no-files-found: error",
        "TEST_ONLY-native-runtime-ci-${{ github.run_id }}-${{ github.run_attempt }}",
    ):
        assert check in text
    assert not re.search(
        r"(?m)^\s+path:\s*(?:\.|\*|\$\{\{\s*(?:github.workspace|runner.temp)\s*\}\}/?\s*$)", text
    )
    script = inline_python(text)
    tree = ast.parse(script)
    group_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "GROUPS" for target in node.targets)
    )
    groups = ast.literal_eval(group_node.value)
    assert tuple(group[1] for group in groups) == FILES
    assert tuple(group[2] for group in groups) == FLOORS
    assert all(group[3] for group in groups)
    assert groups[1][0] == "hot-native"
    for gate in (
        "assert os.name == 'nt' and sys.version_info[:2] == (3, 12)",
        "assert sys.dont_write_bytecode and sys.flags.isolated",
        "assert compiler, 'Required existing GCC absent; cannot skip'",
        "Path(compiler).samefile(Path(metadata['compiler']))",
        "sys.path.insert(0, str(root))",
        "assert not directory.exists()",
        "tempfile.tempdir = str(private)",
        "'--noconftest'",
        "'--strict-markers'",
        "'--tb=no'",
        "'--timeout=300'",
        "'junit_logging=no'",
        "'--basetemp', str(directory / 'fixtures')",
        "str(root / 'tests' / filename)",
        "if result != 0:",
        "counts[group] = verify_junit(",
        "if problems:",
        "raise SystemExit('Required native runtime failed:",
        "assert before == after",
        "'source-provenance.json'",
        "'positive-counts.json'",
    ):
        assert gate in script
    assert validate_workflow_text(WORKFLOW, text) == []
    return groups


def test_required_public_native_workflow_source_contract():
    validate_source(WORKFLOW.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("runs-on: windows-2022", "runs-on: windows-latest"),
        ("timeout-minutes: 20", "timeout-minutes: 60"),
        ("python-version: '3.12'", "python-version: '3.10'"),
        ("contents: read", "contents: write"),
        ("persist-credentials: false", "persist-credentials: true"),
        (ACTIONS[0], "actions/checkout@v6"),
        (ACTIONS[1], "actions/setup-python@v6"),
        (ACTIONS[2], "actions/upload-artifact@v7"),
        ("branches: [main, master]\n", "branches: [main, master]\n    paths: ['**']\n"),
        ("branches: [main, master]\n", "branches: [main, master]\n    paths: ['output/**']\n"),
        ("    runs-on:", "    continue-on-error: true\n    runs-on:"),
        ("        if: always()", "        if: success()"),
        ("pytest==9.0.3", "pytest>=9"),
        ("pytest-timeout==2.4.0", "pytest-timeout"),
        ("python -I -B -m pip install -r $manifest", "python -m pip install gcc"),
        (
            "path: ${{ runner.temp }}/${{ env.NATIVE_CI_OUTPUT_NAME }}/",
            "path: ${{ github.workspace }}/",
        ),
        (
            "path: ${{ runner.temp }}/${{ env.NATIVE_CI_OUTPUT_NAME }}/",
            "path: ${{ runner.temp }}/",
        ),
        (
            "path: ${{ runner.temp }}/${{ env.NATIVE_CI_OUTPUT_NAME }}/",
            "path: ${{ env.NATIVE_CI_OUTPUT }}/",
        ),
        ("if-no-files-found: error", "if-no-files-found: ignore"),
        ("PYTHONDONTWRITEBYTECODE: '1'", "PYTHONDONTWRITEBYTECODE: '0'"),
        (
            "NATIVE_CI_OUTPUT_NAME: TEST_ONLY-native-runtime-ci-",
            "NATIVE_CI_OUTPUT: ${{ runner.temp }}/TEST_ONLY-native-runtime-ci-",
        ),
        ("$env:GITHUB_ENV -Encoding utf8 -Append", "$env:GITHUB_PATH -Encoding utf8 -Append"),
        ("$env:RUNNER_TEMP $env:NATIVE_CI_OUTPUT_NAME", "$env:RUNNER_TEMP 'shared-output'"),
        ("'test_runtime_preview_native.py'", "'test_runtime_preview_controller.py'"),
        ("'test_runtime_simulator.py'", "'test_runtime_preview_controller.py'"),
        ("'test_runtime_preview_process_bridge.py'", "'test_runtime_preview_controller.py'"),
        ("'test_simulator_process.py'", "'test_runtime_preview_controller.py'"),
        ("'test_runtime_simulator_hot_native.py'", "'test_runtime_preview_controller.py'"),
        ("'test_runtime_simulator_hot_native.py', 6", "'test_runtime_simulator_hot_native.py', 1"),
        ("'--noconftest'", "'--collect-only'"),
        ("'--tb=no'", "'--tb=long'"),
        ("if result != 0:", "if result < 0:"),
        ("if problems:", "if False:"),
        ("assert before == after", "assert True"),
        ("counts[group] = verify_junit(", "counts[group] = count_without_gate("),
        ("assert compiler,", "assert True,"),
        ("Path(compiler).samefile(Path(metadata['compiler']))", "True"),
        ("[IO.FileAttributes]::ReparsePoint", "[IO.FileAttributes]::Archive"),
        ("$ancestor = $item.Directory", "$ancestor = $item"),
        ("$ancestor = $ancestor.Parent", "$ancestor = $null"),
        ("$item.FullName -dumpmachine", "$item.FullName --help"),
    ],
)
def test_source_mutations_cannot_silently_weaken_required_profile(before, after):
    text = WORKFLOW.read_text(encoding="utf-8")
    assert before in text
    with pytest.raises(AssertionError):
        validate_source(text.replace(before, after, 1))


def test_only_windows_native_modules_are_explicitly_deselected_from_general_ci():
    registry = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"\[tool.pytest.ini_options\]\nmarkers = (\[.*?\])", registry, re.S)
    assert match and any(item.startswith("native_windows:") for item in ast.literal_eval(match[1]))
    for filename in FILES[1:3]:
        tree = ast.parse((ROOT / "tests" / filename).read_text(encoding="utf-8"))
        marks = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in node.targets
            )
        ]
        assert len(marks) == 1
        assert ast.unparse(marks[0].value) == "pytest.mark.native_windows"
    # Linux-safe simulator defaults and existing Windows-only skipifs stay intact.
    simulator = (ROOT / "tests" / FILES[0]).read_text(encoding="utf-8")
    assert "pytestmark" not in simulator
    assert "test_production_edit_clamp_exit_navigation_and_checkbox" in simulator
    general = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    commands = [line.strip() for line in general.splitlines() if "python -B -m pytest" in line]
    assert len(commands) == 3
    covered = [command for command in commands if "--cov " in command]
    assert len(covered) == 1 and covered[0].endswith(" -m 'not native_windows'")
    for required in (
        "--ignore=output",
        "-n 2 --maxprocesses 2",
        "--cov-config=pyproject.toml",
        "--cov-branch",
        "--cov-fail-under=80",
    ):
        assert required in covered[0]
    assert sum("native_windows" in command for command in commands) == 1


def write_report(path, filename, count, required):
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root, "testsuite", tests=str(count), failures="0", errors="0", skipped="0"
    )
    names = list(required) + [
        f"TEST_ONLY_control_{index}" for index in range(count - len(required))
    ]
    for name in names:
        ET.SubElement(suite, "testcase", classname="tests." + Path(filename).stem, name=name)
    ET.ElementTree(root).write(path, encoding="utf-8")
    return root


@pytest.mark.parametrize("index", range(5))
def test_positive_count_and_named_controls_accept_each_exact_evidence_group(tmp_path, index):
    namespace = definitions(WORKFLOW.read_text(encoding="utf-8"))
    _, filename, minimum, required = namespace["GROUPS"][index]
    path = tmp_path / "TEST_ONLY-junit.xml"
    write_report(path, filename, minimum, required)
    assert namespace["verify_junit"](path, filename, minimum, required) == minimum


@pytest.mark.parametrize(
    "mutation",
    [
        "skipped-total",
        "errors-total",
        "failures-total",
        "count-lie",
        "empty",
        "below-floor",
        "missing-positive",
        "wrong-source",
        "hidden-skip",
        "hidden-error",
        "hidden-failure",
        "duplicate",
        "missing-counter",
        "no-suite",
        "wrong-root",
        "malformed",
    ],
)
def test_junit_mutations_reject_nonactual_or_nonpassing_evidence(tmp_path, mutation):
    namespace = definitions(WORKFLOW.read_text(encoding="utf-8"))
    path = tmp_path / "TEST_ONLY-junit.xml"
    required, filename, minimum = ("test_required_real_control",), FILES[0], 12
    root = write_report(path, filename, minimum, required)
    suite = root.find("testsuite")
    first = suite.find("testcase")
    if mutation.endswith("-total"):
        suite.set(mutation.removesuffix("-total"), "1")
    elif mutation == "count-lie":
        suite.set("tests", "100")
    elif mutation == "empty":
        suite.clear()
        suite.attrib.update(tests="0", failures="0", errors="0", skipped="0")
    elif mutation == "below-floor":
        suite.remove(suite.findall("testcase")[-1])
        suite.set("tests", str(minimum - 1))
    elif mutation == "missing-positive":
        first.set("name", "TEST_ONLY_not_the_required_control")
    elif mutation == "wrong-source":
        first.set("classname", "tests.test_runtime_preview_controller")
    elif mutation.startswith("hidden-"):
        tag = {"skip": "skipped", "error": "error", "failure": "failure"}[mutation[7:]]
        ET.SubElement(first, tag)
    elif mutation == "duplicate":
        suite.findall("testcase")[1].set("name", first.get("name"))
    elif mutation == "missing-counter":
        del suite.attrib["skipped"]
    elif mutation == "no-suite":
        root.remove(suite)
    elif mutation == "wrong-root":
        root.tag = "not_actual_junit"
    ET.ElementTree(root).write(path, encoding="utf-8")
    if mutation == "malformed":
        path.write_text("TEST_ONLY invalid XML", encoding="utf-8")
    with pytest.raises((AssertionError, ET.ParseError)):
        namespace["verify_junit"](path, filename, minimum, required)


def test_absent_junit_cannot_pass_a_required_group(tmp_path):
    namespace = definitions(WORKFLOW.read_text(encoding="utf-8"))
    with pytest.raises(FileNotFoundError):
        namespace["verify_junit"](tmp_path / "absent.xml", FILES[0], 12, ("test_required",))
