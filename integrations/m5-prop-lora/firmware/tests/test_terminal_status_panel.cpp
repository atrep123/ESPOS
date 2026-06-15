#include "../sticks3-terminal/src/terminal_status_panel.h"

#include <iostream>
#include <string>

namespace {

using terminal_setup::Status;
using terminal_status_panel::StatusPanelCache;
using terminal_status_panel::makeStatusPanelPlan;
using terminal_status_panel::rememberStatusPanelDraw;
using terminal_status_panel::shouldDrawStatusPanel;
using terminal_status_panel::textPixelHeight;
using terminal_status_panel::textPixelWidth;

bool statusPanelCentersTextInsideStickS3LandscapePixels() {
    const auto plan = makeStatusPanelPlan(Status::Uploaded, 240, 135);
    const int titleW = textPixelWidth(plan.title.text, plan.title.textSize);
    const int statusW = textPixelWidth(plan.statusLine.text, plan.statusLine.textSize);
    const int titleH = textPixelHeight(plan.title.textSize);
    const int statusH = textPixelHeight(plan.statusLine.textSize);
    const int groupTop = plan.title.y;
    const int groupBottom = plan.statusLine.y + statusH;
    const int groupCenter = (groupTop + groupBottom) / 2;

    return std::string(plan.title.text) == "TERMINAL" &&
           std::string(plan.statusLine.text) == "NAHRANO" &&
           plan.title.x == (240 - titleW) / 2 &&
           plan.statusLine.x == (240 - statusW) / 2 &&
           plan.title.y >= 0 &&
           plan.statusLine.y >= plan.title.y + titleH + 4 &&
           groupBottom <= 135 &&
           (groupCenter == 67 || groupCenter == 68);
}

bool statusPanelKeepsLongestStatusCenteredAndVisible() {
    const auto plan = makeStatusPanelPlan(Status::Uploading, 240, 135);
    const int statusW = textPixelWidth(plan.statusLine.text, plan.statusLine.textSize);
    const int statusH = textPixelHeight(plan.statusLine.textSize);
    return std::string(plan.statusLine.text) == "NAHRAVAM" &&
           plan.statusLine.x == (240 - statusW) / 2 &&
           plan.statusLine.x >= 0 &&
           plan.statusLine.x + statusW <= 240 &&
           plan.statusLine.y + statusH <= 135;
}

bool statusPanelCacheSuppressesUnchangedRedraws() {
    StatusPanelCache cache;
    if (!shouldDrawStatusPanel(cache, Status::Ready, 240, 135, false)) {
        return false;
    }
    rememberStatusPanelDraw(cache, Status::Ready, 240, 135);
    return !shouldDrawStatusPanel(cache, Status::Ready, 240, 135, false) &&
           shouldDrawStatusPanel(cache, Status::Dirty, 240, 135, false) &&
           shouldDrawStatusPanel(cache, Status::Ready, 241, 135, false) &&
           shouldDrawStatusPanel(cache, Status::Ready, 240, 135, true);
}

bool runCase(const char* name, bool (*test)()) {
    const bool passed = test();
    std::cout << (passed ? "PASS " : "FAIL ") << name << '\n';
    return passed;
}

}  // namespace

int main() {
    int failures = 0;
    failures += runCase("status panel centers text inside StickS3 landscape pixels",
                        statusPanelCentersTextInsideStickS3LandscapePixels) ? 0 : 1;
    failures += runCase("status panel keeps longest status centered and visible",
                        statusPanelKeepsLongestStatusCenteredAndVisible) ? 0 : 1;
    failures += runCase("status panel cache suppresses unchanged redraws",
                        statusPanelCacheSuppressesUnchangedRedraws) ? 0 : 1;
    return failures == 0 ? 0 : 1;
}
