# M5StickS3 Terminal

USB setup terminal for ESPOS prop configuration.

This Terminal has no radio module, no radio modem path, and no radio protocol
sender. Dial remains the radio fire controller and does not own setup editing.
Terminal owns setup editing. DinMeter remains the receiver-side safety
authority and LED execution/indication surface.

Hardware bring-up is not complete yet. The current firmware has tested setup,
USB, switch, filter, M5Chain dependency, and display-format boundaries, but real
fader ADC wiring, real chain encoder sampling, and real external OLED IO still
need bench proof.

M1 control model:

- 5 sliders/faders set LED brightness. Fader brightness 0 means the lane is normally off; any value above 0 means the lane is normally on.
- 5 encoders step each LED through the named color palette.
- Encoder button toggles whether that lane changes state during fire: a
  normally on lane turns off during fire, and a normally off lane turns on.
- Double-click is intentionally ignored until hardware testing proves it is
  needed.
- When an external OLED sink is enabled and validated, the large display shows
  one framed row per LED: LED number, color name, brightness or `VYP`, and
  whether the lane changes state during fire as `ODP` or `---`.
- There is no menu navigation and no hidden button-driven UI movement.
- A stable upload switch press asks app logic to send the staged values over the
  USB setup link.
- If the prop accepts the upload, the M5StickS3 status screen shows `NAHRANO`
  on a green background.
- If the upload fails or the USB setup link does not answer before timeout, the
  M5StickS3 status screen shows `PROBLEM` on a red background and the staged
  values revert to the last saved values. `PROBLEM` stays visible across later
  physical control movement until the next upload changes status.
- The last physical U206 switch drives SIM_FIRE preview over the setup link.
  It does not commit setup values and does not use the radio fire path.
- Built-in M5StickS3 status panel never mirrors lane rows. Lane values stay on
  the large display so the small status screen cannot overflow.

Current bench wiring snapshot, 2026-06-14:

- M5StickS3 connects by USB-C to the PC.
- M5StickS3 Grove cable goes to the primary Pa.HUB v2.1.
- Primary Pa.HUB port 0 is the serial chain branch:
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
  Serial output tracked fader movement from raw 0 to 4095, so G4 is accepted as
  the verified shared-pin candidate for the fifth slider ADC. This consumes the
  StickS3 IMU interrupt pin; do not use IMU interrupt or low-power IMU wake
  features in the Terminal build. The observed direction is inverted: physical
  bottom is raw 4095 and physical top is raw 0.
- Primary Pa.HUB port 1 is reserved for now; do not connect Pot5 there for
  signal reads.
- Primary Pa.HUB port 2 is reserved for now; do not connect Pot4 there for
  signal reads.
- Primary Pa.HUB port 3 is the external 2.4 inch display branch.
- Primary Pa.HUB port 5 goes to the secondary Pa.HUB v2.1.
- Secondary Pa.HUB ports 2, 3, and 4 are reserved for now; do not connect Pot3,
  Pot2, or Pot1 there for signal reads.
- Logical lane names remain LED1..LED5 for setup lines, effects, display rows,
  and logs. The physical encoder branch order is
  `DATA IN -> LED5 -> LED4 -> LED3 -> LED2 -> LED1 -> upload switch -> sim-fire switch`.
- The first U206 uploads the staged values to the prop over the USB-C setup-link
  path. The second U206 is the global SIM_FIRE preview switch and sends one
  setup-link preview edge when pressed.
- Pot1..Pot5 are confirmed M5Stack Unit Fader U123 modules: B10K analog slider
  plus 14x SK6812 programmable RGB LEDs. Pa.HUB port ownership is recorded only
  for the remaining non-fader paths; Pa.HUB still must not be treated as a fader
  signal router. First hardware slice reads only the analog slider outputs and
  leaves fader LEDs disabled/deferred; bare StickS3 still needs an external
  ADC/mux or one explicitly verified shared pin to reach five clean slider ADCs.

Build:

