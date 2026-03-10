"""Tests for hardware display profiles — framebuffer math, profile switching,
resource estimation, widget rendering, and validation across all 16 profiles."""

import pygame
import pytest

from cyberpunk_designer import drawing
from cyberpunk_designer.constants import PROFILE_ORDER
from cyberpunk_editor import CyberpunkEditorApp
from tools.validate_design import validate_data
from ui_designer import HARDWARE_PROFILES, UIDesigner, WidgetConfig

ALL_PROFILES = list(HARDWARE_PROFILES.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch, *, profile=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    kw = {}
    if profile:
        kw["profile"] = profile
    return CyberpunkEditorApp(json_path, (256, 192), **kw)


def _fb_bytes_expected(width, height, color_depth):
    area = width * height
    if color_depth <= 1:
        return (area + 7) // 8
    return int(area * (color_depth / 8.0))


BG_COLOR = (0, 0, 0)


# ---------------------------------------------------------------------------
# 1. All profiles have valid structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_profile_has_required_fields(key):
    p = HARDWARE_PROFILES[key]
    for field in ("label", "width", "height", "color_depth", "max_fb_kb", "max_flash_kb"):
        assert field in p, f"profile '{key}' missing field '{field}'"
    assert isinstance(p["label"], str) and p["label"]
    assert isinstance(p["width"], int) and p["width"] > 0
    assert isinstance(p["height"], int) and p["height"] > 0
    assert p["color_depth"] in (1, 4, 8, 16), f"unexpected depth {p['color_depth']}"
    assert float(p["max_fb_kb"]) > 0
    assert float(p["max_flash_kb"]) > 0


# ---------------------------------------------------------------------------
# 2. Framebuffer math
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_framebuffer_bytes_formula(key):
    p = HARDWARE_PROFILES[key]
    designer = UIDesigner(p["width"], p["height"])
    designer.create_scene("main")
    designer.set_hardware_profile(key)
    est = designer.estimate_resources(profile=key, color_depth=p["color_depth"])
    expected = _fb_bytes_expected(p["width"], p["height"], p["color_depth"])
    assert int(est["framebuffer_bytes"]) == expected


@pytest.mark.parametrize("depth", [1, 4, 16])
def test_framebuffer_bytes_per_depth(depth):
    """Verify the math for each bit-depth on a known area."""
    w, h = 128, 64
    designer = UIDesigner(w, h)
    designer.create_scene("main")
    est = designer.estimate_resources(color_depth=depth)
    expected = _fb_bytes_expected(w, h, depth)
    assert int(est["framebuffer_bytes"]) == expected


# ---------------------------------------------------------------------------
# 3. Framebuffer fits within max_fb_kb for each profile
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_framebuffer_within_profile_limit(key):
    p = HARDWARE_PROFILES[key]
    fb = _fb_bytes_expected(p["width"], p["height"], p["color_depth"])
    limit = float(p["max_fb_kb"]) * 1024
    assert fb <= limit, (
        f"profile '{key}': fb {fb} bytes > limit {limit:.0f} bytes ({p['max_fb_kb']} KB)"
    )


# ---------------------------------------------------------------------------
# 4. set_hardware_profile works for every key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_set_hardware_profile(key):
    p = HARDWARE_PROFILES[key]
    designer = UIDesigner(16, 16)
    designer.create_scene("main")
    result = designer.set_hardware_profile(key)
    assert result is not None, f"set_hardware_profile('{key}') returned None"
    assert designer.width == p["width"]
    assert designer.height == p["height"]
    sc = designer.scenes["main"]
    assert sc.width == p["width"]
    assert sc.height == p["height"]


def test_set_unknown_profile_returns_none():
    designer = UIDesigner(16, 16)
    assert designer.set_hardware_profile("nonexistent_display") is None


# ---------------------------------------------------------------------------
# 5. estimate_resources returns valid dict for all profiles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_estimate_resources_structure(key):
    p = HARDWARE_PROFILES[key]
    designer = UIDesigner(p["width"], p["height"])
    designer.create_scene("main")
    designer.set_hardware_profile(key)
    est = designer.estimate_resources()
    required_keys = {
        "framebuffer_bytes",
        "framebuffer_kb",
        "flash_bytes",
        "flash_kb",
        "color_depth",
        "area",
        "widgets",
        "fb_over",
        "flash_over",
        "max_fb_kb",
        "max_flash_kb",
        "text_bytes",
        "widget_bytes",
        "overlaps",
        "overlap_pairs",
        "profile",
    }
    for k in required_keys:
        assert k in est, f"estimate_resources('{key}') missing key '{k}'"
    assert est["profile"] == key
    assert est["color_depth"] == float(p["color_depth"])
    assert est["area"] == float(p["width"] * p["height"])


# ---------------------------------------------------------------------------
# 6. Profile switching updates scene dimensions
# ---------------------------------------------------------------------------


def test_profile_switch_updates_scene_dims():
    designer = UIDesigner(128, 64)
    designer.create_scene("main")
    designer.set_hardware_profile("oled_128x64")
    assert designer.scenes["main"].width == 128
    assert designer.scenes["main"].height == 64

    designer.set_hardware_profile("tft_320x240")
    assert designer.scenes["main"].width == 320
    assert designer.scenes["main"].height == 240

    designer.set_hardware_profile("oled_72x40")
    assert designer.scenes["main"].width == 72
    assert designer.scenes["main"].height == 40


# ---------------------------------------------------------------------------
# 7. PROFILE_ORDER matches HARDWARE_PROFILES keys
# ---------------------------------------------------------------------------


def test_profile_order_keys_valid():
    for key in PROFILE_ORDER:
        assert key in HARDWARE_PROFILES, f"PROFILE_ORDER key '{key}' not in HARDWARE_PROFILES"


def test_all_profiles_in_order():
    missing = set(ALL_PROFILES) - set(PROFILE_ORDER)
    assert not missing, f"profiles not in PROFILE_ORDER: {missing}"


# ---------------------------------------------------------------------------
# 8. Widget rendering at each resolution
# ---------------------------------------------------------------------------

_RENDER_PROFILES = [
    "oled_128x64",
    "oled_128x32",
    "oled_72x40",
    "oled_128x128_sh1107",
    "oled_256x64_ssd1322",
    "esp32os_256x128_gray4",
    "tft_160x128_st7735",
    "tft_240x135_st7789",
    "tft_320x240",
    "tft_480x320",
]


@pytest.mark.parametrize("key", _RENDER_PROFILES)
def test_widget_renders_at_profile_resolution(key, tmp_path, monkeypatch):
    """Render a label and button at each profile's resolution, verify pixels."""
    p = HARDWARE_PROFILES[key]
    app = _make_app(tmp_path, monkeypatch)
    surf_w = max(p["width"], 64)
    surf_h = max(p["height"], 32)
    surf = pygame.Surface((surf_w, surf_h))
    surf.fill(BG_COLOR)

    # Fit widget inside profile bounds
    ww = min(60, p["width"] - 4)
    wh = min(20, p["height"] - 4)
    w = WidgetConfig(
        type="label",
        x=2,
        y=2,
        width=ww,
        height=wh,
        text="TEST",
        color_fg="#f0f0f0",
        color_bg="black",
        border=True,
        border_style="single",
    )
    rect = pygame.Rect(2, 2, ww, wh)
    drawing.draw_widget_preview(app, surf, w, rect, BG_COLOR, 2, False)
    # Check that some pixels were drawn
    has_pixels = False
    for x in range(rect.left, min(rect.right, surf_w)):
        for y in range(rect.top, min(rect.bottom, surf_h)):
            if surf.get_at((x, y))[:3] != BG_COLOR:
                has_pixels = True
                break
        if has_pixels:
            break
    assert has_pixels, f"no pixels drawn for profile '{key}' at {p['width']}x{p['height']}"


# ---------------------------------------------------------------------------
# 9. Validation adapts to profile bounds
# ---------------------------------------------------------------------------

_SMALL_PROFILES = ["oled_72x40", "oled_128x32", "oled_128x64"]
_LARGE_PROFILES = ["tft_320x240", "tft_480x320"]


@pytest.mark.parametrize("key", _SMALL_PROFILES)
def test_validation_catches_out_of_bounds_small(key):
    """Placing a large widget in a small profile should trigger a warning."""
    p = HARDWARE_PROFILES[key]
    data = {
        "scenes": {
            "main": {
                "width": p["width"],
                "height": p["height"],
                "widgets": [
                    {
                        "type": "label",
                        "x": 0,
                        "y": 0,
                        "width": p["width"] + 10,
                        "height": p["height"] + 10,
                        "text": "big",
                    }
                ],
            }
        }
    }
    issues = validate_data(data, file_label="test", warnings_as_errors=False)
    out_of_bounds = [i for i in issues if "out of bounds" in i.message.lower()]
    assert out_of_bounds, f"expected out-of-bounds warning for oversized widget in {key}"


@pytest.mark.parametrize("key", _LARGE_PROFILES)
def test_validation_passes_for_fitting_widget(key):
    p = HARDWARE_PROFILES[key]
    data = {
        "scenes": {
            "main": {
                "width": p["width"],
                "height": p["height"],
                "widgets": [
                    {
                        "type": "button",
                        "x": 10,
                        "y": 10,
                        "width": 80,
                        "height": 30,
                        "text": "OK",
                        "border": True,
                        "border_style": "single",
                    }
                ],
            }
        }
    }
    issues = validate_data(data, file_label="test", warnings_as_errors=False)
    errors = [i for i in issues if i.severity == "ERROR"]
    assert not errors, f"unexpected errors for profile {key}: {errors}"


# ---------------------------------------------------------------------------
# 10. Resource estimation with widgets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ALL_PROFILES)
def test_estimation_with_widgets(key):
    """Add some widgets to a scene and verify estimation reflects them."""
    p = HARDWARE_PROFILES[key]
    designer = UIDesigner(p["width"], p["height"])
    designer.create_scene("main")
    designer.set_hardware_profile(key)
    sc = designer.scenes["main"]
    # Add a few widgets fitting inside bounds
    ww = min(40, p["width"])
    wh = min(12, p["height"])
    for i in range(3):
        sc.widgets.append(
            WidgetConfig(type="label", x=0, y=i * wh, width=ww, height=wh, text=f"W{i}")
        )
    est = designer.estimate_resources()
    assert est["widgets"] == 3.0
    assert est["text_bytes"] > 0
    assert est["widget_bytes"] == 128 * 3


# ---------------------------------------------------------------------------
# 11. Tiny display specific edge cases
# ---------------------------------------------------------------------------


def test_oled_72x40_fits_minimum_widget():
    """The smallest OLED should still fit at least a 1x1 widget."""
    designer = UIDesigner(72, 40)
    designer.create_scene("main")
    designer.set_hardware_profile("oled_72x40")
    sc = designer.scenes["main"]
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=1, height=1))
    est = designer.estimate_resources()
    assert est["fb_over"] == 0.0


