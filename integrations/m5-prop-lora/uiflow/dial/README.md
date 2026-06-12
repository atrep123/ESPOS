# UIFlow2 Dial port — protocol-parity PoC

Proof-of-concept for porting **only the Dial UI** to M5Stack UIFlow2 (MicroPython)
while keeping the C++ LoRa modems, the DinMeter receiver, and all safety logic
exactly as they are. This PoC delivers the **hard part** of that port — the
authenticated frame encoder — and proves it is **byte-for-byte identical** to the
current C++ firmware, so a UIFlow app could drive the existing modem + receiver
unchanged.

> Scope: the *protocol* layer (the "hard 20%") is proven byte-exact; **`main.py` now
> adds a first-iteration UI** on top (orb / action picker / per-LED colour edit + UART
> link) — the "easy 80%", to verify and tune on the actual M5Dial. See [Status](#status).

## Files

| File | Role |
|------|------|
| [`prop_frame.py`](prop_frame.py) | MicroPython encoder — frame header + hand-rolled HMAC-SHA256 + payload builders + `FF <HEX>\n` UART line. Mirrors `shared/protocol/prop_protocol.h`, `protocol.py`, and the Dial's `app_prop_tx.cpp` (SHARED_KEY, addressing, nonce). **Proven byte-exact.** |
| [`main.py`](main.py) | UIFlow2 Dial **UI app**: draws the orb / action picker / 5 LED swatches, reads the rotary encoder + push button, edits per-LED hue, persists the palette + sequence to NVS, and sends the proven `prop_frame` command lines over UART to the C++ modem. Protocol + persistence proven; display/input paths marked **VERIFY ON DEVICE**. |
| [`prop_state.py`](prop_state.py) | Pure persistence logic (no hardware imports → CPython-testable like `prop_frame.py`): palette↔blob codec + flash-wear-friendly sequence reservation. `main.py` supplies the thin `esp32.NVS` I/O. Proven by [`../../tests/test_uiflow_prop_state.py`](../../tests/test_uiflow_prop_state.py). |
| [`../../tests/test_uiflow_prop_frame_parity.py`](../../tests/test_uiflow_prop_frame_parity.py) | Parity test (CPython): asserts `prop_frame` == `protocol.py` byte-for-byte across every frame type, all payload encoders, the HMAC, the hex, and the UART line — then round-trips each frame through the real receiver-side verifier. |

## Why this proves C++ parity

```
prop_frame.py  ==(this PoC's 14 tests, byte-exact)==  protocol.py
protocol.py    ==(test_protocol_roundtrip_sim.py)==    prop_protocol.h (C++)
---------------------------------------------------------------------------
=> prop_frame.py  ==  the C++ firmware wire format
```

`protocol.py` is the Python reference that the existing suite already pins to the
C++ header (`test_protocol_py_constants_match_prop_protocol_h` + the full
encode→decode round-trip tests all pass). This PoC pins `prop_frame.py` to
`protocol.py`. Parity is therefore transitive.

## Run the parity test

```sh
python -m pytest tests/test_uiflow_prop_frame_parity.py -v
# 14 passed, 51 subtests passed
```

## On-device sanity check (the only thing CPython can't prove)

CPython cannot prove that the *M5 MicroPython* `hashlib.sha256` yields identical
digests — but SHA-256 is a fixed standard and the MP core implementation is
conformant, so this is guaranteed by spec. To confirm it on real hardware in two
minutes once UIFlow MicroPython is flashed, encode this exact frame and compare:

```python
import prop_frame as pf
colors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0)]
enc = pf.encode_frame(pf.PREVIEW, 1, 0x11, 0x22, 1, 0x00000001DEADBEEF,
                      pf.encode_led_payload(0xFF, colors))
print(pf.ff_line(enc).strip())
```

Expected (golden vector — identical to the C++ Dial):

```
FF 504C02030111220000000100000001DEADBEEF0DFFFF000000FF000000FFFFFF00BFDB63E1FFED7CB411008898
```

If the device prints that line, the MicroPython crypto path matches the firmware.

## Usage (what a UIFlow app would call)

```python
import prop_frame as pf
from machine import UART

uart = UART(1, baudrate=115200, tx=13, rx=15)   # Dial -> its LoRa modem
tx = pf.PropSender()                             # monotonic sequence + per-boot epoch

uart.write(tx.preview_line([(255,0,0),(0,255,0),(0,0,255),(255,255,0)]))
for line in tx.fire_burst_lines([(255,0,0),(0,255,0),(0,0,255),(255,255,0)]):
    uart.write(line)                         # production FIRE path: FF burst
uart.write(tx.stop_line())                       # STOP is the master off
uart.write(tx.remote_led_line(pf.REMOTE_LED_BIT_LED5))
```

`PropSender` mirrors the firmware's bookkeeping: `sequence` increments per frame
(the C++ side persists it in NVS — a real app should too), and `nonce` is
`(epoch << 32) | rand32` with a per-boot nonzero random epoch.

## MicroPython notes

- **`hashlib.sha256`** from the MP core (UIFlow MicroPython ≥ 2.x). Falls back to
  `uhashlib` on older builds.
- **HMAC is hand-rolled** on purpose. The MicroPython `hmac` stdlib relies on a
  `.copy()` method the M5 hashlib build does not expose (`AttributeError`). This
  module only ever creates fresh `sha256()` objects, sidestepping the bug.
- **Big-endian packing is manual** (bit-shifts) to avoid any `struct`-format
  differences between MP builds.

## Status

**Proven (CPython tests, byte-exact):** the whole protocol path — frame encode, HMAC,
payload builders, the `FF`/`SEND` UART line, the per-boot nonce.

**`main.py` — first iteration, VERIFY ON DEVICE:** the orb / action picker (NAHLED, ARM,
ODPAL, STOP, LED3, LED5) / 5 LED swatches, the rotary encoder + push button, per-LED hue
edit, and the UART send + `OK`/`ERR`/`RX` reply read. It runs on the proven `prop_frame`,
but UIFlow2 display/input method names can differ by firmware version — those call sites
are commented `VERIFY ON DEVICE` and funneled through small helpers so a rename is a
one-line fix.

**Done since the first iteration:** `sequence` + palette now **persist to NVS**
(`prop_state.py`, unit-tested) so a power-cycle keeps the operator's tuned colours and
never rewinds the frame counter; flash wear is bounded by reserving sequence numbers in
blocks (one write per 64 frames). Also fixed: the first iteration declared `global tx`
in `setup()` but never created the `PropSender`, so `tx` stayed `None` and **every send
failed with "TX FAIL"** — `tx` is now instantiated, resuming its sequence from NVS.

**Still to do for a faithful full port (all VERIFY ON DEVICE — need the M5Dial in hand):**
receiver-side FIRE confirmation display if the Dial should surface deferred ACK telemetry;
touch-zone input (currently encoder-only); polishing the layout to the round 240×240.
The UIFlow FIRE send path now mirrors the production C++ default: one authenticated FIRE
frame is emitted as a redundant `FF` burst, with receiver deduplication by sequence.

### Run on the M5Dial
1. Flash UIFlow2 MicroPython to the Dial (M5Burner), or use the UIFlow2 web IDE.
2. Upload the runtime modules — `prop_frame.py`, `prop_state.py`, `prop_ui.py`, and `main.py` — to the device (UIFlow2 file manager or `mpremote`).
3. Wire the Dial's Grove **Port A** to the LoRa modem: TX=GPIO13 → modem RX, RX=GPIO15 ← modem TX, plus GND/5V.
4. Run `main.py`. Rotate to pick an action, **press** to send; **long-press** to enter NASTAVENI (per-LED hue), press to step LEDs, long-press to sync the palette and return.
5. Confirm reactions on the modem OLED / the DinMeter, and the status line for `OK`/`ERR`/`RX`.

Safety smoke for any FIRE-capable UIFlow build:

- Use only a dummy/LED-only load. Do not connect live pyro or actuator outputs.
- FIRE before ARM must return `NOT_ARMED` or have no effect.
- ARM must report `ARMED`; FIRE is allowed only inside the ARM TTL.
- STOP must immediately clear output and require a fresh ARM before any later FIRE.

The safety-critical ARM/Fire/STOP **enforcement stays on the C++ DinMeter** — the Dial
only ever *sends*; it never decides whether to fire.

### Acceptance level

Dry smoke is not a production release. UIFlow2/MicroPython work may be dry-smoked
only on a dummy/LED-only load while local deterministic checks and Gemini gates are
green. The production-release gate stays closed while the prototype HMAC key is compiled in; release builds must instead prove `PROP_ALLOW_PROTOTYPE_SHARED_KEY=0`,
`PROP_TX_ALLOW_SELFTEST_FIRE=0`, and `SELFTEST_FIRE=0` are consumed by the firmware
build systems.

### Offline runtime deploy

The fully offline field path is the Python runtime upload through `mpremote`. The `.m5b2`
file avoids Block Designer export, but the UIFlow2 canvas still needs UIFlow2 Web or an
already cached/available UIFlow2 app to edit blocks visually. Prepare `mpremote` before
going offline, for example with `python -m pip install mpremote` on the same Python used
for deploy, or pre-download a wheelhouse.

**Runtime-only offline path:** Choose this when you want the Dial to run without opening UIFlow2.
Upload the `.py` files from the bundle to `/flash` with
`mpremote`, then run `/flash/main.py`.

**Block Designer / canvas path:** Choose this when you want visual block editing.
Import `blocks/PropTx.m5b2` with **Custom -> Open** in UIFlow2, build the canvas,
and let UIFlow2 generate/upload the resulting Python. The `.m5b2` is for the
editor; it is not uploaded by `mpremote`.

For bench work without internet after that prep, use the local bundle/deploy helper:

```sh
python tools/uiflow_dial_offline.py bundle
python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline
python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline --dry-run
python tools/uiflow_dial_offline.py deploy --port COM6 --bundle build/uiflow_dial_offline
```

`bundle` writes an offline package to `build/uiflow_dial_offline/`:

- `device/prop_frame.py`, `device/prop_state.py`, `device/prop_ui.py`, `device/PropTx.py`, `device/main.py` for the Dial filesystem.
- `blocks/PropTx.m5b2` for UIFlow2 **Custom -> Open** when you do want the block canvas.
- `offline_manifest.json` with SHA-256 hashes of every copied file.

`device/PropTx.py` is the runtime module imported by code generated from `PropTx.m5b2`.
`device/main.py` is the standalone no-canvas Dial app.

`deploy` uploads only the runtime files to `/flash` via `mpremote`; the `.m5b2` block
package is never uploaded to the device. The tracked copy of that offline block import file
lives at `uiflow/dial/blocks/dist/PropTx.m5b2`, so it is available without visiting Block
Designer.

### Gemini code/workflow review gate

Gemini is not required for deterministic local validation. No Gemini secret is committed.
For text review of the block/offline/protocol workflow, set `GEMINI_API_KEY`,
set `GEMINI_API_KEY_FILE` to a local secret file, or create a gitignored
`.gemini_api_key` in this repo or at `~/.gemini_api_key`:

```sh
python tools/gemini_code_review.py --dry-run --out build/reviews/gemini_code_review_prompt.md
python tools/gemini_code_review.py --out build/reviews/gemini_code_review.md
```

Use the dry-run prompt when sharing the review package manually. Accept the
code/workflow side only when Gemini has no hardware-acceptance blockers, and the
local block/offline checks still pass (`tools/validate_uiflow_blocks.py`,
`tools/uiflow_dial_offline.py verify`, and the focused UIFlow pytest pack).

### Gemini visual review gate

For the visual design review gate, set `GEMINI_API_KEY`, set `GEMINI_API_KEY_FILE`
to a local secret file, or create a gitignored `.gemini_api_key` in this repo or at
`~/.gemini_api_key`:

```sh
python tools/preview_prop_tx.py
python tools/gemini_jury.py --dir build/preview --device "M5 Dial (round 240x240)" --per 3 --workers 3
```

Accept the visual side only if the report does not flag armed/fire ambiguity.
