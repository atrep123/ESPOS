#include "ui_core.h"

static uint16_t ui_core_rgb565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r & 0xF8) << 8) |
           ((uint16_t)(g & 0xFC) << 3) |
           (uint16_t)(b >> 3);
}

void ui_core_init(ui_state_t *st)
{
    if (!st) {
        return;
    }

    st->bg = ui_core_rgb565(8, 8, 8);
    st->t = 0;
    st->btnA = 0;
    st->btnB = 0;
    st->btnC = 0;
    st->scene = UI_SCENE_HOME;
    st->metrics_free_heap = 0;
    st->metrics_min_free_heap = 0;
}

void ui_core_on_tick(ui_state_t *st)
{
    if (!st) {
        return;
    }

    st->t++;
}

void ui_core_on_button(ui_state_t *st, uint8_t id, bool pressed)
{
    if (!st) {
        return;
    }

    switch (id) {
        case 0: /* Button A: cycle scenes on press */
            st->btnA = pressed ? 1U : 0U;
            if (pressed) {
                st->scene = (ui_scene_t)((st->scene + 1) % UI_SCENE__COUNT);
            }
            break;
        case 1: /* Button B */
            st->btnB = pressed ? 1U : 0U;
            break;
        case 2: /* Button C */
            st->btnC = pressed ? 1U : 0U;
            break;
        default:
            break;
    }
}

void ui_core_on_rpc_bg(ui_state_t *st, uint32_t rgb)
{
    if (!st) {
        return;
    }

    uint8_t r = (uint8_t)((rgb >> 16) & 0xFF);
    uint8_t g = (uint8_t)((rgb >> 8) & 0xFF);
    uint8_t b = (uint8_t)(rgb & 0xFF);

    st->bg = ui_core_rgb565(r, g, b);
}
