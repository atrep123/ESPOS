#define ARDUINO 1
#define TERMINAL_UPLOAD_SWITCH_PIN 21
#define TERMINAL_SIM_FIRE_SWITCH_PIN 22

#include "../sticks3-terminal/src/drivers/terminal_switch_driver.h"

#include <array>
#include <cstddef>
#include <iostream>

namespace {

struct PinModeCall {
    int pin = -1;
    int mode = -1;
};

std::array<PinModeCall, 4> g_pinModeCalls = {};
std::array<int, 64> g_pinStates = {};
std::array<int, 8> g_digitalReadPins = {};
std::size_t g_pinModeCount = 0;
std::size_t g_digitalReadCount = 0;

void resetArduinoStub() {
    g_pinModeCalls.fill(PinModeCall{-1, -1});
    g_pinStates.fill(HIGH);
    g_digitalReadPins.fill(-1);
    g_pinModeCount = 0;
    g_digitalReadCount = 0;
}

bool pinModeConfiguresBothSwitchesAsInputPullup() {
    resetArduinoStub();
    terminal_switch_driver::SwitchDriver switches;
    switches.begin();

    return g_pinModeCount == 2 &&
           g_pinModeCalls[0].pin == 21 && g_pinModeCalls[0].mode == INPUT_PULLUP &&
           g_pinModeCalls[1].pin == 22 && g_pinModeCalls[1].mode == INPUT_PULLUP;
}

bool lowReadsAsPressedAndHighReadsAsReleased() {
    resetArduinoStub();
    g_pinStates[21] = LOW;
    g_pinStates[22] = HIGH;

    terminal_switch_driver::SwitchDriver switches;
    const terminal_switches::SwitchSnapshot first = switches.read();
    if (!first.uploadPressed || first.simFirePressed) {
        return false;
    }
    if (g_digitalReadCount != 2 || g_digitalReadPins[0] != 21 || g_digitalReadPins[1] != 22) {
        return false;
    }

    g_pinStates[21] = HIGH;
    g_pinStates[22] = LOW;
    const terminal_switches::SwitchSnapshot second = switches.read();
    return !second.uploadPressed && second.simFirePressed;
}

bool simultaneousLowReadsBothSwitchesPressed() {
    resetArduinoStub();
    g_pinStates[21] = LOW;
    g_pinStates[22] = LOW;

    terminal_switch_driver::SwitchDriver switches;
    const terminal_switches::SwitchSnapshot snapshot = switches.read();

    return snapshot.uploadPressed &&
           snapshot.simFirePressed &&
           g_digitalReadCount == 2 &&
           g_digitalReadPins[0] == 21 &&
           g_digitalReadPins[1] == 22;
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
    (void)pin;
    return 0;
}

int digitalRead(int pin) {
    if (g_digitalReadCount < g_digitalReadPins.size()) {
        g_digitalReadPins[g_digitalReadCount] = pin;
    }
    ++g_digitalReadCount;
    if (pin >= 0 && static_cast<std::size_t>(pin) < g_pinStates.size()) {
        return g_pinStates[static_cast<std::size_t>(pin)];
    }
    return HIGH;
}

int main() {
    int failures = 0;
    failures += runCase("pinMode configures both switches as INPUT_PULLUP", pinModeConfiguresBothSwitchesAsInputPullup) ? 0 : 1;
    failures += runCase("LOW reads as pressed and HIGH reads as released", lowReadsAsPressedAndHighReadsAsReleased) ? 0 : 1;
    failures += runCase("simultaneous LOW reads both switches pressed", simultaneousLowReadsBothSwitchesPressed) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
