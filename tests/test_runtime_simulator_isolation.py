"""TEST_ONLY wrapper wiring; compiler and C runtime are never executed here."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tools import espos_runtime_simulator as simulator
from tools.simulator_process import ProcessResult, SimulatorProcessError


def mock_provenance(initial, final=None):
    return {
        "hardware_transport": "mock",
        "display": initial,
        "initial_display": initial,
        "final_display": final if final is not None else initial,
    }


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    # TEST_ONLY routing admits mocked app children on every real host. Replace
    # only the wrapper's binding; shared os/pathlib keep their native behavior.
    monkeypatch.setattr(simulator, "os", SimpleNamespace(name="nt"))
    compiler = tmp_path / "TEST_ONLY-gcc.bin"
    compiler.write_bytes(b"TEST_ONLY inert compiler placeholder")
    created, calls = [], []

    def private_directory(*, prefix):
        path = tmp_path / (prefix + "TEST_ONLY")
        path.mkdir()
        created.append(path)
        return str(path)

    monkeypatch.setattr(simulator.shutil, "which", lambda name: str(compiler))
    monkeypatch.setattr(simulator.tempfile, "mkdtemp", private_directory)
    monkeypatch.setattr(
        simulator,
        "generate_ui_design_multi_pair",
        lambda path, **options: ("TEST_ONLY generated C", "TEST_ONLY generated H"),
    )

    def child(command, **options):
        calls.append((command, options))
        # TEST_ONLY final-status report fixture. No UI/driver behavior is modeled.
        status = 0
        if command[0].endswith("runtime.exe"):
            status = int(command[2])
            for event in command[3:]:
                if event.startswith("display:"):
                    status = {"connected": 0, "disconnected": 0x105, "error": -1}[
                        event.split(":")[1]
                    ]
        state = {
            "runtime_simulation": True,
            "display_status": status,
            "widgets": [{"value": 3}],
            "texts": ["\u017dlu\u0165".encode("utf-8").hex()],
        }
        return ProcessResult(
            0, (json.dumps(state) + "\n").encode("utf-8"), b"", "TEST_ONLY-mocked-process", True
        )

    monkeypatch.setattr(simulator, "run_child", child)
    return compiler, created, calls


@pytest.mark.parametrize(("platform_name", "app"), [("nt", False), ("posix", False), ("nt", True)])
def test_mock_pipeline_routes_supported_platform_modes(
    tmp_path, pipeline, monkeypatch, platform_name, app
):
    _compiler, created, calls = pipeline
    monkeypatch.setattr(simulator, "os", SimpleNamespace(name=platform_name))
    events = ["button:0:release", "tick:1", "display:disconnected"]
    state = simulator.run(
        tmp_path / "TEST_ONLY-scene.json",
        tmp_path / "TEST_ONLY-frame.pgm",
        events,
        app=app,
    )
    assert len(calls) == 2 and len(created) == 1
    assert ("-DSIM_APP=1" in calls[0][0]) is app
    assert calls[1][0][3:] == events
    assert state["simulation"] == mock_provenance("connected", "disconnected")
    assert not created[0].exists()


def test_posix_app_preflight_fails_before_setup_or_child_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(simulator, "os", SimpleNamespace(name="posix"))
    forbidden = Mock(side_effect=AssertionError("unsupported app must fail before setup/children"))
    monkeypatch.setattr(simulator, "shutil", SimpleNamespace(which=forbidden))
    monkeypatch.setattr(simulator, "tempfile", SimpleNamespace(mkdtemp=forbidden))
    for name in (
        "_ordinary_path",
        "build_environment",
        "generate_ui_design_multi_pair",
        "run_child",
    ):
        monkeypatch.setattr(simulator, name, forbidden)
    with pytest.raises(SimulatorProcessError, match=r"^simulator-preflight-failed$") as caught:
        simulator.run(
            tmp_path / "TEST_ONLY-unused.json",
            tmp_path / "TEST_ONLY-unused.pgm",
            ["tick:1", "display:error"],
            app=True,
        )
    forbidden.assert_not_called()
    assert caught.value.cleanup_confirmed is True
    assert not hasattr(caught.value, "retained_build")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("invalid", [True, False, -1, 256, "action:x:0", None])
def test_invalid_event_fails_before_compiler_discovery_or_directory_creation(
    tmp_path, monkeypatch, invalid
):
    def forbidden(*args, **options):
        raise AssertionError("invalid input must fail before any compiler/filesystem work")

    monkeypatch.setattr(simulator.shutil, "which", forbidden)
    monkeypatch.setattr(simulator.tempfile, "mkdtemp", forbidden)
    with pytest.raises(ValueError, match="At most 256"):
        simulator.run(tmp_path / "unused.json", tmp_path / "unused.pgm", [invalid])


@pytest.mark.parametrize("display", ["connected", "disconnected", "error"])
def test_wrapper_uses_private_cwd_explicit_environment_and_marks_mock_transport(
    tmp_path, pipeline, display
):
    compiler, created, calls = pipeline
    state = simulator.run(
        tmp_path / "TEST_ONLY-scene.json", tmp_path / "TEST_ONLY-frame.pgm", [0, 6, 1], display
    )
    assert len(calls) == 2 and len(created) == 1
    compile_command, compile_options = calls[0]
    runtime_command, runtime_options = calls[1]
    build = created[0]
    assert compile_command[0] == str(compiler)
    assert compile_options["cwd"] == runtime_options["cwd"] == build
    assert compile_options["timeout"] == 60 and runtime_options["timeout"] == 10
    assert compile_options["env"] == runtime_options["env"]
    assert compile_options["env"]["TEMP"] == compile_options["env"]["TMP"] == str(build)
    assert runtime_command == [
        str(build / "runtime.exe"),
        str(tmp_path / "TEST_ONLY-frame.pgm"),
        str({"connected": 0, "disconnected": 0x105, "error": -1}[display]),
        "0",
        "6",
        "1",
    ]
    assert state["widgets"] == [{"value": 3}] and state["texts"] == ["\u017dlu\u0165"]
    assert state["simulation"] == mock_provenance(display)
    assert not build.exists()


@pytest.mark.parametrize("cleanup", [True, False, None])
def test_owned_process_failure_retains_build_only_when_cleanup_unconfirmed(
    tmp_path, pipeline, monkeypatch, cleanup
):
    _compiler, created, calls = pipeline

    def failed(*args, **options):
        raise SimulatorProcessError("simulator-timeout", cleanup_confirmed=cleanup)

    monkeypatch.setattr(simulator, "run_child", failed)
    with pytest.raises(SimulatorProcessError, match="simulator-timeout") as caught:
        simulator.run(tmp_path / "TEST_ONLY-scene.json", tmp_path / "TEST_ONLY-frame.pgm", [])
    assert len(created) == 1 and not calls
    assert created[0].exists() is (cleanup is not True)
    if cleanup is not True:
        assert caught.value.retained_build == str(created[0])


def test_runtime_cannot_overwrite_mock_transport_provenance(tmp_path, pipeline, monkeypatch):
    _compiler, created, _calls = pipeline
    response = json.dumps({"simulation": {"hardware_transport": "real"}}).encode("utf-8")
    monkeypatch.setattr(
        simulator,
        "run_child",
        lambda *args, **options: ProcessResult(0, response, b"", "TEST_ONLY-mocked-process", True),
    )
    with pytest.raises(ValueError, match="transport provenance"):
        simulator.run(tmp_path / "TEST_ONLY-scene.json", tmp_path / "TEST_ONLY-frame.pgm", [])
    assert not created[0].exists()


@pytest.mark.parametrize("app", [False, True])
def test_exact_default_and_app_child_shapes_keep_distinct_wrapper_provenance(app):
    child = {
        "runtime_simulation": True,
        "display_status": 0,
        "widgets": [
            {"index": 0, "value": 3, "checked": 0, "style": 1, "visible": 1},
        ],
    }
    if app:
        child.update(
            app_screen=1,
            logic_booted=1,
            scheduler_steps=12,
            bus_drops=0,
            texts=["Žluť".encode().hex()],
        )
    state = simulator._decode_runtime_state((json.dumps(child) + "\n").encode("utf-8"), "error")
    assert state["runtime_simulation"] is True
    assert state["widgets"] == child["widgets"]
    assert state["simulation"] == mock_provenance("error", "connected")
    if app:
        assert state["texts"] == ["Žluť"] and state["app_screen"] == 1
        assert state["scheduler_steps"] == 12 and state["bus_drops"] == 0


def test_actual_c_source_emits_runtime_marker_not_wrapper_owned_field():
    source = (simulator.ROOT / "tools/native_simulator/main.c").read_text(encoding="utf-8")
    assert r'printf("{\"runtime_simulation\":true,\"display_status\":%d,\"widgets\":[' in source
    assert r"\"simulation\"" not in source


@pytest.mark.parametrize("marker", [False, 1, None, "true", {}, []])
def test_missing_or_non_boolean_true_runtime_marker_is_refused(marker):
    with pytest.raises(ValueError, match="identify its simulated runtime"):
        simulator._decode_runtime_state(
            json.dumps({"runtime_simulation": marker}).encode(), "connected"
        )
    with pytest.raises(ValueError, match="identify its simulated runtime"):
        simulator._decode_runtime_state(b"{}", "connected")


@pytest.mark.parametrize("forged", [True, False, None, {}, {"hardware_transport": "real"}])
def test_any_child_owned_transport_field_is_refused_even_with_valid_runtime_marker(forged):
    child = {"runtime_simulation": True, "simulation": forged}
    with pytest.raises(ValueError, match="transport provenance"):
        simulator._decode_runtime_state(json.dumps(child).encode(), "connected")


@pytest.mark.parametrize("stdout", [b"", b" \n", b"[]", b"null", b"not-json"])
def test_empty_or_non_object_runtime_output_has_explicit_failure(stdout):
    with pytest.raises(ValueError, match=r"no JSON state|JSON object|Expecting value"):
        simulator._decode_runtime_state(stdout, "connected")


def test_cleanup_rejects_changed_private_directory_identity_before_recursive_delete(
    tmp_path, monkeypatch
):
    private = tmp_path / "espos-runtime-TEST_ONLY"
    private.mkdir()
    info = private.lstat()
    monkeypatch.setattr(
        simulator.shutil,
        "rmtree",
        lambda *args, **options: pytest.fail("changed identity must not trigger deletion"),
    )
    with pytest.raises(RuntimeError, match="directory changed"):
        simulator._cleanup_private_build(private, tmp_path, (info.st_dev, info.st_ino + 1))
    assert private.exists()


def test_cleanup_rejects_broad_directory_before_recursive_delete(tmp_path, monkeypatch):
    info = tmp_path.lstat()
    monkeypatch.setattr(
        simulator.shutil,
        "rmtree",
        lambda *args, **options: pytest.fail("broad path must not trigger deletion"),
    )
    with pytest.raises(RuntimeError, match="directory changed"):
        simulator._cleanup_private_build(tmp_path, tmp_path.parent, (info.st_dev, info.st_ino))
    assert tmp_path.exists()


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("display", ["connected", "disconnected", "error"])
@pytest.mark.parametrize(
    "events",
    [
        ["tick:1"],
        ["tick:1000"] * 6,
        [0, "button:0:release", "tick:7", "button:255:press", "tick:1", 255],
    ],
)
def test_timed_ingress_reaches_the_child_in_order_and_keeps_provenance(
    tmp_path, pipeline, app, display, events
):
    _compiler, created, calls = pipeline
    state = simulator.run(
        tmp_path / "TEST_ONLY-scene.json",
        tmp_path / "TEST_ONLY-frame.pgm",
        events,
        display,
        app=app,
    )
    assert calls[1][0][3:] == list(map(str, events))
    assert ("-DSIM_APP=1" in calls[0][0]) is app
    assert state["runtime_simulation"] is True
    assert state["simulation"] == mock_provenance(display)
    assert not created[0].exists()


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize(
    "events",
    [
        ["button:256:press"],
        ["button:0:RELEASE"],
        ["button:0:1"],
        ["tick:0"],
        ["tick:1001"],
        ["tick:1\x00"],
        ["tick:1000"] * 6 + [0],
        ["tick:1"] * 257,
        [{"button": 0, "pressed": False}],
        ["../arbitrary"],
        ["cmd.exe"],
        ["button:0:press", "tick:1000", "bad"],
    ],
)
def test_timed_ingress_validation_precedes_all_compiler_and_filesystem_work(
    tmp_path, monkeypatch, app, events
):
    def forbidden(*args, **options):
        pytest.fail("invalid timed ingress must fail before compiler/filesystem/process work")

    monkeypatch.setattr(simulator.shutil, "which", forbidden)
    monkeypatch.setattr(simulator.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(simulator, "_ordinary_path", forbidden)
    monkeypatch.setattr(simulator, "generate_ui_design_multi_pair", forbidden)
    monkeypatch.setattr(simulator, "run_child", forbidden)
    with pytest.raises(ValueError, match="At most 256"):
        simulator.run(tmp_path / "unused.json", tmp_path / "unused.pgm", events, app=app)


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("cleanup", [True, False, None])
@pytest.mark.parametrize("display", ["disconnected", "error"])
def test_timed_runtime_failure_has_the_same_owned_cleanup_contract(
    tmp_path, pipeline, monkeypatch, app, cleanup, display
):
    _compiler, created, calls = pipeline
    original_child = simulator.run_child

    def child(command, **options):
        if len(calls) == 0:
            return original_child(command, **options)
        assert command[3:] == ["button:0:press", "tick:2", "button:0:release"]
        raise SimulatorProcessError("simulator-timeout", cleanup_confirmed=cleanup)

    monkeypatch.setattr(simulator, "run_child", child)
    with pytest.raises(SimulatorProcessError, match="simulator-timeout") as caught:
        simulator.run(
            tmp_path / "TEST_ONLY-scene.json",
            tmp_path / "TEST_ONLY-frame.pgm",
            ["button:0:press", "tick:2", "button:0:release"],
            display,
            app=app,
        )
    assert len(calls) == 1
    assert created[0].exists() is (cleanup is not True)
    assert (caught.value.retained_build == str(created[0])) if cleanup is not True else True


@pytest.mark.parametrize("display", ["connected", "disconnected", "error"])
@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (
            {"runtime_simulation": True, "simulation": {"hardware_transport": "real"}},
            "transport provenance",
        ),
        ({"runtime_simulation": 1}, "explicitly identify"),
        (
            {"runtime_simulation": True, "display_status": 0, "texts": ["not-hex"]},
            "non-hexadecimal",
        ),
    ],
)
def test_timed_child_decode_failure_cleans_the_private_build(
    tmp_path, pipeline, monkeypatch, display, app, response, error
):
    _compiler, created, _calls = pipeline
    response = dict(response)
    if "display_status" in response:
        response["display_status"] = {"connected": 0, "disconnected": 0x105, "error": -1}[display]
    monkeypatch.setattr(
        simulator,
        "run_child",
        lambda *args, **options: ProcessResult(
            0, json.dumps(response).encode(), b"", "TEST_ONLY-mocked-process", True
        ),
    )
    with pytest.raises(ValueError, match=error):
        simulator.run(
            tmp_path / "TEST_ONLY-scene.json",
            tmp_path / "TEST_ONLY-frame.pgm",
            ["tick:1", "button:0:release"],
            display,
            app=app,
        )
    assert not created[0].exists()


def test_cli_passes_the_validated_event_sequence_without_native_execution(
    tmp_path, monkeypatch, capsys
):
    events_seen = []

    def fixture_run(scene, output, events, display, *, app):
        events_seen.append((events, display, app))
        return {"TEST_ONLY": True}

    monkeypatch.setattr(simulator, "run", fixture_run)
    monkeypatch.setattr(
        simulator.sys,
        "argv",
        [
            "simulator",
            str(tmp_path / "unused.json"),
            "--output",
            str(tmp_path / "unused.pgm"),
            "--app",
            "--display",
            "error",
            "--events",
            "0,button:0:release,tick:17,action:menu.item0:0",
        ],
    )
    simulator.main()
    assert events_seen == [
        ([0, "button:0:release", "tick:17", "action:menu.item0:0"], "error", True)
    ]
    assert json.loads(capsys.readouterr().out) == {"TEST_ONLY": True}


@pytest.mark.parametrize(
    "events", ["0,", "tick:0", "button:0:1", "../arbitrary", "tick:1000," * 6 + "0"]
)
def test_cli_rejects_bad_events_before_calling_the_runner(tmp_path, monkeypatch, capsys, events):
    monkeypatch.setattr(
        simulator, "run", lambda *args, **options: pytest.fail("runner must not be called")
    )
    monkeypatch.setattr(
        simulator.sys,
        "argv",
        [
            "simulator",
            str(tmp_path / "unused.json"),
            "--output",
            str(tmp_path / "unused.pgm"),
            "--events",
            events,
        ],
    )
    with pytest.raises(SystemExit) as caught:
        simulator.main()
    assert caught.value.code == 1
    assert "At most 256" in capsys.readouterr().err


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("initial", ["connected", "disconnected", "error"])
@pytest.mark.parametrize("final", ["connected", "disconnected", "error"])
def test_hot_sequence_keeps_ingress_order_initial_config_and_reported_final_status(
    tmp_path, pipeline, app, initial, final
):
    _compiler, created, calls = pipeline
    events = [
        "button:0:press",
        "display:disconnected",
        "tick:3",
        "button:0:release",
        "display:error",
        "tick:2",
        "display:connected",
        "tick:1",
        "display:" + final,
    ]
    state = simulator.run(
        tmp_path / "TEST_ONLY-scene.json",
        tmp_path / "TEST_ONLY-frame.pgm",
        events,
        initial,
        app=app,
    )
    assert calls[1][0][3:] == events
    assert calls[1][0][2] == str({"connected": 0, "disconnected": 0x105, "error": -1}[initial])
    assert state["display_status"] == {"connected": 0, "disconnected": 0x105, "error": -1}[final]
    assert state["simulation"] == mock_provenance(initial, final)
    assert state["runtime_simulation"] is True
    assert state["widgets"] == [{"value": 3}]  # returned child fixture, never a host UI model
    assert not created[0].exists()


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize(
    "events",
    [
        ["display:CONNECTED"],
        ["display:connected\x00"],
        ["display:0"],
        ["display:connected:tick:1"],
        ["display:../path"],
        ["display:cmd.exe"],
        [{"display": "connected"}],
        ["display:error"] * 257,
        ["tick:1000"] * 6 + ["display:connected"],
        ["display:disconnected", "tick:1", "display: connected"],
    ],
)
def test_hot_display_validation_precedes_compiler_filesystem_and_generation(
    tmp_path, monkeypatch, app, events
):
    def forbidden(*args, **options):
        pytest.fail("invalid hot display step must fail before compiler/filesystem/process work")

    monkeypatch.setattr(simulator.shutil, "which", forbidden)
    monkeypatch.setattr(simulator.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(simulator, "_ordinary_path", forbidden)
    monkeypatch.setattr(simulator, "generate_ui_design_multi_pair", forbidden)
    monkeypatch.setattr(simulator, "run_child", forbidden)
    with pytest.raises(ValueError, match="At most 256"):
        simulator.run(tmp_path / "unused.json", tmp_path / "unused.pgm", events, app=app)


@pytest.mark.parametrize(
    ("status", "final"), [(0, "connected"), (0x105, "disconnected"), (-1, "error")]
)
def test_decoder_uses_observed_child_status_separately_from_initial_configuration(status, final):
    child = {"runtime_simulation": True, "display_status": status, "widgets": []}
    state = simulator._decode_runtime_state(json.dumps(child).encode(), "error")
    assert state["display_status"] == status
    assert state["simulation"] == mock_provenance("error", final)


@pytest.mark.parametrize(
    "status", [True, False, 0.0, -1.0, "0", "connected", None, [], {}, 1, 256, 262, 10**100]
)
def test_final_status_requires_exact_builtin_int_and_known_mock_driver_status(status):
    with pytest.raises(ValueError, match="bounded integer display_status"):
        simulator._decode_runtime_state(
            json.dumps({"runtime_simulation": True, "display_status": status}).encode(), "connected"
        )


def test_missing_final_status_is_not_inferred_from_initial_config():
    with pytest.raises(ValueError, match="bounded integer display_status"):
        simulator._decode_runtime_state(b'{"runtime_simulation":true}', "connected")


@pytest.mark.parametrize(
    "key", ["simulation", "hardware_transport", "initial_display", "final_display"]
)
@pytest.mark.parametrize("value", ["real", "mock", None, False, {}])
def test_child_cannot_supply_transport_or_display_provenance_fields(key, value):
    child = {"runtime_simulation": True, "display_status": 0, key: value}
    with pytest.raises(ValueError, match="transport provenance"):
        simulator._decode_runtime_state(json.dumps(child).encode(), "connected")


@pytest.mark.parametrize(
    "stdout",
    [
        b'{"runtime_simulation":true,"display_status":-1,"display_status":0}',
        b'{"runtime_simulation":false,"runtime_simulation":true,"display_status":0}',
        b'{"runtime_simulation":true,"display_status":0,"widgets":[{"value":1,"value":2}]}',
    ],
)
def test_ambiguous_duplicate_child_json_is_refused(stdout):
    with pytest.raises(ValueError, match="duplicate JSON fields"):
        simulator._decode_runtime_state(stdout, "connected")


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize(
    ("response", "error"),
    [
        (
            {"runtime_simulation": True, "display_status": 0},  # ignored hot disconnect
            "does not match validated ingress",
        ),
        ({"runtime_simulation": True, "display_status": True}, "bounded integer display_status"),
        ({"runtime_simulation": True}, "bounded integer display_status"),
        (
            {"runtime_simulation": True, "display_status": 0x105, "hardware_transport": "real"},
            "transport provenance",
        ),
        (
            {
                "runtime_simulation": True,
                "display_status": 0x105,
                "simulation": {"hardware_transport": "mock"},
            },
            "transport provenance",
        ),
    ],
)
def test_hot_response_mismatch_forgery_and_missing_status_preserve_cleanup(
    tmp_path, pipeline, monkeypatch, app, response, error
):
    _compiler, created, _calls = pipeline
    monkeypatch.setattr(
        simulator,
        "run_child",
        lambda *args, **options: ProcessResult(
            0, json.dumps(response).encode(), b"", "TEST_ONLY-mocked-process", True
        ),
    )
    with pytest.raises(ValueError, match=error):
        simulator.run(
            tmp_path / "TEST_ONLY-scene.json",
            tmp_path / "TEST_ONLY-frame.pgm",
            ["display:error", "tick:2", "display:disconnected"],
            "connected",
            app=app,
        )
    assert not created[0].exists()


@pytest.mark.parametrize("app", [False, True])
@pytest.mark.parametrize("cleanup", [True, False, None])
def test_hot_process_failure_preserves_owned_cleanup_and_retained_build_rules(
    tmp_path, pipeline, monkeypatch, app, cleanup
):
    _compiler, created, calls = pipeline
    original_child = simulator.run_child

    def child(command, **options):
        if len(calls) == 0:
            return original_child(command, **options)
        assert command[3:] == ["display:disconnected", "tick:1", "display:connected"]
        raise SimulatorProcessError("simulator-timeout", cleanup_confirmed=cleanup)

    monkeypatch.setattr(simulator, "run_child", child)
    with pytest.raises(SimulatorProcessError) as caught:
        simulator.run(
            tmp_path / "TEST_ONLY-scene.json",
            tmp_path / "TEST_ONLY-frame.pgm",
            ["display:disconnected", "tick:1", "display:connected"],
            app=app,
        )
    assert len(calls) == 1
    assert created[0].exists() is (cleanup is not True)
    if cleanup is not True:
        assert caught.value.retained_build == str(created[0])


def test_cli_hot_display_sequence_uses_the_same_validated_ingress(tmp_path, monkeypatch, capsys):
    calls = []

    def fixture_run(scene, output, events, display, *, app):
        calls.append((events, display, app))
        return {"TEST_ONLY": True}

    monkeypatch.setattr(simulator, "run", fixture_run)
    monkeypatch.setattr(
        simulator.sys,
        "argv",
        [
            "simulator",
            str(tmp_path / "unused.json"),
            "--output",
            str(tmp_path / "unused.pgm"),
            "--display",
            "error",
            "--events",
            "display:disconnected,button:0:release,tick:4,display:connected",
        ],
    )
    simulator.main()
    assert calls == [
        (
            ["display:disconnected", "button:0:release", "tick:4", "display:connected"],
            "error",
            False,
        )
    ]
    assert json.loads(capsys.readouterr().out) == {"TEST_ONLY": True}
