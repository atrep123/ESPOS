# M5 Prop LoRa Controller Hardware

Current Terminal setup slice: **M5StickS3 Terminal** owns setup editing.
Terminal owns setup editing, Terminal has no radio module, no radio modem path,
and no radio protocol sender. The default bench firmware uses the local USB
setup link; the first prop-side route uses
`sticks3-terminal-prop-link-g43-g44-600` over a private A140 cable to XIAO. Dial
remains the radio fire controller only through the C6 modem pair. DinMeter
remains the receiver-side safety authority, setup persistence owner, and LED
execution/indication surface.
Terminal sends only `SETUP` / `SIM_FIRE` setup-link commands; setup uploads use
`SETUP <request_id>` with request-scoped `SETUP_OK <request_id>` /
`SETUP_ERR <request_id>` replies.

This plan uses an M5 Dial as the handheld transmitter, an M5 DIN-style receiver, and an M5Stack Unit C6L as the LoRa modem link.

## M5StickS3 Terminal hardware status

- Final backplane pin map is not confirmed; Terminal firmware keeps pins disabled
  by default until the bench wiring is chosen.
- The chain encoder UART branch has compile coverage, but the final RX/TX lane
  order and connector orientation still need on-device bring-up.
- The fader ADC/RGB path is guarded behind Pb.HUB build flags; PaHUB must not
  be used as an analog fader router.
- The external OLED controller and address are not confirmed. The LaskaKit 2.42
  inch module may need a dedicated sink after I2C scan/display bring-up.
- Use `sticks3-terminal-oled-i2c-scan-smoke` with real SDA/SCL overrides and
  `tools/read_com.py` to capture `OLED_I2C_SCAN FOUND`,
  `OLED_I2C_SCAN EXPECTED_FOUND 1`, and `OLED_I2C_SCAN DONE` before enabling
  any display sink.
- Grove2USB-C role is not finalized for final enclosure/power routing. A140 is
  now the first private prop-link candidate: StickS3 RX G44 reads XIAO D4/GPIO6
  and StickS3 TX G43 drives XIAO D5/GPIO7. It is not USB protocol; do not plug
  this private cable into a PC or phone.

Current Terminal bench wiring snapshot, 2026-06-14:

- M5StickS3 connects by USB-C to the PC, then a Grove cable connects StickS3 to
  the primary Pa.HUB v2.1.
- Primary Pa.HUB port 0 is the serial branch:
  `Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch`.
- Pot1..Pot5 do not use Pa.HUB as their final signal path. Pa.HUB only selects
  the downstream I2C branch.
- Pb.HUB #1 at address 0x61 is behind primary Pa.HUB port 5.
- Pb.HUB reads the five Unit Fader ADC channels and drives their SK6812 RGB
  reflection.
- Pb.HUB port 0 -> Pot5.
- Pb.HUB port 1 -> Pot4.
- Pb.HUB port 2 -> Pot3.
- Pb.HUB port 3 -> Pot2.
- Pb.HUB port 4 -> Pot1.
- Pb.HUB port 5 -> Grove2USB-C/C module branch toward XIAO. This port is
  reserved for that link and must not be used as a sixth fader port.
- PB.HUB port 5 is not a transparent Serial2 UART route. The current
  `sticks3-terminal-prop-link-g43-g44-600` smoke uses direct StickS3 RX G44 / TX
  G43 wiring outside PB.HUB; a PB.HUB-hosted XIAO branch needs a separate
  low-speed GPIO/I2C transport design.
- Runtime fader mapping intentionally reverses this physical Pb.HUB order:
  logical LED1..LED5 use Pot1..Pot5.
- A bare StickS3 direct 10-signal fader+RGB map remains rejected because
  StickS3 `G1..G4` share internal PMIC/speaker/IMU functions and Grove `G9/G10`
  remains reserved for the Pa.HUB/Pb.HUB topology.
- G4 ADC smoke on 2026-06-14 built, uploaded, and ran on the connected StickS3.
  Runtime serial output tracked fader movement from raw 0 to 4095, so G4 is
  accepted as the verified shared-pin candidate for the fifth slider ADC. This
  consumes the StickS3 IMU interrupt pin; do not use IMU interrupt or low-power
  IMU wake features in the Terminal build. The observed direction is inverted:
  physical bottom is raw 4095 and physical top is raw 0, so the fader calibration
  must use rawMin greater than rawMax for this lane if bottom means 0 percent.
- Primary Pa.HUB port 3 is the external 2.4 inch display branch, and primary
  Pa.HUB port 5 goes to the Pb.HUB v1.1 fader branch.
- Logical lane names stay LED1..LED5 even though the physical encoder branch
  starts at LED5 and ends at LED1 before the two switches.
- The first U206 switch is the upload switch. The second U206 switch is the global SIM_FIRE preview switch; it sends preview only and does not commit setup values.
- Pot1..Pot5 are confirmed M5Stack Unit Fader U123 modules: B10K analog slider
  plus 14x SK6812 programmable RGB LEDs. Pa.HUB channel ownership is documented
  only for branch selection. Pb.HUB owns the fader ADC reads and fader RGB
  reflection; Pa.HUB does not read slider positions or drive fader LEDs.

## Dial transmitter

