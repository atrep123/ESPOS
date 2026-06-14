# M5StickS3 Terminal Architecture

The Terminal is the accessible setup surface for the ESPOS prop chain. Terminal
owns setup editing. DinMeter remains the receiver-side safety authority and LED
execution surface.

Terminal has no radio module, no radio modem path, and no radio protocol sender.
Dial remains the radio fire controller, keeps the old fire-focused design, and
Dial does not own setup editing.

Hardware bring-up is still staged. The current firmware has tested setup,
USB-link, switch, fader-filter, encoder-filter, M5Chain dependency, and display
format boundaries, but final fader ADC wiring, chain lane order, encoder-button
fire-change mapping, and external OLED IO still need bench proof.

## Bench Wiring Snapshot 2026-06-14

This snapshot records the intended physical bench wiring. It is not yet proof
that every module behind the hubs can be read by the current firmware.

- M5StickS3 connects by USB-C to the PC for build, flash, USB diagnostics, and
  the local setup-link role.
- M5StickS3 Grove cable goes to the primary Pa.HUB v2.1.
- Primary Pa.HUB port 0 carries the serial chain branch:
  `Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch`.
- Bench smoke on 2026-06-14 selected Pa.HUB `0x70` channel 0 over Grove I2C
  SDA G9 / SCL G10, then M5Chain UART worked with RX G10 / TX G9. The opposite
  UART direction timed out.
- The first U207 Chain Encoder in that branch belongs to LED 5. The last U207
  encoder before the switches belongs to LED 1.
- The first U206 switch uploads the staged values to the prop over the USB-C
  setup-link path.
- The second U206 switch is the global SIM_FIRE preview switch. It emits a
  setup-link preview edge only; it must not commit setup values or call the
  radio fire path.
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
  The runtime serial output tracked fader movement from raw 0 to 4095, so G4 is
  accepted as the verified shared-pin candidate for the fifth slider ADC. This
  consumes the StickS3 IMU interrupt pin; do not use IMU interrupt or low-power
  IMU wake features in the Terminal build. The observed direction is inverted:
  physical bottom is raw 4095 and physical top is raw 0.
- Primary Pa.HUB port 1 is reserved for now; do not connect Pot5 there for
  signal reads.
- Primary Pa.HUB port 2 is reserved for now; do not connect Pot4 there for
  signal reads.
- Primary Pa.HUB port 3 is the external 2.4 inch display branch.
- Primary Pa.HUB port 5 goes to the secondary Pa.HUB v2.1.
- Secondary Pa.HUB ports 2, 3, and 4 are reserved for now; do not connect
  Pot3, Pot2, or Pot1 there for signal reads.

Lane numbers are logical Terminal lane IDs. `LED1` through `LED5` remain stable
logical names used by configuration, effects, UI, setup upload lines, and logs.
The physical encoder chain order is documented separately as
`DATA IN -> LED5 -> LED4 -> LED3 -> LED2 -> LED1 -> upload switch -> sim-fire switch`.
Do not infer logical lane numbering from the physical daisy-chain order.
Firmware maps logical lanes LED1..LED5 through `CHAIN_ENCODER_IDS = {5, 4, 3, 2, 1}`.

Confirmed module facts:

- Pot1..Pot5 are M5Stack Unit Fader U123 modules: B10K analog slider plus
  14x SK6812 programmable RGB LEDs.
- The Unit Fader Grove pin map is `GND / 5V / RGB / Analog Input`, so each
  module has two non-I2C signals that matter for Terminal: one analog slider
  output and one digital SK6812 RGB data input.
- Pa.HUB port ownership in this document records the remaining bench layout, not a final electrical solution for the Unit Faders. Pa.HUB must not be used as the final route for the analog slider output or the SK6812 RGB data line.

Open bench checks before driver finalization:

- Do not use the rejected direct RGB map `ADC G1/G2/G4/G7/G8` plus
  `RGB G3/G5/G6/G43/G44` for production.
- Choose the fifth slider ADC strategy before real fader upload: external
  ADC/mux for all five sliders, a small fader MCU that reports values over
  I2C/UART, or one measured and accepted shared StickS3 pin from `G1..G4`.
  The 2026-06-14 G4 smoke accepted G4 as that measured shared StickS3 pin: it
  observed raw 0 and raw 4095 endpoints plus intermediate movement while the
  fader was moved.
