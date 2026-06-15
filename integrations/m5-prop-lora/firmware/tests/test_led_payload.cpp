#include "../../shared/protocol/prop_protocol.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {

using LedColors = std::array<std::array<std::uint8_t, 3>, 4>;

using prop_protocol::LED_PAYLOAD_LENGTH;
using prop_protocol::PROP_ACTION_BARREL_EFFECT;
using prop_protocol::PROP_ACTION_BLUE_SET;
using prop_protocol::encodeLedPayload;
using prop_protocol::encodePropActionPayload;
using prop_protocol::parsePropActionPayload;

bool applyLedPayload(const std::vector<std::uint8_t>& payload, LedColors& out) {
    if (payload.size() != LED_PAYLOAD_LENGTH) {
        return false;
    }

    for (std::size_t i = 0; i < out.size(); ++i) {
        out[i][0] = payload[1 + i * 3];
        out[i][1] = payload[2 + i * 3];
        out[i][2] = payload[3 + i * 3];
    }
    return true;
}

bool byteOrderMatchesDocumentedLayout() {
    const LedColors colors = {{
        {{0x11, 0x12, 0x13}},
        {{0x21, 0x22, 0x23}},
        {{0x31, 0x32, 0x33}},
        {{0x41, 0x42, 0x43}},
    }};

    std::vector<std::uint8_t> payload;
    if (!encodeLedPayload(0xA5, colors, payload)) {
        return false;
    }

    const std::vector<std::uint8_t> expected = {
        0xA5,
        0x11, 0x12, 0x13,
        0x21, 0x22, 0x23,
        0x31, 0x32, 0x33,
        0x41, 0x42, 0x43,
    };
    return payload == expected;
}

bool encodeApplyRoundTripPreservesFourRgbColors() {
    const LedColors in = {{
        {{0x00, 0x7F, 0xFF}},
        {{0x10, 0x20, 0x30}},
        {{0xFE, 0x01, 0x80}},
        {{0xAA, 0x55, 0x33}},
    }};

    std::vector<std::uint8_t> payload;
    if (!encodeLedPayload(0xC8, in, payload)) {
        return false;
    }

    LedColors out = {};
    return applyLedPayload(payload, out) && out == in;
}

bool rejectsWrongLengthPayload() {
    LedColors out = {};
    return !applyLedPayload(std::vector<std::uint8_t>{0xC8}, out);
}

bool propActionPayloadRoundTripsBlueSet() {
    std::vector<std::uint8_t> payload;
    prop_protocol::PropActionPayload parsed;
    return encodePropActionPayload(PROP_ACTION_BLUE_SET, 1, 0x01020304, payload) &&
           payload == std::vector<std::uint8_t>({1, 1, 1, 2, 3, 4}) &&
           parsePropActionPayload(payload, parsed) &&
           parsed.action == PROP_ACTION_BLUE_SET &&
           parsed.value == 1 &&
           parsed.eventId == 0x01020304;
}

bool propActionPayloadRoundTripsBarrelEffect() {
    std::vector<std::uint8_t> payload;
    prop_protocol::PropActionPayload parsed;
    return encodePropActionPayload(PROP_ACTION_BARREL_EFFECT, 0, 7, payload) &&
           payload == std::vector<std::uint8_t>({2, 0, 0, 0, 0, 7}) &&
           parsePropActionPayload(payload, parsed) &&
           parsed.action == PROP_ACTION_BARREL_EFFECT &&
           parsed.value == 0 &&
           parsed.eventId == 7;
}

bool propActionPayloadRejectsInvalidValues() {
    std::vector<std::uint8_t> payload;
    prop_protocol::PropActionPayload parsed;
    return !encodePropActionPayload(0, 0, 1, payload) &&
           !encodePropActionPayload(PROP_ACTION_BLUE_SET, 2, 1, payload) &&
           !encodePropActionPayload(PROP_ACTION_BARREL_EFFECT, 1, 1, payload) &&
           !parsePropActionPayload(std::vector<std::uint8_t>{1, 1}, parsed);
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("LED payload byte order is reserved byte + 4 RGB", byteOrderMatchesDocumentedLayout) ? 0 : 1;
    failures += runCase("encode/apply round-trip preserves four RGB colours", encodeApplyRoundTripPreservesFourRgbColors) ? 0 : 1;
    failures += runCase("apply rejects wrong payload length", rejectsWrongLengthPayload) ? 0 : 1;
    failures += runCase("prop action payload round-trips blue set", propActionPayloadRoundTripsBlueSet) ? 0 : 1;
    failures += runCase("prop action payload round-trips barrel effect", propActionPayloadRoundTripsBarrelEffect) ? 0 : 1;
    failures += runCase("prop action payload rejects invalid values", propActionPayloadRejectsInvalidValues) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
