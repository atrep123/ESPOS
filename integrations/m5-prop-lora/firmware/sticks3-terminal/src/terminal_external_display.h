#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string>

#include "terminal_setup.h"

namespace terminal_external_display {

constexpr std::size_t DISPLAY_ROW_COUNT = terminal_setup::LANE_COUNT;
constexpr std::uint8_t OLED_WIDTH_PX = 128;
constexpr std::uint8_t OLED_HEIGHT_PX = 64;
constexpr std::uint8_t OLED_FONT_WIDTH_PX = 6;
constexpr std::uint8_t OLED_FIRST_ROW_Y_PX = 2;
constexpr std::uint8_t OLED_ROW_HEIGHT_PX = 12;
constexpr std::size_t COLOR_TEXT_MAX_CHARS = 7;
constexpr std::size_t BRIGHTNESS_TEXT_MAX_CHARS = 4;
constexpr std::size_t EFFECT_TEXT_CHARS = 3;

struct DisplayRect {
    constexpr DisplayRect(std::uint8_t x = 0,
                          std::uint8_t y = 0,
                          std::uint8_t width = 0,
                          std::uint8_t height = 0)
        : xPx(x),
          yPx(y),
          widthPx(width),
          heightPx(height) {}

    std::uint8_t xPx = 0;
    std::uint8_t yPx = 0;
    std::uint8_t widthPx = 0;
    std::uint8_t heightPx = 0;
};

struct DisplayRowPlan {
    DisplayRect rowBox = {};
    DisplayRect laneBox = {};
    std::uint8_t laneTextX = 0;
    std::uint8_t laneTextY = 0;
    std::uint8_t colorTextX = 0;
    std::uint8_t colorTextY = 0;
    std::uint8_t brightnessTextX = 0;
    std::uint8_t brightnessTextY = 0;
    DisplayRect brightnessBarBox = {};
    DisplayRect effectBox = {};
    std::uint8_t effectTextX = 0;
    std::uint8_t effectTextY = 0;
};

struct DisplayRenderPlan {
    std::uint8_t widthPx = OLED_WIDTH_PX;
    std::uint8_t heightPx = OLED_HEIGHT_PX;
    std::uint8_t fontWidthPx = OLED_FONT_WIDTH_PX;
    std::uint8_t rowHeightPx = OLED_ROW_HEIGHT_PX;
    DisplayRect frameBox = {0, 0, OLED_WIDTH_PX, OLED_HEIGHT_PX};
    std::array<DisplayRowPlan, DISPLAY_ROW_COUNT> rows = {};
};

struct DisplayRow {
    std::uint8_t laneNumber = 0;
    std::string colorName = {};
    std::uint8_t brightnessPercent = 0;
    std::string brightnessLabel = {};
    bool on = false;
    bool effect = false;
    std::string effectLabel = {};
};

struct DisplayFrame {
    std::array<DisplayRow, DISPLAY_ROW_COUNT> rows = {};
};

inline bool operator==(const DisplayRect& lhs, const DisplayRect& rhs) {
    return lhs.xPx == rhs.xPx &&
           lhs.yPx == rhs.yPx &&
           lhs.widthPx == rhs.widthPx &&
           lhs.heightPx == rhs.heightPx;
}

inline bool operator!=(const DisplayRect& lhs, const DisplayRect& rhs) {
    return !(lhs == rhs);
}

inline bool operator==(const DisplayRow& lhs, const DisplayRow& rhs) {
    return lhs.laneNumber == rhs.laneNumber &&
           lhs.colorName == rhs.colorName &&
           lhs.brightnessPercent == rhs.brightnessPercent &&
           lhs.brightnessLabel == rhs.brightnessLabel &&
           lhs.on == rhs.on &&
           lhs.effect == rhs.effect &&
           lhs.effectLabel == rhs.effectLabel;
}

inline bool operator!=(const DisplayRow& lhs, const DisplayRow& rhs) {
    return !(lhs == rhs);
}

inline bool operator==(const DisplayFrame& lhs, const DisplayFrame& rhs) {
    return lhs.rows == rhs.rows;
}

inline bool operator!=(const DisplayFrame& lhs, const DisplayFrame& rhs) {
    return !(lhs == rhs);
}

inline std::uint8_t rectRight(const DisplayRect& rect) {
    return static_cast<std::uint8_t>(rect.xPx + rect.widthPx);
}

inline std::uint8_t rectBottom(const DisplayRect& rect) {
    return static_cast<std::uint8_t>(rect.yPx + rect.heightPx);
}

inline DisplayRowPlan rowPlan(std::size_t row) {
    const std::uint8_t y = static_cast<std::uint8_t>(OLED_FIRST_ROW_Y_PX + row * OLED_ROW_HEIGHT_PX);
    DisplayRowPlan plan;
    plan.rowBox = DisplayRect{0, y, OLED_WIDTH_PX, OLED_ROW_HEIGHT_PX};
    plan.laneBox = DisplayRect{3, y, 10, 11};
    plan.laneTextX = 5;
    plan.laneTextY = static_cast<std::uint8_t>(y + 2);
    plan.colorTextX = 15;
    plan.colorTextY = static_cast<std::uint8_t>(y + 2);
    plan.brightnessTextX = 60;
    plan.brightnessTextY = static_cast<std::uint8_t>(y + 2);
    plan.brightnessBarBox = DisplayRect{60, static_cast<std::uint8_t>(y + 9), 40, 3};
    plan.effectBox = DisplayRect{104, static_cast<std::uint8_t>(y + 1), 20, 10};
    plan.effectTextX = 105;
    plan.effectTextY = static_cast<std::uint8_t>(y + 2);
    return plan;
}

inline DisplayRenderPlan renderPlan() {
    DisplayRenderPlan plan;
    for (std::size_t row = 0; row < DISPLAY_ROW_COUNT; ++row) {
        plan.rows[row] = rowPlan(row);
    }
    return plan;
}

inline std::string brightnessLabel(const terminal_setup::LedLane& lane) {
    if (!lane.on) {
        return "VYP";
    }
    char out[BRIGHTNESS_TEXT_MAX_CHARS + 1] = {};
    std::snprintf(out, sizeof(out), "%u%%", static_cast<unsigned>(lane.brightness));
    return std::string(out);
}

inline DisplayRow makeRow(std::size_t lane, const terminal_setup::TerminalSetupState& setup) {
    const terminal_setup::LedLane& item = setup.draftLane(lane);
    const auto& color = terminal_setup::colorDefinitionFromHue(item.hue);
    DisplayRow row;
    row.laneNumber = static_cast<std::uint8_t>(lane + 1);
    row.colorName = color.name;
    row.brightnessPercent = item.brightness;
    row.brightnessLabel = brightnessLabel(item);
    row.on = item.on;
    row.effect = item.effect;
    row.effectLabel = item.effect ? "ODP" : "---";
    return row;
}

inline DisplayFrame makeFrame(const terminal_setup::TerminalSetupState& setup) {
    DisplayFrame frame;
    for (std::size_t lane = 0; lane < DISPLAY_ROW_COUNT; ++lane) {
        frame.rows[lane] = makeRow(lane, setup);
    }
    return frame;
}

static_assert(COLOR_TEXT_MAX_CHARS * OLED_FONT_WIDTH_PX <= 42,
              "color field must fit its 42px display slot");
static_assert(BRIGHTNESS_TEXT_MAX_CHARS * OLED_FONT_WIDTH_PX <= 40,
              "brightness field must fit above its 40px bar");
static_assert(EFFECT_TEXT_CHARS * OLED_FONT_WIDTH_PX <= 23,
              "effect text must fit the right status box");
static_assert(OLED_FIRST_ROW_Y_PX + DISPLAY_ROW_COUNT * OLED_ROW_HEIGHT_PX <= OLED_HEIGHT_PX - 1,
              "display rows must fit 64px OLED height");

}  // namespace terminal_external_display
