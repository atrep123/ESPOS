#pragma once

#include <array>
#include <cstddef>

#include "terminal_control_surface.h"

namespace terminal_fader_filter {

constexpr int RAW_SAMPLE_MISSING = -1;
constexpr int BRIGHTNESS_STEP_PERCENT = 2;
static_assert(BRIGHTNESS_STEP_PERCENT == terminal_setup::BRIGHTNESS_STEP_PERCENT,
              "fader brightness step must match setup state");

struct FaderCalibration {
    constexpr FaderCalibration(int rawMinValue = 0,
                               int rawMaxValue = 4095,
                               int deadbandPercentValue = 1,
                               int endpointSnapPercentValue = 1)
        : rawMin(rawMinValue),
          rawMax(rawMaxValue),
          deadbandPercent(deadbandPercentValue),
          endpointSnapPercent(endpointSnapPercentValue) {}

    int rawMin = 0;
    int rawMax = 4095;
    int deadbandPercent = 1;
    int endpointSnapPercent = 1;
};

inline int clampInt(int value, int lower, int upper) {
    if (value < lower) return lower;
    if (value > upper) return upper;
    return value;
}

inline int absoluteDelta(int lhs, int rhs) {
    return lhs > rhs ? lhs - rhs : rhs - lhs;
}

inline int snapEndpointPercent(int percent, const FaderCalibration& calibration) {
    const int snap = clampInt(calibration.endpointSnapPercent, 0, 50);
    if (percent <= snap) {
        return 0;
    }
    if (percent >= 100 - snap) {
        return 100;
    }
    return percent;
}

inline int quantizePercent(int percent) {
    return terminal_setup::quantizePercent(percent);
}

inline int rawToPercent(int raw, const FaderCalibration& calibration) {
    const int span = calibration.rawMax - calibration.rawMin;
    if (span == 0) {
        return 0;
    }
    if (span > 0) {
        const int clamped = clampInt(raw, calibration.rawMin, calibration.rawMax);
        return quantizePercent(
            snapEndpointPercent(((clamped - calibration.rawMin) * 100 + span / 2) / span,
                                calibration));
    }
    const int reverseSpan = calibration.rawMin - calibration.rawMax;
    const int clamped = clampInt(raw, calibration.rawMax, calibration.rawMin);
    return quantizePercent(
        snapEndpointPercent(((calibration.rawMin - clamped) * 100 + reverseSpan / 2) / reverseSpan,
                            calibration));
}

class FaderFilter {
   public:
    explicit FaderFilter(FaderCalibration calibration = {}) : calibration_(calibration) {
        reset();
    }

    void reset() {
        lastPercent_.fill(terminal_control_surface::SLIDER_UNCHANGED);
        pickupPercent_.fill(terminal_control_surface::SLIDER_UNCHANGED);
    }

    void prime(std::size_t lane, int raw) {
        if (lane >= terminal_setup::LANE_COUNT || raw == RAW_SAMPLE_MISSING) {
            return;
        }
        lastPercent_[lane] = rawToPercent(raw, calibration_);
        pickupPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
    }

    void lockUntilPickup(std::size_t lane, int percent) {
        if (lane >= terminal_setup::LANE_COUNT) {
            return;
        }
        pickupPercent_[lane] = clampInt(percent, 0, 100);
        lastPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
    }

    int update(std::size_t lane, int raw) {
        if (lane >= terminal_setup::LANE_COUNT || raw == RAW_SAMPLE_MISSING) {
            return terminal_control_surface::SLIDER_UNCHANGED;
        }
        const int next = rawToPercent(raw, calibration_);
        const int pickup = pickupPercent_[lane];
        if (pickup != terminal_control_surface::SLIDER_UNCHANGED) {
            if (absoluteDelta(next, pickup) <= calibration_.deadbandPercent) {
                pickupPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
                lastPercent_[lane] = next;
            }
            return terminal_control_surface::SLIDER_UNCHANGED;
        }
        const int previous = lastPercent_[lane];
        if (previous != terminal_control_surface::SLIDER_UNCHANGED) {
            if (next == previous || absoluteDelta(next, previous) < calibration_.deadbandPercent) {
                return terminal_control_surface::SLIDER_UNCHANGED;
            }
        }
        lastPercent_[lane] = next;
        return next;
    }

   private:
    FaderCalibration calibration_;
    std::array<int, terminal_setup::LANE_COUNT> lastPercent_ = {};
    std::array<int, terminal_setup::LANE_COUNT> pickupPercent_ = {};
};

}  // namespace terminal_fader_filter
