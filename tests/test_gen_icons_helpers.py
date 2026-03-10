"""Tests for pure helpers in tools/gen_icons.py."""

from tools.gen_icons import _c_ident, _chunked, _ends_with

# ── _c_ident ──────────────────────────────────────────────────────────


def test_c_ident_passthrough():
    assert _c_ident("hello") == "hello"


def test_c_ident_alpha_numeric():
    assert _c_ident("abc123") == "abc123"


def test_c_ident_underscores():
    assert _c_ident("my_var") == "my_var"


def test_c_ident_special_chars():
    assert _c_ident("hello-world") == "hello_world"
    assert _c_ident("a.b") == "a_b"
    assert _c_ident("x y") == "x_y"


def test_c_ident_leading_digit():
    assert _c_ident("3foo") == "_3foo"


def test_c_ident_all_special():
    assert _c_ident("---") == "___"


def test_c_ident_empty():
    assert _c_ident("") == ""


def test_c_ident_single_digit():
    assert _c_ident("9") == "_9"


# ── _chunked ─────────────────────────────────────────────────────────


def test_chunked_exact():
    result = list(_chunked([1, 2, 3, 4], 2))
    assert result == [[1, 2], [3, 4]]


def test_chunked_remainder():
    result = list(_chunked([1, 2, 3, 4, 5], 2))
    assert result == [[1, 2], [3, 4], [5]]


def test_chunked_single():
    result = list(_chunked([10, 20, 30], 1))
    assert result == [[10], [20], [30]]


def test_chunked_large_n():
    result = list(_chunked([1, 2], 10))
    assert result == [[1, 2]]


def test_chunked_empty():
    result = list(_chunked([], 3))
    assert result == []


def test_chunked_generator_input():
    result = list(_chunked(range(6), 3))
    assert result == [[0, 1, 2], [3, 4, 5]]


# ── _ends_with ───────────────────────────────────────────────────────


def test_ends_with_true():
    assert _ends_with("hello.png", ".png") is True


def test_ends_with_false():
    assert _ends_with("hello.jpg", ".png") is False


def test_ends_with_exact_match():
    assert _ends_with(".png", ".png") is True


def test_ends_with_shorter_than_suffix():
    assert _ends_with("ab", "abc") is False


def test_ends_with_empty_suffix():
    # buf[-0:] == buf[0:] == full string, so empty suffix returns False
    assert _ends_with("anything", "") is False


def test_ends_with_empty_both():
    # "" [-0:] == "" [0:] == "" == "" → True
    assert _ends_with("", "") is True


def test_ends_with_empty_buf():
    assert _ends_with("", "x") is False
