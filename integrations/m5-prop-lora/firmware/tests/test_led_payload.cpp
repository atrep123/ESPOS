#include "../../shared/protocol/prop_protocol.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {

using LedColors = std::array<std::array<std::uint8_t, 3>, 4>;

using prop_protocol::LED_PAYLOAD_LENGTH;
using prop_protocol::encodeLedPayload;

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
    return failures == 0 ? 0 : 1;
}
