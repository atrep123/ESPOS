#include "../sticks3-terminal/src/terminal_switch_debounce.h"

#include <iostream>

namespace {

using terminal_switch_debounce::SwitchDebouncer;
using terminal_switches::SwitchSnapshot;

bool pressBounceWaitsForStableDebounceWindow() {
    SwitchDebouncer debouncer(30);
    SwitchSnapshot raw;
    debouncer.prime(raw, 0);

    raw.uploadPressed = true;
    if (debouncer.update(raw, 10).uploadPressed) {
        return false;
    }
    raw.uploadPressed = false;
    if (debouncer.update(raw, 15).uploadPressed) {
        return false;
    }
    raw.uploadPressed = true;
    if (debouncer.update(raw, 40).uploadPressed) {
        return false;
    }
    if (debouncer.update(raw, 69).uploadPressed) {
        return false;
    }
    return debouncer.update(raw, 70).uploadPressed == true;
}

bool releaseBounceWaitsForStableDebounceWindow() {
    SwitchDebouncer debouncer(30);
    SwitchSnapshot raw;
    raw.uploadPressed = true;
    debouncer.prime(raw, 0);

    raw.uploadPressed = false;
    if (!debouncer.update(raw, 10).uploadPressed) {
        return false;
    }
    raw.uploadPressed = true;
    if (!debouncer.update(raw, 15).uploadPressed) {
        return false;
    }
    raw.uploadPressed = false;
    if (!debouncer.update(raw, 40).uploadPressed) {
        return false;
    }
    if (!debouncer.update(raw, 69).uploadPressed) {
        return false;
    }
    return debouncer.update(raw, 70).uploadPressed == false;
}

bool uploadAndSimFireDebounceIndependently() {
    SwitchDebouncer debouncer(30);
    SwitchSnapshot raw;
    debouncer.prime(raw, 0);

    raw.uploadPressed = true;
    debouncer.update(raw, 10);
    raw.simFirePressed = true;
    const SwitchSnapshot beforeSimStable = debouncer.update(raw, 40);
    if (!beforeSimStable.uploadPressed || beforeSimStable.simFirePressed) {
        return false;
    }
    const SwitchSnapshot afterSimStable = debouncer.update(raw, 70);
    return afterSimStable.uploadPressed && afterSimStable.simFirePressed;
}

bool primeKeepsBootHeldSwitchStableWithoutTransition() {
    SwitchDebouncer debouncer(30);
    SwitchSnapshot raw;
    raw.uploadPressed = true;
    raw.simFirePressed = true;
    debouncer.prime(raw, 100);
    const SwitchSnapshot stable = debouncer.stable();
    if (!stable.uploadPressed || !stable.simFirePressed) {
        return false;
    }
    return debouncer.update(raw, 101).uploadPressed && debouncer.update(raw, 101).simFirePressed;
}

bool zeroDebounceFollowsRawImmediately() {
    SwitchDebouncer debouncer(0);
    SwitchSnapshot raw;
    debouncer.prime(raw, 0);
    raw.simFirePressed = true;
    const SwitchSnapshot pressed = debouncer.update(raw, 1);
    if (!pressed.simFirePressed) {
        return false;
    }
    raw.simFirePressed = false;
    return debouncer.update(raw, 2).simFirePressed == false;
}

bool millisRolloverKeepsDebounceWindow() {
    SwitchDebouncer debouncer(30);
    SwitchSnapshot raw;
    debouncer.prime(raw, 0xFFFFFFF0u);

    raw.uploadPressed = true;
    if (debouncer.update(raw, 0xFFFFFFF5u).uploadPressed) {
        return false;
    }
    if (debouncer.update(raw, 18).uploadPressed) {
        return false;
    }
    return debouncer.update(raw, 19).uploadPressed == true;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("press bounce waits for stable debounce window", pressBounceWaitsForStableDebounceWindow) ? 0 : 1;
    failures += runCase("release bounce waits for stable debounce window", releaseBounceWaitsForStableDebounceWindow) ? 0 : 1;
    failures += runCase("upload and sim-fire debounce independently", uploadAndSimFireDebounceIndependently) ? 0 : 1;
    failures += runCase("prime keeps boot-held switch stable without transition", primeKeepsBootHeldSwitchStableWithoutTransition) ? 0 : 1;
    failures += runCase("zero debounce follows raw immediately", zeroDebounceFollowsRawImmediately) ? 0 : 1;
    failures += runCase("millis rollover keeps debounce window", millisRolloverKeepsDebounceWindow) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
