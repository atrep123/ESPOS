"""Editor-owned one-shot runtime previews; no process/build wrapper or GUI imports.

Only the existing simulator run owns children. A stopped generation cannot deliver
frames; uncertain cleanup retains ownership and the private snapshot for review.
"""

from __future__ import annotations

import copy
import json
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.simulator_contract import validate_inputs
from tools.simulator_process import SimulatorProcessError

SNAPSHOT_LIMIT = 1024 * 1024
FRAME_WIDTH = 256
FRAME_HEIGHT = 128
PGM_HEADER = b"P5\n256 128\n255\n"


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    pixels: bytes


def read_frame(path: Path) -> Frame:
    """Decode exactly the bounded gray8 PGM shape documented by runner tests."""
    size = len(PGM_HEADER) + FRAME_WIDTH * FRAME_HEIGHT
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    if len(data) != size or not data.startswith(PGM_HEADER):
        raise ValueError("runtime-preview-invalid-pgm")
    return Frame(FRAME_WIDTH, FRAME_HEIGHT, data[len(PGM_HEADER) :])


def detached_document(designer) -> dict:
    """Snapshot live dataclasses and opaque metadata without save/preflight/export.

    The selected scene is first for the existing multi-scene code generator;
    other scenes remain available. No authored object is changed or saved.
    """
    current = designer.current_scene
    if current not in designer.scenes:
        raise ValueError("runtime-preview-no-scene")
    selected = designer.scenes[current]
    if (selected.width, selected.height) != (FRAME_WIDTH, FRAME_HEIGHT):
        raise ValueError("runtime-preview-requires-256x128")
    metadata = getattr(designer, "_scene_metadata", {})
    scenes = {}
    for name in (current, *(key for key in designer.scenes if key != current)):
        scene = copy.deepcopy(metadata.get(name, {}))
        scene.update(asdict(designer.scenes[name]))
        scenes[name] = scene
    document = copy.deepcopy(getattr(designer, "_document_metadata", {}))
    document.update(width=designer.width, height=designer.height, scenes=scenes)
    # Preserve the source container representation, including scene IDs.
    if getattr(designer, "_scenes_as_list", False):
        document["scenes"] = list(scenes.values())
    return document


def _run_existing(*args, **kwargs):
    from tools.espos_runtime_simulator import run

    return run(*args, **kwargs)


@dataclass
class _Work:
    generation: int
    cancel: threading.Event = field(default_factory=threading.Event)
    thread: object = None
    workspace: Path | None = None
    cleanup_confirmed: bool | None = None
    frame: Frame | None = None
    state: dict | None = None
    error: str | None = None
    retained_build: str | None = None
    observed: bool = False


def _execute(work, runner, payload, events, display, app_mode, workspace_parent):
    called = False
    try:
        if work.cancel.is_set():
            raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)
        work.workspace = Path(
            tempfile.mkdtemp(prefix="espos-runtime-preview-", dir=workspace_parent)
        ).resolve(strict=True)
        info = work.workspace.lstat()
        identity = (info.st_dev, info.st_ino)
        scene = work.workspace / "scene.json"
        if work.cancel.is_set():
            raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)
        scene.write_text(payload, encoding="utf-8")
        output = work.workspace / "frame.pgm"
        called = True
        state = runner(scene, output, events, display, app=app_mode, cancel_event=work.cancel)
        # Successful run returns only after its owned children/readers are gone.
        work.cleanup_confirmed = True
        if work.cancel.is_set():
            raise SimulatorProcessError("simulator-cancelled", cleanup_confirmed=True)
        work.frame = read_frame(output)
        work.state = copy.deepcopy(state)
    except SimulatorProcessError as error:
        work.cleanup_confirmed = error.cleanup_confirmed
        work.error = str(error)
        work.retained_build = getattr(error, "retained_build", None)
    except Exception:
        # No raw exception/child output in editor messages. An unknown exception
        # from an invoked runner does not certify that its children were cleaned.
        work.error = "runtime-preview-failed"
        if not called:
            work.cleanup_confirmed = True
    finally:
        if work.cleanup_confirmed is True and work.workspace is not None:
            try:
                from tools.espos_runtime_simulator import _cleanup_private_build

                _cleanup_private_build(work.workspace, work.workspace.parent, identity)
            except Exception:
                work.cleanup_confirmed = None
                work.error = "runtime-preview-snapshot-cleanup-uncertain"


class RuntimePreview:
    """One background owner; poll performs at most one zero-time join/delivery."""

    def __init__(
        self,
        *,
        on_frame,
        on_status,
        runner=_run_existing,
        thread_factory=threading.Thread,
        workspace_parent=None,
    ):
        self._on_frame = on_frame
        self._on_status = on_status
        self._runner = runner
        self._thread_factory = thread_factory
        self._workspace_parent = workspace_parent
        self._work = None
        self._generation = 0
        self._document_key = None
        self.frame = None
        self.state = None
        self.status = "idle"

    @property
    def owns_work(self):
        return self._work is not None

    @property
    def retained_paths(self):
        work = self._work
        return (
            ()
            if work is None
            else tuple(path for path in (work.workspace, work.retained_build) if path is not None)
        )

    def _status(self, status):
        if self.status != status:
            self.status = status
            self._on_status(status)

    def _clear_frame(self):
        if self.frame is not None or self.state is not None:
            self.frame = self.state = None
            self._on_frame(None, None)

    def sync_document(self, key):
        if key != self._document_key:
            self.stop()
            self._document_key = key

    def start(self, document, key, events=(), display="connected", *, app=False):
        self.sync_document(key)
        if self.owns_work:
            return False
        events = validate_inputs(events, display, app)
        payload = json.dumps(document, allow_nan=False)
        if type(document) is not dict or len(payload.encode("utf-8")) > SNAPSHOT_LIMIT:
            raise ValueError("runtime-preview-snapshot-invalid")
        if not document.get("scenes"):
            raise ValueError("runtime-preview-no-scene")
        self._generation += 1
        self._clear_frame()
        work = _Work(self._generation)
        work.thread = self._thread_factory(
            target=_execute,
            args=(work, self._runner, payload, events, display, app, self._workspace_parent),
            name="espos-runtime-preview",
            daemon=False,
        )
        self._work = work
        try:
            work.thread.start()
        except Exception:
            work.cancel.set()
            if work.thread.is_alive():
                self._status("stopping")
            else:
                self._work = None
                self._status("runtime-preview-start-failed")
            return False
        self._status("running")
        return True

    def stop(self):
        work = self._work
        if work is not None and not work.cancel.is_set():
            self._generation += 1
            work.cancel.set()
            if not work.observed:
                self._status("stopping")
        elif self.frame is not None or self.state is not None:
            self._generation += 1
            self._status("stopped")
        self._clear_frame()

    def poll(self, key):
        self.sync_document(key)
        work = self._work
        if work is None or work.observed or work.thread.is_alive():
            return
        work.thread.join(timeout=0)
        if work.thread.is_alive():
            return
        work.observed = True
        if work.cleanup_confirmed is not True:
            self._status("cleanup-uncertain: ownership retained; exit and restart blocked")
            return
        self._work = None
        if work.generation != self._generation or work.cancel.is_set():
            self._status("stopped")
            return
        if work.error is not None:
            self._status(work.error)
            return
        self.frame, self.state = work.frame, work.state
        self._on_frame(self.frame, copy.deepcopy(self.state))
        if work.generation == self._generation:
            self._status("completed (mock display)")
