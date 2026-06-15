# DualKey Broadcast TX Design

Date: 2026-06-15

## Goal

Build a minimal handheld prop controller from:

- M5Stack Chain DualKey C147
- M5Stack Unit C6L LoRa modem

The controller is not a replacement for the M5 Dial fire UI. It is a two-action broadcast controller for props that already share the project runtime key. It must work when multiple receivers are present and when ACK traffic is noisy or collides.

Hardware references:

- Chain DualKey C147: ESP32-S3FN8, two keys on G0/G17, two WS2812B LEDs on G21, LED power enable on G40, two UART HY2.0 ports.
- Unit C6L: ESP32-C6 + SX1262 LoRa, 64x48 SSD1306 OLED, WS2812C RGB LED, buzzer, Grove UART on G5/G4.

## Confirmed Behavior

The two C147 keys map to two independent prop actions:

- Key 1: toggle the default blue LED state. The transmitter owns the desired on/off state and sends `BLUE_SET on/off`. Receivers set the state to that value. They do not locally toggle on every received frame.
- Key 2: trigger the barrel effect once per press. Receivers must suppress duplicate copies of the same event so a retransmitted frame does not replay the effect multiple times.

Both actions are broadcast to every compatible receiver:

- `destination = 0xFF`
- existing HMAC runtime key and key id
- existing sequence and nonce replay protections
- no required single ACK before the controller considers the user action sent

## Why Set-State For Blue

Broadcast retransmission and multi-receiver LoRa are intentionally messy. A receiver may hear one, two, or all repeated frames.

For Key 1, a raw `TOGGLE` command would be unsafe because duplicate accepted frames could flip the LED twice. The controller instead keeps local desired state:

- first press sends `BLUE_SET 1`
- second press sends `BLUE_SET 0`
- retransmissions carry the same desired state/event identity

That makes the action idempotent.

For Key 2, the action is a one-shot effect. Retransmissions must use the same event identity or sequence/nonce so receiver replay filtering can suppress duplicates.

## Architecture

### Chain DualKey firmware

Add a new PlatformIO firmware project:

`firmware/dualkey-tx`

Responsibilities:

- read C147 Key 1 and Key 2
- debounce and edge-detect button presses
- maintain the desired blue LED state
- construct authenticated `prop_protocol` frames
- write frames to Unit C6L over UART as `FF <hex>\n`
- drive C147 RGB LEDs as local feedback

The C147 must not send setup/editor frames:

- no `PaletteSet`
- no `LedColorSet`
- no Terminal setup upload protocol
- no Dial ARM/FIRE UI flow unless explicitly added later

### Unit C6L modem firmware

Keep `firmware/c6l-modem` as the transport and status device.

The modem already accepts `FF <hex>` for no-ACK radio forwarding and has a 64x48 OLED status path. It should remain mostly generic. Optional TX status additions may show:

- `BLUE ON`
- `BLUE OFF`
- `BARREL`
- `TX`
- `RX`
- `ERR`

The modem must not become the prop action authority. It only forwards frames and displays link health.

### Receiver path

DinMeter/XIAO stays the action authority. It validates:

- HMAC and key id
- source address for the new DualKey transmitter
- destination is either its own address or the broadcast address `0xFF`, depending on frame type
- replay/duplicate window
- payload shape

Current receiver routing rejects any frame whose destination is not its own address. The implementation must change that narrowly: broadcast destination is accepted only for the new DualKey action frame(s), not globally for every legacy frame.

## Protocol Shape

Use the existing `prop_protocol` frame envelope.

Add a small action command rather than overloading palette/setup frames:

- action: `BLUE_SET`
- action: `BARREL_EFFECT`

The exact encoding can be either:

1. a new `FrameType` for prop actions with compact payload `{action_id, value, event_id...}`;
2. two explicit new `FrameType` values.

Recommendation: one new `FrameType::PropAction` with a tiny payload. It keeps the protocol enum from growing one type per prop action and gives receivers one clear broadcast gate.

Payload v1:

- byte 0: action id
- byte 1: value
- bytes 2-5: event id, copied from or derived from sequence for duplicate-safe diagnostics

Action ids:

- `1 = BLUE_SET`, value `0/1`
- `2 = BARREL_EFFECT`, value currently ignored

## ACK Policy

The controller must not wait for one matching ACK for broadcast actions.

Reasons:

- multiple receivers may answer at once
- LoRa ACK collisions can look like failure even when the prop executed
- a single missing receiver must not block the whole handheld controller

Receiver ACKs may still be emitted with random jitter later for diagnostics, but first implementation treats them as optional telemetry only.

## Safety And Failure Behavior

- Runtime key provisioning remains mandatory before hardware acceptance.
- Receivers that do not recognize `PropAction` must ignore it.
- Replayed/stale prop actions must not execute.
- Duplicate `BARREL_EFFECT` copies must not retrigger the effect.
- Duplicate `BLUE_SET` copies are harmless because the command is set-state.
- STOP behavior for the existing Dial path is unchanged.
- This controller does not replace the Dial's safety-oriented firing path unless explicitly approved later.

## Test Plan

Host tests before hardware upload:

- DualKey button state machine:
  - Key 1 press alternates desired blue state.
  - Key 2 press emits one barrel event.
  - held buttons do not repeat without a fresh edge.
- Protocol tests:
  - DualKey action frames use `destination = 0xFF`.
  - frames use the project key id and new DualKey source address.
  - no palette/setup/editor frame types are emitted.
  - `BLUE_SET` retransmissions are idempotent.
  - `BARREL_EFFECT` retransmissions share a duplicate-suppressible event identity.
- Receiver tests:
  - current direct-address frames still work.
  - broadcast destination is accepted for `PropAction`.
  - broadcast destination remains rejected for unrelated legacy frames unless explicitly allowed.
  - stale/duplicate actions are dropped.
- Modem tests:
  - `FF <hex>` remains no-ACK forwarding.
  - status rendering does not require ACK success.

Build checks:

- `pio run -d firmware/dualkey-tx -e chain-dualkey-c147`
- `pio run -d firmware/c6l-modem -e m5stack-c6l`
- existing DinMeter, Terminal, protocol, and host test suites.

## Open Implementation Choices

These are intentionally left for the implementation plan:

- final numeric value for `FrameType::PropAction`
- final DualKey source address
- UART port selection on C147: HY2.0 port 1 or port 2
- local C147 LED feedback colors
- whether C6L OLED action labels are driven from host UART annotations or inferred from frame decode

