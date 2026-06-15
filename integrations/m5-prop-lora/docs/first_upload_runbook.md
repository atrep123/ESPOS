# First Upload Runbook

This is the operator runbook for the first bench uploads of the prop chain:

- **Odpalovac / Dial:** M5 Dial ESP32-S3 fire controller plus its C6 modem.
- **Odpalovac / DualKey:** M5Stack Chain DualKey C147 broadcast controller plus
  a C6L modem. Key 1 toggles the default blue prop lane, key 2 triggers the
  one-shot red barrel effect.
- **Terminal:** M5StickS3 Terminal USB setup editor.
- **Prop electronics:** DinMeter/StampS3 receiver, receiver-side C6 modem,
  DinMeter Port B UART to Seeed XIAO RP2040, XIAO buttons/switch, four status
  LEDs, 18x WS2812B barrel dummy/load path, and the Terminal USB setup link.

Detailed XIAO wiring, power, and signal-integrity notes live in
`docs/prop_xiao_electronics.md`.

Do not connect live pyro or actuator outputs during this run. First upload is a
dummy/LED-only dry-smoke bench path until the hardware receipt proves matching
runtime keys, safe ARM/FIRE behavior, STOP, and Terminal setup rollback.

## Current PC Preflight

Checked on 2026-06-15 from `C:\Users\atrep\Desktop\ESPOS`:

- `pio` is available.
- `python -m esptool version` works.
- `python -m mpremote --help` works.
- ESP-IDF v5.1.3 is installed at
  `C:\Users\atrep\esp\esp-idf-v5.1.3\export.ps1`; load it before Dial C++
  build/flash.
- After ESP-IDF export, `python` changes to the IDF venv. That venv currently
  does not have `mpremote`, so run UIFlow/mpremote upload commands from the
  normal Python shell or install `mpremote` into the IDF venv intentionally.
- Current enumeration on 2026-06-15 showed `COM10`, `COM23`, and `COM29` plus
  legacy `COM1`. Re-enumerate before flashing and do not assume these roles.

Generate the current non-secret rehearsal report before every first-upload
attempt:

```powershell
python tools/first_upload_preflight.py --out build/first_upload_preflight.md
```

Use `--strict` when you want CI-style failure while any blocker remains.

## Port Map To Fill Before Flashing

Run:

```powershell
pio device list
```

Fill this table from the actual device enumeration. Do not rely on historical
COM values.

| Role | Variable | Example only | Upload path |
|---|---|---:|---|
| M5 Dial fire controller | `<DIAL_COM>` | COM6 | ESP-IDF `dial-tx` |
| Dial-side C6 modem | `<MODEM_DIAL_COM>` | COM7 | PlatformIO env `m5stack-c6l` / flash target `c6l-modem` |
| Prop-side C6 modem | `<MODEM_PROP_COM>` | COM8 | PlatformIO env `m5stack-c6l` / flash target `c6l-modem` |
| DinMeter / prop receiver | `<DIN_COM>` | COM9 | PlatformIO `din-rx` |
| XIAO prop electronics | `<XIAO_COM>` | COM11 | PlatformIO standalone `seeed_xiao_rp2040_terminal_link_600` |
| M5StickS3 Terminal | `<TERMINAL_COM>` | COM10 | PlatformIO `sticks3-terminal-prop-link-g43-g44-600` |
| Chain DualKey odpalovac | `<DUALKEY_COM>` | COM12 | PlatformIO `chain-dualkey-c147` / flash target `dualkey-tx` |

For each ESP32-S3 target, record identity before and after flashing:

```powershell
python -m esptool --chip esp32s3 --port <DIAL_COM> chip_id
python -m esptool --chip esp32s3 --port <DIAL_COM> read_mac
```

For C6 modems use the same command with `--chip esp32c6`.
For XIAO RP2040, record the COM port shown by `pio device list` after entering
bootloader mode; do not use ESP32 `esptool` commands on it.

## Deterministic Gates Before Hardware

Run from `integrations/m5-prop-lora` unless noted:

