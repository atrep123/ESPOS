# m5-prop-lora

Bezdrátový ovladač rekvizit na M5Stack: **M5 Dial** (ruční vysílač) dálkově řídí **4× SK6812 RGBW** LED na **M5 DinMeter** (přijímač) přes dvojici **ESP32-C6 LoRa modemů** (dual-band — LoRa 868 MHz + ESP-NOW 2.4 GHz, redundantně). Funguje i **samostatně bez vysílače** (lokální tlačítka/přepínač přímo na přijímači).

```
[M5 Dial] ──UART──> [C6 modem]  ···· LoRa 868 + ESP-NOW 2.4 ····  [C6 modem] ──UART──> [M5 DinMeter] ──I2C──> NeoDriver → 4× SK6812
  vysílač                              (redundantně, oba pásy)                            přijímač          + ByteButton (vstupy)
```

## Z čeho se to skládá
| Část | HW | Adresář | Toolchain |
|---|---|---|---|
| **din-rx** | M5 DinMeter (ESP32-S3) — UI + 4 LED + vstupy | `firmware/din-rx` | PlatformIO |
| **dial-tx** | M5 Dial (ESP32-S3) — ruční vysílač | `firmware/dial-tx` | ESP-IDF v5.1.3 |
| **c6l-modem** | 2× ESP32-C6 LoRa modem | `firmware/c6l-modem` | PlatformIO |
| **shared/protocol** | společný rámcový protokol (HMAC-SHA256) | `shared/protocol` | — |

## Co to umí
- **4 LED kanály:** LED1/LED2 = tlačítka (přepínání zap/vyp), LED3 = přepínač (drží úroveň), LED4 = **„odpal"** (záblesk s nastavitelným **náběhem / svitem / zhasnutím** + tvarem křivky).
- **UI na DinMeteru** (1 enkodér + 1 tlačítko): 4 stránky **Stav / Barvy / Čas / Jas** s navigací šipkou (`>` na posledním řádku → další stránka).
  - **Stav** — živý stav LED + stav vysílače (KLID / NABITO / STOP).
  - **Barvy** — barva každé LED (sada stavových presetů).
  - **Čas** — odpal: náběh / svit / zhasnutí (ms) + křivka (Hrana / Lin / Sinus).
  - **Jas** — globální jas všech LED (0–100 %).
- **Obousměrná synchronizace barev** Dial ↔ DinMeter (změna na jednom se propíše na druhý).
- **Vstupy:** M5 Unit ByteButton (3 tlačítka + přepínač), nebo emulace přes onboard enkodér, když modul není připojen (hot-plug podporován).

## Bezpečnost
- **ARM gate** — odpal (Fire) projde jen když je přijímač ARMED (čerstvě, ne v lockoutu, v TTL okně).
- **STOP lockout** — STOP okamžitě zhasne výstup a zamkne další odpal až do nového Arm.
- **Replay-okno + HMAC-SHA256** — autentizace a ochrana proti přehrání rámců.
- **Proudový strop** LED (220 mA) jako tvrdý limit nad nastaveným jasem.

## Build & flash
Viz **[BUILD.md](BUILD.md)** — přenos na nový PC (`git clone`), instalace toolchainů, build/flash každého kusu a **bring-up checklist** (co po flashi ověřit naživo).

## Další dokumentace (`docs/`)
- `M5_PROP_CONTROLLER.md` — celkový návrh ovladače
- `control_architecture.md` — architektura ovládání
- `hardware.md` — zapojení a piny
- `bench_test_checklist.md` — testovací checklist

## Stav
Aktivní větev `dinmeter-vlw-port`. Oba firmwary se buildí; chain (Dial → modemy → DinMeter) ověřen na reálném HW (LoRa + 2.4 link, ARM/Fire/Preview/sync).
