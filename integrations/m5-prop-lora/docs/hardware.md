# M5 Prop LoRa Controller Hardware

This plan uses an M5 Dial as the handheld transmitter, an M5 DIN-style receiver, and an M5Stack Unit C6L as the LoRa modem link.

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
- LED driver: M5 Unit NeoDriver at 0x60, driving 4x SK6812 RGBW
- Local inputs: M5 Unit ByteButton at 0x47
- Role: LED-only receiver feedback plus local button/switch inputs

Port B carries the I2C bus for the NeoDriver and ByteButton. The receiver slice is LED-only: it reports accepted controller state through the addressable LED path and does not drive any actuator output.

## LoRa modem

- Target name: `c6l-modem`
- Hardware: Unit C6L
- Role: UART-to-LoRa modem between `dial-tx` and `din-rx`

The Unit C6L firmware should keep the radio behavior isolated from controller UI and receiver LED behavior. The Dial and DIN firmware talk to it over UART, while the modem owns LoRa packet timing and radio state.

Build note: the C6L modem builds with PlatformIO through the `pioarduino` ESP32 platform, because the official PlatformIO `espressif32` ESP32-C6 board manifests do not expose the Arduino framework. The C6 project pins Arduino core `3.3.8` and the matching ESP32-C6 library package. The build and flash helpers also set a short per-firmware PlatformIO core cache under the drive root, such as `C:\.pio-m5-prop-lora\c6l-modem`, so C6 and DIN builds do not overwrite each other's global `framework-arduinoespressif32` package or hit Windows long-path extraction failures. The DIN receiver also builds with PlatformIO, and the Dial fork expects ESP-IDF.
