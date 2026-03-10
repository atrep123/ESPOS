#include "input.h"

#include <stddef.h>
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "display/ssd1363.h"
#include "display_config.h"
#include "input_config.h"
#include "kernel/msgbus.h"
#include "seesaw.h"

static const char *TAG = "input";

typedef struct {
    int pin;
    uint8_t id;
} input_btn_cfg_t;

typedef struct {
    int stable; /* raw gpio level */
    int last;   /* raw gpio level */
    int cnt;
} input_btn_state_t;

static int input_is_used_pin(int pin)
{
    return pin >= 0;
}

static int input_read_level(int pin)
{
    return gpio_get_level((gpio_num_t)pin) ? 1 : 0;
}

static int input_level_to_pressed(int level)
{
#if INPUT_ACTIVE_LOW
    return level == 0;
#else
    return level != 0;
#endif
}

static void input_publish_btn(uint8_t id, int pressed)
{
    msg_t m = {
        .topic = TOP_INPUT_BTN,
        .u.btn = {
            .id = id,
            .pressed = (uint8_t)(pressed ? 1 : 0),
        },
    };
    bus_publish(&m);
}

static void input_configure_pin(int pin)
{
    gpio_config_t c = {
        .pin_bit_mask = 1ULL << pin,
        .mode = GPIO_MODE_INPUT,
#if INPUT_ACTIVE_LOW
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
#else
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
#endif
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&c);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "gpio_config(pin=%d) failed: %s", pin, esp_err_to_name(err));
    }
}

static int input_has_encoder(void)
{
    return input_is_used_pin(INPUT_PIN_ENC_A) && input_is_used_pin(INPUT_PIN_ENC_B);
}

typedef struct {
    uint8_t raw_id;
    uint8_t press_id;
    uint8_t hold_id;
    int pressed;
    TickType_t press_tick;
    int hold_sent;
} input_hold_btn_t;

static void input_hold_btn_init(input_hold_btn_t *b, uint8_t raw_id, uint8_t press_id, uint8_t hold_id)
{
    if (b == NULL) {
        return;
    }
    b->raw_id = raw_id;
    b->press_id = press_id;
    b->hold_id = hold_id;
    b->pressed = 0;
    b->press_tick = 0;
    b->hold_sent = 0;
}

static void input_hold_btn_update(input_hold_btn_t *b, int pressed_now)
{
    if (b == NULL) {
        return;
    }

    if (pressed_now != b->pressed) {
        b->pressed = pressed_now ? 1 : 0;
        input_publish_btn(b->raw_id, b->pressed);
        if (b->pressed) {
            b->press_tick = xTaskGetTickCount();
            b->hold_sent = 0;
        } else {
            if (!b->hold_sent) {
                input_publish_btn(b->press_id, 1);
            }
            b->hold_sent = 0;
        }
    }

    if (b->pressed && !b->hold_sent) {
        TickType_t now = xTaskGetTickCount();
        if ((now - b->press_tick) >= pdMS_TO_TICKS(INPUT_ENC_HOLD_MS)) {
            input_publish_btn(b->hold_id, 1);
            b->hold_sent = 1;
        }
    }
}

static void input_encoder_group_ids(
    int group,
    uint8_t *raw_id,
    uint8_t *press_id,
    uint8_t *hold_id,
    uint8_t *cw_id,
    uint8_t *ccw_id
)
{
    switch (group) {
        case 0:
            *raw_id = INPUT_ID_ENC;
            *press_id = INPUT_ID_ENC_PRESS;
            *hold_id = INPUT_ID_ENC_HOLD;
            *cw_id = INPUT_ID_ENC_CW;
            *ccw_id = INPUT_ID_ENC_CCW;
            break;
        case 1:
            *raw_id = INPUT_ID_ENC2;
            *press_id = INPUT_ID_ENC2_PRESS;
            *hold_id = INPUT_ID_ENC2_HOLD;
            *cw_id = INPUT_ID_ENC2_CW;
            *ccw_id = INPUT_ID_ENC2_CCW;
            break;
        case 2:
            *raw_id = INPUT_ID_ENC3;
            *press_id = INPUT_ID_ENC3_PRESS;
            *hold_id = INPUT_ID_ENC3_HOLD;
            *cw_id = INPUT_ID_ENC3_CW;
            *ccw_id = INPUT_ID_ENC3_CCW;
            break;
        case 3:
            *raw_id = INPUT_ID_ENC4;
            *press_id = INPUT_ID_ENC4_PRESS;
            *hold_id = INPUT_ID_ENC4_HOLD;
            *cw_id = INPUT_ID_ENC4_CW;
            *ccw_id = INPUT_ID_ENC4_CCW;
            break;
        default:
            *raw_id = INPUT_ID_ENC5;
            *press_id = INPUT_ID_ENC5_PRESS;
            *hold_id = INPUT_ID_ENC5_HOLD;
            *cw_id = INPUT_ID_ENC5_CW;
            *ccw_id = INPUT_ID_ENC5_CCW;
            break;
    }
}

