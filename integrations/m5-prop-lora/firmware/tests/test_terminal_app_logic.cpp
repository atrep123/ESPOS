#include "../sticks3-terminal/src/terminal_app_logic.h"

#include <iostream>

namespace {

using terminal_app_logic::TerminalAction;
using terminal_app_logic::handleUploadEvent;
using terminal_app_logic::requestSimFire;
using terminal_app_logic::requestUpload;
using terminal_setup::Status;
using terminal_setup::TerminalSetupState;
using terminal_usb_link::UploadEvent;
using terminal_usb_link::UsbSetupLink;

bool emptyAction(const TerminalAction& action) {
    return !action.drainUsbInput && !action.sendLine && !action.lockFadersToDraft &&
           !action.redraw && action.line.empty();
}

bool uploadRequestEmitsSetupLineAndStartsInFlight() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);

    const TerminalAction action = requestUpload(state, link, 100, 1500);

    return action.drainUsbInput &&
           action.sendLine &&
           action.redraw &&
           action.line.rfind("SETUP 1 ", 0) == 0 &&
           state.status() == Status::Uploading &&
           link.inFlight() &&
           link.requestId() == 1;
}

bool uploadRequestIgnoredWhileUploadIsAlreadyInFlight() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    const TerminalAction first = requestUpload(state, link, 100, 1500);
    const TerminalAction second = requestUpload(state, link, 120, 1500);

    return first.sendLine && emptyAction(second) && state.status() == Status::Uploading && link.inFlight();
}

bool secondUploadGetsNewRequestId() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    const TerminalAction first = requestUpload(state, link, 100, 1500);
    const TerminalAction accepted = handleUploadEvent(state, link, UploadEvent::Accepted);
    state.setBrightness(0, 42);

    const TerminalAction second = requestUpload(state, link, 200, 1500);

    return first.line.rfind("SETUP 1 ", 0) == 0 &&
           accepted.redraw &&
           second.sendLine &&
           second.line.rfind("SETUP 2 ", 0) == 0 &&
           link.requestId() == 2 &&
           state.status() == Status::Uploading;
}

bool simFireEmitsLineOnlyWhileIdle() {
    TerminalSetupState state;
    UsbSetupLink link(160);

    const TerminalAction idle = requestSimFire(state, link, 100, 1500);
    const TerminalAction uploadBlocked = requestUpload(state, link, 120, 1500);
    const TerminalAction simFireBlocked = requestSimFire(state, link, 130, 1500);

    return idle.sendLine &&
           idle.drainUsbInput &&
           idle.redraw &&
           idle.line == "SIM_FIRE 1" &&
           link.inFlight() &&
           emptyAction(uploadBlocked) &&
           emptyAction(simFireBlocked) &&
           state.status() == Status::SimFire;
}

bool simFireBlockedWhenSetupOnlyUploadState() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.beginUpload();

    const TerminalAction action = requestSimFire(state, link, 100, 1500);

    return emptyAction(action) && state.status() == Status::Uploading && !link.inFlight();
}

bool simFireBlockedWhenLinkOnlyUploadState() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    link.beginUpload(100, 1500);

    const TerminalAction action = requestSimFire(state, link, 120, 1500);

    return emptyAction(action) &&
           state.status() == Status::Dirty &&
           link.inFlight() &&
           state.draftLane(0).brightness == 42;
}

bool simFireBlockedWhenDraftIsDirty() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);

    const TerminalAction action = requestSimFire(state, link, 100, 1500);

    return emptyAction(action) &&
           !link.inFlight() &&
           state.status() == Status::Dirty &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 42;
}

bool uploadRequestBlockedWhenSetupOnlyUploadState() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.beginUpload();

    const TerminalAction action = requestUpload(state, link, 120, 1500);

    return emptyAction(action) && state.status() == Status::Uploading && !link.inFlight();
}

bool uploadRequestBlockedWhenLinkOnlyUploadState() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    link.beginUpload(100, 1500);

    const TerminalAction action = requestUpload(state, link, 120, 1500);

    return emptyAction(action) &&
           state.status() == Status::Dirty &&
           link.inFlight() &&
           state.draftLane(0).brightness == 42;
}

bool acceptedUploadCommitsSentSnapshot() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    const TerminalAction upload = requestUpload(state, link, 100, 1500);
    state.setBrightness(0, 7);

    const TerminalAction accepted = handleUploadEvent(state, link, UploadEvent::Accepted);

    return upload.sendLine &&
           accepted.redraw &&
           !accepted.sendLine &&
           !link.inFlight() &&
           state.status() == Status::Uploaded &&
           state.savedLane(0).brightness == 42 &&
           state.draftLane(0).brightness == 42;
}

