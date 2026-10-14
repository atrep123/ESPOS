"""TEST_ONLY source/collection controls; never run native fixtures or a baseline.

Read public Python test source only. Collection uses inert functions with source
names, marks and parameter counts, not the original imports, bodies or fixtures.
Linux/GCC availability are literal inputs, never host or compiler probes. Existing
Windows skipifs remain skips; only native_windows modules are deselected.
"""

from __future__ import annotations

import ast
import inspect
import shlex
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "test_runtime_simulator.py",
    "test_runtime_simulator_hot_native.py",
    "test_runtime_preview_native.py",
    "test_runtime_preview_process_bridge.py",
    "test_simulator_process.py",
)
NATIVE_FILES = FILES[1:3]
RUNNER = "python -B -m pytest -x -q --ignore=output --tb=no -m 'not native_windows'"
MUTMUT = {
    "paths_to_mutate": "cyberpunk_designer/",
    "tests_dir": "tests/",
    "runner": RUNNER,
    "dict_synonyms": "Struct,NamedStruct",
}
PORTABLE_SIMULATOR = {
    "test_production_edit_clamp_exit_navigation_and_checkbox": 1,
    "test_simulated_transport_failure_keeps_frame_black": 2,
    "test_bounded_input_rejected_before_compile": 1,
}
WINDOWS_SIMULATOR = {
    "test_actual_app_subscriber_and_visual_logic_roundtrip": 1,
    "test_app_roundtrip_via_input_ids_only": 1,
    "test_command_restores_focus_for_activation": 3,
    "test_command_preserves_existing_focus": 3,
}


def mutation_settings(text):
    # These four settings are strings: stdlib parsing works on CI Python 3.10
    # too, without adding a TOML dependency or importing product code.
    section = text.split("[tool.mutmut]\n", 1)[1].split("\n[", 1)[0]
    return {
        key.strip(): ast.literal_eval(value.strip())
        for line in section.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        for key, value in [line.split("=", 1)]
    }


def validate_settings(settings):
    assert settings == MUTMUT, "Keep mutation scope and bounded runner exactly"
    tokens = shlex.split(settings["runner"])
    assert tokens == [
        "python",
        "-B",
        "-m",
        "pytest",
        "-x",
        "-q",
        "--ignore=output",
        "--tb=no",
        "-m",
        "not native_windows",
    ]
    return tokens[4:]


def linux_condition(node, *, gcc_available):
    """Evaluate only the source guards used by these five public test groups."""
    if isinstance(node, ast.Compare):
        assert ast.unparse(node.left) == "os.name"
        assert len(node.ops) == len(node.comparators) == 1
        assert isinstance(node.ops[0], ast.NotEq)
        assert ast.literal_eval(node.comparators[0]) == "nt"
        return True  # Literal TEST_ONLY Linux profile, even on a Windows host.
    if isinstance(node, ast.Call):
        assert ast.unparse(node.func) == "shutil.which"
        assert len(node.args) == 1 and not node.keywords
        assert ast.literal_eval(node.args[0]) == "gcc"
        return gcc_available
    if isinstance(node, ast.UnaryOp):
        assert isinstance(node.op, ast.Not)
        return not linux_condition(node.operand, gcc_available=gcc_available)
    if isinstance(node, ast.BoolOp):
        assert isinstance(node.op, ast.Or)
        return any(linux_condition(value, gcc_available=gcc_available) for value in node.values)
    return ast.literal_eval(node)


def source_mark(node, *, gcc_available):
    call = isinstance(node, ast.Call)
    name = ast.unparse(node.func if call else node)
    assert name in {
        "pytest.mark.native_windows",
        "pytest.mark.skipif",
        "pytest.mark.timeout",
        "pytest.mark.parametrize",
    }, f"Unmodeled source mark: {name}"
    if name == "pytest.mark.native_windows":
        assert not call
        return pytest.mark.native_windows, ()
    assert call
    keywords = {keyword.arg: ast.literal_eval(keyword.value) for keyword in node.keywords}
    if name == "pytest.mark.skipif":
        assert len(node.args) == 1
        condition = linux_condition(node.args[0], gcc_available=gcc_available)
        return pytest.mark.skipif(condition, **keywords), ()
    if name == "pytest.mark.timeout":
        return pytest.mark.timeout(ast.literal_eval(node.args[0]), **keywords), ()
    assert len(node.args) == 2
    names = ast.literal_eval(node.args[0])
    names = tuple(part.strip() for part in names.split(",")) if isinstance(names, str) else names
    assert isinstance(node.args[1], (ast.List, ast.Tuple))
    # Never evaluate values containing calls, paths, executable names, etc.
    # Keep each source row and literal ids, using inert TEST_ONLY values instead.
    values = [
        tuple(f"TEST_ONLY_{index}_{name}" for name in names)
        for index in range(len(node.args[1].elts))
    ]
    return pytest.mark.parametrize(names, values, **keywords), names