typedef struct {
    uint8_t active;
    uint8_t addr;
    uint8_t btn_pressed[6];
    int axis_x;
    int axis_y;
} input_seesaw_gamepad_t;

typedef struct {
    uint8_t active;
    uint8_t addr;
    uint8_t invert_dir;
    input_hold_btn_t btn;
    uint8_t cw_id;
    uint8_t ccw_id;
} input_seesaw_rotary_t;

typedef struct {
    uint8_t active;
    uint8_t addr;
    uint8_t invert_dir;
    uint8_t group_base; /* 0=ENC, 1=ENC2, ... */
    input_hold_btn_t btn[4];
    uint8_t cw_id[4];
    uint8_t ccw_id[4];
} input_seesaw_quad_t;

static int input_axis_update(int value, int center, int deadzone, int hyst, int *state)
{
    int s = *state;
    if (s < 0) {
        if (value >= (center - deadzone + hyst)) {
            s = 0;
        }
    } else if (s > 0) {
        if (value <= (center + deadzone - hyst)) {
            s = 0;
        }
    } else {
        if (value <= (center - deadzone)) {
            s = -1;
        } else if (value >= (center + deadzone)) {
            s = 1;
        }
    }
    int changed = (s != *state);
    *state = s;
    return changed;
}

static void input_publish_axis_lr(int old_s, int new_s)
{
    if (old_s == -1 && new_s != -1) input_publish_btn(INPUT_ID_LEFT, 0);
    if (old_s == 1 && new_s != 1) input_publish_btn(INPUT_ID_RIGHT, 0);
    if (new_s == -1 && old_s != -1) input_publish_btn(INPUT_ID_LEFT, 1);
    if (new_s == 1 && old_s != 1) input_publish_btn(INPUT_ID_RIGHT, 1);
}

static void input_publish_axis_ud(int old_s, int new_s)
{
    if (old_s == -1 && new_s != -1) input_publish_btn(INPUT_ID_UP, 0);
    if (old_s == 1 && new_s != 1) input_publish_btn(INPUT_ID_DOWN, 0);
    if (new_s == -1 && old_s != -1) input_publish_btn(INPUT_ID_UP, 1);
    if (new_s == 1 && old_s != 1) input_publish_btn(INPUT_ID_DOWN, 1);
}

static void __attribute__((unused)) input_seesaw_try_init_gamepad(input_seesaw_gamepad_t *gp)
{
#if !INPUT_SEESAW_ENABLE
    (void)gp;
    return;
#else
    if (gp == NULL) {
        return;
    }
    gp->active = 0;
    gp->addr = 0;
    for (size_t i = 0; i < sizeof(gp->btn_pressed); ++i) {
        gp->btn_pressed[i] = 0;
    }
    gp->axis_x = 0;
    gp->axis_y = 0;

    uint8_t hw = 0;
    for (int off = 0; off < INPUT_SEESAW_GAMEPAD_ADDR_COUNT; ++off) {
        uint8_t addr = (uint8_t)(INPUT_SEESAW_GAMEPAD_BASE_ADDR + off);
        if (seesaw_read_u8(addr, SEESAW_STATUS_BASE, SEESAW_STATUS_HW_ID, &hw) != ESP_OK) {
            continue;
        }
        if (!seesaw_hw_id_supported(hw)) {
            continue;
        }
        gp->active = 1;
        gp->addr = addr;
        break;
    }

    if (!gp->active) {
        return;
    }

    /* Button pins from Adafruit seesaw_gamepad_qt.py */
    const uint32_t mask =
        (1u << 6) |  /* X */
        (1u << 2) |  /* Y */
        (1u << 5) |  /* A */
        (1u << 1) |  /* B */
        (1u << 0) |  /* SELECT */
        (1u << 16);  /* START */
    esp_err_t seerr = seesaw_pin_mode_bulk(gp->addr, mask, SEESAW_PIN_INPUT_PULLUP);
    if (seerr != ESP_OK) {
        ESP_LOGW(TAG, "seesaw gamepad pin_mode_bulk failed: %s", esp_err_to_name(seerr));
    }
    ESP_LOGI("input", "Seesaw gamepad detected at 0x%02X", (unsigned)gp->addr);
#endif
}