```powershell
pio run -d integrations/m5-prop-lora/firmware/sticks3-terminal
pio run -d integrations/m5-prop-lora/firmware/sticks3-terminal -e sticks3-terminal-chain-uart-smoke
pio run -d integrations/m5-prop-lora/firmware/sticks3-terminal -e sticks3-terminal-oled-i2c-scan-smoke
pio run -d integrations/m5-prop-lora/firmware/sticks3-terminal -e sticks3-terminal-grove-i2c-scan-smoke
pio run -d integrations/m5-prop-lora/firmware/sticks3-terminal -e sticks3-terminal-oled-draw-smoke
```

The PlatformIO board is intentionally `esp32-s3-devkitc-1` with `qio_opi` and
PSRAM flags, matching the M5StickS3 ESP32-S3-PICO-1-N8R8 memory layout used by
M5Stack examples. Do not change it just because the board name is generic.
The `sticks3-terminal-chain-uart-smoke` environment is the current bench
diagnostic for the M5Chain branch. It selects primary Pa.HUB address `0x70`
channel `0` over Grove I2C SDA G9 / SCL G10, then uses UART RX G10 / TX G9 and
logs `CHAIN_UART_SMOKE ...` lines for expected encoder IDs 1..5 and U206 key
IDs 6..7. On 2026-06-14 the original RX G9 / TX G10 direction timed out, while
the swapped RX G10 / TX G9 direction connected and enumerated all seven chain
devices.
The `sticks3-terminal-oled-i2c-scan-smoke` environment compiles the external
OLED I2C scan path with dummy G1/G2 pins. For real LaskaKit bring-up, rebuild it
with the actual `TERMINAL_EXTERNAL_OLED_SDA_PIN` and
`TERMINAL_EXTERNAL_OLED_SCL_PIN`, read serial with `tools/read_com.py`, and
record `OLED_I2C_SCAN FOUND 0x..`, `OLED_I2C_SCAN EXPECTED_FOUND 1`, and
`OLED_I2C_SCAN DONE count=..` before enabling any display sink. These scan lines are USB serial diagnostics, not setup-link protocol traffic; `SETUP_OK <request_id>` / `SETUP_ERR <request_id>` remain the
only upload acknowledgements.
The `sticks3-terminal-grove-i2c-scan-smoke` environment is the real StickS3
Grove scan: SDA G9, SCL G10, expected address 0x70 for the primary Pa.HUB/PCA9548
mux. It should be the first Grove I2C hardware test before scanning downstream
modules through Pa.HUB channels. On 2026-06-14 this smoke firmware was uploaded
to the connected StickS3 on COM29: the root bus saw `0x70 MUX`, all six Pa.HUB
channel selects returned `err=0`, and both 400 kHz and 100 kHz scans reported
`downstream=0` / `DOWNSTREAM_EMPTY` on every channel. That proves the primary
Pa.HUB and StickS3 Grove pins, but not the OLED branch. A working external OLED
branch should add a non-0x70 downstream address, typically `0x3C` or `0x3D`.
Do not cascade a second Pa.HUB at the same `0x70` address behind primary port 5;
give the secondary mux a different PCA9548 address or remove the cascade.
After the external display SDA/SCL wiring was corrected on 2026-06-14, the same
scan repeatedly found `0x3C DOWNSTREAM` on primary Pa.HUB port 3 at both
400 kHz and 100 kHz. The `sticks3-terminal-oled-draw-smoke` environment is the
next isolated bench test: it selects Pa.HUB port 3 and sends a simple
SSD1309-oriented smoke frame to the 0x3C display. It does not enable the
production external OLED sink. Its serial/I2C write path passed on COM29:
`OLED_DRAW_SMOKE SELECT_PAHUB ... err=0` and repeated
`OLED_DRAW_SMOKE DRAWN address=0x3C channel=3`, but the first SSD1306-style
smoke frame was not visible on the physical OLED. The current draw smoke first
sends `OLED_DRAW_SMOKE ALL_ON_BOOT`; this should briefly light the whole panel
only at boot, then keep a stable text frame. The bench panel was observed
rotated, so the smoke firmware uses `0xA1/0xC8` segment/COM scan orientation.

USB setup link contract:

- Shared parser/formatter: `shared/terminal/terminal_setup_link.h`.
- Setup line example:
  `SETUP <request_id> L1:360,100,1,1 L2:365,50,1,0 L3:364,25,0,1 L4:368,0,1,0 L5:367,80,1,1`
