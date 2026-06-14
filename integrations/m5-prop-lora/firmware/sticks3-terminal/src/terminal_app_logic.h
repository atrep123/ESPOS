#pragma once

#include <cstdint>
#include <string>

#include "../../../shared/terminal/terminal_setup_link.h"
#include "terminal_setup.h"
#include "terminal_usb_link.h"

namespace terminal_app_logic {

constexpr const char* SIM_FIRE_LINE = "SIM_FIRE";

struct TerminalAction {
    bool drainUsbInput = false;
    bool sendLine = false;
    bool lockFadersToDraft = false;
    bool redraw = false;
    std::string line;
};

inline bool uploadInFlight(const terminal_setup::TerminalSetupState& setup,
                           const terminal_usb_link::UsbSetupLink& link) {
    return setup.status() == terminal_setup::Status::Uploading && link.inFlight() &&
           link.requestKind() == terminal_usb_link::RequestKind::Upload;
}

inline bool uploadBusy(const terminal_setup::TerminalSetupState& setup,
                       const terminal_usb_link::UsbSetupLink& link) {
    return setup.status() == terminal_setup::Status::Uploading || link.inFlight();
}

inline bool canStartUpload(const terminal_setup::TerminalSetupState& setup,
                           const terminal_usb_link::UsbSetupLink& link) {
    return !uploadBusy(setup, link);
}

inline TerminalAction startUploadAfterUsbDrain(terminal_setup::TerminalSetupState& setup,
                                               terminal_usb_link::UsbSetupLink& link,
                                               std::uint32_t nowMs,
                                               std::uint32_t timeoutMs) {
    if (!canStartUpload(setup, link)) {
        return {};
    }
    setup.beginUpload();
    const std::uint32_t requestId = link.beginUpload(nowMs, timeoutMs);
    TerminalAction action;
    action.sendLine = true;
    action.redraw = true;
    action.line = setup.uploadLine(requestId);
    return action;
}

inline TerminalAction requestUpload(terminal_setup::TerminalSetupState& setup,
                                    terminal_usb_link::UsbSetupLink& link,
                                    std::uint32_t nowMs,
                                    std::uint32_t timeoutMs) {
    TerminalAction action = startUploadAfterUsbDrain(setup, link, nowMs, timeoutMs);
    action.drainUsbInput = action.sendLine;
    return action;
}

inline TerminalAction requestSimFire(terminal_setup::TerminalSetupState& setup,
                                     terminal_usb_link::UsbSetupLink& link,
                                     std::uint32_t nowMs,
                                     std::uint32_t timeoutMs) {
    if (uploadBusy(setup, link) || setup.dirty()) {
        return {};
    }
    setup.simulateFire();
    const std::uint32_t requestId = link.beginSimFire(nowMs, timeoutMs);
    TerminalAction action;
    action.drainUsbInput = true;
    action.sendLine = true;
    action.redraw = true;
    action.line = terminal_setup_link::formatSimFireLine(requestId);
    return action;
}

inline TerminalAction handleUploadEvent(terminal_setup::TerminalSetupState& setup,
                                        terminal_usb_link::UsbSetupLink& link,
                                        terminal_usb_link::UploadEvent event) {
    TerminalAction action;
    if (event == terminal_usb_link::UploadEvent::None) {
        return action;
    }
    if (!link.inFlight()) {
        return action;
    }
    if (link.requestKind() == terminal_usb_link::RequestKind::SimFire) {
        link.finishUpload();
        if (event == terminal_usb_link::UploadEvent::Rejected) {
            setup.markProblem();
            action.redraw = true;
        }
        return action;
    }
    if (!uploadInFlight(setup, link)) {
        if (link.inFlight()) {
            link.finishUpload();
        }
        return action;
    }
    switch (event) {
        case terminal_usb_link::UploadEvent::Accepted:
            link.finishUpload();
            setup.commitAccepted();
            action.redraw = true;
            return action;
        case terminal_usb_link::UploadEvent::Rejected:
            link.finishUpload();
            setup.commitRejected();
            action.lockFadersToDraft = true;
            action.redraw = true;
            return action;
        case terminal_usb_link::UploadEvent::None:
            return action;
    }
    return action;
}

}  // namespace terminal_app_logic
