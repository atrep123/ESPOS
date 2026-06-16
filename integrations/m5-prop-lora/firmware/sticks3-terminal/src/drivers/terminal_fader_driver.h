#pragma once

#include <cstddef>

#include "../terminal_config.h"
#include "../terminal_control_surface.h"
#include "../terminal_fader_filter.h"
#include "terminal_pbhub_client.h"

#if defined(ARDUINO) && TERMINAL_FADER_ADC_ENABLED
#include <Arduino.h>
#define TERMINAL_FADER_HAS_ARDUINO_ADC 1
#else
#define TERMINAL_FADER_HAS_ARDUINO_ADC 0
#endif

#if defined(ARDUINO) && TERMINAL_FADER_PBHUB_ENABLED
#define TERMINAL_FADER_HAS_PBHUB 1
#else
#define TERMINAL_FADER_HAS_PBHUB 0
#endif

namespace terminal_fader_driver {

using terminal_control_surface::ControlSnapshot;

class FaderRawReader {
   public:
    virtual ~FaderRawReader() = default;
    virtual bool begin() = 0;
    virtual int readRaw(std::size_t lane) = 0;
};

class MissingFaderRawReader : public FaderRawReader {
   public:
    bool begin() override {
        return false;
    }

    int readRaw(std::size_t lane) override {
        (void)lane;
        return terminal_fader_filter::RAW_SAMPLE_MISSING;
    }
};

class PbHubFaderRawReader : public FaderRawReader {
   public:
    explicit PbHubFaderRawReader(terminal_pbhub_client::PbHubClient& client)
        : client_(client) {}

    bool begin() override {
        available_ = client_.ping();
        return available_;
    }

    int readRaw(std::size_t lane) override {
        if (!available_ || lane >= terminal_config::PBHUB_FADER_PORTS.size()) {
            return terminal_fader_filter::RAW_SAMPLE_MISSING;
        }
        std::uint16_t raw = 0;
        if (!client_.readAnalog(terminal_config::PBHUB_FADER_PORTS[lane], raw)) {
            return terminal_fader_filter::RAW_SAMPLE_MISSING;
        }
        return static_cast<int>(raw);
    }

   private:
    terminal_pbhub_client::PbHubClient& client_;
    bool available_ = false;
};

#if TERMINAL_FADER_HAS_PBHUB
class ArduinoPbHubFaderRawReader : public FaderRawReader {
   public:
    ArduinoPbHubFaderRawReader()
        : client_(bus_, static_cast<std::uint8_t>(terminal_config::PBHUB_I2C_ADDRESS)),
          reader_(client_) {}

    bool begin() override {
        return reader_.begin();
    }

    int readRaw(std::size_t lane) override {
        return reader_.readRaw(lane);
    }

   private:
    terminal_pbhub_client::ArduinoPbHubBus bus_;
    terminal_pbhub_client::PbHubClient client_;
    PbHubFaderRawReader reader_;
};
#else
class ArduinoPbHubFaderRawReader : public MissingFaderRawReader {};
#endif

#if TERMINAL_FADER_HAS_ARDUINO_ADC
class ArduinoAdcFaderRawReader : public FaderRawReader {
   public:
    bool begin() override {
        if (!terminal_config::FADER_ADC_ENABLED) {
            return false;
        }
        for (std::size_t lane = 0; lane < terminal_config::FADER_ADC_PINS.size(); ++lane) {
            pinMode(terminal_config::FADER_ADC_PINS[lane], INPUT);
        }
        return true;
    }

    int readRaw(std::size_t lane) override {
        if (!terminal_config::FADER_ADC_ENABLED || lane >= terminal_config::FADER_ADC_PINS.size()) {
            return terminal_fader_filter::RAW_SAMPLE_MISSING;
        }
        return analogRead(terminal_config::FADER_ADC_PINS[lane]);
    }
};
#else
class ArduinoAdcFaderRawReader : public MissingFaderRawReader {};
#endif

#if TERMINAL_FADER_HAS_PBHUB
using ConfiguredFaderRawReader = ArduinoPbHubFaderRawReader;
#elif TERMINAL_FADER_HAS_ARDUINO_ADC
using ConfiguredFaderRawReader = ArduinoAdcFaderRawReader;
#else
using ConfiguredFaderRawReader = MissingFaderRawReader;
#endif

class FaderDriver {
   public:
    FaderDriver()
        : FaderDriver(defaultReader()) {}

