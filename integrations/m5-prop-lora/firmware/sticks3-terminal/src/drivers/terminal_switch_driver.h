#pragma once

#include <Arduino.h>

#include "../terminal_config.h"
#include "../terminal_switches.h"

namespace terminal_switch_driver {

class SwitchDriver {
   public:
    void begin() const {
        configureInput(terminal_config::UPLOAD_SWITCH_PIN);
        configureInput(terminal_config::SIM_FIRE_SWITCH_PIN);
    }

    terminal_switches::SwitchSnapshot read() const {
        terminal_switches::SwitchSnapshot snapshot;
        snapshot.uploadPressed = isPressed(terminal_config::UPLOAD_SWITCH_PIN);
        snapshot.simFirePressed = isPressed(terminal_config::SIM_FIRE_SWITCH_PIN);
        return snapshot;
    }

   private:
    static bool isConfigured(int pin) {
        return pin >= 0;
    }

    static void configureInput(int pin) {
        if (pin >= 0) {
            pinMode(pin, INPUT_PULLUP);
        }
    }

    static bool isPressed(int pin) {
        return pin >= 0 && digitalRead(pin) == LOW;
    }
};

}  // namespace terminal_switch_driver
