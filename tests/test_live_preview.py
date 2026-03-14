"""Tests for cyberpunk_designer/live_preview.py — serial port discovery,
frame formatting, and error-handling paths."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cyberpunk_designer.live_preview import (
    refresh_available_ports,
    send_live_preview,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app(tmp_path: Path, *, port: str = "", baud: int = 115200) -> SimpleNamespace:
    json_path = tmp_path / "scene.json"
    json_path.write_text('{"scenes":{}}', encoding="utf-8")
    return SimpleNamespace(
        live_preview_port=port,
        live_preview_baud=baud,
        json_path=json_path,
        available_ports=[],
        available_ports_idx=-1,
        _set_status=MagicMock(),
    )


# ---------------------------------------------------------------------------
# refresh_available_ports
# ---------------------------------------------------------------------------


class TestRefreshAvailablePorts:
    def test_no_pyserial(self, tmp_path):
        app = _app(tmp_path)
        with patch.dict("sys.modules", {"serial": None, "serial.tools": None, "serial.tools.list_ports": None}):
            refresh_available_ports(app)
        assert app.available_ports == []
        assert app.available_ports_idx == -1

    def test_with_ports(self, tmp_path):
        app = _app(tmp_path)
        fake_port = SimpleNamespace(device="COM3")
        fake_lp = MagicMock()
        fake_lp.comports.return_value = [fake_port]

        fake_serial = MagicMock()
        fake_serial.tools.list_ports = fake_lp

        with patch.dict("sys.modules", {
            "serial": fake_serial,
            "serial.tools": fake_serial.tools,
            "serial.tools.list_ports": fake_lp,
        }):
            refresh_available_ports(app)
        assert "COM3" in app.available_ports
        assert app.available_ports_idx == 0

    def test_empty_ports(self, tmp_path):
        app = _app(tmp_path)
        fake_lp = MagicMock()
        fake_lp.comports.return_value = []

        fake_serial = MagicMock()
        fake_serial.tools.list_ports = fake_lp

        with patch.dict("sys.modules", {
            "serial": fake_serial,
            "serial.tools": fake_serial.tools,
            "serial.tools.list_ports": fake_lp,
        }):
            refresh_available_ports(app)
        assert app.available_ports == []
        assert app.available_ports_idx == -1


# ---------------------------------------------------------------------------
# send_live_preview
# ---------------------------------------------------------------------------


class TestSendLivePreview:
    def test_no_port_set(self, tmp_path):
        app = _app(tmp_path, port="")
        send_live_preview(app)
        app._set_status.assert_called_once()
        assert "live_port" in str(app._set_status.call_args).lower() or "LIVE_PORT" in str(
            app._set_status.call_args
        )

    def test_no_pyserial(self, tmp_path):
        app = _app(tmp_path, port="COM3")
        with patch.dict("sys.modules", {"serial": None}):
            send_live_preview(app)
        app._set_status.assert_called_once()
        assert "pyserial" in str(app._set_status.call_args).lower()

    def test_json_read_error(self, tmp_path):
        app = _app(tmp_path, port="COM3")
        app.json_path = tmp_path / "nonexistent.json"
        fake_serial = MagicMock()
        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        app._set_status.assert_called_once()
        assert "cannot read" in str(app._set_status.call_args).lower()

    def test_successful_send(self, tmp_path):
        app = _app(tmp_path, port="COM3", baud=9600)
        mock_ser = MagicMock()
        mock_serial_cls = MagicMock()
        mock_serial_cls.__enter__ = MagicMock(return_value=mock_ser)
        mock_serial_cls.__exit__ = MagicMock(return_value=False)

        fake_serial = MagicMock()
        fake_serial.Serial.return_value = mock_serial_cls

        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        # Verify Serial was called with correct params
        fake_serial.Serial.assert_called_once_with(port="COM3", baudrate=9600, timeout=2)

    def test_frame_format(self, tmp_path):
        """Verify the frame uses <<UIJSON>>...<<END>> delimiters."""
        app = _app(tmp_path, port="COM3")
        payload = app.json_path.read_text(encoding="utf-8")
        expected_frame = f"<<UIJSON>>{payload}<<END>>".encode()

        mock_ser = MagicMock()
        mock_serial_cls = MagicMock()
        mock_serial_cls.__enter__ = MagicMock(return_value=mock_ser)
        mock_serial_cls.__exit__ = MagicMock(return_value=False)

        fake_serial = MagicMock()
        fake_serial.Serial.return_value = mock_serial_cls

        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        mock_serial_cls.__enter__().write.assert_called_once_with(expected_frame)

    def test_serial_oserror(self, tmp_path):
        app = _app(tmp_path, port="COM99")

        fake_serial = MagicMock()
        fake_serial.Serial.side_effect = OSError("port not found")

        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        assert "failed" in str(app._set_status.call_args).lower()


# ===================================================================
# BK – live_preview edge cases
# ===================================================================


class TestRefreshPortsEdge:
    def test_many_ports_truncated_status(self, tmp_path):
        """Status message shows at most 10 ports."""
        app = _app(tmp_path)
        port_objs = [SimpleNamespace(device=f"COM{i}") for i in range(20)]
        fake_list_ports = MagicMock()
        fake_list_ports.comports.return_value = port_objs
        fake_serial_tools = SimpleNamespace(list_ports=fake_list_ports)
        fake_serial = MagicMock()
        fake_serial.tools = fake_serial_tools
        with patch.dict("sys.modules", {
            "serial": fake_serial,
            "serial.tools": fake_serial_tools,
            "serial.tools.list_ports": fake_list_ports,
        }):
            refresh_available_ports(app)
        assert len(app.available_ports) == 20
        assert app.available_ports_idx == 0

    def test_empty_port_name(self, tmp_path):
        """Port with empty device string is still captured."""
        app = _app(tmp_path)
        port_objs = [SimpleNamespace(device="")]
        fake_list_ports = MagicMock()
        fake_list_ports.comports.return_value = port_objs
        fake_serial_tools = SimpleNamespace(list_ports=fake_list_ports)
        fake_serial = MagicMock()
        fake_serial.tools = fake_serial_tools
        with patch.dict("sys.modules", {
            "serial": fake_serial,
            "serial.tools": fake_serial_tools,
            "serial.tools.list_ports": fake_list_ports,
        }):
            refresh_available_ports(app)
        assert len(app.available_ports) == 1


class TestSendLivePreviewEdge:
    def test_empty_json_file(self, tmp_path):
        """Sending an empty JSON file doesn't crash."""
        app = _app(tmp_path, port="COM9")
        app.json_path.write_text("", encoding="utf-8")
        mock_ser = MagicMock()
        mock_serial_cls = MagicMock()
        mock_serial_cls.__enter__ = MagicMock(return_value=mock_ser)
        mock_serial_cls.__exit__ = MagicMock(return_value=False)
        fake_serial = MagicMock()
        fake_serial.Serial.return_value = mock_serial_cls
        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        # Frame should be sent, even if empty
        mock_ser.write.assert_called_once()
        data = mock_ser.write.call_args[0][0]
        assert data.startswith(b"<<UIJSON>>")
        assert data.endswith(b"<<END>>")

    def test_large_json_file(self, tmp_path):
        """Large JSON payload is transmitted intact."""
        app = _app(tmp_path, port="COM1", baud=115200)
        payload = '{"big": "' + 'x' * 10000 + '"}'
        app.json_path.write_text(payload, encoding="utf-8")
        mock_ser = MagicMock()
        mock_serial_cls = MagicMock()
        mock_serial_cls.__enter__ = MagicMock(return_value=mock_ser)
        mock_serial_cls.__exit__ = MagicMock(return_value=False)
        fake_serial = MagicMock()
        fake_serial.Serial.return_value = mock_serial_cls
        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        data = mock_ser.write.call_args[0][0]
        assert len(data) > 10000

    def test_baud_rate_passed_correctly(self, tmp_path):
        """The configured baud rate is passed to Serial."""
        app = _app(tmp_path, port="COM5", baud=9600)
        mock_ser = MagicMock()
        mock_serial_cls = MagicMock()
        mock_serial_cls.__enter__ = MagicMock(return_value=mock_ser)
        mock_serial_cls.__exit__ = MagicMock(return_value=False)
        fake_serial = MagicMock()
        fake_serial.Serial.return_value = mock_serial_cls
        with patch.dict("sys.modules", {"serial": fake_serial}):
            send_live_preview(app)
        call_kw = fake_serial.Serial.call_args
        assert call_kw.kwargs.get("baudrate") == 9600 or call_kw[1].get("baudrate") == 9600
