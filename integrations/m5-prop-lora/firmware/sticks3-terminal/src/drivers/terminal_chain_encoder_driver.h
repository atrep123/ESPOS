#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "../terminal_config.h"
#include "../terminal_control_surface.h"
#include "../terminal_encoder_filter.h"
#include "../terminal_grove_route.h"
#include "../terminal_switches.h"

#if TERMINAL_CHAIN_RX_PIN >= 0 && TERMINAL_CHAIN_TX_PIN >= 0
#define TERMINAL_CHAIN_UART_CONFIGURED 1
#else
#define TERMINAL_CHAIN_UART_CONFIGURED 0
#endif

#if defined(ARDUINO) && TERMINAL_CHAIN_UART_CONFIGURED
#include <M5Chain.h>
#define TERMINAL_CHAIN_HAS_M5CHAIN 1
#else
#define TERMINAL_CHAIN_HAS_M5CHAIN 0
#endif

namespace terminal_chain_encoder_driver {

using terminal_control_surface::ControlSnapshot;

// The bench chain is wired physical LED5 -> LED1, while setup lanes are logical LED1 -> LED5.
constexpr std::array<std::uint8_t, terminal_setup::LANE_COUNT> CHAIN_ENCODER_IDS = {5, 4, 3, 2, 1};
constexpr std::uint8_t CHAIN_KEY_UPLOAD_ID = 6;
constexpr std::uint8_t CHAIN_KEY_SIM_FIRE_ID = 7;
constexpr unsigned long CHAIN_ENCODER_QUERY_TIMEOUT_MS = 20;
constexpr unsigned long CHAIN_KEY_QUERY_TIMEOUT_MS = 20;

constexpr std::uint8_t chainEncoderIdForLane(std::size_t lane) {
    return lane < CHAIN_ENCODER_IDS.size() ? CHAIN_ENCODER_IDS[lane] : 0;
}

struct ChainPressEdges {
    ChainPressEdges() = default;
    ChainPressEdges(bool encoderPressedValue, bool effectPressedValue)
        : encoderPressed(encoderPressedValue),
          effectPressed(effectPressedValue) {}

    bool encoderPressed = false;
    bool effectPressed = false;
};

inline ChainPressEdges classifyChainPress(bool sawSinglePress, bool sawLongPress) {
    return ChainPressEdges{
        false,
        sawSinglePress || sawLongPress};
}

inline terminal_encoder_filter::EncoderSample makeChainEncoderSample(
    int position,
    bool sawSinglePress,
    bool sawLongPress) {
    const ChainPressEdges press = classifyChainPress(sawSinglePress, sawLongPress);
    return terminal_encoder_filter::EncoderSample{
        position,
        press.encoderPressed,
        press.effectPressed};
}

inline terminal_encoder_filter::EncoderSample makeChainEncoderIncrementSample(
    int increment,
    bool sawSinglePress,
    bool sawLongPress) {
    const ChainPressEdges press = classifyChainPress(sawSinglePress, sawLongPress);
    return terminal_encoder_filter::EncoderSample{
        terminal_encoder_filter::ENCODER_POSITION_MISSING,
        press.encoderPressed,
        press.effectPressed,
        increment,
        true};
}

inline void applyChainKeyButtonLevels(bool uploadButtonPressed,
                                      bool lastSwitchPressed,
                                      terminal_switches::SwitchSnapshot& snapshot) {
    snapshot.uploadPressed = snapshot.uploadPressed || uploadButtonPressed;
    snapshot.simFirePressed = snapshot.simFirePressed || lastSwitchPressed;
}

class ChainEncoderRawReader {
   public:
    virtual ~ChainEncoderRawReader() = default;
    virtual bool begin() = 0;

    virtual bool prepareReadCycle() {
        return true;
    }

    virtual terminal_encoder_filter::EncoderSample readSample(std::size_t lane) = 0;

    virtual void readSwitches(terminal_switches::SwitchSnapshot& snapshot) {
        (void)snapshot;
    }
};

class MissingChainEncoderRawReader : public ChainEncoderRawReader {
   public:
    bool begin() override {
        return false;
    }

    bool prepareReadCycle() override {
        return false;
    }

    terminal_encoder_filter::EncoderSample readSample(std::size_t lane) override {
        (void)lane;
        return terminal_encoder_filter::EncoderSample{
            terminal_encoder_filter::ENCODER_POSITION_MISSING,
            false,
            false};
    }
};

#if TERMINAL_CHAIN_HAS_M5CHAIN
class M5ChainEncoderRawReader : public ChainEncoderRawReader {
   public:
    bool begin() override {
        if (!prepareReadCycle()) {
            return false;
        }
        if (!chain_.isDeviceConnected()) {
            return false;
        }
        configureEncoders();
        configureKeys();
        return true;
    }

