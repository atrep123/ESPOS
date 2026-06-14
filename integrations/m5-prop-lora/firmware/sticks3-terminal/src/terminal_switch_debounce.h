#pragma once

#include <cstdint>

#include "terminal_switches.h"

namespace terminal_switch_debounce {

class SwitchDebouncer {
   public:
    explicit SwitchDebouncer(std::uint32_t debounceMs) : debounceMs_(debounceMs) {}

    void prime(const terminal_switches::SwitchSnapshot& snapshot, std::uint32_t nowMs) {
        primeChannel(upload_, snapshot.uploadPressed, nowMs);
        primeChannel(simFire_, snapshot.simFirePressed, nowMs);
    }

    terminal_switches::SwitchSnapshot update(const terminal_switches::SwitchSnapshot& raw,
                                             std::uint32_t nowMs) {
        updateChannel(upload_, raw.uploadPressed, nowMs);
        updateChannel(simFire_, raw.simFirePressed, nowMs);
        return stable();
    }

    terminal_switches::SwitchSnapshot stable() const {
        terminal_switches::SwitchSnapshot snapshot;
        snapshot.uploadPressed = upload_.stable;
        snapshot.simFirePressed = simFire_.stable;
        return snapshot;
    }

   private:
    struct Channel {
        bool stable = false;
        bool candidate = false;
        std::uint32_t changedMs = 0;
    };

    static void primeChannel(Channel& channel, bool stable, std::uint32_t nowMs) {
        channel.stable = stable;
        channel.candidate = stable;
        channel.changedMs = nowMs;
    }

    void updateChannel(Channel& channel, bool raw, std::uint32_t nowMs) const {
        if (raw != channel.candidate) {
            channel.candidate = raw;
            channel.changedMs = nowMs;
        }
        if (channel.stable != channel.candidate &&
            (debounceMs_ == 0 || nowMs - channel.changedMs >= debounceMs_)) {
            channel.stable = channel.candidate;
        }
    }

    std::uint32_t debounceMs_ = 0;
    Channel upload_;
    Channel simFire_;
};

}  // namespace terminal_switch_debounce
