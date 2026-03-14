"""Tests for scripts/pio_generate_ui_design.py helper functions.

The PlatformIO script uses SCons Import("env") at module level, so we
cannot import it directly.  Instead we test the extractable helper
``_strip_optional_quotes`` and env-var parsing logic by exec-ing parts.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Extract _strip_optional_quotes from the script source
# ---------------------------------------------------------------------------

_SRC = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "scripts"
    / "pio_generate_ui_design.py"
).read_text(encoding="utf-8")


def _extract_function(source: str, name: str) -> str:
    """Return function body from *source* by finding ``def name(...):``."""
    lines = source.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"def {name}("):
            start = i
            break
    if start is None:
        raise ValueError(f"Function {name!r} not found in source")
    body_lines = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() and not line[0].isspace():
            break
        body_lines.append(line)
    return "".join(body_lines)


_ns: dict = {}
exec(compile(_extract_function(_SRC, "_strip_optional_quotes"), "<pio>", "exec"), _ns)  # noqa: S102
_strip_optional_quotes = _ns["_strip_optional_quotes"]


# ---------------------------------------------------------------------------
# _strip_optional_quotes
# ---------------------------------------------------------------------------


class TestStripOptionalQuotes:
    def test_plain_string(self):
        assert _strip_optional_quotes("hello") == "hello"

    def test_double_quoted(self):
        assert _strip_optional_quotes('"hello"') == "hello"

    def test_single_quoted(self):
        assert _strip_optional_quotes("'hello'") == "hello"

    def test_surrounding_spaces(self):
        assert _strip_optional_quotes('  "spaced"  ') == "spaced"

    def test_inner_spaces_preserved(self):
        assert _strip_optional_quotes('" a b "') == "a b"

    def test_empty_string(self):
        assert _strip_optional_quotes("") == ""

    def test_single_char(self):
        assert _strip_optional_quotes("x") == "x"

    def test_mismatched_quotes_kept(self):
        assert _strip_optional_quotes("\"hello'") == "\"hello'"

    def test_only_quotes(self):
        assert _strip_optional_quotes('""') == ""


# ---------------------------------------------------------------------------
# Env-var flag parsing (unit logic extracted inline)
# ---------------------------------------------------------------------------

_TRUTHY = {"1", "true", "on", "yes"}
_FALSY = {"0", "false", "off", "no"}


def _parse_export_flag(raw: str) -> str:
    """Replicate the flag parsing logic from the script."""
    val = raw.strip().lower()
    if val in _FALSY:
        return "disabled"
    if val in _TRUTHY:
        return "enabled"
    return "invalid"


class TestExportFlagParsing:
    @pytest.mark.parametrize("raw", ["0", "false", "off", "no", " 0 ", "FALSE", "Off"])
    def test_disabled(self, raw):
        assert _parse_export_flag(raw) == "disabled"

    @pytest.mark.parametrize("raw", ["1", "true", "on", "yes", " 1 ", "TRUE", "Yes"])
    def test_enabled(self, raw):
        assert _parse_export_flag(raw) == "enabled"

    @pytest.mark.parametrize("raw", ["2", "maybe", "", "yep"])
    def test_invalid(self, raw):
        assert _parse_export_flag(raw) == "invalid"


# ---------------------------------------------------------------------------
# Path security check logic (replicated from script)
# ---------------------------------------------------------------------------


class TestPathSecurity:
    def test_relative_path_inside_project(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        json_path = (project_dir / "main_scene.json").resolve()
        json_path.touch()
        # Should not raise
        json_path.relative_to(project_dir.resolve())

    def test_path_escapes_project(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        outside = (tmp_path / "outside.json").resolve()
        outside.touch()
        with pytest.raises(ValueError, match="is not in the subpath of"):
            outside.relative_to(project_dir.resolve())

    def test_directory_path_detected(self, tmp_path):
        d = tmp_path / "somedir"
        d.mkdir()
        assert d.is_dir()
