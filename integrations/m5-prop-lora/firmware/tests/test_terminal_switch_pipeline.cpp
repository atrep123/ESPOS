#include "../sticks3-terminal/src/terminal_switch_pipeline.h"

#include <iostream>

namespace {

using terminal_switch_dispatch::SwitchAction;
using terminal_switch_pipeline::SwitchPipeline;
using terminal_switches::SwitchSnapshot;

bool bounceDoesNotDispatchBeforeStableWindow() {
    SwitchPipeline pipeline(30);
    SwitchSnapshot raw;
    pipeline.prime(raw, 0);

    raw.uploadPressed = true;
    if (pipeline.update(raw, 10, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = false;
    if (pipeline.update(raw, 15, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = true;
    if (pipeline.update(raw, 40, false) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 69, false) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 70, false) != SwitchAction::Upload) {
        return false;
    }
    return pipeline.update(raw, 75, false) == SwitchAction::None;
}

bool bootHeldSwitchesDoNotDispatchUntilReleaseAndRepress() {
    SwitchPipeline pipeline(30);
    SwitchSnapshot raw;
    raw.uploadPressed = true;
    raw.simFirePressed = true;
    pipeline.prime(raw, 100);

    if (pipeline.update(raw, 150, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = false;
    raw.simFirePressed = false;
    if (pipeline.update(raw, 190, false) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 220, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = true;
    if (pipeline.update(raw, 230, false) != SwitchAction::None) {
        return false;
    }
    return pipeline.update(raw, 260, false) == SwitchAction::Upload;
}

bool simFireHeldWhileUploadInFlightNeedsReleaseAndRepress() {
    SwitchPipeline pipeline(0);
    SwitchSnapshot raw;
    pipeline.prime(raw, 0);

    raw.simFirePressed = true;
    if (pipeline.update(raw, 1, true) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 2, false) != SwitchAction::None) {
        return false;
    }
    raw.simFirePressed = false;
    if (pipeline.update(raw, 3, false) != SwitchAction::None) {
        return false;
    }
    raw.simFirePressed = true;
    return pipeline.update(raw, 4, false) == SwitchAction::SimFire;
}

bool uploadHeldWhileUploadInFlightNeedsReleaseAndRepress() {
    SwitchPipeline pipeline(0);
    SwitchSnapshot raw;
    pipeline.prime(raw, 0);

    raw.uploadPressed = true;
    if (pipeline.update(raw, 1, true) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 2, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = false;
    if (pipeline.update(raw, 3, false) != SwitchAction::None) {
        return false;
    }
    raw.uploadPressed = true;
    return pipeline.update(raw, 4, false) == SwitchAction::Upload;
}

bool simultaneousDebouncedPressPrefersUpload() {
    SwitchPipeline pipeline(20);
    SwitchSnapshot raw;
    pipeline.prime(raw, 0);

    raw.uploadPressed = true;
    raw.simFirePressed = true;
    if (pipeline.update(raw, 10, false) != SwitchAction::None) {
        return false;
    }
    if (pipeline.update(raw, 29, false) != SwitchAction::None) {
        return false;
    }
    return pipeline.update(raw, 30, false) == SwitchAction::Upload;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("bounce does not dispatch before stable window", bounceDoesNotDispatchBeforeStableWindow) ? 0 : 1;
    failures += runCase(
        "boot-held switches do not dispatch until release and repress",
        bootHeldSwitchesDoNotDispatchUntilReleaseAndRepress)
        ? 0
        : 1;
    failures += runCase(
        "sim fire held while upload in flight needs release and repress",
        simFireHeldWhileUploadInFlightNeedsReleaseAndRepress)
        ? 0
        : 1;
    failures += runCase(
        "upload held while upload in flight needs release and repress",
        uploadHeldWhileUploadInFlightNeedsReleaseAndRepress)
        ? 0
        : 1;
    failures += runCase("simultaneous debounced press prefers upload", simultaneousDebouncedPressPrefersUpload) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
