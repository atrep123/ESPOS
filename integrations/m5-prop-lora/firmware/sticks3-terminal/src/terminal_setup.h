#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <string>

#include "../../../shared/terminal/terminal_color_definitions.h"
#include "../../../shared/terminal/terminal_setup_link.h"

namespace terminal_setup {

constexpr std::size_t LANE_COUNT = 5;
constexpr std::size_t OLED_LINE_MAX_CHARS = 21;
constexpr int ENCODER_DEGREES_PER_PALETTE_STEP = 6;

struct LedLane {
    constexpr LedLane() = default;
    constexpr LedLane(std::uint16_t colorCode,
                      std::uint8_t brightnessPercent,
                      bool enabled,
                      bool effectEnabled)
        : hue(colorCode),
          brightness(brightnessPercent),
          on(enabled),
          effect(effectEnabled) {}

    std::uint16_t hue = 0;
    std::uint8_t brightness = 100;
    bool on = true;
    bool effect = false;
};

inline bool operator==(const LedLane& lhs, const LedLane& rhs) {
    return lhs.hue == rhs.hue && lhs.brightness == rhs.brightness && lhs.on == rhs.on &&
           lhs.effect == rhs.effect;
}

inline bool operator!=(const LedLane& lhs, const LedLane& rhs) {
    return !(lhs == rhs);
}

enum class Status {
    Ready,
    Dirty,
    Uploading,
    Uploaded,
    Problem,
    SimFire,
};

inline std::uint8_t clampPercent(int value) {
    if (value < 0) return 0;
    if (value > 100) return 100;
    return static_cast<std::uint8_t>(value);
}

inline std::uint16_t wrapHue(int value) {
    int wrapped = value % 360;
    if (wrapped < 0) wrapped += 360;
    return static_cast<std::uint16_t>(wrapped);
}

inline const char* colorNameFromHue(std::uint16_t hue) {
    return terminal_color_definitions::colorFromWireCode(hue).name;
}

inline const terminal_color_definitions::ColorDefinition& colorDefinitionFromHue(
    std::uint16_t hue) {
    return terminal_color_definitions::colorFromWireCode(hue);
}

inline int paletteStepsFromEncoderDelta(int deltaDegrees) {
    if (deltaDegrees == 0) {
        return 0;
    }
    const int coarseSteps = deltaDegrees / ENCODER_DEGREES_PER_PALETTE_STEP;
    if (coarseSteps != 0) {
        return coarseSteps;
    }
    return deltaDegrees > 0 ? 1 : -1;
}

inline std::size_t wrapPaletteIndex(int value) {
    const int count = static_cast<int>(terminal_color_definitions::COLOR_COUNT);
    int wrapped = value % count;
    if (wrapped < 0) {
        wrapped += count;
    }
    return static_cast<std::size_t>(wrapped);
}

inline std::array<LedLane, LANE_COUNT> defaultLanes() {
    return {{
        LedLane{360, 100, true, false},
        LedLane{365, 100, true, false},
        LedLane{363, 100, true, false},
        LedLane{terminal_color_definitions::WHITE_WIRE_CODE, 100, true, false},
        LedLane{365, 100, true, false},
    }};
}

class TerminalSetupState {
   public:
    const LedLane& draftLane(std::size_t lane) const { return draft_[safeLane(lane)]; }
    const LedLane& savedLane(std::size_t lane) const { return saved_[safeLane(lane)]; }
    Status status() const { return status_; }
    bool dirty() const { return draft_ != saved_; }

    void setBrightness(std::size_t lane, int brightness) {
        if (!editableLane(lane)) return;
        const std::uint8_t next = clampPercent(brightness);
        const bool nextOn = next > 0;
        if (draft_[lane].brightness == next && draft_[lane].on == nextOn) return;
        draft_[lane].brightness = next;
        draft_[lane].on = nextOn;
        refreshDraftStatus();
    }

    void rotateHue(std::size_t lane, int deltaDegrees) {
        if (!editableLane(lane)) return;
        LedLane& target = draft_[lane];
        const int steps = paletteStepsFromEncoderDelta(deltaDegrees);
        if (steps == 0) return;
        const std::size_t currentIndex =
            terminal_color_definitions::colorIndexFromWireCode(target.hue);
        const std::uint16_t next =
            terminal_color_definitions::colorByIndex(
                wrapPaletteIndex(static_cast<int>(currentIndex) + steps)).wireCode;
        if (target.hue == next) return;
        target.hue = next;
        refreshDraftStatus();
    }

