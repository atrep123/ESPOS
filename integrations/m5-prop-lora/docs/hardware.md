# M5 Prop LoRa Controller Hardware

Current Terminal setup slice: **M5StickS3 Terminal** owns setup editing over the
local USB setup link. Terminal owns setup editing, Terminal has no radio module,
no radio modem path, and no radio protocol sender. Dial remains the radio fire
controller only through the C6 modem pair. DinMeter remains the receiver-side
safety authority, setup persistence owner, and LED execution/indication surface.
Terminal sends only `SETUP` / `SIM_FIRE` setup-link commands; setup uploads use
`SETUP <request_id>` with request-scoped `SETUP_OK <request_id>` /
`SETUP_ERR <request_id>` replies.

This plan uses an M5 Dial as the handheld transmitter, an M5 DIN-style receiver, and an M5Stack Unit C6L as the LoRa modem link.

## M5StickS3 Terminal hardware status

- Final backplane pin map is not confirmed; Terminal firmware keeps pins disabled
  by default until the bench wiring is chosen.
- The chain encoder UART branch has compile coverage, but the final RX/TX lane
  order and connector orientation still need on-device bring-up.
- The fader ADC path is guarded behind build flags; PaHUB must not be used as an
  analog fader router.
- The external OLED controller and address are not confirmed. The LaskaKit 2.42
  inch module may need a dedicated sink after I2C scan/display bring-up.
- Use `sticks3-terminal-oled-i2c-scan-smoke` with real SDA/SCL overrides and
  `tools/read_com.py` to capture `OLED_I2C_SCAN FOUND`,
  `OLED_I2C_SCAN EXPECTED_FOUND 1`, and `OLED_I2C_SCAN DONE` before enabling
  any display sink.
- Grove2USB-C role is not finalized: it may be only the setup cable path, a
  setup-link adapter, a UART bridge, or removed from final wiring.

Current Terminal bench wiring snapshot, 2026-06-14:

- M5StickS3 connects by USB-C to the PC, then a Grove cable connects StickS3 to
  the primary Pa.HUB v2.1.
- Primary Pa.HUB port 0 is the serial branch:
  `Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch`.
- Pot1..Pot5 do not use Pa.HUB as their signal path. A bare StickS3 direct
  10-signal fader+RGB map is rejected because StickS3 `G1..G4` share internal
  PMIC/speaker/IMU functions and Grove `G9/G10` remains reserved for the rest of
  Terminal.
- First fader slice is slider-only: use 5 ADC channels for Pot1..Pot5 and leave
  the Unit Fader SK6812 LEDs disabled/deferred.
- Bare StickS3 still does not expose five clean direct ADC channels while the
  rest of Terminal remains attached. Safe direct ADC budget is four candidates
  (`G5/G6/G7/G8`); the fifth slider needs an external ADC/mux or one explicitly
  verified shared pin from `G1..G4`.
- G4 ADC smoke on 2026-06-14 built, uploaded, and ran on the connected StickS3.
  Runtime serial output tracked fader movement from raw 0 to 4095, so G4 is
  accepted as the verified shared-pin candidate for the fifth slider ADC. This
  consumes the StickS3 IMU interrupt pin; do not use IMU interrupt or low-power
  IMU wake features in the Terminal build. The observed direction is inverted:
  physical bottom is raw 4095 and physical top is raw 0, so the fader calibration
  must use rawMin greater than rawMax for this lane if bottom means 0 percent.
- Primary Pa.HUB port 1 and port 2 are reserved for now; do not connect Pot5/Pot4
  there for signal reads. Port 3 is the external 2.4 inch display branch, and
  port 5 goes to the secondary Pa.HUB v2.1.
- Secondary Pa.HUB ports 2, 3, and 4 are reserved for now; do not connect
  Pot3/Pot2/Pot1 there for signal reads.
- Logical lane names stay LED1..LED5 even though the physical encoder branch
  starts at LED5 and ends at LED1 before the two switches.
- The first U206 switch is the upload switch. The second U206 switch is the global SIM_FIRE preview switch; it sends preview only and does not commit setup values.
- Pot1..Pot5 are confirmed M5Stack Unit Fader U123 modules: B10K analog slider
  plus 14x SK6812 programmable RGB LEDs. Pa.HUB channel ownership is documented
  only for remaining non-fader paths. First hardware slice reads only the analog
  slider outputs and leaves fader LEDs disabled/deferred; bare StickS3 still
  needs an external ADC/mux or one explicitly verified shared pin to reach five
  clean slider ADCs.

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
- I2C: G1/G2 at 100 kHz
- LED driver: M5 Unit NeoDriver at 0x60, driving 5x SK6812 RGBW
- Local inputs: M5 Unit ByteButton at 0x47
- Role: LED-only receiver feedback plus local button/switch inputs

Port B carries the I2C bus for the NeoDriver and ByteButton. The receiver slice is LED-only: it reports accepted controller state through the addressable LED path and does not drive any actuator output.

## LoRa modem

- Target name: `c6l-modem`
- Hardware: Unit C6L
- Role: UART-to-LoRa modem between `dial-tx` and `din-rx`

The Unit C6L firmware should keep the radio behavior isolated from controller UI and receiver LED behavior. The Dial and DIN firmware talk to it over UART, while the modem owns LoRa packet timing and radio state.

Build note: the C6L modem builds with PlatformIO through the `pioarduino` ESP32 platform, because the official PlatformIO `espressif32` ESP32-C6 board manifests do not expose the Arduino framework. The C6 project pins Arduino core `3.3.8` and the matching ESP32-C6 library package. The build and flash helpers also set a short per-firmware PlatformIO core cache under the drive root, such as `C:\.pio-m5-prop-lora\c6l-modem`, so C6 and DIN builds do not overwrite each other's global `framework-arduinoespressif32` package or hit Windows long-path extraction failures. The DIN receiver also builds with PlatformIO, and the Dial fork expects ESP-IDF.
