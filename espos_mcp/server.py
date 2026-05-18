"""FastMCP server: real espos tools over stdio.

Design rules honored here:

* **No business logic in the server.** Each tool validates its inputs at the
  boundary and then calls a real espos library function. The heavy lifting
  (codegen, validation, pio, snapping, schema enforcement) lives in the
  existing modules and is *reused*, never reimplemented.
* **Real functional depth.** Every tool operates end-to-end on a real design
  JSON file using the same load / atomic-save paths the pygame designer uses
  (``UIDesigner.load_from_json`` / ``save_to_json`` written through a
  ``tempfile`` + ``os.replace`` like ``cyberpunk_designer.io_ops.save_json``).
* **Structured errors.** Invalid input or a real library failure raises
  ``ToolError`` with an actionable message instead of returning a fake success.

Widget identity: tools accept a 0-based ``index`` (the designer's native
addressing) and, where useful, an optional ``widget_id`` that matches the
widget's ``id`` / ``_widget_id`` field. Designs are addressed by a JSON path
argument, defaulting to ``main_scene.json`` at the repo root.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Make the espos repo root importable (mirrors tools/build.py) ---------- #
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as exc:  # pragma: no cover - exercised via __main__
    raise ModuleNotFoundError(
        "The 'mcp' Python SDK is required to run the espos MCP server but is "
        "not importable. It is a managed dependency of this server — install "
        "it with:\n"
        f'    "{sys.executable}" -m pip install -r '
        f"{REPO_ROOT / 'requirements-mcp.txt'}\n"
        "or, minimally:\n"
        f'    "{sys.executable}" -m pip install "mcp>=1.2,<2"'
    ) from exc

# Real espos library surfaces (imported once; thin wrappers below).
from board_registry import load_registry
from tools.build import (
    BuildError,
    BuildResult,
    build_board,
    flash_board,
    platformio_version,
    resolve_env,
)
from tools.ui_export_c_header import export_header
from tools.ui_export_svg import export_svg
from tools.validate_design import validate_file
from ui_designer import UIDesigner

DEFAULT_DESIGN = "main_scene.json"


# --------------------------------------------------------------------------- #
# Boundary helpers (path safety, design load/save) — NOT business logic
# --------------------------------------------------------------------------- #


class ToolError(RuntimeError):
    """Actionable, user-facing failure surfaced to the MCP client."""


def _resolve_design_path(design_path: Optional[str], *, must_exist: bool) -> Path:
    """Resolve a design JSON path argument safely.

    Relative paths are taken relative to the espos repo root. The resolved
    path is confined to the repo (no escaping via ``..`` / absolute paths
    outside the tree) — the server only ever exposes espos.
    """
    raw = (design_path or DEFAULT_DESIGN).strip()
    if not raw:
        raise ToolError("design_path must not be empty.")
    p = Path(raw)
    if not p.is_absolute():
        p = REPO_ROOT / p
    try:
        resolved = p.resolve()
    except OSError as exc:
        raise ToolError(f"invalid design_path {raw!r}: {exc}") from exc
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ToolError(
            f"design_path must stay inside the espos repo ({REPO_ROOT}); "
            f"got {resolved}"
        ) from exc
    if must_exist and not resolved.exists():
        raise ToolError(f"design JSON not found: {resolved}")
    return resolved


def _load_designer(path: Path) -> UIDesigner:
    """Load a design via the real ``UIDesigner`` model."""
    d = UIDesigner()
    d.load_from_json(str(path))
    if not d.scenes:
        raise ToolError(
            f"{path.name}: no scenes loaded (invalid or empty design)."
        )
    return d


def _atomic_save(designer: UIDesigner, path: Path) -> None:
    """Persist via ``UIDesigner.save_to_json`` through a temp file +
    ``os.replace`` — the exact atomic pattern ``io_ops.save_json`` uses.
    """
    dir_name = str(path.parent)
    tmp_path: Optional[str] = None
    # The designer's save_to_json triggers an auto preflight/export by
    # default; the dedicated `build`/`export_*` tools own that explicitly, so
    # keep a pure data write here and restore the env afterward.
    prev = os.environ.get("ESP32OS_AUTO_EXPORT")
    os.environ["ESP32OS_AUTO_EXPORT"] = "0"
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_name)
        os.close(fd)
        designer.save_to_json(tmp_path)
        os.replace(tmp_path, str(path))
        tmp_path = None
    except OSError as exc:
        raise ToolError(f"failed to save {path.name}: {exc}") from exc
    finally:
        if prev is None:
            os.environ.pop("ESP32OS_AUTO_EXPORT", None)
        else:
            os.environ["ESP32OS_AUTO_EXPORT"] = prev
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _design_dict(path: Path) -> Dict[str, Any]:
    """Raw design JSON (for logic/event edits that round-trip as-is)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolError(f"failed to read {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ToolError(f"{path.name}: root must be a JSON object.")
    return data


def _schema_check(data: Dict[str, Any], path: Path) -> None:
    """Reject a mutation that would break the schema, using the *real*
    validator. Run BEFORE writing so a bad edit never lands on disk.
    """
    tmp_path: Optional[str] = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        issues = validate_file(
            Path(tmp_path), warnings_as_errors=False, strict_critical=False
        )
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    errors = [i.message for i in issues if i.level == "ERROR"]
    if errors:
        raise ToolError(
            "edit rejected: it would make the design invalid:\n- "
            + "\n- ".join(errors[:8])
        )


def _write_dict(data: Dict[str, Any], path: Path) -> None:
    """Atomic write of a raw design dict (temp file + os.replace)."""
    dir_name = str(path.parent)
    tmp_path: Optional[str] = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_name)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_path, str(path))
        tmp_path = None
    except OSError as exc:
        raise ToolError(f"failed to save {path.name}: {exc}") from exc
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _scenes_of(data: Dict[str, Any]) -> Dict[str, Any]:
    sc = data.get("scenes")
    if not isinstance(sc, dict) or not sc:
        raise ToolError("design has no 'scenes' object.")
    return sc


