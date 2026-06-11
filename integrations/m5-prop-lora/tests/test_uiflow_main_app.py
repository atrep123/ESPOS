from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UIFLOW = ROOT / "uiflow" / "dial"


class FakeTime:
    def __init__(self) -> None:
        self.now = 0

    def ticks_ms(self) -> int:
        self.now += 10
        return self.now

    def ticks_add(self, value: int, delta: int) -> int:
        return value + delta

    def ticks_diff(self, end: int, start: int) -> int:
        return end - start

    def sleep_ms(self, value: int) -> None:
        self.now += value


class FakeLcd:
    def fillScreen(self, *_args) -> None:
        pass

    def drawCircle(self, *_args) -> None:
        pass

    def fillCircle(self, *_args) -> None:
        pass

    def setTextColor(self, *_args) -> None:
        pass

    def setTextSize(self, *_args) -> None:
        pass

    def drawCenterString(self, *_args) -> None:
        pass


class FakeUART:
    instances: list["FakeUART"] = []

    def __init__(self, *_args, **_kwargs) -> None:
        self.kwargs = _kwargs
        self.writes: list[str] = []
        self.lines = []
        FakeUART.instances.append(self)

    def write(self, data) -> None:
        if isinstance(data, bytes):
            data = data.decode("ascii")
        self.writes.append(data)

    def any(self) -> bool:
        return bool(self.lines)

    def readline(self):
        return self.lines.pop(0) if self.lines else None


class FakeRotary:
    def get_rotary_value(self) -> int:
        return 0


def load_uiflow_main(monkeypatch):
    fake_m5 = types.ModuleType("M5")
    fake_m5.Lcd = FakeLcd()
    fake_m5.Widgets = types.SimpleNamespace()
    fake_m5.BtnA = types.SimpleNamespace(wasHold=lambda: False, wasClicked=lambda: False)
    fake_m5.begin = lambda: None
    fake_m5.update = lambda: None

    fake_hardware = types.ModuleType("hardware")
    fake_hardware.UART = FakeUART
    fake_hardware.Rotary = FakeRotary

    monkeypatch.setitem(sys.modules, "M5", fake_m5)
    monkeypatch.setitem(sys.modules, "hardware", fake_hardware)
    monkeypatch.syspath_prepend(str(UIFLOW))
    FakeUART.instances.clear()

    module_name = "uiflow_dial_main_under_test"
    spec = importlib.util.spec_from_file_location(module_name, UIFLOW / "main.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.time = FakeTime()
    return module


def test_setup_initializes_prop_sender(monkeypatch):
    app = load_uiflow_main(monkeypatch)

    app.setup()

    assert isinstance(app.tx, app.pf.PropSender)


def test_first_action_send_uses_initialized_sender(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()

    app.send_current_action()

    uart = FakeUART.instances[-1]
    assert any(line.startswith("FF ") for line in uart.writes)
    assert app._status != "TX FAIL"


def test_drain_modem_accepts_str_uart_lines(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    uart.lines.append("OK ACK\n")

    seen = app.drain_modem(20)

    assert seen == "OK ACK"
    assert app._status == "OK"


def test_setup_configures_short_uart_timeout(monkeypatch):
    app = load_uiflow_main(monkeypatch)

    app.setup()

    uart = FakeUART.instances[-1]
    assert uart.kwargs["timeout"] <= 20
    assert uart.kwargs["timeout_char"] <= 5
