#include "../sticks3-terminal/src/terminal_encoder_filter.h"

#include <iostream>

namespace {

using terminal_encoder_filter::ENCODER_POSITION_MISSING;
using terminal_encoder_filter::EncoderCalibration;
using terminal_encoder_filter::EncoderFilter;
using terminal_encoder_filter::EncoderSample;

bool firstAbsolutePositionPrimesWithoutDelta() {
    EncoderFilter filter(EncoderCalibration{6});
    const auto first = filter.update(0, EncoderSample{10, false, false});
    const auto second = filter.update(0, EncoderSample{11, false, false});
    return first.encoderDelta == 0 && second.encoderDelta == 6;
}

bool detentScaleConvertsSignedMovementToDegrees() {
    EncoderFilter filter(EncoderCalibration{15});
    filter.prime(0, EncoderSample{20, false, false});
    const auto forward = filter.update(0, EncoderSample{22, false, false});
    const auto backward = filter.update(0, EncoderSample{19, false, false});
    return forward.encoderDelta == 30 && backward.encoderDelta == -45;
}

bool missingPositionDoesNotCreateDeltaButPassesButtons() {
    EncoderFilter filter(EncoderCalibration{10});
    filter.prime(0, EncoderSample{5, false, false});
    const auto sample = filter.update(0, EncoderSample{ENCODER_POSITION_MISSING, true, true});
    return sample.encoderDelta == 0 && sample.encoderPressed == true && sample.effectPressed == true;
}

bool lanesTrackPositionsIndependently() {
    EncoderFilter filter(EncoderCalibration{5});
    filter.prime(0, EncoderSample{10, false, false});
    filter.prime(1, EncoderSample{100, false, false});
    const auto lane0 = filter.update(0, EncoderSample{12, false, false});
    const auto lane1 = filter.update(1, EncoderSample{99, false, false});
    return lane0.encoderDelta == 10 && lane1.encoderDelta == -5;
}

bool resetMakesNextPositionPrimeAgain() {
    EncoderFilter filter(EncoderCalibration{6});
    filter.prime(0, EncoderSample{3, false, false});
    filter.reset();
    const auto first = filter.update(0, EncoderSample{7, false, false});
    return first.encoderDelta == 0;
}

bool invalidLaneReturnsNoopInput() {
    EncoderFilter filter(EncoderCalibration{6});
    const auto input = filter.update(terminal_setup::LANE_COUNT, EncoderSample{8, true, true});
    return input.encoderDelta == 0 && input.encoderPressed == false && input.effectPressed == false;
}

bool primeWithMissingPositionDoesNotBlockFirstValidDelta() {
    EncoderFilter filter(EncoderCalibration{6});
    filter.prime(0, EncoderSample{ENCODER_POSITION_MISSING, false, false});
    const auto first = filter.update(0, EncoderSample{5, false, false});
    const auto second = filter.update(0, EncoderSample{6, false, false});
    return first.encoderDelta == 0 && second.encoderDelta == 6;
}

bool buttonLevelsPassThroughWithoutMovement() {
    EncoderFilter filter(EncoderCalibration{6});
    filter.prime(2, EncoderSample{44, false, false});
    const auto input = filter.update(2, EncoderSample{44, true, false});
    return input.encoderDelta == 0 && input.encoderPressed == true && input.effectPressed == false;
}

bool incrementalSamplesPublishDeltaWithoutAbsolutePrime() {
    EncoderFilter filter(EncoderCalibration{6});
    const auto forward = filter.update(0, EncoderSample{ENCODER_POSITION_MISSING, false, false, 1, true});
    const auto backward = filter.update(0, EncoderSample{ENCODER_POSITION_MISSING, true, true, -2, true});
    return forward.encoderDelta == 6 &&
           !forward.encoderPressed &&
           !forward.effectPressed &&
           backward.encoderDelta == -12 &&
           backward.encoderPressed &&
           backward.effectPressed;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("first absolute position primes without delta", firstAbsolutePositionPrimesWithoutDelta) ? 0 : 1;
    failures += runCase("detent scale converts signed movement to degrees", detentScaleConvertsSignedMovementToDegrees) ? 0 : 1;
    failures += runCase("missing position does not create delta but passes buttons", missingPositionDoesNotCreateDeltaButPassesButtons) ? 0 : 1;
    failures += runCase("lanes track positions independently", lanesTrackPositionsIndependently) ? 0 : 1;
    failures += runCase("reset makes next position prime again", resetMakesNextPositionPrimeAgain) ? 0 : 1;
    failures += runCase("invalid lane returns noop input", invalidLaneReturnsNoopInput) ? 0 : 1;
    failures += runCase("prime with missing position does not block first valid delta", primeWithMissingPositionDoesNotBlockFirstValidDelta) ? 0 : 1;
    failures += runCase("button levels pass through without movement", buttonLevelsPassThroughWithoutMovement) ? 0 : 1;
    failures += runCase("incremental samples publish delta without absolute prime", incrementalSamplesPublishDeltaWithoutAbsolutePrime) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
