#pragma once

#include "../../utilities/gui_base/gui_base.h"

#include <array>
#include <cstdint>

namespace MOONCAKE
{
    namespace USER_APP
    {
        namespace PROP_TX
        {
            enum ViewField_t : uint8_t
            {
                VIEW_FIELD_LED = 0,
                VIEW_FIELD_HUE,
                VIEW_FIELD_MODE,
            };

            struct View_t
            {
                const char* action_label = "PREVIEW";
                const char* field_label = "LED";
                const char* status = "ready";
                char field_value[24] = "1";
                ViewField_t field = VIEW_FIELD_LED;
                bool command_mode = false;
                bool armed = false;
                bool awaiting_ack = false;
                uint8_t selected_led = 0;
                uint16_t selected_hue_degrees = 0;
                uint32_t shot_count = 0;
                uint32_t status_age_ms = 0;
                uint32_t arm_remaining_ms = 0;
                // 5 slots: dot 4 (index 4) is LED#5. The lower-ring dot renderer and the
                // _view() copy loop are count-driven off colors.size(), so the 5th dot draws
                // for free; the angle layout widens automatically via led_angle(i, count).
                std::array<std::array<uint8_t, 3>, 5> colors = {{
                    {255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {0, 128, 255}, {255, 255, 0}}};
            };
        }
    }
}

class GUI_PropTx : public GUI_Base
{
    public:
        void init() override;
        void renderPage(const MOONCAKE::USER_APP::PROP_TX::View_t& view);
};
