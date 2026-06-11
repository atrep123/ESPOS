#include "../../shared/protocol/prop_protocol.h"

#include <array>
#include <cstdint>
#include <iostream>
#include <vector>

namespace {

using prop_protocol::HEADER_LENGTH;
using prop_protocol::MAC_LENGTH;
using prop_protocol::MAX_FRAME_LENGTH;
using prop_protocol::MAX_PALETTE_COLORS;
using prop_protocol::PALETTE_HEADER_LENGTH;
using prop_protocol::PalettePayload;
using prop_protocol::encodePalettePayload;
using prop_protocol::parsePalettePayload;

std::array<uint8_t, 3> color(uint8_t r, uint8_t g, uint8_t b) {
    return {r, g, b};
}

bool roundTripOneColorStep() {
    PalettePayload in;
    in.paletteRev = 7;
    in.fade = false;
    in.colors.push_back(color(0x12, 0x34, 0x56));

    std::vector<uint8_t> payload;
    if (!encodePalettePayload(in, payload)) {
        return false;
    }
    if (payload != std::vector<uint8_t>{7, 0, 1, 0x12, 0x34, 0x56}) {
        return false;
    }

    PalettePayload out;
    return parsePalettePayload(payload, out) &&
           out.paletteRev == in.paletteRev &&
           out.fade == in.fade &&
           out.colors == in.colors;
}

bool roundTripEightColorsFade() {
    PalettePayload in;
    in.paletteRev = 42;
    in.fade = true;
    in.colors = {
        color(0, 1, 2),
        color(3, 4, 5),
        color(6, 7, 8),
        color(9, 10, 11),
        color(12, 13, 14),
        color(15, 16, 17),
        color(18, 19, 20),
        color(21, 22, 23),
    };

    std::vector<uint8_t> payload;
    if (!encodePalettePayload(in, payload)) {
        return false;
    }
    if (payload.size() != PALETTE_HEADER_LENGTH + 3 * MAX_PALETTE_COLORS) {
        return false;
    }
    if (payload[0] != 42 || payload[1] != 1 || payload[2] != MAX_PALETTE_COLORS) {
        return false;
    }

    PalettePayload out;
    return parsePalettePayload(payload, out) &&
           out.paletteRev == in.paletteRev &&
           out.fade == in.fade &&
           out.colors == in.colors;
}

bool rejectCountZero() {
    PalettePayload out;
    return !parsePalettePayload(std::vector<uint8_t>{1, 0, 0}, out);
}

bool rejectOversized() {
    PalettePayload in;
    in.colors = {
        color(0, 0, 0),
        color(1, 1, 1),
        color(2, 2, 2),
        color(3, 3, 3),
        color(4, 4, 4),
        color(5, 5, 5),
        color(6, 6, 6),
        color(7, 7, 7),
        color(8, 8, 8),
    };

    std::vector<uint8_t> payload;
    return !encodePalettePayload(in, payload);
}

bool rejectTruncatedPayload() {
    PalettePayload out;
    return !parsePalettePayload(std::vector<uint8_t>{3, 1, 2, 0xAA, 0xBB, 0xCC}, out);
}

bool maxPaletteFrameFits() {
    const size_t payloadLen = PALETTE_HEADER_LENGTH + 3 * MAX_PALETTE_COLORS;
    const size_t frameLen = HEADER_LENGTH + payloadLen + MAC_LENGTH;
    return payloadLen == 27 && frameLen == 59 && frameLen <= MAX_FRAME_LENGTH;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("round-trip 1 colour STEP", roundTripOneColorStep) ? 0 : 1;
    failures += runCase("round-trip 8 colours FADE", roundTripEightColorsFade) ? 0 : 1;
    failures += runCase("reject count=0", rejectCountZero) ? 0 : 1;
    failures += runCase("reject oversized 9 colours", rejectOversized) ? 0 : 1;
    failures += runCase("reject truncated payload", rejectTruncatedPayload) ? 0 : 1;
    failures += runCase("8-colour palette frame fits", maxPaletteFrameFits) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
