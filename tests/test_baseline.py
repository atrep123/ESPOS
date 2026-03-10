import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_models import _make_baseline


@pytest.mark.parametrize(
    "w,h,bw,bh,expected_w,expected_h",
    [
        (None, None, None, None, 0, 0),
        (5, None, 10, 12, 5, 0),
        (None, 7, 10, 12, 0, 7),
        (3, 4, None, None, 3, 4),
    ],
)
def test_make_baseline_optional_dims(w, h, bw, bh, expected_w, expected_h):
    b = _make_baseline(1, 2, w, h, bw, bh)
    assert b["x"] == 1
    assert b["y"] == 2
    assert b["width"] == expected_w
    assert b["height"] == expected_h