static void __attribute__((unused)) input_seesaw_try_init_rotary(input_seesaw_rotary_t *rot)
{
#if !INPUT_SEESAW_ENABLE
    (void)rot;
    return;
#else
    if (rot == NULL) {
        return;
    }
    rot->active = 0;
    rot->addr = 0;
    rot->invert_dir = (uint8_t)(INPUT_SEESAW_ROTARY_INVERT_DIR ? 1 : 0);
    rot->cw_id = INPUT_ID_ENC_CW;
    rot->ccw_id = INPUT_ID_ENC_CCW;
    input_hold_btn_init(&rot->btn, INPUT_ID_ENC, INPUT_ID_ENC_PRESS, INPUT_ID_ENC_HOLD);

    uint8_t hw = 0;
    if (seesaw_read_u8((uint8_t)INPUT_SEESAW_ROTARY_ADDR, SEESAW_STATUS_BASE, SEESAW_STATUS_HW_ID, &hw) != ESP_OK) {
        return;
    }
    if (!seesaw_hw_id_supported(hw)) {
        return;
    }
    rot->active = 1;
    rot->addr = (uint8_t)INPUT_SEESAW_ROTARY_ADDR;

    /* Button pin from Adafruit seesaw_rotary_simpletest.py */
    esp_err_t seerr = seesaw_pin_mode_bulk(rot->addr, (1u << 24), SEESAW_PIN_INPUT_PULLUP);
    if (seerr != ESP_OK) {
        ESP_LOGW(TAG, "seesaw rotary pin_mode_bulk failed: %s", esp_err_to_name(seerr));
    }
    ESP_LOGI("input", "Seesaw rotary detected at 0x%02X", (unsigned)rot->addr);
#endif
}

static void __attribute__((unused)) input_seesaw_try_init_quad(input_seesaw_quad_t *quad, uint8_t group_base)
{
#if !INPUT_SEESAW_ENABLE
    (void)quad;
    (void)group_base;
    return;
#else
    if (quad == NULL) {
        return;
    }
    quad->active = 0;
    quad->addr = 0;
    quad->invert_dir = (uint8_t)(INPUT_SEESAW_QUAD_INVERT_DIR ? 1 : 0);
    quad->group_base = group_base;

    uint8_t hw = 0;
    if (seesaw_read_u8((uint8_t)INPUT_SEESAW_QUAD_ADDR, SEESAW_STATUS_BASE, SEESAW_STATUS_HW_ID, &hw) != ESP_OK) {
        return;
    }
    if (!seesaw_hw_id_supported(hw)) {
        return;
    }
    quad->active = 1;
    quad->addr = (uint8_t)INPUT_SEESAW_QUAD_ADDR;

    const uint8_t pins[4] = { 12, 14, 17, 9 }; /* from Adafruit seesaw_quadrotary.py */
    uint32_t mask = 0;
    for (int i = 0; i < 4; ++i) {
        mask |= (1u << pins[i]);
    }
    esp_err_t seerr = seesaw_pin_mode_bulk(quad->addr, mask, SEESAW_PIN_INPUT_PULLUP);
    if (seerr != ESP_OK) {
        ESP_LOGW(TAG, "seesaw quad pin_mode_bulk failed: %s", esp_err_to_name(seerr));
    }

    for (int i = 0; i < 4; ++i) {
        uint8_t raw_id, press_id, hold_id, cw_id, ccw_id;
        input_encoder_group_ids((int)quad->group_base + i, &raw_id, &press_id, &hold_id, &cw_id, &ccw_id);
        input_hold_btn_init(&quad->btn[i], raw_id, press_id, hold_id);
        quad->cw_id[i] = cw_id;
        quad->ccw_id[i] = ccw_id;
    }

    ESP_LOGI("input", "Seesaw quad encoder detected at 0x%02X (group_base=%u)", (unsigned)quad->addr, (unsigned)quad->group_base);
#endif
}