- Confirm the primary/secondary Pa.HUB I2C addresses and whether the second
  Pa.HUB is cascaded through primary port 5 exactly as listed above.
- Confirm whether Pa.HUB port numbers mean the printed labels `0..5`; firmware
  constants use those printed zero-based labels.
- Confirm the exact external 2.4 inch display controller, I2C address, and
  reset/backlight wiring before enabling a real display sink.
- Confirm the Grove2USB-C setup-link path electrically. Do not treat Grove2USB-C
  as normal I2C/UART until the adapter role is measured.
- Confirm shared 5V/common-ground power, current limit, no backfeed into
  StickS3 power, and 3.3V-safe GPIO/ADC levels.

## Direct Controls

- Five logical lanes map left-to-right to LED 1 through LED 5.
- Each lane has one fader/slider for brightness. Fader brightness 0 means the lane is normally off; any value above 0 means the lane is normally on.
- Raw fader samples pass through a pure fader filter before they become
  `sliderPercent` updates. The filter maps calibrated ADC range to `0..100` and
  suppresses small percent jitter with a deadband.
- The fader filter can prime the current physical position without publishing
  it. After rollback it can also lock a lane until the physical fader reaches
  the restored value, so stale physical positions do not immediately overwrite
  the saved draft.
- M5Stack Unit Fader is an analog slider input plus separate SK6812 RGB data.
  The Terminal fader ADC path reads brightness only; RGB routing for the fader's
  own 14 SK6812 LEDs is separate hardware work.
- Each lane has one encoder for stepping through the named color palette.
- Raw chain-encoder positions pass through a pure encoder filter before they
  become `encoderDelta` updates. The first absolute position primes without a
  color jump, then detent movement steps through the palette.
- Encoder button toggles whether that lane changes state during fire: a
  normally on lane turns off during fire, and a normally off lane turns on.
- Fire-change participation is stored per LED. The control model also keeps a
  per-lane `effectPressed` compatibility edge for older tests and adapters; both
  edges toggle the same per-lane fire-change flag without page navigation.
- Double-click is intentionally ignored until hardware testing proves it is
  needed.
- There is no menu navigation. The operator should not need a page button, mode
  button, or hidden focus movement to change ordinary LED settings.

## Displays

- The large external display shows one framed row per LED: LED number, color
  name, brightness or `VYP`, a small brightness bar, and `ODP`/`---` fire-change
  participation.
- Brightness, normal on/off state, and fire-change participation are visible on
  the large display, because there is no page navigation or hidden focus
  movement.
- `DisplayRenderPlan` targets a 128x64 OLED pixel budget: exactly five framed
  lane rows with deterministic field boxes.
- The large external display is lane-only: no title, status, menu, page, or
  hidden focus text may be rendered there.
- The M5StickS3 display is only a secondary status panel. It shows states like
  `NAHRANO` on green background and `PROBLEM` on red background.

## Upload And Revert

- All physical edits first change a staged draft.
- A stable upload switch press asks app logic to send the staged draft over the
  USB setup link to the prop.
- If the prop accepts the upload, the draft becomes the saved state.
- If the prop rejects the upload or the link fails/times out, the draft reverts
  to the previous saved state.
- `PROBLEM` remains latched on the built-in status panel after rollback. Later
  physical control movement may edit the draft, but it must not hide the error
  state before the next upload attempt.
- `SIM_FIRE` is the setup-link preview command driven by the last physical U206
  switch. It is a preview-only command and never commits setup values.

## Switch Edge Model

- `TERMINAL_UPLOAD_SWITCH_PIN` and `TERMINAL_SIM_FIRE_SWITCH_PIN` default to
  `-1`, which disables direct GPIO switch inputs until wiring is finalized. The
  Chain branch maps the last U206 to the same `SIM_FIRE` switch snapshot.
- Configured switch pins use `INPUT_PULLUP` and are active-low: released is
  HIGH, pressed/shorted to ground is LOW.
- Raw switch samples pass through a pure switch debounce layer before edge
  detection. The default debounce window is `SWITCH_DEBOUNCE_MS = 30`, so short
  mechanical bounce cannot create extra upload or preview/aux edges.
- Commands fire only on the unpressed-to-pressed edge. Holding a switch must not repeat a command; release rearms the next edge.
- The pure switch pipeline owns debounce, edge tracking, and dispatch priority.
  `main.cpp` only feeds raw active-low snapshots into the pipeline and performs
  the returned action.
