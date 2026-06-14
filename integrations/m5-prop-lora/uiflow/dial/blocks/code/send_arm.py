# type: ignore # noqa: F821
for line in prop_tx.arm_lines():
    prop_uart.write(line)
