# type: ignore # noqa: F821
((prop_uart.read() or b"").decode("utf-8", "ignore") if prop_uart.any() else "")