bool rejectedUploadRevertsDraft() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    const TerminalAction upload = requestUpload(state, link, 100, 1500);

    const TerminalAction rejected = handleUploadEvent(state, link, UploadEvent::Rejected);

    return upload.sendLine &&
           rejected.redraw &&
           rejected.lockFadersToDraft &&
           !link.inFlight() &&
           state.status() == Status::Problem &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 100;
}

bool staleAcceptedFromLinkOnlyUploadClearsLinkWithoutCommit() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    link.beginUpload(100, 1500);

    const TerminalAction action = handleUploadEvent(state, link, UploadEvent::Accepted);

    return emptyAction(action) &&
           !link.inFlight() &&
           state.status() == Status::Dirty &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 42;
}

bool staleRejectedFromLinkOnlyUploadClearsLinkWithoutRollback() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);
    link.beginUpload(100, 1500);

    const TerminalAction action = handleUploadEvent(state, link, UploadEvent::Rejected);

    return emptyAction(action) &&
           !link.inFlight() &&
           state.status() == Status::Dirty &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 42;
}

bool noneUploadEventIsNoOp() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    state.setBrightness(0, 42);

    const TerminalAction action = handleUploadEvent(state, link, UploadEvent::None);

    return emptyAction(action) &&
           state.status() == Status::Dirty &&
           !link.inFlight() &&
           state.draftLane(0).brightness == 42;
}

bool simFireAcceptedClearsLinkWithoutCommittingSetup() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    const TerminalAction simFire = requestSimFire(state, link, 100, 1500);

    const TerminalAction accepted = handleUploadEvent(state, link, UploadEvent::Accepted);

    return simFire.line == "SIM_FIRE 1" &&
           emptyAction(accepted) &&
           !link.inFlight() &&
           state.status() == Status::SimFire &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 100;
}

bool simFireRejectedMarksProblemWithoutRollingBackDraft() {
    TerminalSetupState state;
    UsbSetupLink link(160);
    const TerminalAction simFire = requestSimFire(state, link, 100, 1500);

    const TerminalAction rejected = handleUploadEvent(state, link, UploadEvent::Rejected);

    return simFire.line == "SIM_FIRE 1" &&
           rejected.redraw &&
           !rejected.lockFadersToDraft &&
           !link.inFlight() &&
           state.status() == Status::Problem &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 100;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("upload request emits setup line and starts in-flight", uploadRequestEmitsSetupLineAndStartsInFlight) ? 0 : 1;
    failures += runCase("upload request ignored while upload is already in flight", uploadRequestIgnoredWhileUploadIsAlreadyInFlight) ? 0 : 1;
    failures += runCase("second upload gets new request id", secondUploadGetsNewRequestId) ? 0 : 1;
    failures += runCase("sim-fire emits line only while idle", simFireEmitsLineOnlyWhileIdle) ? 0 : 1;
    failures += runCase("sim-fire blocked when setup-only upload state", simFireBlockedWhenSetupOnlyUploadState) ? 0 : 1;
    failures += runCase("sim-fire blocked when link-only upload state", simFireBlockedWhenLinkOnlyUploadState) ? 0 : 1;
    failures += runCase("sim-fire blocked when draft is dirty", simFireBlockedWhenDraftIsDirty) ? 0 : 1;
    failures += runCase("upload request blocked when setup-only upload state", uploadRequestBlockedWhenSetupOnlyUploadState) ? 0 : 1;
    failures += runCase("upload request blocked when link-only upload state", uploadRequestBlockedWhenLinkOnlyUploadState) ? 0 : 1;
    failures += runCase("accepted upload commits sent snapshot", acceptedUploadCommitsSentSnapshot) ? 0 : 1;
    failures += runCase("rejected upload reverts draft", rejectedUploadRevertsDraft) ? 0 : 1;
    failures += runCase("stale accepted from link-only upload clears link without commit", staleAcceptedFromLinkOnlyUploadClearsLinkWithoutCommit) ? 0 : 1;
    failures += runCase("stale rejected from link-only upload clears link without rollback", staleRejectedFromLinkOnlyUploadClearsLinkWithoutRollback) ? 0 : 1;
    failures += runCase("none upload event is no-op", noneUploadEventIsNoOp) ? 0 : 1;
    failures += runCase("sim-fire accepted clears link without committing setup", simFireAcceptedClearsLinkWithoutCommittingSetup) ? 0 : 1;
    failures += runCase("sim-fire rejected marks problem without rolling back draft", simFireRejectedMarksProblemWithoutRollingBackDraft) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
