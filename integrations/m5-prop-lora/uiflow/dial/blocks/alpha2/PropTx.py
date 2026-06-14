"""
file     PropTx
time     2026-06-10
author
email
license  MIT License
"""


def _remember_colors(instance, colors):
    incoming = list(colors)
    if len(incoming) == 4 and len(instance._colors) > 4:
        instance._colors = incoming + list(instance._colors[4:])
    else:
        instance._colors = incoming
    return incoming


def _first_four_for_frame(instance, colors):
    return _remember_colors(instance, colors)[:4]


DEFAULT_HUES = [0, 120, 240, 210, 60]


def _delay_ms_or_raise(message):
    delay_ms = None
    try:
        import time

        if hasattr(time, "sleep_ms"):
            delay_ms = time.sleep_ms
        elif hasattr(time, "sleep"):
            delay_ms = lambda ms: time.sleep(ms / 1000)
    except ImportError:
        delay_ms = None
    if delay_ms is None:
        raise RuntimeError(message)
    return delay_ms


class PropTx:
    """
    note:
        en: Prop TX UIFlow2 bridge for the authenticated prop_frame sender.
    details:
        color: '#2E9E72'
        link: https://github.com/atrep123/m5-prop-lora
        image: ''
        category: Custom
    example: ''
    """

    def __init__(self, tx: int = 13, rx: int = 15):
        """
        label:
            en: '%1 Prop init TX %2 RX %3'
        params:
            tx:
                name: tx
                type: int
                default: '13'
                field: number
                min: '0'
                max: '48'
            rx:
                name: rx
                type: int
                default: '15'
                field: number
                min: '0'
                max: '48'
        """
        import prop_frame
        import prop_ui
        from hardware import UART

        self._uart = UART(1, baudrate=115200, bits=8, parity=None, stop=1, tx=tx, rx=rx)
        self._tx = prop_frame.PropSender()
        self._prop_frame = prop_frame
        self._prop_ui = prop_ui
        self._colors = self.default_colors()
        self._armed = False
        self._uart.write("\n")

    def preview(self, colors):
        """
        label:
            en: 'Prop PREVIEW %1 colors %2'
        params:
            colors:
                name: colors
                type: list
        """
        self._uart.write(self._tx.preview_line(_first_four_for_frame(self, colors)))

    def fire(self, colors):
        """
        label:
            en: 'Prop ODPAL %1 colors %2'
        params:
            colors:
                name: colors
                type: list
        """
        if not self._armed:
            raise RuntimeError("Prop FIRE requires Prop ARM first")
        delay_ms = _delay_ms_or_raise(
            "time.sleep_ms or time.sleep is required for Prop FIRE burst timing"
        )
        lines = self._tx.fire_burst_lines(_first_four_for_frame(self, colors))
        for index, line in enumerate(lines):
            self._uart.write(line)
            # Keep redundant FIRE copies spaced by the protocol constant; the
            # receiver dedups them by sequence, but the modem still needs air gap.
            if index + 1 < len(lines):
                delay_ms(self._prop_frame.FIRE_BURST_GAP_MS)
        self._armed = False

    def stop(self):
        """
        label:
            en: 'Prop STOP %1'
        """
        delay_ms = _delay_ms_or_raise(
            "time.sleep_ms or time.sleep is required for Prop STOP retry timing"
        )
        lines = self._tx.stop_lines()
        for index, line in enumerate(lines):
            self._uart.write(line)
            if index + 1 < len(lines):
                delay_ms(self._prop_frame.STOP_RETRY_GAP_MS)
        self._armed = False

    def arm(self):
        """
        label:
            en: 'Prop ARM %1'
        """
        for line in self._tx.arm_lines():
            self._uart.write(line)
        self._armed = True

    def reply(self) -> str:
        """
        label:
            en: 'Prop reply %1'
        """
        if not self._uart.any():
            return ""
        data = self._uart.read() or b""
        if isinstance(data, str):
            return data
        try:
            return data.decode("utf-8", "ignore")
        except Exception:
            return ""

    def default_colors(self) -> list:
        """
        label:
            en: 'Prop default colors %1'
        """
        self._colors = self._prop_ui.palette_from_hues(DEFAULT_HUES)
        return list(self._colors)

    def first_four(self, colors) -> list:
        """
        label:
            en: 'Prop first four %1 colors %2'
        params:
            colors:
                name: colors
                type: list
        """
        return list(colors)[:4]

    def rgb_color(self, r: int = 255, g: int = 0, b: int = 0) -> tuple:
        """
        label:
            en: 'Prop RGB %1 R %2 G %3 B %4'
        params:
            r:
                name: r
                type: int
                default: '255'
                field: number
                min: '0'
                max: '255'
            g:
                name: g
                type: int
                default: '0'
                field: number
                min: '0'
                max: '255'
            b:
                name: b
                type: int
                default: '0'
                field: number
                min: '0'
                max: '255'
        """

        def clamp(value):
            return max(0, min(255, int(value)))

        return (clamp(r), clamp(g), clamp(b))

    def rgb888(self, color) -> int:
        """
        label:
            en: 'Prop RGB888 %1 color %2'
        params:
            color:
                name: color
                type: tuple
        """
        return self._prop_ui.rgb888(color)

