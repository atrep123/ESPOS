# main.py -- UIFlow2 (MicroPython) Dial app: the UI layer of the port.
#
# Sits on top of the byte-exact prop_frame.py protocol encoder (proven == the C++
# firmware by tests/test_uiflow_prop_frame_parity.py). This file is the "easy 80%":
# it draws the operator UI on the M5Dial, reads the encoder + button, and sends the
# SAME "FF <HEX>\n" / "SEND <HEX>\n" UART command lines to the C++ LoRa modem -- which,
# with the DinMeter receiver, stays C++ and keeps ALL the safety (ARM/Fire/STOP gating).
#
# STATUS: first runnable iteration. The PROTOCOL path is proven; the DISPLAY/INPUT
# path uses the UIFlow2 MicroPython API as documented and is marked "VERIFY ON DEVICE"
# where a method name may differ across UIFlow firmware versions. Drawing is funneled
# through small helpers so any API rename is a one-line fix.
#
# Hardware (mirrors firmware/dial-tx/.../prop_tx_config.h):
#   UART to the modem: id=1, 115200 8N1, TX=GPIO13 -> modem RX, RX=GPIO15 <- modem TX.
#   Display: M5Dial round 240x240. Input: built-in rotary encoder + its push button.

import M5
from M5 import Widgets          # noqa: F401  (kept for managed widgets if preferred)
from hardware import UART, Rotary
import time

try:
    import prop_frame as pf
    _PROP_FRAME_IMPORT_ERROR = None
except Exception as e:
    pf = None
    _PROP_FRAME_IMPORT_ERROR = e
import prop_state as ps


def delay_ms(ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)
    elif hasattr(time, "sleep"):
        time.sleep(ms / 1000)
    else:
        raise RuntimeError("time.sleep_ms or time.sleep is required for Prop timing")


# ---------------------------------------------------------------------------
# NVS persistence -- the thin device layer. esp32.NVS exists only on the M5;
# off-device (CPython) these degrade to no-ops so the app still imports/runs.
# WHAT to store is decided (and unit-tested) in prop_state.py; this only does I/O.
# VERIFY ON DEVICE: esp32.NVS method names are stable across UIFlow2 builds.
# ---------------------------------------------------------------------------
_NVS_NS = "propdial"
try:
    from esp32 import NVS
    _nvs = NVS(_NVS_NS)

    def _nvs_get_i32(key, default):
        try:
            return _nvs.get_i32(key)
        except (OSError, KeyError, ValueError):
            return default

    def _nvs_set_i32(key, value):
        try:
            _nvs.set_i32(key, int(value)); _nvs.commit()
        except Exception as e:                  # never let persistence wedge the UI
            print("nvs set_i32 err:", e)

    def _nvs_get_blob(key, size):
        try:
            buf = bytearray(size)
            n = _nvs.get_blob(key, buf)
            return bytes(buf[:n])
        except (OSError, KeyError, ValueError):
            return None

    def _nvs_set_blob(key, data):
        try:
            _nvs.set_blob(key, bytes(data)); _nvs.commit()
        except Exception as e:
            print("nvs set_blob err:", e)
except ImportError:                             # off-device: persistence is a no-op
    def _nvs_get_i32(key, default):
        return default

    def _nvs_set_i32(key, value):
        pass

    def _nvs_get_blob(key, size):
        return None

    def _nvs_set_blob(key, data):
        pass


# ---------------------------------------------------------------------------
# Config (mirror prop_tx_config.h)
# ---------------------------------------------------------------------------
UART_ID, UART_TX, UART_RX, UART_BAUD = 1, 13, 15, 115200

SCREEN = 240
CX = CY = SCREEN // 2
ORB_R = 46

# Theme (subset of gui/ui_theme_dial_generated.h)
BG_BASE   = 0x14171D
RING_TRK  = 0x363D4A
TEXT_HI   = 0xE7E9ED
TEXT_DIM  = 0x8B9097
P_GREEN   = 0x3FB36B   # ready / ok
P_AMBER   = 0xFF8C00   # waiting / no-ack
P_RED     = 0xCC0000   # armed / error / STOP
MODE_SETUP = 0x59C6DC  # cyan: NASTAVENI (edit) mode

# Command actions, mirroring COMMAND_ACTIONS in app_prop_tx.cpp.
A_PREVIEW, A_ARM, A_ODPAL, A_STOP = range(4)
ACTIONS = ("NAHLED", "ARM", "ODPAL", "STOP")
ACTION_COLOR = (P_GREEN, P_RED, P_AMBER, P_RED)

# Factory effect colors used only for PREVIEW/FIRE payloads. Terminal owns setup.
DEFAULT_HUES = [0, 120, 240, 210, 60]
NUM_LEDS = 5

