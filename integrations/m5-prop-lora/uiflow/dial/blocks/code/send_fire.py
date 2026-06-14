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
    raise RuntimeError("time.sleep_ms or time.sleep is required for Prop FIRE burst timing")

_prop_lines = prop_tx.fire_burst_lines(${colors})
for _prop_index, _prop_line in enumerate(_prop_lines):
    prop_uart.write(_prop_line)
    if _prop_index + 1 < len(_prop_lines):
        # Keep redundant FIRE copies spaced by the protocol constant; the
        # receiver dedups them by sequence, but the modem still needs air gap.
        _prop_delay_ms(prop_frame.FIRE_BURST_GAP_MS)
