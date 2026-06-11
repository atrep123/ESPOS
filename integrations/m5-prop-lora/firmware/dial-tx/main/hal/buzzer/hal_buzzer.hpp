/**
 * @file hal_buzzer.hpp
 * @author Forairaaaaa
 * @brief 
 * @version 0.1
 * @date 2023-05-21
 * 
 * @copyright Copyright (c) 2023
 * 
 */
#pragma once
#include <stdint.h>
#include "../arduino/Tone.h"


namespace BUZZER {

    class BUZZER {
        private:
            uint8_t _pin;

        public:
            BUZZER() : _pin(15) {}

            inline void init(int8_t pin) { _pin = pin; }

            /* Wrap. Buzzer DISABLED (Filip): silence every buzz.tone() caller (encoder/button
               click feedback) at this single chokepoint -- no caller-thread sleep, no UART/radio
               code touched. noTone() still actively silences the LEDC pin. */
            inline void tone(unsigned int /*frequency*/, unsigned long /*duration*/ = 0) { ARDUINO::noTone(_pin); }
            inline void noTone() { ARDUINO::noTone(_pin); }

    };

}
