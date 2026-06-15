#include "../sticks3-terminal/src/terminal_setup.h"

#include <iostream>
#include <string>

namespace {

using terminal_setup::Status;
using terminal_setup::TerminalSetupState;

bool fiveLanesHaveDirectControls() {
    TerminalSetupState state;
    state.setBrightness(2, 73);
    state.rotateHue(2, 6);
    state.toggleOn(2);
    state.setEffectLed(2, true);
    const auto lane = state.draftLane(2);
    return lane.brightness == 74 &&
           lane.hue == 361 &&
           lane.on == false &&
           lane.effect == true;
}

bool defaultLanesUsePropRoleColors() {
    TerminalSetupState state;
    return state.draftLane(0).hue == 363 &&
           state.draftLane(1).hue == 360 &&
           state.draftLane(2).hue == 360 &&
           state.draftLane(3).hue == 365 &&
           state.draftLane(3).effect == true &&
           state.draftLane(4).hue == 360 &&
           state.draftLane(4).effect == true;
}

bool barrelLaneKeepsRedFireEffectEnabled() {
    TerminalSetupState state;
    state.rotateHue(4, 6);
    state.setEffectLed(4, false);
    const auto lane = state.draftLane(4);
    const std::string line = state.uploadLine();
    return lane.hue == 360 &&
           lane.effect == true &&
           line.find("L5:360,100,1,1") != std::string::npos;
}

bool brightnessIsQuantizedToTwoPercentSteps() {
    TerminalSetupState state;
    state.setBrightness(0, 1);
    const auto onePercent = state.draftLane(0);
    state.setBrightness(0, 73);
    const auto middle = state.draftLane(0);
    state.setBrightness(0, 99);
    const auto top = state.draftLane(0);
    return onePercent.brightness == 2 &&
           onePercent.on == true &&
           middle.brightness == 74 &&
           top.brightness == 100;
}

bool commitAcceptedSavesDraftAndShowsUploaded() {
    TerminalSetupState state;
    state.setBrightness(0, 50);
    state.beginUpload();
    state.commitAccepted();
    return state.status() == Status::Uploaded &&
           state.savedLane(0).brightness == 50 &&
           std::string(state.statusText()) == "NAHRANO";
}

bool commitRejectedRevertsDraftAndShowsProblem() {
    TerminalSetupState state;
    state.setBrightness(1, 35);
    state.beginUpload();
    state.commitRejected();
    return state.status() == Status::Problem &&
           state.draftLane(1).brightness == state.savedLane(1).brightness &&
           std::string(state.statusText()) == "PROBLEM";
}

bool rejectedUploadRollsBackAllLanesToAcceptedBaseline() {
    TerminalSetupState state;
    state.setBrightness(0, 40);
    state.rotateHue(4, 6);
    state.beginUpload();
    state.commitAccepted();

    state.setBrightness(0, 99);
    state.rotateHue(4, 12);
    state.toggleOn(2);
    state.setEffectLed(3, true);
    state.beginUpload();
    state.commitRejected();

    for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
        if (state.draftLane(lane) != state.savedLane(lane)) {
            return false;
        }
    }
    return state.draftLane(0).brightness == 40 &&
           state.draftLane(4).hue == 360 &&
           state.status() == Status::Problem &&
           state.dirty() == false;
}

bool problemStatusStaysLatchedAfterPostRejectEdit() {
    TerminalSetupState state;
    state.setBrightness(0, 40);
    state.beginUpload();
    state.commitRejected();
    state.setBrightness(0, 80);
    return state.status() == Status::Problem &&
           state.draftLane(0).brightness == 80 &&
           state.dirty();
}

bool physicalEditsDuringUploadDoNotCommitUnsentValues() {
    TerminalSetupState state;
    state.setBrightness(0, 20);
    state.beginUpload();
    state.setBrightness(0, 90);
    state.rotateHue(0, 45);
    state.toggleOn(0);
    state.commitAccepted();
    return state.savedLane(0).brightness == 20 &&
           state.savedLane(0).hue == 363 &&
           state.savedLane(0).on == true &&
           state.draftLane(0) == state.savedLane(0) &&
           state.status() == Status::Uploaded;
}

bool uploadLineRemainsSnapshotWhileUploading() {
    TerminalSetupState state;
    state.setBrightness(0, 20);
    state.rotateHue(4, 6);
    state.beginUpload();
    const std::string upload = state.uploadLine();
    state.setBrightness(0, 99);
    state.rotateHue(4, 12);
    state.toggleOn(2);
    return upload.find("L1:363,20,1,0") != std::string::npos &&
           upload.find("L5:360,100,1,1") != std::string::npos &&
           state.uploadLine() == upload &&
           state.status() == Status::Uploading;
}

bool simFireIgnoredDuringUploadKeepsSnapshot() {
    TerminalSetupState state;
    state.setBrightness(0, 44);
    state.beginUpload();
    const std::string upload = state.uploadLine();
    state.simulateFire();
    return state.status() == Status::Uploading &&
           state.uploadLine() == upload;
}

bool simulateFireDoesNotCommitSetup() {
    TerminalSetupState state;
    state.setBrightness(4, 88);
    state.simulateFire();
    return state.status() == Status::SimFire &&
           state.savedLane(4).brightness != 88;
}

