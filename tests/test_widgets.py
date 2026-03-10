import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui_models import WidgetConfig


@pytest.mark.parametrize(
    "wtype",
    [
        "label",
        "button",
        "panel",
        "progressbar",
        "gauge",
        "slider",
        "chart",
        "checkbox",
        "textbox",
        "icon",
    ],
)
def test_widget_types_construct(wtype):
    cfg = WidgetConfig(type=wtype, x=0, y=0, width=5, height=5)
    assert cfg.type == wtype
    assert cfg.width >= 1 and cfg.height >= 1
