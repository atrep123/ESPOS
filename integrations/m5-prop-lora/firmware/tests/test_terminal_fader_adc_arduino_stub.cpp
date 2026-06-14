#define ARDUINO 1
#define TERMINAL_FADER_ADC_ENABLED 1
#define TERMINAL_FADER_LANE1_ADC_PIN 11
#define TERMINAL_FADER_LANE2_ADC_PIN 12
#define TERMINAL_FADER_LANE3_ADC_PIN 13
#define TERMINAL_FADER_LANE4_ADC_PIN 14
#define TERMINAL_FADER_LANE5_ADC_PIN 15

#include "../sticks3-terminal/src/drivers/terminal_fader_driver.h"

#include <array>
#include <cstddef>
#include <iostream>
#include <type_traits>

static_assert(std::is_same<terminal_fader_driver::ConfiguredFaderRawReader, terminal_fader_driver::ArduinoAdcFaderRawReader>::value,
              "configured fader raw reader should use Arduino ADC when enabled");

namespace {

struct PinModeCall {
    int pin = -1;
    int mode = -1;
};

std::array<PinModeCall, 8> g_pinModeCalls = {};
std::array<int, 64> g_analogValues = {};
std::array<int, 8> g_analogReadPins = {};
std::size_t g_pinModeCount = 0;
std::size_t g_analogReadCount = 0;

void resetArduinoStub() {
    g_pinModeCalls.fill(PinModeCall{-1, -1});
    g_analogValues.fill(0);
    g_analogReadPins.fill(-1);
    g_pinModeCount = 0;
    g_analogReadCount = 0;
}

bool pinModeCallsFiveLanePinsAsInput() {
    resetArduinoStub();
    terminal_fader_driver::ArduinoAdcFaderRawReader reader;
    const bool began = reader.begin();

    return began &&
           g_pinModeCount == 5 &&
           g_pinModeCalls[0].pin == 11 && g_pinModeCalls[0].mode == INPUT &&
           g_pinModeCalls[1].pin == 12 && g_pinModeCalls[1].mode == INPUT &&
           g_pinModeCalls[2].pin == 13 && g_pinModeCalls[2].mode == INPUT &&
           g_pinModeCalls[3].pin == 14 && g_pinModeCalls[3].mode == INPUT &&
           g_pinModeCalls[4].pin == 15 && g_pinModeCalls[4].mode == INPUT;
}

bool analogReadFollowsLanePinMapping() {
    resetArduinoStub();
    g_analogValues[11] = 111;
    g_analogValues[12] = 222;
    g_analogValues[13] = 333;
    g_analogValues[14] = 444;
    g_analogValues[15] = 555;

    terminal_fader_driver::ArduinoAdcFaderRawReader reader;
    if (!reader.begin()) {
        return false;
    }

    return reader.readRaw(0) == 111 &&
           reader.readRaw(1) == 222 &&
           reader.readRaw(2) == 333 &&
           reader.readRaw(3) == 444 &&
           reader.readRaw(4) == 555 &&
           g_analogReadCount == 5 &&
           g_analogReadPins[0] == 11 &&
           g_analogReadPins[1] == 12 &&
           g_analogReadPins[2] == 13 &&
           g_analogReadPins[3] == 14 &&
           g_analogReadPins[4] == 15;
}

bool invalidLaneReturnsMissingSample() {
    resetArduinoStub();
    terminal_fader_driver::ArduinoAdcFaderRawReader reader;
    if (!reader.begin()) {
        return false;
    }
    g_analogReadCount = 0;
    return reader.readRaw(terminal_setup::LANE_COUNT) == terminal_fader_filter::RAW_SAMPLE_MISSING &&
           g_analogReadCount == 0;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

void pinMode(int pin, int mode) {
    if (g_pinModeCount < g_pinModeCalls.size()) {
        g_pinModeCalls[g_pinModeCount] = PinModeCall{pin, mode};
    }
    ++g_pinModeCount;
}

int analogRead(int pin) {
    if (g_analogReadCount < g_analogReadPins.size()) {
        g_analogReadPins[g_analogReadCount] = pin;
    }
    ++g_analogReadCount;
    if (pin >= 0 && static_cast<std::size_t>(pin) < g_analogValues.size()) {
        return g_analogValues[static_cast<std::size_t>(pin)];
    }
    return terminal_fader_filter::RAW_SAMPLE_MISSING;
}

int main() {
    int failures = 0;
    failures += runCase("pinMode calls five lane pins as INPUT", pinModeCallsFiveLanePinsAsInput) ? 0 : 1;
    failures += runCase("analogRead follows lane pin mapping", analogReadFollowsLanePinMapping) ? 0 : 1;
    failures += runCase("invalid lane returns missing sample", invalidLaneReturnsMissingSample) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
