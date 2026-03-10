"""Tests for CLI main() entry points of tools/ scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# tools/audit_designs.py main()
# ---------------------------------------------------------------------------

class TestAuditDesignsMain:
    def test_no_files_exits_0(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        from tools.audit_designs import main
        with patch("sys.argv", ["audit_designs", "--root", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "No design" in out

    def test_valid_file_exits_0(self, tmp_path, monkeypatch, capsys):
        design = {
            "width": 256, "height": 128,
            "scenes": {"main": {"widgets": [{"type": "label"}]}}
        }
        (tmp_path / "test.json").write_text(json.dumps(design), encoding="utf-8")
        from tools.audit_designs import main
        with patch("sys.argv", ["audit_designs", "--root", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "[OK]" in out

    def test_invalid_file_exits_1(self, tmp_path, monkeypatch, capsys):
        design = {"width": 0, "height": 0, "scenes": {}}
        (tmp_path / "bad.json").write_text(json.dumps(design), encoding="utf-8")
        from tools.audit_designs import main
        with patch("sys.argv", ["audit_designs", "--root", str(tmp_path)]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    def test_custom_max_dimensions(self, tmp_path, monkeypatch, capsys):
        design = {
            "width": 400, "height": 300,
            "scenes": {"main": {"widgets": []}}
        }
        (tmp_path / "big.json").write_text(json.dumps(design), encoding="utf-8")
        from tools.audit_designs import main
        with patch("sys.argv", ["audit_designs", "--root", str(tmp_path),
                                 "--max-width", "500", "--max-height", "500"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0


# ---------------------------------------------------------------------------
# tools/clean_artifacts.py main()
# ---------------------------------------------------------------------------

class TestCleanArtifactsMain:
    def test_dry_run_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from tools.clean_artifacts import main
        with patch("sys.argv", ["clean_artifacts"]):
            main()  # dry-run by default, should not raise

    def test_apply_flag_accepted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from tools.clean_artifacts import main
        with patch("sys.argv", ["clean_artifacts", "--apply"]):
            main()  # nothing to clean, but flag is accepted


# ---------------------------------------------------------------------------
# tools/ui_export_c_header.py main()
# ---------------------------------------------------------------------------

class TestExportCHeaderMain:
    def test_missing_json_exits(self, tmp_path):
        from tools.ui_export_c_header import main
        with patch("sys.argv", ["ui_export_c_header",
                                 str(tmp_path / "nonexistent.json"),
                                 "-o", str(tmp_path / "out.h")]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code is not None

    def test_valid_json_exports(self, tmp_path, capsys):
        design = {
            "width": 256, "height": 128,
            "scenes": {"main": {"widgets": [
                {"type": "label", "x": 0, "y": 0, "width": 40, "height": 14,
                 "text": "hi"}
            ]}}
        }
        json_path = tmp_path / "scene.json"
        json_path.write_text(json.dumps(design), encoding="utf-8")
        out_path = tmp_path / "subdir" / "ui.h"
        from tools.ui_export_c_header import main
        with patch("sys.argv", ["ui_export_c_header", str(json_path),
                                 "-o", str(out_path)]):
            main()
        assert out_path.exists()
        text = out_path.read_text(encoding="utf-8")
        assert "#ifndef" in text
        out = capsys.readouterr().out
        assert "[OK]" in out


# ---------------------------------------------------------------------------
# tools/live_preview.py main()
# ---------------------------------------------------------------------------

class TestLivePreviewMain:
    def test_missing_json_exits(self, tmp_path):
        from tools.live_preview import main
        with patch("sys.argv", ["live_preview",
                                 str(tmp_path / "nonexistent.json"),
                                 "--port", "COM99"]):
            with pytest.raises(SystemExit):
                main()

    def test_valid_json_calls_send(self, tmp_path, monkeypatch):
        design = {
            "width": 256, "height": 128,
            "scenes": {"main": {"widgets": []}}
        }
        json_path = tmp_path / "scene.json"
        json_path.write_text(json.dumps(design), encoding="utf-8")

        sent = []
        import tools.live_preview as lp_mod
        monkeypatch.setattr(lp_mod, "send_live_preview",
                            lambda path, port, baud: sent.append((str(path), port, baud)))

        from tools.live_preview import main
        with patch("sys.argv", ["live_preview", str(json_path),
                                 "--port", "COM99", "--baud", "9600"]):
            main()
        assert len(sent) == 1
        assert sent[0][1] == "COM99"
        assert sent[0][2] == 9600