- The first lane field accepts legacy hue `0..359` and named palette codes
  `360..368`. Terminal uploads named palette codes so `BILA` is unambiguous.
- Simulate-fire line: `SIM_FIRE`.
- Accepted reply: `SETUP_OK <request_id>`.
- Rejected reply: `SETUP_ERR <request_id>`.
- Generic `OK`/`ERR` serial diagnostics are ignored while waiting for upload
  confirmation.
- Before each new upload, stale setup replies already waiting in the USB RX
  buffer are drained.
- Upload waits `UPLOAD_ACK_TIMEOUT_MS = 1500` ms and reads reply lines up to
  `USB_LINE_MAX = 160` bytes. Timeout is checked before ACK parsing in each
  loop, so a late ACK after the deadline rolls the draft back.
- `SETUP <request_id>` is atomic on DinMeter for malformed lines,
  out-of-range values, and persistence failure. A wrong request id, USB line
  overflow, or timeout rolls the Terminal draft back; if DinMeter already
  processed and persisted the line before the reply was lost, the receiver-side
  setup may already be committed.

Upload state table:

| Event | Result |
| --- | --- |
| `SETUP <request_id>` sent | `NAHRAVAM`; exact sent snapshot is frozen. |
| matching `SETUP_OK <request_id>` before timeout | `NAHRANO`; sent snapshot becomes saved setup. |
| matching `SETUP_ERR <request_id>` before timeout | `PROBLEM`; draft returns to last saved setup. |
| timeout or USB line overflow | `PROBLEM`; draft returns to last saved setup. |
| physical control movement after `PROBLEM` | values may be edited, but status stays `PROBLEM` until next upload. |
| noise such as `OK`, `ERR`, `BOOT`, `RX`, debug lines, bare setup replies, or wrong request id | stay `NAHRAVAM` until matching reply or timeout. |

Hardware pin mapping for the fader bank, encoders, encoder button fire-change
mapping, upload switch, sim-fire switch, and large display still needs final
bench proof before production upload.

Terminal hardware topology contract:

- 1 M5StickS3 controller.
- 5 Unit Faders and 5 Chain Encoders, one of each per LED lane.
- 2 mechanical switches: upload and sim-fire preview.
- 2 PaHUB modules and 2 Grove2USB-C adapters.
- 1 external 128x64 OLED.
- Terminal has no radio module. Dial remains the radio fire controller.
- PaHUB must not be treated as an analog fader router or as a SK6812 fader LED
  data router.
- Grove2USB-C and external OLED roles remain unfinalized until hardware bring-up
  proves the cable topology, controller, address, and pins.