def _scene_or_first(data: Dict[str, Any], scene: Optional[str]) -> str:
    scenes = _scenes_of(data)
    if scene:
        if scene not in scenes:
            raise ToolError(
                f"scene {scene!r} not found. Available: "
                f"{', '.join(sorted(scenes))}"
            )
        return scene
    return next(iter(scenes))


def _widget_index(
    widgets: List[Dict[str, Any]],
    index: Optional[int],
    widget_id: Optional[str],
) -> int:
    """Resolve a widget reference (index or id) to a list index."""
    if widget_id:
        for i, w in enumerate(widgets):
            if str(w.get("id") or w.get("_widget_id") or "") == widget_id:
                return i
        raise ToolError(f"no widget with id {widget_id!r} in scene.")
    if index is None:
        raise ToolError("provide either 'index' or 'widget_id'.")
    if not (0 <= index < len(widgets)):
        raise ToolError(
            f"widget index {index} out of range (scene has {len(widgets)})."
        )
    return index


def _result(**kw: Any) -> Dict[str, Any]:
    """Uniform success envelope."""
    out: Dict[str, Any] = {"ok": True}
    out.update(kw)
    return out


def _build_result_dict(r: BuildResult) -> Dict[str, Any]:
    return {
        "env": r.env,
        "action": r.action,
        "ok": r.ok,
        "returncode": r.returncode,
        "firmware_path": str(r.firmware_path) if r.firmware_path else None,
        "ram_used": r.ram_used,
        "flash_used": r.flash_used,
        "hardware_unverified": r.hardware_unverified,
        "summary": r.summary(),
        "output_tail": list(r.output_tail),
    }


# --------------------------------------------------------------------------- #
# Server + tool registration
# --------------------------------------------------------------------------- #


