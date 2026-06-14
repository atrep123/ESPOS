# type: ignore # noqa: F821
((lambda _data: _data if isinstance(_data, str) else (_data or b"").decode("utf-8", "ignore"))(prop_uart.read()) if prop_uart.any() else "")
