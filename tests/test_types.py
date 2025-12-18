import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_models import WidgetConfig, _coerce_int, _make_baseline


@pytest.mark.parametrize("value,expected", [(None, 0), ("3", 3), (-2, -2), (True, 1)])
def test_coerce_int_handles_optional(value, expected):
    assert _coerce_int(value) == expected


@pytest.mark.parametrize("width,height", [(10, 10), (0, 0), (None, None)])
def test_make_baseline_accepts_optional(width, height):
    b = _make_baseline(1, 2, width, height, None, None)
    assert b["x"] == 1
    assert b["y"] == 2
    assert b["width"] >= 0
    assert b["height"] >= 0


@pytest.mark.parametrize("w,h", [(10, 10), (1, 1), (None, None)])
def test_widget_config_defaults(w, h):
    cfg = WidgetConfig(type="box", x=0, y=0, width=w, height=h)
    assert cfg.width >= 1
    assert cfg.height >= 1
