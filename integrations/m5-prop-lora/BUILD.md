# M5 LoRa Prop — Build & Flash

Sestava ovládače rekvizit:
- **din-rx** — M5 **DinMeter** (StampS3 / ESP32-S3), PŘIJÍMAČ: 4× SK6812 RGBW (Adafruit NeoDriver, I2C) + M5 Unit ByteButton (vstupy) + LCD UI. → `firmware/din-rx` (PlatformIO)
- **dial-tx** — M5 **Dial** (ESP32-S3), VYSÍLAČ. → `firmware/dial-tx` (ESP-IDF v5.1.3)
- **c6l-modem** — 2× **C6 LoRa modem** (ESP32-C6), dual-band LoRa 868 + ESP-NOW 2.4 GHz. → `firmware/c6l-modem` (PlatformIO)
- **shared/protocol** — sdílený rámcový protokol (HMAC-SHA256), společný pro vysílač i přijímač.

## Přenos na nový PC
```bash
git clone https://github.com/atrep123/m5-prop-lora.git
cd m5-prop-lora
git checkout dinmeter-vlw-port
```
Build cache (`.pio/`, `build/`, stažené knihovny) se NEpřenáší — je v `.gitignore` a vygeneruje se při prvním buildu (potřeba internet, stáhne knihovny dle `platformio.ini` / `idf_component.yml`).

## Toolchainy (jednorázová instalace)
- **PlatformIO Core** (din-rx + c6l-modem): `pip install platformio`, nebo rozšíření PlatformIO IDE ve VS Code.
- **ESP-IDF v5.1.3** (dial-tx): viz https://docs.espressif.com/projects/esp-idf/en/v5.1.3/esp32s3/get-started/ (Windows installer, nebo `git clone -b v5.1.3 ... && install.ps1`). Před každým `idf.py` načti prostředí (`export.ps1` / `export.sh`).

## Build + flash

### din-rx (DinMeter přijímač) — PlatformIO
```bash
# PYTHONIOENCODING=utf-8 na Windows (pio click crashuje na cp1250)
pio run -d firmware/din-rx -e esp32-s3-devkitc-1                                  # build
pio run -d firmware/din-rx -e esp32-s3-devkitc-1 -t upload --upload-port COMx     # flash
```
StampS3 = native USB (HWCDC). `COMx` = port DinMeteru.

### c6l-modem (oba LoRa modemy) — PlatformIO
```bash
pio run -d firmware/c6l-modem -e m5stack-c6l -t upload --upload-port COMy
```
ESP32-C6. `DUAL_BAND=1` (LoRa + ESP-NOW) je default. Flashni oba modemy stejným firmwarem.

### dial-tx (Dial vysílač) — ESP-IDF v5.1.3
```bash
# nejprve načti IDF prostředí (export.ps1 / export.sh)
idf.py -C firmware/dial-tx set-target esp32s3      # jen poprvé
idf.py -C firmware/dial-tx build
idf.py -C firmware/dial-tx -p COMz flash
```
M5 Dial = ESP32-S3. `SELFTEST_FIRE=0` (produkce — vysílač se sám neodpaluje).

## Acceptance levels

**Dry smoke:** bench-only validation with dummy LEDs or another non-actuator load.
Do not connect live pyro or actuator outputs. It is acceptable for dry smoke that
the prototype HMAC key is still compiled in, but only when release gates are known
to fail closed and `SELFTEST_FIRE=0`.

**Production release:** blocked until the prototype HMAC key is replaced by a
non-source secret/provisioning path and release builds compile with:
`PROP_ALLOW_PROTOTYPE_SHARED_KEY=0`, `PROP_TX_ALLOW_SELFTEST_FIRE=0`, and
`SELFTEST_FIRE=0`. The release helper exports those defines for PlatformIO and
ESP-IDF; a production release must prove both firmware toolchains consumed them.