bool largeDisplayTextContainsOperatorValuesOnly() {
    TerminalSetupState state;
    state.setBrightness(0, 80);
    state.rotateHue(0, 6);
    state.setEffectLed(0, true);
    const std::string line = state.largeDisplayLine(0);
    return line.find("LED 1") != std::string::npos &&
           line.find("BARVA TYRKYS") != std::string::npos &&
           line.find("JAS 80%") != std::string::npos &&
           line.find("ZAP 1") != std::string::npos &&
           line.find("ODP 1") != std::string::npos &&
           line.find("RGB") == std::string::npos &&
           line.find("#") == std::string::npos &&
           line.find("ODSTIN") == std::string::npos &&
           line.find("MENU") == std::string::npos;
}

bool oledOperatorSummaryFits128x64TextBudget() {
    TerminalSetupState state;
    state.setBrightness(0, 80);
    state.rotateHue(0, 6);
    state.setEffectLed(0, true);
    const std::string line = state.oledDisplayLine(0);
    return line.size() <= terminal_setup::OLED_LINE_MAX_CHARS &&
           line == "1 TYRKYS 80% ODP";
}

bool oledOperatorSummaryShowsColorBrightnessPowerAndEffect() {
    TerminalSetupState state;
    const std::string before = state.oledDisplayLine(0);
    state.rotateHue(0, 6);
    const std::string afterColor = state.oledDisplayLine(0);
    state.setBrightness(0, 42);
    const std::string afterBrightness = state.oledDisplayLine(0);
    state.toggleOn(0);
    const std::string afterPower = state.oledDisplayLine(0);
    state.setEffectLed(0, true);
    const std::string after = state.oledDisplayLine(0);
    return before == "1 ZELENA 100% ---" &&
           afterColor == "1 TYRKYS 100% ---" &&
           afterBrightness == "1 TYRKYS 42% ---" &&
           afterPower == "1 TYRKYS VYP ---" &&
           after == "1 TYRKYS VYP ODP" &&
           after.size() <= terminal_setup::OLED_LINE_MAX_CHARS;
}

bool uploadLineContainsAllFiveLedLanes() {
    TerminalSetupState state;
    state.setBrightness(0, 10);
    state.toggleOn(3);
    state.setEffectLed(3, true);
    state.setBrightness(4, 90);
    state.setEffectLed(4, true);
    const std::string line = state.uploadLine();
    const std::string scopedLine = state.uploadLine(42);
    return line.find("SETUP") == 0 &&
           scopedLine.find("SETUP 42 ") == 0 &&
           line.find("L1:363,10,1,0") != std::string::npos &&
           scopedLine.find("L1:363,10,1,0") != std::string::npos &&
           line.find("L2:360,100,1,0") != std::string::npos &&
           line.find("L3:360,100,1,0") != std::string::npos &&
           line.find("L4:365,100,0,1") != std::string::npos &&
           line.find("L5:360,90,1,1") != std::string::npos;
}

bool invalidLaneWritesDoNotMutateLastLane() {
    TerminalSetupState state;
    state.setBrightness(99, 0);
    state.rotateHue(99, 45);
    state.toggleOn(99);
    state.setEffectLed(99, true);
    const auto lane = state.draftLane(4);
    return lane.brightness == 100 &&
           lane.hue == 360 &&
           lane.on == true &&
           lane.effect == true &&
           state.status() == Status::Ready;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("five lanes have direct controls", fiveLanesHaveDirectControls) ? 0 : 1;
    failures += runCase("default lanes use prop role colors", defaultLanesUsePropRoleColors) ? 0 : 1;
    failures += runCase("barrel lane keeps red fire effect enabled", barrelLaneKeepsRedFireEffectEnabled) ? 0 : 1;
    failures += runCase("brightness is quantized to two percent steps", brightnessIsQuantizedToTwoPercentSteps) ? 0 : 1;
    failures += runCase("accepted upload saves draft", commitAcceptedSavesDraftAndShowsUploaded) ? 0 : 1;
    failures += runCase("rejected upload reverts draft", commitRejectedRevertsDraftAndShowsProblem) ? 0 : 1;
    failures += runCase("rejected upload rolls back all lanes to accepted baseline", rejectedUploadRollsBackAllLanesToAcceptedBaseline) ? 0 : 1;
    failures += runCase("problem status stays latched after post-reject edit", problemStatusStaysLatchedAfterPostRejectEdit) ? 0 : 1;
    failures += runCase("physical edits during upload do not commit unsent values", physicalEditsDuringUploadDoNotCommitUnsentValues) ? 0 : 1;
    failures += runCase("upload line remains snapshot while uploading", uploadLineRemainsSnapshotWhileUploading) ? 0 : 1;
    failures += runCase("SIM_FIRE ignored during upload keeps snapshot", simFireIgnoredDuringUploadKeepsSnapshot) ? 0 : 1;
    failures += runCase("simulate fire does not commit setup", simulateFireDoesNotCommitSetup) ? 0 : 1;
    failures += runCase("large display text contains operator values only", largeDisplayTextContainsOperatorValuesOnly) ? 0 : 1;
    failures += runCase("OLED operator summary fits 128x64 text budget",
                        oledOperatorSummaryFits128x64TextBudget) ? 0 : 1;
    failures += runCase("OLED operator summary shows color brightness power and effect",
                        oledOperatorSummaryShowsColorBrightnessPowerAndEffect) ? 0 : 1;
    failures += runCase("upload line contains all five LED lanes", uploadLineContainsAllFiveLedLanes) ? 0 : 1;
    failures += runCase("invalid lane writes do not mutate last lane", invalidLaneWritesDoNotMutateLastLane) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