static void input_seesaw_poll_gamepad(input_seesaw_gamepad_t *gp)
{
#if !INPUT_SEESAW_ENABLE
    (void)gp;
    return;
#else
    if (gp == NULL || !gp->active) {
        return;
    }

    uint32_t gpio = 0;
    if (seesaw_read_u32(gp->addr, SEESAW_GPIO_BASE, SEESAW_GPIO_BULK, &gpio) == ESP_OK) {
        const struct { uint8_t pin; uint8_t id; int idx; } map[] = {
            { 5, INPUT_ID_A, 0 },      /* A */
            { 1, INPUT_ID_B, 1 },      /* B */
            { 6, INPUT_ID_X, 2 },      /* X */
            { 2, INPUT_ID_Y, 3 },      /* Y */
            { 0, INPUT_ID_SELECT, 4 }, /* Select */
            { 16, INPUT_ID_START, 5 }, /* Start */
        };
        for (size_t i = 0; i < sizeof(map) / sizeof(map[0]); ++i) {
            int pressed = ((gpio & (1u << map[i].pin)) == 0u) ? 1 : 0; /* pullup -> active low */
            int idx = map[i].idx;
            if ((uint8_t)pressed != gp->btn_pressed[idx]) {
                gp->btn_pressed[idx] = (uint8_t)pressed;
                input_publish_btn(map[i].id, pressed);
            }
        }
    }

    uint16_t ax = 0;
    uint16_t ay = 0;
    if (seesaw_read_u16(gp->addr, SEESAW_ADC_BASE, (uint8_t)(SEESAW_ADC_CHANNEL_OFFSET + INPUT_GAMEPAD_JOY_X_PIN), &ax) != ESP_OK) {
        return;
    }
    if (seesaw_read_u16(gp->addr, SEESAW_ADC_BASE, (uint8_t)(SEESAW_ADC_CHANNEL_OFFSET + INPUT_GAMEPAD_JOY_Y_PIN), &ay) != ESP_OK) {
        return;
    }
    int x = (int)ax;
    int y = (int)ay;
#if INPUT_GAMEPAD_JOY_INVERT_X
    x = INPUT_GAMEPAD_JOY_MAX - x;
#endif
#if INPUT_GAMEPAD_JOY_INVERT_Y
    y = INPUT_GAMEPAD_JOY_MAX - y;
#endif

    int old_x = gp->axis_x;
    int old_y = gp->axis_y;
    (void)input_axis_update(x, INPUT_GAMEPAD_JOY_CENTER, INPUT_GAMEPAD_JOY_DEADZONE, INPUT_GAMEPAD_JOY_HYST, &gp->axis_x);
    (void)input_axis_update(y, INPUT_GAMEPAD_JOY_CENTER, INPUT_GAMEPAD_JOY_DEADZONE, INPUT_GAMEPAD_JOY_HYST, &gp->axis_y);
    if (old_x != gp->axis_x) {
        input_publish_axis_lr(old_x, gp->axis_x);
    }
    if (old_y != gp->axis_y) {
        input_publish_axis_ud(old_y, gp->axis_y);
    }
#endif
}

static void input_seesaw_poll_rotary(input_seesaw_rotary_t *rot)
{
#if !INPUT_SEESAW_ENABLE
    (void)rot;
    return;
#else
    if (rot == NULL || !rot->active) {
        return;
    }

    int32_t delta = 0;
    if (seesaw_read_i32(rot->addr, SEESAW_ENCODER_BASE, (uint8_t)(SEESAW_ENCODER_DELTA + 0), &delta) == ESP_OK) {
        if (rot->invert_dir) {
            delta = -delta;
        }
        if (delta > 0) {
            for (int i = 0; i < (int)delta; ++i) {
                input_publish_btn(rot->cw_id, 1);
            }
        } else if (delta < 0) {
            int steps = (int)(-delta);
            for (int i = 0; i < steps; ++i) {
                input_publish_btn(rot->ccw_id, 1);
            }
        }
    }

    uint32_t gpio = 0;
    if (seesaw_read_u32(rot->addr, SEESAW_GPIO_BASE, SEESAW_GPIO_BULK, &gpio) == ESP_OK) {
        int pressed = ((gpio & (1u << 24)) == 0u) ? 1 : 0; /* pullup -> active low */
        input_hold_btn_update(&rot->btn, pressed);
    } else {
        input_hold_btn_update(&rot->btn, rot->btn.pressed);
    }
#endif
}