MODE_CMD = 0

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
tx = None            # pf.PropSender
uart = None
rotary = None
LCD = None           # the display object (M5.Lcd) -- see setup()

_mode = MODE_CMD
_action = A_PREVIEW
_led = 0
_hues = list(DEFAULT_HUES)
_colors = [(0, 0, 0)] * NUM_LEDS
_status = "READY"
_status_color = P_GREEN
_last_rotary = 0
_dirty = True
_seq_reserved = 0    # sequence high-water already reserved in NVS (flash-wear guard)


# ---------------------------------------------------------------------------
# Colour helpers (UI only -- prop_frame.py stays protocol-only)
# ---------------------------------------------------------------------------
def hsv_to_rgb(h, s=1.0, v=1.0):
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if   h < 60:  r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def rgb888(c):
    return (c[0] << 16) | (c[1] << 8) | c[2]


def refresh_colors():
    for i in range(NUM_LEDS):
        _colors[i] = hsv_to_rgb(_hues[i])


# ---------------------------------------------------------------------------
# Drawing (immediate-mode via M5.Lcd / LovyanGFX). VERIFY ON DEVICE: a couple of
# method names below may differ slightly by UIFlow version -- all isolated here.
# ---------------------------------------------------------------------------
def _text_center(s, x, y, color, size=1, bg=BG_BASE):
    LCD.setTextColor(color, bg)
    LCD.setTextSize(size)
    # drawCenterString(text, x, y) is the LovyanGFX centred-text call.
    LCD.drawCenterString(s, x, y)


def draw():
    global _dirty
    _dirty = False
    LCD.fillScreen(BG_BASE)
    LCD.drawCircle(CX, CY, 116, RING_TRK)            # outer gauge ring

    command = (_mode == MODE_CMD)
    _text_center("PRIKAZ" if command else "NASTAVENI", CX, 26,
                 TEXT_HI if command else MODE_SETUP, 1)

    if command:
        col = ACTION_COLOR[_action]
        LCD.fillCircle(CX, CY, ORB_R, col)
        _text_center(ACTIONS[_action], CX, CY - 8, BG_BASE, 2, col)
        _text_center("stisk = odeslat", CX, CY + ORB_R + 16, TEXT_DIM, 1)
    else:
        col = rgb888(_colors[_led])
        LCD.fillCircle(CX, CY, ORB_R, col)
        _text_center("LED %d" % (_led + 1), CX, CY - 16, BG_BASE, 2, col)
        _text_center("%d" % _hues[_led] + chr(0xB0), CX, CY + 10, BG_BASE, 2, col)
        _text_center("toc = barva  stisk = dalsi LED", CX, CY + ORB_R + 16, TEXT_DIM, 1)

    # LED dots row (5 swatches) near the bottom arc
    n = NUM_LEDS
    gap = 30
    x0 = CX - (gap * (n - 1)) // 2
    dy = SCREEN - 30
    for i in range(n):
        x = x0 + i * gap
        LCD.fillCircle(x, dy, 7, rgb888(_colors[i]))
        if (not command) and i == _led:
            LCD.drawCircle(x, dy, 11, MODE_SETUP)    # selection ring

    _text_center(_status, CX, 50, _status_color, 1)


# ---------------------------------------------------------------------------
# Modem link
# ---------------------------------------------------------------------------
def set_status(text, color=TEXT_HI):
    global _status, _status_color, _dirty
    _status, _status_color, _dirty = text, color, True


def _persist_seq_if_needed():
    """Persist the sequence high-water at most once per reserved block (flash wear)."""
    global _seq_reserved
    if tx is None:
        return
    new_res, should_write = ps.seq_next_reservation(tx.sequence, _seq_reserved)
    if should_write:
        _seq_reserved = new_res
        _nvs_set_i32("seq", new_res)


def drain_modem(deadline_ms=120):
    """Read modem reply lines for a short window; surface the most relevant one."""
    end = time.ticks_add(time.ticks_ms(), deadline_ms)
    seen = None
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if uart.any():
            line = uart.readline()
            if not line:
                continue
            try:
                s = line.decode().strip() if isinstance(line, bytes) else str(line).strip()
            except Exception:
                continue
            if not s:
                continue
            seen = s
            if s.startswith("OK"):
                set_status("OK", P_GREEN)
            elif s.startswith("ERR"):
                set_status(s[:18], P_RED)
            elif s.startswith("RX"):
                set_status("RX", P_GREEN)
        else:
            delay_ms(2)
    return seen


