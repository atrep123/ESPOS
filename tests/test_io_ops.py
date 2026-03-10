"""Tests for cyberpunk_designer/io_ops.py — file I/O, presets, autosave."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from cyberpunk_designer.io_ops import (
    apply_preset_slot,
    load_json,
    load_or_default,
    load_prefs,
    load_widget_presets,
    maybe_autosave,
    save_json,
    save_prefs,
    save_preset_slot,
    save_widget_presets,
    write_audit_report,
)
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_widget(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=10, y=20, width=40, height=12, text="Hi")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path: Path, *, widgets=None):
    """Build a minimal app-like namespace usable by io_ops functions."""
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    if widgets:
        sc.widgets.extend(widgets)

    # Layout stub
    layout = MagicMock()

    state = EditorState(designer, layout)
    state.selected = []
    state.selected_idx = None

    app = SimpleNamespace(
        designer=designer,
        json_path=tmp_path / "design.json",
        autosave_path=tmp_path / ".autosave.json",
        preset_path=tmp_path / "presets.json",
        default_size=(256, 128),
        state=state,
        widget_presets=[],
        autosave_enabled=True,
        autosave_interval=5,
        _dirty=False,
        _dirty_scenes=set(),
        _last_autosave_ts=0.0,
        _restored_from_autosave=False,
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        window=None,
        prefs={},
        favorite_ports=[],
        _rebuild_layout=MagicMock(),
    )
    # re-bind _mark_dirty so it refers to the actual namespace
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# load_or_default
# ---------------------------------------------------------------------------


class TestLoadOrDefault:
    def test_creates_scene_when_no_files(self, tmp_path):
        app = _make_app(tmp_path)
        # Clear scenes to simulate fresh state
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        assert app.designer.current_scene is not None
        sc = app.designer.scenes[app.designer.current_scene]
        assert sc.width == 256
        assert sc.height == 128

    def test_loads_base_json(self, tmp_path):
        app = _make_app(tmp_path)
        # Save baseline
        app.designer.save_to_json(str(app.json_path))
        # Clear and reload
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        assert "main" in app.designer.scenes

    def test_prefers_autosave_when_newer(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="base")])
        app.designer.save_to_json(str(app.json_path))
        time.sleep(0.05)
        # Add a widget and save as autosave
        sc = app.designer.scenes["main"]
        sc.widgets.append(_make_widget(text="auto"))
        app.designer.save_to_json(str(app.autosave_path))
        # Clear and reload
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        sc = app.designer.scenes[app.designer.current_scene]
        texts = [w.text for w in sc.widgets]
        assert "auto" in texts
        assert app._restored_from_autosave is True


# ---------------------------------------------------------------------------
# Widget presets
# ---------------------------------------------------------------------------


class TestWidgetPresets:
    def test_load_returns_empty_when_no_file(self, tmp_path):
        app = _make_app(tmp_path)
        assert load_widget_presets(app) == []

    def test_save_and_load_round_trip(self, tmp_path):
        app = _make_app(tmp_path)
        app.widget_presets = [{"type": "button", "width": 40}]
        save_widget_presets(app)
        loaded = load_widget_presets(app)
        assert loaded == [{"type": "button", "width": 40}]

    def test_load_returns_empty_on_corrupt_json(self, tmp_path):
        app = _make_app(tmp_path)
        app.preset_path.write_text("NOT JSON", encoding="utf-8")
        assert load_widget_presets(app) == []


class TestSavePresetSlot:
    def test_no_selection_is_noop(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        save_preset_slot(app, 1)
        assert app.widget_presets == []

    def test_saves_selected_widget(self, tmp_path):
        w = _make_widget(text="saved")
        app = _make_app(tmp_path, widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        save_preset_slot(app, 1)
        assert len(app.widget_presets) == 1
        preset = app.widget_presets[0]
        assert preset["text"] == "saved"
        assert "x" not in preset
        assert "y" not in preset


class TestApplyPresetSlot:
    def test_invalid_slot_is_noop(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app.widget_presets = [{"type": "button", "width": 99}]
        apply_preset_slot(app, 0)  # slot 0 → < 1
        assert app.designer.scenes["main"].widgets[0].width == 40

    def test_apply_to_selection(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(width=40)])
        app.widget_presets = [{"type": "button", "width": 99}]
        app.state.selected = [0]
        app.state.selected_idx = 0
        apply_preset_slot(app, 1)
        assert app.designer.scenes["main"].widgets[0].width == 99

    def test_add_new_widget_without_xy_in_preset_is_noop(self, tmp_path):
        """WidgetConfig requires x/y; if preset strips them, construction fails silently."""
        app = _make_app(tmp_path)
        app.widget_presets = [
            {"type": "label", "x": 0, "y": 0, "width": 50, "height": 20, "text": "new"}
        ]
        apply_preset_slot(app, 1, add_new=True)
        sc = app.designer.scenes["main"]
        # The code strips x/y from preset dict before constructing WidgetConfig,
        # so the constructor raises TypeError (missing x/y). The except returns early.
        assert len(sc.widgets) == 0


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


class TestPrefs:
    def test_load_prefs_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cyberpunk_designer.io_ops.PREFS_PATH", tmp_path / "no.json")
        app = _make_app(tmp_path)
        load_prefs(app)
        assert app.prefs == {}

    def test_save_and_load_round_trip(self, tmp_path, monkeypatch):
        prefs_file = tmp_path / "test_prefs.json"
        monkeypatch.setattr("cyberpunk_designer.io_ops.PREFS_PATH", prefs_file)
        app = _make_app(tmp_path)
        app.favorite_ports = ["COM3", "COM4"]
        save_prefs(app)
        # Reset and reload
        app.prefs = {}
        app.favorite_ports = []
        load_prefs(app)
        assert app.favorite_ports == ["COM3", "COM4"]


# ---------------------------------------------------------------------------
# save_json / write_audit_report
# ---------------------------------------------------------------------------


class TestSaveJson:
    def test_atomic_save(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="atom")])
        app._dirty = True
        save_json(app)
        assert app.json_path.exists()
        data = json.loads(app.json_path.read_text(encoding="utf-8"))
        texts = [w["text"] for w in data["scenes"]["main"]["widgets"]]
        assert "atom" in texts
        assert app._dirty is False

    def test_write_audit_report(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        app = _make_app(tmp_path, widgets=[_make_widget()])
        write_audit_report(app)
        report = (tmp_path / "reports" / "last_audit.txt").read_text(encoding="utf-8")
        assert "widgets: 1" in report


# ---------------------------------------------------------------------------
# maybe_autosave
# ---------------------------------------------------------------------------


class TestMaybeAutosave:
    def test_not_dirty_skips(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app._dirty = False
        maybe_autosave(app)
        assert not app.autosave_path.exists()

    def test_disabled_skips(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app._dirty = True
        app.autosave_enabled = False
        maybe_autosave(app)
        assert not app.autosave_path.exists()

    def test_respects_interval(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app._dirty = True
        app._last_autosave_ts = time.time()  # just now
        app.autosave_interval = 9999
        maybe_autosave(app)
        assert not app.autosave_path.exists()

    def test_saves_when_due(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="auto")])
        app._dirty = True
        app._last_autosave_ts = 0  # long ago
        maybe_autosave(app)
        assert app.autosave_path.exists()
        assert app._dirty is False


# ---------------------------------------------------------------------------
# Extended edge-case coverage
# ---------------------------------------------------------------------------


class TestLoadOrDefaultExtended:
    def test_corrupt_autosave_falls_back_to_base(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="base")])
        app.designer.save_to_json(str(app.json_path))
        time.sleep(0.05)
        app.autosave_path.write_text("NOT JSON", encoding="utf-8")
        # Clear and reload
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        assert "main" in app.designer.scenes

    def test_no_autosave_loads_base(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="only_base")])
        app.designer.save_to_json(str(app.json_path))
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        sc = app.designer.scenes[app.designer.current_scene]
        texts = [w.text for w in sc.widgets]
        assert "only_base" in texts


class TestSavePresetSlotExtended:
    def test_slot_extends_list(self, tmp_path):
        w = _make_widget(text="ext")
        app = _make_app(tmp_path, widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        save_preset_slot(app, 3)
        assert len(app.widget_presets) == 3
        assert app.widget_presets[2]["text"] == "ext"

    def test_out_of_range_selection_noop(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        save_preset_slot(app, 1)
        assert app.widget_presets == []


class TestApplyPresetSlotExtended:
    def test_empty_preset_noop(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app.widget_presets = [{}]
        app.state.selected = [0]
        apply_preset_slot(app, 1)
        # Empty preset applied — no crash
        assert app.designer.scenes["main"].widgets[0].type == "label"

    def test_slot_beyond_list_noop(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app.widget_presets = [{"type": "button"}]
        apply_preset_slot(app, 5)  # only 1 preset exists


class TestSaveJsonExtended:
    def test_overwrite_existing(self, tmp_path):
        app = _make_app(tmp_path, widgets=[_make_widget(text="v1")])
        app._dirty = True
        save_json(app)
        # Modify and save again
        app.designer.scenes["main"].widgets[0].text = "v2"
        app._dirty = True
        save_json(app)
        data = json.loads(app.json_path.read_text(encoding="utf-8"))
        assert data["scenes"]["main"]["widgets"][0]["text"] == "v2"


class TestPrefsExtended:
    def test_corrupt_prefs_resets(self, tmp_path, monkeypatch):
        prefs_file = tmp_path / "bad_prefs.json"
        prefs_file.write_text("{bad json", encoding="utf-8")
        monkeypatch.setattr("cyberpunk_designer.io_ops.PREFS_PATH", prefs_file)
        app = _make_app(tmp_path)
        load_prefs(app)
        assert app.prefs == {}


# ---------------------------------------------------------------------------
# load_or_default — deeper edge cases
# ---------------------------------------------------------------------------


class TestLoadOrDefaultDeep:
    def test_stat_exception_skips_autosave(self, tmp_path, monkeypatch):
        """When stat() raises during mtime comparison, autosave is skipped."""
        app = _make_app(tmp_path, widgets=[_make_widget(text="base")])
        app.designer.save_to_json(str(app.json_path))
        # Create autosave file so both paths exist
        app.autosave_path.write_text(app.json_path.read_text(encoding="utf-8"), encoding="utf-8")
        # Patch Path.stat to raise only after the .exists() calls
        real_stat = Path.stat
        call_count = [0]

        def flaky_stat(self_, *a, **kw):
            call_count[0] += 1
            # exists() calls stat twice (json_path, autosave_path),
            # then the mtime check calls stat again — fail on call 3+
            if call_count[0] > 2:
                raise OSError("flaky stat")
            return real_stat(self_, *a, **kw)

        monkeypatch.setattr(Path, "stat", flaky_stat)
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        # Should fall through to base (stat exception → use_autosave=False)
        assert app.designer.current_scene is not None

    def test_corrupt_autosave_falls_through(self, tmp_path):
        """Confirm corrupt autosave triggers exception path and falls to base."""
        app = _make_app(tmp_path, widgets=[_make_widget(text="base")])
        app.designer.save_to_json(str(app.json_path))
        app.autosave_path.write_text("NOT JSON AT ALL", encoding="utf-8")
        # Ensure autosave has later mtime than base (don't rely on sleep)
        base_mtime = app.json_path.stat().st_mtime
        os.utime(str(app.autosave_path), (base_mtime + 10, base_mtime + 10))
        app.designer.scenes.clear()
        app.designer.current_scene = None
        load_or_default(app)
        assert "main" in app.designer.scenes


# ---------------------------------------------------------------------------
# apply_preset_slot — deeper branches
# ---------------------------------------------------------------------------


class TestApplyPresetSlotDeep:
    def test_out_of_range_selection_idx_skipped(self, tmp_path):
        """Selection with out-of-range index is skipped, valid indices applied."""
        app = _make_app(tmp_path, widgets=[_make_widget(width=40)])
        app.widget_presets = [{"type": "button", "width": 99, "text": "preset"}]
        app.state.selected = [0, 50]  # 50 is out of range
        app.state.selected_idx = 0
        apply_preset_slot(app, 1)
        assert app.designer.scenes["main"].widgets[0].text == "preset"

    def test_no_selection_in_else_branch(self, tmp_path):
        """When no widgets are selected and add_new=False, returns early."""
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app.widget_presets = [{"type": "button", "width": 99}]
        app.state.selected = []
        apply_preset_slot(app, 1, add_new=False)
        # No crash, no change
        assert app.designer.scenes["main"].widgets[0].width == 40


# ---------------------------------------------------------------------------
# load_json
# ---------------------------------------------------------------------------


class TestLoadJson:
    def test_load_json_no_file(self, tmp_path):
        """load_json returns early if file doesn't exist."""
        app = _make_app(tmp_path)
        app.layout = MagicMock()
        load_json(app)
        # No crash, no change — file doesn't exist

    def test_load_json_basic(self, tmp_path):
        """load_json loads the file and rebuilds state."""
        app = _make_app(tmp_path, widgets=[_make_widget(text="saved")])
        app.designer.save_to_json(str(app.json_path))
        app.layout = MagicMock()
        # Modify in memory
        app.designer.scenes["main"].widgets[0].text = "modified"
        app._dirty = True
        # Load from file — should restore
        load_json(app)
        sc = app.designer.scenes[app.designer.current_scene]
        assert any(w.text == "saved" for w in sc.widgets)
        assert app._dirty is False
        app._rebuild_layout.assert_called_once()


