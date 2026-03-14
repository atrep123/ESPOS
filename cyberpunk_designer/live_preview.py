"""Serial live preview to ESP32 hardware."""

from __future__ import annotations

from typing import List


def open_live_dialog(app) -> None:
    """Send a framed UI JSON to ESP32 (best-effort) using configured port."""
    send_live_preview(app)
    return None


def refresh_available_ports(app) -> None:
    """Best-effort serial port discovery (optional: requires pyserial)."""
    ports: List[str] = []
    try:
        from serial.tools import list_ports  # type: ignore

        ports = [str(p.device) for p in list_ports.comports()]
    except (ImportError, ModuleNotFoundError):
        ports = []
    app.available_ports = ports
    app.available_ports_idx = 0 if ports else -1
    if ports:
        msg = ", ".join(ports[:10])
        app._set_status(f"Ports: {msg}", ttl_sec=6.0)
        print(f"[INFO] Serial ports: {msg}")
    else:
        app._set_status("No serial ports found (or pyserial missing).", ttl_sec=6.0)
        print("[INFO] No serial ports found (or pyserial missing).")


def send_live_preview(app) -> None:
    """Send live preview."""
    if not app.live_preview_port:
        app._set_status("Live preview: set ESP32OS_LIVE_PORT (or prefs live_port).", ttl_sec=6.0)
        return
    try:
        import serial  # type: ignore
    except (ImportError, ModuleNotFoundError):
        app._set_status("Live preview: pyserial missing.", ttl_sec=6.0)
        return
    try:
        payload = app.json_path.read_text(encoding="utf-8")
    except OSError as exc:
        app._set_status(f"Live preview: cannot read JSON ({exc})", ttl_sec=6.0)
        return
    frame = f"<<UIJSON>>{payload}<<END>>".encode()
    try:
        with serial.Serial(
            port=app.live_preview_port, baudrate=int(app.live_preview_baud), timeout=2
        ) as ser:
            ser.write(frame)
            ser.flush()
        app._set_status(
            f"Live preview sent to {app.live_preview_port}@{app.live_preview_baud}",
            ttl_sec=5.0,
        )
    except OSError as exc:
        app._set_status(f"Live preview failed: {exc}", ttl_sec=6.0)
