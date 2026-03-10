# PlatformIO C Unit Tests

This folder contains PlatformIO/Unity unit tests for the firmware-side C modules.

- Test suites live under `test/<suite_name>/`
- Shared host-only stubs live under `test/stubs/` (used by `[env:native]`)

## Running

```bash
pio test -e native          # all suites
pio test -e native -f test_ui_core  # single suite
```

## Test Suites

| Suite | Module Under Test | Tests |
|-------|-------------------|-------|
| `test_msgbus` | `src/kernel/msgbus.c` — message bus pub/sub | 8 |
| `test_seesaw` | `src/services/input/seesaw.c` — Adafruit seesaw encoder | 25 |
| `test_store` | `src/services/store/` — NVS/SPIFFS persistence | 18 |
| `test_ui_bindings` | `src/services/ui/ui_bindings.c` — runtime value bindings | 18 |
| `test_ui_cmd` | `src/services/ui/ui_cmd.c` — UI command dispatch | 25 |
| `test_ui_components` | `src/services/ui/ui_components.c` — widget rendering | 16 |
| `test_ui_core` | `src/services/ui/ui_core.c` — widget tree & state | 15 |
| `test_ui_font` | `src/ui_font_6x8.c` — bitmap font data | 8 |
| `test_ui_listmodel` | `src/services/ui/ui_listmodel.c` — list/tree model | 11 |
| `test_ui_meta` | `src/services/ui/ui_meta.c` — widget metadata | 12 |
| `test_ui_nav` | `src/ui_nav.c` — focus navigation | 41 |
| `test_ui_render_swbuf` | `src/ui_render_swbuf.c` — software-buffered renderer | 44 |

**Total: ~241 test cases**

## Stubs

`test/stubs/` provides host-compatible replacements for ESP-IDF APIs:

- `ssd1363_stub.c` — display driver (no-op)
- `i2c_stub.c` — I2C bus
- `nvs_stub.c` — NVS flash storage
- `store_stub.c` — config store
- `esp_err_stub.c` — error code helpers
- `esp_err.h`, `esp_log.h`, `freertos/*.h` — header shims