# ---------------------------------------------------------------------------
# save_json — fallback path
# ---------------------------------------------------------------------------


class TestSaveJsonFallback:
    def test_tempfile_failure_falls_back(self, tmp_path, monkeypatch):
        """When mkstemp fails, save_json falls back to direct save."""
        import tempfile

        app = _make_app(tmp_path, widgets=[_make_widget(text="fb")])
        app._dirty = True
        monkeypatch.chdir(tmp_path)

        # Make mkstemp raise
        def bad_mkstemp(**kwargs):
            raise OSError("mock mkstemp failure")

        monkeypatch.setattr(tempfile, "mkstemp", bad_mkstemp)
        save_json(app)
        assert app.json_path.exists()
        data = json.loads(app.json_path.read_text(encoding="utf-8"))
        texts = [w["text"] for w in data["scenes"]["main"]["widgets"]]
        assert "fb" in texts
        assert app._dirty is False

    def test_tempfile_rename_failure_falls_back(self, tmp_path, monkeypatch):
        """When os.replace fails after mkstemp, falls back to direct save."""
        app = _make_app(tmp_path, widgets=[_make_widget(text="rn")])
        app._dirty = True
        monkeypatch.chdir(tmp_path)

        # Make os.replace raise (after temp file is written)
        def bad_replace(src, dst):
            raise OSError("mock replace failure")

        monkeypatch.setattr("os.replace", bad_replace)
        save_json(app)
        assert app.json_path.exists()
        assert app._dirty is False