static void input_seesaw_poll_quad(input_seesaw_quad_t *quad)
{
#if !INPUT_SEESAW_ENABLE
    (void)quad;
    return;
#else
    if (quad == NULL || !quad->active) {
        return;
    }

    static const uint8_t pins[4] = { 12, 14, 17, 9 };

    for (int n = 0; n < 4; ++n) {
        int32_t delta = 0;
        if (seesaw_read_i32(quad->addr, SEESAW_ENCODER_BASE, (uint8_t)(SEESAW_ENCODER_DELTA + n), &delta) != ESP_OK) {
            continue;
        }
        if (quad->invert_dir) {
            delta = -delta;
        }
        if (delta > 0) {
            for (int i = 0; i < (int)delta; ++i) {
                input_publish_btn(quad->cw_id[n], 1);
            }
        } else if (delta < 0) {
            int steps = (int)(-delta);
            for (int i = 0; i < steps; ++i) {
                input_publish_btn(quad->ccw_id[n], 1);
            }
        }
    }

    uint32_t gpio = 0;
    if (seesaw_read_u32(quad->addr, SEESAW_GPIO_BASE, SEESAW_GPIO_BULK, &gpio) == ESP_OK) {
        for (int n = 0; n < 4; ++n) {
            int pressed = ((gpio & (1u << pins[n])) == 0u) ? 1 : 0;
            input_hold_btn_update(&quad->btn[n], pressed);
        }
    } else {
        for (int n = 0; n < 4; ++n) {
            input_hold_btn_update(&quad->btn[n], quad->btn[n].pressed);
        }
    }
#endif
}

