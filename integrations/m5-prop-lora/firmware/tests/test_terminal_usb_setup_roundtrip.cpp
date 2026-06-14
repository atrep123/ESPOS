#include "../sticks3-terminal/src/terminal_app_logic.h"
#include "../../shared/terminal/terminal_setup_receiver.h"

#include <iostream>
#include <string>

namespace {

using terminal_app_logic::TerminalAction;
using terminal_app_logic::handleUploadEvent;
using terminal_app_logic::requestSimFire;
using terminal_app_logic::requestUpload;
using terminal_setup::Status;
using terminal_setup::TerminalSetupState;
using terminal_setup_receiver::ReceiverCallbacks;
using terminal_setup_receiver::Reply;
using terminal_setup_receiver::ReplyResult;
using terminal_usb_link::UploadEvent;

struct ReceiverHarness {
    int commits = 0;
    int previews = 0;
    bool acceptCommit = true;
    bool acceptPreview = true;
    terminal_setup_apply::AppliedSetup lastSetup = {};
};

bool commitSetup(void* ctx, const terminal_setup_apply::AppliedSetup& setup) {
    auto* harness = static_cast<ReceiverHarness*>(ctx);
    ++harness->commits;
    harness->lastSetup = setup;
    return harness->acceptCommit;
}

bool previewSimFire(void* ctx) {
    auto* harness = static_cast<ReceiverHarness*>(ctx);
    ++harness->previews;
    return harness->acceptPreview;
}

ReceiverCallbacks callbacks(ReceiverHarness& harness) {
    return ReceiverCallbacks{&harness, commitSetup, previewSimFire};
}

UploadEvent feedLine(terminal_usb_link::UsbSetupLink& link, const std::string& line) {
    UploadEvent last = UploadEvent::None;
    for (char ch : line) {
        const UploadEvent event = link.push(ch);
        if (event != UploadEvent::None) {
            last = event;
        }
    }
    const UploadEvent newline = link.push('\n');
    return newline == UploadEvent::None ? last : newline;
}

bool emptyAction(const TerminalAction& action) {
    return !action.drainUsbInput && !action.sendLine && !action.lockFadersToDraft &&
           !action.redraw && action.line.empty();
}

bool uploadSetupLineCommitsThroughReceiverReply() {
    TerminalSetupState state;
    terminal_usb_link::UsbSetupLink link(160);
    ReceiverHarness receiver;

    state.setBrightness(0, 42);
    state.rotateHue(0, 6);
    state.setEffectLed(0, true);
    state.setBrightness(1, 0);
    state.setEffectLed(1, true);

    const TerminalAction upload = requestUpload(state, link, 100, 1500);
    if (!upload.sendLine || upload.line.rfind("SETUP 1 ", 0) != 0 ||
        state.status() != Status::Uploading || !link.inFlight()) {
        return false;
    }

    const ReplyResult reply = terminal_setup_receiver::handleLineResult(
        upload.line.c_str(),
        callbacks(receiver));
    if (reply.kind != Reply::SetupOk ||
        terminal_setup_receiver::replyLine(reply) != "SETUP_OK 1" ||
        receiver.commits != 1 ||
        receiver.lastSetup.lanes[0].brightness != terminal_setup_apply::percentToByte(42) ||
        receiver.lastSetup.lanes[0].color != terminal_setup_apply::Rgb{255, 128, 0} ||
        receiver.lastSetup.lanes[0].effect != true ||
        receiver.lastSetup.lanes[1].on != false ||
        receiver.lastSetup.lanes[1].effect != true ||
        receiver.lastSetup.effectPreviewMask != 0x03) {
        return false;
    }

    const UploadEvent event = feedLine(link, terminal_setup_receiver::replyLine(reply));
    const TerminalAction accepted = handleUploadEvent(state, link, event);
    return event == UploadEvent::Accepted &&
           accepted.redraw &&
           !link.inFlight() &&
           state.status() == Status::Uploaded &&
           state.savedLane(0).brightness == 42 &&
           state.savedLane(0).hue == 361 &&
           state.savedLane(0).effect == true;
}

bool receiverSetupErrRollsTerminalBackToProblem() {
    TerminalSetupState state;
    terminal_usb_link::UsbSetupLink link(160);
    ReceiverHarness receiver;
    receiver.acceptCommit = false;

    state.setBrightness(0, 42);
    const TerminalAction upload = requestUpload(state, link, 100, 1500);
    const ReplyResult reply = terminal_setup_receiver::handleLineResult(
        upload.line.c_str(),
        callbacks(receiver));
    if (reply.kind != Reply::SetupErr ||
        terminal_setup_receiver::replyLine(reply) != "SETUP_ERR 1" ||
        receiver.commits != 1) {
        return false;
    }

    const UploadEvent event = feedLine(link, terminal_setup_receiver::replyLine(reply));
    const TerminalAction rejected = handleUploadEvent(state, link, event);
    return event == UploadEvent::Rejected &&
           rejected.redraw &&
           rejected.lockFadersToDraft &&
           !link.inFlight() &&
           state.status() == Status::Problem &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 100;
}

bool simFirePreviewUsesReceiverCallbackWithoutSetupCommit() {
    TerminalSetupState state;
    terminal_usb_link::UsbSetupLink link(160);
    ReceiverHarness receiver;

    const TerminalAction action = requestSimFire(state, link, 100, 1500);
    const ReplyResult reply = terminal_setup_receiver::handleLineResult(
        action.line.c_str(),
        callbacks(receiver));
    const UploadEvent event = feedLine(link, terminal_setup_receiver::replyLine(reply));
    const TerminalAction accepted = handleUploadEvent(state, link, event);

    return action.sendLine &&
           action.line == "SIM_FIRE 1" &&
           state.status() == Status::SimFire &&
           reply.kind == Reply::SetupOk &&
           terminal_setup_receiver::replyLine(reply) == "SETUP_OK 1" &&
           event == UploadEvent::Accepted &&
           emptyAction(accepted) &&
           receiver.commits == 0 &&
           receiver.previews == 1 &&
           !link.inFlight();
}

bool simFireRejectionRollsTerminalToProblem() {
    TerminalSetupState state;
    terminal_usb_link::UsbSetupLink link(160);
    ReceiverHarness receiver;
    receiver.acceptPreview = false;

    const TerminalAction action = requestSimFire(state, link, 100, 1500);
    const ReplyResult reply = terminal_setup_receiver::handleLineResult(
        action.line.c_str(),
        callbacks(receiver));
    const UploadEvent event = feedLine(link, terminal_setup_receiver::replyLine(reply));
    const TerminalAction rejected = handleUploadEvent(state, link, event);

    return action.line == "SIM_FIRE 1" &&
           reply.kind == Reply::SetupErr &&
           terminal_setup_receiver::replyLine(reply) == "SETUP_ERR 1" &&
           event == UploadEvent::Rejected &&
           rejected.redraw &&
           !link.inFlight() &&
           state.status() == Status::Problem &&
           state.draftLane(0).brightness == 100 &&
           state.savedLane(0).brightness == 100;
}

bool lateSetupOkAfterTimeoutCannotCommit() {
    TerminalSetupState state;
    terminal_usb_link::UsbSetupLink link(160);
    ReceiverHarness receiver;

    state.setBrightness(0, 42);
    const TerminalAction upload = requestUpload(state, link, 100, 1500);
    const ReplyResult reply = terminal_setup_receiver::handleLineResult(
        upload.line.c_str(),
        callbacks(receiver));
    if (reply.kind != Reply::SetupOk || receiver.commits != 1) {
        return false;
    }

    const UploadEvent timeout = link.pollTimeout(1601);
    const TerminalAction rejected = handleUploadEvent(state, link, timeout);
    if (timeout != UploadEvent::Rejected ||
        !rejected.redraw ||
        state.status() != Status::Problem ||
        link.inFlight()) {
        return false;
    }

    const UploadEvent late = feedLine(link, terminal_setup_receiver::replyLine(reply));
    const TerminalAction lateAction = handleUploadEvent(state, link, late);
    return late == UploadEvent::None &&
           !lateAction.redraw &&
           state.status() == Status::Problem &&
           state.savedLane(0).brightness == 100 &&
           state.draftLane(0).brightness == 100;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("upload SETUP line commits through receiver reply", uploadSetupLineCommitsThroughReceiverReply) ? 0 : 1;
    failures += runCase("receiver SETUP_ERR rolls terminal back to problem", receiverSetupErrRollsTerminalBackToProblem) ? 0 : 1;
    failures += runCase("SIM_FIRE preview uses receiver callback without setup commit", simFirePreviewUsesReceiverCallbackWithoutSetupCommit) ? 0 : 1;
    failures += runCase("SIM_FIRE rejection rolls terminal to problem", simFireRejectionRollsTerminalToProblem) ? 0 : 1;
    failures += runCase("late SETUP_OK after timeout cannot commit", lateSetupOkAfterTimeoutCannotCommit) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