Hardware smoke pass criteria: FIRE before ARM must show `NOT_ARMED` or have no
effect; ARM reply must show ARMED; FIRE must require that fresh ARM; STOP must clear output within one operator-visible cycle and require another fresh ARM
before later FIRE. `COM6` is only an example port in commands and docs; use the
actual Dial/DinMeter/modem port found on the PC. COM6 is only an example.

## UIFlow2 Dial offline workflow

For the M5 Dial MicroPython/block path, use `uiflow/dial/README.md`. That document
is the source of truth for the `mpremote` runtime-only bundle, the `.m5b2` block
canvas import, and the Gemini code/visual gates. Keep C++ firmware build/flash
work in this file and UIFlow2 runtime/block deployment in `uiflow/dial/README.md`.

## Identifikace portů
Více ESP32 na USB → urči, co je co, přes MAC/chip:
```bash
pio device list                       # porty + popisy
python <esptool> --port COMx chip_id  # ESP32-S3 = DinMeter/Dial, ESP32-C6 = modem
```
Nikdy nedrž 2 sériové monitory na stejném portu (kolize).

## Pozn. k zapojení (zkráceně)
- DinMeter Port B (G1/G2) = I2C @100kHz: NeoDriver @0x60 (4× SK6812 RGBW), ByteButton @0x47 (3 tlačítka + 1 přepínač jako latch). Port A (G13/G15) = UART na C6 modem.
- Dial Port A = UART na svůj C6 modem.
- Modemy mluví spolu LoRa 868 + ESP-NOW 2.4 (redundantně).

## Po flashi — co ověřit naživo (bring-up)
**DinMeter (din-rx):**
1. Boot: 4 LED krátce projedou jednotlivě R→G→B→W (per-pixel self-test). Všechny 4 svítí = HW OK.
2. Displej čistý (žádné diag texty); status bar = EMU/BB · RF tečka · stav-chip · baterie %.
3. Navigace: encoder vybírá řádek, poslední řádek = šipka `>` (klik = další stránka). Cyklus **Stav → Barvy → Cas → Jas → Stav**. Dlouhý stisk = domů/ulož.
4. **Stav:** LED1/LED2 ON/OFF, SPINAC = slider (switch glyph), ODPAL = SAFE/NABITO/STOP. Baterie reálné % (ne 255 %).
5. **Barvy:** klik cykluje barvu LED (živý náhled na pásku).
6. **Cas:** NABEH/SVIT/ZHASNUTI (klik = edit/amber, encoder mění ms) + KRIVKA (HRANA/LIN/SINUS).
7. **Jas:** klik = edit, encoder mění 0–100 % jasu všech LED.
8. Encoder točí spolehlivě oběma směry bez přeskoků.
9. (S ByteButtonem) připoj modul za běhu → stav „MODUL OK", tlačítka/přepínač ovládají LED; encoder zůstává jako override.

**Dial (dial-tx / UIFlow Dial):** testuj jen na dummy/LED-only zátěži, nikdy na live pyro/aktuátoru. PASS: FIRE před ARM → `NOT_ARMED` / žádný efekt; ARM → `ARMED`; FIRE funguje jen v ARM TTL; STOP okamžitě zhasne/ukončí výstup a další FIRE znovu vyžaduje čerstvý ARM. Preview/Arm/Stop → DinMeter reaguje. Změna barev na jedné straně se propíše na druhou (Preview/LedColorSet).

**Modemy:** beze změny (jen forwardují sync rámce); LoRa+2.4 link drží.

**Diagnostika přes USB** (115200): `[hb]`/`[bb]`/`[i2c]` log; čti přes `tools/read_com.py` (StampS3 = native USB, potřeba dtr-toggle).

## Zbývá dodělat (Dial-side, volitelné)
- **Zamknout počet LED na 4** (F2) + **snížit výběr odstínů** na stavové presety (F3) na Dialu — nálezy + návrh hotové (8× Opus debug), implementace neprovedena.