def source_module(filename, source, *, gcc_available):
    tree = ast.parse(source, filename=filename)
    module = ModuleType("TEST_ONLY_" + Path(filename).stem)
    module.__file__ = str(ROOT / "tests" / filename)
    module.pytestmark = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets
        ):
            marks = (
                node.value.elts if isinstance(node.value, (ast.List, ast.Tuple)) else [node.value]
            )
            module.pytestmark.extend(
                source_mark(mark, gcc_available=gcc_available)[0] for mark in marks
            )
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue

        def inert(**parameters):
            raise AssertionError("TEST_ONLY source collection must never execute test bodies")

        inert.__name__ = node.name
        inert.__module__ = module.__name__
        parameters = []
        for decorator in reversed(node.decorator_list):
            mark, names = source_mark(decorator, gcc_available=gcc_available)
            parameters.extend(names)
            inert = mark(inert)
        inert.__signature__ = inspect.Signature(
            inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD) for name in parameters
        )
        setattr(module, node.name, inert)
    return module


class SourceCollection:
    def __init__(self, sources, gcc_available):
        self.sources = sources
        self.gcc_available = gcc_available
        self.loaded = set()
        self.selected = []
        self.deselected = []

    def pytest_ignore_collect(self, collection_path, config):
        if collection_path.parent == ROOT / "tests":
            return collection_path.name not in {*self.sources, "__init__.py"}
        return None

    def pytest_pycollect_makemodule(self, module_path, parent):
        filename = module_path.name
        if module_path == ROOT / "tests" / "__init__.py":
            module = ModuleType("TEST_ONLY_empty_test_package")
            module.__file__ = str(module_path)
        else:
            assert filename in self.sources, f"Collection escaped bounded source groups: {filename}"
            module = source_module(
                filename, self.sources[filename], gcc_available=self.gcc_available
            )
            self.loaded.add(filename)

        class InertModule(pytest.Module):
            def _getobj(self):
                return module

        return InertModule.from_parent(parent, path=module_path)

    def pytest_deselected(self, items):
        self.deselected.extend(items)

    def pytest_collection_finish(self, session):
        self.selected = list(session.items)


def collect_sources(tmp_path, sources, arguments, *, gcc_available=True):
    collector = SourceCollection(sources, gcc_available)
    result = pytest.main(
        [
            *arguments,
            "--collect-only",
            "--noconftest",
            "--disable-plugin-autoload",
            "--strict-markers",
            "-p",
            "no:cacheprovider",
            "-c",
            str(ROOT / "pyproject.toml"),
            "-o",
            "addopts=",
            "-o",
            "filterwarnings=ignore::pytest.PytestConfigWarning",
            "--basetemp",
            str(tmp_path / "TEST_ONLY-source-collection"),
            *(str(ROOT / "tests" / filename) for filename in sources),
        ],
        plugins=[collector],
    )
    assert result == pytest.ExitCode.OK
    assert collector.loaded == set(sources)
    return collector


def case_counts(items, filename):
    counts = {}
    for item in items:
        if item.path.name == filename:
            counts[item.originalname] = counts.get(item.originalname, 0) + 1
    return counts


def validate_portable_defaults(source):
    functions = {
        node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
    }
    for name in PORTABLE_SIMULATOR:
        calls = [
            node
            for node in ast.walk(functions[name])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run"
        ]
        assert calls, "Retained cases must exercise the real default wrapper entry point"
        assert all(
            keyword.arg not in {None, "app"} for call in calls for keyword in call.keywords
        ), "Portable controls must retain the implicit app=False default"


