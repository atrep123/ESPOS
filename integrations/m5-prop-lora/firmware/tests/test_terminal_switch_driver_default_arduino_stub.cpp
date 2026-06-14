#define ARDUINO 1

#include "../sticks3-terminal/src/drivers/terminal_switch_driver.h"

#include <cstddef>
#include <iostream>

namespace {

std::size_t g_pinModeCount = 0;
std::size_t g_digitalReadCount = 0;

bool negativePinsStayUnconfiguredAndUnpressed() {
    terminal_switch_driver::SwitchDriver switches;
    switches.begin();
    const terminal_switches::SwitchSnapshot snapshot = switches.read();
    return g_pinModeCount == 0 &&
           g_digitalReadCount == 0 &&
           !snapshot.uploadPressed &&
           !snapshot.simFirePressed;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

void pinMode(int pin, int mode) {
    (void)pin;
    (void)mode;
    ++g_pinModeCount;
}

int analogRead(int pin) {
    (void)pin;
    return 0;
}

int digitalRead(int pin) {
    (void)pin;
    ++g_digitalReadCount;
    return HIGH;
}

int main() {
    int failures = 0;
    failures += runCase("negative pins stay unconfigured and unpressed", negativePinsStayUnconfiguredAndUnpressed) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
