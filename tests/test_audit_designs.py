"""Tests for tools/audit_designs.py — design file auditing."""

import json

from tools.audit_designs import audit_file, find_design_files

# ── find_design_files ──────────────────────────────────────────────────


def test_find_design_files(tmp_path):
    (tmp_path / "scene.json").write_text("{}")
    (tmp_path / "other.json").write_text("{}")
    (tmp_path / "readme.txt").write_text("nope")
    files = sorted(p.name for p in find_design_files(tmp_path))
    assert "scene.json" in files
    assert "other.json" in files
    assert "readme.txt" not in files


def test_find_design_files_skips_defaults(tmp_path):
    (tmp_path / "templates.json").write_text("{}")
    (tmp_path / "pyrightconfig.json").write_text("{}")
    (tmp_path / "real.json").write_text("{}")
    files = [p.name for p in find_design_files(tmp_path)]
    assert "templates.json" not in files
    assert "pyrightconfig.json" not in files
    assert "real.json" in files


def test_find_design_files_empty_dir(tmp_path):
    assert list(find_design_files(tmp_path)) == []


# ── audit_file ─────────────────────────────────────────────────────────


def _write_design(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_audit_file_valid(tmp_path):
    data = {
        "width": 128, "height": 64,
        "scenes": {
            "main": {"widgets": [{"type": "label"}]}
        }
    }
    p = _write_design(tmp_path, "ok.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert ok is True
    assert "ok.json" in msg
    assert "128x64" in msg
    assert "scenes=1" in msg
    assert "widgets=1" in msg


def test_audit_file_invalid_size(tmp_path):
    data = {"width": 0, "height": 0, "scenes": {}}
    p = _write_design(tmp_path, "bad.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert ok is False
    assert "invalid size" in msg


def test_audit_file_oversize(tmp_path):
    data = {
        "width": 800, "height": 600,
        "scenes": {"s": {"widgets": [{"type": "box"}]}}
    }
    p = _write_design(tmp_path, "big.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert "oversize" in msg


def test_audit_file_empty_scene(tmp_path):
    data = {
        "width": 128, "height": 64,
        "scenes": {"empty": {"widgets": []}}
    }
    p = _write_design(tmp_path, "e.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert "empty scenes" in msg


def test_audit_file_broken_json(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    ok, msg = audit_file(p, 320, 240)
    assert ok is False
    assert "FAILED" in msg


def test_audit_file_fb_estimate_small(tmp_path):
    data = {"width": 128, "height": 64, "scenes": {"s": {"widgets": [{"type": "box"}]}}}
    p = _write_design(tmp_path, "small.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert "fb_est=" in msg
    assert ok is True


def test_audit_file_fb_estimate_large(tmp_path):
    data = {"width": 256, "height": 128, "scenes": {"s": {"widgets": [{"type": "box"}]}}}
    p = _write_design(tmp_path, "large.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert "fb_est=" in msg
    # 256x128 at 16bpp → 256*128*2 = 65536 bytes = 64KB
    assert ok is True


def test_audit_file_multiple_scenes(tmp_path):
    data = {
        "width": 128, "height": 64,
        "scenes": {
            "a": {"widgets": [{"type": "label"}, {"type": "button"}]},
            "b": {"widgets": [{"type": "box"}]},
        }
    }
    p = _write_design(tmp_path, "multi.json", data)
    ok, msg = audit_file(p, 320, 240)
    assert ok is True
    assert "scenes=2" in msg
    assert "widgets=3" in msg
