#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace terminal_color_definitions {

struct ColorRgb {
    constexpr ColorRgb() = default;
    constexpr ColorRgb(std::uint8_t red, std::uint8_t green, std::uint8_t blue)
        : r(red), g(green), b(blue) {}

    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;
};

struct ColorDefinition {
    constexpr ColorDefinition() = default;
    constexpr ColorDefinition(const char* colorName, std::uint16_t colorWireCode, ColorRgb colorRgb)
        : name(colorName), wireCode(colorWireCode), rgb(colorRgb) {}

    const char* name = "CERVENA";
    std::uint16_t wireCode = 0;
    ColorRgb rgb = {};
};

constexpr std::size_t COLOR_COUNT = 9;
constexpr std::size_t DEFAULT_COLOR_INDEX = 0;
constexpr std::uint16_t NAMED_COLOR_CODE_BASE = 360;
constexpr std::uint16_t MAX_NAMED_COLOR_CODE =
    static_cast<std::uint16_t>(NAMED_COLOR_CODE_BASE + COLOR_COUNT - 1U);
constexpr std::uint16_t WHITE_WIRE_CODE = MAX_NAMED_COLOR_CODE;

constexpr std::array<ColorDefinition, COLOR_COUNT> COLORS = {{
    {"CERVENA", 360, {255, 0, 0}},
    {"ORANZ", 361, {255, 128, 0}},
    {"ZLUTA", 362, {255, 255, 0}},
    {"ZELENA", 363, {0, 255, 0}},
    {"TYRKYS", 364, {0, 255, 255}},
    {"MODRA", 365, {0, 0, 255}},
    {"FIALOVA", 366, {128, 0, 255}},
    {"RUZOVA", 367, {255, 0, 128}},
    {"BILA", WHITE_WIRE_CODE, {255, 255, 255}},
}};

inline std::uint16_t wrapLegacyHue(std::uint16_t hue) {
    return static_cast<std::uint16_t>(hue % 360U);
}

inline const ColorDefinition& colorByIndex(std::size_t index) {
    return COLORS[index % COLORS.size()];
}

inline std::uint16_t hueDistance(std::uint16_t lhs, std::uint16_t rhs) {
    const std::uint16_t high = lhs > rhs ? lhs : rhs;
    const std::uint16_t low = lhs > rhs ? rhs : lhs;
    const std::uint16_t direct = static_cast<std::uint16_t>(high - low);
    const std::uint16_t around = static_cast<std::uint16_t>(360U - direct);
    return direct < around ? direct : around;
}

inline bool isNamedColorCode(std::uint16_t code) {
    return code >= NAMED_COLOR_CODE_BASE && code <= MAX_NAMED_COLOR_CODE;
}

inline std::size_t colorIndexFromLegacyHue(std::uint16_t hue) {
    const std::uint16_t wrapped = wrapLegacyHue(hue);
    constexpr std::uint16_t LEGACY_HUES[COLOR_COUNT - 1] = {
        0, 30, 60, 120, 180, 240, 270, 300};
    for (std::size_t i = 0; i < COLORS.size(); ++i) {
        if (i < COLOR_COUNT - 1 && LEGACY_HUES[i] == wrapped) {
            return i;
        }
    }

    std::size_t best = DEFAULT_COLOR_INDEX;
    std::uint16_t bestDistance = 361;
    for (std::size_t i = 0; i < COLOR_COUNT - 1; ++i) {
        const std::uint16_t distance = hueDistance(wrapped, LEGACY_HUES[i]);
        if (distance < bestDistance) {
            best = i;
            bestDistance = distance;
        }
    }
    return best;
}

inline std::size_t colorIndexFromWireCode(std::uint16_t code) {
    if (isNamedColorCode(code)) {
        return static_cast<std::size_t>(code - NAMED_COLOR_CODE_BASE);
    }
    return colorIndexFromLegacyHue(code);
}

inline const ColorDefinition& colorFromWireCode(std::uint16_t code) {
    return colorByIndex(colorIndexFromWireCode(code));
}

inline std::uint16_t canonicalWireCode(std::uint16_t code) {
    return colorFromWireCode(code).wireCode;
}

}  // namespace terminal_color_definitions
