#include "../sticks3-terminal/src/terminal_switch_dispatch.h"

#include <iostream>

namespace {

using terminal_switch_dispatch::SwitchAction;
using terminal_switch_dispatch::chooseAction;
using terminal_switches::SwitchEdgeTracker;
using terminal_switches::SwitchEvents;
using terminal_switches::SwitchSnapshot;

bool uploadEventSelectsUpload() {
    SwitchEvents events;
    events.upload = true;
    return chooseAction(events, false) == SwitchAction::Upload;
}

bool simFireEventSelectsSimFireWhenIdle() {
    SwitchEvents events;
    events.simFire = true;
    return chooseAction(events, false) == SwitchAction::SimFire;
}

bool simultaneousSwitchesPreferUpload() {
    SwitchEvents events;
    events.upload = true;
    events.simFire = true;
    return chooseAction(events, false) == SwitchAction::Upload;
}

bool uploadInFlightSuppressesSwitchActions() {
    SwitchEvents events;
    events.upload = true;
    events.simFire = true;
    return chooseAction(events, true) == SwitchAction::None;
}

bool idleSwitchEventsSelectNoAction() {
    SwitchEvents events;
    return chooseAction(events, false) == SwitchAction::None;
}

bool simFireHeldThroughUploadCompletionNeedsReleaseAndRepress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.simFirePressed = true;

    const SwitchEvents duringUpload = tracker.update(snapshot);
    if (chooseAction(duringUpload, true) != SwitchAction::None) {
        return false;
    }

    const SwitchEvents stillHeldAfterUpload = tracker.update(snapshot);
    if (chooseAction(stillHeldAfterUpload, false) != SwitchAction::None) {
        return false;
    }

    snapshot.simFirePressed = false;
    tracker.update(snapshot);
    snapshot.simFirePressed = true;
    return chooseAction(tracker.update(snapshot), false) == SwitchAction::SimFire;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("upload event selects upload", uploadEventSelectsUpload) ? 0 : 1;
    failures += runCase("sim-fire event selects sim-fire when idle", simFireEventSelectsSimFireWhenIdle) ? 0 : 1;
    failures += runCase("simultaneous switches prefer upload", simultaneousSwitchesPreferUpload) ? 0 : 1;
    failures += runCase("upload in flight suppresses switch actions", uploadInFlightSuppressesSwitchActions) ? 0 : 1;
    failures += runCase("idle switch events select no action", idleSwitchEventsSelectNoAction) ? 0 : 1;
    failures += runCase(
        "sim fire held through upload completion needs release and repress",
        simFireHeldThroughUploadCompletionNeedsReleaseAndRepress)
        ? 0
        : 1;
    return failures == 0 ? 0 : 1;
}