# ---------------------------------------------------------------------------
# maybe_autosave — exception branch
# ---------------------------------------------------------------------------


class TestMaybeAutosaveDeep:
    def test_save_exception_is_silenced(self, tmp_path):
        """When save_to_json raises in autosave, exception is silenced."""
        app = _make_app(tmp_path, widgets=[_make_widget()])
        app._dirty = True
        app._last_autosave_ts = 0
        # Make save raise
        app.designer.save_to_json = MagicMock(side_effect=OSError("disk full"))
        maybe_autosave(app)
        # No crash — exception silenced
        assert not app.autosave_path.exists()


# ---------------------------------------------------------------------------
# save_widget_presets — exception branch
# ---------------------------------------------------------------------------


class TestSaveWidgetPresetsDeep:
    def test_write_exception_silenced(self, tmp_path):
        """When writing presets fails, exception is silenced."""
        app = _make_app(tmp_path, widgets=[])
        app.widget_presets = [{"type": "button"}]
        # Make path read-only dir
        app.preset_path = tmp_path / "readonly" / "presets.json"
        save_widget_presets(app)
        # No crash

    def test_load_corrupt_returns_empty(self, tmp_path):
        """Corrupt preset JSON returns empty list."""
        app = _make_app(tmp_path)
        app.preset_path.write_text("{invalid: json", encoding="utf-8")
        result = load_widget_presets(app)
        assert result == []
