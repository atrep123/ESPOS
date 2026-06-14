# C++ Runtime HMAC Key Provisioning

Production PropTx hardware must not use a compiled HMAC key. The Dial C++
transmitter and DinMeter C++ receiver both load the same runtime key from ESP32
NVS/Preferences namespace `prop_key`, key `shared`, matching the UIFlow
`/flash/prop_key.py` generated from the same local key file.

This document is the production runbook contract. It intentionally does not
contain the key bytes.

## Source Of Truth

Use one local, ignored key file for all PropTx runtimes:

```powershell
python -c "import pathlib,secrets; pathlib.Path('prop-key.hex').write_text(secrets.token_hex(32) + '\n', encoding='ascii')"
```

Rules:

- Keep the file outside git or under an ignored name such as `prop-key.hex`.
- Key length after hex decoding must be 16 to 64 bytes.
- Do not use the bench-only dry-smoke key represented in tooling as
  `PROTOTYPE_KEY_HEX` for production.
- If you intentionally use that dry-smoke key for a C++ dummy-load bench run,
  build the C++ firmware with `PROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1`. Production
  and release builds keep that define at `0` and must use a non-prototype key.
- Record only `sha256(key_bytes)` in bench notes.
- Use this same file for UIFlow:
  `python tools/uiflow_dial_offline.py bundle --production --prop-key-hex-file prop-key.hex`
  followed by
  `python tools/uiflow_dial_offline.py verify --production --prop-key-hex-file prop-key.hex`.

Generate the local C++ provisioning material and non-secret receipt from the same
file before touching hardware:

```powershell
python tools/provision_prop_key.py --key-file prop-key.hex --out build/prop_key_provisioning
```

The tool writes `prop_key_manifest.json` with `sha256(key_bytes)`, plus
`prop_key.nvs.csv` and `prop_key_bytes.h` under the ignored `build/` tree. The
CSV/header contain secret bytes and are only for local factory/service use. If
ESP-IDF's `nvs_partition_gen.py` is available, add `--generate-nvs-bin` to create
`prop_key.nvs.bin` from the same CSV; that binary is also a secret artifact and
is a complete NVS partition image that can overwrite existing target NVS data.
The tool also writes `prop_key_receipt.template.json`; it is non-secret until an
operator fills in device IDs, readback hashes, and protection posture.

## Hardware Receipt And Readback

After provisioning actual devices, copy `prop_key_receipt.template.json` to a
bench-specific ignored receipt and fill it from hardware evidence. Record only
chip IDs, MACs, firmware build/release flags, hashes/fingerprints, pass/fail
results, and the selected runtime-key-at-rest protection decision. Never commit
or paste `prop_key.nvs.bin`, `readback/*.bin`, `prop_key.nvs.csv`,
`prop_key_bytes.h`, or raw key bytes.

Dial has a checked-in NVS partition at offset `0x9000`, size `0x6000`:

```powershell
python -m esptool --chip esp32s3 --port <DIAL_COM> chip_id
python -m esptool --chip esp32s3 --port <DIAL_COM> read_mac
python -m esptool --chip esp32s3 --port <DIAL_COM> read_flash 0x9000 0x6000 build/prop_key_provisioning/readback/dial_nvs.bin
python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('build/prop_key_provisioning/readback/dial_nvs.bin').read_bytes()).hexdigest())"
```

DinMeter uses the board/default partition table unless a custom table is added.
Read the partition table first, parse the active `data,nvs` offset/size, then
read that exact range:

```powershell
python -m esptool --chip esp32s3 --port <DIN_COM> chip_id
python -m esptool --chip esp32s3 --port <DIN_COM> read_mac
python -m esptool --chip esp32s3 --port <DIN_COM> read_flash 0x8000 0x1000 build/prop_key_provisioning/readback/dinmeter_partitions.bin
python -m esptool --chip esp32s3 --port <DIN_COM> read_flash <DIN_NVS_OFFSET> <DIN_NVS_SIZE> build/prop_key_provisioning/readback/dinmeter_nvs.bin
```

readback bins are secret artifacts because they may contain the runtime HMAC key.
Keep them under ignored local output and record only SHA-256 hashes in notes.

## Required C++ NVS Writes

Any factory tool, one-shot provisioning firmware, or local service task used for
production must validate through `prop_runtime_key::RuntimeKey::set(...)`, write
the exact bytes, read them back, and verify the loaded size/fingerprint. Do not
only check that `nvs_set_blob()` or `putBytes()` returned success; a key with the
wrong length or a disallowed dry-smoke value would still fail closed at runtime.

