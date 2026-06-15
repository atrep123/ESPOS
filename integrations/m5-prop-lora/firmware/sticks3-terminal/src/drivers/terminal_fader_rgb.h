#pragma once

#include <cstddef>
#include <cstdint>

#include "../terminal_config.h"
#include "../terminal_setup.h"
#include "terminal_pbhub_client.h"

namespace terminal_fader_rgb {

class FaderRgbSink {
   public:
    virtual ~FaderRgbSink() = default;
    virtual bool begin() = 0;
    virtual bool draw(const terminal_setup::TerminalSetupState& setup) = 0;
};

class MissingFaderRgbSink : public FaderRgbSink {
   public:
    bool begin() override {
        return false;
    }

    bool draw(const terminal_setup::TerminalSetupState& setup) override {
        (void)setup;
        return false;
    }
};

class PbHubFaderRgbSink : public FaderRgbSink {
   public:
    explicit PbHubFaderRgbSink(terminal_pbhub_client::PbHubClient& client)
        : client_(client) {}

    bool begin() override {
        available_ = client_.ping();
        if (!available_) {
            return false;
        }
        bool ok = true;
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            const std::uint8_t port = terminal_config::PBHUB_FADER_PORTS[lane];
            ok = client_.setLedNum(port, terminal_hardware_topology::UNIT_FADER_RGB_LED_COUNT) && ok;
            ok = client_.setLedBrightness(
                     port,
                     static_cast<std::uint8_t>(terminal_config::PBHUB_RGB_MAX_BRIGHTNESS)) &&
                 ok;
        }
        available_ = ok;
        return available_;
    }

    bool draw(const terminal_setup::TerminalSetupState& setup) override {
        if (!available_ && !begin()) {
            return false;
        }

        bool ok = true;
        for (std::size_t remaining = terminal_setup::LANE_COUNT; remaining > 0; --remaining) {
            const std::size_t lane = remaining - 1U;
            const terminal_setup::LedLane& item = setup.draftLane(lane);
            const terminal_color_definitions::ColorDefinition& color =
                terminal_setup::colorDefinitionFromHue(item.hue);
            const std::uint8_t scale = item.on ? item.brightness : 0;
            const std::uint8_t red = scaleColor(color.rgb.r, scale);
            const std::uint8_t green = scaleColor(color.rgb.g, scale);
            const std::uint8_t blue = scaleColor(color.rgb.b, scale);
            const std::uint8_t port = terminal_config::PBHUB_FADER_PORTS[lane];

            ok = client_.fillLedColor(
                     port,
                     0,
                     terminal_hardware_topology::UNIT_FADER_RGB_LED_COUNT,
                     red,
                     green,
                     blue) &&
                 ok;
            const std::uint8_t marker = item.effect
                                            ? static_cast<std::uint8_t>(terminal_config::PBHUB_RGB_MAX_BRIGHTNESS)
                                            : 0;
            ok = client_.setLedColor(port, 0, marker, marker, marker) && ok;
        }

        if (ok) {
            available_ = true;
        }
        return ok;
    }

   private:
    static std::uint8_t scaleColor(std::uint8_t value, std::uint8_t percent) {
        return static_cast<std::uint8_t>((static_cast<unsigned>(value) * percent) / 100U);
    }

    terminal_pbhub_client::PbHubClient& client_;
    bool available_ = false;
};

#if defined(ARDUINO) && TERMINAL_FADER_PBHUB_RGB_ENABLED
class ConfiguredFaderRgbSink : public FaderRgbSink {
   public:
    ConfiguredFaderRgbSink()
        : client_(bus_, static_cast<std::uint8_t>(terminal_config::PBHUB_I2C_ADDRESS)),
          sink_(client_) {}

    bool begin() override {
        return sink_.begin();
    }

    bool draw(const terminal_setup::TerminalSetupState& setup) override {
        return sink_.draw(setup);
    }

   private:
    terminal_pbhub_client::ArduinoPbHubBus bus_;
    terminal_pbhub_client::PbHubClient client_;
    PbHubFaderRgbSink sink_;
};
#else
class ConfiguredFaderRgbSink : public MissingFaderRgbSink {};
#endif

}  // namespace terminal_fader_rgb
