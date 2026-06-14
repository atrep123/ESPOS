#pragma once

#include <cstdint>

#include "terminal_switch_debounce.h"
#include "terminal_switch_dispatch.h"
#include "terminal_switches.h"

namespace terminal_switch_pipeline {

class SwitchPipeline {
   public:
    explicit SwitchPipeline(std::uint32_t debounceMs) : debouncer_(debounceMs) {}

    void prime(const terminal_switches::SwitchSnapshot& raw, std::uint32_t nowMs) {
        debouncer_.prime(raw, nowMs);
        edges_.prime(debouncer_.stable());
    }

    terminal_switch_dispatch::SwitchAction update(const terminal_switches::SwitchSnapshot& raw,
                                                  std::uint32_t nowMs,
                                                  bool uploadInFlight) {
        const terminal_switches::SwitchSnapshot stable = debouncer_.update(raw, nowMs);
        const terminal_switches::SwitchEvents events = edges_.update(stable);
        return terminal_switch_dispatch::chooseAction(events, uploadInFlight);
    }

    terminal_switches::SwitchSnapshot stable() const {
        return debouncer_.stable();
    }

   private:
    terminal_switch_debounce::SwitchDebouncer debouncer_;
    terminal_switches::SwitchEdgeTracker edges_;
};

}  // namespace terminal_switch_pipeline