- During boot, Terminal primes the switch pipeline from the current switch
  levels after configuring the active-low pins. A switch already held at startup
  is treated as held, not as a new command, no action is queued, and the switch
  must be released/repressed.
- Upload edges freeze and send the current staged setup. Upload edges while an
  upload is already in flight are ignored.
- Software preview edges ask app logic to emit `SIM_FIRE` only when no upload is
  in flight. Preview while uploading is ignored and never commits setup values.

## USB Setup Link

- Shared parser and formatter live in `shared/terminal/terminal_setup_link.h`.
- Terminal sends one complete setup line:
  `SETUP <request_id> L1:color,brightness,on,effect L2:color,brightness,on,effect L3:color,brightness,on,effect L4:color,brightness,on,effect L5:color,brightness,on,effect`.
- The first field accepts legacy hue `0..359` for compatibility and named
  palette color codes `360..368` for new Terminal uploads. Brightness is
  `0..100`, and on/effect are `0` or `1`.
- DinMeter replies with `SETUP_OK <request_id>` / `SETUP_ERR <request_id>`;
  Terminal must not accept generic modem-style `OK` or `ERR` debug lines,
  bare setup replies, or replies with a mismatched request id as setup
  confirmation.
- Terminal waits `UPLOAD_ACK_TIMEOUT_MS = 1500` ms. Timeout rejects the upload
  and rolls the staged draft back to the last saved values.
- Terminal accepts at most `USB_LINE_MAX = 160` bytes per reply line. Line
  overflow during upload is treated as link failure and rolls back.
- Before starting a new upload, Terminal drains stale setup replies already
  buffered on USB so an old `SETUP_OK <request_id>` cannot confirm the next
  staged draft.
- Timeout is polled before reply bytes in the main loop, so a late ACK after
  `UPLOAD_ACK_TIMEOUT_MS` rolls back instead of committing stale state.
- `SETUP <request_id>` is atomic on DinMeter for parsing, validation, and
  persistence failures. Terminal request-id mismatch, line overflow, or timeout
  rolls Terminal's staged draft back to the last saved values; if DinMeter
  already processed and persisted the line before the reply was lost, the
  receiver-side setup may already be committed.
- `SIM_FIRE` is a local USB setup-link preview command. It must not call the
  radio frame parser, authenticated fire path, or live fire trigger helpers.

## Boundaries

- Terminal owns setup editing: colors, brightness/normal on-off state,
  fire-change participation, upload, and local preview.
- Dial remains the radio fire controller and should not regain setup controls.
- DinMeter remains the receiver-side safety authority: frame validation,
  fire-gate behavior, LED output, and indication.
- The radio transport remains outside Terminal.

## Current Terminal Implementation

| Area | State |
| --- | --- |
| Five-lane state model | Implemented in `TerminalSetupState`: saved draft, staged draft, upload snapshot, rollback, and setup-line formatting. |
| Fader filter | Implemented as a pure fader filter for raw ADC-to-percent mapping, missing samples, deadband, per-lane last values, and rollback pickup locks. |
| Fader driver | Implemented with a raw-reader seam: default missing-reader mode is safe no-op, while `ArduinoAdcFaderRawReader` can be enabled later with five ADC pins. |
| Encoder filter | Implemented as a pure encoder filter for absolute position priming, missing samples, signed movement deltas, per-lane last positions, and button/effect level passthrough. |
| Chain encoder driver | Implemented with a raw-reader seam: disabled config uses `MissingChainEncoderRawReader` as a safe no-op, while configured Arduino builds can use `M5ChainEncoderRawReader` through `ConfiguredChainEncoderDriver` after Chain UART RX/TX pins are set together. |
| Physical input mapper | Implemented as `ControlSurface`: five filtered slider percentages, five encoder deltas, encoder press rising edges, `effectPressed` rising edges, and post-upload edge priming can mutate the staged draft without menu navigation. |
| App logic | Implemented as a pure app logic layer for upload requests, software preview requests, ACK/ERR handling, and rollback decisions. |
| Switch pipeline | Implemented as a pure pipeline that debounces raw switch samples, converts stable presses into edges, and dispatches at most one action per poll. |
| Switch dispatch | Implemented as a pure policy layer used by the switch pipeline. Upload has priority over the software preview/aux input from debounced switch edges. |
| Switch boot priming | Implemented by priming `SwitchPipeline` from `SwitchDriver` in `setup()` so held switches at startup are not commands. |
| Switch debounce | Implemented as a pure debounce layer between raw active-low pin reads and edge tracking. |
| Upload link | Implemented with shared parser/formatter and explicit `SETUP_OK <request_id>` / `SETUP_ERR <request_id>` replies. |
| Upload race guard | Implemented with an upload snapshot, so confirmation stores exactly the draft that was sent. |
| External display formatter | Implemented as a pure external display formatter that returns five framed operator rows with color, brightness/on-off, and fire-change participation, with no status/menu text. |
| Built-in M5StickS3 display | Implemented as a secondary status panel. |
| OLED pixel budget | Implemented as `DisplayRenderPlan` with fixed five-row field geometry for 128x64 framed rendering. |
| SwitchDriver | Implemented as the active-low Arduino pin adapter; the pure `SwitchEdgeTracker` still owns one-shot edge behavior. |

