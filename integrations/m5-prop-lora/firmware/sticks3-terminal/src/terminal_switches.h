#pragma once

namespace terminal_switches {

struct SwitchSnapshot {
    bool uploadPressed = false;
    bool simFirePressed = false;
};

struct SwitchEvents {
    bool upload = false;
    bool simFire = false;
};

class SwitchEdgeTracker {
   public:
    SwitchEvents update(const SwitchSnapshot& snapshot) {
        SwitchEvents events;
        events.upload = snapshot.uploadPressed && !previousUploadPressed_;
        events.simFire = snapshot.simFirePressed && !previousSimFirePressed_;
        previousUploadPressed_ = snapshot.uploadPressed;
        previousSimFirePressed_ = snapshot.simFirePressed;
        return events;
    }

    void prime(const SwitchSnapshot& snapshot) {
        previousUploadPressed_ = snapshot.uploadPressed;
        previousSimFirePressed_ = snapshot.simFirePressed;
    }

    void reset() {
        prime({});
    }

   private:
    bool previousUploadPressed_ = false;
    bool previousSimFirePressed_ = false;
};

}  // namespace terminal_switches