def build_server() -> FastMCP:
    """Construct and return the configured espos :class:`FastMCP` server.

    All tools are registered here. Kept as a factory so importing the package
    is cheap and the server can be introspected/tested in-process.
    """
    mcp = FastMCP(
        "espos",
        instructions=(
            "ESP32OS UI Toolkit. Design embedded UI scenes (256x128 gray4 and "
            "other registered boards), attach a real event/rule logic model, "
            "validate against the strict schema, export pixel-faithful SVG or "
            "an embedded C header, and build/flash genuine firmware with the "
            "bundled PlatformIO toolchain. Designs are JSON files in the espos "
            "repo; the default is main_scene.json. Each tool wraps a real "
            "espos library function — no operation is simulated."
        ),
    )

    # ---- scenes -------------------------------------------------------- #

    @mcp.tool()
    def list_scenes(design_path: str = DEFAULT_DESIGN) -> Dict[str, Any]:
        """List the scenes in a design (name, size, widget/rule counts).

        Wraps ``ui_designer.UIDesigner.load_from_json``.
        """
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        scenes = []
        for name, sc in d.scenes.items():
            scenes.append(
                {
                    "name": name,
                    "width": sc.width,
                    "height": sc.height,
                    "bg_color": sc.bg_color,
                    "widget_count": len(sc.widgets),
                    "rule_count": len(getattr(sc, "rules", []) or []),
                }
            )
        return _result(
            design=str(path),
            width=d.width,
            height=d.height,
            scene_count=len(scenes),
            scenes=scenes,
        )

    @mcp.tool()
    def get_scene(
        scene: Optional[str] = None, design_path: str = DEFAULT_DESIGN
    ) -> Dict[str, Any]:
        """Return one scene fully: every widget (with its index + fields) and
        the scene's logic rules.

        Wraps ``ui_designer.UIDesigner.load_from_json``. If ``scene`` is
        omitted the first scene is returned.
        """
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        name = scene or next(iter(d.scenes))
        if name not in d.scenes:
            raise ToolError(
                f"scene {name!r} not found. Available: "
                f"{', '.join(sorted(d.scenes))}"
            )
        sc = d.scenes[name]
        widgets = []
        for i, w in enumerate(sc.widgets):
            wd = asdict(w)
            widgets.append(
                {
                    "index": i,
                    "id": wd.get("_widget_id"),
                    "type": wd.get("type"),
                    "x": wd.get("x"),
                    "y": wd.get("y"),
                    "width": wd.get("width"),
                    "height": wd.get("height"),
                    "text": wd.get("text"),
                    "events": wd.get("events") or {},
                    "fields": wd,
                }
            )
        return _result(
            design=str(path),
            scene=name,
            width=sc.width,
            height=sc.height,
            bg_color=sc.bg_color,
            widgets=widgets,
            rules=[dict(r) for r in (getattr(sc, "rules", []) or [])],
        )

    @mcp.tool()
    def add_scene(
        name: str, design_path: str = DEFAULT_DESIGN
    ) -> Dict[str, Any]:
        """Create a new (empty) scene and save the design.

        Wraps ``ui_designer.UIDesigner.create_scene`` + atomic save.
        """
        if not name or not name.strip():
            raise ToolError("scene name must not be empty.")
        name = name.strip()
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        if name in d.scenes:
            raise ToolError(f"scene {name!r} already exists.")
        d.create_scene(name)
        _atomic_save(d, path)
        return _result(
            design=str(path), scene=name, scene_count=len(d.scenes)
        )

    @mcp.tool()
    def delete_scene(
        name: str, design_path: str = DEFAULT_DESIGN
    ) -> Dict[str, Any]:
        """Delete a scene and save the design (the design must keep >=1 scene).

        Operates on the real ``UIDesigner`` model + atomic save.
        """
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        if name not in d.scenes:
            raise ToolError(
                f"scene {name!r} not found. Available: "
                f"{', '.join(sorted(d.scenes))}"
            )
        if len(d.scenes) <= 1:
            raise ToolError("cannot delete the only scene in the design.")
        del d.scenes[name]
        if d.current_scene == name:
            d.current_scene = next(iter(d.scenes))
        _atomic_save(d, path)
        return _result(
            design=str(path),
            deleted=name,
            scene_count=len(d.scenes),
        )

    # ---- widgets ------------------------------------------------------- #

    @mcp.tool()
    def add_widget(
        widget_type: str,
        x: int,
        y: int,
        width: int,
        height: int,
        scene: Optional[str] = None,
        text: str = "",
        widget_id: Optional[str] = None,
        z_index: int = 0,
        design_path: str = DEFAULT_DESIGN,
    ) -> Dict[str, Any]:
        """Add a widget to a scene and save.

        Wraps ``ui_designer.UIDesigner.add_widget`` (which applies the real
        grid + magnetic snapping). Returns the new widget's index. Common
        widget types: label, box, button, gauge, progressbar, checkbox,
        slider, icon, chart, list, toggle, radiobutton.
        """
        for fld, val in (("width", width), ("height", height)):
            if val <= 0:
                raise ToolError(f"{fld} must be a positive integer.")
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        name = scene or d.current_scene or next(iter(d.scenes))
        if name not in d.scenes:
            raise ToolError(
                f"scene {name!r} not found. Available: "
                f"{', '.join(sorted(d.scenes))}"
            )
        kwargs: Dict[str, Any] = {
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "text": text or "",
            "z_index": int(z_index),
        }
        try:
            d.add_widget(str(widget_type), scene_name=name, **kwargs)
        except (TypeError, ValueError) as exc:
            raise ToolError(f"could not add widget: {exc}") from exc
        new_index = len(d.scenes[name].widgets) - 1
        if widget_id:
            d.scenes[name].widgets[new_index]._widget_id = str(widget_id)
        _atomic_save(d, path)
        w = asdict(d.scenes[name].widgets[new_index])
        return _result(
            design=str(path),
            scene=name,
            index=new_index,
            widget={
                "type": w.get("type"),
                "x": w.get("x"),
                "y": w.get("y"),
                "width": w.get("width"),
                "height": w.get("height"),
                "id": w.get("_widget_id"),
            },
        )

    @mcp.tool()
    def set_widget(
        properties: Dict[str, Any],
        index: Optional[int] = None,
        widget_id: Optional[str] = None,
        scene: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
    ) -> Dict[str, Any]:
        """Update fields of an existing widget and save.

        Addressed by 0-based ``index`` or by ``widget_id``. ``properties`` is
        a flat map of widget fields (e.g. ``{"text": "Hi", "x": 10,
        "value": 50, "visible": false}``). The edit is schema-validated with
        the **real** validator before it is written; an edit that would break
        the design is rejected and nothing is saved.
        """
        if not isinstance(properties, dict) or not properties:
            raise ToolError("'properties' must be a non-empty object.")
        path = _resolve_design_path(design_path, must_exist=True)
        data = _design_dict(path)
        name = _scene_or_first(data, scene)
        widgets = data["scenes"][name].setdefault("widgets", [])
        idx = _widget_index(widgets, index, widget_id)
        # Guard widget-identity keys; use add/delete for structural changes.
        protected = {"events"}
        applied = {}
        for key, value in properties.items():
            if key in protected:
                raise ToolError(
                    f"'{key}' is managed via set_widget_event, not set_widget."
                )
            widgets[idx][key] = value
            applied[key] = value
        _schema_check(data, path)
        _write_dict(data, path)
        return _result(
            design=str(path), scene=name, index=idx, applied=applied
        )

    @mcp.tool()
    def delete_widget(
        index: Optional[int] = None,
        widget_id: Optional[str] = None,
        scene: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
    ) -> Dict[str, Any]:
        """Delete a widget (by ``index`` or ``widget_id``) and save.

        Wraps ``ui_designer.UIDesigner.delete_widget`` (which also re-indexes
        groups/selection) + atomic save.
        """
        path = _resolve_design_path(design_path, must_exist=True)
        d = _load_designer(path)
        name = scene or d.current_scene or next(iter(d.scenes))
        if name not in d.scenes:
            raise ToolError(
                f"scene {name!r} not found. Available: "
                f"{', '.join(sorted(d.scenes))}"
            )
        sc = d.scenes[name]
        wdicts = [asdict(w) for w in sc.widgets]
        idx = _widget_index(wdicts, index, widget_id)
        if getattr(sc.widgets[idx], "locked", False):
            raise ToolError(f"widget {idx} is locked; unlock it first.")
        d.delete_widget(idx, scene_name=name)
        _atomic_save(d, path)
        return _result(
            design=str(path),
            scene=name,
            deleted_index=idx,
            widget_count=len(d.scenes[name].widgets),
        )

    # ---- logic model (#36): events + rules ----------------------------- #

    @mcp.tool()
    def set_widget_event(
        handler: str,
        actions: List[Dict[str, Any]],
        index: Optional[int] = None,
        widget_id: Optional[str] = None,
        scene: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
    ) -> Dict[str, Any]:
        """Set a widget's event handler (the #36 visual-backend logic model).

        ``handler`` is one of ``on_press`` / ``on_change`` / ``on_focus``.
        ``actions`` is the ordered action list (e.g.
        ``[{"type": "set_scene", "scene": "menu"}]``). The change is
        schema-validated with the real validator before writing; an invalid
        action list is rejected. Pass an empty list to clear the handler.
        """
        valid = {"on_press", "on_change", "on_focus"}
        if handler not in valid:
            raise ToolError(
                f"handler must be one of {sorted(valid)}; got {handler!r}."
            )
        if not isinstance(actions, list) or not all(
            isinstance(a, dict) for a in actions
        ):
            raise ToolError("'actions' must be a list of action objects.")
        path = _resolve_design_path(design_path, must_exist=True)
        data = _design_dict(path)
        name = _scene_or_first(data, scene)
        widgets = data["scenes"][name].setdefault("widgets", [])
        idx = _widget_index(widgets, index, widget_id)
        w = widgets[idx]
        # The widget must carry an id for its events to be wired by codegen.
        if not (w.get("id") or w.get("_widget_id")):
            raise ToolError(
                "widget needs an 'id' before events can be wired "
                "(set one via set_widget {\"id\": \"...\"})."
            )
        ev = w.get("events")
        if not isinstance(ev, dict):
            ev = {}
        if actions:
            ev[handler] = actions
        else:
            ev.pop(handler, None)
        w["events"] = ev
        _schema_check(data, path)
        _write_dict(data, path)
        return _result(
            design=str(path),
            scene=name,
            index=idx,
            handler=handler,
            action_count=len(actions),
        )

    @mcp.tool()
    def add_rule(
        trigger: Dict[str, Any],
        actions: List[Dict[str, Any]],
        conditions: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None,
        scene: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
    ) -> Dict[str, Any]:
        """Append a scene rule (trigger -> optional conditions -> actions).

        The #36 logic model. Example::

            trigger = {"type": "boot"}
            actions = [{"type": "toast", "text": "ready"}]

        Schema-validated with the real validator before writing; an invalid
        rule is rejected and nothing is saved. Returns the new rule index.
        """
        if not isinstance(trigger, dict) or "type" not in trigger:
            raise ToolError("'trigger' must be an object with a 'type'.")
        if not isinstance(actions, list) or not actions:
            raise ToolError("'actions' must be a non-empty list.")
        path = _resolve_design_path(design_path, must_exist=True)
        data = _design_dict(path)
        sname = _scene_or_first(data, scene)
        scene_obj = data["scenes"][sname]
        rules = scene_obj.get("rules")
        if not isinstance(rules, list):
            rules = []
        rule: Dict[str, Any] = {"trigger": trigger, "actions": actions}
        if conditions:
            if not isinstance(conditions, list):
                raise ToolError("'conditions' must be a list when provided.")
            rule["conditions"] = conditions
        if name:
            rule["name"] = str(name)
        rules.append(rule)
        scene_obj["rules"] = rules
        _schema_check(data, path)
        _write_dict(data, path)
        return _result(
            design=str(path),
            scene=sname,
            rule_index=len(rules) - 1,
            rule_count=len(rules),
        )

    # ---- boards -------------------------------------------------------- #

    @mcp.tool()
    def list_boards() -> Dict[str, Any]:
        """List every board/module in the registry with its pio env.

        Wraps ``board_registry.load_registry`` (the language-agnostic
        ``boards.json`` source of truth).
        """
        try:
            reg = load_registry()
        except Exception as exc:  # RegistryError or import guard
            raise ToolError(f"could not load board registry: {exc}") from exc
        boards = []
        for b in reg.boards:
            boards.append(
                {
                    "id": b.id,
                    "label": b.label,
                    "env": b.env_name(),
                    "platformio_board": b.platformio_board,
                    "mcu": b.mcu,
                    "vendor": b.vendor,
                    "has_display": b.has_display,
                    "display_profile": b.display_profile,
                    "display": (
                        {
                            "w": b.display.w,
                            "h": b.display.h,
                            "depth": b.display.depth,
                            "driver": b.display.driver,
                        }
                        if b.display
                        else None
                    ),
                    "peripherals": list(b.peripherals),
                }
            )
        return _result(board_count=len(boards), boards=boards)

    @mcp.tool()
    def set_board(
        board: str, design_path: str = DEFAULT_DESIGN
    ) -> Dict[str, Any]:
        """Record the target board on the design's root ``runtime`` metadata
        and resize display-bearing scenes to the board's panel.

        Uses ``board_registry.load_registry`` (validity + display profile) and
        ``ui_designer.HARDWARE_PROFILES`` for geometry; saved atomically.
        Headless modules are recorded without touching scene geometry (the UI
        designer does not apply to a screenless board — honest, not faked).
        """
        if not board or not board.strip():
            raise ToolError("board must not be empty.")
        board = board.strip()
        path = _resolve_design_path(design_path, must_exist=True)
        try:
            reg = load_registry()
        except Exception as exc:
            raise ToolError(f"could not load board registry: {exc}") from exc
        b = reg.get(board)
        if b is None:
            raise ToolError(
                f"unknown board {board!r}. Valid: {', '.join(reg.ids())}"
            )
        data = _design_dict(path)
        # Persist the board selection in a way that round-trips and that the
        # validator's board-peripheral gating (Rule 130) reads.
        data["board"] = b.id
        resized: List[str] = []
        if b.has_display and b.display is not None:
            from ui_designer import HARDWARE_PROFILES

            prof = HARDWARE_PROFILES.get(b.display_profile or "")
            if prof:
                data["width"] = int(prof["width"])
                data["height"] = int(prof["height"])
                for sname, sc in _scenes_of(data).items():
                    if isinstance(sc, dict):
                        sc["width"] = int(prof["width"])
                        sc["height"] = int(prof["height"])
                        resized.append(sname)
        _schema_check(data, path)
        _write_dict(data, path)
        return _result(
            design=str(path),
            board=b.id,
            env=b.env_name(),
            has_display=b.has_display,
            resized_scenes=resized,
        )

    # ---- validate / export -------------------------------------------- #

    @mcp.tool()
    def validate_design(
        design_path: str = DEFAULT_DESIGN,
        warnings_as_errors: bool = False,
        strict_critical: bool = False,
    ) -> Dict[str, Any]:
        """Run the real espos validator on a design.

        Wraps ``tools.validate_design.validate_file`` — the same mandatory
        JSON-Schema + semantic + logic + board-peripheral gate that guards
        codegen / demo generation / PlatformIO builds. Returns the structured
        issue list and whether the design passes.
        """
        path = _resolve_design_path(design_path, must_exist=True)
        issues = validate_file(
            path,
            warnings_as_errors=bool(warnings_as_errors),
            strict_critical=bool(strict_critical),
        )
        items = [{"level": i.level, "message": i.message} for i in issues]
        errors = [i for i in items if i["level"] == "ERROR"]
        warns = [i for i in items if i["level"] == "WARN"]
        return _result(
            design=str(path),
            passed=not errors,
            error_count=len(errors),
            warning_count=len(warns),
            issues=items,
        )

    @mcp.tool()
    def export_c(
        design_path: str = DEFAULT_DESIGN,
        output_path: str = "output/ui.h",
    ) -> Dict[str, Any]:
        """Export the design to an embedded C header (ui_scene.h schema).

        Wraps ``tools.ui_export_c_header.export_header`` (the real
        ``tools.ui_codegen`` path). Returns the written header path + size.
        """
        src = _resolve_design_path(design_path, must_exist=True)
        out = _resolve_design_path(output_path, must_exist=False)
        try:
            export_header(src, out)
        except (OSError, ValueError, RuntimeError) as exc:
            raise ToolError(f"C export failed: {exc}") from exc
        if not out.exists():
            raise ToolError("C export reported success but no file was written.")
        return _result(
            design=str(src),
            output=str(out),
            bytes=out.stat().st_size,
        )

    @mcp.tool()
    def export_svg_scene(
        design_path: str = DEFAULT_DESIGN,
        scene: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export a scene to a pixel-faithful, gray4-quantized SVG.

        Wraps ``tools.ui_export_svg.export_svg`` (renders through the real
        designer renderer, so it is pixel-exact to the firmware). Returns the
        written SVG path and its dimensions.
        """
        src = _resolve_design_path(design_path, must_exist=True)
        if output_path:
            out = _resolve_design_path(output_path, must_exist=False)
        else:
            out = src.with_suffix(".svg")
        try:
            width, height, resolved = export_svg(
                src, out, scene_name=scene or None
            )
        except (OSError, ValueError, RuntimeError, SystemExit) as exc:
            raise ToolError(f"SVG export failed: {exc}") from exc
        return _result(
            design=str(src),
            output=str(out),
            scene=resolved,
            width=width,
            height=height,
        )

    # ---- build / flash (real PlatformIO) ------------------------------- #

    @mcp.tool()
    def toolchain_status() -> Dict[str, Any]:
        """Report whether the bundled PlatformIO toolchain is available.

        Wraps ``tools.build.platformio_version``. Use this before ``build`` /
        ``flash`` to confirm the real compiler is installed.
        """
        ver = platformio_version()
        return _result(
            platformio_available=ver is not None,
            platformio_version=ver,
        )

    @mcp.tool()
    def build(
        board: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
        regen: bool = True,
        timeout: int = 1800,
    ) -> Dict[str, Any]:
        """Compile real firmware with the bundled PlatformIO toolchain.

        Wraps ``tools.build.build_board`` -> a genuine ``pio run`` (no fake
        progress). ``board`` is an espos board id or a pio env; ``None`` uses
        the hardware-less reference env. Returns the real firmware path and
        RAM/Flash usage scraped from pio's own report. This is a slow,
        heavyweight operation.
        """
        src = _resolve_design_path(design_path, must_exist=True)
        try:
            env = resolve_env(board)
        except BuildError as exc:
            raise ToolError(str(exc)) from exc
        lines: List[str] = []
        try:
            res = build_board(
                board,
                regen=bool(regen),
                json_path=src,
                sink=lines.append,
                timeout=int(timeout),
            )
        except BuildError as exc:
            raise ToolError(f"build setup failed: {exc}") from exc
        out = _build_result_dict(res)
        out["resolved_env"] = env
        return _result(**out)

    @mcp.tool()
    def flash(
        board: Optional[str] = None,
        port: Optional[str] = None,
        design_path: str = DEFAULT_DESIGN,
        regen: bool = True,
        timeout: int = 1800,
    ) -> Dict[str, Any]:
        """Build then upload firmware to a connected board.

        Wraps ``tools.build.flash_board`` -> a real ``pio run -t upload``.
        HONESTY: with no ESP32 attached this cannot be hardware-confirmed; the
        upload command is genuinely constructed and launched and the result
        carries the honest ``hardware_unverified`` flag rather than pretending
        success. This is a slow, heavyweight operation.
        """
        src = _resolve_design_path(design_path, must_exist=True)
        try:
            env = resolve_env(board)
        except BuildError as exc:
            raise ToolError(str(exc)) from exc
        lines: List[str] = []
        try:
            res = flash_board(
                board,
                port=port or None,
                regen=bool(regen),
                json_path=src,
                sink=lines.append,
                timeout=int(timeout),
            )
        except BuildError as exc:
            raise ToolError(f"flash setup failed: {exc}") from exc
        out = _build_result_dict(res)
        out["resolved_build_env"] = env
        return _result(**out)

    return mcp
