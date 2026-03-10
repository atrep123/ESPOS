"""Tests for cyberpunk_designer/inspector_logic.py utility functions
and cyberpunk_designer/inspector_utils.py helpers."""

from __future__ import annotations

from cyberpunk_designer.inspector_logic import _parse_active_count, _sorted_role_indices
from cyberpunk_designer.inspector_utils import format_int_list, parse_int_list

# ---------------------------------------------------------------------------
# _sorted_role_indices
# ---------------------------------------------------------------------------


class TestSortedRoleIndices:
    def test_basic(self):
        role_idx = {"btn0": 0, "btn1": 5, "btn2": 3}
        result = _sorted_role_indices(role_idx, "btn")
        assert result == [(0, 0), (1, 5), (2, 3)]

    def test_empty_prefix_returns_empty(self):
        assert _sorted_role_indices({"a0": 1}, "") == []

    def test_none_prefix_returns_empty(self):
        assert _sorted_role_indices({"a0": 1}, None) == []

    def test_none_role_idx(self):
        assert _sorted_role_indices(None, "x") == []

    def test_non_digit_suffix_ignored(self):
        role_idx = {"btn0": 1, "btn_extra": 2, "btnA": 3}
        result = _sorted_role_indices(role_idx, "btn")
        assert result == [(0, 1)]

    def test_no_matches(self):
        role_idx = {"label0": 1, "label1": 2}
        assert _sorted_role_indices(role_idx, "btn") == []


# ---------------------------------------------------------------------------
# _parse_active_count
# ---------------------------------------------------------------------------


class TestParseActiveCount:
    def test_basic(self):
        assert _parse_active_count("2/5") == (1, 5)  # 1-based → 0-based

    def test_first_item(self):
        assert _parse_active_count("1/3") == (0, 3)

    def test_last_item(self):
        assert _parse_active_count("3/3") == (2, 3)

    def test_clamped_above(self):
        # active > count → clamped to count
        assert _parse_active_count("10/3") == (2, 3)

    def test_clamped_below(self):
        # active < 1 → clamped to 1 → (0, count)
        assert _parse_active_count("0/3") == (0, 3)

    def test_zero_count(self):
        assert _parse_active_count("1/0") == (0, 0)

    def test_negative_count(self):
        assert _parse_active_count("1/-1") == (0, 0)

    def test_empty(self):
        assert _parse_active_count("") is None

    def test_none(self):
        assert _parse_active_count(None) is None

    def test_no_slash(self):
        assert _parse_active_count("5") is None

    def test_non_numeric(self):
        assert _parse_active_count("a/b") is None

    def test_whitespace(self):
        assert _parse_active_count(" 2 / 5 ") == (1, 5)


# ---------------------------------------------------------------------------
# format_int_list
# ---------------------------------------------------------------------------


class TestFormatIntList:
    def test_basic(self):
        assert format_int_list([1, 2, 3]) == "1,2,3"

    def test_empty(self):
        assert format_int_list([]) == ""

    def test_none(self):
        assert format_int_list(None) == ""

    def test_truncation(self):
        items = list(range(10))
        result = format_int_list(items, max_items=3)
        assert result == "0,1,2,..."

    def test_exactly_max(self):
        result = format_int_list([1, 2, 3], max_items=3)
        assert result == "1,2,3"

    def test_single(self):
        assert format_int_list([42]) == "42"


# ---------------------------------------------------------------------------
# parse_int_list
# ---------------------------------------------------------------------------


class TestParseIntList:
    def test_basic(self):
        assert parse_int_list("1,2,3") == [1, 2, 3]

    def test_empty(self):
        assert parse_int_list("") == []

    def test_none_input(self):
        assert parse_int_list(None) == []

    def test_spaces(self):
        assert parse_int_list("1 2 3") == [1, 2, 3]

    def test_semicolons(self):
        assert parse_int_list("1;2;3") == [1, 2, 3]

    def test_hex_values(self):
        assert parse_int_list("0x10,0xff") == [16, 255]

    def test_invalid_returns_none(self):
        assert parse_int_list("1,abc,3") is None

    def test_max_items_exceeded(self):
        big = ",".join(str(i) for i in range(300))
        assert parse_int_list(big, max_items=10) is None

    def test_value_clamping(self):
        result = parse_int_list("999999999", min_value=-100, max_value=100)
        assert result == [100]

    def test_negative_values(self):
        assert parse_int_list("-5,-10,0") == [-5, -10, 0]

    def test_whitespace_only(self):
        assert parse_int_list("   ") == []

    def test_leading_trailing_whitespace(self):
        assert parse_int_list("  10, 20  ") == [10, 20]

    def test_float_returns_none(self):
        assert parse_int_list("3.14") is None

    def test_min_clamping(self):
        result = parse_int_list("-999999999", min_value=-50)
        assert result == [-50]

    def test_mixed_separators(self):
        assert parse_int_list("1, 2; 3  4") == [1, 2, 3, 4]

    def test_exactly_max_items(self):
        assert parse_int_list("1,2,3", max_items=3) == [1, 2, 3]


class TestFormatIntListExtended:
    def test_negative_values(self):
        assert format_int_list([-5, 0, 5]) == "-5,0,5"

    def test_max_items_clamp_min_one(self):
        result = format_int_list([1, 2, 3], max_items=0)
        assert result == "1,..."

    def test_tuple_input(self):
        assert format_int_list((10, 20)) == "10,20"

    def test_default_max_32(self):
        items32 = list(range(32))
        assert "..." not in format_int_list(items32)
        items33 = list(range(33))
        assert format_int_list(items33).endswith(",...")

    def test_non_int_content_returns_empty(self):
        assert format_int_list(["a", "b"]) == ""

    def test_string_input_returns_empty(self):
        assert format_int_list("abc") == ""

