# M5 LoRa Prop — Build & Flash

Sestava ovládače rekvizit:
- **din-rx** — M5 **DinMeter** (StampS3 / ESP32-S3), PŘIJÍMAČ: 5× SK6812 RGBW (Adafruit NeoDriver, I2C) + M5 Unit ByteButton (vstupy) + LCD UI. → `firmware/din-rx` (PlatformIO)
- **dial-tx** — M5 **Dial** (ESP32-S3), VYSÍLAČ. → `firmware/dial-tx` (ESP-IDF v5.1.3)
- **c6l-modem** — 2× **C6 LoRa modem** (ESP32-C6), dual-band LoRa 868 + ESP-NOW 2.4 GHz. → `firmware/c6l-modem` (PlatformIO)
- **shared/protocol** — sdílený rámcový protokol (HMAC-SHA256), společný pro vysílač i přijímač.

## Přenos na nový PC
```bash
git clone https://github.com/atrep123/ESPOS.git
cd ESPOS/integrations/m5-prop-lora
git checkout main
```
Build cache (`.pio/`, `build/`, stažené knihovny) se NEpřenáší — je v `.gitignore` a vygeneruje se při prvním buildu (potřeba internet, stáhne knihovny dle `platformio.ini` / `idf_component.yml`).

## Toolchainy (jednorázová instalace)
- **PlatformIO Core** (din-rx + c6l-modem): `pip install platformio`, nebo rozšíření PlatformIO IDE ve VS Code.
- **ESP-IDF v5.1.3** (dial-tx): viz https://docs.espressif.com/projects/esp-idf/en/v5.1.3/esp32s3/get-started/ (Windows installer, nebo `git clone -b v5.1.3 ... && install.ps1`). Před každým `idf.py` načti prostředí (`export.ps1` / `export.sh`).

## Terminal setup slice

Current Terminal setup slice: **M5StickS3 Terminal** owns setup editing over the
local USB setup link. Terminal owns setup editing, Terminal has no radio module,
no radio modem path, and no radio protocol sender. Dial remains the radio fire
controller only through the C6 modem pair. DinMeter remains the receiver-side
safety authority, setup persistence owner, and LED execution/indication surface.
Terminal sends only `SETUP` / `SIM_FIRE` setup-link commands; setup uploads use
`SETUP <request_id>` with request-scoped `SETUP_OK <request_id>` /
`SETUP_ERR <request_id>` replies.

```bash
pio run -d firmware/sticks3-terminal -e sticks3-terminal
pio run -d firmware/sticks3-terminal -e sticks3-terminal-chain-uart-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-oled-i2c-scan-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-grove-i2c-scan-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-g4-adc-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal -t upload --upload-port COMt
```

`sticks3-terminal-oled-i2c-scan-smoke uses dummy G1/G2 pins` for compile coverage.
For hardware bring-up, rebuild that env with the actual
`TERMINAL_EXTERNAL_OLED_SDA_PIN` and `TERMINAL_EXTERNAL_OLED_SCL_PIN` overrides
before reading the scan output.
`sticks3-terminal-grove-i2c-scan-smoke` uses StickS3 Grove SDA/SCL G9/G10 and
expects the primary Pa.HUB/PCA9548 mux at 0x70.
`sticks3-terminal-g4-adc-smoke` is a diagnostic-only shared-pin smoke. On
2026-06-14 it uploaded and ran, and G4 tracked fader movement from raw 0 to
4095, so it is accepted as the verified shared-pin candidate for the fifth
slider ADC. The observed orientation is inverted: physical bottom is raw 4095
and physical top is raw 0, so use `TERMINAL_FADER_RAW_MIN=4095` and
`TERMINAL_FADER_RAW_MAX=0` for that lane orientation if bottom means 0 percent.

## Host C++ logic tests

Pure C++ safety, protocol, Terminal pure logic, setup, control, switch, and USB
tests run without hardware. The runner auto-discovers `firmware/tests/test_*.cpp`:

```powershell
./tools/run_host_tests.ps1
```

They require `g++`. GitHub Actions on `ubuntu-24.04` has it available; on
Windows install WinLibs with `winget install --id BrechtSanders.WinLibs.POSIX.UCRT`
or pass an explicit compiler path with `./tools/run_host_tests.ps1 -Compiler C:\path\to\g++.exe`.
On Ubuntu/Debian, install it with `sudo apt-get install g++`. On macOS, install
the command-line tools with `xcode-select --install` and pass an explicit
compiler path if needed.

## CI / local deterministic gates