M5Stack Unit Fader U123 is an analog input path for the slider plus a separate
SK6812 RGB data path for 14 onboard LEDs. The ADC driver only reads brightness;
Unit Fader RGB routing is separate bring-up work and must not be routed through
Pa.HUB as if it were I2C.
Rejected direct fader+RGB map: ADC `G1/G2/G4/G7/G8` plus SK6812 data
`G3/G5/G6/G43/G44`. Do not use it for production; `G1..G4` share internal
PMIC/speaker/IMU functions on StickS3, and `G9/G10` stays reserved for the
remaining Grove/I2C topology. Use an external ADC/mux or explicitly verified shared pin strategy before real fader upload.
The 2026-06-14 `sticks3-terminal-g4-adc-smoke` run is the shared-pin acceptance
for G4: it observed raw 0 and raw 4095 endpoints plus intermediate movement
while the fader was moved.
The two switch pins default to disabled and can be supplied later through build
flags: `-DTERMINAL_UPLOAD_SWITCH_PIN=<pin>` and
`-DTERMINAL_SIM_FIRE_SWITCH_PIN=<pin>`.
The mechanical switch debounce window defaults to 30 ms and can be tuned during
bring-up with `-DTERMINAL_SWITCH_DEBOUNCE_MS=<ms>`.
The fader filter maps raw ADC samples to `0..100` brightness and suppresses
small jitter. Bring-up can tune `-DTERMINAL_FADER_RAW_MIN=<raw>`,
`-DTERMINAL_FADER_RAW_MAX=<raw>`, and
`-DTERMINAL_FADER_DEADBAND_PERCENT=<percent>`. Inverted wiring is supported by
setting rawMin greater than rawMax; for the verified G4 fader orientation,
physical bottom is raw 4095 and maps to 0 percent brightness, while physical top
is raw 0 and maps to 100 percent brightness.
The real fader driver can prime current raw positions at boot. After rollback,
it locks each fader until the physical slider reaches the restored brightness,
so stale physical positions do not immediately overwrite the saved draft.
The fader ADC reader is disabled by default. Enable it only after all five final
ADC GPIOs are known by setting `-DTERMINAL_FADER_ADC_ENABLED=1` plus
`-DTERMINAL_FADER_LANE1_ADC_PIN=<pin>` through
`-DTERMINAL_FADER_LANE5_ADC_PIN=<pin>`. The raw min/max/deadband flags calibrate
readings; they do not select pins and do not enable sampling.
The encoder filter maps raw absolute chain-encoder positions to color-step deltas. The
first valid position primes without a color jump, and bring-up can tune
`-DTERMINAL_ENCODER_DEGREES_PER_DETENT=<degrees>`.
The configured chain encoder driver is disabled by default with
`TERMINAL_CHAIN_RX_PIN=-1` and `TERMINAL_CHAIN_TX_PIN=-1`; in that mode
`ConfiguredChainEncoderDriver` uses `MissingChainEncoderRawReader` and is a safe
no-op. Set both `-DTERMINAL_CHAIN_RX_PIN=<pin>` and
`-DTERMINAL_CHAIN_TX_PIN=<pin>` together to enable the M5Chain raw reader;
`-DTERMINAL_CHAIN_BAUD=<baud>` defaults to 115200. The M5Chain raw reader feeds
raw absolute positions and button press events into the pure encoder filter;
`ControlSurface` still owns named-palette stepping and press-edge toggles.
Encoder button toggles whether that lane changes state during fire; double-click
is ignored.
For final hardware acceptance, add `-DTERMINAL_REQUIRE_CHAIN_UART=1`; the build
then fails unless both Chain UART pins are configured.
Enabling the Chain UART only selects the reader. It does not prove lane order,
detent direction, encoder-button fire-change semantics, or press debounce; those
remain hardware bring-up checks.
The current firmware has the setup state model, USB link, switch pipeline,
switch driver, M5Chain dependency, built-in status panel, and an optional
M5UnitGLASS2 external OLED sink; it does not yet include real fader sampling,
PaHUB driver logic, Grove2USB-C bridge proof, or a validated LaskaKit 2.42 inch
OLED sink.
The app logic layer is pure C++: it decides upload, simulate-fire, ACK accept,
ERR/timeout rollback, and redraw/send-line actions. `main.cpp` keeps the
hardware side of those actions: it drains stale USB input before starting an
upload, then uses `Serial.println`, `millis`, and M5 display rendering.
The switch pipeline is also pure C++: raw active-low switch samples are
debounced, converted to one-shot edges, and reduced to at most one action per
poll. Upload has priority over simulate-fire, and held switches must be released
and pressed again after upload completion.
The switch debounce layer is pure C++ and sits before edge tracking. Raw
active-low samples must remain stable for `SWITCH_DEBOUNCE_MS = 30` ms before
they become press/release edges.

Hardware bring-up checklist:

