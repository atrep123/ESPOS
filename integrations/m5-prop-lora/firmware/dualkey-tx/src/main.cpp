#include <Arduino.h>
#include <Preferences.h>
#include <driver/gpio.h>
#include <driver/spi_master.h>
#include <esp_err.h>
#include <esp_system.h>

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "dualkey_tx_logic.h"
#include "prop_protocol.h"
#include "prop_runtime_key.h"

#ifndef DUALKEY_UART_SMOKE
#define DUALKEY_UART_SMOKE 0
#endif

#ifndef DUALKEY_LED_SMOKE
#define DUALKEY_LED_SMOKE 0
#endif

#ifndef DUALKEY_KEY_PROVISION
#define DUALKEY_KEY_PROVISION 0
#endif

#ifndef DUALKEY_TX_TRACE
#define DUALKEY_TX_TRACE 0
#endif

#ifndef DUALKEY_AUTO_SMOKE
#define DUALKEY_AUTO_SMOKE 0
#endif

#if DUALKEY_KEY_PROVISION
#include "prop_key_bytes.h"
#endif

namespace {

constexpr int KEY1_PIN = 0;
constexpr int KEY2_PIN = 17;
constexpr int RGB_DATA_PIN = 21;
constexpr int RGB_POWER_PIN = 40;

// C147 HY2.0 port 1 pin map used by the M5 Chain Bus examples:
// RX=G47, TX=G48. A straight port1 -> Unit C6L cable carries TX/G48 to C6L G5/RX.
constexpr int C6L_UART_RX_PIN = 47;
constexpr int C6L_UART_TX_PIN = 48;
constexpr std::uint32_t C6L_UART_BAUD = 115200;

constexpr std::uint8_t PROP_KEY_ID = 1;
constexpr std::uint8_t PROP_SOURCE = 0x33;
constexpr std::uint8_t PROP_BROADCAST_DESTINATION = 0xFF;
constexpr std::uint8_t TX_BURST_COUNT = 3;
constexpr std::uint32_t TX_BURST_GAP_MS = 25;

dualkey_tx::DualKeyTxLogic logic(25);
prop_runtime_key::RuntimeKey runtimeKey;
spi_device_handle_t ledSpi = nullptr;
std::uint8_t ledBrightness = 32;
std::uint8_t ledEncoded[64] = {};
std::uint32_t txSequence = 1;
std::uint32_t txEpoch = 1;
bool keyLoaded = false;

std::uint32_t color(std::uint8_t red, std::uint8_t green, std::uint8_t blue) {
    return (static_cast<std::uint32_t>(red) << 16) |
           (static_cast<std::uint32_t>(green) << 8) |
           static_cast<std::uint32_t>(blue);
}

std::uint8_t scaleChannel(std::uint32_t colorValue, std::uint8_t shift) {
    const std::uint32_t channel = (colorValue >> shift) & 0xFFU;
    return static_cast<std::uint8_t>((channel * ledBrightness + 127U) / 255U);
}

void setRgbPower(bool enabled) {
    // Chain DualKey C147 follows the official M5 BSP: GPIO40 is open-drain,
    // active LOW for WS2812 power.
    gpio_set_level(static_cast<gpio_num_t>(RGB_POWER_PIN), enabled ? 0 : 1);
}

void configureRgbPower() {
    gpio_config_t io = {};
    io.pin_bit_mask = 1ULL << RGB_POWER_PIN;
    io.mode = GPIO_MODE_OUTPUT_OD;
    io.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io.pull_up_en = GPIO_PULLUP_DISABLE;
    io.intr_type = GPIO_INTR_DISABLE;
    gpio_config(&io);
    setRgbPower(true);
}

void writeEncodedNibble(std::size_t nibbleIndex, std::uint8_t nibble) {
    const std::size_t byteIndex = nibbleIndex / 2U;
    if (byteIndex >= sizeof(ledEncoded)) {
        return;
    }
    if ((nibbleIndex % 2U) == 0U) {
        ledEncoded[byteIndex] = static_cast<std::uint8_t>((nibble << 4) | (ledEncoded[byteIndex] & 0x0FU));
    } else {
        ledEncoded[byteIndex] = static_cast<std::uint8_t>((ledEncoded[byteIndex] & 0xF0U) | nibble);
    }
}

void encodeWs2812Byte(std::uint8_t value, std::size_t& nibbleIndex) {
    for (std::uint8_t mask = 0x80; mask != 0; mask >>= 1) {
        // SPI at 3.2 MHz: 0b1000 ~= WS2812 "0", 0b1110 ~= WS2812 "1".
        writeEncodedNibble(nibbleIndex++, (value & mask) ? 0x0E : 0x08);
    }
}

bool initLedStrip(std::uint8_t brightness) {
    ledBrightness = brightness;

    spi_bus_config_t busConfig = {};
    busConfig.mosi_io_num = RGB_DATA_PIN;
    busConfig.miso_io_num = GPIO_NUM_NC;
    busConfig.sclk_io_num = GPIO_NUM_NC;
    busConfig.quadwp_io_num = GPIO_NUM_NC;
    busConfig.quadhd_io_num = GPIO_NUM_NC;
    busConfig.max_transfer_sz = sizeof(ledEncoded);

    esp_err_t result = spi_bus_initialize(SPI2_HOST, &busConfig, SPI_DMA_CH_AUTO);
    if (result != ESP_OK && result != ESP_ERR_INVALID_STATE) {
        Serial.print("DUALKEY LED SPI BUS FAIL ");
        Serial.println(esp_err_to_name(result));
        return false;
    }

    spi_device_interface_config_t deviceConfig = {};
    deviceConfig.clock_speed_hz = 3200000;
    deviceConfig.mode = 0;
    deviceConfig.spics_io_num = GPIO_NUM_NC;
    deviceConfig.queue_size = 1;

    result = spi_bus_add_device(SPI2_HOST, &deviceConfig, &ledSpi);
    if (result != ESP_OK && result != ESP_ERR_INVALID_STATE) {
        Serial.print("DUALKEY LED SPI DEVICE FAIL ");
        Serial.println(esp_err_to_name(result));
        ledSpi = nullptr;
        return false;
    }
    return true;
}

void encodePhysicalPixel(std::uint32_t value, std::size_t& nibbleIndex) {
    encodeWs2812Byte(scaleChannel(value, 8), nibbleIndex);
    encodeWs2812Byte(scaleChannel(value, 16), nibbleIndex);
    encodeWs2812Byte(scaleChannel(value, 0), nibbleIndex);
}

void setPixels(std::uint32_t left, std::uint32_t right) {
    if (!ledSpi) {
        return;
    }
    std::memset(ledEncoded, 0, sizeof(ledEncoded));
    std::size_t nibbleIndex = 0;
    // Official M5 mapping: right key is physical LED index 0, left key is index 1.
    encodePhysicalPixel(right, nibbleIndex);
    encodePhysicalPixel(left, nibbleIndex);

    spi_transaction_t transaction = {};
    transaction.length = sizeof(ledEncoded) * 8U;
    transaction.tx_buffer = ledEncoded;
    const esp_err_t result = spi_device_transmit(ledSpi, &transaction);
    if (result != ESP_OK) {
        Serial.print("DUALKEY LED SPI TX FAIL ");
        Serial.println(esp_err_to_name(result));
    }
}

void showIdle() {
    const std::uint32_t blue = logic.blueOn() ? color(0, 0, 40) : color(0, 0, 4);
    setPixels(blue, color(0, 8, 0));
}

void showProblem() {
    setPixels(color(40, 0, 0), color(40, 0, 0));
}

bool loadRuntimeKey() {
    Preferences prefs;
    if (!prefs.begin(prop_runtime_key::NVS_NAMESPACE, true)) {
        runtimeKey.clear();
        return false;
    }
    const std::size_t len = prefs.getBytesLength(prop_runtime_key::NVS_KEY);
    std::uint8_t buffer[prop_runtime_key::MAX_KEY_LENGTH] = {};
    bool ok = false;
    if (len >= prop_runtime_key::MIN_KEY_LENGTH &&
        len <= prop_runtime_key::MAX_KEY_LENGTH &&
        prefs.getBytes(prop_runtime_key::NVS_KEY, buffer, len) == len) {
        ok = runtimeKey.set(buffer, len);
    }
    prefs.end();
    prop_runtime_key::secureZero(buffer, sizeof(buffer));
    if (!ok) {
        runtimeKey.clear();
    }
    return ok;
}

#if DUALKEY_KEY_PROVISION
bool provisionRuntimeKey() {
    prop_runtime_key::RuntimeKey validated;
    if (!validated.set(PROP_PROVISIONING_KEY, PROP_PROVISIONING_KEY_LEN)) {
        Serial.println("DUALKEY KEY PROVISION FAIL validate");
        showProblem();
        return false;
    }
    validated.clear();

    Preferences prefs;
    if (!prefs.begin(prop_runtime_key::NVS_NAMESPACE, false)) {
        Serial.println("DUALKEY KEY PROVISION FAIL nvs");
        showProblem();
        return false;
    }

    bool ok =
        prefs.putBytes(prop_runtime_key::NVS_KEY, PROP_PROVISIONING_KEY, PROP_PROVISIONING_KEY_LEN) ==
        PROP_PROVISIONING_KEY_LEN;
    std::uint8_t readback[prop_runtime_key::MAX_KEY_LENGTH] = {};
    const std::size_t readbackLen =
        ok ? prefs.getBytes(prop_runtime_key::NVS_KEY, readback, sizeof(readback)) : 0U;

    prop_runtime_key::RuntimeKey loaded;
    ok = ok &&
         readbackLen == PROP_PROVISIONING_KEY_LEN &&
         loaded.set(readback, readbackLen) &&
         loaded.size() == PROP_PROVISIONING_KEY_LEN;
    for (std::size_t i = 0; ok && i < PROP_PROVISIONING_KEY_LEN; ++i) {
        ok = readback[i] == PROP_PROVISIONING_KEY[i];
    }

    prop_runtime_key::secureZero(readback, sizeof(readback));
    loaded.clear();
    prefs.end();

    if (!ok) {
        Serial.println("DUALKEY KEY PROVISION FAIL readback");
        showProblem();
        return false;
    }

    Serial.print("DUALKEY KEY PROVISION OK len=");
    Serial.println(PROP_PROVISIONING_KEY_LEN);
    setPixels(color(0, 40, 0), color(0, 40, 0));
    return true;
}
#endif

bool encodeEventFrame(const dualkey_tx::TxEvent& event, std::vector<std::uint8_t>& encoded) {
    if (!runtimeKey.loaded()) {
        return false;
    }

    std::uint8_t action = 0;
    switch (event.kind) {
        case dualkey_tx::EventKind::BlueSet:
            action = prop_protocol::PROP_ACTION_BLUE_SET;
            break;
        case dualkey_tx::EventKind::BarrelEffect:
            action = prop_protocol::PROP_ACTION_BARREL_EFFECT;
            break;
        case dualkey_tx::EventKind::None:
            return false;
    }

    std::vector<std::uint8_t> payload;
    if (!prop_protocol::encodePropActionPayload(action, event.value, event.eventId, payload)) {
        return false;
    }

    const std::uint32_t seq = txSequence++;
    prop_protocol::Frame frame;
    frame.type = prop_protocol::FrameType::PropAction;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_BROADCAST_DESTINATION;
    frame.sequence = seq;
    frame.nonce = (static_cast<std::uint64_t>(txEpoch) << 32) | seq;
    frame.payload = payload;
    return prop_protocol::encodeFrame(frame, runtimeKey.data(), runtimeKey.size(), encoded);
}

void sendNoAckFrame(const std::vector<std::uint8_t>& encoded) {
    const std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
    for (std::uint8_t i = 0; i < TX_BURST_COUNT; ++i) {
        Serial2.print("FF ");
        Serial2.println(hex.c_str());
        if (i + 1 < TX_BURST_COUNT) {
            delay(TX_BURST_GAP_MS);
        }
    }
}

#if DUALKEY_TX_TRACE
void traceTxEvent(const dualkey_tx::TxEvent& event, std::size_t encodedSize) {
    switch (event.kind) {
        case dualkey_tx::EventKind::BlueSet:
            Serial.print("DUALKEY TX BLUE_SET");
            break;
        case dualkey_tx::EventKind::BarrelEffect:
            Serial.print("DUALKEY TX BARREL_EFFECT");
            break;
        case dualkey_tx::EventKind::None:
            Serial.print("DUALKEY TX NONE");
            break;
    }
    Serial.print(" value=");
    Serial.print(event.value);
    Serial.print(" event=");
    Serial.print(static_cast<unsigned long>(event.eventId));
    Serial.print(" bytes=");
    Serial.println(static_cast<unsigned long>(encodedSize));
}

void drainModemTrace() {
    while (Serial2.available() > 0) {
        const int ch = Serial2.read();
        Serial.write(ch);
    }
}

void traceKeyLevels(bool key1, bool key2) {
    static bool started = false;
    static bool lastKey1 = false;
    static bool lastKey2 = false;
    if (started && key1 == lastKey1 && key2 == lastKey2) {
        return;
    }

    started = true;
    lastKey1 = key1;
    lastKey2 = key2;
    Serial.print("DUALKEY KEYS key1=");
    Serial.print(key1 ? "DOWN" : "UP");
    Serial.print(" key2=");
    Serial.println(key2 ? "DOWN" : "UP");
}
#endif

void sendEvent(const dualkey_tx::TxEvent& event) {
    std::vector<std::uint8_t> encoded;
    if (!encodeEventFrame(event, encoded)) {
        showProblem();
        return;
    }
#if DUALKEY_TX_TRACE
    traceTxEvent(event, encoded.size());
#endif
    sendNoAckFrame(encoded);
    if (event.kind == dualkey_tx::EventKind::BlueSet) {
        showIdle();
    } else {
        setPixels(color(20, 12, 0), color(20, 12, 0));
        delay(60);
        showIdle();
    }
}

#if DUALKEY_AUTO_SMOKE
void runAutoSmoke() {
#if DUALKEY_TX_TRACE
    drainModemTrace();
#endif
    if (!keyLoaded) {
        delay(100);
        keyLoaded = loadRuntimeKey();
        if (keyLoaded) {
            Serial.println("DUALKEY AUTO SMOKE KEY LOADED");
            showIdle();
        }
        return;
    }

    static std::uint32_t lastSendMs = 0;
    static std::uint32_t autoEventId = 10000;
    static std::uint8_t step = 0;
    static bool blueOn = false;
    const std::uint32_t now = millis();
    if (lastSendMs == 0 || now - lastSendMs >= 1500U) {
        lastSendMs = now;
        ++autoEventId;
        if ((step++ % 2U) == 0U) {
            blueOn = !blueOn;
            sendEvent(dualkey_tx::TxEvent{
                dualkey_tx::EventKind::BlueSet,
                static_cast<std::uint8_t>(blueOn ? 1 : 0),
                autoEventId,
            });
        } else {
            sendEvent(dualkey_tx::TxEvent{
                dualkey_tx::EventKind::BarrelEffect,
                0,
                autoEventId,
            });
        }
    }
    delay(10);
}
#endif

bool pressed(int pin) {
    return digitalRead(pin) == LOW;
}

#if DUALKEY_LED_SMOKE
void runLedSmoke() {
    static std::uint32_t lastStepMs = 0;
    static std::uint8_t step = 0;
    const std::uint32_t now = millis();
    if (now - lastStepMs < 400U) {
        delay(5);
        return;
    }
    lastStepMs = now;
    ++step;
    const bool powerEnabled = (step / 6U) % 2U == 0U;
    setRgbPower(powerEnabled);
    Serial.print("DUALKEY LED SMOKE TICK ");
    Serial.println(step);
    Serial.print("  pwr=");
    Serial.print(powerEnabled ? "ON_LOW" : "OFF_HIGH");
    Serial.print(" key1=");
    Serial.print(pressed(KEY1_PIN) ? "DOWN" : "UP");
    Serial.print(" key2=");
    Serial.println(pressed(KEY2_PIN) ? "DOWN" : "UP");
    switch (step % 6U) {
        case 0:
            setPixels(color(255, 0, 0), color(0, 255, 0));
            break;
        case 1:
            setPixels(color(0, 0, 255), color(255, 255, 0));
            break;
        case 2:
            setPixels(color(255, 0, 255), color(0, 255, 255));
            break;
        case 3:
            setPixels(color(255, 255, 255), color(255, 255, 255));
            break;
        case 4:
            setPixels(color(0, 0, 0), color(0, 0, 0));
            break;
        default:
            setPixels(color(0, 0, 255), color(0, 0, 255));
            break;
    }
}
#endif

#if DUALKEY_UART_SMOKE
void smokeLog(const char* line) {
    Serial.println(line);
}

void logUartSmokePing(bool key1, bool key2) {
    Serial.print("DUALKEY UART SMOKE TX PING key1=");
    Serial.print(key1 ? "DOWN" : "UP");
    Serial.print(" key2=");
    Serial.println(key2 ? "DOWN" : "UP");
}

void runUartSmoke() {
    static std::uint32_t lastPingMs = 0;
    static bool lastKey1 = false;
    static bool lastKey2 = false;

    while (Serial2.available() > 0) {
        const int ch = Serial2.read();
        Serial.write(ch);
    }

    const std::uint32_t now = millis();
    const bool key1 = pressed(KEY1_PIN);
    const bool key2 = pressed(KEY2_PIN);
    const bool shouldPing =
        (now - lastPingMs >= 1000U) || (key1 && !lastKey1) || (key2 && !lastKey2);
    if (shouldPing) {
        Serial2.println("PING");
        logUartSmokePing(key1, key2);
        setPixels(
            key1 ? color(0, 20, 0) : color(0, 0, 20),
            key2 ? color(20, 10, 0) : color(0, 0, 20));
        lastPingMs = now;
    }

    lastKey1 = key1;
    lastKey2 = key2;
    delay(10);
}
#endif

}  // namespace

