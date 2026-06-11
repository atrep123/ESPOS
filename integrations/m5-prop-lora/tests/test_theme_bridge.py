"""Regression tests for the M5 design -> firmware theme bridge.

The single source is tools/m5_theme.json; it feeds the Python render harnesses and
(via tools/gen_firmware_theme.py) the generated firmware headers. These tests guard
the bridge invariants: no header drift, no C++ token injection, no orphan editable
tokens, and apply_theme() is a no-op for the saved theme.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gen_firmware_theme as G  # noqa: E402
import preview_din_rx_render as DIN  # noqa: E402
import preview_prop_tx as DIAL  # noqa: E402

THEME = json.loads((TOOLS / "m5_theme.json").read_text(encoding="utf-8"))
DIN_HEADER = (ROOT / "firmware/din-rx/src/ui_theme_generated.h").read_text(encoding="utf-8")
DIAL_HEADER = (
    ROOT / "firmware/dial-tx/main/apps/app_prop_tx/gui/ui_theme_dial_generated.h"
).read_text(encoding="utf-8")


def test_generated_headers_in_sync():
    """Committed headers must match what the generator produces from the JSON."""
    assert G.main(["--check"]) == 0


def test_dinmeter_colors_emitted():
    for name, value in THEME["colors"].items():
        assert f"constexpr std::uint32_t {name} = {value};" in DIN_HEADER


def test_dinmeter_layout_emitted():
    for name, value in THEME["layout"].items():
        assert f"constexpr int {name} = {value};" in DIN_HEADER


def test_dial_colors_emitted_with_name_map():
    for name, value in THEME["dial"].items():
        fw = G.DIAL_NAME_EXCEPTIONS.get(name, name)
        assert f"constexpr std::uint32_t {fw} = {value};" in DIAL_HEADER


def test_no_orphan_dial_tokens():
    """Every editable dial token must reach firmware (no dead 'SURF'-class tokens)."""
    for name in THEME["dial"]:
        fw = G.DIAL_NAME_EXCEPTIONS.get(name, name)
        assert f"{fw} =" in DIAL_HEADER, f"dial token {name!r} not emitted to firmware"


def test_codegen_rejects_token_injection():
    """Safety: malformed names/values must never become C++ tokens."""
    for bad in ["x; evil()", "0 //", "DROP; --", "1+1", ""]:
        with pytest.raises(ValueError):
            G._check_name(bad)
    for bad in ["0xZZZZZZ", "0x12", "0x12; #x", "red", "#ff0000"]:
        with pytest.raises(ValueError):
            G._check_color(bad)


def test_apply_theme_noop_dinmeter():
    view, page = DIN.scenes()["main_firing"]
    h0 = hashlib.sha256(DIN.render(view, page, hires=True).tobytes()).hexdigest()
    DIN.apply_theme(THEME)  # the saved theme must not change the render
    h1 = hashlib.sha256(DIN.render(view, page, hires=True).tobytes()).hexdigest()
    assert h0 == h1


def test_apply_theme_noop_dial():
    view = DIAL.scenes()["03_armed"]
    h0 = hashlib.sha256(DIAL.render(view).tobytes()).hexdigest()
    DIAL.apply_theme(THEME["dial"])
    h1 = hashlib.sha256(DIAL.render(view).tobytes()).hexdigest()
    assert h0 == h1
