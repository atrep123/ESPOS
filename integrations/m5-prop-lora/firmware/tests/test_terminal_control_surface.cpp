#include "../sticks3-terminal/src/terminal_control_surface.h"

#include <iostream>

namespace {

using terminal_control_surface::ControlSnapshot;
using terminal_control_surface::ControlSurface;
using terminal_setup::Status;
using terminal_setup::TerminalSetupState;

bool emptySnapshotDoesNotDirtySetup() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    surface.apply(snapshot, state);
    return state.status() == Status::Ready && !state.dirty();
}

bool slidersSetBrightnessAndPowerFromZeroToHundredForFiveLanes() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].sliderPercent = 0;
    snapshot.lanes[1].sliderPercent = 25;
    snapshot.lanes[2].sliderPercent = 50;
    snapshot.lanes[3].sliderPercent = 75;
    snapshot.lanes[4].sliderPercent = 150;
    surface.apply(snapshot, state);
    return state.draftLane(0).brightness == 0 &&
           state.draftLane(0).on == false &&
           state.draftLane(1).brightness == 26 &&
           state.draftLane(1).on == true &&
           state.draftLane(2).brightness == 50 &&
           state.draftLane(2).on == true &&
           state.draftLane(3).brightness == 76 &&
           state.draftLane(3).on == true &&
           state.draftLane(4).brightness == 100 &&
           state.draftLane(4).on == true;
}

bool encodersStepNamedPaletteWithWraparound() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].encoderDelta = -6;
    snapshot.lanes[1].encoderDelta = -6;
    surface.apply(snapshot, state);
    return state.draftLane(0).hue == 362 &&
           state.draftLane(1).hue == 368 &&
           state.status() == Status::Dirty &&
           state.dirty();
}

bool encoderPressTogglesEffectWithoutChangingPower() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[2].encoderPressed = true;
    surface.apply(snapshot, state);
    const bool firstEffect = state.draftLane(2).effect;
    const bool firstOn = state.draftLane(2).on;
    surface.apply(snapshot, state);
    const bool heldEffect = state.draftLane(2).effect;
    snapshot.lanes[2].encoderPressed = false;
    surface.apply(snapshot, state);
    snapshot.lanes[2].encoderPressed = true;
    surface.apply(snapshot, state);
    const bool secondEffect = state.draftLane(2).effect;
    const bool secondOn = state.draftLane(2).on;
    return firstEffect == true &&
           firstOn == true &&
           heldEffect == true &&
           secondEffect == false &&
           secondOn == true;
}

bool effectSelectRisingEdgeTogglesParticipationOnly() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[3].effectPressed = true;
    surface.apply(snapshot, state);
    const bool firstEffect = state.draftLane(3).effect;
    const bool firstOn = state.draftLane(3).on;
    surface.apply(snapshot, state);
    const bool heldEffect = state.draftLane(3).effect;
    snapshot.lanes[3].effectPressed = false;
    surface.apply(snapshot, state);
    snapshot.lanes[3].effectPressed = true;
    surface.apply(snapshot, state);
    const bool secondEffect = state.draftLane(3).effect;
    return firstEffect == false && firstOn == true && heldEffect == false && secondEffect == true;
}

bool barrelLaneEffectCannotBeDisabledByButtonOrEvent() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[4].encoderPressed = true;
    snapshot.lanes[4].effectPressed = true;
    snapshot.lanes[4].effectToggleEvent = true;
    surface.apply(snapshot, state);
    return state.draftLane(4).effect == true &&
           state.draftLane(4).hue == 360 &&
           state.status() == Status::Ready &&
           !state.dirty();
}

bool simultaneousEncoderAndEffectEdgesToggleEffectOnlyOnce() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[4].encoderPressed = true;
    snapshot.lanes[4].effectPressed = true;
    surface.apply(snapshot, state);
    return state.draftLane(4).effect == true &&
           state.draftLane(4).on == true;
}