def test_tiny_oled_framebuffer_sizes():
    """Verify exact framebuffer sizes for tiny monochrome OLEDs."""
    cases = [
        ("oled_128x64", (128 * 64 + 7) // 8),  # 1024 bytes
        ("oled_128x32", (128 * 32 + 7) // 8),  # 512 bytes
        ("oled_72x40", (72 * 40 + 7) // 8),  # 360 bytes
        ("oled_128x128_sh1107", (128 * 128 + 7) // 8),  # 2048 bytes
    ]
    for key, expected_fb in cases:
        p = HARDWARE_PROFILES[key]
        assert _fb_bytes_expected(p["width"], p["height"], p["color_depth"]) == expected_fb


# ---------------------------------------------------------------------------
# 12. 4bpp grayscale specific
# ---------------------------------------------------------------------------


def test_4bpp_framebuffer_is_half_area():
    """4-bit grayscale: 2 pixels per byte → fb = area/2."""
    for key in ("esp32os_256x128_gray4", "oled_256x64_ssd1322"):
        p = HARDWARE_PROFILES[key]
        fb = _fb_bytes_expected(p["width"], p["height"], 4)
        assert fb == (p["width"] * p["height"]) // 2


# ---------------------------------------------------------------------------
# 13. 16bpp RGB565 specific
# ---------------------------------------------------------------------------


def test_16bpp_framebuffer_is_double_area():
    """16-bit RGB565: 2 bytes per pixel → fb = area*2."""
    rgb_profiles = [k for k in ALL_PROFILES if HARDWARE_PROFILES[k]["color_depth"] == 16]
    assert len(rgb_profiles) >= 5, "expected at least 5 RGB565 profiles"
    for key in rgb_profiles:
        p = HARDWARE_PROFILES[key]
        fb = _fb_bytes_expected(p["width"], p["height"], 16)
        assert fb == p["width"] * p["height"] * 2


# ---------------------------------------------------------------------------
# 14. CyberpunkEditorApp profile initialization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["oled_128x64", "esp32os_256x128_gray4", "tft_320x240"])
def test_app_init_with_profile(key, tmp_path, monkeypatch):
    """App initialized with profile should use that profile's dimensions."""
    p = HARDWARE_PROFILES[key]
    app = _make_app(tmp_path, monkeypatch, profile=key)
    assert app.designer.width == p["width"]
    assert app.designer.height == p["height"]


# ---------------------------------------------------------------------------
# 15. Overlap detection scales with display size
# ---------------------------------------------------------------------------


def test_overlap_detection_on_large_display():
    p = HARDWARE_PROFILES["tft_480x320"]
    designer = UIDesigner(p["width"], p["height"])
    designer.create_scene("main")
    sc = designer.scenes["main"]
    # Non-overlapping widgets
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=100, height=50))
    sc.widgets.append(WidgetConfig(type="box", x=200, y=100, width=100, height=50))
    est = designer.estimate_resources()
    assert est["overlaps"] == 0.0

    # Overlapping widgets
    sc.widgets.append(WidgetConfig(type="box", x=50, y=25, width=100, height=50))
    est2 = designer.estimate_resources()
    assert est2["overlaps"] >= 1.0


def test_overlap_detection_on_tiny_display():
    p = HARDWARE_PROFILES["oled_72x40"]
    designer = UIDesigner(p["width"], p["height"])
    designer.create_scene("main")
    sc = designer.scenes["main"]
    # Two widgets that overlap in the small space
    sc.widgets.append(WidgetConfig(type="box", x=0, y=0, width=40, height=20))
    sc.widgets.append(WidgetConfig(type="box", x=20, y=10, width=40, height=20))
    est = designer.estimate_resources()
    assert est["overlaps"] >= 1.0