    bool prepareReadCycle() override {
        const bool wasChainSelected = terminal_grove_route::chainSelected();
        if (!terminal_grove_route::selectChainPahub()) {
            return false;
        }
        if (!serialBegun_ || !wasChainSelected) {
            Serial1.end();
            delay(2);
            chain_.begin(
                &Serial1,
                terminal_config::CHAIN_BAUD,
                terminal_config::CHAIN_RX_PIN,
                terminal_config::CHAIN_TX_PIN);
            serialBegun_ = true;
        }
        return true;
    }

    terminal_encoder_filter::EncoderSample readSample(std::size_t lane) override {
        if (!prepareReadCycle() || lane >= terminal_setup::LANE_COUNT) {
            return terminal_encoder_filter::EncoderSample{
                terminal_encoder_filter::ENCODER_POSITION_MISSING,
                false,
                false};
        }
        const std::uint8_t id = chainEncoderIdForLane(lane);
#if TERMINAL_LIVE_DEBUG
        const unsigned long nowMs = millis();
        if (lane == 0 && nowMs - lastDiagnosticMs_ >= 1000UL) {
            diagnosticCycle_ = true;
            lastDiagnosticMs_ = nowMs;
        }
        int16_t absoluteValue = 0;
        const int valueStatus =
            chain_.getEncoderValue(id, &absoluteValue, CHAIN_ENCODER_QUERY_TIMEOUT_MS);
#endif
        int16_t increment = 0;
        const int incrementStatus =
            chain_.getEncoderIncValue(id, &increment, CHAIN_ENCODER_QUERY_TIMEOUT_MS);
        const bool incrementOk = incrementStatus == CHAIN_OK;

        bool singlePressed = false;
        bool effectPressed = false;
        chain_button_press_type_t pressType = CHAIN_BUTTON_PRESS_SINGLE;
        while (chain_.getEncoderButtonPressStatus(id, &pressType)) {
            if (pressType == CHAIN_BUTTON_PRESS_SINGLE) {
                singlePressed = true;
            } else if (pressType == CHAIN_BUTTON_PRESS_LONG) {
                effectPressed = true;
            }
        }
        const int reportedIncrement = incrementOk ? static_cast<int>(increment) : 0;
#if TERMINAL_LIVE_DEBUG
        if (diagnosticCycle_) {
            Serial.printf("TERMINAL_CHAIN_RAW L%u id=%u value_status=%d value=%d inc_status=%d inc=%d single=%u long=%u\n",
                          static_cast<unsigned>(lane + 1U),
                          id,
                          valueStatus,
                          static_cast<int>(absoluteValue),
                          incrementStatus,
                          static_cast<int>(increment),
                          singlePressed ? 1U : 0U,
                          effectPressed ? 1U : 0U);
            if (lane + 1U >= terminal_setup::LANE_COUNT) {
                diagnosticCycle_ = false;
                Serial.flush();
            }
        }
#endif
        return makeChainEncoderIncrementSample(reportedIncrement, singlePressed, effectPressed);
    }

    void readSwitches(terminal_switches::SwitchSnapshot& snapshot) override {
        if (!prepareReadCycle()) {
            return;
        }

        std::uint8_t uploadButton = 0;
        const bool uploadOk =
            chain_.getKeyButtonStatus(CHAIN_KEY_UPLOAD_ID, &uploadButton, CHAIN_KEY_QUERY_TIMEOUT_MS) == CHAIN_OK;

        std::uint8_t simFireButton = 0;
        const bool simFireOk =
            chain_.getKeyButtonStatus(CHAIN_KEY_SIM_FIRE_ID, &simFireButton, CHAIN_KEY_QUERY_TIMEOUT_MS) == CHAIN_OK;

        applyChainKeyButtonLevels(uploadOk && uploadButton != 0,
                                  simFireOk && simFireButton != 0,
                                  snapshot);
    }