bool effectSelectEdgesAreIndependentPerLane() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].effectPressed = true;
    surface.apply(snapshot, state);
    snapshot.lanes[1].effectPressed = true;
    surface.apply(snapshot, state);
    const bool lane0Held = state.draftLane(0).effect;
    const bool lane1First = state.draftLane(1).effect;
    snapshot.lanes[0].effectPressed = false;
    snapshot.lanes[1].effectPressed = false;
    surface.apply(snapshot, state);
    snapshot.lanes[0].effectPressed = true;
    surface.apply(snapshot, state);
    return lane0Held == true && lane1First == true && state.draftLane(0).effect == false &&
           state.draftLane(1).effect == true;
}

bool effectToggleEventsAreNotSuppressedByHeldLevelState() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].effectToggleEvent = true;
    surface.apply(snapshot, state);
    const bool firstEffect = state.draftLane(0).effect;
    surface.apply(snapshot, state);
    const bool secondEffect = state.draftLane(0).effect;
    return firstEffect == true && secondEffect == false;
}

bool primedHeldEncoderPressDoesNotToggleUntilReleaseAndRepress() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].encoderPressed = true;
    snapshot.lanes[1].effectPressed = true;
    surface.primeEdges(snapshot);
    surface.apply(snapshot, state);
    const bool heldIgnored = state.draftLane(0).effect == false &&
                             state.draftLane(0).on == true &&
                             state.draftLane(1).effect == false;
    snapshot.lanes[0].encoderPressed = false;
    snapshot.lanes[1].effectPressed = false;
    surface.apply(snapshot, state);
    snapshot.lanes[0].encoderPressed = true;
    snapshot.lanes[1].effectPressed = true;
    surface.apply(snapshot, state);
    return heldIgnored &&
           state.draftLane(0).effect == true &&
           state.draftLane(0).on == true &&
           state.draftLane(1).effect == true;
}

bool missingSliderSamplesDoNotOverwriteDraft() {
    TerminalSetupState state;
    ControlSurface surface;
    ControlSnapshot snapshot;
    snapshot.lanes[0].sliderPercent = 34;
    surface.apply(snapshot, state);
    ControlSnapshot empty;
    surface.apply(empty, state);
    return state.draftLane(0).brightness == 34;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("empty snapshot does not dirty setup", emptySnapshotDoesNotDirtySetup) ? 0 : 1;
    failures += runCase("sliders set brightness and power from zero to hundred for five lanes",
                        slidersSetBrightnessAndPowerFromZeroToHundredForFiveLanes) ? 0 : 1;
    failures += runCase("encoders step named palette with wraparound",
                        encodersStepNamedPaletteWithWraparound) ? 0 : 1;
    failures += runCase("encoder press toggles effect without changing power",
                        encoderPressTogglesEffectWithoutChangingPower) ? 0 : 1;
    failures += runCase("effect select rising edge toggles participation only", effectSelectRisingEdgeTogglesParticipationOnly) ? 0 : 1;
    failures += runCase("barrel lane effect cannot be disabled by button or event",
                        barrelLaneEffectCannotBeDisabledByButtonOrEvent) ? 0 : 1;
    failures += runCase("effect select edges are independent per lane", effectSelectEdgesAreIndependentPerLane) ? 0 : 1;
    failures += runCase("effect toggle events are not suppressed by held level state",
                        effectToggleEventsAreNotSuppressedByHeldLevelState) ? 0 : 1;
    failures += runCase("simultaneous encoder and effect edges toggle effect only once",
                        simultaneousEncoderAndEffectEdgesToggleEffectOnlyOnce) ? 0 : 1;
    failures += runCase("primed held encoder press does not toggle until release and repress", primedHeldEncoderPressDoesNotToggleUntilReleaseAndRepress) ? 0 : 1;
    failures += runCase("missing slider samples do not overwrite draft", missingSliderSamplesDoNotOverwriteDraft) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
