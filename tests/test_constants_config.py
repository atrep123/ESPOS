from pathlib import Path

from constants import BACKUP_DIR, DEFAULT_WIDGET_SIZE, ESP32OS_DIR
from ui_models import WidgetConfig


def test_constants_paths():
    assert Path.home() / ".esp32os" == ESP32OS_DIR
    assert BACKUP_DIR == ESP32OS_DIR / "designer_backups"


def test_default_widget_size_constant_applied():
    w = WidgetConfig(type="label", x=0, y=0, width=None, height=None)
    assert w.width == DEFAULT_WIDGET_SIZE
    assert w.height == DEFAULT_WIDGET_SIZE
    assert DEFAULT_WIDGET_SIZE >= 1
