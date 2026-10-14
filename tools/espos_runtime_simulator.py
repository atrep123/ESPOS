"""Bounded native production UI task runner; hardware transport is simulated."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.simulator_contract import parse_cli_events, validate_inputs
from tools.simulator_environment import build_environment
from tools.simulator_process import ProcessResult, SimulatorProcessError, run_child
from tools.ui_codegen import generate_ui_design_multi_pair


def _ordinary_path(path: Path, *, directory: bool = False) -> None:
    for ancestor in (path, *path.parents):
        info = ancestor.lstat()
        if ancestor.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Simulator paths must not contain symlinks or reparse points")
    if (directory and not path.is_dir()) or (not directory and not path.is_file()):
        raise ValueError("Simulator requires ordinary existing local paths")


def _cleanup_private_build(build: Path, parent: Path, identity: tuple[int, int]) -> None:
    # Resolve and revalidate the precise mkdtemp target, never a root/glob/cwd.
    _ordinary_path(build, directory=True)
    info = build.lstat()
    if (
        build.parent != parent
        or build == Path(build.anchor)
        or not build.name.startswith("espos-runtime-")
        or (info.st_dev, info.st_ino) != identity
    ):
        raise RuntimeError("Simulator private directory changed; retained for review")
    shutil.rmtree(build)
    try:
        build.lstat()
    except FileNotFoundError:
        return
    raise RuntimeError("Simulator private directory cleanup was not confirmed")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    state = {}
    for key, value in pairs:
        if key in state:
            raise ValueError("Simulator runtime must not contain duplicate JSON fields")
        state[key] = value
    return state


def _decode_runtime_state(
    stdout: bytes, display: str, *, expected_final_display: str | None = None
) -> dict:
    lines = stdout.decode("utf-8", errors="strict").strip().splitlines()
    if not lines:
        raise ValueError("Simulator runtime returned no JSON state")
    state = json.loads(lines[-1], object_pairs_hook=_unique_json_object)
    if type(state) is not dict:
        raise ValueError("Simulator runtime must return a JSON object")
    # The C renderer reports its own runtime kind separately. Only this wrapper
    # owns the structured transport provenance; child data cannot replace it.
    if any(
        key in state
        for key in ("simulation", "hardware_transport", "initial_display", "final_display")
    ):
        raise ValueError("Simulator runtime must not replace transport provenance")
    if state.get("runtime_simulation") is not True:
        raise ValueError("Simulator runtime must explicitly identify its simulated runtime")
    status = state.get("display_status")
    statuses = {0: "connected", 0x105: "disconnected", -1: "error"}
    if type(status) is not int or status not in statuses:
        raise ValueError("Simulator runtime must report a bounded integer display_status")
    final_display = statuses[status]
    if expected_final_display is not None and final_display != expected_final_display:
        raise ValueError("Simulator runtime final display status does not match validated ingress")
    if "texts" in state:
        if type(state["texts"]) is not list or any(
            type(value) is not str for value in state["texts"]
        ):
            raise ValueError("Simulator runtime texts must be a list of hex strings")
        state["texts"] = [bytes.fromhex(value).decode("utf-8") for value in state["texts"]]
    state["simulation"] = {
        "hardware_transport": "mock",
        "display": display,
        "initial_display": display,
        "final_display": final_display,
    }
    return state


def _check_cancel(cancel_event: threading.Event | None) -> None:
    # Called only outside an active run_child; that function owns child cleanup.
    if cancel_event is not None and cancel_event.is_set():
        raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)


def run(
    scene: Path,
    output: Path,
    events: list[int | str],
    display: str = "connected",
    *,
    app: bool = False,
    cancel_event: threading.Event | None = None,
) -> dict:
    """Classify failures by child admission, then prove private-build cleanup.

    Unknown exceptions while run_child is invoked cannot certify child exit.
    A returned successful ProcessResult or a confirmed process error can; only
    then may this wrapper remove its exact private build and confirm cleanup.
    Existing non-cancellable callers retain their controlled ValueError input/
    state diagnostics. A cancellable editor invocation receives symbolic process
    errors instead, so it can distinguish failed setup from uncertain cleanup.
    """
    build = parent = identity = None
    child_inflight = False
    build_creation_pending = False
    phase = "preflight"
    failure = None
    try:
        if cancel_event is not None and type(cancel_event) is not threading.Event:
            raise ValueError("simulator-cancel-event-invalid")
        _check_cancel(cancel_event)
        events = validate_inputs(events, display, app)
        expected_final_display = display
        for event in events:
            if type(event) is str and event.startswith("display:"):
                expected_final_display = event.split(":", 1)[1]
        if app and os.name != "nt":
            raise RuntimeError(
                "The deterministic application scheduler currently requires Windows fibers"
            )
        phase = "setup"
        _check_cancel(cancel_event)
        compiler = shutil.which("gcc")
        _check_cancel(cancel_event)
        if not compiler:
            raise SimulatorProcessError("simulator-gcc-unavailable", cleanup_confirmed=True)
        # Bind the concrete paths once; do not inherit compiler overrides.
        compiler_path = Path(compiler).resolve(strict=True)
        python_path = Path(sys.executable).resolve(strict=True)
        _ordinary_path(compiler_path)
        _ordinary_path(python_path)
        _check_cancel(cancel_event)
        build_creation_pending = True
        build = Path(tempfile.mkdtemp(prefix="espos-runtime-"))
        build_creation_pending = False
        parent = build.parent
        info = build.lstat()
        identity = (info.st_dev, info.st_ino)
        _ordinary_path(build, directory=True)
        build = build.resolve(strict=True)
        _check_cancel(cancel_event)
        env = build_environment(compiler_path, python_path, build)
        _check_cancel(cancel_event)
        source, header = generate_ui_design_multi_pair(scene, source_label=scene.name)
        _check_cancel(cancel_event)
        (build / "ui_design.c").write_text(source, encoding="utf-8")
        _check_cancel(cancel_event)
        (build / "ui_design.h").write_text(header, encoding="utf-8")
        # One compiler process; private generated output never touches src/.
        names = [
            "ui_render",
            "ui_render_swbuf",
            "ui_render_text",
            "ui_render_widgets",
            "ui_nav",
            "ui_font_6x8",
            "ui_border",
            "ui_dither",
            "ui_text_layout",
            "ui_widget_style",
            "ui_rect",
            "ui_format",
            "icons",
            "icons_24",
            "icons_registry",
        ]
        sources = [ROOT / "src" / (name + ".c") for name in names]
        sources += list((ROOT / "src/services/ui").glob("*.c"))
        sources = [p for p in sources if p.name not in {"ui.c", "ui_cmd.c"}]
        sources += [
            ROOT / "test/stubs/store_stub.c",
            ROOT / "test/stubs/esp_err_stub.c",
            ROOT / "tools/native_simulator/main.c",
            ROOT / "tools/native_simulator/driver.c",
            build / "ui_design.c",
        ]
        if app:
            sources += [
                ROOT / "tools/native_simulator" / name
                for name in ("scheduler.c", "app_subscriber.c", "logic_subscriber.c")
            ]
            sources += [
                ROOT / "src/kernel/msgbus.c",
                ROOT / "src/services/ui/ui_cmd.c",
                ROOT / "src/services/ui_app/ui_app_logic.c",
            ]
        exe = build / "runtime.exe"
        command = [
            str(compiler_path),
            "-std=gnu11",
            "-O0",
            "-DESPOS_NATIVE=1",
            "-ffunction-sections",
            "-fdata-sections",
            "-Wl,--gc-sections",
            "-I" + str(build),
            "-I" + str(ROOT / "tools/native_simulator"),
            "-I" + str(ROOT / "test/stubs"),
            "-I" + str(ROOT / "src"),
            *map(str, sources),
            "-lm",
            "-o",
            str(exe),
        ]
        if app:
            command.insert(1, "-DSIM_APP=1")
        # Omit the keyword entirely for legacy callers and fake child runners.
        options = {} if cancel_event is None else {"cancel_event": cancel_event}
        _check_cancel(cancel_event)
        child_inflight = True
        compiled = run_child(command, cwd=build, env=env, timeout=60, **options)
        if not (
            isinstance(compiled, ProcessResult)
            and compiled.returncode == 0
            and compiled.owned_scope_empty is True
        ):
            raise SimulatorProcessError(
                "simulator-child-completion-unconfirmed", cleanup_confirmed=None
            )
        child_inflight = False
        _check_cancel(cancel_event)
        status = {"connected": 0, "disconnected": 0x105, "error": -1}[display]
        runtime_command = [str(exe), str(output.resolve()), str(status), *map(str, events)]
        child_inflight = True
        result = run_child(runtime_command, cwd=build, env=env, timeout=10, **options)
        if not (
            isinstance(result, ProcessResult)
            and result.returncode == 0
            and result.owned_scope_empty is True
        ):
            raise SimulatorProcessError(
                "simulator-child-completion-unconfirmed", cleanup_confirmed=None
            )
        child_inflight = False
        _check_cancel(cancel_event)
        phase = "state"
        state = _decode_runtime_state(
            result.stdout, display, expected_final_display=expected_final_display
        )
        _check_cancel(cancel_event)
    except SimulatorProcessError as error:
        # Preserve the producer's exact cancellation code and True/False/None.
        failure = error
    except BaseException as error:
        code = (
            "simulator-child-call-failed"
            if child_inflight
            else {
                "preflight": "simulator-preflight-failed",
                "setup": "simulator-setup-failed",
                "state": "simulator-state-invalid",
            }[phase]
        )
        if (
            cancel_event is None
            and isinstance(error, ValueError)
            and phase in ("preflight", "state")
            and not child_inflight
        ):
            # These existing validation/decoder errors are controlled by this
            # wrapper, outside a live child call. Preserve the public API; the
            # cleanup block below can still downgrade the attached proof.
            error.cleanup_confirmed = not build_creation_pending
            failure = error
        else:
            failure = SimulatorProcessError(
                code, cleanup_confirmed=None if child_inflight or build_creation_pending else True
            )

    if build is not None and (failure is None or failure.cleanup_confirmed is True):
        try:
            if identity is None or parent is None:
                raise RuntimeError("Private build identity was not established")
            _cleanup_private_build(build, parent, identity)
        except BaseException:
            if failure is None:
                failure = SimulatorProcessError("simulator-build-cleanup-failed")
            failure.cleanup_confirmed = None
            failure.cleanup_error = "simulator-build-cleanup-failed"
    if failure is not None:
        if build is not None and failure.cleanup_confirmed is not True:
            failure.retained_build = str(build)
        raise failure from None
    _check_cancel(cancel_event)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Production framebuffer as PGM")
    parser.add_argument(
        "--events",
        default="",
        help=(
            "Comma-separated INPUT_ID 0..255, button:id:press|release, tick:1..1000, "
            "display:connected|disconnected|error "
            "(10 ms/tick, total <=6000 including 5/non-tick step); "
            "--app also permits action:id:value / cmd:kind:id:value (kind 2,3,20)"
        ),
    )
    parser.add_argument(
        "--display",
        choices=["connected", "disconnected", "error"],
        default="connected",
        help="Initial mock display state; display: events can change it during the run",
    )
    parser.add_argument(
        "--app", action="store_true", help="Run production UI, app and visual-logic subscribers"
    )
    args = parser.parse_args()
    try:
        events = parse_cli_events(args.events, args.display, args.app)
        print(json.dumps(run(args.scene, args.output, events, args.display, app=args.app)))
    except SimulatorProcessError as exc:
        # No raw child output or parent credentials reflected into CLI diagnostics.
        parser.exit(1, str(exc) + "\n")
    except (ValueError, RuntimeError, OSError, UnicodeError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
