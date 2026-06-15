#pragma once

#include <cstdint>

#include "terminal_setup.h"

namespace terminal_status_panel {

constexpr int FONT_BASE_WIDTH_PX = 6;
constexpr int FONT_BASE_HEIGHT_PX = 8;
constexpr int TITLE_TEXT_SIZE = 2;
constexpr int STATUS_TEXT_SIZE = 3;
constexpr int TEXT_GAP_PX = 8;

struct StatusPanelText {
    constexpr StatusPanelText() = default;
    constexpr StatusPanelText(const char* textValue, std::uint8_t textSizeValue, int xValue, int yValue)
        : text(textValue), textSize(textSizeValue), x(xValue), y(yValue) {}

    const char* text = "";
    std::uint8_t textSize = 1;
    int x = 0;
    int y = 0;
};

struct StatusPanelPlan {
    terminal_setup::Status status = terminal_setup::Status::Ready;
    int widthPx = 0;
    int heightPx = 0;
    StatusPanelText title = {};
    StatusPanelText statusLine = {};
};

struct StatusPanelCache {
    bool valid = false;
    terminal_setup::Status status = terminal_setup::Status::Ready;
    int widthPx = 0;
    int heightPx = 0;
};

inline int textLength(const char* text) {
    int count = 0;
    while (text != nullptr && text[count] != '\0') {
        ++count;
    }
    return count;
}

inline int textPixelWidth(const char* text, int textSize) {
    return textLength(text) * FONT_BASE_WIDTH_PX * textSize;
}

inline int textPixelHeight(int textSize) {
    return FONT_BASE_HEIGHT_PX * textSize;
}

inline int centeredX(const char* text, int textSize, int widthPx) {
    const int x = (widthPx - textPixelWidth(text, textSize)) / 2;
    return x < 0 ? 0 : x;
}

inline StatusPanelPlan makeStatusPanelPlan(terminal_setup::Status status,
                                           int widthPx,
                                           int heightPx) {
    const char* title = "TERMINAL";
    const char* statusText = terminal_setup::statusText(status);
    const int titleH = textPixelHeight(TITLE_TEXT_SIZE);
    const int statusH = textPixelHeight(STATUS_TEXT_SIZE);
    const int groupH = titleH + TEXT_GAP_PX + statusH;
    int groupY = (heightPx - groupH) / 2;
    if (groupY < 0) {
        groupY = 0;
    }

    StatusPanelPlan plan;
    plan.status = status;
    plan.widthPx = widthPx;
    plan.heightPx = heightPx;
    plan.title = StatusPanelText{
        title,
        TITLE_TEXT_SIZE,
        centeredX(title, TITLE_TEXT_SIZE, widthPx),
        groupY};
    plan.statusLine = StatusPanelText{
        statusText,
        STATUS_TEXT_SIZE,
        centeredX(statusText, STATUS_TEXT_SIZE, widthPx),
        groupY + titleH + TEXT_GAP_PX};
    return plan;
}

inline bool shouldDrawStatusPanel(const StatusPanelCache& cache,
                                  terminal_setup::Status status,
                                  int widthPx,
                                  int heightPx,
                                  bool force) {
    return force ||
           !cache.valid ||
           cache.status != status ||
           cache.widthPx != widthPx ||
           cache.heightPx != heightPx;
}

inline void rememberStatusPanelDraw(StatusPanelCache& cache,
                                    terminal_setup::Status status,
                                    int widthPx,
                                    int heightPx) {
    cache.valid = true;
    cache.status = status;
    cache.widthPx = widthPx;
    cache.heightPx = heightPx;
}

}  // namespace terminal_status_panel