void setup() {
    Serial.begin(115200);
#if !DUALKEY_LED_SMOKE && !DUALKEY_KEY_PROVISION
    Serial2.begin(C6L_UART_BAUD, SERIAL_8N1, C6L_UART_RX_PIN, C6L_UART_TX_PIN);
#endif
    pinMode(KEY1_PIN, INPUT_PULLUP);
    pinMode(KEY2_PIN, INPUT_PULLUP);
    configureRgbPower();
#if DUALKEY_LED_SMOKE
    initLedStrip(255);
#else
    initLedStrip(32);
#endif
    txEpoch = esp_random();
    if (txEpoch == 0) {
        txEpoch = 1;
    }
#if DUALKEY_KEY_PROVISION
    Serial.println("DUALKEY KEY PROVISION");
    provisionRuntimeKey();
#elif DUALKEY_LED_SMOKE
    Serial.println("DUALKEY LED SMOKE");
    setPixels(color(255, 255, 255), color(255, 255, 255));
#elif DUALKEY_UART_SMOKE
    smokeLog("DUALKEY UART SMOKE TX=G48 RX=G47");
    setPixels(color(0, 0, 20), color(0, 0, 20));
#elif DUALKEY_AUTO_SMOKE
    keyLoaded = loadRuntimeKey();
    if (keyLoaded) {
        Serial.println("DUALKEY AUTO SMOKE");
        showIdle();
    } else {
        Serial.println("DUALKEY AUTO SMOKE KEY MISSING");
        showProblem();
    }
#else
    keyLoaded = loadRuntimeKey();
    if (keyLoaded) {
        showIdle();
#if DUALKEY_TX_TRACE
        Serial.println("DUALKEY TX TRACE");
#endif
    } else {
        showProblem();
    }
#endif
}

