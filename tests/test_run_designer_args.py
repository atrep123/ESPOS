"""Tests for run_designer.py functions.

Covers: parse_args, _apply_headless_env, run_headless, send_live_preview.
"""

from __future__ import annotations

import os
import sys

import pytest

from run_designer import _apply_headless_env, parse_args, run_headless

# ===================================================================
# parse_args
# ===================================================================


class TestParseArgs:
    def test_default_args(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py"])
        args = parse_args()
        assert args.width == 320
        assert args.height == 240
        assert args.headless_export is False
        assert args.headless is False
        assert args.profile is None

    def test_json_path(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "my_scene.json"])
        args = parse_args()
        assert str(args.json) == "my_scene.json"

    def test_custom_dimensions(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--width", "128", "--height", "64"])
        args = parse_args()
        assert args.width == 128
        assert args.height == 64

    def test_profile_flag(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_designer.py", "--profile", "esp32os_256x128_gray4"]
        )
        args = parse_args()
        assert args.profile == "esp32os_256x128_gray4"

    def test_headless_export(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--headless-export"])
        args = parse_args()
        assert args.headless_export is True

    def test_headless_mode(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--headless"])
        args = parse_args()
        assert args.headless is True

    def test_no_audio(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--no-audio"])
        args = parse_args()
        assert args.no_audio is True

    def test_fps_limit(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--fps-limit", "30"])
        args = parse_args()
        assert args.fps_limit == 30

    def test_autosave_flags(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--autosave"])
        args = parse_args()
        assert args.autosave is True
        assert args.no_autosave is False

    def test_no_autosave_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py", "--no-autosave"])
        args = parse_args()
        assert args.no_autosave is True

    def test_live_preview_port(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_designer.py", "--live-preview-port", "COM3"]
        )
        args = parse_args()
        assert args.live_preview_port == "COM3"

    def test_live_preview_baud_default(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_designer.py"])
        args = parse_args()
        assert args.live_preview_baud == 115200

    def test_live_preview_baud_custom(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_designer.py", "--live-preview-baud", "9600"]
        )
        args = parse_args()
        assert args.live_preview_baud == 9600

    def test_invalid_profile_rejected(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["run_designer.py", "--profile", "nonexistent"]
        )
        with pytest.raises(SystemExit):
            parse_args()


# ===================================================================
# _apply_headless_env
# ===================================================================


class TestApplyHeadlessEnv:
    def test_sets_video_driver(self, monkeypatch):
        monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
        _apply_headless_env(enable_headless=True, disable_audio=False)
        assert os.environ.get("SDL_VIDEODRIVER") == "dummy"

    def test_sets_audio_driver(self, monkeypatch):
        monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
        _apply_headless_env(enable_headless=False, disable_audio=True)
        assert os.environ.get("SDL_AUDIODRIVER") == "dummy"

    def test_both_flags(self, monkeypatch):
        monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
        monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
        _apply_headless_env(enable_headless=True, disable_audio=True)
        assert os.environ.get("SDL_VIDEODRIVER") == "dummy"
        assert os.environ.get("SDL_AUDIODRIVER") == "dummy"

    def test_no_flags_no_change(self, monkeypatch):
        monkeypatch.delenv("SDL_VIDEODRIVER", raising=False)
        monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
        _apply_headless_env(enable_headless=False, disable_audio=False)
        assert os.environ.get("SDL_VIDEODRIVER") is None
        assert os.environ.get("SDL_AUDIODRIVER") is None

    def test_does_not_override_existing(self, monkeypatch):
        monkeypatch.setenv("SDL_VIDEODRIVER", "x11")
        _apply_headless_env(enable_headless=True, disable_audio=False)
        assert os.environ.get("SDL_VIDEODRIVER") == "x11"


# ===================================================================
# run_headless
# ===================================================================


class TestRunHeadless:
    def test_creates_json(self, tmp_path):
        json_path = tmp_path / "test_scene.json"
        rc = run_headless(json_path, 256, 128)
        assert rc == 0
        assert json_path.exists()

    def test_with_profile(self, tmp_path):
        json_path = tmp_path / "test_scene.json"
        rc = run_headless(json_path, 256, 128, profile="esp32os_256x128_gray4")
        assert rc == 0
        assert json_path.exists()

    def test_updates_existing(self, tmp_path):
        import json

        json_path = tmp_path / "test_scene.json"
        run_headless(json_path, 256, 128)
        # Load and verify file exists
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "scenes" in data
        # Run again — should update, not crash
        rc = run_headless(json_path, 256, 128)
        assert rc == 0

    def test_creates_parent_dirs(self, tmp_path):
        json_path = tmp_path / "subdir" / "nested" / "scene.json"
        rc = run_headless(json_path, 256, 128)
        assert rc == 0
        assert json_path.exists()


# ===================================================================
# send_live_preview (error paths only — no real serial)
# ===================================================================


class TestSendLivePreview:
    def test_missing_pyserial_no_crash(self, tmp_path, monkeypatch):
        from run_designer import send_live_preview

        json_path = tmp_path / "scene.json"
        json_path.write_text('{"scenes":{}}', encoding="utf-8")
        # If pyserial is not installed, should print warning and return
        # If it IS installed, it'll fail on the fake port — either way no crash
        send_live_preview(json_path, "FAKE_PORT_9999", 115200)
