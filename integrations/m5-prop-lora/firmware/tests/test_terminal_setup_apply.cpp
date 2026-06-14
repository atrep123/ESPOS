#include "../../shared/terminal/terminal_setup_apply.h"
#include "../../shared/terminal/terminal_color_definitions.h"
#include "../../shared/terminal/terminal_setup_link.h"

#include <iostream>
#include <string>

namespace {

using terminal_setup_apply::AppliedSetup;
using terminal_setup_apply::Rgb;
using terminal_setup_apply::applySetupCommand;
using terminal_setup_apply::hueToRgb;
using terminal_setup_apply::percentToByte;
using terminal_setup_link::parseLine;

bool mapsPercentBrightnessToByteRange() {
    return percentToByte(0) == 0 &&
           percentToByte(50) == 128 &&
           percentToByte(100) == 255;
}

bool mapsHueToPrimaryRgbColors() {
    return hueToRgb(0) == Rgb{255, 0, 0} &&
           hueToRgb(120) == Rgb{0, 255, 0} &&
           hueToRgb(240) == Rgb{0, 0, 255};
}

bool namedPaletteCoversTypicalColorsIncludingWhite() {
    using terminal_color_definitions::colorFromWireCode;
    return std::string(colorFromWireCode(360).name) == "CERVENA" &&
           std::string(colorFromWireCode(361).name) == "ORANZ" &&
           std::string(colorFromWireCode(362).name) == "ZLUTA" &&
           std::string(colorFromWireCode(364).name) == "TYRKYS" &&
           std::string(colorFromWireCode(368).name) == "BILA" &&
           std::string(colorFromWireCode(359).name) == "CERVENA";
}

bool appliesParsedSetupToFiveLaneModel() {
    const auto parsed = parseLine(
        "SETUP L1:360,100,1,1 L2:361,50,0,0 L3:364,25,1,1 L4:368,0,1,0 L5:367,80,0,1");
    if (!parsed.ok()) {
        return false;
    }
    const AppliedSetup applied = applySetupCommand(parsed.setup);
    return applied.lanes[0].color == Rgb{255, 0, 0} &&
           applied.lanes[0].brightness == 255 &&
           applied.lanes[1].color == Rgb{255, 128, 0} &&
           applied.lanes[1].brightness == 128 &&
           applied.lanes[1].on == false &&
           applied.lanes[2].color == Rgb{0, 255, 255} &&
           applied.lanes[3].color == Rgb{255, 255, 255} &&
           applied.lanes[4].color == Rgb{255, 0, 128} &&
           applied.lanes[3].brightness == 0 &&
           applied.effectMask == 0b00010101;
}

bool fireChangeMaskIncludesOffLanesSelectedForStateInversion() {
    const auto parsed = parseLine(
        "SETUP L1:0,100,1,1 L2:120,50,0,1 L3:240,25,1,0 L4:60,80,1,1 L5:300,80,0,1");
    if (!parsed.ok()) {
        return false;
    }
    const AppliedSetup applied = applySetupCommand(parsed.setup);
    return applied.onMask == 0b00001101 &&
           applied.effectMask == 0b00011011 &&
           applied.effectPreviewMask == 0b00011011;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("maps percent brightness to byte range", mapsPercentBrightnessToByteRange) ? 0 : 1;
    failures += runCase("maps hue to primary RGB colors", mapsHueToPrimaryRgbColors) ? 0 : 1;
    failures += runCase("named palette covers typical colors including white",
                        namedPaletteCoversTypicalColorsIncludingWhite) ? 0 : 1;
    failures += runCase("applies parsed setup to five-lane model", appliesParsedSetupToFiveLaneModel) ? 0 : 1;
    failures += runCase("fire change mask includes off lanes selected for state inversion",
                        fireChangeMaskIncludesOffLanesSelectedForStateInversion) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
