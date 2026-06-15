#pragma once

#include <cstddef>
#include <cstdint>

#include "../terminal_config.h"

#if defined(ARDUINO) && (TERMINAL_FADER_PBHUB_ENABLED || TERMINAL_FADER_PBHUB_RGB_ENABLED)
#define TERMINAL_PBHUB_HAS_ARDUINO_BUS 1
#else
#define TERMINAL_PBHUB_HAS_ARDUINO_BUS 0
#endif

#if TERMINAL_PBHUB_HAS_ARDUINO_BUS
#include <Wire.h>

#include "../terminal_grove_route.h"
#endif

namespace terminal_pbhub_client {

constexpr std::uint8_t DEFAULT_I2C_ADDRESS = 0x61;
constexpr std::uint8_t PORT_COUNT = 6;
constexpr std::uint8_t RGB_DATA_OFFSET = 0x09;
constexpr std::uint8_t RGB_FILL_OFFSET = 0x0A;
constexpr std::uint8_t RGB_BRIGHTNESS_OFFSET = 0x0B;
constexpr std::uint8_t RGB_COUNT_OFFSET = 0x08;
constexpr std::uint8_t ANALOG_READ_OFFSET = 0x06;
constexpr std::uint8_t FIRMWARE_VERSION_REG = 0xFE;

inline bool validPort(std::uint8_t port) {
    return port < PORT_COUNT;
}

inline std::uint8_t pbhubPortRegBase(std::uint8_t port) {
    const std::uint8_t normalized = port == 5 ? 6 : port;
    return static_cast<std::uint8_t>((normalized + 4U) << 4U);
}

inline std::uint8_t pbhubRegister(std::uint8_t port, std::uint8_t offset) {
    return static_cast<std::uint8_t>(pbhubPortRegBase(port) | (offset & 0x0F));
}

class PbHubBus {
   public:
    virtual ~PbHubBus() = default;
    virtual bool write(std::uint8_t address,
                       std::uint8_t reg,
                       const std::uint8_t* data,
                       std::size_t length) = 0;
    virtual bool read(std::uint8_t address,
                      std::uint8_t reg,
                      std::uint8_t* data,
                      std::size_t length) = 0;
};

class PbHubClient {
   public:
    explicit PbHubClient(PbHubBus& bus,
                         std::uint8_t address = DEFAULT_I2C_ADDRESS)
        : bus_(bus), address_(address) {}

    bool ping() {
        std::uint8_t version = 0;
        return readFirmwareVersion(version);
    }

    bool readFirmwareVersion(std::uint8_t& version) {
        return bus_.read(address_, FIRMWARE_VERSION_REG, &version, 1);
    }

    bool readAnalog(std::uint8_t port, std::uint16_t& raw) {
        if (!validPort(port)) {
            return false;
        }
        std::uint8_t data[2] = {};
        if (!bus_.read(address_, pbhubRegister(port, ANALOG_READ_OFFSET), data, sizeof(data))) {
            return false;
        }
        raw = static_cast<std::uint16_t>((static_cast<std::uint16_t>(data[1]) << 8U) | data[0]);
        return true;
    }

    bool setLedNum(std::uint8_t port, std::uint16_t count) {
        if (!validPort(port)) {
            return false;
        }
        const std::uint8_t data[2] = {
            static_cast<std::uint8_t>(count & 0xFFU),
            static_cast<std::uint8_t>(count >> 8U),
        };
        return bus_.write(address_, pbhubRegister(port, RGB_COUNT_OFFSET), data, sizeof(data));
    }

    bool setLedBrightness(std::uint8_t port, std::uint8_t value) {
        if (!validPort(port)) {
            return false;
        }
        return bus_.write(address_, pbhubRegister(port, RGB_BRIGHTNESS_OFFSET), &value, 1);
    }

    bool setLedColor(std::uint8_t port,
                     std::uint16_t index,
                     std::uint8_t red,
                     std::uint8_t green,
                     std::uint8_t blue) {
        if (!validPort(port)) {
            return false;
        }
        const std::uint8_t data[5] = {
            static_cast<std::uint8_t>(index & 0xFFU),
            static_cast<std::uint8_t>(index >> 8U),
            red,
            green,
            blue,
        };
        return bus_.write(address_, pbhubRegister(port, RGB_DATA_OFFSET), data, sizeof(data));
    }

    bool fillLedColor(std::uint8_t port,
                      std::uint16_t start,
                      std::uint16_t count,
                      std::uint8_t red,
                      std::uint8_t green,
                      std::uint8_t blue) {
        if (!validPort(port)) {
            return false;
        }
        const std::uint8_t data[7] = {
            static_cast<std::uint8_t>(start & 0xFFU),
            static_cast<std::uint8_t>(start >> 8U),
            static_cast<std::uint8_t>(count & 0xFFU),
            static_cast<std::uint8_t>(count >> 8U),
            red,
            green,
            blue,
        };
        return bus_.write(address_, pbhubRegister(port, RGB_FILL_OFFSET), data, sizeof(data));
    }

   private:
    PbHubBus& bus_;
    std::uint8_t address_;
};

#if TERMINAL_PBHUB_HAS_ARDUINO_BUS
class ArduinoPbHubBus : public PbHubBus {
   public:
    bool write(std::uint8_t address,
               std::uint8_t reg,
               const std::uint8_t* data,
               std::size_t length) override {
        if (!terminal_grove_route::selectPbHubPahub()) {
            return false;
        }
        TwoWire& targetBus = bus();
        targetBus.beginTransmission(address);
        targetBus.write(reg);
        targetBus.write(data, length);
        return targetBus.endTransmission() == 0;
    }

    bool read(std::uint8_t address,
              std::uint8_t reg,
              std::uint8_t* data,
              std::size_t length) override {
        if (!terminal_grove_route::selectPbHubPahub()) {
            return false;
        }
        TwoWire& targetBus = bus();
        targetBus.beginTransmission(address);
        targetBus.write(reg);
        if (targetBus.endTransmission(false) != 0) {
            return false;
        }
        const std::size_t received = targetBus.requestFrom(
            static_cast<int>(address),
            static_cast<int>(length));
        if (received != length) {
            return false;
        }
        for (std::size_t i = 0; i < length; ++i) {
            data[i] = static_cast<std::uint8_t>(targetBus.read());
        }
        return true;
    }

   private:
    TwoWire& bus() const {
        return terminal_config::PBHUB_I2C_PORT == 1 ? Wire1 : Wire;
    }
};
#endif

#undef TERMINAL_PBHUB_HAS_ARDUINO_BUS

}  // namespace terminal_pbhub_client
