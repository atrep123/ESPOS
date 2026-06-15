#pragma once

#include <array>
#include <cstddef>

#include "terminal_setup.h"

namespace terminal_control_surface {

constexpr int SLIDER_UNCHANGED = -1;

struct LaneInput {
    int sliderPercent = SLIDER_UNCHANGED;
    int encoderDelta = 0;
    bool encoderPressed = false;
    bool effectPressed = false;
    bool effectToggleEvent = false;
};

struct ControlSnapshot {
    std::array<LaneInput, terminal_setup::LANE_COUNT> lanes = {};
};

class ControlSurface {
   public:
    void resetEdges() {
        previousPressed_.fill(false);
        previousEffectPressed_.fill(false);
    }

    void primeEdges(const ControlSnapshot& snapshot) {
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            previousPressed_[lane] = snapshot.lanes[lane].encoderPressed;
            previousEffectPressed_[lane] = snapshot.lanes[lane].effectPressed;
        }
    }

    void apply(const ControlSnapshot& snapshot, terminal_setup::TerminalSetupState& setup) {
        for (std::size_t lane = 0; lane < terminal_setup::LANE_COUNT; ++lane) {
            const LaneInput& input = snapshot.lanes[lane];
            if (input.sliderPercent != SLIDER_UNCHANGED) {
                setup.setBrightness(lane, input.sliderPercent);
            }
            if (input.encoderDelta != 0) {
                setup.rotateHue(lane, input.encoderDelta);
            }
            const bool encoderButtonEdge = input.encoderPressed && !previousPressed_[lane];
            const bool effectButtonEdge = input.effectPressed && !previousEffectPressed_[lane];
            if (encoderButtonEdge || effectButtonEdge || input.effectToggleEvent) {
                setup.setEffectLed(lane, !setup.draftLane(lane).effect);
            }
            previousPressed_[lane] = input.encoderPressed;
            previousEffectPressed_[lane] = input.effectPressed;
        }
    }

   private:
    std::array<bool, terminal_setup::LANE_COUNT> previousPressed_ = {};
    std::array<bool, terminal_setup::LANE_COUNT> previousEffectPressed_ = {};
};

}  // namespace terminal_control_surface
