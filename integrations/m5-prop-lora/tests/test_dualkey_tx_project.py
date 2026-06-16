from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.exists(), f"{relative} does not exist"
    return path.read_text(encoding="utf-8")


def test_dualkey_tx_project_declares_chain_dualkey_environment() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    assert "default_envs = chain-dualkey-c147" in ini
    assert "[env:chain-dualkey-c147]" in ini
    assert "board = m5stack-stamps3" in ini
    assert "-I../../shared/protocol" in ini


def test_dualkey_tx_has_separate_uart_smoke_environment() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    release_env = ini.split("[env:chain-dualkey-c147-uart-smoke]", 1)[0]
    assert "-DDUALKEY_UART_SMOKE=1" not in release_env
    assert "-DDUALKEY_LED_SMOKE=1" not in release_env
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" not in release_env
    assert "-DDUALKEY_KEY_PROVISION=1" not in release_env
    assert "[env:chain-dualkey-c147-uart-smoke]" in ini
    assert "extends = env:chain-dualkey-c147" in ini
    assert "-DDUALKEY_UART_SMOKE=1" in ini

    main = read("firmware/dualkey-tx/src/main.cpp")
    assert "#ifndef DUALKEY_UART_SMOKE" in main
    assert "void runUartSmoke()" in main
    assert 'Serial2.println("PING")' in main
    assert 'Serial.print("DUALKEY UART SMOKE TX PING key1=")' in main
    assert 'Serial.print(key1 ? "DOWN" : "UP")' in main
    assert 'Serial.print(" key2=")' in main


def test_dualkey_tx_has_explicit_dry_smoke_and_key_provisioning_environments() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    main = read("firmware/dualkey-tx/src/main.cpp")

    assert "[env:chain-dualkey-c147-dry-smoke]" in ini
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" in ini
    assert "[env:chain-dualkey-c147-key-provision-dry-smoke]" in ini
    assert "-DDUALKEY_KEY_PROVISION=1" in ini
    assert "-I../../build/prop_key_provisioning_dry_smoke" in ini
    assert "#ifndef DUALKEY_KEY_PROVISION" in main
    assert "bool provisionRuntimeKey()" in main
    assert "#include \"prop_key_bytes.h\"" in main
    assert "DUALKEY KEY PROVISION OK len=" in main


def test_dualkey_tx_has_local_non_dry_key_provisioning_environment() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")

    assert "[env:chain-dualkey-c147-key-provision-local]" in ini
    local_env = ini.split("[env:chain-dualkey-c147-key-provision-local]", 1)[1].split("[env:", 1)[0]
    assert "extends = env:chain-dualkey-c147" in local_env
    assert "-DDUALKEY_KEY_PROVISION=1" in local_env
    assert "-I../../build/prop_key_provisioning_local" in local_env
    assert "-DPROP_ALLOW_DRY_SMOKE_RUNTIME_KEY=1" not in local_env


def test_dualkey_tx_has_separate_trace_environment_for_bench_debug() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    main = read("firmware/dualkey-tx/src/main.cpp")

    release_env = ini.split("[env:chain-dualkey-c147-uart-smoke]", 1)[0]
    dry_smoke_env = ini.split("[env:chain-dualkey-c147-dry-smoke]", 1)[1].split("[env:", 1)[0]

    assert "-DDUALKEY_TX_TRACE=1" not in release_env
    assert "-DDUALKEY_TX_TRACE=1" not in dry_smoke_env
    assert "[env:chain-dualkey-c147-dry-smoke-trace]" in ini
    assert "extends = env:chain-dualkey-c147-dry-smoke" in ini
    assert "-DDUALKEY_TX_TRACE=1" in ini
    assert "#ifndef DUALKEY_TX_TRACE" in main
    assert "void drainModemTrace()" in main
    assert "void traceKeyLevels(" in main
    assert "DUALKEY KEYS key1=" in main
    assert "DUALKEY TX BLUE_SET" in main
    assert "DUALKEY TX BARREL_EFFECT" in main


def test_dualkey_tx_has_separate_auto_smoke_environment_for_bench_rf() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    main = read("firmware/dualkey-tx/src/main.cpp")

    release_env = ini.split("[env:chain-dualkey-c147-uart-smoke]", 1)[0]
    assert "-DDUALKEY_AUTO_SMOKE=1" not in release_env

    assert "[env:chain-dualkey-c147-dry-smoke-auto]" in ini
    assert "extends = env:chain-dualkey-c147-dry-smoke" in ini
    assert "-DDUALKEY_AUTO_SMOKE=1" in ini
    assert "-DDUALKEY_TX_TRACE=1" in ini
    assert "#ifndef DUALKEY_AUTO_SMOKE" in main
    assert "void runAutoSmoke()" in main
    assert "DUALKEY AUTO SMOKE" in main
    assert "EventKind::BlueSet" in main
    assert "EventKind::BarrelEffect" in main


def test_dualkey_tx_has_separate_led_smoke_environment() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    assert "[env:chain-dualkey-c147-led-smoke]" in ini
    assert "extends = env:chain-dualkey-c147" in ini
    assert "-DDUALKEY_LED_SMOKE=1" in ini

    main = read("firmware/dualkey-tx/src/main.cpp")
    assert "#ifndef DUALKEY_LED_SMOKE" in main
    assert "DUALKEY LED SMOKE" in main
    assert "runLedSmoke()" in main


def test_dualkey_tx_uses_spi_led_driver_not_adafruit_neopixel() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    main = read("firmware/dualkey-tx/src/main.cpp")

    assert "Adafruit NeoPixel" not in ini
    assert "#include <Adafruit_NeoPixel.h>" not in main
    assert "#include <driver/spi_master.h>" in main
    assert "SPI2_HOST" in main
    assert "GPIO_NUM_NC" in main
    assert "GPIO_MODE_OUTPUT_OD" in main
    assert "enabled ? 0 : 1" in main


def test_dualkey_tx_uses_c147_pins_and_c6l_uart_port() -> None:
    main = read("firmware/dualkey-tx/src/main.cpp")
    assert "KEY1_PIN = 0" in main
    assert "KEY2_PIN = 17" in main
    assert "RGB_DATA_PIN = 21" in main
    assert "RGB_POWER_PIN = 40" in main
    assert "C6L_UART_RX_PIN = 47" in main
    assert "C6L_UART_TX_PIN = 48" in main
    assert "Serial2.begin" in main


def test_dualkey_tx_sends_no_ack_broadcast_prop_actions_only() -> None:
    main = read("firmware/dualkey-tx/src/main.cpp")
    assert "FrameType::PropAction" in main
    assert "PROP_BROADCAST_DESTINATION" in main
    assert 'Serial2.print("FF ")' in main
    assert "PROP_ACTION_BLUE_SET" in main
    assert "PROP_ACTION_BARREL_EFFECT" in main
    forbidden = [
        "FrameType::PaletteSet",
        "FrameType::LedColorSet",
        "FrameType::Arm",
        "FrameType::Fire",
        "SEND ",
    ]
    for needle in forbidden:
        assert needle not in main


def test_dualkey_tx_logic_is_pure_and_host_tested() -> None:
    logic = read("firmware/dualkey-tx/src/dualkey_tx_logic.h")
    assert "class DualKeyTxLogic" in logic
    assert "ButtonLevel" in logic
    assert "EventKind::BlueSet" in logic
    assert "EventKind::BarrelEffect" in logic
    assert "Arduino" not in logic
