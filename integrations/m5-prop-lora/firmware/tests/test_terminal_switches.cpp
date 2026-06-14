#include "../sticks3-terminal/src/terminal_switches.h"

#include <iostream>

namespace {

using terminal_switches::SwitchEdgeTracker;
using terminal_switches::SwitchEvents;
using terminal_switches::SwitchSnapshot;

bool uploadSwitchFiresOncePerPress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    const SwitchEvents first = tracker.update(snapshot);
    const SwitchEvents held = tracker.update(snapshot);
    return first.upload == true && held.upload == false && first.simFire == false;
}

bool simulateSwitchFiresOncePerPress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.simFirePressed = true;
    const SwitchEvents first = tracker.update(snapshot);
    const SwitchEvents held = tracker.update(snapshot);
    return first.simFire == true && held.simFire == false && first.upload == false;
}

bool releaseAndRepressEmitsNewEvents() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    tracker.update(snapshot);
    snapshot.uploadPressed = false;
    tracker.update(snapshot);
    snapshot.uploadPressed = true;
    return tracker.update(snapshot).upload == true;
}

bool simultaneousSwitchesEmitBothEvents() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    snapshot.simFirePressed = true;
    const SwitchEvents events = tracker.update(snapshot);
    return events.upload == true && events.simFire == true;
}

bool resetClearsHeldSwitchHistory() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    tracker.update(snapshot);
    tracker.reset();
    return tracker.update(snapshot).upload == true;
}

bool bootHeldSwitchesArePrimedWithoutEvents() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    snapshot.simFirePressed = true;
    tracker.prime(snapshot);
    const SwitchEvents held = tracker.update(snapshot);
    return held.upload == false && held.simFire == false;
}

bool bootHeldSimFireNeedsReleaseAndRepress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.simFirePressed = true;
    tracker.prime(snapshot);
    if (tracker.update(snapshot).simFire) {
        return false;
    }
    snapshot.simFirePressed = false;
    if (tracker.update(snapshot).simFire) {
        return false;
    }
    snapshot.simFirePressed = true;
    const SwitchEvents repress = tracker.update(snapshot);
    return repress.simFire == true && repress.upload == false;
}

bool bootHeldUploadNeedsReleaseAndRepress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    tracker.prime(snapshot);
    if (tracker.update(snapshot).upload) {
        return false;
    }
    snapshot.uploadPressed = false;
    if (tracker.update(snapshot).upload) {
        return false;
    }
    snapshot.uploadPressed = true;
    const SwitchEvents repress = tracker.update(snapshot);
    return repress.upload == true && repress.simFire == false;
}

bool bootPrimeWithIdleSwitchesPreservesFirstRealPress() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    tracker.prime(snapshot);
    snapshot.uploadPressed = true;
    const SwitchEvents upload = tracker.update(snapshot);
    if (!upload.upload || upload.simFire) {
        return false;
    }
    snapshot.uploadPressed = false;
    tracker.update(snapshot);
    snapshot.simFirePressed = true;
    const SwitchEvents simFire = tracker.update(snapshot);
    return simFire.simFire == true && simFire.upload == false;
}

bool bootHeldBothReleaseUploadThenRepressUploadEmitsOnlyUpload() {
    SwitchEdgeTracker tracker;
    SwitchSnapshot snapshot;
    snapshot.uploadPressed = true;
    snapshot.simFirePressed = true;
    tracker.prime(snapshot);
    if (tracker.update(snapshot).upload || tracker.update(snapshot).simFire) {
        return false;
    }
    snapshot.uploadPressed = false;
    if (tracker.update(snapshot).upload || tracker.update(snapshot).simFire) {
        return false;
    }
    snapshot.uploadPressed = true;
    const SwitchEvents repress = tracker.update(snapshot);
    return repress.upload == true && repress.simFire == false;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("upload switch fires once per press", uploadSwitchFiresOncePerPress) ? 0 : 1;
    failures += runCase("simulate switch fires once per press", simulateSwitchFiresOncePerPress) ? 0 : 1;
    failures += runCase("release and repress emits new events", releaseAndRepressEmitsNewEvents) ? 0 : 1;
    failures += runCase("simultaneous switches emit both events", simultaneousSwitchesEmitBothEvents) ? 0 : 1;
    failures += runCase("reset clears held switch history", resetClearsHeldSwitchHistory) ? 0 : 1;
    failures += runCase("boot-held switches are primed without events", bootHeldSwitchesArePrimedWithoutEvents) ? 0 : 1;
    failures += runCase("boot-held sim-fire needs release and repress", bootHeldSimFireNeedsReleaseAndRepress) ? 0 : 1;
    failures += runCase("boot-held upload needs release and repress", bootHeldUploadNeedsReleaseAndRepress) ? 0 : 1;
    failures += runCase("boot prime with idle switches preserves first real press", bootPrimeWithIdleSwitchesPreservesFirstRealPress) ? 0 : 1;
    failures += runCase(
        "boot-held both release upload then repress upload emits only upload",
        bootHeldBothReleaseUploadThenRepressUploadEmitsOnlyUpload)
        ? 0
        : 1;
    return failures == 0 ? 0 : 1;
}
