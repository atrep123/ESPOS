from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UIFLOW = ROOT / "uiflow" / "dial"
TEST_PROP_KEY_HEX = "00112233445566778899aabbccddeeff"


class FakeTime:
    def __init__(self) -> None:
        self.now = 0
        self.sleeps: list[int] = []

    def ticks_ms(self) -> int:
        self.now += 10
        return self.now

    def ticks_add(self, value: int, delta: int) -> int:
        return value + delta

    def ticks_diff(self, end: int, start: int) -> int:
        return end - start

    def sleep_ms(self, value: int) -> None:
        self.sleeps.append(value)
        self.now += value


class FakeSleepOnlyTime:
    def __init__(self) -> None:
        self.sleeps: list[float] = []

    def sleep(self, value: float) -> None:
        self.sleeps.append(value)


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


def load_uiflow_main(monkeypatch, prop_key=True):
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
    if prop_key:
        monkeypatch.setitem(
            sys.modules,
            "prop_key",
            types.SimpleNamespace(
                SHARED_KEY_HEX=TEST_PROP_KEY_HEX,
                ALLOW_PROTOTYPE_SHARED_KEY=True,
            ),
        )
    else:
        monkeypatch.delitem(sys.modules, "prop_key", raising=False)
    monkeypatch.delitem(sys.modules, "prop_frame", raising=False)
    monkeypatch.syspath_prepend(str(ROOT))
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


def test_setup_surfaces_missing_prop_key_without_import_crash(monkeypatch):
    app = load_uiflow_main(monkeypatch, prop_key=False)

    app.setup()
    app.send_current_action()

    assert app.tx is None
    assert app._status == "KEY MISSING"
    assert FakeUART.instances == []


def test_loop_surfaces_missing_prop_key_during_button_input(monkeypatch):
    app = load_uiflow_main(monkeypatch, prop_key=False)
    clicked = [True]
    app.M5.BtnA = types.SimpleNamespace(
        wasHold=lambda: False,
        wasClicked=lambda: clicked.pop() if clicked else False,
    )

    app.setup()
    app.loop()

    assert app.tx is None
    assert app.uart is None
    assert app._status == "KEY MISSING"
    assert FakeUART.instances == []


def test_first_action_send_uses_initialized_sender(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    uart.writes.clear()

    app.send_current_action()

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
    frame_lines = [
        line for line in uart.writes if isinstance(line, str) and line.startswith("FF ")
    ]
    assert len(frame_lines) == 1
    frame = proto.decode_frame(
        bytes.fromhex(frame_lines[0].split(" ", 1)[1].strip()), keys
    )
    assert frame.frame_type == proto.FrameType.PREVIEW
    assert app._status != "TX FAIL"


def test_command_actions_use_four_led_frames_and_do_not_expose_remote_led(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    app._colors = [
        (1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        (10, 11, 12),
        (13, 14, 15),
    ]

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}

    assert app.ACTIONS == ("NAHLED", "ARM", "ODPAL", "STOP")
    assert not hasattr(app, "A_LED3")
    assert not hasattr(app, "A_LED5")

    uart.writes.clear()
    app._action = app.A_PREVIEW
    app.send_current_action()
    preview_lines = [
        line for line in uart.writes if isinstance(line, str) and line.startswith("FF ")
    ]
    preview = proto.decode_frame(
        bytes.fromhex(preview_lines[0].split(" ", 1)[1].strip()), keys
    )
    assert proto.parse_led_payload(bytes(preview.payload))["colors"] == app._colors[:4]

    uart.writes.clear()
    app._action = app.A_ODPAL
    app.send_current_action()
    fire_lines = [
        line for line in uart.writes if isinstance(line, str) and line.startswith("FF ")
    ]
    fire_frames = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in fire_lines
    ]
    assert [frame.frame_type for frame in fire_frames] == [proto.FrameType.FIRE] * 3
    assert all(
        proto.parse_led_payload(bytes(frame.payload))["colors"] == app._colors[:4]
        for frame in fire_frames
    )


def test_hold_keeps_uiflow_dial_setup_on_terminal(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    uart.writes.clear()

    app.on_hold()

    assert app._mode == app.MODE_CMD
    assert app._status == "SETUP NA TERMINALU"
    assert uart.writes == []


def test_fire_action_uses_redundant_ff_burst(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    uart.writes.clear()
    app.time.sleeps.clear()
    app._action = app.A_ODPAL

    app.send_current_action()

    fire_lines = [
        line for line in uart.writes if isinstance(line, str) and line.startswith("FF ")
    ]
    assert len(fire_lines) == 3
    assert len(set(fire_lines)) == 1

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
    decoded = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in fire_lines
    ]
    assert [frame.frame_type for frame in decoded] == [proto.FrameType.FIRE] * 3
    assert decoded[0].sequence == decoded[1].sequence == decoded[2].sequence
    assert decoded[0].nonce == decoded[1].nonce == decoded[2].nonce
    assert not any(line.startswith("SEND ") for line in uart.writes)
    assert app.time.sleeps[:3] == [0, app.pf.FIRE_BURST_GAP_MS, app.pf.FIRE_BURST_GAP_MS]
    assert app.time.sleeps.count(app.pf.FIRE_BURST_GAP_MS) == 2


def test_stop_action_retries_same_send_frame_without_ack(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    app.setup()
    uart = FakeUART.instances[-1]
    uart.writes.clear()
    app.time.sleeps.clear()
    app._action = app.A_STOP

    app.send_current_action()

    stop_lines = [
        line for line in uart.writes if isinstance(line, str) and line.startswith("SEND ")
    ]
    assert len(stop_lines) == app.pf.STOP_RETRY_COPIES
    assert len(set(stop_lines)) == 1
    assert app.time.sleeps.count(app.pf.STOP_RETRY_GAP_MS) == app.pf.STOP_RETRY_COPIES - 1

    from shared.protocol import protocol as proto

    keys = {1: bytes.fromhex("00112233445566778899aabbccddeeff")}
    decoded = [
        proto.decode_frame(bytes.fromhex(line.split(" ", 1)[1].strip()), keys)
        for line in stop_lines
    ]
    assert [frame.frame_type for frame in decoded] == [proto.FrameType.STOP] * app.pf.STOP_RETRY_COPIES
    assert decoded[0].sequence == decoded[1].sequence == decoded[2].sequence
    assert decoded[0].nonce == decoded[1].nonce == decoded[2].nonce


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


def test_delay_ms_falls_back_to_seconds_sleep(monkeypatch):
    app = load_uiflow_main(monkeypatch)
    fake_time = FakeSleepOnlyTime()
    app.time = fake_time

    app.delay_ms(25)

    assert fake_time.sleeps == [0.025]
