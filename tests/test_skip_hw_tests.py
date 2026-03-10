"""Tests for scripts/skip_hw_tests.py — ESP32 board detection and skip logic."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from skip_hw_tests import (
    ARDUINO_NANO_ESP32_PIDS,
    ARDUINO_VID,
    ESP32S3_PIDS,
    ESPRESSIF_VID,
    has_esp32s3,
    main,
)

# ===================================================================
# Constants
# ===================================================================


class TestConstants:
    def test_espressif_vid(self):
        assert ESPRESSIF_VID == 0x303A

    def test_esp32s3_pids(self):
        assert isinstance(ESP32S3_PIDS, list)
        assert len(ESP32S3_PIDS) > 0

    def test_arduino_vid(self):
        assert ARDUINO_VID == 0x2341

    def test_arduino_nano_pids(self):
        assert 0x0070 in ARDUINO_NANO_ESP32_PIDS


# ===================================================================
# has_esp32s3
# ===================================================================


def _make_port(vid=None, pid=None, description=""):
    return SimpleNamespace(vid=vid, pid=pid, description=description)


class TestHasEsp32s3:
    def test_no_devices(self, monkeypatch):
        import skip_hw_tests

        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: []))
        assert has_esp32s3() is False

    def test_espressif_vid_match(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=ESPRESSIF_VID, pid=ESP32S3_PIDS[0])
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_arduino_vid_match(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=ARDUINO_VID, pid=ARDUINO_NANO_ESP32_PIDS[0])
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_description_esp32s3(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0, pid=0, description="ESP32-S3 USB JTAG")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_description_espressif(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0, pid=0, description="Espressif Device")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_description_arduino_nano(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0, pid=0, description="Arduino Nano ESP32")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_description_nora(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0, pid=0, description="NORA-W306 Bluetooth")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True

    def test_unrelated_device(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0x1234, pid=0x5678, description="Generic Serial")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is False

    def test_list_ports_none(self, monkeypatch):
        import skip_hw_tests

        monkeypatch.setattr(skip_hw_tests, "list_ports", None)
        assert has_esp32s3() is False

    def test_usb_jtag_description(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=0, pid=0, description="USB JTAG serial debug")
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        assert has_esp32s3() is True


# ===================================================================
# main
# ===================================================================


class TestMain:
    def test_no_board_returns_zero(self, monkeypatch):
        import skip_hw_tests

        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: []))
        monkeypatch.setattr(sys, "argv", ["skip_hw_tests.py", "test"])
        assert main() == 0

    def test_board_present_returns_zero(self, monkeypatch):
        import skip_hw_tests

        port = _make_port(vid=ESPRESSIF_VID, pid=ESP32S3_PIDS[0])
        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: [port]))
        monkeypatch.setattr(sys, "argv", ["skip_hw_tests.py", "upload"])
        assert main() == 0

    def test_no_argv_uses_test(self, monkeypatch):
        import skip_hw_tests

        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: []))
        monkeypatch.setattr(sys, "argv", ["skip_hw_tests.py"])
        assert main() == 0

    def test_nohw_env_strips_suffix(self, monkeypatch, capsys):
        import skip_hw_tests

        monkeypatch.setattr(skip_hw_tests, "list_ports", SimpleNamespace(comports=lambda: []))
        monkeypatch.setenv("PIOENV", "esp32-s3-devkitm-1-nohw")
        monkeypatch.setattr(sys, "argv", ["skip_hw_tests.py"])
        main()
        out = capsys.readouterr().out
        assert "esp32-s3-devkitm-1" in out
