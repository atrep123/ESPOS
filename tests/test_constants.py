import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import constants


def test_numeric_constants():
    assert constants.GRID_SIZE_SMALL == 4
    assert constants.GRID_SIZE_MEDIUM == 8
    assert constants.GRID_SIZE_LARGE == 16
    assert constants.DEFAULT_WIDGET_WIDTH == 10
    assert constants.DEFAULT_WIDGET_HEIGHT == 10
    assert constants.DEFAULT_WIDGET_SIZE == 10
    assert constants.MIN_WIDGET_SIZE == 1
    assert constants.MAX_WIDGET_SIZE == 1000


def test_path_constants():
    assert constants.ESP32_CONFIG_DIR == ".esp32os"
    assert constants.BACKUP_DIR_NAME == "designer_backups"
    assert constants.ESP32OS_DIR == Path.home() / ".esp32os"
    assert constants.BACKUP_DIR == constants.ESP32OS_DIR / "designer_backups"
