"""File I/O: save, load, autosave, and export operations."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict
from dataclasses import fields as _dc_fields
from pathlib import Path
from typing import List

from ui_designer import WidgetConfig

from .constants import PREFS_PATH
from .state import EditorState

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "ui_design.schema.json"
_schema_cache: dict | None = None


def _load_schema() -> dict | None:
    """Load and cache the JSON schema (best-effort)."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    try:
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _schema_cache = None  # type: ignore[assignment]
    return _schema_cache


def validate_design(app) -> list[str]:
    """Validate current design against JSON schema. Returns list of error messages."""
    try:
        import jsonschema
    except ImportError:
        return []
    schema = _load_schema()
    if schema is None:
        return []
    try:
        data = json.loads(json.dumps(app.designer.to_dict(), default=str))
        validator = jsonschema.Draft202012Validator(schema)
        return [e.message for e in validator.iter_errors(data)]
    except Exception:
        return []


def load_or_default(app) -> None:
    base_exists = app.json_path.exists()
    autosave_exists = app.autosave_path.exists()
    use_autosave = False

    if autosave_exists and base_exists:
        try:
            base_mtime = app.json_path.stat().st_mtime
            autosave_mtime = app.autosave_path.stat().st_mtime
            if autosave_mtime > base_mtime:
                use_autosave = True
        except OSError:
            logger.debug("Could not compare mtime for autosave detection")

    if use_autosave:
        try:
            app.designer.load_from_json(str(app.autosave_path))
            sc = app.designer.scenes[app.designer.current_scene]
            if sc.width <= 0 or sc.height <= 0:
                sc.width, sc.height = app.default_size
            app._restored_from_autosave = True
            return
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Autosave recovery failed for %s", app.autosave_path, exc_info=True)

    if base_exists:
        app.designer.load_from_json(str(app.json_path))
        return

    app.designer.create_scene("main")
    sc = app.designer.scenes[app.designer.current_scene]
    sc.width, sc.height = app.default_size
    sc.bg_color = "#0a0f14"
    app.designer.width, app.designer.height = sc.width, sc.height


def load_widget_presets(app) -> List[dict]:
    if not app.preset_path.exists():
        return []
    try:
        return json.loads(app.preset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        logger.warning("Failed to load widget presets from %s", app.preset_path, exc_info=True)
        return []


def save_widget_presets(app) -> None:
    try:
        app.preset_path.write_text(json.dumps(app.widget_presets, indent=2), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        logger.warning("Failed to save widget presets to %s", app.preset_path, exc_info=True)


def save_preset_slot(app, slot: int) -> None:
    """Save current selection as a widget preset into a numbered slot."""
    if not app.state.selected:
        return
    sc = app.state.current_scene()
    idx = app.state.selected_idx if app.state.selected_idx is not None else app.state.selected[0]
    if idx is None or not (0 <= idx < len(sc.widgets)):
        return
    w = sc.widgets[idx]
    preset = asdict(w)
    preset.pop("x", None)
    preset.pop("y", None)
    while len(app.widget_presets) < slot:
        app.widget_presets.append({})
    app.widget_presets[slot - 1] = preset
    save_widget_presets(app)
    print(f"[OK] Preset saved to slot {slot}")


def apply_preset_slot(app, slot: int, add_new: bool = False) -> None:
    """Apply or add preset from slot to selection (or as new widget)."""
    if slot < 1 or slot > len(app.widget_presets):
        return
    preset = app.widget_presets[slot - 1] if slot - 1 < len(app.widget_presets) else None
    if not preset:
        return
    sc = app.state.current_scene()
    if add_new:
        try:
            config = dict(preset)
            config["x"] = 10
            config["y"] = 10
            new_w = WidgetConfig(**config)
            sc.widgets.append(new_w)
            app.state.selected = [len(sc.widgets) - 1]
            app.state.selected_idx = app.state.selected[0]
        except (TypeError, ValueError):
            return
    else:
        if not app.state.selected:
            return
        for idx in app.state.selected:
            if not (0 <= idx < len(sc.widgets)):
                continue
            w = sc.widgets[idx]
            _allowed = {f.name for f in _dc_fields(type(w))}
            for key, val in preset.items():
                if key in ("x", "y") or key not in _allowed:
                    continue
                setattr(w, key, val)
    app._mark_dirty()


def load_prefs(app) -> None:
    """Load preferences from file."""
    if PREFS_PATH.exists():
        try:
            app.prefs = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
            fav = app.prefs.get("favorite_ports")
            if isinstance(fav, list):
                app.favorite_ports = [str(p) for p in fav]
        except (OSError, json.JSONDecodeError, ValueError):
            app.prefs = {}
    else:
        app.prefs = {}


def save_prefs(app) -> None:
    """Save preferences to file."""
    try:
        app.prefs["favorite_ports"] = app.favorite_ports
        PREFS_PATH.write_text(json.dumps(app.prefs, indent=2), encoding="utf-8")
    except OSError:
        logger.warning("Failed to save preferences to %s", PREFS_PATH, exc_info=True)


def save_json(app) -> None:
    errors = validate_design(app)
    if errors:
        logger.warning("Design validation warnings: %s", errors[:5])
    import tempfile

    target = str(app.json_path)
    dir_name = str(Path(target).parent)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_name)
        os.close(fd)
        app.designer.save_to_json(tmp_path)
        os.replace(tmp_path, target)
        tmp_path = None  # replaced successfully, no cleanup needed
    except OSError:  # pragma: no cover
        logger.warning("Atomic save failed, falling back to direct write", exc_info=True)
        # Fallback: direct save
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        app.designer.save_to_json(target)
    write_audit_report(app)
    app._dirty = False
    app._dirty_scenes = set()


def load_json(app) -> None:
    if not app.json_path.exists():
        return
    app.designer.load_from_json(str(app.json_path))
    app.designer.set_responsive_base()
    win_size = app.window.get_size() if app.window else None
    app._rebuild_layout(window_size=win_size, force_scene_size=False, lock_scale=None)
    app.state = EditorState(app.designer, app.layout)
    app._dirty = False
    app._dirty_scenes = set()
    # Drain stale events so they don't apply to the freshly loaded scene
    try:
        import pygame

        pygame.event.clear()
    except (ImportError, RuntimeError):
        pass


def write_audit_report(app) -> None:
    """Write audit report."""
    try:
        sc = app.state.current_scene()
        report_dir = Path("reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "last_audit.txt"
        lines = [f"file: {app.json_path}", f"scene: {sc.name}", f"widgets: {len(sc.widgets)}"]
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except (OSError, RuntimeError, KeyError, AttributeError):
        logger.debug("Could not write audit report")


def maybe_autosave(app) -> None:
    """Auto-save if dirty and enabled."""
    if not app.autosave_enabled or not app._dirty:
        return
    now = time.time()
    if now - app._last_autosave_ts < app.autosave_interval:
        return
    try:
        app.designer.save_to_json(str(app.autosave_path))
        app._last_autosave_ts = now
        app._dirty = False
        app._dirty_scenes = set()
    except OSError:
        logger.warning("Autosave failed for %s", app.autosave_path, exc_info=True)
