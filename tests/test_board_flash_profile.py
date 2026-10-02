"""Guard the generated S3 board env against flash-size drift."""

from pathlib import Path
import re

from board_registry import RegistryError, _coerce_board, load_registry

ROOT = Path(__file__).resolve().parents[1]


def _flash_size(config: Path) -> str:
    matches = re.findall(r'^CONFIG_ESPTOOLPY_FLASHSIZE="([^"]+)"$',
                         config.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(matches) == 1, f"{config.name}: expected exactly one configured flash size"
    return matches[0]


def test_reference_s3_board_pins_versioned_8mb_sdkconfig():
    board = load_registry().get("esp32-s3-devkitm-1")
    assert board is not None
    assert board.sdkconfig_path == "sdkconfig.esp32-s3-devkitm-1"
    assert _flash_size(ROOT / board.sdkconfig_path) == "8MB"


def test_generated_reference_s3_env_uses_pinned_sdkconfig():
    generated = load_registry().render_pio_block()
    assert (
        "board_build.esp-idf.sdkconfig_path = sdkconfig.esp32-s3-devkitm-1"
        in generated
    )


def test_registry_rejects_sdkconfig_escape_path():
    raw = {
        "id": "esp32-s3-devkitm-1",
        "label": "ESP32-S3 test board",
        "platform": "espressif32",
        "mcu": "ESP32-S3",
        "platformio_board": "esp32-s3-devkitm-1",
        "has_display": False,
        "display_profile": None,
        "sdkconfig_path": "../outside.sdkconfig",
    }
    try:
        _coerce_board(raw)
    except RegistryError as exc:
        assert "sdkconfig_path" in str(exc)
    else:
        raise AssertionError("registry accepted sdkconfig path outside the project")
