#include "../sticks3-terminal/src/terminal_physical_tick.h"

#include "../../shared/terminal/terminal_setup_link.h"

#include <iostream>
#include <string>

namespace {

using terminal_control_surface::ControlSnapshot;
using terminal_control_surface::ControlSurface;
using terminal_external_display::DisplayFrame;
using terminal_physical_tick::runPhysicalTick;
using terminal_setup::Status;
using terminal_setup::TerminalSetupState;
using terminal_setup_link::CommandKind;
using terminal_switch_dispatch::SwitchAction;
using terminal_usb_link::UsbSetupLink;

ControlSnapshot fiveLaneEditSnapshot() {
    ControlSnapshot snapshot;
    snapshot.lanes[0].sliderPercent = 12;
    snapshot.lanes[0].encoderDelta = 6;
    snapshot.lanes[0].effectPressed = true;
    snapshot.lanes[1].sliderPercent = 34;
    snapshot.lanes[1].encoderDelta = -6;
    snapshot.lanes[1].encoderPressed = true;
    snapshot.lanes[2].sliderPercent = 56;
    snapshot.lanes[2].encoderDelta = 6;
    snapshot.lanes[2].effectPressed = true;
    snapshot.lanes[3].sliderPercent = 78;
    snapshot.lanes[3].encoderDelta = -6;
    snapshot.lanes[3].encoderPressed = true;
    snapshot.lanes[3].effectPressed = true;
    snapshot.lanes[4].sliderPercent = 99;
    snapshot.lanes[4].encoderDelta = 6;
    return snapshot;
}

bool hasFragment(const std::string& haystack, const char* needle) {
    return haystack.find(needle) != std::string::npos;
}

bool hasRow(const terminal_external_display::DisplayRow& row,
            std::uint8_t laneNumber,
            const char* colorName,
            std::uint8_t brightnessPercent,
            const char* brightnessLabel,
            bool on,
            bool effect,
            const char* effectLabel) {
    return row.laneNumber == laneNumber &&
           row.colorName == colorName &&
           row.brightnessPercent == brightnessPercent &&
           row.brightnessLabel == brightnessLabel &&
           row.on == on &&
           row.effect == effect &&
           row.effectLabel == effectLabel;
}

bool sameTickPhysicalEditsAreUploadedAndShownOnOled() {
    TerminalSetupState state;
    ControlSurface controls;
    UsbSetupLink link(160);
    DisplayFrame frame;
    bool drained = false;

    const auto result = runPhysicalTick(
        fiveLaneEditSnapshot(),
        SwitchAction::Upload,
        state,
        controls,
        link,
        frame,
        100,
        1500,
        [&drained]() { drained = true; });

    const auto parsed = terminal_setup_link::parseLine(result.action.line.c_str());
    return drained &&
           result.drainedUsbBeforeUpload &&
           result.frameChanged &&
           result.action.sendLine &&
           result.action.redraw &&
           result.action.line.rfind("SETUP 1 ", 0) == 0 &&
           hasFragment(result.action.line, "L1:361,12,1,1") &&
           hasFragment(result.action.line, "L2:364,34,1,1") &&
           hasFragment(result.action.line, "L3:364,56,1,1") &&
           hasFragment(result.action.line, "L4:367,78,1,1") &&
           hasFragment(result.action.line, "L5:366,99,1,0") &&
           parsed.kind == CommandKind::Setup &&
           parsed.setup.requestId == 1 &&
           parsed.setup.lanes[0].hue == 361 &&
           parsed.setup.lanes[0].brightness == 12 &&
           parsed.setup.lanes[0].effect == true &&
           parsed.setup.lanes[1].on == true &&
           parsed.setup.lanes[1].effect == true &&
           parsed.setup.lanes[3].on == true &&
           parsed.setup.lanes[3].effect == true &&
           hasRow(result.frame.rows[0], 1, "ORANZ", 12, "12%", true, true, "ODP") &&
           hasRow(result.frame.rows[1], 2, "TYRKYS", 34, "34%", true, true, "ODP") &&
           hasRow(result.frame.rows[2], 3, "TYRKYS", 56, "56%", true, true, "ODP") &&
           hasRow(result.frame.rows[3], 4, "RUZOVA", 78, "78%", true, true, "ODP") &&
           hasRow(result.frame.rows[4], 5, "FIALOVA", 99, "99%", true, false, "---") &&
           frame == result.frame &&
           state.status() == Status::Uploading &&
           link.inFlight();
}

bool sameTickUploadBlockedWhileInFlightStillShowsFreshDraft() {
    TerminalSetupState state;
    ControlSurface controls;
    UsbSetupLink link(160);
    DisplayFrame frame;
    bool drained = false;
    state.setBrightness(0, 33);
    link.beginUpload(50, 1500);

    const auto result = runPhysicalTick(
        fiveLaneEditSnapshot(),
        SwitchAction::Upload,
        state,
        controls,
        link,
        frame,
        100,
        1500,
        [&drained]() { drained = true; });

    return !drained &&
           !result.drainedUsbBeforeUpload &&
           !result.action.sendLine &&
           result.frameChanged &&
           hasRow(result.frame.rows[0], 1, "ORANZ", 12, "12%", true, true, "ODP") &&
           state.status() == Status::Dirty &&
           link.inFlight();
}

bool sameTickSimFireIsBlockedByDirtyDraftButStillShowsFreshOledDraft() {
    TerminalSetupState state;
    ControlSurface controls;
    UsbSetupLink link(160);
    DisplayFrame frame;
    bool drained = false;

    const auto result = runPhysicalTick(
        fiveLaneEditSnapshot(),
        SwitchAction::SimFire,
        state,
        controls,
        link,
        frame,
        100,
        1500,
        [&drained]() { drained = true; });

    return !drained &&
           !result.action.drainUsbInput &&
           !result.action.sendLine &&
           result.action.line.empty() &&
           hasRow(result.frame.rows[4], 5, "FIALOVA", 99, "99%", true, false, "---") &&
           frame == result.frame &&
           state.status() == Status::Dirty &&
           !link.inFlight();
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("same-tick physical edits are uploaded and shown on OLED",
                        sameTickPhysicalEditsAreUploadedAndShownOnOled) ? 0 : 1;
    failures += runCase("same-tick upload blocked while in-flight still shows fresh draft",
                        sameTickUploadBlockedWhileInFlightStillShowsFreshDraft) ? 0 : 1;
    failures += runCase("same-tick sim-fire is blocked by dirty draft but still shows fresh OLED draft",
                        sameTickSimFireIsBlockedByDirtyDraftButStillShowsFreshOledDraft) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
