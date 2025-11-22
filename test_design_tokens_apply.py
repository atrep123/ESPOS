#!/usr/bin/env python3
"""Tests for design_tokens helper utilities."""

import types
import pytest

from design_tokens import apply_tokens, resolve_token, color_hex, spacing


def test_apply_tokens_to_dict():
    target = {"bg": "old", "pad": 0}
    mapping = {"bg": "theme_light_bg", "pad": "md"}
    out = apply_tokens(target, mapping)
    assert out is target
    assert target["bg"] == color_hex("theme_light_bg")
    assert target["pad"] == spacing("md")


def test_apply_tokens_to_object_and_ignore_unknowns():
    obj = types.SimpleNamespace(bg=None, fg=None)
    mapping = {
        "bg": "theme_dark_bg",
        "fg": "theme_dark_text",
        "missing_field": "theme_dark_primary",  # should be ignored
        "fg_missing_token": "does_not_exist",   # should be ignored
    }
    out = apply_tokens(obj, mapping)
    assert out is obj
    assert obj.bg == color_hex("theme_dark_bg")
    assert obj.fg == color_hex("theme_dark_text")


def test_resolve_token_unknown_raises():
    with pytest.raises(KeyError):
        resolve_token("not_a_token")