GitHub Actions currently runs deterministic M5 gates: Python source tests,
`tools/build.ps1 -ReleaseGatesOnly`, UIFlow dry-smoke bundle/verify, host C++
logic tests, Terminal PlatformIO firmware builds (`sticks3-terminal`,
`sticks3-terminal-prop-link-g43-g44-600`, `sticks3-terminal-chain-uart-smoke`,
`sticks3-terminal-oled-i2c-scan-smoke`, and `sticks3-terminal-g4-adc-smoke`),
plus DinMeter and C6 modem PlatformIO builds.
It still does not compile Dial ESP-IDF. A production release still requires
`./tools/build.ps1 -Release` on a machine with PlatformIO and ESP-IDF installed,
plus hardware key provisioning and on-device acceptance.

CI-equivalent local gate from the ESPOS repo root:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
cd integrations/m5-prop-lora
python -m pytest -q --tb=short tests
pwsh -NoProfile -ExecutionPolicy Bypass -File tools/build.ps1 -ReleaseGatesOnly
python tools/validate_uiflow_blocks.py
python tools/uiflow_dial_offline.py bundle --dry-smoke --out build/m5_uiflow_dial_offline
python tools/uiflow_dial_offline.py verify --bundle build/m5_uiflow_dial_offline
./tools/run_host_tests.ps1
pio run -d firmware/sticks3-terminal -e sticks3-terminal
pio run -d firmware/sticks3-terminal -e sticks3-terminal-prop-link-g43-g44-600
pio run -d firmware/sticks3-terminal -e sticks3-terminal-chain-uart-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-oled-i2c-scan-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-grove-i2c-scan-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-g4-adc-smoke
pio run -d firmware/din-rx -e esp32-s3-devkitc-1
pio run -d firmware/c6l-modem -e m5stack-c6l
```

## Build + flash

For the first combined upload of the Dial fire controller, M5StickS3 Terminal,
DinMeter, and both C6 modems, follow `docs/first_upload_runbook.md`. It includes
the current PC preflight, port map, runtime-key preflight, upload order, and
dummy-load acceptance checks.

### din-rx (DinMeter přijímač) — PlatformIO
```bash
# PYTHONIOENCODING=utf-8 na Windows (pio click crashuje na cp1250)
pio run -d firmware/din-rx -e esp32-s3-devkitc-1                                  # build
pio run -d firmware/din-rx -e esp32-s3-devkitc-1 -t upload --upload-port COMx     # flash
```
StampS3 = native USB (HWCDC). `COMx` = port DinMeteru.

### c6l-modem (oba LoRa modemy) — PlatformIO
```bash
# Windows PowerShell: keep C6 pioarduino packages isolated from DinMeter Arduino packages.
$env:PLATFORMIO_CORE_DIR = "C:\.pio-m5-prop-lora\c6l-modem"
pio run -d firmware/c6l-modem -e m5stack-c6l -t upload --upload-port COMy
Remove-Item Env:\PLATFORMIO_CORE_DIR
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
C++ Dial/DinMeter firmware no longer compiles an HMAC key. Both devices load the
runtime key from NVS/Preferences namespace `prop_key`, key `shared`; without it
authenticated frames fail closed with `KEY MISSING`/`BAD MAC`.

## Acceptance levels

**Dry smoke:** bench-only validation with dummy LEDs or another non-actuator load.
Do not connect live pyro or actuator outputs. UIFlow dry smoke may use the
explicit `--dry-smoke` `/flash/prop_key.py` bundle. C++ dry smoke still needs a
runtime-provisioned key in `prop_key/shared`; there is no compiled fallback. If
you intentionally provision the bench dry-smoke key into C++ hardware, build that
bench firmware with `PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1`; production/release
builds keep it at `0` and must use a non-prototype key.

**Production release:** requires a non-source HMAC secret provisioned consistently
to the C++ Dial, C++ DinMeter, and any UIFlow Dial bundle. Release builds compile
with `PROP_TX_ALLOW_SELFTEST_FIRE=0` and `SELFTEST_FIRE=0`; a production release
must prove both firmware toolchains consumed those flags, the runtime key is
present on target, missing/mismatched keys fail closed, and flash/NVS protection is
appropriate for the hardware risk.

Production release checklist summary: runtime key is present on target, missing or
mismatched keys fail closed, and `SELFTEST_FIRE=0`.

### Production key provisioning runbook

Use one local, ignored key file (for example `prop_key.hex` or `prop-key.hex`) as
the only source for both runtimes. Do not commit this file. Record only the
non-secret SHA-256 fingerprint of the key bytes in bench notes.

Detailed C++ provisioning contract: `docs/cxx_key_provisioning.md`.

