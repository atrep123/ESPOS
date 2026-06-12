"""
file     PropTx
time     2026-06-10
author
email
license  MIT License
"""


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
        self._uart.write(self._tx.preview_line(colors))

    def fire(self, colors):
        """
        label:
            en: 'Prop ODPAL %1 colors %2'
        params:
            colors:
                name: colors
                type: list
        """
        self._uart.write(self._tx.fire_line(colors))

    def stop(self):
        """
        label:
            en: 'Prop STOP %1'
        """
        self._uart.write(self._tx.stop_line())

    def arm(self):
        """
        label:
            en: 'Prop ARM %1'
        """
        self._uart.write(self._tx.arm_line())

    def remote_led(self, which: int = 3):
        """
        label:
            en: 'Prop remote LED %1 which %2'
        params:
            which:
                name: which
                type: int
                default: '3'
                field: number
                min: '3'
                max: '5'
        """
        if which == 3:
            bit = self._prop_frame.REMOTE_LED_BIT_LED3
        elif which == 5:
            bit = self._prop_frame.REMOTE_LED_BIT_LED5
        else:
            raise ValueError("remote LED must be 3 or 5")
        self._uart.write(self._tx.remote_led_line(bit))

    def sync_palette(self, colors):
        """
        label:
            en: 'Prop sync palette %1 colors %2'
        params:
            colors:
                name: colors
                type: list
        """
        self._uart.write(self._tx.palette_line(1, False, colors, track_ack=False))

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
            return data.decode()
        except Exception:
            return ""

    def hue_color(self, deg: int = 0) -> tuple:
        """
        label:
            en: 'Prop hue %1 deg %2 to color'
        params:
            deg:
                name: deg
                type: int
                default: '0'
                field: number
                min: '0'
                max: '359'
        """
        return self._prop_ui.hsv(deg)

    def default_hues(self) -> list:
        """
        label:
            en: 'Prop default hues %1'
        """
        return [0, 120, 240, 210, 60]

    def default_colors(self) -> list:
        """
        label:
            en: 'Prop default colors %1'
        """
        return self._prop_ui.palette_from_hues(self.default_hues())

    def palette_from_hues(self, hues) -> list:
        """
        label:
            en: 'Prop colors from hues %1 hues %2'
        params:
            hues:
                name: hues
                type: list
        """
        return self._prop_ui.palette_from_hues(hues)

    def set_color(self, colors, index: int = 1, color=(255, 0, 0)) -> list:
        """
        label:
            en: 'Prop set color %1 colors %2 LED %3 color %4'
        params:
            colors:
                name: colors
                type: list
            index:
                name: index
                type: int
                default: '1'
                field: number
                min: '1'
                max: '5'
            color:
                name: color
                type: tuple
        """
        out = list(colors)
        if not out:
            return [color]
        try:
            pos = int(index)
        except Exception:
            pos = 1
        pos = max(1, min(pos, len(out)))
        out[pos - 1] = color
        return out

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

    def remote_led3(self):
        """
        label:
            en: 'Prop remote LED3 %1'
        """
        self.remote_led(3)

    def remote_led5(self):
        """
        label:
            en: 'Prop remote LED5 %1'
        """
        self.remote_led(5)
