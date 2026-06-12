# type: ignore # noqa: F821
try:
    import time
except ImportError:
    time = None

_prop_lines = prop_tx.fire_burst_lines(${colors})
for _prop_index, _prop_line in enumerate(_prop_lines):
    prop_uart.write(_prop_line)
    if _prop_index + 1 < len(_prop_lines):
        # Keep redundant FIRE copies spaced by the protocol constant; the
        # receiver dedups them by sequence, but the modem still needs air gap.
        if time is not None and hasattr(time, "sleep_ms"):
            time.sleep_ms(prop_frame.FIRE_BURST_GAP_MS)
        elif time is not None and hasattr(time, "sleep"):
            time.sleep(prop_frame.FIRE_BURST_GAP_MS / 1000)
        else:
            raise RuntimeError("time.sleep_ms or time.sleep is required for Prop FIRE burst timing")
