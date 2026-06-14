#pragma once

#include <array>
#include <cstddef>

#include "terminal_control_surface.h"

namespace terminal_encoder_filter {

constexpr int ENCODER_POSITION_MISSING = -2147483647;

struct EncoderCalibration {
    constexpr explicit EncoderCalibration(int degreesPerDetentValue = 6)
        : degreesPerDetent(degreesPerDetentValue) {}

    int degreesPerDetent = 6;
};

struct EncoderSample {
    constexpr EncoderSample(int positionValue = ENCODER_POSITION_MISSING,
                            bool encoderPressedValue = false,
                            bool effectPressedValue = false,
                            int incrementValue = 0,
                            bool hasIncrementValue = false)
        : position(positionValue),
          encoderPressed(encoderPressedValue),
          effectPressed(effectPressedValue),
          increment(incrementValue),
          hasIncrement(hasIncrementValue) {}

    int position = ENCODER_POSITION_MISSING;
    bool encoderPressed = false;
    bool effectPressed = false;
    int increment = 0;
    bool hasIncrement = false;
};

class EncoderFilter {
   public:
    explicit EncoderFilter(EncoderCalibration calibration = EncoderCalibration()) : calibration_(calibration) {
        reset();
    }

    void reset() {
        lastPosition_.fill(ENCODER_POSITION_MISSING);
    }

    void prime(std::size_t lane, const EncoderSample& sample) {
        if (lane >= terminal_setup::LANE_COUNT || sample.position == ENCODER_POSITION_MISSING) {
            return;
        }
        lastPosition_[lane] = sample.position;
    }

    terminal_control_surface::LaneInput update(std::size_t lane, const EncoderSample& sample) {
        terminal_control_surface::LaneInput input;
        if (lane >= terminal_setup::LANE_COUNT) {
            return input;
        }
        input.encoderPressed = sample.encoderPressed;
        input.effectPressed = sample.effectPressed;
        if (sample.hasIncrement) {
            input.encoderDelta = sample.increment * calibration_.degreesPerDetent;
            return input;
        }
        if (sample.position == ENCODER_POSITION_MISSING) {
            return input;
        }
        const int previous = lastPosition_[lane];
        lastPosition_[lane] = sample.position;
        if (previous == ENCODER_POSITION_MISSING) {
            return input;
        }
        input.encoderDelta = (sample.position - previous) * calibration_.degreesPerDetent;
        return input;
    }

   private:
    EncoderCalibration calibration_;
    std::array<int, terminal_setup::LANE_COUNT> lastPosition_ = {};
};

}  // namespace terminal_encoder_filter
