# type: ignore # noqa: F821
((prop_uart.read() or b'').decode() if prop_uart.any() else '')
