#pragma once

#include "terminal_switches.h"

namespace terminal_switch_dispatch {

enum class SwitchAction {
    None,
    Upload,
    SimFire,
};

inline SwitchAction chooseAction(const terminal_switches::SwitchEvents& events,
                                 bool uploadInFlight) {
    if (uploadInFlight) {
        return SwitchAction::None;
    }
    if (events.upload) {
        return SwitchAction::Upload;
    }
    if (events.simFire) {
        return SwitchAction::SimFire;
    }
    return SwitchAction::None;
}

}  // namespace terminal_switch_dispatch
