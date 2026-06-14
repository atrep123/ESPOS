#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "terminal_color_definitions.h"
#include "terminal_setup_link.h"

namespace terminal_setup_apply {

struct Rgb {
    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;

    constexpr Rgb() = default;
    constexpr Rgb(std::uint8_t rr, std::uint8_t gg, std::uint8_t bb) : r(rr), g(gg), b(bb) {}
};

inline bool operator==(const Rgb& lhs, const Rgb& rhs) {
    return lhs.r == rhs.r && lhs.g == rhs.g && lhs.b == rhs.b;
}

inline bool operator!=(const Rgb& lhs, const Rgb& rhs) {
    return !(lhs == rhs);
}

struct AppliedLane {
    Rgb color = {};
    std::uint8_t brightness = 255;
    bool on = true;
    bool effect = false;
};

struct AppliedSetup {
    std::array<AppliedLane, terminal_setup_link::LANE_COUNT> lanes = {};
    std::uint8_t onMask = 0;
    std::uint8_t effectMask = 0;
    std::uint8_t effectPreviewMask = 0;
};

inline std::uint8_t percentToByte(std::uint8_t percent) {
    const std::uint16_t value = static_cast<std::uint16_t>(percent) * 255U + 50U;
    return static_cast<std::uint8_t>(value / 100U);
}

inline std::uint8_t hueSegmentValue(std::uint16_t x, bool rising) {
    const std::uint16_t value = rising ? x : static_cast<std::uint16_t>(60U - x);
    return static_cast<std::uint8_t>((static_cast<std::uint32_t>(value) * 255U + 30U) / 60U);
}

inline Rgb hueToRgb(std::uint16_t hue) {
    hue %= 360U;
    const std::uint16_t sector = hue / 60U;
    const std::uint16_t x = hue % 60U;
    switch (sector) {
        case 0: return Rgb{255, hueSegmentValue(x, true), 0};
        case 1: return Rgb{hueSegmentValue(x, false), 255, 0};
        case 2: return Rgb{0, 255, hueSegmentValue(x, true)};
        case 3: return Rgb{0, hueSegmentValue(x, false), 255};
        case 4: return Rgb{hueSegmentValue(x, true), 0, 255};
        default: return Rgb{255, 0, hueSegmentValue(x, false)};
    }
}

inline AppliedSetup applySetupCommand(const terminal_setup_link::SetupCommand& command) {
    AppliedSetup out;
    for (std::size_t i = 0; i < terminal_setup_link::LANE_COUNT; ++i) {
        const terminal_setup_link::Lane& in = command.lanes[i];
        const terminal_color_definitions::ColorDefinition& color =
            terminal_color_definitions::colorFromWireCode(in.hue);
        out.lanes[i].color = Rgb{color.rgb.r, color.rgb.g, color.rgb.b};
        out.lanes[i].brightness = percentToByte(in.brightness);
        out.lanes[i].on = in.on;
        out.lanes[i].effect = in.effect;
        if (in.on) {
            out.onMask |= static_cast<std::uint8_t>(1U << i);
        }
        if (in.effect) {
            out.effectMask |= static_cast<std::uint8_t>(1U << i);
            out.effectPreviewMask |= static_cast<std::uint8_t>(1U << i);
        }
    }
    return out;
}

}  // namespace terminal_setup_apply