## Open Hardware Drivers

## Terminal hardware topology contract

- Planned controller: 1 M5StickS3.
- Planned lane controls: 5 Unit Faders and 5 Chain Encoders, one of each per
  LED lane.
- Planned command switches: 2 mechanical switches, upload and sim-fire preview.
- Planned adapters: 2 PaHUB modules and 2 Grove2USB-C adapters.
- Planned external display: 1 external 128x64 OLED.
- Terminal has no radio module. Dial remains the radio fire controller.
- PaHUB must not be assumed to route Unit Fader reads or LEDs. The first slice
  reads slider values only and leaves fader LEDs disabled/deferred, but bare
  StickS3 still does not safely provide five clean direct ADC lines while the
  rest of Terminal remains attached.
- Grove2USB-C and external OLED roles are explicitly not finalized until hardware
  bring-up proves the cable topology, controller, address, and pins.

- The fader driver has an ADC reader seam that is disabled by default. Real
  hardware work needs final ADC/backplane wiring, raw calibration, and separate
  SK6812 RGB data routing for the 14 onboard LEDs on each fader.
- The configured chain encoder driver has an M5Chain raw-reader hook that is
  disabled until RX/TX pins are configured. Real hardware work needs bus
  ordering, lane IDs, detent direction, and press debounce validation.
- External OLED driver is disabled by default, and the external OLED driver
  remains a safe no-op until real hardware bring-up. Real hardware work needs controller,
  bus/address, pins, text font, and refresh policy.
- OLED I2C scan smoke is the first hardware step before any LaskaKit sink:
  compile `sticks3-terminal-oled-i2c-scan-smoke` with actual SDA/SCL pins, capture
  `OLED_I2C_SCAN FOUND 0x..` over USB, and only then decide whether the panel is M5UnitGLASS2-compatible or needs its own sink.
- The Grove2USB-C role is still open: native USB cable, setup-link adapter, UART
  bridge, or removed from the final wiring.
- PaHUB channel ownership is now recorded only for the remaining non-fader bench
  paths. PaHUB must still not be assumed to solve analog fader reads or SK6812
  fader LED data.

## Hardware Stub Contracts

- `FaderDriver` writes only `sliderPercent`. A missing sample must remain
  `SLIDER_UNCHANGED`, so stale or disconnected faders do not overwrite the
  staged draft. `terminal_fader_filter.h` owns raw ADC clamping, percent mapping,
  deadband, priming, rollback pickup locks, and per-lane last values before the
  driver writes `sliderPercent`. `TERMINAL_FADER_ADC_ENABLED` must stay disabled
  until all five final ADC pins are configured.
- `ChainEncoderDriver` writes only `encoderDelta`, `encoderPressed`, and
  `effectPressed`. `terminal_encoder_filter.h` owns absolute position priming,
  missing samples, signed movement deltas, and per-lane last positions before
  the driver writes `encoderDelta`. `ControlSurface` owns named-palette stepping
  and both rising-edge press toggles. After upload completion, `main.cpp` primes direct
  control edges from the current physical snapshot so held encoder/effect inputs
  do not immediately erase `PROBLEM` or replay stale edits.
- `ConfiguredChainEncoderDriver` owns raw-reader selection only. With no
  configured Chain UART, it must use `MissingChainEncoderRawReader` and emit
  missing positions plus false press levels so setup state remains unchanged.
  When `M5ChainEncoderRawReader` is active, it may call M5Chain APIs such as
  `getEncoderValue` and `getEncoderButtonStatus`, but it still feeds
  `terminal_encoder_filter::EncoderSample` through `EncoderFilter`;
  `ControlSurface` remains the owner of named-palette stepping and rising-edge toggles.
