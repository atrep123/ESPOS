# type: ignore # noqa: F821
try:
    import time
except ImportError:
    time = None

_prop_lines = prop_tx.fire_burst_lines(${colors})
for _prop_index, _prop_line in enumerate(_prop_lines):
    prop_uart.write(_prop_line)
    if _prop_index + 1 < len(_prop_lines):
        if time is None or not hasattr(time, "sleep_ms"):
            raise RuntimeError("time.sleep_ms is required for Prop FIRE burst timing")
        time.sleep_ms(prop_frame.FIRE_BURST_GAP_MS)