1. Generate the local C++ provisioning material and non-secret receipt:
   `python tools/provision_prop_key.py --key-file <local-key-file> --out build/prop_key_provisioning`.
   The generated CSV/header/bin under `build/prop_key_provisioning` contain secret
   bytes; `prop_key.nvs.bin` is a complete NVS partition image and can overwrite
   existing NVS settings. Record only the fingerprint from `prop_key_manifest.json`
   and fill hardware evidence into `prop_key_receipt.template.json`.
2. Provision the C++ Dial and DinMeter runtime key into namespace `prop_key`, key
   `shared` using the same local key bytes, following `docs/cxx_key_provisioning.md`.
   Production remains blocked until this provisioning has been performed and
   verified on the actual devices being shipped.
3. Build the UIFlow bundle from the same local key file:
   `python tools/uiflow_dial_offline.py bundle --production --prop-key-hex-file <local-key-file>`.
4. Verify the UIFlow bundle against that same file before upload:
   `python tools/uiflow_dial_offline.py verify --production --prop-key-hex-file <local-key-file>`.
5. Deploy production UIFlow bundles only with the same verification argument:
   `python tools/uiflow_dial_offline.py deploy --port COM6 --production --prop-key-hex-file <local-key-file> --bundle build/uiflow_dial_offline`.
6. On hardware, prove fail-closed behavior: missing key shows `KEY MISSING`, a
   mismatched C++/UIFlow key produces `BAD MAC`/no accepted frame, and matching
   keys allow PREVIEW/ARM/STOP on dummy load only.
7. Keep `docs/runtime_key_at_rest_decision.json` current. Release gates require
   that non-secret decision/waiver while flash/NVS protection is disabled or not
   statically provable.

Hardware smoke pass criteria: FIRE before ARM must show `NOT_ARMED` or have no
effect; ARM reply must show ARMED; FIRE must require that fresh ARM; STOP must clear output within one operator-visible cycle and require another fresh ARM
before later FIRE. `COM6` is only an example port in commands and docs; use the
actual Dial/DinMeter/modem port found on the PC. COM6 is only an example.
Receiver reboot clears the volatile STOP latch as a local reset and must boot
disarmed/off; lastSeq/epoch replay high-water persists.

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
- DinMeter Port B (G1/G2) = I2C @100kHz: NeoDriver @0x60 (5× SK6812 RGBW), ByteButton @0x47 (3 tlačítka + 1 přepínač jako latch). Port A (G13/G15) = UART na C6 modem.
- Dial Port A = UART na svůj C6 modem.
- Modemy mluví spolu LoRa 868 + ESP-NOW 2.4 (redundantně).

## Po flashi — co ověřit naživo (bring-up)
**DinMeter (din-rx):**
1. Boot: 5 LED krátce projedou jednotlivě R→G→B→W (per-pixel self-test). Všech 5 svítí = HW OK.
2. Displej čistý (žádné diag texty); status bar = EMU/BB · RF tečka · stav-chip · baterie %.
3. DinMeter does not expose setup editing. It is the receiver-side safety
   authority, setup persistence owner, and LED execution/indication surface.
4. Upload from Terminal over USB: `SETUP <request_id>` returns
   `SETUP_OK <request_id>` or `SETUP_ERR <request_id>`.
5. Unsafe upload rejection: while armed, firing, locked out, or inhibited,
   DinMeter must reject setup without partially committing draft values.
6. `SIM_FIRE <request_id>` previews only enabled effect lanes and must not use
   the live radio FIRE path.
7. (With ByteButton) live inputs still drive receiver-side indication and safety
   states; they do not become setup navigation.

**Dial (dial-tx / UIFlow Dial):** test only on a dummy/LED-only load, never on
live pyro/actuators. PASS: FIRE before ARM -> `NOT_ARMED` / no effect; ARM ->
`ARMED`; FIRE works only in the ARM TTL; STOP immediately clears/ends output
and the next FIRE requires a fresh ARM. Preview/Arm/Stop -> DinMeter reacts.
Setup editing stays on Terminal; Dial remains the radio fire controller.

**Modemy:** beze změny (jen forwardují sync rámce); LoRa+2.4 link drží.

**Diagnostika přes USB** (115200): `[hb]`/`[bb]`/`[i2c]` log; čti přes `tools/read_com.py` (StampS3 = native USB, potřeba dtr-toggle).

## Zbývá dodělat (Dial-side, volitelné)
- **Snížit výběr odstínů** na stavové presety (F3) na Dialu — nálezy + návrh hotové (8× Opus debug), implementace neprovedena.