- `ExternalOledDriver` consumes `terminal_external_display::DisplayFrame` and
  the pure `DisplayRenderPlan`. It does not own lane formatting, USB setup
  traffic, status transitions, menu/page/focus text, or radio/fire behavior.
  Controller, bus address, and pins are hardware bring-up checks, not confirmed
  defaults. OLED bring-up may select hardware, but it must not change the
  lane-only display contract.
- `SwitchDriver` is only the active-low pin adapter. It configures enabled
  switch pins with `INPUT_PULLUP` and returns a `SwitchSnapshot`; it does not
  debounce, send USB lines, change setup state, or own upload gating.
- `terminal_switch_pipeline.h` owns the pure switch path from raw
  `SwitchSnapshot` to `SwitchAction`. It combines debounce, one-shot edge
  tracking, upload priority, and in-flight suppression without Arduino, USB, or
  display dependencies.
- `terminal_switch_dispatch.h` owns switch dispatch policy. `SwitchEdgeTracker`
  may report both upload and software preview/aux raw edges for a simultaneous
  physical press, but switch dispatch chooses only one action: upload wins, the
  preview/aux path is suppressed during upload, and a held preview/aux input
  needs release/repress after upload completion.
- `terminal_switch_debounce.h` owns switch debounce. It consumes raw
  `SwitchSnapshot` samples and returns the last stable snapshot. It does not
  know USB commands, dispatch policy, setup state, or hardware pins.
- `terminal_app_logic.h` owns setup-link decisions: start upload, emit
  `SIM_FIRE`, commit exact accepted snapshots, and roll back rejected uploads.
  Rejected uploads also ask `main.cpp` to lock faders to the restored draft until
  pickup. It has no Arduino, display, pin, USB drain, or radio dependency;
  `main.cpp` drains USB input before `startUploadAfterUsbDrain()`, then performs
  returned actions by printing command lines, locking faders, and redrawing
  displays.
- Stub drivers must not print to USB, emit `SETUP`/`SIM_FIRE`, or depend on the
  radio protocol. `main.cpp` remains the only place that sends setup-link
  command lines.

## Hardware Notes

- PaHUB does not solve the faders. M5Stack Unit Fader exposes analog input plus
  SK6812 RGB data, not I2C; the analog slider and fader LEDs require their own
  safe signal paths.
- Use an external 5V rail with common ground for the faders, chain modules, OLED,
  and hubs.
- Do not power the whole fader/encoder/OLED stack from the StickS3 Grove port.
  Current-limit or fuse the 5V rail, avoid backfeeding `EXT_5V`/Grove power, and
  level-shift any 5V logic before it reaches 3.3V GPIO or ADC pins.
- Switch pins must short only to GND when configured with `INPUT_PULLUP`.
- The fader bank needs direct ADC/RGB wiring, an analog/RGB backplane, or a
  future hardware substitution.
- `TERMINAL_FADER_RAW_MIN`, `TERMINAL_FADER_RAW_MAX`, and
  `TERMINAL_FADER_DEADBAND_PERCENT` calibrate readings only; they do not select
  pins or enable hardware sampling. Inverted wiring is supported by setting
  rawMin greater than rawMax; for the verified G4 fader orientation, physical
  bottom is raw 4095 and should map to 0 percent brightness, while physical top
  is raw 0 and should map to 100 percent brightness.
- Encoder bus order for this bench snapshot is LED5, LED4, LED3, LED2, LED1,
  then upload U206, then sim-fire U206. Production maps this physical order
  back to logical LED1..LED5 with `CHAIN_ENCODER_IDS = {5, 4, 3, 2, 1}`.
  Firmware still needs on-device proof of
  Chain IDs, detent direction, encoder-button fire-change participation, and
  ignored double-click behavior.
- Grove2USB-C role is still open: decide whether it is only the USB setup cable,
  a setup-link adapter, a UART bridge, or removed from the final wiring.
- The external 2.42 inch OLED bus/address/driver are still open; current
  firmware has a no-op external OLED boundary. Lane text belongs only on the
  external display path; the built-in M5StickS3 display remains status-only.
- The upload and sim-fire switch pins are build-time overrides until the
  backplane pin map is finalized.
