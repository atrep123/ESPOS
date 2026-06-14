#pragma once

#include <cstdint>

#include "terminal_config.h"

#if defined(ARDUINO)
#include <Arduino.h>
#include <Wire.h>
#endif

namespace terminal_grove_route {

enum class GroveRoute {
    None,
    ChainUart,
    ExternalOledI2c,
};

inline GroveRoute& currentRoute() {
    static GroveRoute route = GroveRoute::None;
    return route;
}

inline bool chainSelected() {
    return currentRoute() == GroveRoute::ChainUart;
}

inline bool externalOledSelected() {
    return currentRoute() == GroveRoute::ExternalOledI2c;
}

#if defined(ARDUINO)
inline bool selectPahubChannel(TwoWire& bus, std::uint8_t address, std::uint8_t channel) {
    bus.beginTransmission(address);
    bus.write(static_cast<std::uint8_t>(1U << channel));
    return bus.endTransmission() == 0;
}
#endif

inline bool selectChainPahub() {
#if defined(ARDUINO)
    if (!terminal_config::CHAIN_UART_SELECT_PAHUB) {
        currentRoute() = GroveRoute::ChainUart;
        return true;
    }
    if (chainSelected()) {
        return true;
    }

    currentRoute() = GroveRoute::None;
    Serial1.end();
    delay(2);
    Wire.begin(
        terminal_config::CHAIN_PAHUB_SDA_PIN,
        terminal_config::CHAIN_PAHUB_SCL_PIN,
        100000);
    const bool selected = selectPahubChannel(
        Wire,
        static_cast<std::uint8_t>(terminal_config::CHAIN_PAHUB_ADDRESS),
        static_cast<std::uint8_t>(terminal_config::CHAIN_PAHUB_CHANNEL));
    Wire.end();
    delay(10);
    if (selected) {
        currentRoute() = GroveRoute::ChainUart;
    }
    return selected;
#else
    currentRoute() = GroveRoute::ChainUart;
    return true;
#endif
}

inline bool selectExternalOledPahub() {
#if defined(ARDUINO)
    if (!terminal_config::EXTERNAL_OLED_SELECT_PAHUB) {
        currentRoute() = GroveRoute::ExternalOledI2c;
        return true;
    }
    if (externalOledSelected()) {
        return true;
    }

    currentRoute() = GroveRoute::None;
    Serial1.end();
    delay(2);
    TwoWire& bus = terminal_config::EXTERNAL_OLED_I2C_PORT == 1 ? Wire1 : Wire;
    bus.begin(
        terminal_config::EXTERNAL_OLED_SDA_PIN,
        terminal_config::EXTERNAL_OLED_SCL_PIN,
        terminal_config::EXTERNAL_OLED_I2C_FREQ);
    const bool selected = selectPahubChannel(
        bus,
        static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_PAHUB_ADDRESS),
        static_cast<std::uint8_t>(terminal_config::EXTERNAL_OLED_PAHUB_CHANNEL));
    if (selected) {
        currentRoute() = GroveRoute::ExternalOledI2c;
    } else {
        bus.end();
    }
    return selected;
#else
    currentRoute() = GroveRoute::ExternalOledI2c;
    return true;
#endif
}

}  // namespace terminal_grove_route
