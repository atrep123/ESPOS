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
    assert Path.home() / ".esp32os" == constants.ESP32OS_DIR
    assert constants.BACKUP_DIR == constants.ESP32OS_DIR / "designer_backups"


def test_path_constants_types_and_structure():
    """Ensure path constants are strings/Paths (kills None-replacement mutants)."""
    assert isinstance(constants.ESP32_CONFIG_DIR, str)
    assert isinstance(constants.BACKUP_DIR_NAME, str)
    assert isinstance(constants.ESP32OS_DIR, Path)
    assert isinstance(constants.BACKUP_DIR, Path)
    # Structural: ESP32OS_DIR contains ESP32_CONFIG_DIR, BACKUP_DIR contains BACKUP_DIR_NAME
    assert constants.ESP32_CONFIG_DIR in str(constants.ESP32OS_DIR)
    assert constants.BACKUP_DIR_NAME in str(constants.BACKUP_DIR)
    # Path division, not multiplication
    assert constants.ESP32OS_DIR.name == constants.ESP32_CONFIG_DIR
    assert constants.BACKUP_DIR.name == constants.BACKUP_DIR_NAME
