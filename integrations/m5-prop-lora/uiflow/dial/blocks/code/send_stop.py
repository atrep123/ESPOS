# type: ignore # noqa: F821
import prop_frame

try:
    import time
except ImportError:
    time = None

if time is not None and hasattr(time, "sleep_ms"):
    _prop_delay_ms = time.sleep_ms
elif time is not None and hasattr(time, "sleep"):
    _prop_delay_ms = lambda ms: time.sleep(ms / 1000)
else:
    raise RuntimeError("time.sleep_ms or time.sleep is required for Prop STOP retry timing")

_prop_lines = prop_tx.stop_lines()
for _prop_index, _prop_line in enumerate(_prop_lines):
    prop_uart.write(_prop_line)
    if _prop_index + 1 < len(_prop_lines):
        _prop_delay_ms(prop_frame.STOP_RETRY_GAP_MS)