- Target name: `dial-tx`
- Expansion header: Port A
- UART TX to the Unit C6L: G13
- UART RX from the Unit C6L: G15
- Radio module: Unit C6L on Port A
- FIRE button: M5Stack Chain Key (Mechanical Key Button STM32G031, SKU U206) on Port B
- FIRE button protocol: M5Chain UART cascade, 115200 8N1, Port B pins G1/G2

Port A carries power, ground, and the UART pair for the Unit C6L. Keep TX/RX crossed at the module side if using loose jumpers instead of a keyed Grove cable. Port B carries the Chain Key UART cascade for the dedicated FIRE button; firmware defaults to G2 as TX and G1 as RX, but those two may need swapping on real hardware depending on the cable/adapter orientation.

## DIN receiver

- Target name: `din-rx`
- Expansion header: Port B
- Production Port B backend: UART to a Seeed Studio XIAO RP2040 prop-I/O board
- DinMeter TX: Port B G2/yellow/GO -> XIAO D7/GPIO1 RX
- DinMeter RX: Port B G1/white/GI <- XIAO D6/GPIO0 TX
- UART: 115200 8N1, protocol in `shared/protocol/prop_xiao_link.h`
- XIAO local inputs: 3 momentary buttons plus 1 maintained switch, all
  `INPUT_PULLUP`, active-low to GND
- XIAO outputs: one 4-pixel status LED data chain plus one 18x WS2812B barrel strip
- Role: DinMeter remains safety/protocol/persistence authority; XIAO is only the
  prop electronics coprocessor for local inputs and LED output

Production Port B must not run I2C at the same time as the XIAO UART bridge.
The legacy I2C path remains compiled as a bench fallback only: ByteButton at
0x47 and NeoDriver at 0x60 on G1/G2. In the current prop build
`PROP_IO_XIAO_UART_ENABLED = true`, so DinMeter leaves Port B I2C idle and uses
UART2 for XIAO.

XIAO wiring snapshot, 2026-06-14:

| Function | XIAO RP2040 pin | Electrical note |
| --- | --- | --- |
| UART TX to DinMeter RX | D6 / GPIO0 | 3.3 V logic, no level shifter |
| UART RX from DinMeter TX | D7 / GPIO1 | 3.3 V logic, no level shifter |
| Switch 1 | D0 / GPIO26 | `INPUT_PULLUP`, switch to GND |
| Switch 2 | D1 / GPIO27 | `INPUT_PULLUP`, switch to GND |
| Switch 3 / local fire | D2 / GPIO28 | `INPUT_PULLUP`, switch to GND |
| Maintained toggle switch | D3 / GPIO29 | `INPUT_PULLUP`, switch to GND |
| Terminal private link TX | D4 / GPIO6 | XIAO to Terminal via Grove2USB-C A140 data pin |
| Terminal private link RX | D5 / GPIO7 | Terminal to XIAO via Grove2USB-C A140 data pin |
| Barrel strip data | D8 / GPIO2 | 18x WS2812B, red whole-barrel effect |
| Four status LEDs data | D10 / GPIO3 | 4 logical status LEDs |
| Reserved | D9 / GPIO4 | keep free for future bench use |

Power rules:

- Do not power the LED strips from DinMeter Port B. The Port B 5 V rail is only
  a low-current accessory rail and is not sized for the barrel.
- Use an external regulated 5 V LED supply. Budget at least 2 A; 3 A gives
  margin for the 18 WS2812B barrel plus four RGB/RGBW status LEDs.
- Tie DinMeter GND, XIAO GND, LED supply GND, and level-shifter GND together.
- Put a 74AHCT125/74HCT245-class level shifter between XIAO data pins and 5 V
  WS2812/SK6812 data inputs.
- Put 330-500 ohm series resistance near each first LED data input and
  500-1000 uF bulk capacitance on the 5 V LED rail near the first LEDs.

Logical mapping:

- DinMeter still keeps five logical lanes so Terminal/Dial setup semantics stay
  stable.
- The four-pixel XIAO status LED chain receives logical LED1, LED2, switch, and
  the remote blue latch via `STAT4` on one data line.
- Logical ODPAL drives only the 18-pixel barrel as a single red
  intensity/effect group via `BARREL RED/OFF`; the blue latch keeps its
  pre-fire state.

## LoRa modem

- Target name: `c6l-modem`
- Hardware: Unit C6L
- Role: UART-to-LoRa modem between `dial-tx` and `din-rx`

The Unit C6L firmware should keep the radio behavior isolated from controller UI and receiver LED behavior. The Dial and DIN firmware talk to it over UART, while the modem owns LoRa packet timing and radio state.

Build note: the C6L modem builds with PlatformIO through the `pioarduino` ESP32 platform, because the official PlatformIO `espressif32` ESP32-C6 board manifests do not expose the Arduino framework. The C6 project pins Arduino core `3.3.8` and the matching ESP32-C6 library package. The build and flash helpers also set a short per-firmware PlatformIO core cache under the drive root, such as `C:\.pio-m5-prop-lora\c6l-modem`, so C6 and DIN builds do not overwrite each other's global `framework-arduinoespressif32` package or hit Windows long-path extraction failures. The DIN receiver also builds with PlatformIO, and the Dial fork expects ESP-IDF.
