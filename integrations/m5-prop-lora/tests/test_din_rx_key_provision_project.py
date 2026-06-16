from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.exists(), f"{relative} does not exist"
    return path.read_text(encoding="utf-8")


def test_din_rx_has_separate_dry_smoke_and_key_provisioning_environments() -> None:
    ini = read("firmware/din-rx/platformio.ini")
    cpp = read("firmware/din-rx/src/prop_rx.cpp")

    release_env = ini.split("[env:esp32-s3-devkitc-1-debug]", 1)[0]
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" not in release_env
    assert "-DDIN_RX_KEY_PROVISION=1" not in release_env

    assert "[env:esp32-s3-devkitc-1-dry-smoke]" in ini
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" in ini
    assert "[env:esp32-s3-devkitc-1-key-provision-dry-smoke]" in ini
    assert "-DDIN_RX_KEY_PROVISION=1" in ini
    assert "-I../../build/prop_key_provisioning_dry_smoke" in ini

    assert "#ifndef DIN_RX_KEY_PROVISION" in cpp
    assert "#include \"prop_key_bytes.h\"" in cpp
    assert "bool provisionDinRxRuntimeKey()" in cpp
    assert "prop_runtime_key::NVS_NAMESPACE" in cpp
    assert "prop_runtime_key::NVS_KEY" in cpp
    assert "DIN RX KEY PROVISION OK len=" in cpp

    run_section = cpp[cpp.index("void prop_rx_run") :]
    provision_run_section = run_section[
        run_section.index("#if DIN_RX_KEY_PROVISION") : run_section.index("#else")
    ]
    assert "Serial.begin(115200);" in provision_run_section


def test_din_rx_has_local_non_dry_key_provisioning_environment() -> None:
    ini = read("firmware/din-rx/platformio.ini")

    assert "[env:esp32-s3-devkitc-1-key-provision-local]" in ini
    local_env = ini.split("[env:esp32-s3-devkitc-1-key-provision-local]", 1)[1].split("[env:", 1)[0]
    assert "extends = env:esp32-s3-devkitc-1" in local_env
    assert "-DDIN_RX_KEY_PROVISION=1" in local_env
    assert "-I../../build/prop_key_provisioning_local" in local_env
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" not in local_env


def test_din_rx_has_separate_dry_smoke_trace_environment_for_uart_debug() -> None:
    ini = read("firmware/din-rx/platformio.ini")
    cpp = read("firmware/din-rx/src/prop_rx.cpp")

    release_env = ini.split("[env:esp32-s3-devkitc-1-debug]", 1)[0]
    assert "-DDIN_RX_PROP_TRACE=1" not in release_env

    assert "[env:esp32-s3-devkitc-1-dry-smoke-trace]" in ini
    assert "extends = env:esp32-s3-devkitc-1-dry-smoke" in ini
    assert "-DDIN_RX_PROP_TRACE=1" in ini
    assert "-DDEBUG_HUD=1" in ini

    assert "#ifndef DIN_RX_PROP_TRACE" in cpp
    assert "DIN RX TRACE LINE RX len=" in cpp
    assert "DIN RX TRACE KEY MISSING" in cpp
    assert "DIN RX TRACE BAD MAC" in cpp
    assert "DIN RX TRACE PROP_ACTION action=" in cpp
