"""Tests for tools/ui_export_c_header.py — JSON-to-C-header export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ui_export_c_header import export_header


def _minimal_scene_json(tmp_path: Path, *, scene_name: str = "main") -> Path:
    """Write a minimal valid design JSON and return its path."""
    data = {
        "width": 256,
        "height": 128,
        "scenes": {
            scene_name: {
                "name": scene_name,
                "width": 256,
                "height": 128,
                "bg_color": "#000000",
                "widgets": [
                    {
                        "type": "label",
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 12,
                        "text": "Hello",
                    }
                ],
            }
        },
    }
    p = tmp_path / "test_scene.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestExportHeader:
    def test_produces_valid_header(self, tmp_path):
        json_path = _minimal_scene_json(tmp_path)
        out_path = tmp_path / "output" / "ui_test.h"
        export_header(json_path, out_path)
        text = out_path.read_text(encoding="utf-8")
        assert "#ifndef" in text
        assert "#define" in text
        assert '#include "ui_scene.h"' in text
        assert "Auto-generated" in text

    def test_guard_derived_from_filename(self, tmp_path):
        json_path = _minimal_scene_json(tmp_path)
        out_path = tmp_path / "my-header.h"
        export_header(json_path, out_path)
        text = out_path.read_text(encoding="utf-8")
        assert "MY_HEADER_H" in text

    def test_creates_parent_dirs(self, tmp_path):
        json_path = _minimal_scene_json(tmp_path)
        out_path = tmp_path / "deep" / "nested" / "ui.h"
        export_header(json_path, out_path)
        assert out_path.exists()

    def test_contains_widget_data(self, tmp_path):
        json_path = _minimal_scene_json(tmp_path)
        out_path = tmp_path / "ui.h"
        export_header(json_path, out_path)
        text = out_path.read_text(encoding="utf-8")
        # Should contain the widget text string and scene reference
        assert "Hello" in text
        assert "main" in text.lower()

    def test_multi_scene(self, tmp_path):
        data = {
            "width": 128,
            "height": 64,
            "scenes": {
                "home": {
                    "name": "home",
                    "width": 128,
                    "height": 64,
                    "bg_color": "#000",
                    "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50, "height": 10, "text": "Home"}],
                },
                "settings": {
                    "name": "settings",
                    "width": 128,
                    "height": 64,
                    "bg_color": "#000",
                    "widgets": [{"type": "label", "x": 0, "y": 0, "width": 50, "height": 10, "text": "Settings"}],
                },
            },
        }
        json_file = tmp_path / "multi.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        out_path = tmp_path / "multi.h"
        export_header(json_file, out_path)
        text = out_path.read_text(encoding="utf-8")
        assert "Home" in text
        assert "Settings" in text

    def test_empty_scenes_raises(self, tmp_path):
        data = {"width": 128, "height": 64, "scenes": {}}
        json_file = tmp_path / "empty.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        out_path = tmp_path / "empty.h"
        with pytest.raises(ValueError, match="No scenes"):
            export_header(json_file, out_path)

    def test_unix_line_endings(self, tmp_path):
        json_path = _minimal_scene_json(tmp_path)
        out_path = tmp_path / "ui.h"
        export_header(json_path, out_path)
        raw = out_path.read_bytes()
        assert b"\r\n" not in raw  # Unix line endings
