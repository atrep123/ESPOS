"""Focused fake runner/thread/UI seams only. Run with --noconftest; no GUI/spawn.

Existing wrapper compilation, environment setup and native execution are mocked.
App hooks are compiled from their actual AST with inert pygame/app collaborators,
so the real app module/constructor, exports and repository fixtures never run.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cyberpunk_designer import runtime_preview as preview  # noqa: E402
from tools import espos_runtime_simulator as wrapper  # noqa: E402
from tools.simulator_process import ProcessResult, SimulatorProcessError  # noqa: E402


class ManualThread:
    def __init__(self, *, target, args, **options):
        self.target, self.args = target, args
        self.alive = False
        self.joins = []

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def join(self, *, timeout):
        self.joins.append(timeout)
        assert timeout == 0

    def finish(self):
        self.target(*self.args)
        self.alive = False


def document():
    return {
        "opaque": {"keep": [1]},
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [{"type": "button", "text": "unsaved"}],
            }
        },
    }


def state():
    return {
        "runtime_simulation": True,
        "display_status": 0,
        "texts": ["observed"],
        "simulation": {"hardware_transport": "mock", "final_display": "connected"},
    }


@pytest.fixture
def harness(tmp_path):
    frames, statuses, calls = [], [], []

    def runner(scene, output, events, display, *, app, cancel_event):
        calls.append((json.loads(scene.read_text()), list(events), display, app, cancel_event))
        output.write_bytes(preview.PGM_HEADER + bytes([17]) * (256 * 128))
        return state()

    controller = preview.RuntimePreview(
        on_frame=lambda frame, value: frames.append((frame, value)),
        on_status=statuses.append,
        runner=runner,
        thread_factory=ManualThread,
        workspace_parent=tmp_path,
    )
    return controller, frames, statuses, calls


def finish(controller, key="doc"):
    work = controller._work
    work.thread.finish()
    controller.poll(key)
    return work


def test_detached_snapshot_events_single_owner_and_ui_thread_delivery(harness):
    controller, frames, statuses, calls = harness
    source, events = document(), [0, "tick:1"]
    assert controller.start(source, "doc", events)
    assert not controller.start(document(), "doc")
    source["opaque"]["keep"].append(2)
    source["scenes"]["main"]["widgets"][0]["text"] = "later"
    events.append(1)
    work = controller._work
    work.thread.finish()
    assert frames == [] and controller.owns_work
    assert calls[0][0]["opaque"] == {"keep": [1]}
    assert calls[0][0]["scenes"]["main"]["widgets"][0]["text"] == "unsaved"
    assert calls[0][1] == [0, "tick:1"]
    controller.poll("doc")
    assert len(calls) == len(frames) == 1 and not controller.owns_work
    assert frames[0][0].pixels == bytes([17]) * (256 * 128)
    assert frames[0][1] == state() and statuses[-1] == "completed (mock display)"
    frames[0][1]["texts"].append("consumer mutation")
    assert controller.state["texts"] == ["observed"]
    assert work.thread.joins == [0] and not work.workspace.exists()


@pytest.mark.parametrize("reason", ["stop", "switch", "reload"])
def test_cancelled_generation_never_delivers_and_waits_for_join(harness, reason):
    controller, frames, _statuses, calls = harness
    assert controller.start(document(), "doc")
    work = controller._work
    work.thread.finish()  # Completion races with the user action before UI poll.
    if reason == "stop":
        controller.stop()
        key = "doc"
    else:
        key = reason
        controller.sync_document(key)
    assert controller.owns_work and work.cancel.is_set()
    assert not controller.start(document(), key)
    controller.poll(key)
    assert not controller.owns_work and frames == [] and len(calls) == 1
    assert work.thread.joins == [0]
    controller.poll(key)
    assert frames == [] and work.thread.joins == [0]


def test_stop_before_worker_admission_never_invokes_runner(harness):
    controller, frames, _statuses, calls = harness
    controller.start(document(), "doc")
    controller.stop()
    controller.stop()
    assert controller.owns_work
    work = finish(controller)
    assert calls == frames == [] and not controller.owns_work
    assert work.cleanup_confirmed is True and work.workspace is None


def test_cancel_during_fake_run_drops_frame_and_cleans_after_completion(harness):
    controller, frames, _statuses, _calls = harness

    def runner(scene, output, events, display, **options):
        controller.stop()
        output.write_bytes(preview.PGM_HEADER + bytes(256 * 128))
        return state()

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    assert frames == [] and not controller.owns_work
    assert not work.workspace.exists() and work.cleanup_confirmed is True


@pytest.mark.parametrize("confirmed", [False, None])
def test_uncertain_cleanup_retains_owner_partial_and_build_without_retry(
    harness, tmp_path, confirmed
):
    controller, frames, _statuses, calls = harness
    retained_build = tmp_path / "producer-retained"
    retained_build.mkdir()
    (retained_build / "partial").write_bytes(b"TEST_ONLY")

    def runner(scene, output, events, display, **options):
        calls.append("attempt")
        output.write_bytes(b"partial frame")
        error = SimulatorProcessError("simulator-cancelled", cleanup_confirmed=confirmed)
        error.retained_build = str(retained_build)
        raise error

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    assert controller.owns_work and frames == []
    assert work.workspace.exists() and (work.workspace / "frame.pgm").exists()
    assert retained_build.exists() and len(controller.retained_paths) == 2
    for _ in range(3):
        controller.stop()
        controller.poll("other")
        assert not controller.start(document(), "other")
    assert calls == ["attempt"] and work.thread.joins == [0]
    assert controller.status.startswith("cleanup-uncertain")


def test_unknown_runner_failure_is_not_cleanup_confirmation(harness):
    controller, frames, _statuses, _calls = harness

    def runner(*args, **kwargs):
        raise RuntimeError("TEST_ONLY unknown failure")

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    assert controller.owns_work and frames == [] and work.workspace.exists()


def test_confirmed_startup_rejection_releases_without_accepting_frame(harness):
    controller, frames, statuses, _calls = harness

    def runner(*args, **kwargs):
        raise SimulatorProcessError("TEST_ONLY-rejected", cleanup_confirmed=True)

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    assert not controller.owns_work and frames == [] and not work.workspace.exists()
    assert statuses[-1] == "TEST_ONLY-rejected"


@pytest.mark.parametrize(
    "data",
    [
        b"P2\n256 128\n255\n",
        b"P5\n1 1\n255\n\x00",
        preview.PGM_HEADER + b"short",
        preview.PGM_HEADER + bytes(256 * 128 + 1),
    ],
    ids=["wrong-magic", "wrong-size", "truncated", "extra-pixels"],
)
def test_invalid_pgm_never_reaches_consumer_after_confirmed_run(harness, data):
    controller, frames, statuses, _calls = harness

    def runner(scene, output, *args, **kwargs):
        output.write_bytes(data)
        return state()

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    assert not controller.owns_work and frames == [] and not work.workspace.exists()
    assert statuses[-1] == "runtime-preview-failed"


def test_snapshot_cleanup_failure_retains_owner_even_after_valid_result(harness, monkeypatch):
    controller, frames, _statuses, _calls = harness
    controller.start(document(), "doc")

    def failed(*args):
        raise RuntimeError("TEST_ONLY cleanup failed")

    monkeypatch.setattr(wrapper, "_cleanup_private_build", failed)
    work = finish(controller)
    assert controller.owns_work and work.workspace.exists() and frames == []


def test_poll_does_not_wait_for_blocked_fake_runner(tmp_path):
    entered, release = threading.Event(), threading.Event()

    def runner(scene, output, *args, **kwargs):
        entered.set()
        assert release.wait(timeout=2)
        raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)

    controller = preview.RuntimePreview(
        on_frame=lambda *args: None,
        on_status=lambda _: None,
        runner=runner,
        workspace_parent=tmp_path,
    )
    controller.start(document(), "doc")
    work = controller._work
    try:
        assert entered.wait(timeout=2)
        for _ in range(20):
            controller.poll("doc")
        controller.stop()
        assert controller.owns_work and work.thread.is_alive()
    finally:
        release.set()
        work.thread.join(timeout=2)  # Test-only teardown, not editor polling.
    assert not work.thread.is_alive()
    controller.poll("doc")
    assert not controller.owns_work


@dataclass
class FakeWidget:
    type: str = "button"
    text: str = "unsaved"


@dataclass
class FakeScene:
    name: str = "main"
    width: int = 256
    height: int = 128
    widgets: list = field(default_factory=lambda: [FakeWidget()])


@pytest.mark.parametrize("as_list", [False, True])
def test_snapshot_preserves_opaque_metadata_without_save_or_exports(as_list):
    designer = SimpleNamespace(
        current_scene="main",
        scenes={"other": FakeScene("other"), "main": FakeScene()},
        width=256,
        height=128,
        _document_metadata={"opaque": {"keep": [1]}},
        _scene_metadata={"main": {"id": "main", "unknown": ["retain"]}, "other": {"id": "other"}},
        _scenes_as_list=as_list,
    )
    original = copy.deepcopy(designer.__dict__)
    snapshot = preview.detached_document(designer)
    scenes = snapshot["scenes"]
    active = scenes[0] if as_list else scenes["main"]
    assert active["id"] == "main" and active["unknown"] == ["retain"]
    assert active["widgets"][0]["text"] == "unsaved"
    snapshot["opaque"]["keep"].append(2)
    active["unknown"].append("mutation")
    assert designer.__dict__ == original


def app_hooks(**collaborators):
    tree = ast.parse((ROOT / "cyberpunk_designer/app.py").read_text())
    source = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CyberpunkEditorApp"
    )
    names = {
        "_build_toolbar",
        "_runtime_document_key",
        "_runtime_preview_status",
        "_accept_runtime_frame",
        "_draw_runtime_preview",
        "_start_runtime_preview",
        "_stop_runtime_preview",
        "load_json",
        "_new_scene",
        "_switch_scene",
        "_jump_to_scene",
        "run",
        "_run_editor_loop",
    }
    source.body = [
        node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    module = ast.Module(body=[source], type_ignores=[])
    namespace = {
        "runtime_preview": preview,
        "time": SimpleNamespace(time=lambda: 0),
        "os": SimpleNamespace(getenv=lambda *args: ""),
        "text_metrics": SimpleNamespace(is_device_profile=lambda _: False),
        "sys": SimpleNamespace(exit=lambda _: None),
        **collaborators,
    }
    exec(compile(module, "actual-editor-hooks", "exec"), namespace)  # noqa: S102 -- explicit trusted AST, inert collaborators
    return namespace["CyberpunkEditorApp"]


def test_actual_toolbar_action_and_frame_blit_without_pygame_import(harness):
    controller, _frames, _statuses, _calls = harness
    # Fixed inert fixture types only; no app or pygame module is imported.
    path = ROOT / "tests/test_runtime_preview_layout.py"
    spec = importlib.util.spec_from_file_location("_preview_layout_fixture_types", path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    Rect, Surface, Font = helpers.Rect, helpers.Surface, helpers.Font
    images = []
    surface = Surface((256, 128), tag="snapshot")

    def frombuffer(rgb, size, mode):
        images.append((rgb, size, mode))
        return surface

    cls = app_hooks(
        pygame=SimpleNamespace(
            Rect=Rect,
            image=SimpleNamespace(frombuffer=frombuffer),
            draw=SimpleNamespace(rect=lambda *args: None),
            transform=SimpleNamespace(scale=lambda value, size: Surface(size, tag=value.tag)),
        ),
        _constants=SimpleNamespace(
            PALETTE={"text": "text", "panel": "panel", "panel_border": "border"}
        ),
    )
    app = cls()
    app.designer = SimpleNamespace(
        current_scene="main", scenes={"main": FakeScene()}, width=256, height=128
    )
    app.json_path, app.state, app.hardware_profile = Path("TEST_ONLY.json"), object(), None
    app._runtime_preview = controller
    app._runtime_preview_surface = None
    app._dirty_scenes = {"author-change"}
    app.window = Surface((800, 500), tag="window")
    app.logical_surface = Surface((800, 400), tag="logical")
    app.font_small = Font()
    app.layout = SimpleNamespace(canvas_rect=Rect(120, 38, 320, 260))
    for name in (
        "save_json",
        "_do_undo",
        "_do_redo",
        "_open_template_menu",
        "_open_icon_palette",
        "_open_live_dialog",
        "_auto_arrange_grid",
        "_fit_selection_to_text",
        "_fit_selection_to_widget",
        "_export_svg",
        "_cycle_board",
        "_open_logic_editor",
        "_open_build_flash",
        "_flash_firmware",
        "_toggle_overflow_warnings",
    ):
        setattr(app, name, lambda: None)
    controller._on_frame = app._accept_runtime_frame
    controller._on_status = app._runtime_preview_status
    app._build_toolbar()
    actions = dict(app.toolbar_actions)
    actions["Simulator"]()
    actions["Simulator"]()
    key = app._runtime_document_key()
    finish(controller, key)
    app._draw_runtime_preview()
    assert images[0] == (bytes([17]) * (256 * 128 * 3), (256, 128), "RGB")
    assert app.logical_surface.operations == [
        ("SIM SNAPSHOT | MOCK", Rect(182, 40, 114, 10), Rect(120, 38, 320, 260)),
        ("snapshot", Rect(182, 52, 256, 128), Rect(120, 38, 320, 260)),
    ]
    assert app._runtime_preview_hitbox == Rect(180, 38, 260, 144)
    assert app.window.operations == []
    assert app._runtime_preview_state == state()
    assert app._dirty_scenes == {"author-change"}
    actions["Stop simulator"]()
    assert app._runtime_preview_surface is None


@pytest.mark.parametrize(
    ("method", "args"),
    [("load_json", ()), ("_new_scene", ()), ("_switch_scene", (1,)), ("_jump_to_scene", (1,))],
)
def test_actual_document_hooks_signal_cancel_before_replacement(harness, method, args):
    controller, _frames, _statuses, _calls = harness
    controller.start(document(), "doc")
    work = controller._work
    observed = []

    def change(*args):
        observed.append(work.cancel.is_set())

    cls = app_hooks(
        io_ops=SimpleNamespace(load_json=change),
        scene_ops=SimpleNamespace(new_scene=change, switch_scene=change, jump_to_scene=change),
    )
    app = cls()
    app._runtime_preview = controller
    getattr(app, method)(*args)
    assert observed == [True] and controller.owns_work
    finish(controller)


def test_actual_exit_loop_polls_until_confirmed_join_without_autosave(harness):
    controller, frames, _statuses, _calls = harness
    controller.start(document(), "doc")
    work = controller._work
    exits, quits, autosaves = [], [], []
    cls = app_hooks(
        pygame=SimpleNamespace(quit=lambda: quits.append(True)),
        sys=SimpleNamespace(exit=exits.append),
    )
    app = cls()
    app._runtime_preview, app.running = controller, True
    app._runtime_document_key = lambda: "doc"
    app.vsync_enabled = app.auto_scale_adjust = app.auto_optimize = False
    app.fps_limit, app.fps_history = 30, []
    app.clock = SimpleNamespace(tick=lambda _: 1, get_fps=lambda: 30)
    count = 0

    def events():
        nonlocal count
        count += 1
        if count == 1:
            app.running = False
        else:
            assert exits == quits == [] and work.cancel.is_set() and controller.owns_work
            work.thread.finish()

    app._handle_events = events
    app._update_cursor = app._optimized_draw_frame = app._draw_runtime_preview = lambda: None
    app._maybe_hide_help_overlay = lambda: None
    app._maybe_autosave = lambda: autosaves.append(True)
    app.run()
    assert count == 2 and exits == [0] and quits == [True]
    assert frames == autosaves == [] and work.thread.joins == [0]


@pytest.mark.parametrize("confirmed", [False, None])
def test_actual_exit_loop_cannot_quit_or_release_uncertain_owner(harness, confirmed):
    controller, frames, _statuses, _calls = harness

    def runner(*args, **kwargs):
        raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=confirmed)

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    exits, quits = [], []
    cls = app_hooks(
        pygame=SimpleNamespace(quit=lambda: quits.append(True)),
        sys=SimpleNamespace(exit=exits.append),
    )
    app = cls()
    app._runtime_preview, app.running = controller, False
    app._runtime_document_key = lambda: "doc"
    app.vsync_enabled = app.auto_scale_adjust = app.auto_optimize = False
    app.fps_limit, app.fps_history = 30, []
    app.clock = SimpleNamespace(tick=lambda _: 1, get_fps=lambda: 30)
    app._update_cursor = app._optimized_draw_frame = app._draw_runtime_preview = lambda: None
    count = 0

    class EndObservation(BaseException):
        pass

    def events():
        nonlocal count
        count += 1
        assert controller.owns_work and work.workspace.exists()
        assert exits == quits == frames == []
        if count == 3:
            raise EndObservation

    app._handle_events = events
    with pytest.raises(EndObservation):
        app.run()
    assert count == 3 and controller.owns_work and work.cancel.is_set()
    assert work.thread.joins == [0]


def test_frame_consumer_stop_cannot_receive_stale_completion_status(harness):
    controller, frames, statuses, _calls = harness

    def consumer(frame, value):
        frames.append((frame, value))
        if frame is not None:
            controller.stop()

    controller._on_frame = consumer
    controller.start(document(), "doc")
    finish(controller)
    assert controller.frame is controller.state is None
    assert "completed (mock display)" not in statuses


def test_editor_error_signals_cancel_and_polls_before_propagating(harness):
    controller, frames, _statuses, _calls = harness
    controller.start(document(), "doc")
    work = controller._work
    pumps, quits = [], []

    def pump():
        assert work.cancel.is_set() and controller.owns_work
        pumps.append(True)
        work.thread.finish()

    cls = app_hooks(
        pygame=SimpleNamespace(
            event=SimpleNamespace(pump=pump), error=RuntimeError, quit=lambda: quits.append(True)
        )
    )
    app = cls()
    app._runtime_preview = controller
    app.clock = SimpleNamespace(tick=lambda _: None)

    def broken_loop():
        raise RuntimeError("TEST_ONLY editor error")

    app._run_editor_loop = broken_loop
    app._runtime_preview_status = lambda _: None
    with pytest.raises(RuntimeError, match="TEST_ONLY editor error"):
        app.run()
    assert pumps == [True] and frames == quits == []
    assert work.thread.joins == [0] and not controller.owns_work


@pytest.mark.parametrize("confirmed", [False, None])
def test_editor_error_never_drops_uncertain_owner(harness, confirmed):
    controller, frames, _statuses, _calls = harness

    def runner(*args, **kwargs):
        raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=confirmed)

    controller._runner = runner
    controller.start(document(), "doc")
    work = finish(controller)
    pumps = []

    class EndObservation(BaseException):
        pass

    def pump():
        assert controller.owns_work and work.cancel.is_set() and work.workspace.exists()
        pumps.append(True)
        if len(pumps) == 3:
            raise EndObservation

    cls = app_hooks(pygame=SimpleNamespace(event=SimpleNamespace(pump=pump), error=RuntimeError))
    app = cls()
    app._runtime_preview = controller
    app.clock = SimpleNamespace(tick=lambda _: None)

    def broken_loop():
        raise RuntimeError("TEST_ONLY editor error")

    app._run_editor_loop = broken_loop
    messages = []
    app._runtime_preview_status = messages.append
    with pytest.raises(EndObservation):
        app.run()
    assert controller.owns_work and frames == [] and len(pumps) == 3
    assert all(message.startswith("cleanup-uncertain") for message in messages)


def test_thread_start_failure_does_not_call_runner_or_hold_owner(harness):
    controller, frames, statuses, calls = harness

    class RejectedThread(ManualThread):
        def start(self):
            raise RuntimeError("TEST_ONLY rejected")

    controller._thread_factory = RejectedThread
    assert not controller.start(document(), "doc")
    assert not controller.owns_work and frames == calls == []
    assert statuses[-1] == "runtime-preview-start-failed"


def test_poll_performs_no_filesystem_io_after_worker_completion(harness, monkeypatch):
    controller, frames, _statuses, _calls = harness
    controller.start(document(), "doc")
    controller._work.thread.finish()

    def forbidden(*args, **kwargs):
        pytest.fail("UI poll performed file IO")

    monkeypatch.setattr(Path, "open", forbidden)
    controller.poll("doc")
    assert len(frames) == 1 and not controller.owns_work


@pytest.mark.parametrize(
    "invalid", [None, {}, {"scenes": {}}, {"scenes": {"main": {"value": float("nan")}}}]
)
def test_invalid_snapshot_has_no_owner_or_thread_admission(harness, invalid):
    controller, frames, _statuses, calls = harness
    with pytest.raises((ValueError, TypeError)):
        controller.start(invalid, "doc")
    assert not controller.owns_work and frames == calls == []


def test_snapshot_limit_rejected_without_owner(harness):
    controller, frames, _statuses, calls = harness
    value = document()
    value["large"] = "x" * preview.SNAPSHOT_LIMIT
    with pytest.raises(ValueError, match="snapshot-invalid"):
        controller.start(value, "doc")
    assert not controller.owns_work and frames == calls == []


@pytest.fixture
def fake_pipeline(tmp_path, monkeypatch):
    compiler = tmp_path / "TEST_ONLY-gcc"
    compiler.write_bytes(b"inert")
    created, calls = [], []
    monkeypatch.setattr(wrapper, "ROOT", tmp_path)
    monkeypatch.setattr(wrapper.shutil, "which", lambda _: str(compiler))
    monkeypatch.setattr(wrapper, "_ordinary_path", lambda *args, **kwargs: None)
    monkeypatch.setattr(wrapper, "build_environment", lambda *args: {"TEST_ONLY": "1"})
    monkeypatch.setattr(
        wrapper, "generate_ui_design_multi_pair", lambda *args, **kwargs: ("C", "H")
    )

    def private_directory(**kwargs):
        path = tmp_path / (kwargs["prefix"] + "fake")
        path.mkdir()
        created.append(path)
        return str(path)

    def child(command, **kwargs):
        calls.append(kwargs)
        return ProcessResult(
            0, b'{"runtime_simulation":true,"display_status":0}', b"", "fake", True
        )

    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", private_directory)
    monkeypatch.setattr(wrapper, "run_child", child)
    return created, calls


def test_wrapper_precancelled_token_prevents_all_lookup_generation_writes(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("cancelled operation reached compiler or filesystem")

    monkeypatch.setattr(wrapper.shutil, "which", forbidden)
    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(wrapper, "generate_ui_design_multi_pair", forbidden)
    token = threading.Event()
    token.set()
    with pytest.raises(SimulatorProcessError, match="simulator-cancelled") as caught:
        wrapper.run(tmp_path / "unused", tmp_path / "unused.pgm", [], cancel_event=token)
    assert caught.value.cleanup_confirmed is True


@pytest.mark.parametrize("supplied", [False, True])
def test_wrapper_keyword_is_optional_and_forwarded_to_both_phases(
    fake_pipeline, tmp_path, supplied
):
    created, calls = fake_pipeline
    token = threading.Event()
    options = {"cancel_event": token} if supplied else {}
    wrapper.run(tmp_path / "scene", tmp_path / "frame", [], **options)
    assert len(calls) == 2 and not created[0].exists()
    assert all(
        (call.get("cancel_event") is token) if supplied else ("cancel_event" not in call)
        for call in calls
    )


def test_wrapper_default_accepts_old_explicit_fake_signature(fake_pipeline, tmp_path, monkeypatch):
    def legacy(command, *, cwd, env, timeout):
        return ProcessResult(
            0, b'{"runtime_simulation":true,"display_status":0}', b"", "fake", True
        )

    monkeypatch.setattr(wrapper, "run_child", legacy)
    assert wrapper.run(tmp_path / "scene", tmp_path / "frame", [])["runtime_simulation"] is True


@pytest.mark.parametrize(
    "phase", ["lookup", "environment", "generation", "compile", "runtime", "decode"]
)
def test_wrapper_cancellation_between_phases_preserves_cleanup(
    fake_pipeline, tmp_path, monkeypatch, phase
):
    created, calls = fake_pipeline
    token = threading.Event()
    if phase in ("lookup", "environment", "generation", "decode"):
        owner, name = {
            "lookup": (wrapper.shutil, "which"),
            "environment": (wrapper, "build_environment"),
            "generation": (wrapper, "generate_ui_design_multi_pair"),
            "decode": (wrapper, "_decode_runtime_state"),
        }[phase]
        original = getattr(owner, name)

        def cancelled(*args, **kwargs):
            result = original(*args, **kwargs)
            token.set()
            return result

        monkeypatch.setattr(owner, name, cancelled)
    else:
        original = wrapper.run_child

        def child(*args, **kwargs):
            result = original(*args, **kwargs)
            if len(calls) == (1 if phase == "compile" else 2):
                token.set()
            return result

        monkeypatch.setattr(wrapper, "run_child", child)
    with pytest.raises(SimulatorProcessError, match="simulator-cancelled") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [], cancel_event=token)
    assert caught.value.cleanup_confirmed is True
    assert all(not path.exists() for path in created)
    expected = {
        "lookup": 0,
        "environment": 0,
        "generation": 0,
        "compile": 1,
        "runtime": 2,
        "decode": 2,
    }
    assert len(calls) == expected[phase]


@pytest.mark.parametrize("confirmed", [False, None, True])
@pytest.mark.parametrize("phase", [1, 2])
def test_wrapper_owned_cancel_retains_build_only_when_uncertain(
    fake_pipeline, tmp_path, monkeypatch, confirmed, phase
):
    created, calls = fake_pipeline
    original = wrapper.run_child

    def cancelled(*args, **kwargs):
        if len(calls) + 1 == phase:
            raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=confirmed)
        return original(*args, **kwargs)

    monkeypatch.setattr(wrapper, "run_child", cancelled)
    with pytest.raises(SimulatorProcessError, match="simulator-cancelled") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [], cancel_event=threading.Event())
    assert caught.value.cleanup_confirmed is confirmed
    assert created[0].exists() is (confirmed is not True)
    if confirmed is not True:
        assert caught.value.retained_build == str(created[0])


def test_wrapper_missing_gcc_reports_confirmed_no_child_without_files(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("missing compiler admitted setup or a child")

    monkeypatch.setattr(wrapper.shutil, "which", lambda _: None)
    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(wrapper, "run_child", forbidden)
    with pytest.raises(SimulatorProcessError, match=r"^simulator-gcc-unavailable$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [])
    assert caught.value.cleanup_confirmed is True
    assert not hasattr(caught.value, "retained_build")


@pytest.mark.parametrize(
    "options",
    [
        {"events": [True]},
        {"events": [-1]},
        {"display": "unknown"},
        {"app": 1},
        {"cancel_event": True},
    ],
)
def test_wrapper_invalid_preflight_reports_confirmed_no_child(tmp_path, monkeypatch, options):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid preflight reached a compiler lookup or filesystem")

    monkeypatch.setattr(wrapper.shutil, "which", forbidden)
    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(wrapper, "run_child", forbidden)
    arguments = {"events": [], "cancel_event": threading.Event(), **options}
    with pytest.raises(SimulatorProcessError, match=r"^simulator-preflight-failed$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", **arguments)
    assert caught.value.cleanup_confirmed is True
    assert not hasattr(caught.value, "retained_build")


@pytest.mark.parametrize("phase", ["environment", "generation", "write"])
def test_wrapper_setup_failure_confirms_only_after_private_cleanup(
    fake_pipeline, tmp_path, monkeypatch, phase
):
    created, calls = fake_pipeline

    def failed(*args, **kwargs):
        raise ValueError("TEST_ONLY invalid setup")

    if phase == "environment":
        monkeypatch.setattr(wrapper, "build_environment", failed)
    elif phase == "generation":
        monkeypatch.setattr(wrapper, "generate_ui_design_multi_pair", failed)
    else:
        monkeypatch.setattr(Path, "write_text", failed)
    with pytest.raises(SimulatorProcessError, match=r"^simulator-setup-failed$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [])
    assert caught.value.cleanup_confirmed is True and calls == []
    assert len(created) == 1 and not created[0].exists()


@pytest.mark.parametrize(
    "data",
    [b"not-json", b"\xff", b"{}", b'{"runtime_simulation":true,"display_status":"0"}'],
    ids=["json", "utf8", "missing-marker", "invalid-status"],
)
def test_wrapper_malformed_state_after_natural_returns_has_confirmed_cleanup(
    fake_pipeline, tmp_path, monkeypatch, data
):
    created, calls = fake_pipeline
    original = wrapper.run_child

    def child(*args, **kwargs):
        result = original(*args, **kwargs)
        if len(calls) == 2:
            return ProcessResult(0, data, b"", "fake", True)
        return result

    monkeypatch.setattr(wrapper, "run_child", child)
    with pytest.raises(SimulatorProcessError, match=r"^simulator-state-invalid$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [], cancel_event=threading.Event())
    assert len(calls) == 2 and caught.value.cleanup_confirmed is True
    assert not created[0].exists()


@pytest.mark.parametrize("phase", [1, 2])
@pytest.mark.parametrize("error_type", [RuntimeError, ValueError, KeyboardInterrupt])
def test_wrapper_unexpected_inflight_exception_never_recursively_cleans_or_confirms(
    fake_pipeline, tmp_path, monkeypatch, phase, error_type
):
    created, calls = fake_pipeline
    original = wrapper.run_child
    cleanup_calls = []

    def child(*args, **kwargs):
        if len(calls) + 1 == phase:
            raise error_type("TEST_ONLY unexpected in-flight failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(wrapper, "run_child", child)
    monkeypatch.setattr(wrapper, "_cleanup_private_build", lambda *args: cleanup_calls.append(args))
    with pytest.raises(SimulatorProcessError, match=r"^simulator-child-call-failed$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [])
    assert caught.value.cleanup_confirmed is None and cleanup_calls == []
    assert caught.value.retained_build == str(created[0]) and created[0].exists()
    assert len(calls) == phase - 1


@pytest.mark.parametrize("phase", ["success", "setup", "state", "cancel"])
@pytest.mark.parametrize("cleanup_behavior", ["raises", "no-removal"])
def test_wrapper_failed_private_cleanup_retains_build_and_never_leaves_stale_true(
    fake_pipeline, tmp_path, monkeypatch, phase, cleanup_behavior
):
    created, calls = fake_pipeline
    token = threading.Event()
    if cleanup_behavior == "raises":

        def failed(*args):
            raise OSError("TEST_ONLY private directory cleanup failed")

        monkeypatch.setattr(wrapper, "_cleanup_private_build", failed)
    else:
        monkeypatch.setattr(wrapper.shutil, "rmtree", lambda *args: None)

    if phase in ("setup", "cancel"):

        def generation(*args, **kwargs):
            if phase == "setup":
                raise ValueError("TEST_ONLY invalid generation")
            token.set()
            return "C", "H"

        monkeypatch.setattr(wrapper, "generate_ui_design_multi_pair", generation)
    elif phase == "state":

        def decode(*args, **kwargs):
            raise ValueError("TEST_ONLY malformed state")

        monkeypatch.setattr(wrapper, "_decode_runtime_state", decode)
    code = {
        "success": "simulator-build-cleanup-failed",
        "setup": "simulator-setup-failed",
        "state": "simulator-state-invalid",
        "cancel": "simulator-cancelled",
    }[phase]
    with pytest.raises(SimulatorProcessError, match="^" + code + "$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [], cancel_event=token)
    assert caught.value.cleanup_confirmed is None and created[0].exists()
    assert caught.value.retained_build == str(created[0])
    assert caught.value.cleanup_error == "simulator-build-cleanup-failed"
    assert len(calls) == (2 if phase in ("success", "state") else 0)


def test_wrapper_unproved_completion_receipt_retains_ownership(
    fake_pipeline, tmp_path, monkeypatch
):
    created, calls = fake_pipeline
    original = wrapper.run_child

    def child(*args, **kwargs):
        original(*args, **kwargs)
        return ProcessResult(0, b"", b"", "fake", False)

    monkeypatch.setattr(wrapper, "run_child", child)
    with pytest.raises(
        SimulatorProcessError, match=r"^simulator-child-completion-unconfirmed$"
    ) as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [])
    assert caught.value.cleanup_confirmed is None and len(calls) == 1
    assert created[0].exists() and caught.value.retained_build == str(created[0])


def test_wrapper_unreturned_directory_creation_cannot_claim_cleanup(
    fake_pipeline, tmp_path, monkeypatch
):
    _created, calls = fake_pipeline
    partial = tmp_path / "espos-runtime-unreturned"

    def interrupted_creation(**kwargs):
        partial.mkdir()
        raise OSError("TEST_ONLY allocation failed after directory creation")

    monkeypatch.setattr(wrapper.tempfile, "mkdtemp", interrupted_creation)
    with pytest.raises(SimulatorProcessError, match=r"^simulator-setup-failed$") as caught:
        wrapper.run(tmp_path / "scene", tmp_path / "frame", [])
    assert caught.value.cleanup_confirmed is None and partial.exists() and calls == []
