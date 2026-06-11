# type: ignore # noqa: F821
global prop_uart, prop_tx, prop_frame, prop_ui
import prop_frame
import prop_ui
from hardware import UART
prop_uart = UART(1, baudrate=115200, bits=8, parity=None, stop=1, tx=${tx}, rx=${rx})
prop_uart.write('\n')
prop_tx = prop_frame.PropSender()
