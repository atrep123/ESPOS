#include "../../shared/protocol/prop_xiao_link.h"

#include <array>
#include <iostream>
#include <string>

namespace {

using prop_xiao_link::BarrelMode;
using prop_xiao_link::CommandKind;
using prop_xiao_link::ParseError;
using prop_xiao_link::Rgb;
using prop_xiao_link::parseLine;

bool parsesHelloWithTopology() {
    const auto parsed = parseLine("HELLO XIAO_PROP_IO 1 WS:18 LED:4 BTN:3 SW:1");
    return parsed.kind == CommandKind::Hello &&
           parsed.error == ParseError::None &&
           parsed.hello.version == 1 &&
           parsed.hello.ws2812Count == 18 &&
           parsed.hello.ledCount == 4 &&
           parsed.hello.buttonCount == 3 &&
           parsed.hello.switchCount == 1;
}

bool parsesPingPongSequence() {
    const auto ping = parseLine("PING 42");
    const auto pong = parseLine("PONG 42");
    return ping.kind == CommandKind::Ping &&
           pong.kind == CommandKind::Pong &&
           ping.sequence == 42 &&
           pong.sequence == 42 &&
           prop_xiao_link::formatPingLine(42) == "PING 42" &&
           prop_xiao_link::formatPongLine(42) == "PONG 42";
}

bool parsesButtonAndSwitchEvents() {
    const auto buttonDown = parseLine("BTN 3 DOWN");
    const auto buttonUp = parseLine("BTN 3 UP");
    const auto switchOn = parseLine("SW 1 ON");
    const auto switchOff = parseLine("SW 1 OFF");
    return buttonDown.kind == CommandKind::Button &&
           buttonDown.input.index == 3 &&
           buttonDown.input.active &&
           buttonUp.kind == CommandKind::Button &&
           buttonUp.input.index == 3 &&
           !buttonUp.input.active &&
           switchOn.kind == CommandKind::Switch &&
           switchOn.input.index == 1 &&
           switchOn.input.active &&
           switchOff.kind == CommandKind::Switch &&
           !switchOff.input.active &&
           prop_xiao_link::formatButtonLine(2, true) == "BTN 2 DOWN" &&
           prop_xiao_link::formatSwitchLine(1, false) == "SW 1 OFF";
}

bool parsesAndFormatsStat4Colors() {
    const std::array<Rgb, prop_xiao_link::STATUS_LED_COUNT> colors = {{
        {255, 0, 0},
        {0, 255, 0},
        {0, 0, 255},
        {16, 32, 48},
    }};
    const auto line = prop_xiao_link::formatStat4Line(colors);
    const auto parsed = parseLine(line.c_str());
    return line == "STAT4 FF0000 00FF00 0000FF 102030" &&
           parsed.kind == CommandKind::Stat4 &&
           parsed.stat4[0].r == 255 &&
           parsed.stat4[1].g == 255 &&
           parsed.stat4[2].b == 255 &&
           parsed.stat4[3].r == 16 &&
           parsed.stat4[3].g == 32 &&
           parsed.stat4[3].b == 48;
}

bool parsesBarrelCommands() {
    const auto off = parseLine("BARREL OFF");
    const auto red = parseLine("BARREL RED 180");
    const auto fire = parseLine("BARREL FIRE 150 400 650 2");
    return off.kind == CommandKind::Barrel &&
           off.barrel.mode == BarrelMode::Off &&
           red.kind == CommandKind::Barrel &&
           red.barrel.mode == BarrelMode::Red &&
           red.barrel.intensity == 180 &&
           fire.kind == CommandKind::Barrel &&
           fire.barrel.mode == BarrelMode::Fire &&
           fire.barrel.rampMs == 150 &&
           fire.barrel.holdMs == 400 &&
           fire.barrel.fadeMs == 650 &&
           fire.barrel.curve == 2 &&
           prop_xiao_link::formatBarrelOffLine() == "BARREL OFF" &&
           prop_xiao_link::formatBarrelRedLine(180) == "BARREL RED 180" &&
           prop_xiao_link::formatBarrelFireLine(150, 400, 650, 2) == "BARREL FIRE 150 400 650 2";
}

bool rejectsMalformedLines() {
    return parseLine("BTN 0 DOWN").error == ParseError::BadValue &&
           parseLine("BTN 4 DOWN").error == ParseError::BadValue &&
           parseLine("BTN3 DOWN").kind == CommandKind::Error &&
           parseLine("BTN 3DOWN").kind == CommandKind::Error &&
           parseLine("BTN 3 DOWNX").kind == CommandKind::Error &&
           parseLine("SW 2 ON").error == ParseError::BadValue &&
           parseLine("SW1 ON").kind == CommandKind::Error &&
           parseLine("SW 1ON").kind == CommandKind::Error &&
           parseLine("STAT4 FF0000 00FF00 0000FF").error == ParseError::BadValue &&
           parseLine("STAT4 FF000000FF00 0000FF 001122").kind == CommandKind::Error &&
           parseLine("STAT4 FF0000 00FF00 0000FF 001122 EXTRA").error == ParseError::ExtraToken &&
           parseLine("BARREL RED 256").error == ParseError::BadValue &&
           parseLine("BARRELRED 180").kind == CommandKind::Error &&
           parseLine("BARREL RED180").kind == CommandKind::Error &&
           parseLine("BARREL FIRE 150 400 650 3").error == ParseError::BadValue &&
           parseLine("BARREL FIRE 150400 650 2").kind == CommandKind::Error &&
           parseLine("PING42").kind == CommandKind::Error &&
           parseLine("PING 10000").error == ParseError::BadValue &&
           parseLine("PONG42").kind == CommandKind::Error &&
           parseLine("PONG 10000").error == ParseError::BadValue &&
           parseLine("HELLOXIAO_PROP_IO 1 WS:18 LED:4 BTN:3 SW:1").kind == CommandKind::Error &&
           parseLine("HELLO XIAO_PROP_IO 1 WS:18LED:4 BTN:3 SW:1").kind == CommandKind::Error &&
           parseLine(std::string(prop_xiao_link::MAX_LINE_LENGTH, 'A').c_str()).error == ParseError::BadValue &&
           parseLine("HELLO XIAO_PROP_IO 2 WS:18 LED:4 BTN:3 SW:1").error == ParseError::BadValue;
}

bool formattedLinesFitBudget() {
    const std::array<Rgb, prop_xiao_link::STATUS_LED_COUNT> colors = {{
        {255, 255, 255},
        {255, 255, 255},
        {255, 255, 255},
        {255, 255, 255},
    }};
    return prop_xiao_link::formatHelloLine().size() < prop_xiao_link::MAX_LINE_LENGTH &&
           prop_xiao_link::formatStat4Line(colors).size() < prop_xiao_link::MAX_LINE_LENGTH &&
           prop_xiao_link::formatBarrelFireLine(5000, 5000, 5000, 2).size() < prop_xiao_link::MAX_LINE_LENGTH;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("parses HELLO topology", parsesHelloWithTopology) ? 0 : 1;
    failures += runCase("parses PING/PONG sequence", parsesPingPongSequence) ? 0 : 1;
    failures += runCase("parses button and switch events", parsesButtonAndSwitchEvents) ? 0 : 1;
    failures += runCase("parses and formats STAT4 colors", parsesAndFormatsStat4Colors) ? 0 : 1;
    failures += runCase("parses BARREL commands", parsesBarrelCommands) ? 0 : 1;
    failures += runCase("rejects malformed lines", rejectsMalformedLines) ? 0 : 1;
    failures += runCase("formatted lines fit budget", formattedLinesFitBudget) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