def send_current_action():
    if tx is None or uart is None:
        set_status("KEY MISSING", P_RED)
        return
    a = _action
    try:
        if a == A_PREVIEW:
            uart.write(tx.preview_line(_colors[:4])); set_status("NAHLED ->", P_GREEN)
        elif a == A_ARM:
            for line in tx.arm_lines():
                uart.write(line)
            set_status("ARM ->", P_AMBER)
        elif a == A_ODPAL:
            delay_ms(0)
            fire_lines = tx.fire_burst_lines(_colors[:4])
            for index, line in enumerate(fire_lines):
                uart.write(line)
                if index + 1 < len(fire_lines):
                    # Keep redundant FIRE copies spaced by the protocol constant;
                    # the receiver dedups them, but the modem still needs air gap.
                    delay_ms(pf.FIRE_BURST_GAP_MS)
            set_status("ODPAL ->", P_AMBER)
        elif a == A_STOP:
            delay_ms(0)
            stop_lines = tx.stop_lines()
            for index, line in enumerate(stop_lines):
                uart.write(line)
                set_status("STOP ->", P_RED)
                seen = drain_modem(pf.STOP_RETRY_TIMEOUT_MS)
                if seen and (seen.startswith("OK") or seen.startswith("RX")):
                    break
                if index + 1 < len(stop_lines):
                    delay_ms(pf.STOP_RETRY_GAP_MS)
    except Exception as e:           # never let a send fault wedge the UI
        set_status("TX FAIL", P_RED)
        print("send error:", e)
        return
    # ARM/ODPAL round-trip an ACK over LoRa -- give it longer to land than a local cmd.
    # STOP drains during its retry loop above.
    if a != A_STOP:
        drain_modem(350 if a in (A_ARM, A_ODPAL) else 120)
    _persist_seq_if_needed()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
def on_rotate(delta):
    global _action, _hues, _dirty
    if _mode == MODE_CMD:
        _action = (_action + delta) % len(ACTIONS)
    else:
        _hues[_led] = (_hues[_led] + delta * 2) % 360   # 2 deg / detent
        refresh_colors()
    _dirty = True


def on_click():
    """Short press: command mode -> fire the action; setup mode -> next LED."""
    global _led, _dirty
    if _mode == MODE_CMD:
        send_current_action()
    else:
        _led = (_led + 1) % NUM_LEDS
        _dirty = True


def on_hold():
    """Long press: setup handoff. Terminal owns all setup editing."""
    global _mode, _dirty
    _mode = MODE_CMD
    set_status("SETUP NA TERMINALU", MODE_SETUP)
    _dirty = True


# ---------------------------------------------------------------------------
# UIFlow lifecycle
# ---------------------------------------------------------------------------
def setup():
    global tx, uart, rotary, LCD, _last_rotary, _seq_reserved
    M5.begin()
    # M5.Lcd is the LovyanGFX display on the Dial. (If a build exposes it as
    # M5.Display instead, change this one line.)
    LCD = M5.Lcd

    refresh_colors()
    if _PROP_FRAME_IMPORT_ERROR is not None:
        tx = None
        uart = None
        rotary = Rotary()
        _last_rotary = rotary.get_rotary_value()
        set_status("KEY MISSING", P_RED)
        print("prop_frame import error:", _PROP_FRAME_IMPORT_ERROR)
        draw()
        return

    # Resume the frame sequence one past the last value reserved in NVS, so a reboot
    # never reuses or rewinds a sequence number. tx MUST be created here -- the first
    # iteration omitted this, leaving tx=None so every send hit "TX FAIL".
    seq_start = ps.seq_resume_from(_nvs_get_i32("seq", 0))
    _seq_reserved = seq_start
    tx = pf.PropSender(sequence=seq_start)
    _persist_seq_if_needed()             # claim the first block up-front (power-loss safe)

    uart = UART(UART_ID, baudrate=UART_BAUD, bits=8, parity=None, stop=1,
                tx=UART_TX, rx=UART_RX, timeout=20, timeout_char=5)
    uart.write("\n")                 # leading newline flushes the modem's line parser
    delay_ms(50)
    drain_modem(80)

    rotary = Rotary()
    _last_rotary = rotary.get_rotary_value()
    set_status("READY", P_GREEN)
    draw()


def loop():
    global _last_rotary
    M5.update()

    # encoder: accumulate detents into a signed delta
    v = rotary.get_rotary_value()
    if v != _last_rotary:
        on_rotate(v - _last_rotary)
        _last_rotary = v

    # button: the M5Dial encoder push button is BtnA in UIFlow. VERIFY ON DEVICE.
    try:
        if M5.BtnA.wasHold():
            on_hold()
        elif M5.BtnA.wasClicked():
            on_click()
    except AttributeError:
        pass                          # button object differs on this build -- see note

    if _dirty:
        draw()
    delay_ms(10)


if __name__ == "__main__":
    try:
        setup()
        while True:
            loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg
            print_error_msg(e)
        except ImportError:
            print("please update to the latest UIFlow2 firmware")
            raise
