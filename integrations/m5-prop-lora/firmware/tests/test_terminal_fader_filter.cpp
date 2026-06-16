#include "../sticks3-terminal/src/terminal_fader_filter.h"

#include <array>
#include <iostream>

namespace {

using terminal_control_surface::SLIDER_UNCHANGED;
using terminal_fader_filter::FaderCalibration;
using terminal_fader_filter::FaderFilter;
using terminal_fader_filter::RAW_SAMPLE_MISSING;
using terminal_fader_filter::rawToPercent;

bool rawToPercentClampsAndRounds() {
    const FaderCalibration calibration{0, 4095, 1};
    return rawToPercent(-25, calibration) == 0 &&
           rawToPercent(0, calibration) == 0 &&
           rawToPercent(2048, calibration) == 50 &&
           rawToPercent(4095, calibration) == 100 &&
           rawToPercent(5000, calibration) == 100;
}

bool invertedRawToPercentMapsHighRawToLowBrightness() {
    const FaderCalibration calibration{4095, 0, 1};
    return rawToPercent(5000, calibration) == 0 &&
           rawToPercent(4095, calibration) == 0 &&
           rawToPercent(2048, calibration) == 50 &&
           rawToPercent(0, calibration) == 100 &&
           rawToPercent(-25, calibration) == 100;
}

bool calibratedInvertedMidpointNotchPreservesTwoPercentSteps() {
    const FaderCalibration calibration{4095, 0, 1};
    return rawToPercent(2048, calibration) == 50 &&
           rawToPercent(2047, calibration) == 50 &&
           rawToPercent(1966, calibration) == 52 &&
           rawToPercent(2129, calibration) == 48;
}

bool customRawMidpointMapsMeasuredLaneFourDetentToFiftyPercent() {
    const FaderCalibration lane4Calibration{4095, 0, 1, 1, 2255};
    return rawToPercent(2255, lane4Calibration) == 50 &&
           rawToPercent(4095, lane4Calibration) == 0 &&
           rawToPercent(0, lane4Calibration) == 100;
}

bool endpointSnapSuppressesOnePercentAtPhysicalStops() {
    const FaderCalibration normal{0, 4095, 1};
    const FaderCalibration inverted{4095, 0, 1};
    return rawToPercent(41, normal) == 0 &&
           rawToPercent(4054, normal) == 100 &&
           rawToPercent(4054, inverted) == 0 &&
           rawToPercent(41, inverted) == 100;
}

bool brightnessQuantizesToTwoPercentSteps() {
    const FaderCalibration normal{0, 1000, 1};
    const FaderCalibration inverted{1000, 0, 1};
    return rawToPercent(20, normal) == 2 &&
           rawToPercent(230, normal) == 24 &&
           rawToPercent(990, normal) == 100 &&
           rawToPercent(770, inverted) == 24 &&
           rawToPercent(10, inverted) == 100;
}

bool firstValidSampleAlwaysPublishes() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    return filter.update(0, 0) == 0 &&
           filter.update(1, 1000) == 100;
}

bool missingSampleDoesNotOverwriteLastValue() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    if (filter.update(0, 400) != 40) {
        return false;
    }
    if (filter.update(0, RAW_SAMPLE_MISSING) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 404) == SLIDER_UNCHANGED;
}

bool invertedEndpointSpikeDoesNotPublishFalseHundredPercent() {
    FaderFilter filter(FaderCalibration{4095, 0, 1});
    if (filter.update(0, 2048) != 50) {
        return false;
    }
    if (filter.update(0, 0) != SLIDER_UNCHANGED) {
        return false;
    }
    if (filter.update(0, 2048) != SLIDER_UNCHANGED) {
        return false;
    }
    if (filter.update(0, 0) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 0) == 100;
}

bool deadbandSuppressesSmallPercentJitter() {
    FaderFilter filter(FaderCalibration{0, 1000, 3});
    if (filter.update(0, 500) != 50) {
        return false;
    }
    if (filter.update(0, 520) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 530) == 54;
}

bool lanesFilterIndependently() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    if (filter.update(0, 100) != 10 || filter.update(1, 900) != 90) {
        return false;
    }
    if (filter.update(0, 104) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(1, 870) == 88;
}