    explicit FaderDriver(FaderRawReader& rawReader)
        : rawReader_(rawReader),
          filter_(terminal_fader_filter::FaderFilter::CalibrationSet{
              terminal_fader_filter::FaderCalibration{
                  terminal_config::FADER_RAW_MIN,
                  terminal_config::FADER_RAW_MAX,
                  terminal_config::FADER_DEADBAND_PERCENT,
                  1,
                  terminal_config::FADER_RAW_MIDS[0]},
              terminal_fader_filter::FaderCalibration{
                  terminal_config::FADER_RAW_MIN,
                  terminal_config::FADER_RAW_MAX,
                  terminal_config::FADER_DEADBAND_PERCENT,
                  1,
                  terminal_config::FADER_RAW_MIDS[1]},
              terminal_fader_filter::FaderCalibration{
                  terminal_config::FADER_RAW_MIN,
                  terminal_config::FADER_RAW_MAX,
                  terminal_config::FADER_DEADBAND_PERCENT,
                  1,
                  terminal_config::FADER_RAW_MIDS[2]},
              terminal_fader_filter::FaderCalibration{
                  terminal_config::FADER_RAW_MIN,
                  terminal_config::FADER_RAW_MAX,
                  terminal_config::FADER_DEADBAND_PERCENT,
                  1,
                  terminal_config::FADER_RAW_MIDS[3]},
              terminal_fader_filter::FaderCalibration{
                  terminal_config::FADER_RAW_MIN,
                  terminal_config::FADER_RAW_MAX,
                  terminal_config::FADER_DEADBAND_PERCENT,
                  1,
                  terminal_config::FADER_RAW_MIDS[4]}}) {}

    bool begin() {
        filter_.reset();
        available_ = rawReader_.begin();
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            filter_.prime(lane, rawReader_.readRaw(lane));
        }
        return available_;
    }

    bool available() const {
        return available_;
    }

    void lockToDraft(const terminal_setup::TerminalSetupState& setup) {
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            filter_.lockUntilPickup(lane, setup.draftLane(lane).brightness);
        }
    }

    void read(ControlSnapshot& snapshot) {
        for (std::size_t lane = 0; lane < snapshot.lanes.size(); ++lane) {
            snapshot.lanes[lane].sliderPercent = terminal_control_surface::SLIDER_UNCHANGED;
            const int filtered = filter_.update(lane, rawReader_.readRaw(lane));
            if (filtered != terminal_control_surface::SLIDER_UNCHANGED) {
                snapshot.lanes[lane].sliderPercent = filtered;
            }
        }
    }

   private:
    static MissingFaderRawReader& defaultReader() {
        static MissingFaderRawReader reader;
        return reader;
    }

    FaderRawReader& rawReader_;
    bool available_ = false;
    terminal_fader_filter::FaderFilter filter_;
};

class ConfiguredFaderDriver {
   public:
    ConfiguredFaderDriver()
        : driver_(rawReader_) {}

    bool begin() {
        return driver_.begin();
    }

    bool available() const {
        return driver_.available();
    }

    void lockToDraft(const terminal_setup::TerminalSetupState& setup) {
        driver_.lockToDraft(setup);
    }

    void read(ControlSnapshot& snapshot) {
        driver_.read(snapshot);
    }

   private:
    ConfiguredFaderRawReader rawReader_;
    FaderDriver driver_;
};

#undef TERMINAL_FADER_HAS_ARDUINO_ADC
#undef TERMINAL_FADER_HAS_PBHUB

}  // namespace terminal_fader_driver