   private:
    void configureEncoders() {
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            const std::uint8_t id = chainEncoderIdForLane(lane);
            uint8_t operationStatus = 0;
            chain_.setEncoderButtonTriggerInterval(
                id,
                BUTTON_DOUBLE_CLICK_TIME_200MS,
                BUTTON_LONG_PRESS_TIME_3S,
                &operationStatus,
                CHAIN_ENCODER_QUERY_TIMEOUT_MS);
            chain_.setEncoderButtonMode(
                id,
                CHAIN_BUTTON_REPORT_MODE,
                &operationStatus,
                CHAIN_ENCODER_QUERY_TIMEOUT_MS);
            chain_.setEncoderABDirect(
                id,
                ENCODER_AB,
                &operationStatus,
                CHAIN_SAVE_FLASH_DISABLE,
                CHAIN_ENCODER_QUERY_TIMEOUT_MS);
        }
    }

    void configureKeys() {
        const std::uint8_t keyIds[] = {CHAIN_KEY_UPLOAD_ID, CHAIN_KEY_SIM_FIRE_ID};
        for (std::uint8_t id : keyIds) {
            std::uint8_t operationStatus = 0;
            chain_.setKeyButtonTriggerInterval(
                id,
                BUTTON_DOUBLE_CLICK_TIME_200MS,
                BUTTON_LONG_PRESS_TIME_3S,
                &operationStatus,
                CHAIN_KEY_QUERY_TIMEOUT_MS);
            chain_.setKeyButtonMode(id, CHAIN_BUTTON_REPORT_MODE, &operationStatus, CHAIN_KEY_QUERY_TIMEOUT_MS);
        }
    }

    bool serialBegun_ = false;
    Chain chain_;
#if TERMINAL_LIVE_DEBUG
    unsigned long lastDiagnosticMs_ = 0;
    bool diagnosticCycle_ = false;
#endif
};
#else
class M5ChainEncoderRawReader : public MissingChainEncoderRawReader {};
#endif

#if TERMINAL_CHAIN_HAS_M5CHAIN
using ConfiguredChainEncoderRawReader = M5ChainEncoderRawReader;
#else
using ConfiguredChainEncoderRawReader = MissingChainEncoderRawReader;
#endif

class ChainEncoderDriver {
   public:
    ChainEncoderDriver()
        : ChainEncoderDriver(defaultReader()) {}

    explicit ChainEncoderDriver(ChainEncoderRawReader& rawReader)
        : rawReader_(rawReader),
          filter_(terminal_encoder_filter::EncoderCalibration{
              terminal_config::ENCODER_DEGREES_PER_DETENT}) {}

    bool begin() {
        filter_.reset();
        available_ = rawReader_.begin();
        if (available_) {
            for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
                filter_.prime(lane, rawReader_.readSample(lane));
            }
        }
        return available_;
    }

    bool available() const {
        return available_;
    }

    void read(ControlSnapshot& snapshot) {
        const bool cycleReady = available_ && rawReader_.prepareReadCycle();
        for (std::size_t lane = 0; lane < snapshot.lanes.size(); ++lane) {
            snapshot.lanes[lane].encoderDelta = 0;
            snapshot.lanes[lane].encoderPressed = false;
            snapshot.lanes[lane].effectPressed = false;
            const terminal_control_surface::LaneInput input = cycleReady
                ? filter_.update(lane, rawReader_.readSample(lane))
                : terminal_control_surface::LaneInput{};
            snapshot.lanes[lane].encoderDelta = input.encoderDelta;
            snapshot.lanes[lane].encoderPressed = input.encoderPressed;
            snapshot.lanes[lane].effectPressed = input.effectPressed;
        }
    }

    void readSwitches(terminal_switches::SwitchSnapshot& snapshot) {
        if (available_) {
            rawReader_.readSwitches(snapshot);
        }
    }

   private:
    static MissingChainEncoderRawReader& defaultReader() {
        static MissingChainEncoderRawReader reader;
        return reader;
    }

    ChainEncoderRawReader& rawReader_;
    bool available_ = false;
    terminal_encoder_filter::EncoderFilter filter_;
};

class ConfiguredChainEncoderDriver {
   public:
    ConfiguredChainEncoderDriver()
        : driver_(rawReader_) {}

    bool begin() {
        return driver_.begin();
    }

    bool available() const {
        return driver_.available();
    }

    void read(ControlSnapshot& snapshot) {
        driver_.read(snapshot);
    }

    void readSwitches(terminal_switches::SwitchSnapshot& snapshot) {
        driver_.readSwitches(snapshot);
    }

   private:
    ConfiguredChainEncoderRawReader rawReader_;
    ChainEncoderDriver driver_;
};

#undef TERMINAL_CHAIN_HAS_M5CHAIN
#undef TERMINAL_CHAIN_UART_CONFIGURED

}  // namespace terminal_chain_encoder_driver
