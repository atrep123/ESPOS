#pragma once

#include <cstdint>

#include "terminal_app_logic.h"
#include "terminal_control_surface.h"
#include "terminal_external_display.h"
#include "terminal_switch_dispatch.h"
#include "terminal_usb_link.h"

namespace terminal_physical_tick {

struct PhysicalTickResult {
    terminal_external_display::DisplayFrame frame = {};
    terminal_app_logic::TerminalAction action = {};
    bool frameChanged = false;
    bool drainedUsbBeforeUpload = false;
};

template <typename DrainUsbInput>
PhysicalTickResult runPhysicalTick(const terminal_control_surface::ControlSnapshot& snapshot,
                                   terminal_switch_dispatch::SwitchAction switchAction,
                                   terminal_setup::TerminalSetupState& setup,
                                   terminal_control_surface::ControlSurface& controls,
                                   terminal_usb_link::UsbSetupLink& link,
                                   terminal_external_display::DisplayFrame& cachedFrame,
                                   std::uint32_t nowMs,
                                   std::uint32_t timeoutMs,
                                   DrainUsbInput drainUsbInput) {
    controls.apply(snapshot, setup);

    PhysicalTickResult result;
    result.frame = terminal_external_display::makeFrame(setup);
    result.frameChanged = result.frame != cachedFrame;

    switch (switchAction) {
        case terminal_switch_dispatch::SwitchAction::Upload:
            if (!terminal_app_logic::canStartUpload(setup, link)) {
                return result;
            }
            drainUsbInput();
            result.drainedUsbBeforeUpload = true;
            result.action =
                terminal_app_logic::startUploadAfterUsbDrain(setup, link, nowMs, timeoutMs);
            return result;
        case terminal_switch_dispatch::SwitchAction::SimFire:
            result.action = terminal_app_logic::requestSimFire(setup, link, nowMs, timeoutMs);
            return result;
        case terminal_switch_dispatch::SwitchAction::None:
            return result;
    }
    return result;
}

}  // namespace terminal_physical_tick
