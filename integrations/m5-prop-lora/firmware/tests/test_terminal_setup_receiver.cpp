#include "../../shared/terminal/terminal_setup_receiver.h"

#include <iostream>

namespace {

using terminal_setup_receiver::ReceiverCallbacks;
using terminal_setup_receiver::Reply;
using terminal_setup_receiver::ReplyResult;
using terminal_setup_receiver::handleLine;
using terminal_setup_receiver::handleLineResult;
using terminal_setup_receiver::replyLine;

struct Harness {
    int commits = 0;
    int previews = 0;
    bool acceptCommit = true;
    bool acceptPreview = true;
    terminal_setup_apply::AppliedSetup last = {};
};

bool commitSetup(void* ctx, const terminal_setup_apply::AppliedSetup& setup) {
    auto* harness = static_cast<Harness*>(ctx);
    ++harness->commits;
    harness->last = setup;
    return harness->acceptCommit;
}

bool previewSimFire(void* ctx) {
    auto* harness = static_cast<Harness*>(ctx);
    ++harness->previews;
    return harness->acceptPreview;
}

ReceiverCallbacks callbacks(Harness& harness) {
    return ReceiverCallbacks{&harness, commitSetup, previewSimFire};
}

bool validSetupAppliesAtomicallyAndReturnsOk() {
    Harness harness;
    const Reply reply = handleLine(
        "SETUP L1:0,100,1,1 L2:120,50,0,0 L3:240,25,1,1 L4:60,0,1,0 L5:300,80,0,1",
        callbacks(harness));
    return reply == Reply::SetupOk &&
           replyLine(reply) == std::string("SETUP_OK") &&
           harness.commits == 1 &&
           harness.previews == 0 &&
           harness.last.lanes[0].brightness == 255 &&
           harness.last.lanes[1].on == false &&
           harness.last.effectMask == 0b00010101;
}

bool validSetupEchoesRequestId() {
    Harness harness;
    const ReplyResult reply = handleLineResult(
        "SETUP 42 L1:0,100,1,1 L2:120,50,0,0 L3:240,25,1,1 L4:60,0,1,0 L5:300,80,0,1",
        callbacks(harness));
    return reply.kind == Reply::SetupOk &&
           reply.requestId == 42 &&
           replyLine(reply) == std::string("SETUP_OK 42") &&
           harness.commits == 1 &&
           harness.previews == 0;
}

bool validSetupAppliesNamedWhiteOnLane3() {
    Harness harness;
    const Reply reply = handleLine(
        "SETUP L1:360,100,1,1 L2:365,50,0,0 L3:368,25,1,1 L4:361,0,1,0 L5:367,80,0,1",
        callbacks(harness));
    return reply == Reply::SetupOk &&
           harness.commits == 1 &&
           harness.previews == 0 &&
           harness.last.lanes[2].color == terminal_setup_apply::Rgb{255, 255, 255} &&
           harness.last.lanes[2].brightness == 64 &&
           harness.last.lanes[2].on &&
           harness.last.lanes[2].effect;
}

bool malformedSetupReturnsErrWithoutCommit() {
    Harness harness;
    const Reply reply = handleLine(
        "SETUP L1:0,100,1,1 L2:120,50,0,0",
        callbacks(harness));
    return reply == Reply::SetupErr &&
           replyLine(reply) == std::string("SETUP_ERR") &&
           harness.commits == 0 &&
           harness.previews == 0;
}

bool malformedSetupEchoesRequestIdWithoutCommit() {
    Harness harness;
    const ReplyResult reply = handleLineResult(
        "SETUP 42 L1:0,100,1,1 L2:120,50,0,0",
        callbacks(harness));
    return reply.kind == Reply::SetupErr &&
           reply.requestId == 42 &&
           replyLine(reply) == std::string("SETUP_ERR 42") &&
           harness.commits == 0 &&
           harness.previews == 0;
}

bool callbackFailureReturnsErr() {
    Harness harness;
    harness.acceptCommit = false;
    const Reply reply = handleLine(
        "SETUP L1:0,100,1,0 L2:0,100,1,0 L3:0,100,1,0 L4:0,100,1,0 L5:0,100,1,0",
        callbacks(harness));
    return reply == Reply::SetupErr &&
           harness.commits == 1 &&
           harness.previews == 0;
}

bool simFireUsesOnlyPreviewCallback() {
    Harness harness;
    const Reply reply = handleLine("SIM_FIRE", callbacks(harness));
    return reply == Reply::SetupOk &&
           harness.commits == 0 &&
           harness.previews == 1;
}

bool simFireEchoesRequestId() {
    Harness harness;
    const ReplyResult reply = handleLineResult("SIM_FIRE 42", callbacks(harness));
    return reply.kind == Reply::SetupOk &&
           reply.requestId == 42 &&
           replyLine(reply) == std::string("SETUP_OK 42") &&
           harness.commits == 0 &&
           harness.previews == 1;
}

bool unknownCommandReturnsErrWithoutCallbacks() {
    Harness harness;
    const Reply reply = handleLine("FIRE", callbacks(harness));
    return reply == Reply::SetupErr &&
           harness.commits == 0 &&
           harness.previews == 0;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("valid SETUP applies atomically and returns OK", validSetupAppliesAtomicallyAndReturnsOk) ? 0 : 1;
    failures += runCase("valid SETUP echoes request id", validSetupEchoesRequestId) ? 0 : 1;
    failures += runCase("valid SETUP applies named white on lane 3", validSetupAppliesNamedWhiteOnLane3) ? 0 : 1;
    failures += runCase("malformed SETUP returns ERR without commit", malformedSetupReturnsErrWithoutCommit) ? 0 : 1;
    failures += runCase("malformed SETUP echoes request id without commit", malformedSetupEchoesRequestIdWithoutCommit) ? 0 : 1;
    failures += runCase("callback failure returns ERR", callbackFailureReturnsErr) ? 0 : 1;
    failures += runCase("SIM_FIRE uses only preview callback", simFireUsesOnlyPreviewCallback) ? 0 : 1;
    failures += runCase("SIM_FIRE echoes request id", simFireEchoesRequestId) ? 0 : 1;
    failures += runCase("unknown command returns ERR without callbacks", unknownCommandReturnsErrWithoutCallbacks) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
