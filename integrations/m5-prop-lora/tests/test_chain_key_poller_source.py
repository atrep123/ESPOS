from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.exists(), f"{relative_path} does not exist"
    return path.read_text(encoding="utf-8")


def test_dial_tx_chain_key_poller_uses_esp_idf_uart2_protocol() -> None:
    cpp = read("firmware/dial-tx/main/apps/app_prop_tx/chain_key_poller.cpp")
    header = read("firmware/dial-tx/main/apps/app_prop_tx/chain_key_poller.h")

    assert "UART_NUM_2" in cpp
    assert "PROP_TX_CHAIN_TX_GPIO" in cpp
    assert "PROP_TX_CHAIN_RX_GPIO" in cpp
    assert "G2=TX" in cpp
    assert "G1=RX" in cpp
    assert "uart_driver_install" in cpp
    assert "uart_param_config" in cpp
    assert "uart_set_pin" in cpp
    assert "uart_read_bytes" in cpp
    assert "uart_write_bytes" in cpp

    assert "PACK_HEAD_HIGH = 0xAA" in cpp
    assert "PACK_HEAD_LOW = 0x55" in cpp
    assert "PACK_END_HIGH = 0x55" in cpp
    assert "PACK_END_LOW = 0xAA" in cpp
    assert "CHAIN_HEARTBEAT = 0xFD" in cpp
    assert "CHAIN_ENUM = 0xFE" in cpp
    assert "CHAIN_GET_DEVICE_TYPE = 0xFB" in cpp
    assert "CHAIN_BUTTON_GET_STATUS = 0xE1" in cpp
    assert "CHAIN_KEY_TYPE_CODE = 0x0003" in cpp

    assert "Arduino.h" not in cpp
    assert "HardwareSerial" not in cpp
    assert "M5Chain" not in cpp
    assert "Arduino.h" not in header
    assert "HardwareSerial" not in header


def test_dial_tx_fire_button_is_chain_key_not_gpio() -> None:
    cpp = read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.cpp")
    header = read("firmware/dial-tx/main/apps/app_prop_tx/app_prop_tx.h")

    assert "chain_key_poller.h" in header
    assert "ChainKeyPoller" in header
    assert "_init_chain_key" in cpp
    assert "_chain_key.begin()" in cpp
    assert "_chain_key.readPressed(&down)" in cpp
    assert "_data.armed && !_data.awaiting_ack" in cpp
    assert "_run_selected_action(PROP_TX::ACTION_FIRE)" in cpp

    assert "PROP_TX_FIRE_BUTTON_GPIO" not in cpp
    assert "fire_button.setPin" not in cpp
    assert "fire_button.begin" not in cpp
    assert "fire_button.read" not in cpp
    assert "Button fire_button" not in header


def test_dial_tx_cmake_explicitly_builds_chain_key_poller() -> None:
    cmake = read("firmware/dial-tx/main/CMakeLists.txt")

    assert "apps/app_prop_tx/chain_key_poller.cpp" in cmake
