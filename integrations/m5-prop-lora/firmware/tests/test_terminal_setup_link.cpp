#include "../../shared/terminal/terminal_setup_link.h"

#include <iostream>
#include <string>

namespace {

using terminal_setup_link::CommandKind;
using terminal_setup_link::ParseError;
using terminal_setup_link::SetupCommand;
using terminal_setup_link::formatSimFireLine;
using terminal_setup_link::formatSetupLine;
using terminal_setup_link::parseLine;

bool parsesValidSetupLine() {
    const auto parsed = parseLine(
        "SETUP L1:0,0,1,0 L2:45,25,0,1 L3:120,50,1,1 L4:240,75,0,0 L5:359,100,1,0");
    return parsed.kind == CommandKind::Setup &&
           parsed.error == ParseError::None &&
           parsed.setup.requestId == 0 &&
           parsed.setup.lanes[0].hue == 0 &&
           parsed.setup.lanes[0].brightness == 0 &&
           parsed.setup.lanes[0].on == true &&
           parsed.setup.lanes[0].effect == false &&
           parsed.setup.lanes[1].hue == 45 &&
           parsed.setup.lanes[1].brightness == 25 &&
           parsed.setup.lanes[1].on == false &&
           parsed.setup.lanes[1].effect == true &&
           parsed.setup.lanes[2].hue == 120 &&
           parsed.setup.lanes[2].brightness == 50 &&
           parsed.setup.lanes[2].on == true &&
           parsed.setup.lanes[2].effect == true &&
           parsed.setup.lanes[3].hue == 240 &&
           parsed.setup.lanes[3].brightness == 75 &&
           parsed.setup.lanes[3].on == false &&
           parsed.setup.lanes[3].effect == false &&
           parsed.setup.lanes[4].hue == 359 &&
           parsed.setup.lanes[4].brightness == 100 &&
           parsed.setup.lanes[4].on == true &&
           parsed.setup.lanes[4].effect == false;
}

bool parsesSetupRequestId() {
    const auto parsed = parseLine(
        "SETUP 42 L1:0,0,1,0 L2:45,25,0,1 L3:120,50,1,1 L4:240,75,0,0 L5:359,100,1,0");
    return parsed.kind == CommandKind::Setup &&
           parsed.error == ParseError::None &&
           parsed.setup.requestId == 42 &&
           parsed.setup.lanes[1].hue == 45 &&
           parsed.setup.lanes[4].brightness == 100;
}

bool parsesSimFireWithoutSetupCommitData() {
    const auto parsed = parseLine("  SIM_FIRE  ");
    const auto scoped = parseLine("  SIM_FIRE 42 ");
    return parsed.kind == CommandKind::SimFire &&
           parsed.error == ParseError::None &&
           parsed.setup.requestId == 0 &&
           scoped.kind == CommandKind::SimFire &&
           scoped.error == ParseError::None &&
           scoped.setup.requestId == 42;
}

bool parsesNamedColorSetupLine() {
    const auto parsed = parseLine(
        "SETUP L1:360,0,1,0 L2:361,25,0,1 L3:364,50,1,1 L4:368,75,0,0 L5:365,100,1,0");
    return parsed.kind == CommandKind::Setup &&
           parsed.error == ParseError::None &&
           parsed.setup.lanes[0].hue == 360 &&
           parsed.setup.lanes[3].hue == 368 &&
           parsed.setup.lanes[4].hue == 365;
}

bool rejectsMalformedSetupLines() {
    return parseLine("SETUP").error == ParseError::MissingLane &&
           parseLine("SETUP L1:0,10,1").kind == CommandKind::Error &&
           parseLine("SETUP L1:0,10,1,0 L1:1,10,1,0 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0").error == ParseError::DuplicateLane &&
           parseLine("SETUP L1:0,10,1,0 L2:0,10,1,0").error == ParseError::MissingLane &&
           parseLine("SETUP L1:369,10,1,0 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0 L5:0,10,1,0").error == ParseError::BadValue &&
           parseLine("SETUP L1:0,101,1,0 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0 L5:0,10,1,0").error == ParseError::BadValue &&
           parseLine("SETUP L1:0,10,2,0 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0 L5:0,10,1,0").error == ParseError::BadValue &&
           parseLine("SETUP L1:0,10,1,2 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0 L5:0,10,1,0").error == ParseError::BadValue &&
           parseLine("SETUP L1:-1,10,1,0 L2:0,10,1,0 L3:0,10,1,0 L4:0,10,1,0 L5:0,10,1,0").error == ParseError::BadValue &&
           parseLine("SIM_FIRE 10000").error == ParseError::BadValue &&
           parseLine("SIM_FIRE NOW").error == ParseError::ExtraToken;
}

bool formatsSetupLineForRoundTrip() {
    SetupCommand command;
    command.lanes[0].hue = 12;
    command.lanes[0].brightness = 34;
    command.lanes[0].on = true;
    command.lanes[0].effect = false;
    command.lanes[4].hue = 270;
    command.lanes[4].brightness = 88;
    command.lanes[4].on = false;
    command.lanes[4].effect = true;

    const std::string line = formatSetupLine(command);
    const std::string scopedLine = formatSetupLine(command, 42);
    const auto parsed = parseLine(line.c_str());
    const auto scopedParsed = parseLine(scopedLine.c_str());
    return line.find("SETUP L1:12,34,1,0") == 0 &&
           scopedLine.find("SETUP 42 L1:12,34,1,0") == 0 &&
           line.find("L5:270,88,0,1") != std::string::npos &&
           scopedLine.find("L5:270,88,0,1") != std::string::npos &&
           parsed.kind == CommandKind::Setup &&
           scopedParsed.kind == CommandKind::Setup &&
           scopedParsed.setup.requestId == 42 &&
           parsed.setup.lanes[0].hue == 12 &&
           parsed.setup.lanes[4].effect == true;
}

bool formatsRequestScopedReplies() {
    return terminal_setup_link::formatResponseLine(terminal_setup_link::RESPONSE_OK, 42) == "SETUP_OK 42" &&
           terminal_setup_link::formatResponseLine(terminal_setup_link::RESPONSE_ERR, 42) == "SETUP_ERR 42" &&
           terminal_setup_link::formatResponseLine(terminal_setup_link::RESPONSE_OK, 0) == "SETUP_OK";
}

bool formatsSimFireLineWithRequestId() {
    return formatSimFireLine(0) == "SIM_FIRE" &&
           formatSimFireLine(42) == "SIM_FIRE 42" &&
           parseLine(formatSimFireLine(42).c_str()).setup.requestId == 42;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("parses valid setup line", parsesValidSetupLine) ? 0 : 1;
    failures += runCase("parses setup request id", parsesSetupRequestId) ? 0 : 1;
    failures += runCase("parses sim fire without setup commit data", parsesSimFireWithoutSetupCommitData) ? 0 : 1;
    failures += runCase("parses named color setup line", parsesNamedColorSetupLine) ? 0 : 1;
    failures += runCase("rejects malformed setup lines", rejectsMalformedSetupLines) ? 0 : 1;
    failures += runCase("formats setup line for round trip", formatsSetupLineForRoundTrip) ? 0 : 1;
    failures += runCase("formats request-scoped replies", formatsRequestScopedReplies) ? 0 : 1;
    failures += runCase("formats SIM_FIRE line with request id", formatsSimFireLineWithRequestId) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