def validate_collection(collector, *, gcc_available):
    assert len(collector.deselected) == 7
    assert {item.path.name for item in collector.deselected} == set(NATIVE_FILES)
    assert sum(item.path.name == NATIVE_FILES[0] for item in collector.deselected) == 6
    assert sum(item.path.name == NATIVE_FILES[1] for item in collector.deselected) == 1
    assert all(item.get_closest_marker("native_windows") for item in collector.deselected)
    assert not any(item.get_closest_marker("native_windows") for item in collector.selected)
    simulator = case_counts(collector.selected, FILES[0])
    assert simulator == PORTABLE_SIMULATOR | WINDOWS_SIMULATOR
    for item in collector.selected:
        guards = [mark.args[0] for mark in item.iter_markers("skipif")]
        if item.path.name == FILES[0]:
            windows = item.originalname in WINDOWS_SIMULATOR
            needs_gcc = item.originalname != "test_bounded_input_rejected_before_compile"
            assert any(guards) is (windows or (needs_gcc and not gcc_available))
        if item.path.name == FILES[3]:
            assert any(guards), "Existing Windows bridge guard must remain effective"
    assert sum(item.path.name == FILES[3] for item in collector.selected) == 5
    assert sum(item.path.name == FILES[4] for item in collector.selected) == 52
    portable_process = [
        item
        for item in collector.selected
        if item.path.name == FILES[4]
        and not any(mark.args[0] for mark in item.iter_markers("skipif"))
    ]
    assert len(portable_process) == 46


def test_mutation_runner_matches_readonly_general_ci():
    validate_settings(mutation_settings((ROOT / "pyproject.toml").read_text(encoding="utf-8")))
    general = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -B -m pytest" in general
    assert "-m 'not native_windows'" in general


def test_portable_defaults_are_real_default_wrapper_calls_and_reject_app_mutation():
    source = (ROOT / "tests" / FILES[0]).read_text(encoding="utf-8")
    validate_portable_defaults(source)
    before = "before = run(scene, initial, [])"
    assert before in source
    with pytest.raises(AssertionError):
        validate_portable_defaults(
            source.replace(before, "before = run(scene, initial, [], app=True)")
        )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (" -B", ""),
        (" -x", ""),
        (" -q", ""),
        (" --ignore=output", ""),
        (" --tb=no", " --tb=long"),
        (" -m 'not native_windows'", ""),
        ("not native_windows", "native_windows"),
        ("not native_windows", "not visual"),
        ("not native_windows", "not native_windows and smoke"),
        ("not native_windows", "not native_windows or smoke"),
        (" --tb=no", " --tb=no --ignore=tests/test_runtime_simulator.py"),
    ],
)
def test_red_runner_mutations_are_rejected(before, after):
    settings = dict(MUTMUT, runner=RUNNER.replace(before, after, 1))
    with pytest.raises(AssertionError):
        validate_settings(settings)


@pytest.mark.parametrize("key", ["paths_to_mutate", "tests_dir", "dict_synonyms"])
def test_red_mutation_scope_changes_are_rejected(key):
    with pytest.raises(AssertionError):
        validate_settings(dict(MUTMUT, **{key: "TEST_ONLY-wrong-scope"}))


@pytest.mark.parametrize("gcc_available", [True, False])
def test_source_collection_deselects_native_modules_and_retains_portable_cases(
    tmp_path, gcc_available
):
    sources = {name: (ROOT / "tests" / name).read_text(encoding="utf-8") for name in FILES}
    settings = mutation_settings((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    collector = collect_sources(
        tmp_path, sources, validate_settings(settings), gcc_available=gcc_available
    )
    validate_collection(collector, gcc_available=gcc_available)


def test_old_runner_collects_native_cases_that_the_fixed_selector_excludes(tmp_path):
    sources = {name: (ROOT / "tests" / name).read_text(encoding="utf-8") for name in FILES}
    old_arguments = shlex.split("python -m pytest -x -q --ignore=output --tb=no")[3:]
    collector = collect_sources(tmp_path, sources, old_arguments)
    assert collector.deselected == []
    assert (
        sum(item.get_closest_marker("native_windows") is not None for item in collector.selected)
        == 7
    )
    with pytest.raises(AssertionError):
        validate_collection(collector, gcc_available=True)


@pytest.mark.parametrize(
    ("filename", "before", "after"),
    [
        (FILES[1], "pytestmark = pytest.mark.native_windows", "pytestmark = []"),
        (FILES[2], "pytestmark = pytest.mark.native_windows", "pytestmark = []"),
        (FILES[0], "import pytest", "import pytest\npytestmark = pytest.mark.native_windows"),
        (FILES[0], 'os.name != "nt"', "False"),
        (FILES[3], 'os.name != "nt"', "False"),
        (FILES[4], 'os.name != "nt"', "False"),
    ],
)
def test_red_source_collection_controls_detect_lost_guards_or_portable_cases(
    tmp_path, filename, before, after
):
    sources = {name: (ROOT / "tests" / name).read_text(encoding="utf-8") for name in FILES}
    assert before in sources[filename]
    sources[filename] = sources[filename].replace(before, after)
    collector = collect_sources(tmp_path, sources, shlex.split(RUNNER)[4:])
    with pytest.raises(AssertionError):
        validate_collection(collector, gcc_available=True)