| Slice | Current proof | Remaining hardware proof |
| --- | --- | --- |
| fader filter | Host-style test covers raw-to-percent mapping, missing samples, deadband, per-lane filtering, reset, priming, rollback pickup lock, and invalid lanes. | Tune raw min/max/deadband on the actual fader rail. |
| encoder filter | Host-style test covers first-position priming, detent scaling, missing samples, per-lane tracking, reset, invalid lanes, and button/effect passthrough. | Tune detent scale and verify lane order/direction on the real chain. |
| control surface mapper | Host-style test covers sliders, encoder deltas, encoder press edges, and effectPressed edges. | Feed real fader and encoder-button fire-change samples into the mapper. |
| switch pipeline | Host-style test covers debounce, boot-held priming, upload priority, and in-flight suppression together. | Confirm the complete physical switch path on the backplane. |
| switch debounce | Host-style test covers press bounce, release bounce, independent channels, and boot priming. | Tune debounce timing against the real mechanical switches. |
| switch dispatch | Host-style test covers upload priority, in-flight suppression, and release/repress after held software preview input. | Confirm simultaneous physical switch behavior on hardware. |
| app logic | Host-style test covers upload, sim-fire, accept, reject, fader pickup lock on reject, and no-op ACK events. | Confirm real USB timing against DinMeter. |
| USB setup link | Terminal firmware builds and formats `SETUP <request_id>`; DinMeter replies with `SETUP_OK <request_id>` / `SETUP_ERR <request_id>`. | Confirm cable topology and timeout behavior with the real prop. |
| external display formatter | Pure formatter returns five framed operator rows with color, brightness/on-off, and fire-change participation, without status/menu text. | Bind it to the real display driver once the bus/controller is fixed. |
| fader driver | ADC reader seam is present but disabled by default; missing-reader mode remains a safe no-op. | Configure five ADC pins, calibrate raw min/max/deadband, and verify stable percent values. |
| chain encoder driver | M5Chain UART hook is present but disabled until RX/TX pins are configured; disabled mode is a safe no-op. | Verify lane order, detent direction, encoder-button debounce, and fire-change press mapping. |
| switch driver | Active-low pin adapter is isolated from one-shot edge logic. | Confirm physical pins, wiring polarity, and no-repeat hold behavior on the backplane. |
| external OLED driver | `DisplayRenderPlan` keeps five framed lane rows inside the 128x64 pixel budget; hardware mode is disabled by default. | Confirm controller, address, pins, font, and refresh rate on the 128x64 module. |

Expected external display sample:

`DisplayRenderPlan` is fixed at five framed rows for the 128x64 large OLED.
Each row is one LED lane with a lane number box, color label, brightness text,
a small brightness bar, and an `ODP`/`---` effect box. Status and menu text stay on the built-in M5StickS3 status panel, never on the large OLED.
Run the OLED I2C scan smoke before enabling a display sink. External OLED is disabled by default and remains a safe no-op until real
hardware bring-up. Enable the M5GFX `M5UnitGLASS2` sink only for a confirmed
M5UnitGLASS2-compatible panel with `-DTERMINAL_EXTERNAL_OLED_ENABLED=1`,
`-DTERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2=1`,
`-DTERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED=1`,
`-DTERMINAL_EXTERNAL_OLED_SDA_PIN=<pin>`, and
`-DTERMINAL_EXTERNAL_OLED_SCL_PIN=<pin>`; optional
`-DTERMINAL_EXTERNAL_OLED_I2C_ADDRESS=<addr>`,
`-DTERMINAL_EXTERNAL_OLED_I2C_PORT=<0-or-1>`, and
`-DTERMINAL_EXTERNAL_OLED_I2C_FREQ=<hz>` tune the bus. The LaskaKit 2.42 inch
128x64 OLED must not be treated as M5UnitGLASS2 until its controller and bus
address are confirmed; it may need its own sink. Controller, bus address, and pins are hardware bring-up checks,
not confirmed defaults. OLED bring-up may select hardware; it must not change
the lane-only display contract.

```text
1 CERVENA 100% ---
2 ORANZ   80%  ODP
3 TYRKYS  45%  ---
4 BILA    VYP  ODP
5 MODRA   75%  ---
```

Switch edge bring-up:

- Pins default to `-1` disabled until the backplane is finalized.
- Configured pins use `INPUT_PULLUP` and are active-low.
- One stable debounced switch press: at most one command.
- Hold switch: no repeated command.
- Release and press again: exactly one new command.
- Switch held while Terminal boots: no command is sent, no action is queued,
  and release/press is required after boot.
- During upload, upload and software preview/aux switch edges are ignored until
  the current upload accepts, rejects, times out, or overflows.

Power and signal safety:

- Do not power the full fader, encoder, OLED, and hub stack from the StickS3
  Grove port.
- Use a current-limited or fused external 5V rail with common ground.
- Unit Fader analog lines must land only on 3.3V-safe ADC pins; the SK6812 RGB
  data path and power budget for 14 LEDs per fader are separate from ADC
  calibration.
- Avoid backfeeding StickS3 `EXT_5V` or Grove power when the port is configured
  as an output source.
- Level-shift any 5V logic before it reaches 3.3V GPIO or ADC pins.
- Switch inputs must short only to GND and use `INPUT_PULLUP`.