```powershell
python -m pytest -q --tb=short tests
powershell -ExecutionPolicy Bypass -File tools/run_host_tests.ps1 -Compiler build\toolchains\winlibs-gcc-16.1.0-msvcrt-r3\mingw64\bin\g++.exe
pio run -d firmware/sticks3-terminal -e sticks3-terminal
pio run -d firmware/sticks3-terminal -e sticks3-terminal-prop-link-g43-g44-600
pio run -d firmware/sticks3-terminal -e sticks3-terminal-chain-uart-smoke
pio run -d firmware/sticks3-terminal -e sticks3-terminal-oled-i2c-scan-smoke
pio run -d firmware/din-rx -e esp32-s3-devkitc-1
pio run -d firmware/dualkey-tx -e chain-dualkey-c147
$env:PLATFORMIO_CORE_DIR = "C:\.pio-m5-prop-lora\c6l-modem"
pio run -d firmware/c6l-modem -e m5stack-c6l
Remove-Item Env:\PLATFORMIO_CORE_DIR
```

Load ESP-IDF v5.1.3 before Dial:

```powershell
& C:\Users\atrep\esp\esp-idf-v5.1.3\export.ps1
idf.py -C firmware/dial-tx build
```

## Runtime HMAC Key Preflight

Firmware intentionally fails closed without the same runtime HMAC key on Dial
and DinMeter. First positive Preview/ARM/FIRE smoke therefore needs key
provisioning, even for a dummy load.

Production key:

```powershell
python -c "import pathlib,secrets; pathlib.Path('prop-key.hex').write_text(secrets.token_hex(32) + '\n', encoding='ascii')"
python tools/provision_prop_key.py --key-file prop-key.hex --out build/prop_key_provisioning
```

Dry-smoke bench key, dummy load only:

```powershell
Set-Content -NoNewline -Encoding ASCII build\prop-key.dry-smoke.hex "00112233445566778899aabbccddeeff"
python tools/provision_prop_key.py --key-file build\prop-key.dry-smoke.hex --allow-dry-smoke --out build/prop_key_provisioning_dry_smoke
```

Any C++ firmware run that uses this bench-only key must be built with
`PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1`. Release and production builds must keep
that define at `0` and use a non-prototype key.

If ESP-IDF `nvs_partition_gen.py` is available, add `--generate-nvs-bin` to
produce `prop_key.nvs.bin`. Treat generated CSV/header/bin files and readback
bins as secret artifacts, even for production. Record only the SHA-256
fingerprint from `prop_key_manifest.json`.

Dial NVS partition is `0x9000` size `0x6000`. DinMeter currently uses the
PlatformIO board/default partition table; read `0x8000` size `0x1000` first and
derive the actual `data,nvs` offset/size before writing or reading NVS.

Before any positive PREVIEW/ARM/FIRE smoke, complete
`prop_key_receipt.template.json`: actual ports, chip ids, MACs, NVS offset/size,
readback command evidence, and matching non-secret fingerprints for Dial and
DinMeter. A `PENDING_HARDWARE` receipt blocks positive acceptance.

## First Upload Commands

Use `tools/flash.ps1` so PlatformIO core directories stay isolated. Run dry-runs
first and inspect the resolved commands before removing `-DryRun`:

```powershell
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port <MODEM_DIAL_COM> -DryRun
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port <MODEM_PROP_COM> -DryRun
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target din-rx -Port <DIN_COM> -DryRun
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target sticks3-terminal -Port <TERMINAL_COM> -DryRun
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target dualkey-tx -Port <DUALKEY_COM> -DryRun
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target dial-tx -Port <DIAL_COM> -DryRun
```

Build and flash the XIAO from its standalone repo after the DinMeter image is
confirmed:

```powershell
cd C:\Users\atrep\Desktop\xiao-prop-electronics-private
python -m pytest -q tests
pio run -e seeed_xiao_rp2040_terminal_link_600
pio run -e seeed_xiao_rp2040_terminal_link_600 -t upload --upload-port <XIAO_COM>
```

Then flash only the confirmed ports:

