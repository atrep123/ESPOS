from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.exists(), f"{relative} does not exist"
    return path.read_text(encoding="utf-8")


def test_dualkey_tx_project_declares_chain_dualkey_environment() -> None:
    ini = read("firmware/dualkey-tx/platformio.ini")
    assert "[env:chain-dualkey-c147]" in ini
    assert "board = esp32-s3-devkitc-1" in ini
    assert "-I../../shared/protocol" in ini


def test_dualkey_tx_uses_c147_pins_and_c6l_uart_port() -> None:
    main = read("firmware/dualkey-tx/src/main.cpp")
    assert "KEY1_PIN = 0" in main
    assert "KEY2_PIN = 17" in main
    assert "RGB_DATA_PIN = 21" in main
    assert "RGB_POWER_PIN = 40" in main
    assert "C6L_UART_RX_PIN = 6" in main
    assert "C6L_UART_TX_PIN = 5" in main
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
