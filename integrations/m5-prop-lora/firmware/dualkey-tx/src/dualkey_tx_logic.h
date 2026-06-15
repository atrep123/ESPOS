#pragma once

#include <cstdint>

namespace dualkey_tx {

struct ButtonLevel {
    bool key1Pressed = false;
    bool key2Pressed = false;

    ButtonLevel() = default;
    ButtonLevel(bool key1, bool key2)
        : key1Pressed(key1), key2Pressed(key2) {}
};

enum class EventKind : std::uint8_t {
    None,
    BlueSet,
    BarrelEffect,
};

struct TxEvent {
    EventKind kind = EventKind::None;
    std::uint8_t value = 0;
    std::uint32_t eventId = 0;

    TxEvent() = default;
    TxEvent(EventKind eventKind, std::uint8_t eventValue, std::uint32_t id)
        : kind(eventKind), value(eventValue), eventId(id) {}
};

class DualKeyTxLogic {
public:
    explicit DualKeyTxLogic(std::uint32_t debounceMs = 25)
        : debounceMs_(debounceMs) {}

    TxEvent update(std::uint32_t nowMs, ButtonLevel level) {
        if (key1_.update(nowMs, level.key1Pressed)) {
            blueOn_ = !blueOn_;
            pendingBlue_ = true;
        }
        if (key2_.update(nowMs, level.key2Pressed)) {
            pendingBarrel_ = true;
        }
        return popPending();
    }

    bool blueOn() const { return blueOn_; }

private:
    class DebouncedKey {
    public:
        bool update(std::uint32_t nowMs, bool pressed) {
            if (pressed != raw_) {
                raw_ = pressed;
                rawChangedMs_ = nowMs;
                return false;
            }
            if (raw_ == stable_) {
                return false;
            }
            if (nowMs - rawChangedMs_ < debounceMs_) {
                return false;
            }
            stable_ = raw_;
            return stable_;
        }

        explicit DebouncedKey(std::uint32_t debounceMs = 25)
            : debounceMs_(debounceMs) {}

    private:
        std::uint32_t debounceMs_;
        std::uint32_t rawChangedMs_ = 0;
        bool raw_ = false;
        bool stable_ = false;
    };

    TxEvent popPending() {
        if (pendingBlue_) {
            pendingBlue_ = false;
            return TxEvent{EventKind::BlueSet,
                           static_cast<std::uint8_t>(blueOn_ ? 1 : 0),
                           nextEventId()};
        }
        if (pendingBarrel_) {
            pendingBarrel_ = false;
            return TxEvent{EventKind::BarrelEffect, 0, nextEventId()};
        }
        return TxEvent{};
    }

    std::uint32_t nextEventId() {
        ++eventCounter_;
        if (eventCounter_ == 0) {
            eventCounter_ = 1;
        }
        return eventCounter_;
    }

    std::uint32_t debounceMs_;
    DebouncedKey key1_{debounceMs_};
    DebouncedKey key2_{debounceMs_};
    bool blueOn_ = false;
    bool pendingBlue_ = false;
    bool pendingBarrel_ = false;
    std::uint32_t eventCounter_ = 0;
};

}  // namespace dualkey_tx
