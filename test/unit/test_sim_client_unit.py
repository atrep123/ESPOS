#!/usr/bin/env python3
from esp32_sim_client import ESP32SimulatorClient


class DummyClient(ESP32SimulatorClient):
    """ESP32SimulatorClient subclass that records the last RPC message."""

    def __init__(self):
        super().__init__(host="127.0.0.1", port=0)
        self.sent = []
        self.connected = True
        self.socket = object()  # non-None sentinel

    def _send_rpc(self, message: dict) -> bool:  # type: ignore[override]
        self.sent.append(message)
        return True


def test_set_bg_hex_valid_rgb():
    c = DummyClient()
    assert c.set_bg_hex("FF0000") is True
    assert c.sent[-1]["rgb"] == [255, 0, 0]


def test_set_bg_hex_with_hash_prefix():
    c = DummyClient()
    assert c.set_bg_hex("#00FF00") is True
    assert c.sent[-1]["rgb"] == [0, 255, 0]


def test_set_bg_hex_invalid_string_returns_false():
    c = DummyClient()
    assert c.set_bg_hex("ZZZZZZ") is False
    # no new command should be appended on failure
    assert c.sent == []