void loop() {
#if DUALKEY_KEY_PROVISION
    delay(1000);
    return;
#endif

#if DUALKEY_LED_SMOKE
    runLedSmoke();
    return;
#endif

#if DUALKEY_UART_SMOKE
    runUartSmoke();
    return;
#endif

#if DUALKEY_AUTO_SMOKE
    runAutoSmoke();
    return;
#endif

#if DUALKEY_TX_TRACE
    drainModemTrace();
    const bool traceKey1 = pressed(KEY1_PIN);
    const bool traceKey2 = pressed(KEY2_PIN);
    traceKeyLevels(traceKey1, traceKey2);
#endif

    if (!keyLoaded) {
        delay(100);
        keyLoaded = loadRuntimeKey();
        if (keyLoaded) {
            showIdle();
#if DUALKEY_TX_TRACE
            Serial.println("DUALKEY TX TRACE");
#endif
        }
        return;
    }

    const dualkey_tx::TxEvent event = logic.update(
        millis(),
        dualkey_tx::ButtonLevel{
#if DUALKEY_TX_TRACE
            traceKey1, traceKey2
#else
            pressed(KEY1_PIN), pressed(KEY2_PIN)
#endif
        });
    if (event.kind != dualkey_tx::EventKind::None) {
        sendEvent(event);
    }
    delay(2);
}
