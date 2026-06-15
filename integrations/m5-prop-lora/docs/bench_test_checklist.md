# Bench-test checklist — Dial → LoRa/ESP-NOW → DinMeter chain

Task #32. Validates the integrated `ESPOS/main` work in `integrations/m5-prop-lora` on the REAL hardware.
Two items here can ONLY be caught on-target (host tests don't cover them):

1. **HAL refactor host-UART fix (HIGH).** The c6l-modem decision/orchestration logic
   moved into `modem_core::Modem` (10 slices) + a council review caught a HIGH bug:
   `SerialHostLinkHal::writeLine` wrote only to USB `Serial`, not the `Serial1` link
   the Dial reads. Fixed (commit `edf45e5`). **The host tests cannot verify the two
   physical UARTs** — only this bench run proves the Dial actually receives the
   modem's `OK/ERR/RX` lines again. **This gates merging the branch to `master`.**
2. **NVS palette persistence (#46).** New DinMeter feature (separate `pal1` NVS key).
   Needs a real power-cycle to verify.

## Terminal setup slice

Current Terminal setup slice: **M5StickS3 Terminal** owns setup editing over the
local USB setup link. Terminal owns setup editing, Terminal has no radio module,
no radio modem path, and no radio protocol sender. Dial remains the radio fire
controller only through the C6 modem pair. DinMeter remains the receiver-side
safety authority, setup persistence owner, and LED execution/indication surface.
Terminal sends only `SETUP` / `SIM_FIRE` setup-link commands; setup uploads use
`SETUP <request_id>` and DinMeter echoes `SETUP_OK <request_id>` or
`SETUP_ERR <request_id>`.

- [ ] Build/flash `firmware/sticks3-terminal` env
      `sticks3-terminal-prop-link-g43-g44-600`.
- [ ] Connect Terminal to XIAO over the private A140 setup link; XIAO forwards
      `SETUP` / `SIM_FIRE` to DinMeter. No C6 modem is required for Terminal
      setup bring-up.
- [ ] Wire the Terminal bench snapshot exactly: StickS3 USB-C to PC; StickS3
      Grove to primary Pa.HUB v2.1; primary port 0 to
      `Encoder LED5 -> Encoder LED4 -> Encoder LED3 -> Encoder LED2 -> Encoder LED1 -> U206 upload switch -> U206 sim-fire switch`;
      primary port 3 to the external 2.4 inch display branch; primary port 5
      to Pb.HUB #1 at address 0x61. Pb.HUB port 0 -> Pot5, port 1 -> Pot4,
      port 2 -> Pot3, port 3 -> Pot2, port 4 -> Pot1, port 5 -> Grove2USB-C/C
      module branch toward XIAO.
- [ ] Treat LED1..LED5 as logical lane names. The physical encoder branch starts
      at LED5 and ends at LED1 before the two U206 switches; do not renumber
      setup lanes from the daisy-chain order. The runtime fader mapping is
      reversed from the physical Pb.HUB port order, so LED1..LED5 use Pot1..Pot5.
- [ ] Pot1..Pot5 are M5Stack Unit Fader U123 modules: B10K analog slider plus
      14x SK6812 programmable RGB LEDs. Do not expect Pa.HUB to read slider
      position or drive fader LEDs; Pb.HUB does both through its PORT.B channels.
      The fader filter snaps endpoint noise so a physical bottom stop displays
      `VYP` rather than `1%`.
- [ ] Flash `sticks3-terminal-pbhub-smoke`; require `PBHUB_SMOKE ONLINE 1`,
      five independent `PBHUB_ADC` lanes, and visible `PBHUB_RGB` reflection
      before accepting the fader bank.
- [ ] Do not use the rejected bare StickS3 fader+RGB map: ADC `LED1/G1 LED2/G2 LED3/G4 LED4/G7 LED5/G8`, RGB data `LED1/G3 LED2/G5 LED3/G6 LED4/G43 LED5/G44`. Official StickS3 docs mark `G1..G4` as shared internal PMIC/speaker/IMU signals, and `G9/G10` stays reserved for remaining Grove/I2C topology.
- [ ] Keep the direct StickS3 ADC strategy as fallback only. The active fader
      strategy is Pb.HUB ADC/RGB behind Pa.HUB port 5.
- [x] G4 ADC smoke on 2026-06-14: `sticks3-terminal-g4-adc-smoke` built,
      uploaded, and ran on the connected StickS3. Serial output tracked fader
      movement across raw 0 and raw 4095 endpoints with intermediate values, so
      G4 is accepted as the verified shared-pin candidate for the fifth slider
      ADC. This consumes the StickS3 IMU interrupt pin; do not enable IMU
      interrupt or low-power IMU wake behavior in the Terminal build. Direction
      is inverted: physical bottom is raw 4095 and physical top is raw 0, so use
      rawMin greater than rawMax if bottom must mean 0 percent brightness.
- [ ] Confirm the last U206 switch emits one SIM_FIRE preview edge, does not
      send `SETUP`, and does not alter Terminal draft/saved state.
- [ ] Flash `sticks3-terminal-oled-i2c-scan-smoke` with real SDA/SCL pins before
      enabling any display sink; capture USB serial with `tools/read_com.py`,
      record `OLED_I2C_SCAN FOUND`, `OLED_I2C_SCAN EXPECTED_FOUND 1`, and
      `OLED_I2C_SCAN DONE`, then decide M5UnitGLASS2-compatible vs dedicated sink.
- [ ] Flash `sticks3-terminal-grove-i2c-scan-smoke` for the real StickS3 Grove
      bus: SDA G9, SCL G10, expected primary Pa.HUB/PCA9548 address 0x70.
      Capture `OLED_I2C_SCAN FOUND 0x70` and `OLED_I2C_SCAN EXPECTED_FOUND 1`
      before scanning downstream Pa.HUB channels.
- [x] Grove I2C smoke on 2026-06-14: `sticks3-terminal-grove-i2c-scan-smoke`
      built, uploaded, and ran on COM29. Root scan saw only `0x70 MUX` on
      G9/G10 at both 400 kHz and 100 kHz; all six primary Pa.HUB channel
      selects returned `err=0`. Every channel reported `downstream=0` and
      `DOWNSTREAM_EMPTY`, so the primary Pa.HUB and StickS3 Grove pins are
      proven, but no downstream I2C module was visible while the external
      display SDA/SCL were swapped. After correcting the display wiring, the
      same scan repeatedly found `0x3C DOWNSTREAM` on primary Pa.HUB port 3 at
      both 400 kHz and 100 kHz.
      Primary port 5 now carries Pb.HUB address `0x61`. If a second Pb.HUB is
      ever added, it must use a different address or a different Pa.HUB branch;
      two default `0x61` Pb.HUB devices on one selected path are ambiguous.
- [ ] Flash `sticks3-terminal-oled-draw-smoke` and visually confirm the large
      OLED shows the smoke text frame. This is still a diagnostic SSD1306/SSD1309
      compatible draw path, not the production Terminal external display sink.
      Serial/I2C write smoke on 2026-06-14 passed on COM29:
      `OLED_DRAW_SMOKE SELECT_PAHUB ... err=0` and repeated
      `OLED_DRAW_SMOKE DRAWN address=0x3C channel=3`, but the first SSD1306-style
      frame was not visible. The next diagnostic firmware uses the product's
      SSD1309 profile. The physical OLED then visibly alternated between a
      white screen and text, proving the panel was alive; the text was rotated.
      The current diagnostic firmware logs `OLED_DRAW_SMOKE ALL_ON_BOOT` only
      once at boot, uses `0xA1/0xC8` orientation, and should then keep a stable
      text frame. This firmware was built and uploaded to COM29; a 12 s serial
      read after boot showed repeated `OLED_DRAW_SMOKE STABLE_TEXT` /
      `OLED_DRAW_SMOKE DRAWN` and no repeated white-screen cycle. Visual
      feedback then still showed a brief blink after a few seconds, traced to
      the smoke firmware reinitializing/redrawing the OLED every 3 s. Current
      smoke firmware performs one boot draw only; later loop iterations emit
      `OLED_DRAW_SMOKE HEARTBEAT stable` without touching the display. Visual
      confirmation on the physical glass is still required before marking this
      item done.
- [ ] Change at least two physical lane values, or inject a synthetic setup line
      only when the physical controls are not wired yet. Press upload and verify
      exact `SETUP_OK <request_id>` plus `NAHRANO`.
- [ ] Chain Encoder final-pin proof: flash Terminal with final
      `TERMINAL_CHAIN_RX_PIN`, `TERMINAL_CHAIN_TX_PIN`, and
      `TERMINAL_REQUIRE_CHAIN_UART=1`. Confirm the physical branch order is
      LED5, LED4, LED3, LED2, LED1, upload switch, sim-fire switch while
      `CHAIN_ENCODER_IDS = {5, 4, 3, 2, 1}` maps logical lanes 1..5
      (LED1..LED5). For each
      lane, rotate CW and CCW: only that lane's BARVA changes and direction is
      recorded. encoder button toggles only that lane fire-change marker. last U206 switch emits one SIM_FIRE preview edge.
      double-click remains ignored. Upload and capture the resulting five-lane
      `SETUP <request_id> ...` plus matching `SETUP_OK <request_id>` and
      `NAHRANO`.
      Bench note from 2026-06-14: Pa.HUB `0x70` channel 0 selected on Grove
      SDA G9 / SCL G10; UART RX G10 / TX G9 enumerated five encoders plus two
      U206 keys, while RX G9 / TX G10 timed out.
- [ ] Force `SETUP_ERR <request_id>`, timeout, or line overflow and verify
      `PROBLEM` plus rollback to the previous saved setup. DinMeter may already have committed
      a valid `SETUP` if only the reply was lost; record that as a
      link-ack failure, not a receiver parser failure.
- [ ] Inject a bare setup reply or a mismatched request id and verify Terminal
      keeps waiting until a matching reply or timeout.
- [ ] Confirm generic `OK`, `ERR`, `RX`, or modem debug lines do not confirm
      setup.
- [ ] If `SIM_FIRE` is tested from software or the last U206, verify preview
      only; SIM_FIRE leaves Terminal draft/saved state unchanged, sends no
      `SETUP`, and does not alter DinMeter persisted setup after
      reboot/readback.

## Field acceptance status

Dry smoke only: run this checklist with a dummy/LED-only load. Do not connect live
pyro or actuator outputs. Production release requires the same non-source HMAC key
to be provisioned into C++ Dial/DinMeter runtime storage and any UIFlow
`/flash/prop_key.py` bundle. The COM ports below are examples;
use the actual ports reported by this PC. The fully offline UIFlow runtime path is
`mpremote` upload from `tools/uiflow_dial_offline.py`; the UIFlow2 canvas still needs UIFlow2 Web or an already cached/available UIFlow2 app. No Gemini secret is committed; provide `GEMINI_API_KEY`, `GEMINI_API_KEY_FILE`, or a local
`.gemini_api_key` only when running the review gate. Dry-smoke expectation:
receiver reboot clears STOP latch as a local reset; lastSeq/epoch replay high-water persists.

## Production key preflight

- [ ] Create or select one local ignored key file (`prop_key.hex` / `prop-key.hex`);
      never commit it and record only the SHA-256 fingerprint of the key bytes.
- [ ] Generate local C++ provisioning material and a non-secret receipt:
      `python tools/provision_prop_key.py --key-file <local-key-file> --out build/prop_key_provisioning`.
      Fill `prop_key_receipt.template.json` after hardware readback. Treat
      generated CSV/header/bin files and readback bins as secret artifacts;
      `prop_key.nvs.bin` is a complete NVS partition image and can overwrite
      existing NVS settings.
- [ ] Provision the same key bytes into C++ Dial and DinMeter runtime storage:
      namespace `prop_key`, key `shared`; follow `docs/cxx_key_provisioning.md`.
- [ ] Read back or otherwise verify the loaded C++ key length/fingerprint on both
      devices; record only `sha256(key_bytes)` in the bench notes.
- [ ] For any run that uses the bench dry-smoke key on C++ hardware, confirm the
      firmware was built with `PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1`. Production
      builds must keep that define at `0` and use a non-prototype key.
- [ ] Confirm the target's chosen flash/NVS protection posture (for example
      flash encryption / secure boot where required for the deployment risk) and
      record it with the key fingerprint evidence. Release gates require the
      non-secret `docs/runtime_key_at_rest_decision.json` decision/waiver while
      protection is disabled or not statically provable.
- [ ] Build and verify any UIFlow bundle with the same file:
      `--production --prop-key-hex-file <local-key-file>`.
- [ ] Negative check: remove or mismatch one side and confirm the chain fails
      closed (`KEY MISSING` for the HMAC runtime key, `BAD MAC`, or no accepted
      frame) before reconnecting any real load. This is separate from the physical
      Chain Key diagnostic `FIRE KEY MISSING`.

## Example ports (per task #31) + flashing

| Device      | Firmware dir            | Port  | Build env                |
|-------------|-------------------------|-------|--------------------------|
| c6l-modem A | `firmware/c6l-modem`    | COM7  | `m5stack-c6l`            |
| c6l-modem B | `firmware/c6l-modem`    | COM8  | `m5stack-c6l`            |
| din-rx      | `firmware/din-rx`       | COM9  | `esp32-s3-devkitc-1`     |
| dial-tx     | `firmware/dial-tx`      | COM6  | ESP-IDF (idf.py)         |
| Terminal    | `firmware/sticks3-terminal` | COM10 | `sticks3-terminal-prop-link-g43-g44-600` |

Flash with the actual ports detected on this PC; the COM values below are examples
from one bench. For the first combined upload, follow
`docs/first_upload_runbook.md`.

```
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port COM7
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port COM8
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target din-rx -Port COM9
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target sticks3-terminal -Port COM10
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target dial-tx -Port COM6
```

> **Serial read constraint:** USB-CDC DTR/RTS toggling resets these boards. Read serial
> ONLY via `tools/read_com.py` with `dtr=False, rts=False`. NEVER open a second monitor
> on COM7/8/9 while the chain runs.

## A. HAL fix — modem responses reach the Dial (CRITICAL)

The regression: migrated modem host lines (`OK TX`, `ERR BUSY/DUTY/TX/ACK_TIMEOUT`,
`RX <hex>`, `OK HEALTH`) went only to USB, not to the Dial. After the fix they must
appear on the Dial's modem-UART again.

- [ ] Power the full chain. On the Dial, confirm the modem link shows **ready / OK**
      (the Dial parses the modem's `OK RADIO_READY` + periodic `OK HEALTH`). Pre-fix,
      the Dial would see silence and likely show a link error.
- [ ] **Chain Key:** confirm no `FIRE KEY MISSING` on boot with the key present;
      press before ARM must not fire; ARM then physical Chain Key press fires;
      missing/undetected key fails safe.
- [ ] Read modem A on COM7 via `read_com.py` (dtr/rts False): confirm `OK RADIO_READY`
      at boot and `OK HEALTH foreign=.. qdrop=.. rxfree=.. peer=.. dutyskip=..` ~every 2s.
- [ ] ARM from the Dial → DinMeter shows **ARMED**. (Proves ARM frame + the modem's
      `RX`/`OK TX` round-trip the Dial sees.)
- [ ] FIRE from the Dial → DinMeter LED effect plays. The Dial should reflect ACK
      (DinMeter ACKs over ESP-NOW; modem A surfaces the `RX <ack>` to the Dial).

## B. Core link behavior

- [ ] **FIRE delivery:** several FIREs in a row all play on the DinMeter (no missed).
- [ ] **STOP latch:** during a running effect, STOP from the Dial → DinMeter latches
      STOP immediately (LEDs off, status STOP). Repeat under rapid FIRE+STOP.
- [ ] **Dual-band:** unplug/disable one band if feasible (or rely on range) — link
      should survive on the other. (Sim shows ~0.98 delivery at 50%/50% loss with
      fire-and-forget burst; bench just needs "still fires".)
- [ ] **ARM TTL:** stop the ARM heartbeat (idle the Dial) for >12 s → DinMeter lapses
      to SAFE (a later FIRE without re-ARM does NOT fire).

## C. Terminal setup persistence

- [ ] On the Terminal, change at least two physical lane values and upload with
      the setup switch. DinMeter replies `SETUP_OK <request_id>` and shows the
      accepted lane colors/effect state.
- [ ] **Power-cycle the DinMeter ONLY** (leave Dial + modems running). After reboot,
      the DinMeter must show the SAME accepted setup, loaded from its persisted
      Terminal setup blob. Trigger preview/effect to confirm the colors render.
- [ ] Upload a different Terminal setup -> power-cycle DinMeter again -> the new
      setup persists (confirms overwrite, not append).
- [ ] Corruption safety: not easily benchable, but the loader validates
      magic/version/checksum + count and silently ignores a bad blob (falls back
      to defaults) — covered by the struct design.

## D. Regression sanity (already green off-target, re-confirm nothing obvious broke)

- [ ] No spurious resets / boot loops on any device (watch `read_com.py` for repeated
      boot banners — would indicate a brownout or crash).
- [ ] DinMeter accepted Terminal setup still persists across reboot; setup upload
      must not disturb the receiver safety state or runtime HMAC key.

---

**If A fails** (Dial doesn't see modem lines): re-check `SerialHostLinkHal::writeLine`
emits `Serial1.println` (commit `edf45e5`) and that COM7/8 are the right modems.
**Do not ship/merge the M5 integration from `ESPOS/main` until section A passes.**
