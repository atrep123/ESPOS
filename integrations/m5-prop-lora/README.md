# m5-prop-lora

Current Terminal setup slice: **M5StickS3 Terminal** owns setup editing over the
local USB setup link. Terminal owns setup editing, Terminal has no radio module,
no radio modem path, and no radio protocol sender. Dial remains the radio fire
controller only through the C6 modem pair. DinMeter remains the receiver-side
safety authority, setup persistence owner, and LED execution/indication surface.
Terminal sends only `SETUP` / `SIM_FIRE` setup-link commands; setup uploads use
`SETUP <request_id>` with request-scoped `SETUP_OK <request_id>` /
`SETUP_ERR <request_id>` replies.

Terminal source locations: `firmware/sticks3-terminal` and `shared/terminal`.

Bezdrátový ovladač rekvizit na M5Stack: **M5 Dial** (ruční vysílač) dálkově řídí **5× SK6812 RGBW** LED na **M5 DinMeter** (přijímač) přes dvojici **ESP32-C6 LoRa modemů** (dual-band — LoRa 868 MHz + ESP-NOW 2.4 GHz, redundantně). Funguje i **samostatně bez vysílače** (lokální tlačítka/přepínač přímo na přijímači).

```
[M5 Dial] ──UART──> [C6 modem]  ···· LoRa 868 + ESP-NOW 2.4 ····  [C6 modem] ──UART──> [M5 DinMeter] ──I2C──> NeoDriver → 5× SK6812
  vysílač                              (redundantně, oba pásy)                            přijímač          + ByteButton (vstupy)
```

## Z čeho se to skládá
| Část | HW | Adresář | Toolchain |
|---|---|---|---|
| **din-rx** | M5 DinMeter (ESP32-S3) — UI + 5 LED + vstupy | `firmware/din-rx` | PlatformIO |
| **dial-tx** | M5 Dial (ESP32-S3) — ruční vysílač | `firmware/dial-tx` | ESP-IDF v5.1.3 |
| **dualkey-tx** | M5Stack Chain DualKey C147 — broadcast odpalovač | `firmware/dualkey-tx` | PlatformIO |
| **sticks3-terminal** | M5StickS3 Terminal — USB setup editor, no radio | `firmware/sticks3-terminal` + `shared/terminal` | PlatformIO + host `g++` tests |
| **c6l-modem** | 2× ESP32-C6 LoRa modem | `firmware/c6l-modem` | PlatformIO |
| **shared/protocol** | společný rámcový protokol (HMAC-SHA256) | `shared/protocol` | — |

## Co to umí
- **5 LED kanálů:** LED1/LED2 = tlačítka (přepínání zap/vyp), LED3 = přepínač (drží úroveň), LED4/LED5 = výstupní kanály včetně **„odpal"** efektu (záblesk s nastavitelným **náběhem / svitem / zhasnutím** + tvarem křivky).
- **Setup editing is on the M5StickS3 Terminal:** five physical lanes set a
  named color palette, brightness/normal on-off state, and whether each lane
  changes state during fire. Upload goes over the local USB setup link as
  `SETUP <request_id>`.
- **DinMeter display is indication/safety only:** it persists accepted setup,
  renders the LED/effect state, and rejects unsafe setup commits while armed,
  firing, locked out, or inhibited.
- **Dial remains fire-focused:** Preview/Arm/Stop/Fire stay on Dial through the
  C6 modem pair; it no longer edits LED setup values.
- **Vstupy:** M5 Unit ByteButton (3 tlačítka + přepínač), nebo emulace přes onboard enkodér, když modul není připojen (hot-plug podporován).

## Bezpečnost
- **ARM gate** — odpal (Fire) projde jen když je přijímač ARMED (čerstvě, ne v lockoutu, v TTL okně).
- **STOP lockout** — STOP okamžitě zhasne výstup a zamkne další odpal až do nového Arm.
- **Replay-okno + HMAC-SHA256** — autentizace a ochrana proti přehrání rámců.
- **Proudový strop** LED (220 mA) jako tvrdý limit nad nastaveným jasem.

## Build & flash
Viz **[BUILD.md](BUILD.md)** — přenos na nový PC (`git clone`), instalace toolchainů, build/flash každého kusu a **bring-up checklist** (co po flashi ověřit naživo). První společný upload Dialu, Terminálu a elektroniky v rekvizitě je v `docs/first_upload_runbook.md`.
Current acceptance: dry-smoke bench work is supported, but full current hardware acceptance, including Chain Key, is pending.
Production release requires runtime non-source HMAC key provisioning on the C++ Dial/DinMeter devices and the UIFlow runtime. See `BUILD.md` acceptance levels and `docs/bench_test_checklist.md`.

## Další dokumentace (`docs/`)
- `M5_PROP_CONTROLLER.md` — celkový návrh ovladače
- `control_architecture.md` — architektura ovládání
- `hardware.md` — zapojení a piny
- `bench_test_checklist.md` — testovací checklist

## Stav
Aktivní větev `ESPOS/main` (`integrations/m5-prop-lora`). Deterministické source/test gates a dry-smoke
bench workflow běží, ale plná aktuální HW akceptace včetně Chain Key zůstává
pending. Produkční release je dál blokovaný, dokud nebude prototypový HMAC klíč
nahrazen non-source provisioning cestou.

Production note: the runtime provisioning path now exists, but release remains
blocked until the same local non-source HMAC key is written to C++ NVS/Preferences
(`prop_key/shared`) and UIFlow `/flash/prop_key.py`, verified by fingerprint, and
confirmed on hardware.
