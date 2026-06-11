# Bench-test checklist — Dial → LoRa/ESP-NOW → DinMeter chain

Task #32. Validates the work on branch `dinmeter-vlw-port` on the REAL hardware.
Two items here can ONLY be caught on-target (host tests don't cover them):

1. **HAL refactor host-UART fix (HIGH).** The c6l-modem decision/orchestration logic
   moved into `modem_core::Modem` (10 slices) + a council review caught a HIGH bug:
   `SerialHostLinkHal::writeLine` wrote only to USB `Serial`, not the `Serial1` link
   the Dial reads. Fixed (commit `edf45e5`). **The host tests cannot verify the two
   physical UARTs** — only this bench run proves the Dial actually receives the
   modem's `OK/ERR/RX` lines again. **This gates merging the branch to `master`.**
2. **NVS palette persistence (#46).** New DinMeter feature (separate `pal1` NVS key).
   Needs a real power-cycle to verify.

## Ports (per task #31) + flashing

| Device      | Firmware dir            | Port  | Build env                |
|-------------|-------------------------|-------|--------------------------|
| c6l-modem A | `firmware/c6l-modem`    | COM7  | `c6l-modem`              |
| c6l-modem B | `firmware/c6l-modem`    | COM8  | `c6l-modem`              |
| din-rx      | `firmware/din-rx`       | COM9  | `esp32-s3-devkitc-1`     |
| dial-tx     | `firmware/dial-tx`      | COM6  | ESP-IDF (idf.py)         |

Flash (off-OneDrive PlatformIO cores; modem needs `c6l` core, din-rx its own):

```
# modems (flash each, swap --upload-port)
cd firmware/c6l-modem && PLATFORMIO_CORE_DIR=C:/piotx-c6l pio run -e c6l-modem -t upload --upload-port COM7
cd firmware/c6l-modem && PLATFORMIO_CORE_DIR=C:/piotx-c6l pio run -e c6l-modem -t upload --upload-port COM8
# din-rx
cd firmware/din-rx && PLATFORMIO_CORE_DIR=C:/piotx-dinrx pio run -e esp32-s3-devkitc-1 -t upload --upload-port COM9
# dial-tx (ESP-IDF)
cd firmware/dial-tx && idf.py -p COM6 flash
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

## C. NVS palette persistence (#46, new)

- [ ] On the Dial, set a custom palette (≥2 colors) and send it. DinMeter shows
      **PALETA OK** + the swatch.
- [ ] **Power-cycle the DinMeter ONLY** (leave Dial + modems running). After reboot,
      the DinMeter must show the SAME palette swatch (loaded from NVS `pal1`) — not
      revert to no-palette. Trigger a preview/effect to confirm the colors render.
- [ ] Send a DIFFERENT palette → power-cycle DinMeter again → the NEW palette persists
      (confirms overwrite, not append).
- [ ] Corruption safety: not easily benchable, but the loader validates
      magic/version/checksum + count and silently ignores a bad blob (falls back to
      no-palette) — covered by the struct design.

## D. Regression sanity (already green off-target, re-confirm nothing obvious broke)

- [ ] No spurious resets / boot loops on any device (watch `read_com.py` for repeated
      boot banners — would indicate a brownout or crash).
- [ ] DinMeter effect-config edits still persist across reboot (existing `eff2` NVS key
      — make sure the new `pal1` key didn't disturb it).

---

**If A fails** (Dial doesn't see modem lines): re-check `SerialHostLinkHal::writeLine`
emits `Serial1.println` (commit `edf45e5`) and that COM7/8 are the right modems.
**Do not merge `dinmeter-vlw-port` → `master` until section A passes.**
