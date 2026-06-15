#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Preferences.h>
#include <esp_system.h>

#include <cstdint>
#include <vector>

#include "dualkey_tx_logic.h"
#include "prop_protocol.h"
#include "prop_runtime_key.h"

namespace {

constexpr int KEY1_PIN = 0;
constexpr int KEY2_PIN = 17;
constexpr int RGB_DATA_PIN = 21;
constexpr int RGB_POWER_PIN = 40;

// C147 HY2.0 port 2 to Unit C6L over a straight Grove cable:
// C147 TX is assigned to yellow/G5 so Unit C6L receives on its G5 host UART.
constexpr int C6L_UART_RX_PIN = 6;
constexpr int C6L_UART_TX_PIN = 5;
constexpr std::uint32_t C6L_UART_BAUD = 115200;

constexpr std::uint8_t PROP_KEY_ID = 1;
constexpr std::uint8_t PROP_SOURCE = 0x33;
constexpr std::uint8_t PROP_BROADCAST_DESTINATION = 0xFF;
constexpr std::uint8_t TX_BURST_COUNT = 3;
constexpr std::uint32_t TX_BURST_GAP_MS = 25;

dualkey_tx::DualKeyTxLogic logic(25);
prop_runtime_key::RuntimeKey runtimeKey;
Adafruit_NeoPixel pixels(2, RGB_DATA_PIN, NEO_GRB + NEO_KHZ800);
std::uint32_t txSequence = 1;
std::uint32_t txEpoch = 1;
bool keyLoaded = false;

void setPixels(std::uint32_t left, std::uint32_t right) {
    pixels.setPixelColor(0, left);
    pixels.setPixelColor(1, right);
    pixels.show();
}

void showIdle() {
    const std::uint32_t blue = logic.blueOn() ? pixels.Color(0, 0, 40) : pixels.Color(0, 0, 4);
    setPixels(blue, pixels.Color(0, 8, 0));
}

void showProblem() {
    setPixels(pixels.Color(40, 0, 0), pixels.Color(40, 0, 0));
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

void sendEvent(const dualkey_tx::TxEvent& event) {
    std::vector<std::uint8_t> encoded;
    if (!encodeEventFrame(event, encoded)) {
        showProblem();
        return;
    }
    sendNoAckFrame(encoded);
    if (event.kind == dualkey_tx::EventKind::BlueSet) {
        showIdle();
    } else {
        setPixels(pixels.Color(20, 12, 0), pixels.Color(20, 12, 0));
        delay(60);
        showIdle();
    }
}

bool pressed(int pin) {
    return digitalRead(pin) == LOW;
}

}  // namespace

void setup() {
    Serial.begin(115200);
    Serial2.begin(C6L_UART_BAUD, SERIAL_8N1, C6L_UART_RX_PIN, C6L_UART_TX_PIN);
    pinMode(KEY1_PIN, INPUT_PULLUP);
    pinMode(KEY2_PIN, INPUT_PULLUP);
    pinMode(RGB_POWER_PIN, OUTPUT);
    digitalWrite(RGB_POWER_PIN, HIGH);
    pixels.begin();
    pixels.setBrightness(32);
    txEpoch = esp_random();
    if (txEpoch == 0) {
        txEpoch = 1;
    }
    keyLoaded = loadRuntimeKey();
    if (keyLoaded) {
        showIdle();
    } else {
        showProblem();
    }
}

void loop() {
    if (!keyLoaded) {
        delay(100);
        keyLoaded = loadRuntimeKey();
        if (keyLoaded) {
            showIdle();
        }
        return;
    }

    const dualkey_tx::TxEvent event = logic.update(
        millis(),
        dualkey_tx::ButtonLevel{pressed(KEY1_PIN), pressed(KEY2_PIN)});
    if (event.kind != dualkey_tx::EventKind::None) {
        sendEvent(event);
    }
    delay(2);
}

