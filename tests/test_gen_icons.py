"""Tests for tools/gen_icons.py — icon bitmap generation and C code generation.

Covers: _c_ident, _chunked, _ends_with, _surface_bg_rgba, _surface_to_mask,
IconBitmap, _write_icons_c, _write_icons_h, _write_icons_24_h, _write_registry.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure tools/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from gen_icons import (
    IconBitmap,
    _c_ident,
    _chunked,
    _ends_with,
    _surface_bg_rgba,
    _surface_to_mask,
    _write_icons_24_h,
    _write_icons_c,
    _write_icons_h,
    _write_registry,
)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

pygame.display.init()
try:
    pygame.display.set_mode((1, 1))
except Exception:
    pass


# ===================================================================
# _c_ident
# ===================================================================


class TestCIdent:
    def test_plain_name(self):
        assert _c_ident("hello_world") == "hello_world"

    def test_special_chars_replaced(self):
        assert _c_ident("foo-bar.baz") == "foo_bar_baz"

    def test_leading_digit_prefixed(self):
        result = _c_ident("3d_icon")
        assert result[0] == "_"
        assert "3d_icon" in result

    def test_empty_string(self):
        assert _c_ident("") == ""

    def test_spaces_replaced(self):
        assert _c_ident("my icon") == "my_icon"

    def test_already_valid(self):
        assert _c_ident("abc_123") == "abc_123"


# ===================================================================
# _chunked
# ===================================================================


class TestChunked:
    def test_exact_division(self):
        result = list(_chunked([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_remainder(self):
        result = list(_chunked([1, 2, 3, 4, 5], 3))
        assert result == [[1, 2, 3], [4, 5]]

    def test_single_element_chunks(self):
        result = list(_chunked([1, 2, 3], 1))
        assert result == [[1], [2], [3]]

    def test_empty_input(self):
        result = list(_chunked([], 4))
        assert result == []

    def test_chunk_larger_than_input(self):
        result = list(_chunked([1, 2], 10))
        assert result == [[1, 2]]


# ===================================================================
# _ends_with
# ===================================================================


class TestEndsWith:
    def test_matches(self):
        assert _ends_with("hello_24px", "_24px") is True

    def test_no_match(self):
        assert _ends_with("hello", "_24px") is False

    def test_exact_match(self):
        assert _ends_with("_24px", "_24px") is True

    def test_shorter_than_suffix(self):
        assert _ends_with("px", "_24px") is False

    def test_empty_suffix(self):
        # _ends_with uses buf[-0:] for empty suffix, which is the full string
        assert _ends_with("anything", "") is False

    def test_empty_both(self):
        assert _ends_with("", "") is True


# ===================================================================
# _surface_bg_rgba
# ===================================================================


class TestSurfaceBgRgba:
    def test_solid_color(self):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        surf.fill((255, 0, 0, 255))
        r, g, b, a = _surface_bg_rgba(surf)
        assert r == 255
        assert g == 0
        assert b == 0
        assert a == 255

    def test_transparent_surface(self):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        _, _, _, a = _surface_bg_rgba(surf)
        assert a == 0

    def test_border_dominates(self):
        """Background comes from sampling edge pixels, so border color should win."""
        surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 255))  # solid black background
        # Draw a colored center — shouldn't affect bg detection
        inner = pygame.Rect(3, 3, 4, 4)
        surf.fill((255, 255, 255, 255), inner)
        r, g, b, a = _surface_bg_rgba(surf)
        assert r == 0  # border is black
        assert g == 0
        assert b == 0


# ===================================================================
# _surface_to_mask
# ===================================================================


class TestSurfaceToMask:
    def test_basic_dimensions(self):
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        assert w == 16
        assert h == 16
        assert stride == 2  # (16+7)//8 = 2
        assert len(data) == stride * h

    def test_transparent_produces_empty(self):
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))  # fully transparent
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        assert all(b == 0 for b in data)

    def test_opaque_white_on_black_border(self):
        """Opaque asset with contrast center should produce mask bits."""
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 255))  # black bg
        # White center pixel
        surf.set_at((4, 4), (255, 255, 255, 255))
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        # The white center pixel should be "on"
        idx = 4 * stride + (4 // 8)
        bit = 0x80 >> (4 & 7)
        assert data[idx] & bit

    def test_alpha_threshold_respected(self):
        """Pixels with alpha below threshold should be off."""
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))  # fully transparent
        surf.set_at((0, 0), (255, 255, 255, 100))  # below 128 threshold
        surf.set_at((1, 0), (255, 255, 255, 200))  # above threshold
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        # Pixel (0,0) should be off
        assert not (data[0] & 0x80)
        # Pixel (1,0) should be on
        assert data[0] & 0x40

    def test_stride_odd_width(self):
        surf = pygame.Surface((5, 1), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        assert stride == 1  # (5+7)//8 = 1

    def test_24x24_icon_size(self):
        """Standard icon size produces correct stride."""
        surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        data, w, h, stride = _surface_to_mask(surf, alpha_threshold=128)
        assert w == 24
        assert h == 24
        assert stride == 3  # (24+7)//8 = 3
        assert len(data) == 3 * 24


# ===================================================================
# IconBitmap dataclass
# ===================================================================


class TestIconBitmap:
    def test_construction(self):
        ib = IconBitmap(name="test", sym_base="mi_test", w=16, h=16, stride=2, data=b"\x00" * 32)
        assert ib.name == "test"
        assert ib.sym_base == "mi_test"
        assert ib.w == 16
        assert ib.h == 16
        assert ib.stride == 2
        assert len(ib.data) == 32

    def test_frozen(self):
        ib = IconBitmap(name="test", sym_base="mi_test", w=16, h=16, stride=2, data=b"\x00")
        with pytest.raises(AttributeError):
            ib.name = "other"


# ===================================================================
# _write_icons_c
# ===================================================================


class TestWriteIconsC:
    def test_basic_output(self, tmp_path):
        icon = IconBitmap(
            name="arrow",
            sym_base="mi_arrow",
            w=16,
            h=16,
            stride=2,
            data=bytes([0xFF] * 32),
        )
        out = tmp_path / "icons.c"
        _write_icons_c(out, [icon], size_px=16)
        content = out.read_text(encoding="utf-8")
        assert "mi_arrow_16px" in content
        assert "icon_t" in content
        assert '#include "icons.h"' in content

    def test_24px_output(self, tmp_path):
        icon = IconBitmap(
            name="wifi",
            sym_base="mi_wifi",
            w=24,
            h=24,
            stride=3,
            data=bytes([0xAA] * 72),
        )
        out = tmp_path / "icons_24.c"
        _write_icons_c(out, [icon], size_px=24)
        content = out.read_text(encoding="utf-8")
        assert "mi_wifi_24px" in content
        assert ".width = 24" in content
        assert ".height = 24" in content

    def test_multiple_icons(self, tmp_path):
        icons = [
            IconBitmap(name="a", sym_base="mi_a", w=16, h=16, stride=2, data=bytes(32)),
            IconBitmap(name="b", sym_base="mi_b", w=16, h=16, stride=2, data=bytes(32)),
        ]
        out = tmp_path / "icons.c"
        _write_icons_c(out, icons, size_px=16)
        content = out.read_text(encoding="utf-8")
        assert "mi_a_16px" in content
        assert "mi_b_16px" in content

    def test_empty_icons_list(self, tmp_path):
        out = tmp_path / "empty.c"
        _write_icons_c(out, [], size_px=16)
        content = out.read_text(encoding="utf-8")
        assert '#include "icons.h"' in content

    def test_hex_values_in_output(self, tmp_path):
        icon = IconBitmap(
            name="test",
            sym_base="mi_test",
            w=8,
            h=1,
            stride=1,
            data=bytes([0xAB]),
        )
        out = tmp_path / "test.c"
        _write_icons_c(out, [icon], size_px=16)
        content = out.read_text(encoding="utf-8")
        assert "0xab" in content


# ===================================================================
# _write_icons_h
# ===================================================================


class TestWriteIconsH:
    def test_basic_header(self, tmp_path):
        icons = [
            IconBitmap(name="a", sym_base="mi_a", w=16, h=16, stride=2, data=bytes(32)),
            IconBitmap(name="b", sym_base="mi_b", w=16, h=16, stride=2, data=bytes(32)),
        ]
        out = tmp_path / "icons.h"
        _write_icons_h(out, icons)
        content = out.read_text(encoding="utf-8")
        assert "#pragma once" in content
        assert "icon_t" in content
        assert "extern const icon_t mi_a_16px;" in content
        assert "extern const icon_t mi_a_24px;" in content
        assert "extern const icon_t mi_b_16px;" in content

    def test_empty_icons(self, tmp_path):
        out = tmp_path / "icons.h"
        _write_icons_h(out, [])
        content = out.read_text(encoding="utf-8")
        assert "#pragma once" in content
        assert "icon_t" in content

    def test_have_icons_guard(self, tmp_path):
        out = tmp_path / "icons.h"
        _write_icons_h(out, [])
        content = out.read_text(encoding="utf-8")
        assert "HAVE_ICONS" in content


# ===================================================================
# _write_icons_24_h
# ===================================================================


class TestWriteIcons24H:
    def test_compat_header(self, tmp_path):
        out = tmp_path / "icons_24.h"
        _write_icons_24_h(out)
        content = out.read_text(encoding="utf-8")
        assert "#pragma once" in content
        assert '#include "icons.h"' in content
        assert "Compatibility" in content


# ===================================================================
# _write_registry
# ===================================================================


class TestWriteRegistry:
    def test_basic_registry(self, tmp_path):
        icons = [
            IconBitmap(name="arrow", sym_base="mi_arrow", w=16, h=16, stride=2, data=bytes(32)),
        ]
        out_h = tmp_path / "icons_registry.h"
        out_c = tmp_path / "icons_registry.c"
        _write_registry(out_h, out_c, icons)

        h_content = out_h.read_text(encoding="utf-8")
        assert "icons_find" in h_content
        assert "#pragma once" in h_content

        c_content = out_c.read_text(encoding="utf-8")
        assert "arrow" in c_content
        assert "mi_arrow_16px" in c_content
        assert "mi_arrow_24px" in c_content
        assert "normalize_key" in c_content

    def test_multiple_icons_in_registry(self, tmp_path):
        icons = [
            IconBitmap(name="a", sym_base="mi_a", w=16, h=16, stride=2, data=bytes(32)),
            IconBitmap(name="b", sym_base="mi_b", w=16, h=16, stride=2, data=bytes(32)),
        ]
        out_h = tmp_path / "reg.h"
        out_c = tmp_path / "reg.c"
        _write_registry(out_h, out_c, icons)
        c_content = out_c.read_text(encoding="utf-8")
        assert '"a"' in c_content
        assert '"b"' in c_content

    def test_empty_icons(self, tmp_path):
        out_h = tmp_path / "empty.h"
        out_c = tmp_path / "empty.c"
        _write_registry(out_h, out_c, [])
        c_content = out_c.read_text(encoding="utf-8")
        assert "k_icons" in c_content

    def test_registry_c_includes_header(self, tmp_path):
        icons = [
            IconBitmap(name="x", sym_base="mi_x", w=16, h=16, stride=2, data=bytes(32)),
        ]
        out_h = tmp_path / "icons_registry.h"
        out_c = tmp_path / "icons_registry.c"
        _write_registry(out_h, out_c, icons)
        c_content = out_c.read_text(encoding="utf-8")
        assert '#include "icons_registry.h"' in c_content

    def test_registry_has_ends_with_helper(self, tmp_path):
        out_h = tmp_path / "r.h"
        out_c = tmp_path / "r.c"
        _write_registry(out_h, out_c, [])
        c_content = out_c.read_text(encoding="utf-8")
        assert "ends_with" in c_content

    def test_registry_has_normalize_key(self, tmp_path):
        out_h = tmp_path / "r.h"
        out_c = tmp_path / "r.c"
        _write_registry(out_h, out_c, [])
        c_content = out_c.read_text(encoding="utf-8")
        assert "normalize_key" in c_content
        assert "mi_" in c_content  # strips mi_ prefix