static void input_task(void *arg)
{
    (void)arg;

    const input_btn_cfg_t btns[] = {
        { INPUT_PIN_A, INPUT_ID_A },
        { INPUT_PIN_B, INPUT_ID_B },
        { INPUT_PIN_UP, INPUT_ID_UP },
        { INPUT_PIN_DOWN, INPUT_ID_DOWN },
        { INPUT_PIN_LEFT, INPUT_ID_LEFT },
        { INPUT_PIN_RIGHT, INPUT_ID_RIGHT },
        { INPUT_PIN_ENC_BTN, INPUT_ID_ENC },
    };
    input_btn_state_t st[sizeof(btns) / sizeof(btns[0])];

    for (size_t i = 0; i < sizeof(btns) / sizeof(btns[0]); ++i) {
        st[i].stable = 1;
        st[i].last = 1;
        st[i].cnt = 0;
        if (!input_is_used_pin(btns[i].pin)) {
            continue;
        }
        input_configure_pin(btns[i].pin);
        int v = input_read_level(btns[i].pin);
        st[i].stable = v;
        st[i].last = v;
    }

    if (input_has_encoder()) {
        input_configure_pin(INPUT_PIN_ENC_A);
        input_configure_pin(INPUT_PIN_ENC_B);
    }

#if INPUT_SEESAW_ENABLE
    input_seesaw_gamepad_t gp;
    input_seesaw_rotary_t rot;
    input_seesaw_quad_t quad;
    int seesaw_ready = 0;
    TickType_t last_i2c_poll = xTaskGetTickCount();

#if DISPLAY_I2C_SDA_GPIO >= 0 && DISPLAY_I2C_SCL_GPIO >= 0
    if (ssd1363_bus_init() == ESP_OK) {
        seesaw_ready = 1;
        input_seesaw_try_init_gamepad(&gp);
        input_seesaw_try_init_rotary(&rot);
        /* If a dedicated rotary is present, map quad encoders starting from ENC2. */
        uint8_t quad_base = (rot.active ? 1u : 0u);
        input_seesaw_try_init_quad(&quad, quad_base);
    } else {
        ESP_LOGW("input", "I2C bus init failed; seesaw inputs disabled");
        gp.active = 0;
        rot.active = 0;
        quad.active = 0;
    }
#else
    gp.active = 0;
    rot.active = 0;
    quad.active = 0;
#endif
#endif

    TickType_t enc_press_tick = 0;
    int enc_pressed = 0;
    int enc_hold_sent = 0;
    uint8_t enc_prev_ab = 0;
    int enc_accum = 0;

    if (input_has_encoder()) {
        int a = input_read_level(INPUT_PIN_ENC_A);
        int b = input_read_level(INPUT_PIN_ENC_B);
#if INPUT_ACTIVE_LOW
        a = a ? 0 : 1;
        b = b ? 0 : 1;
#endif
        enc_prev_ab = (uint8_t)((a << 1) | b);
    }

    while (1) {
        for (size_t i = 0; i < sizeof(btns) / sizeof(btns[0]); ++i) {
            int pin = btns[i].pin;
            if (!input_is_used_pin(pin)) {
                continue;
            }

            int v = input_read_level(pin);
            if (v != st[i].stable) {
                st[i].cnt += 1;
                if (st[i].cnt >= INPUT_DEBOUNCE_SAMPLES) {
                    st[i].stable = v;
                    st[i].cnt = 0;
                }
            } else {
                st[i].cnt = 0;
            }

            if (st[i].stable != st[i].last) {
                int pressed = input_level_to_pressed(st[i].stable);
                input_publish_btn(btns[i].id, pressed);

                if (btns[i].id == INPUT_ID_ENC) {
                    if (pressed) {
                        enc_pressed = 1;
                        enc_press_tick = xTaskGetTickCount();
                        enc_hold_sent = 0;
                    } else {
                        if (enc_pressed && !enc_hold_sent) {
                            input_publish_btn(INPUT_ID_ENC_PRESS, 1);
                        }
                        enc_pressed = 0;
                        enc_hold_sent = 0;
                    }
                }

                st[i].last = st[i].stable;
            }
        }

        if (enc_pressed && !enc_hold_sent) {
            TickType_t now = xTaskGetTickCount();
            TickType_t dt = now - enc_press_tick;
            if (dt >= pdMS_TO_TICKS(INPUT_ENC_HOLD_MS)) {
                input_publish_btn(INPUT_ID_ENC_HOLD, 1);
                enc_hold_sent = 1;
            }
        }

        if (input_has_encoder()) {
            static const int8_t trans[16] = {
                0, -1, +1, 0,
                +1, 0, 0, -1,
                -1, 0, 0, +1,
                0, +1, -1, 0,
            };
            int a = input_read_level(INPUT_PIN_ENC_A);
            int b = input_read_level(INPUT_PIN_ENC_B);
#if INPUT_ACTIVE_LOW
            a = a ? 0 : 1;
            b = b ? 0 : 1;
#endif
            uint8_t ab = (uint8_t)((a << 1) | b);
            uint8_t idx = (uint8_t)(((enc_prev_ab & 0x03) << 2) | (ab & 0x03));
            int8_t step = trans[idx];
            if (step != 0) {
                enc_accum += (int)step;
                enc_prev_ab = ab;
                if (enc_accum >= 4) {
                    input_publish_btn(INPUT_ID_ENC_CW, 1);
                    enc_accum = 0;
                } else if (enc_accum <= -4) {
                    input_publish_btn(INPUT_ID_ENC_CCW, 1);
                    enc_accum = 0;
                }
            } else {
                enc_prev_ab = ab;
            }
        }

#if INPUT_SEESAW_ENABLE
        if (seesaw_ready) {
            TickType_t now = xTaskGetTickCount();
            if ((now - last_i2c_poll) >= pdMS_TO_TICKS(INPUT_SEESAW_POLL_MS)) {
                last_i2c_poll = now;
                input_seesaw_poll_gamepad(&gp);
                input_seesaw_poll_rotary(&rot);
                input_seesaw_poll_quad(&quad);
            }
        }
#endif

        vTaskDelay(pdMS_TO_TICKS(INPUT_POLL_MS));
    }
}

void input_start(void)
{
    BaseType_t rc = xTaskCreatePinnedToCore(input_task, "in", 2048, NULL, 5, NULL, 0);
    if (rc != pdPASS) {
        ESP_LOGE(TAG, "input task creation failed");
    }
}