    void toggleOn(std::size_t lane) {
        if (!editableLane(lane)) return;
        LedLane& target = draft_[lane];
        target.on = !target.on;
        refreshDraftStatus();
    }

    void setEffectLed(std::size_t lane, bool enabled) {
        if (!editableLane(lane)) return;
        if (draft_[lane].effect == enabled) return;
        draft_[lane].effect = enabled;
        refreshDraftStatus();
    }

    void beginUpload() {
        uploadDraft_ = draft_;
        status_ = Status::Uploading;
    }

    void commitAccepted() {
        saved_ = uploadDraft_;
        draft_ = saved_;
        status_ = Status::Uploaded;
    }

    void commitRejected() {
        draft_ = saved_;
        uploadDraft_ = saved_;
        status_ = Status::Problem;
    }

    void markProblem() {
        status_ = Status::Problem;
    }

    void simulateFire() {
        if (status_ == Status::Uploading) return;
        status_ = Status::SimFire;
    }

    const char* statusText() const {
        switch (status_) {
            case Status::Ready:
                return "PRIPRAVEN";
            case Status::Dirty:
                return "ZMENY";
            case Status::Uploading:
                return "NAHRAVAM";
            case Status::Uploaded:
                return "NAHRANO";
            case Status::Problem:
                return "PROBLEM";
            case Status::SimFire:
                return "SIM FIRE";
        }
        return "PRIPRAVEN";
    }

    std::string largeDisplayLine(std::size_t lane) const {
        const std::size_t index = safeLane(lane);
        const LedLane& item = draft_[index];
        const auto& color = colorDefinitionFromHue(item.hue);
        char out[80] = {};
        std::snprintf(
            out,
            sizeof(out),
            "LED %u BARVA %s JAS %u%% ZAP %u ODP %u",
            static_cast<unsigned>(index + 1),
            color.name,
            static_cast<unsigned>(item.brightness),
            item.on ? 1U : 0U,
            item.effect ? 1U : 0U);
        return std::string(out);
    }

    std::string oledDisplayLine(std::size_t lane) const {
        const std::size_t index = safeLane(lane);
        const LedLane& item = draft_[index];
        const auto& color = colorDefinitionFromHue(item.hue);
        char out[OLED_LINE_MAX_CHARS + 1] = {};
        char brightness[5] = {};
        if (item.on) {
            std::snprintf(brightness, sizeof(brightness), "%u%%", static_cast<unsigned>(item.brightness));
        } else {
            std::snprintf(brightness, sizeof(brightness), "VYP");
        }
        std::snprintf(out,
                      sizeof(out),
                      "%u %s %s %s",
                      static_cast<unsigned>(index + 1),
                      color.name,
                      brightness,
                      item.effect ? "ODP" : "---");
        return std::string(out);
    }

    std::string uploadLine() const {
        return uploadLine(0);
    }

    std::string uploadLine(std::uint32_t requestId) const {
        terminal_setup_link::SetupCommand command;
        command.requestId = requestId;
        const std::array<LedLane, LANE_COUNT>& source =
            status_ == Status::Uploading ? uploadDraft_ : draft_;
        for (std::size_t i = 0; i < LANE_COUNT; ++i) {
            const LedLane& item = source[i];
            command.lanes[i].hue = terminal_color_definitions::canonicalWireCode(item.hue);
            command.lanes[i].brightness = item.brightness;
            command.lanes[i].on = item.on;
            command.lanes[i].effect = item.effect;
        }
        return terminal_setup_link::formatSetupLine(command);
    }

   private:
    static bool validLane(std::size_t lane) {
        return lane < LANE_COUNT;
    }

    bool editableLane(std::size_t lane) const {
        return validLane(lane) && status_ != Status::Uploading;
    }

    static std::size_t safeLane(std::size_t lane) {
        return lane < LANE_COUNT ? lane : LANE_COUNT - 1;
    }

    void refreshDraftStatus() {
        if (status_ != Status::Uploading && status_ != Status::Problem) {
            status_ = dirty() ? Status::Dirty : Status::Ready;
        }
    }

    std::array<LedLane, LANE_COUNT> saved_ = defaultLanes();
    std::array<LedLane, LANE_COUNT> draft_ = saved_;
    std::array<LedLane, LANE_COUNT> uploadDraft_ = saved_;
    Status status_ = Status::Ready;
};

}  // namespace terminal_setup
