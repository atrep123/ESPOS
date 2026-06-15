#include "../sticks3-terminal/src/terminal_external_display.h"

#include <iostream>
#include <string>

namespace {

using terminal_external_display::DISPLAY_ROW_COUNT;
using terminal_external_display::renderPlan;
using terminal_external_display::makeFrame;
using terminal_setup::TerminalSetupState;

TerminalSetupState configuredState() {
    TerminalSetupState state;
    state.setBrightness(0, 0);
    state.setEffectLed(0, true);
    state.rotateHue(0, 6);
    state.setBrightness(1, 25);
    state.toggleOn(1);
    state.setBrightness(2, 50);
    state.setEffectLed(2, true);
    state.setBrightness(3, 75);
    state.toggleOn(3);
    state.rotateHue(4, -6);
    state.setBrightness(4, 100);
    state.setEffectLed(4, true);
    return state;
}

bool hasRow(const terminal_external_display::DisplayRow& row,
            std::uint8_t laneNumber,
            const char* colorName,
            std::uint8_t brightnessPercent,
            const char* brightnessLabel,
            bool on,
            bool effect,
            const char* effectLabel) {
    return row.laneNumber == laneNumber &&
           row.colorName == colorName &&
           row.brightnessPercent == brightnessPercent &&
           row.brightnessLabel == brightnessLabel &&
           row.on == on &&
           row.effect == effect &&
           row.effectLabel == effectLabel;
}

std::uint8_t right(const terminal_external_display::DisplayRect& rect) {
    return static_cast<std::uint8_t>(rect.xPx + rect.widthPx);
}

std::uint8_t bottom(const terminal_external_display::DisplayRect& rect) {
    return static_cast<std::uint8_t>(rect.yPx + rect.heightPx);
}

bool fiveFramedOperatorRowsExposeColorBrightnessAndEffect() {
    const auto frame = makeFrame(configuredState());
    return frame.rows.size() == DISPLAY_ROW_COUNT &&
           hasRow(frame.rows[0], 1, "TYRKYS", 0, "VYP", false, true, "ODP") &&
           hasRow(frame.rows[1], 2, "CERVENA", 26, "VYP", false, false, "---") &&
           hasRow(frame.rows[2], 3, "CERVENA", 50, "50%", true, true, "ODP") &&
           hasRow(frame.rows[3], 4, "MODRA", 76, "VYP", false, true, "ODP") &&
           hasRow(frame.rows[4], 5, "CERVENA", 100, "100%", true, true, "ODP");
}

bool rowsFitFramedDisplayFieldBudgets() {
    const auto frame = makeFrame(configuredState());
    for (const auto& row : frame.rows) {
        if (row.laneNumber < 1 || row.laneNumber > DISPLAY_ROW_COUNT) {
            return false;
        }
        if (row.colorName.empty() ||
            row.colorName.size() > terminal_external_display::COLOR_TEXT_MAX_CHARS) {
            return false;
        }
        if (row.brightnessLabel.empty() ||
            row.brightnessLabel.size() > terminal_external_display::BRIGHTNESS_TEXT_MAX_CHARS) {
            return false;
        }
        if (row.effectLabel.size() != terminal_external_display::EFFECT_TEXT_CHARS) {
            return false;
        }
    }
    return true;
}

bool renderPlanFits128x64PixelBudget() {
    const auto& plan = renderPlan();
    if (plan.widthPx != 128 || plan.heightPx != 64 || plan.rows.size() != DISPLAY_ROW_COUNT) {
        return false;
    }
    if (plan.frameBox.xPx != 0 || plan.frameBox.yPx != 0 ||
        plan.frameBox.widthPx != 128 || plan.frameBox.heightPx != 64) {
        return false;
    }
    for (std::size_t row = 0; row < plan.rows.size(); ++row) {
        const auto& rowPlan = plan.rows[row];
        if (rowPlan.rowBox.xPx != 0 ||
            rowPlan.rowBox.yPx != 2 + row * terminal_external_display::OLED_ROW_HEIGHT_PX ||
            rowPlan.rowBox.widthPx != 128 ||
            rowPlan.rowBox.heightPx != terminal_external_display::OLED_ROW_HEIGHT_PX) {
            return false;
        }
        if (right(rowPlan.rowBox) > plan.widthPx || bottom(rowPlan.rowBox) > plan.heightPx) {
            return false;
        }
        if (right(rowPlan.laneBox) >= rowPlan.colorTextX) {
            return false;
        }
        const std::uint8_t colorRight = static_cast<std::uint8_t>(
            rowPlan.colorTextX +
            terminal_external_display::COLOR_TEXT_MAX_CHARS * plan.fontWidthPx);
        if (colorRight >= rowPlan.brightnessTextX) {
            return false;
        }
        const std::uint8_t brightnessRight = static_cast<std::uint8_t>(
            rowPlan.brightnessTextX +
            terminal_external_display::BRIGHTNESS_TEXT_MAX_CHARS * plan.fontWidthPx);
        if (brightnessRight > rowPlan.brightnessBarBox.xPx + rowPlan.brightnessBarBox.widthPx) {
            return false;
        }
        if (right(rowPlan.brightnessBarBox) >= rowPlan.effectBox.xPx) {
            return false;
        }
        if (right(rowPlan.effectBox) > plan.widthPx || bottom(rowPlan.effectBox) > plan.heightPx) {
            return false;
        }
        const std::uint8_t effectTextRight = static_cast<std::uint8_t>(
            rowPlan.effectTextX +
            terminal_external_display::EFFECT_TEXT_CHARS * plan.fontWidthPx);
        if (effectTextRight > rowPlan.effectBox.xPx + rowPlan.effectBox.widthPx) {
            return false;
        }
        if (row > 0 && rowPlan.rowBox.yPx <= plan.rows[row - 1].rowBox.yPx) {
            return false;
        }
    }
    return true;
}

bool effectStateUsesInvertedTextWithoutFrame() {
    const auto& plan = renderPlan();
    for (const auto& rowPlan : plan.rows) {
        if (rowPlan.effectBox.xPx != 104 ||
            rowPlan.effectBox.yPx != rowPlan.rowBox.yPx + 1 ||
            rowPlan.effectBox.widthPx != 20 ||
            rowPlan.effectBox.heightPx != 10) {
            return false;
        }
        if (rowPlan.effectTextX != rowPlan.effectBox.xPx + 1 ||
            rowPlan.effectTextY != rowPlan.rowBox.yPx + 2) {
            return false;
        }
        if (rowPlan.effectBox.xPx < right(rowPlan.brightnessBarBox) + 4 ||
            right(rowPlan.effectBox) > plan.widthPx - 4) {
            return false;
        }
    }
    return true;
}

bool sideControlsKeepTwoPixelOuterGutter() {
    const auto& plan = renderPlan();
    for (const auto& rowPlan : plan.rows) {
        if (rowPlan.laneBox.xPx < 3) {
            return false;
        }
        if (right(rowPlan.effectBox) > plan.widthPx - 4) {
            return false;
        }
        if (rowPlan.laneTextX < rowPlan.laneBox.xPx ||
            rowPlan.colorTextX <= right(rowPlan.laneBox)) {
            return false;
        }
        if (rowPlan.effectTextX < rowPlan.effectBox.xPx ||
            right(rowPlan.effectBox) > plan.widthPx - 4) {
            return false;
        }
    }
    return true;
}

bool laneNumberBoxKeepsExtraRightAndBottomPadding() {
    const auto& plan = renderPlan();
    for (const auto& rowPlan : plan.rows) {
        if (rowPlan.laneBox.widthPx != 10 || rowPlan.laneBox.heightPx != 11) {
            return false;
        }
        if (rowPlan.laneTextX != rowPlan.laneBox.xPx + 2 ||
            rowPlan.laneTextY != rowPlan.laneBox.yPx + 2) {
            return false;
        }
        if (rowPlan.colorTextX < right(rowPlan.laneBox) + 2) {
            return false;
        }
        if (bottom(rowPlan.laneBox) > bottom(rowPlan.rowBox) - 1) {
            return false;
        }
    }
    return true;
}

bool rowGridIsBalancedAndTextBaselinesAreAligned() {
    const auto& plan = renderPlan();
    const auto& first = plan.rows.front();
    const auto& last = plan.rows.back();
    const std::uint8_t topInnerMargin = static_cast<std::uint8_t>(first.rowBox.yPx - 1);
    const std::uint8_t bottomInnerMargin =
        static_cast<std::uint8_t>((plan.heightPx - 1) - bottom(last.rowBox));
    if (topInnerMargin != bottomInnerMargin) {
        return false;
    }
    for (const auto& rowPlan : plan.rows) {
        if (rowPlan.laneBox.yPx != rowPlan.rowBox.yPx) {
            return false;
        }
        if (rowPlan.colorTextY != rowPlan.laneTextY ||
            rowPlan.brightnessTextY != rowPlan.colorTextY ||
            rowPlan.effectTextY != rowPlan.colorTextY) {
            return false;
        }
        if (rowPlan.effectBox.yPx + 1 != rowPlan.effectTextY ||
            rowPlan.effectBox.heightPx != 10) {
            return false;
        }
        if (bottom(rowPlan.brightnessBarBox) != bottom(rowPlan.rowBox)) {
            return false;
        }
    }
    return true;
}

bool frameEqualityDetectsVisibleLaneValueChanges() {
    TerminalSetupState state;
    const auto before = makeFrame(state);
    state.setBrightness(0, 45);
    const auto brightnessChanged = makeFrame(state);
    state.toggleOn(0);
    const auto powerChanged = makeFrame(state);
    state.setEffectLed(0, true);
    const auto effectChanged = makeFrame(state);
    state.rotateHue(0, 45);
    const auto colorChanged = makeFrame(state);
    return before == before &&
           before != brightnessChanged &&
           brightnessChanged != powerChanged &&
           powerChanged != effectChanged &&
           effectChanged != colorChanged;
}

bool frameOmitsStatusAndMenuText() {
    const auto frame = makeFrame(configuredState());
    const char* forbidden[] = {
        "TERMINAL", "NAHRANO", "PROBLEM", "MENU", "large display", "PRIPRAVEN"};
    for (const auto& row : frame.rows) {
        for (const char* word : forbidden) {
            if (row.colorName.find(word) != std::string::npos ||
                row.brightnessLabel.find(word) != std::string::npos ||
                row.effectLabel.find(word) != std::string::npos) {
                return false;
            }
        }
    }
    return true;
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("five framed operator rows expose color brightness and effect",
                        fiveFramedOperatorRowsExposeColorBrightnessAndEffect) ? 0 : 1;
    failures += runCase("rows fit framed display field budgets", rowsFitFramedDisplayFieldBudgets) ? 0 : 1;
    failures += runCase("render plan fits 128x64 pixel budget", renderPlanFits128x64PixelBudget) ? 0 : 1;
    failures += runCase("effect state uses inverted text without frame",
                        effectStateUsesInvertedTextWithoutFrame) ? 0 : 1;
    failures += runCase("side controls keep two pixel outer gutter",
                        sideControlsKeepTwoPixelOuterGutter) ? 0 : 1;
    failures += runCase("lane number box keeps extra right and bottom padding",
                        laneNumberBoxKeepsExtraRightAndBottomPadding) ? 0 : 1;
    failures += runCase("row grid is balanced and text baselines are aligned",
                        rowGridIsBalancedAndTextBaselinesAreAligned) ? 0 : 1;
    failures += runCase("frame equality detects visible lane value changes",
                        frameEqualityDetectsVisibleLaneValueChanges) ? 0 : 1;
    failures += runCase("frame omits status and menu text", frameOmitsStatusAndMenuText) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
