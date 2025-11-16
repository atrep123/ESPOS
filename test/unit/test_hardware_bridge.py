from __future__ import annotations

import socket
import threading
import time
from typing import Any, Callable, List, Protocol, cast

class _PytestMark(Protocol):
    def timeout(self, seconds: float | int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        ...

class _PytestModule(Protocol):
    mark: _PytestMark

class _MonkeyPatchProto(Protocol):
    def setattr(self, target: Any, name: str | None = None, value: Any | None = None, raising: bool = True) -> None:
        ...

try:
    import pytest as _pytest  # type: ignore[import-not-found]
    pytest = cast(_PytestModule, _pytest)
    MonkeyPatch = cast(type[_MonkeyPatchProto], getattr(_pytest, "MonkeyPatch", _MonkeyPatchProto))  # type: ignore
except Exception:
    class _DummyMark:
        def timeout(self, seconds: float | int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn
            return deco
    class _DummyPytest:
        mark: _PytestMark = _DummyMark()
    pytest = cast(_PytestModule, _DummyPytest())
    class MonkeyPatch(_MonkeyPatchProto):  # type: ignore
        def setattr(self, target: Any, name: str | None = None, value: Any | None = None, raising: bool = True) -> None:
            return None

from esp32_hardware_bridge import ESP32HardwareBridge, BridgeConfig


class FakeSerial:
    def __init__(self):
        self._buf: List[bytes] = []
        self.in_waiting: int = 0
        self.closed: bool = False

    def push_line(self, s: str) -> None:
        self._buf.append((s + "\n").encode("utf-8"))
        self.in_waiting = len(self._buf)

    def readline(self) -> bytes:
        if not self._buf:
            return b""
        b = self._buf.pop(0)
        self.in_waiting = len(self._buf)
        return b

    def write(self, data: bytes) -> int:
        # Accept writes; pretend success
        return len(data)

    def close(self) -> None:
        self.closed = True


class CaptureServer:
    def __init__(self):
        self._srv: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self.port: int = self._srv.getsockname()[1]
        self.received: List[str] = []
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def _run(self) -> None:
        conn, _ = self._srv.accept()
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                self.received.append(data.decode("utf-8"))


timeout = cast(Any, pytest.mark.timeout)


@timeout(5)
def test_bridge_sends_parsed_messages(monkeypatch: MonkeyPatch) -> None:
    # Arrange bridge with fake serial and capture server
    cap = CaptureServer()
    cfg = BridgeConfig(serial_port="FAKE", sim_rpc_port=cap.port)
    br = ESP32HardwareBridge(cfg)

    fake = FakeSerial()
    # Monkeypatch serial connection
    monkeypatch.setattr(br, "connect_serial", lambda: True)
    monkeypatch.setattr(br, "serial_conn", fake)

    # Connect to capture server
    assert br.connect_simulator() is True

    # Start workers
    br.running = True
    threading.Thread(target=br.hardware_reader_thread, daemon=True).start()
    threading.Thread(target=br.simulator_sender_thread, daemon=True).start()

    # Push a hardware line
    fake.push_line("SCENE 2")

    # Wait for send
    for _ in range(20):
        if cap.received:
            break
        time.sleep(0.05)

    br.stop()

    assert cap.received, "no data received by RPC server"
    # Should contain JSON with method scene and value 2
    payload = "".join(cap.received)
    assert "\"method\": \"scene\"" in payload
    assert "\"value\": 2" in payload