```powershell
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port <MODEM_DIAL_COM>
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target c6l-modem -Port <MODEM_PROP_COM>
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target din-rx -Port <DIN_COM>
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target sticks3-terminal -Port <TERMINAL_COM>
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target dualkey-tx -Port <DUALKEY_COM>
```

Dial C++ fire controller after ESP-IDF export:

```powershell
powershell -ExecutionPolicy Bypass -File tools/flash.ps1 -Target dial-tx -Port <DIAL_COM>
```

Optional UIFlow runtime bundle for a MicroPython Dial path:

```powershell
python tools/uiflow_dial_offline.py bundle --out build/uiflow_dial_offline --dry-smoke
python tools/uiflow_dial_offline.py verify --bundle build/uiflow_dial_offline
python tools/uiflow_dial_offline.py deploy --port <DIAL_COM> --bundle build/uiflow_dial_offline --dry-smoke --dry-run
python tools/uiflow_dial_offline.py deploy --port <DIAL_COM> --bundle build/uiflow_dial_offline --dry-smoke
```

## First Power-On Order

1. Flash receiver-side C6 modem and DinMeter with XIAO disconnected.
2. Confirm DinMeter shows `XIO` mode and `XIAO?`, proving Port B is not scanning
   legacy I2C.
3. Connect DinMeter Port B GND/TX/RX to XIAO only, then flash XIAO.
4. Confirm XIAO `HELLO` / `PING` / `PONG` before adding LED power.
5. Add button/switch wiring and verify local input logs.
6. Add external 5 V LED power, level shifters, series resistors, and bulk
   capacitance. Keep the barrel as dummy LED load only.
7. Flash Dial-side C6 modem and Dial.
8. Flash Terminal last, then connect the private Terminal setup link to XIAO.
   Terminal G43/G44 uses the A140 data pair to XIAO D5/D4; it is not a PC USB
   or direct DinMeter cable.
9. Keep one serial reader per port at most. Use `tools/read_com.py`, not a
   default monitor that toggles DTR/RTS:

```powershell
python tools/read_com.py <MODEM_DIAL_COM> 15 115200
python tools/read_com.py <DIN_COM> 15 115200
python tools/read_com.py <TERMINAL_COM> 15 115200
```

## Acceptance For First Bench Upload

- Dial/DinMeter with missing or mismatched HMAC key fail closed with `KEY MISSING`,
  `BAD MAC`, or no accepted action.
- With matching runtime keys on dummy load: PREVIEW works, ARM enters armed TTL,
  physical Chain Key before ARM does not fire, Chain Key after ARM fires, STOP
  clears output and requires fresh ARM.
- Terminal upload sends `SETUP <request_id>` and receives matching
  `SETUP_OK <request_id>`; `NAHRANO` appears on Terminal.
- Terminal rejected upload receives matching `SETUP_ERR <request_id>`.
- Forced `SETUP_ERR`, timeout, or overflow shows `PROBLEM` and rolls Terminal
  draft back to the last saved setup.
- `SIM_FIRE <request_id>` previews enabled effect lanes only and does not commit
  setup or use the radio FIRE path.
- XIAO D2 local FIRE is a visual DinMeter-local trigger; it does not require LoRa ARM
  and does not send or consume the authenticated radio FIRE path.
  STOP/lockout blocks XIAO D2 until a fresh LoRa ARM or DinMeter reboot.
- DinMeter/XIAO UART link shows `HELLO` and `PONG`; DinMeter no longer attempts
  Port B I2C ByteButton/NeoDriver in production mode.
- XIAO status LEDs receive `STAT4` in physical order: button 1, ODPAL/status,
  button 2, switch; the 18-pixel barrel also responds as one red
  `BARREL RED/OFF` group during local or radio FIRE.
- DualKey sends authenticated broadcast `PropAction` frames through its C6L
  modem: key 1 toggles the blue lane on/off, key 2 triggers exactly one red
  barrel effect burst per press.
- Power-cycle DinMeter after accepted setup; accepted Terminal setup persists.
