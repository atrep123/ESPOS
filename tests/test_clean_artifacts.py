"""Tests for tools/clean_artifacts.py — remove_path and clean logic."""

from tools.clean_artifacts import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_GLOBS,
    DEFAULT_PATHS,
    clean,
    remove_path,
)

# ── remove_path ───────────────────────────────────────────────────────


def test_remove_path_file_apply(tmp_path):
    f = tmp_path / "test.log"
    f.write_text("hello")
    remove_path(f, apply=True)
    assert not f.exists()


def test_remove_path_dir_apply(tmp_path):
    d = tmp_path / "build"
    d.mkdir()
    (d / "file.o").write_text("data")
    remove_path(d, apply=True)
    assert not d.exists()


def test_remove_path_dry_run_keeps_file(tmp_path):
    f = tmp_path / "test.log"
    f.write_text("hello")
    remove_path(f, apply=False)
    assert f.exists()


def test_remove_path_dry_run_keeps_dir(tmp_path):
    d = tmp_path / "build"
    d.mkdir()
    remove_path(d, apply=False)
    assert d.exists()


def test_remove_path_nonexistent_no_error(tmp_path):
    missing = tmp_path / "nope"
    remove_path(missing, apply=True)  # should not raise


# ── clean ─────────────────────────────────────────────────────────────


def test_clean_removes_default_paths_apply(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".pytest_cache"
    target.mkdir()
    (target / "v" / "cache").mkdir(parents=True)
    (target / "v" / "cache" / "data").write_text("{}")
    clean([target], [], apply=True)
    assert not target.exists()


def test_clean_dry_run_preserves(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / ".ruff_cache"
    target.mkdir()
    clean([target], [], apply=False)
    assert target.exists()


def test_clean_globs_match_pyc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    pyc = pkg / "mod.pyc"
    pyc.write_text("bytecode")
    clean([], ["**/*.pyc"], apply=True)
    assert not pyc.exists()


def test_clean_globs_match_pycache_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cache = tmp_path / "src" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "mod.cpython-312.pyc").write_text("data")
    clean([], ["**/__pycache__"], apply=True)
    assert not cache.exists()


def test_clean_excludes_git_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git_log = tmp_path / ".git" / "test.log"
    git_log.parent.mkdir(parents=True)
    git_log.write_text("log")
    clean([], ["*.log"], apply=True)
    # .git is in DEFAULT_EXCLUDE_DIRS so its contents should NOT be walked
    assert git_log.exists()


# ── constants ─────────────────────────────────────────────────────────


def test_default_paths_are_relative():
    for p in DEFAULT_PATHS:
        assert not p.is_absolute()


def test_default_globs_non_empty():
    assert len(DEFAULT_GLOBS) > 0
    assert all(isinstance(g, str) for g in DEFAULT_GLOBS)


def test_default_exclude_dirs_has_git():
    assert ".git" in DEFAULT_EXCLUDE_DIRS
    assert ".venv" in DEFAULT_EXCLUDE_DIRS