For the ESP-IDF Dial transmitter:

```cpp
#include <nvs.h>
#include <nvs_flash.h>
#include "prop_runtime_key.h"

void provision_prop_key_dial(const uint8_t* key_bytes, size_t key_len) {
    prop_runtime_key::RuntimeKey validated;
    if (!validated.set(key_bytes, key_len)) {
        abort();
    }
    validated.clear();

    nvs_handle_t nvs = 0;
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(nvs_open(prop_runtime_key::NVS_NAMESPACE, NVS_READWRITE, &nvs));
    ESP_ERROR_CHECK(nvs_set_blob(nvs, prop_runtime_key::NVS_KEY, key_bytes, key_len));
    ESP_ERROR_CHECK(nvs_commit(nvs));

    uint8_t readback[prop_runtime_key::MAX_KEY_LENGTH] = {};
    size_t readback_len = sizeof(readback);
    ESP_ERROR_CHECK(nvs_get_blob(nvs, prop_runtime_key::NVS_KEY, readback, &readback_len));
    prop_runtime_key::RuntimeKey loaded;
    bool ok = loaded.set(readback, readback_len) && loaded.size() == key_len;
    for (size_t i = 0; i < key_len; ++i) {
        if (readback[i] != key_bytes[i]) {
            ok = false;
        }
    }
    prop_runtime_key::secureZero(readback, sizeof(readback));
    loaded.clear();
    nvs_close(nvs);
    if (!ok) {
        abort();
    }
}
```

For the Arduino/PlatformIO DinMeter receiver:

```cpp
#include <Preferences.h>
#include "prop_runtime_key.h"

void provision_prop_key_dinmeter(const uint8_t* key_bytes, size_t key_len) {
    prop_runtime_key::RuntimeKey validated;
    if (!validated.set(key_bytes, key_len)) {
        abort();
    }
    validated.clear();

    Preferences prefs;
    if (!prefs.begin(prop_runtime_key::NVS_NAMESPACE, false)) {
        abort();
    }
    if (prefs.putBytes(prop_runtime_key::NVS_KEY, key_bytes, key_len) != key_len) {
        abort();
    }
    uint8_t readback[prop_runtime_key::MAX_KEY_LENGTH] = {};
    const size_t readback_len =
        prefs.getBytes(prop_runtime_key::NVS_KEY, readback, sizeof(readback));
    prop_runtime_key::RuntimeKey loaded;
    bool ok = loaded.set(readback, readback_len) && loaded.size() == key_len;
    for (size_t i = 0; i < key_len; ++i) {
        if (readback[i] != key_bytes[i]) {
            ok = false;
        }
    }
    prop_runtime_key::secureZero(readback, sizeof(readback));
    loaded.clear();
    prefs.end();
    if (!ok) {
        abort();
    }
}
```

The bytes must come from the local non-source key file, a secure serial factory
input, or another local secret store. Do not paste production bytes into
committed source, committed headers, logs, Gemini prompts, or issue trackers.

## Provisioning Sequence

1. Generate or select `prop-key.hex`.
2. Run `python tools/provision_prop_key.py --key-file prop-key.hex --out build/prop_key_provisioning`
   and record only the non-secret fingerprint from `prop_key_manifest.json`.
3. Provision Dial C++ NVS with `prop_key/shared` from that file or from the
   generated local provisioning material.
4. Provision DinMeter C++ Preferences with `prop_key/shared` from that file or
   from the generated local provisioning material.
5. Build and verify the UIFlow production bundle from the same file.
6. Power-cycle both C++ devices and confirm the runtime key loaders report a
   loaded key rather than `KEY MISSING`.
7. Record the flash/NVS protection posture chosen for the target hardware
   (for example flash encryption / secure boot where required by the deployment
   risk), together with only the non-secret key fingerprint and the release-gated
   `docs/runtime_key_at_rest_decision.json` decision.
8. Negative test: erase or mismatch exactly one device key and confirm
   authenticated frames fail closed with `KEY MISSING`, `BAD MAC`, or no accepted
   action.
9. Positive test on dummy load only: matching keys allow PREVIEW, ARM, STOP,
   and FIRE only after a fresh ARM. Setup/color changes are verified through the
   Terminal USB upload path, not Dial palette or remote LED commands.

Production hardware acceptance remains blocked until this sequence is completed
on the actual Dial and DinMeter being shipped.
