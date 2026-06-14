# Prop electronics: DinMeter Port B to XIAO RP2040

This document is the working wiring note for the prop-side electronics. The
DinMeter remains the protocol, persistence, and safety authority. The Seeed
Studio XIAO RP2040 is a local I/O coprocessor so the prop can keep simple
physical buttons and LED wiring without modifying M5Stack button modules.

## Topology

```text
Dial -> C6 modem pair -> DinMeter
                         |
                         | Port B UART, 115200 8N1
                         v
                      XIAO RP2040
                         |-- 3x buttons + 1x maintained switch
                         |-- 4-pixel status LED data chain
                         `-- 18x WS2812B barrel strip, one red effect group
```

DinMeter Port B is **UART in production**. Do not attach the legacy I2C
ByteButton/NeoDriver wiring to Port B while `PROP_IO_XIAO_UART_ENABLED = true`.

## DinMeter to XIAO wiring

| DinMeter Port B wire | DinMeter signal | XIAO signal | XIAO pin |
| --- | --- | --- | --- |
| Black | GND | GND | GND |
| Yellow | G2 / GO / DinMeter TX | UART RX | D7 / GPIO1 |
| White | G1 / GI / DinMeter RX | UART TX | D6 / GPIO0 |
| Red | 5 V accessory rail | optional XIAO 5 V only | 5V/VBUS |

The UART logic is 3.3 V on both sides, so no level shifter is needed for the
DinMeter-XIAO UART. If UART stays silent during bring-up, swap only Yellow and
White. Never move the Red 5 V wire onto a signal pin.

## XIAO local inputs

All input contacts short the XIAO pin to GND when active. Firmware configures
them as `INPUT_PULLUP`, so active means `digitalRead(pin) == LOW`.

| Function | XIAO pin | Behavior in DinMeter |
| --- | --- | --- |
| Button 1 | D0 / GPIO26 | edge toggles logical LED1 |
| Button 2 | D1 / GPIO27 | edge toggles logical LED2 |
| Button 3 | D2 / GPIO28 | local FIRE / ODPAL request |
| Maintained switch | D3 / GPIO29 | live level owns logical switch LED |

## XIAO LED outputs

| Output | XIAO pin | Count | Behavior |
| --- | --- | ---: | --- |
| Barrel WS2812B data | D8 / GPIO2 | 18 | one whole red ODPAL effect group |
| Status LED data | D10 / GPIO3 | 4 | `STAT4`: LED1, LED2, switch, LED5 |

The barrel is not a fifth status LED. DinMeter computes the ODPAL
envelope and sends `BARREL RED <intensity>` or `BARREL OFF`; XIAO applies that
to all 18 barrel pixels.

## Power and signal integrity

- Do not power LEDs from DinMeter Port B.
- Use a regulated external 5 V LED supply. Use 2 A minimum; 3 A is preferred.
- Tie all grounds together: DinMeter, XIAO, LED power supply, and level shifter.
- Use a 74AHCT125 or 74HCT245-class level shifter for each 3.3 V XIAO data line
  that drives 5 V WS2812/SK6812 LEDs.
- Add 330-500 ohm series resistor near each first LED data input.
- Add 500-1000 uF bulk capacitor across the 5 V LED rail near the first LEDs.
- Add fuse/current limiting sized for the actual wire gauge and expected LED
  current.

## UART line protocol

Shared contract: `shared/protocol/prop_xiao_link.h`.

XIAO to DinMeter:

```text
HELLO XIAO_PROP_IO 1 WS:18 LED:4 BTN:3 SW:1
PONG <seq>
BTN <1|2|3> <DOWN|UP>
SW 1 <ON|OFF>
```

DinMeter to XIAO:

```text
HELLO XIAO_PROP_IO 1 WS:18 LED:4 BTN:3 SW:1
PING <seq>
STAT4 <RRGGBB> <RRGGBB> <RRGGBB> <RRGGBB>
BARREL OFF
BARREL RED <0..255>
BARREL FIRE <ramp_ms> <hold_ms> <fade_ms> <curve>
```

The current DinMeter build sends `STAT4` plus `BARREL RED/OFF`. `BARREL FIRE`
is reserved for a later XIAO-owned effect-envelope implementation if needed.

## First bring-up order

1. Flash DinMeter with the XIAO UART build.
2. Leave XIAO disconnected and confirm DinMeter shows `XIO` mode and `XIAO?`
   rather than trying to scan Port B I2C.
3. Connect only GND, TX, RX between DinMeter and XIAO.
4. Flash XIAO firmware and confirm `HELLO`/`PING`/`PONG` on serial logs.
5. Add buttons and switch, verify edge events before connecting LED power.
6. Add external 5 V LED power, level shifters, resistors, and capacitors.
7. Test `STAT4` status LEDs.
8. Test local FIRE and Dial FIRE; barrel should act as one red group.
