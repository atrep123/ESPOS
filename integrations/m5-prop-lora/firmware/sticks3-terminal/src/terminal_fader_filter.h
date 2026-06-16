#pragma once

#include <array>
#include <cstddef>

#include "terminal_control_surface.h"

namespace terminal_fader_filter {

constexpr int RAW_SAMPLE_MISSING = -1;
constexpr int RAW_MIDPOINT_AUTO = -1;
constexpr int BRIGHTNESS_STEP_PERCENT = 2;
constexpr int ENDPOINT_JUMP_CONFIRM_PERCENT = 20;
static_assert(BRIGHTNESS_STEP_PERCENT == terminal_setup::BRIGHTNESS_STEP_PERCENT,
              "fader brightness step must match setup state");

struct FaderCalibration {
    constexpr FaderCalibration(int rawMinValue = 0,
                               int rawMaxValue = 4095,
                               int deadbandPercentValue = 1,
                               int endpointSnapPercentValue = 1,
                               int rawMidValue = RAW_MIDPOINT_AUTO)
        : rawMin(rawMinValue),
          rawMax(rawMaxValue),
          deadbandPercent(deadbandPercentValue),
          endpointSnapPercent(endpointSnapPercentValue),
          rawMid(rawMidValue) {}

    int rawMin = 0;
    int rawMax = 4095;
    int deadbandPercent = 1;
    int endpointSnapPercent = 1;
    int rawMid = RAW_MIDPOINT_AUTO;
};

inline int clampInt(int value, int lower, int upper) {
    if (value < lower) return lower;
    if (value > upper) return upper;
    return value;
}

inline int absoluteDelta(int lhs, int rhs) {
    return lhs > rhs ? lhs - rhs : rhs - lhs;
}

inline bool isEndpointPercent(int percent) {
    return percent == 0 || percent == 100;
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

inline int automaticRawMidpoint(const FaderCalibration& calibration) {
    const int span = calibration.rawMax - calibration.rawMin;
    if (span > 0) {
        return calibration.rawMin + (span + 1) / 2;
    }
    const int reverseSpan = calibration.rawMin - calibration.rawMax;
    return calibration.rawMax + (reverseSpan + 1) / 2;
}

inline int calibratedRawMidpoint(const FaderCalibration& calibration) {
    if (calibration.rawMid == RAW_MIDPOINT_AUTO) {
        return automaticRawMidpoint(calibration);
    }
    const int lower = calibration.rawMin < calibration.rawMax ? calibration.rawMin : calibration.rawMax;
    const int upper = calibration.rawMin < calibration.rawMax ? calibration.rawMax : calibration.rawMin;
    return clampInt(calibration.rawMid, lower, upper);
}

inline int scaleHalfPercent(int numerator, int denominator, int offset) {
    if (denominator <= 0) {
        return offset;
    }
    return offset + (numerator * 50 + denominator / 2) / denominator;
}

inline int rawToPercent(int raw, const FaderCalibration& calibration) {
    const int span = calibration.rawMax - calibration.rawMin;
    if (span == 0) {
        return 0;
    }
    if (span > 0) {
        const int clamped = clampInt(raw, calibration.rawMin, calibration.rawMax);
        const int mid = calibratedRawMidpoint(calibration);
        const int percent = clamped <= mid
                                ? scaleHalfPercent(clamped - calibration.rawMin,
                                                   mid - calibration.rawMin,
                                                   0)
                                : scaleHalfPercent(clamped - mid,
                                                   calibration.rawMax - mid,
                                                   50);
        return quantizePercent(snapEndpointPercent(percent, calibration));
    }
    const int reverseSpan = calibration.rawMin - calibration.rawMax;
    const int clamped = clampInt(raw, calibration.rawMax, calibration.rawMin);
    (void)reverseSpan;
    const int mid = calibratedRawMidpoint(calibration);
    const int percent = clamped >= mid
                            ? scaleHalfPercent(calibration.rawMin - clamped,
                                               calibration.rawMin - mid,
                                               0)
                            : scaleHalfPercent(mid - clamped,
                                               mid - calibration.rawMax,
                                               50);
    return quantizePercent(snapEndpointPercent(percent, calibration));
}

class FaderFilter {
   public:
    using CalibrationSet = std::array<FaderCalibration, terminal_setup::LANE_COUNT>;

    explicit FaderFilter(FaderCalibration calibration = {}) {
        calibrations_.fill(calibration);
        reset();
    }

    explicit FaderFilter(const CalibrationSet& calibrations) : calibrations_(calibrations) {
        reset();
    }

    void reset() {
        lastPercent_.fill(terminal_control_surface::SLIDER_UNCHANGED);
        pickupPercent_.fill(terminal_control_surface::SLIDER_UNCHANGED);
        pendingEndpointPercent_.fill(terminal_control_surface::SLIDER_UNCHANGED);
    }

    void prime(std::size_t lane, int raw) {
        if (lane >= terminal_setup::LANE_COUNT || raw == RAW_SAMPLE_MISSING) {
            return;
        }
        lastPercent_[lane] = rawToPercent(raw, calibrationFor(lane));
        pickupPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
        pendingEndpointPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
    }

    void lockUntilPickup(std::size_t lane, int percent) {
        if (lane >= terminal_setup::LANE_COUNT) {
            return;
        }
        pickupPercent_[lane] = clampInt(percent, 0, 100);
        lastPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
        pendingEndpointPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
    }

    int update(std::size_t lane, int raw) {
        if (lane >= terminal_setup::LANE_COUNT || raw == RAW_SAMPLE_MISSING) {
            return terminal_control_surface::SLIDER_UNCHANGED;
        }
        const FaderCalibration& calibration = calibrationFor(lane);
        const int next = rawToPercent(raw, calibration);
        const int pickup = pickupPercent_[lane];
        if (pickup != terminal_control_surface::SLIDER_UNCHANGED) {
            if (absoluteDelta(next, pickup) <= calibration.deadbandPercent) {
                pickupPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
                lastPercent_[lane] = next;
            }
            return terminal_control_surface::SLIDER_UNCHANGED;
        }
        const int previous = lastPercent_[lane];
        if (previous != terminal_control_surface::SLIDER_UNCHANGED) {
            if (isUnconfirmedEndpointJump(lane, previous, next)) {
                return terminal_control_surface::SLIDER_UNCHANGED;
            }
            if (next == previous || absoluteDelta(next, previous) < calibration.deadbandPercent) {
                return terminal_control_surface::SLIDER_UNCHANGED;
            }
        }
        pendingEndpointPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
        lastPercent_[lane] = next;
        return next;
    }

   private:
    const FaderCalibration& calibrationFor(std::size_t lane) const {
        return calibrations_[lane];
    }

    bool isUnconfirmedEndpointJump(std::size_t lane, int previous, int next) {
        if (!isEndpointPercent(next) ||
            isEndpointPercent(previous) ||
            absoluteDelta(next, previous) < ENDPOINT_JUMP_CONFIRM_PERCENT) {
            pendingEndpointPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
            return false;
        }
        if (pendingEndpointPercent_[lane] == next) {
            pendingEndpointPercent_[lane] = terminal_control_surface::SLIDER_UNCHANGED;
            return false;
        }
        pendingEndpointPercent_[lane] = next;
        return true;
    }

    CalibrationSet calibrations_ = {};
    std::array<int, terminal_setup::LANE_COUNT> lastPercent_ = {};
    std::array<int, terminal_setup::LANE_COUNT> pickupPercent_ = {};
    std::array<int, terminal_setup::LANE_COUNT> pendingEndpointPercent_ = {};
};

}  // namespace terminal_fader_filter