bool laneSpecificMidpointTrimOnlyChangesMeasuredLane() {
    const std::array<FaderCalibration, terminal_setup::LANE_COUNT> calibrations = {
        FaderCalibration{4095, 0, 1},
        FaderCalibration{4095, 0, 1},
        FaderCalibration{4095, 0, 1},
        FaderCalibration{4095, 0, 1, 1, 2255},
        FaderCalibration{4095, 0, 1}};
    FaderFilter filter(calibrations);
    return filter.update(0, 2255) == 46 &&
           filter.update(3, 2255) == 50 &&
           filter.update(4, 2255) == 46;
}

bool resetMakesNextSamplePublishAgain() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    if (filter.update(0, 500) != 50) {
        return false;
    }
    filter.reset();
    return filter.update(0, 500) == 50;
}

bool primeRecordsPositionWithoutPublishing() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    filter.prime(0, 500);
    if (filter.update(0, 500) != SLIDER_UNCHANGED) {
        return false;
    }
    if (filter.update(0, 504) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 530) == 54;
}

bool lockUntilPickupSuppressesRollbackMismatch() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    if (filter.update(0, 900) != 90) {
        return false;
    }
    filter.lockUntilPickup(0, 20);
    if (filter.update(0, 900) != SLIDER_UNCHANGED) {
        return false;
    }
    if (filter.update(0, 250) != SLIDER_UNCHANGED) {
        return false;
    }
    if (filter.update(0, 200) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 230) == 24;
}

bool zeroDeadbandFollowsChangedPercentOnly() {
    FaderFilter filter(FaderCalibration{0, 1000, 0});
    if (filter.update(0, 100) != 10) {
        return false;
    }
    if (filter.update(0, 100) != SLIDER_UNCHANGED) {
        return false;
    }
    return filter.update(0, 110) == 12;
}

bool invalidLaneIsNoOp() {
    FaderFilter filter(FaderCalibration{0, 1000, 2});
    return filter.update(terminal_setup::LANE_COUNT, 500) == SLIDER_UNCHANGED;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("raw to percent clamps and rounds", rawToPercentClampsAndRounds) ? 0 : 1;
    failures += runCase("inverted raw maps high raw to low brightness", invertedRawToPercentMapsHighRawToLowBrightness) ? 0 : 1;
    failures += runCase("calibrated inverted midpoint notch preserves two-percent steps",
                        calibratedInvertedMidpointNotchPreservesTwoPercentSteps) ? 0 : 1;
    failures += runCase("custom raw midpoint maps measured lane four detent to fifty percent",
                        customRawMidpointMapsMeasuredLaneFourDetentToFiftyPercent) ? 0 : 1;
    failures += runCase("endpoint snap suppresses one percent at physical stops",
                        endpointSnapSuppressesOnePercentAtPhysicalStops) ? 0 : 1;
    failures += runCase("brightness quantizes to two percent steps",
                        brightnessQuantizesToTwoPercentSteps) ? 0 : 1;
    failures += runCase("first valid sample always publishes", firstValidSampleAlwaysPublishes) ? 0 : 1;
    failures += runCase("missing sample does not overwrite last value", missingSampleDoesNotOverwriteLastValue) ? 0 : 1;
    failures += runCase("inverted endpoint spike does not publish false hundred percent",
                        invertedEndpointSpikeDoesNotPublishFalseHundredPercent) ? 0 : 1;
    failures += runCase("deadband suppresses small percent jitter", deadbandSuppressesSmallPercentJitter) ? 0 : 1;
    failures += runCase("lanes filter independently", lanesFilterIndependently) ? 0 : 1;
    failures += runCase("lane-specific midpoint trim only changes measured lane",
                        laneSpecificMidpointTrimOnlyChangesMeasuredLane) ? 0 : 1;
    failures += runCase("reset makes next sample publish again", resetMakesNextSamplePublishAgain) ? 0 : 1;
    failures += runCase("prime records position without publishing", primeRecordsPositionWithoutPublishing) ? 0 : 1;
    failures += runCase("lock until pickup suppresses rollback mismatch", lockUntilPickupSuppressesRollbackMismatch) ? 0 : 1;
    failures += runCase("zero deadband follows changed percent only", zeroDeadbandFollowsChangedPercentOnly) ? 0 : 1;
    failures += runCase("invalid lane is no-op", invalidLaneIsNoOp) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
