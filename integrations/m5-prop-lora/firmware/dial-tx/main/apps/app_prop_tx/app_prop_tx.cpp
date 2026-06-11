#include "app_prop_tx.h"
#include "../common_define.h"
#include "prop_colors.h"
#include "prop_protocol.h"
#include "prop_tx_config.h"  // USER KNOBS (Marlin-style): UART pins, encoder/ARM/ACK/FF timings, protocol routing, factory palette. See that file's SECTION INDEX.

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_random.h"
#include "nvs.h"
#include "nvs_flash.h"

#ifndef DEBUG_HUD
#define DEBUG_HUD 0
#endif

#ifndef SELFTEST_FIRE
#define SELFTEST_FIRE 0   // production: Dial no longer auto-fires (was 1 for bench self-test)
#endif
#ifndef PROP_TX_ALLOW_SELFTEST_FIRE
#define PROP_TX_ALLOW_SELFTEST_FIRE 0
#endif
#if SELFTEST_FIRE && !PROP_TX_ALLOW_SELFTEST_FIRE
#error "SELFTEST_FIRE requires explicit bench-only PROP_TX_ALLOW_SELFTEST_FIRE=1"
#endif

#ifndef FIRE_MODE_FF
#define FIRE_MODE_FF 1
#endif

#if DEBUG_HUD || SELFTEST_FIRE
#include "esp_system.h"
#include "esp_timer.h"
#endif

#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

using namespace MOONCAKE::USER_APP;

namespace
{
    // All USER-TUNABLE knobs (UART pins/baud, encoder + ARM/ACK/FF timings,
    // touch zones, protocol routing, factory palette) now live in
    // prop_tx_config.h -- the single Marlin-style configuration header. Pull them
    // into this translation unit unqualified so the logic below reads unchanged.
    using namespace prop_tx_config;

    // The UART knobs in the header are plain ints (portable / no ESP-IDF types in
    // a config file). Re-expose them here as the strongly-typed handles the IDF
    // calls below expect (uart_port_t / gpio_num_t), with identical values.
    constexpr uart_port_t PROP_UART_PORT = static_cast<uart_port_t>(prop_tx_config::PROP_UART_PORT_NUM);
    constexpr gpio_num_t  PROP_UART_TX   = static_cast<gpio_num_t>(prop_tx_config::PROP_UART_TX_GPIO);
    constexpr gpio_num_t  PROP_UART_RX   = static_cast<gpio_num_t>(prop_tx_config::PROP_UART_RX_GPIO);

    // INTERNAL (kept out of the config header on purpose):
    //   PROP_NVS_*  -- NVS blob namespace + log tag (storage layout, not a knob)
    //   SHARED_KEY  -- the 16-byte HMAC secret (NEVER expose / move this)
    //   COMMAND_ACTIONS -- the action-cycle order is wired to the UI/enum below
    constexpr const char* PROP_NVS_NAMESPACE = "prop_tx";
    constexpr const char* PROP_NVS_TAG = "prop_tx_nvs";
    constexpr std::array<PROP_TX::Action_t, 6> COMMAND_ACTIONS = {
        PROP_TX::ACTION_PREVIEW,
        PROP_TX::ACTION_PING,
        PROP_TX::ACTION_STOP,
        PROP_TX::ACTION_LED3_ON,   // ON-only; sits next to STOP (STOP is the master clear for both)
        PROP_TX::ACTION_LED5_ON,
        PROP_TX::ACTION_ARM,
    };
#ifndef PROP_ALLOW_PROTOTYPE_SHARED_KEY
#define PROP_ALLOW_PROTOTYPE_SHARED_KEY 1
#endif
#if !PROP_ALLOW_PROTOTYPE_SHARED_KEY
#error "Release build requested while the prototype shared HMAC key is still compiled in"
#endif
    constexpr uint8_t SHARED_KEY[] = {
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};

#if SELFTEST_FIRE
    constexpr uint32_t SELFTEST_INTERVAL_MS = 700;
    constexpr uint32_t SELFTEST_MAX_SHOTS = 50;

    uint32_t selftestLastMs = 0;
    uint32_t selftestShots = 0;
    bool selftestActive = true;
#endif

#if DEBUG_HUD || SELFTEST_FIRE
    struct DebugHudStats
    {
        uint32_t lastRttMs = 0;
        uint32_t maxRttMs = 0;
        uint32_t fireCount = 0;
        uint32_t ackOkCount = 0;
        uint32_t ackTimeoutCount = 0;
        uint32_t loopMaxUs = 0;
        uint32_t loopLastShowMs = 0;
        const char* bootReason = "?";
        uint32_t minFreeHeap = 0xFFFFFFFF;
        uint32_t bootUntilMs = 0;
        char line[80] = {0};
    };

    DebugHudStats g_debug_hud;

    const char* reset_reason_name(esp_reset_reason_t reason)
    {
        switch (reason)
        {
            case ESP_RST_POWERON:
                return "POWERON";
            case ESP_RST_EXT:
                return "EXT";
            case ESP_RST_SW:
                return "SW";
            case ESP_RST_PANIC:
                return "PANIC";
            case ESP_RST_INT_WDT:
                return "INT_WDT";
            case ESP_RST_TASK_WDT:
                return "TASK_WDT";
            case ESP_RST_WDT:
                return "WDT";
            case ESP_RST_DEEPSLEEP:
                return "DEEPSLEEP";
            case ESP_RST_BROWNOUT:
                return "BROWNOUT";
            case ESP_RST_SDIO:
                return "SDIO";
            case ESP_RST_UNKNOWN:
            default:
                return "UNKNOWN";
        }
    }

    void record_debug_loop_stats(int64_t loopStartUs)
    {
        const uint32_t freeHeap = esp_get_free_heap_size();
        if (freeHeap < g_debug_hud.minFreeHeap)
        {
            g_debug_hud.minFreeHeap = freeHeap;
        }

        const int64_t deltaUs = esp_timer_get_time() - loopStartUs;
        if (deltaUs <= 0)
        {
            return;
        }

        const uint32_t deltaUs32 = deltaUs > 0xFFFFFFFFLL
            ? 0xFFFFFFFFUL
            : static_cast<uint32_t>(deltaUs);
        if (deltaUs32 > g_debug_hud.loopMaxUs)
        {
            g_debug_hud.loopMaxUs = deltaUs32;
        }
    }
#endif

#if DEBUG_HUD
    constexpr uint32_t DEBUG_HUD_BOOT_MS = 1500;
    constexpr uint32_t DEBUG_HUD_REFRESH_MS = 500;
    constexpr uint32_t DEBUG_HUD_MUTED = 0x6F7D86;

    void draw_debug_hud(LGFX_Sprite* canvas, const PROP_TX::Data_t& data)
    {
        if (canvas == nullptr)
        {
            return;
        }
#if !FIRE_MODE_FF
        (void)data;
#endif

        const uint32_t now = millis();
        canvas->setFont(&fonts::Font0);
        canvas->setTextSize(1);
        canvas->setTextColor(DEBUG_HUD_MUTED);

        if (g_debug_hud.bootUntilMs != 0 && now < g_debug_hud.bootUntilMs)
        {
            char boot[40] = {0};
            snprintf(boot, sizeof(boot), "BOOT: %s", g_debug_hud.bootReason);
            canvas->drawCenterString(boot, 120, 120 - canvas->fontHeight() / 2);
            g_debug_hud.loopMaxUs = 0;
            g_debug_hud.loopLastShowMs = now;
            canvas->pushSprite(0, 0);
            return;
        }

        if (g_debug_hud.line[0] == '\0' ||
            g_debug_hud.loopLastShowMs == 0 ||
            now - g_debug_hud.loopLastShowMs >= DEBUG_HUD_REFRESH_MS)
        {
#if FIRE_MODE_FF
            const uint32_t ratio = (data.ffSent == 0) ? 0 : (data.ffConfirmed * 100 / data.ffSent);
            snprintf(g_debug_hud.line, sizeof(g_debug_hud.line),
                     "DR%lu%% FF%lu/%lu Lm%lu",
                     static_cast<unsigned long>(ratio),
                     static_cast<unsigned long>(data.ffConfirmed),
                     static_cast<unsigned long>(data.ffSent),
                     static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000));
#else
            snprintf(g_debug_hud.line, sizeof(g_debug_hud.line),
                     "RTT%lu/%lums OK%lu TO%lu Lm%lu",
                     static_cast<unsigned long>(g_debug_hud.lastRttMs),
                     static_cast<unsigned long>(g_debug_hud.maxRttMs),
                     static_cast<unsigned long>(g_debug_hud.ackOkCount),
                     static_cast<unsigned long>(g_debug_hud.ackTimeoutCount),
                     static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000));
#endif
            g_debug_hud.loopMaxUs = 0;
            g_debug_hud.loopLastShowMs = now;
        }

        canvas->drawCenterString(g_debug_hud.line, 120, 226 - canvas->fontHeight() / 2);
        canvas->pushSprite(0, 0);
    }
#endif

    const char* action_to_label(PROP_TX::Action_t action)
    {
        switch (action)
        {
            case PROP_TX::ACTION_PREVIEW:
                return "PREVIEW";
            case PROP_TX::ACTION_ARM:
                return "ARM";
            case PROP_TX::ACTION_FIRE:
                return "ODPAL";
            case PROP_TX::ACTION_STOP:
                return "STOP";
            case PROP_TX::ACTION_PING:
                return "PING";
            case PROP_TX::ACTION_LED3_ON:
                return "LED3";
            case PROP_TX::ACTION_LED5_ON:
                return "LED5";
            default:
                return "?";
        }
    }

    int command_action_index(PROP_TX::Action_t action)
    {
        for (size_t i = 0; i < COMMAND_ACTIONS.size(); ++i)
        {
            if (COMMAND_ACTIONS[i] == action)
            {
                return static_cast<int>(i);
            }
        }
        return 0;
    }

    uint16_t wrap_hue(int value)
    {
        value %= HUE_MAX;
        if (value < 0)
        {
            value += HUE_MAX;
        }
        return static_cast<uint16_t>(value);
    }

    void set_color_from_hue(uint16_t hue, std::array<uint8_t, 3>& color)
    {
        hue %= HUE_MAX;
        const uint8_t c = 255;
        const uint8_t x = static_cast<uint8_t>(
            (255 * (60 - abs(static_cast<int>(hue % 120) - 60)) + 30) / 60);

        if (hue < 60)
        {
            color = {c, x, 0};
        }
        else if (hue < 120)
        {
            color = {x, c, 0};
        }
        else if (hue < 180)
        {
            color = {0, c, x};
        }
        else if (hue < 240)
        {
            color = {0, x, c};
        }
        else if (hue < 300)
        {
            color = {x, 0, c};
        }
        else
        {
            color = {c, 0, x};
        }
    }

    void bump_palette_rev(uint8_t& palette_rev)
    {
        palette_rev = static_cast<uint8_t>(palette_rev + 1);
        if (palette_rev == 0)
        {
            palette_rev = 1;
        }
    }

    uint16_t hue_from_rgb(const std::array<uint8_t, 3>& color)
    {
        const int red = color[0];
        const int green = color[1];
        const int blue = color[2];
        const int max_channel = (red > green) ? ((red > blue) ? red : blue) : ((green > blue) ? green : blue);
        const int min_channel = (red < green) ? ((red < blue) ? red : blue) : ((green < blue) ? green : blue);
        const int delta = max_channel - min_channel;
        if (delta == 0)
        {
            return 0;
        }

        int hue = 0;
        if (max_channel == red)
        {
            hue = (60 * (green - blue)) / delta;
        }
        else if (max_channel == green)
        {
            hue = 120 + (60 * (blue - red)) / delta;
        }
        else
        {
            hue = 240 + (60 * (red - green)) / delta;
        }
        return wrap_hue(hue);
    }

    bool color_has_hue(const std::array<uint8_t, 3>& color)
    {
        const bool white = color[0] == 255 && color[1] == 255 && color[2] == 255;
        const bool off = color[0] == 0 && color[1] == 0 && color[2] == 0;
        return !white && !off;
    }

    size_t color_preset_index(const std::array<uint8_t, 3>& color)
    {
        return static_cast<size_t>(prop_colors::nearestPresetIndex(color[0], color[1], color[2]));
    }

    bool rejected_ack_payload(const std::string& payload)
    {
        return payload == "NOT_ARMED" ||
               payload == "BAD_PAYLOAD" ||
               payload == "BAD_PALETTE" ||
               payload == "ERR";
    }

    std::array<std::array<uint8_t, 3>, 4> first4_colors(
        const std::array<std::array<uint8_t, 3>, 8>& src)
    {
        return {{src[0], src[1], src[2], src[3]}};
    }

    void nvs_init_once()
    {
        static bool inited = false;
        if (inited)
        {
            return;
        }

        esp_err_t ret = nvs_flash_init();
        // Both NEW_VERSION_FOUND and NO_FREE_PAGES are only recoverable by erasing the NVS
        // partition and re-initialising; a bare re-init on NO_FREE_PAGES just repeats the
        // same failure (the partition is still full/incompatible), leaving every nvs_open
        // failing. Erase once, then re-init for either case.
        if (ret == ESP_ERR_NVS_NEW_VERSION_FOUND || ret == ESP_ERR_NVS_NO_FREE_PAGES)
        {
            ESP_LOGW(PROP_NVS_TAG, "nvs init err %d, erasing + re-init", ret);
            const esp_err_t erase_ret = nvs_flash_erase();
            if (erase_ret == ESP_OK)
            {
                ret = nvs_flash_init();
            }
            else
            {
                ESP_LOGE(PROP_NVS_TAG, "nvs erase failed: %d", erase_ret);
            }
        }
        if (ret == ESP_OK)
        {
            inited = true;
        }
        else
        {
            ESP_LOGE(PROP_NVS_TAG, "nvs init failed: %d", ret);
        }
    }

    uint64_t make_session_nonce(uint32_t bootCount)
    {
        const uint64_t random32 = static_cast<uint64_t>(esp_random() & 0xFFFFFFFFu);
        return (static_cast<uint64_t>(bootCount) << 32) | random32;
    }

    bool retryable_frame(prop_protocol::FrameType frameType)
    {
        switch (frameType)
        {
            case prop_protocol::FrameType::Preview:
            case prop_protocol::FrameType::PaletteSet:
            case prop_protocol::FrameType::Ping:
            case prop_protocol::FrameType::Stop:
                return true;
            default:
                return false;
        }
    }
}

void PropTx::_set_status(const char* fmt, ...)
{
    if (fmt == nullptr)
    {
        return;
    }

    va_list args;
    va_start(args, fmt);
    vsnprintf(_data.status, sizeof(_data.status), fmt, args);
    va_end(args);
    _data.status_started_ms = millis();
}

void PropTx::_disarm()
{
    _data.armed = false;
    _data.armed_started_ms = 0;
    _data.last_arm_ack_pending = false;
    _data.arm_ack_deadline_ms = 0;
    if (_data.selected_action == PROP_TX::ACTION_FIRE)
    {
        // FIX self-arm (#8): park on PREVIEW (not ARM) after a fire/cancel, so a stray/phantom
        // encoder press lands on the harmless PREVIEW action instead of silently re-arming.
        _data.selected_action = PROP_TX::ACTION_PREVIEW;
    }
}

void PropTx::_cancel_to_safe()
{
    // A STOP already awaiting its ack is safety-critical (master-off): never tear down its
    // retry state, or a lost first STOP transmission could leave the receiver live. Keep the
    // pending STOP in flight (its ack-timeout retry continues), just refresh the local UI.
    if (_data.awaiting_ack && _data.pending_type == prop_protocol::FrameType::Stop)
    {
        _data.send_preview_after_palette_ack = false;
        _disarm();
        _set_status("CANCEL");
        return;
    }

    const bool receiver_may_be_armed = _data.armed || _data.last_arm_ack_pending;
    _data.awaiting_ack = false;
    _data.send_preview_after_palette_ack = false;
    if (receiver_may_be_armed)
    {
        _send_frame(prop_protocol::FrameType::Stop);
    }
    else
    {
        _clear_pending_ack_state();
    }
    _disarm();
    _set_status("CANCEL");
}

bool PropTx::_locked() const
{
    return _data.armed || _data.awaiting_ack || _data.last_arm_ack_pending;
}

bool PropTx::_is_command_mode() const
{
    return _data.mode == PROP_TX::MODE_COMMAND || _data.armed ||
           _data.awaiting_ack || _data.last_arm_ack_pending;
}

uint32_t PropTx::_arm_remaining_ms() const
{
    if (!_data.armed || _data.armed_started_ms == 0)
    {
        return 0;
    }

    const uint32_t elapsed = millis() - _data.armed_started_ms;
    if (elapsed >= ARM_WINDOW_MS)
    {
        return 0;
    }
    return ARM_WINDOW_MS - elapsed;
}

void PropTx::_load_settings()
{
    nvs_init_once();
    static bool bootCountLoaded = false;
    static uint32_t bootCountForBoot = 0;

    nvs_handle_t nvs;
    esp_err_t ret = nvs_open(PROP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (ret != ESP_OK)
    {
        _set_status("nvs load err %d", ret);
        return;
    }

    nvs_get_u32(nvs, "shots", &_data.shot_count);
    nvs_get_u32(nvs, "seq", &_data.sequence);
    uint8_t pal_fade = _data.palette_fade ? 1 : 0;
    if (nvs_get_u8(nvs, "palFade", &pal_fade) == ESP_OK)
    {
        _data.palette_fade = pal_fade != 0;
    }
    if (bootCountLoaded)
    {
        _data.session_boot_count = bootCountForBoot;
    }
    else
    {
        // Option A: per-boot RANDOM 32-bit epoch (top 32 bits of the nonce). No NVS
        // counter -> no monotonic ordering -> an erased/reflashed Dial can never be
        // rejected as "rollback" by the receiver (no brick). Generated once per boot
        // (static guard). Fixes the old 8-bit (1/256) epoch collision.
        uint32_t epoch = esp_random();
        if (epoch == 0) epoch = 1;   // nonzero: receiver treats 0 as "no session yet"
        _data.session_boot_count = epoch;
        bootCountForBoot = epoch;
        bootCountLoaded = true;
    }
    size_t color_size = sizeof(_data.colors);
    esp_err_t color_ret = nvs_get_blob(nvs, "colors", _data.colors.data(), &color_size);
    size_t hue_size = sizeof(_data.hues);
    esp_err_t hue_deg_ret = nvs_get_blob(nvs, "hueDeg", _data.hues.data(), &hue_size);
    if (hue_deg_ret != ESP_OK || hue_size != sizeof(_data.hues))
    {
        if (color_ret == ESP_OK && color_size == sizeof(_data.colors))
        {
            for (size_t i = 0; i < _data.hues.size(); ++i)
            {
                _data.hues[i] = hue_from_rgb(_data.colors[i]);
            }
        }
        else
        {
            hue_size = sizeof(_data.hues);
            nvs_get_blob(nvs, "hues", _data.hues.data(), &hue_size);
        }
    }
    for (size_t i = 0; i < _data.hues.size(); ++i)
    {
        _data.hues[i] = wrap_hue(_data.hues[i]);
    }
    if (color_ret != ESP_OK || color_size != sizeof(_data.colors))
    {
        _sync_colors_from_hues();
    }
    if (_data.selected_led >= PROP_TX_FIXED_LEDS)
    {
        _data.selected_led = static_cast<uint8_t>(PROP_TX_FIXED_LEDS - 1);
    }
    _data.armed = false;
    _data.armed_started_ms = 0;
    if (_data.sequence == 0)
    {
        _data.sequence = 1;
    }
    nvs_close(nvs);
}

void PropTx::_save_settings()
{
    nvs_init_once();

    nvs_handle_t nvs;
    esp_err_t ret = nvs_open(PROP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (ret != ESP_OK)
    {
        _set_status("nvs save err %d", ret);
        return;
    }

    nvs_erase_key(nvs, "armed");
    nvs_set_u32(nvs, "shots", _data.shot_count);
    nvs_set_u8(nvs, "palFade", _data.palette_fade ? 1 : 0);
    nvs_set_blob(nvs, "hueDeg", _data.hues.data(), sizeof(_data.hues));
    nvs_erase_key(nvs, "hues");
    nvs_set_blob(nvs, "colors", _data.colors.data(), sizeof(_data.colors));
    nvs_commit(nvs);
    nvs_close(nvs);
}

void PropTx::_save_sequence()
{
    nvs_init_once();

    nvs_handle_t nvs;
    esp_err_t ret = nvs_open(PROP_NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (ret != ESP_OK)
    {
        _set_status("seq save err %d", ret);
        return;
    }

    nvs_set_u32(nvs, "seq", _data.sequence);
    nvs_commit(nvs);
    nvs_close(nvs);
}

void PropTx::_sync_colors_from_hues()
{
    for (size_t i = 0; i < _data.hues.size(); ++i)
    {
        set_color_from_hue(_data.hues[i], _data.colors[i]);
    }
}

void PropTx::_uart_init()
{
    uart_config_t uart_config = {};
    uart_config.baud_rate = PROP_UART_BAUD;
    uart_config.data_bits = UART_DATA_8_BITS;
    uart_config.parity = UART_PARITY_DISABLE;
    uart_config.stop_bits = UART_STOP_BITS_1;
    uart_config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    uart_config.rx_flow_ctrl_thresh = 0;

    ESP_ERROR_CHECK(uart_param_config(PROP_UART_PORT, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(PROP_UART_PORT, PROP_UART_TX, PROP_UART_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    // 0.4 root-fix: idle-high both UART lines via internal pull-ups so the modem's RX
    // never samples our line as boot garbage, and our RX never samples a booting
    // modem's TX as garbage -- fixed at the source. (The flush below stays as a belt.)
    gpio_pullup_en(PROP_UART_TX);
    gpio_pullup_en(PROP_UART_RX);

    esp_err_t ret = uart_driver_install(PROP_UART_PORT, 512, 512, 0, nullptr, 0);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE)
    {
        _set_status("uart err %d", ret);
    }

    // Boot-garbage flush: pre-init pin noise accumulates in the modem's line buffer
    // until a '\n' arrives, at which point it parses [garbage]+[first command] as one
    // BAD_COMMAND -> the modem replies "ERR BAD_COMMAND" -> the Dial disarms. That
    // would corrupt the FIRST ARM/FIRE after boot. A leading newline terminates the
    // stale line so the first real command parses clean. (We are not armed at boot,
    // so the resulting ERR is a harmless no-op.)
    const char sync[] = "\n\n";
    uart_write_bytes(PROP_UART_PORT, sync, sizeof(sync) - 1);
    uart_flush_input(PROP_UART_PORT);
}

void PropTx::_init_chain_key()
{
    _data.chain_key_detected = _chain_key.begin();
    _data.chain_key_was_down = false;
    _data.chain_key_last_poll_ms = 0;

    if (!_data.chain_key_detected)
    {
        _set_status("FIRE KEY MISSING");
        return;
    }

    bool down = false;
    if (_chain_key.readPressed(&down))
    {
        _data.chain_key_was_down = down;
    }
}

void PropTx::_send_frame(prop_protocol::FrameType frameType)
{
    prop_protocol::Frame frame;
    frame.type = frameType;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_DESTINATION;
    frame.sequence = _data.sequence++;
    frame.nonce = make_session_nonce(_data.session_boot_count);

    if (frameType == prop_protocol::FrameType::Preview || frameType == prop_protocol::FrameType::Fire)
    {
        prop_protocol::encodeLedPayload(PROP_TX_LED_PAYLOAD_BRIGHTNESS, first4_colors(_data.colors), frame.payload);
    }

    std::vector<uint8_t> encoded;
    if (!prop_protocol::encodeFrame(frame, SHARED_KEY, sizeof(SHARED_KEY), encoded))
    {
        _set_status("ENCODE FAIL");
        return;
    }

    std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());

    // Preview is ephemeral + non-arming: send it fire-and-forget ("FF") like Arm/Fire so the
    // modem never enters WaitAck on it. Previously Preview used the ack-tracked "SEND" path,
    // which set awaiting_ack (locking the UI) + retried, while the sending modem waited for a
    // modem-level ACK that the receiver's best-effort "PREVIEW" reply never satisfied -> a
    // guaranteed "ERR ACK_TIMEOUT" on every preview. The receiver still applies the colours and
    // sends its "PREVIEW" ack; the Dial simply does not block on it (you SEE the overlay anyway).
    if (frameType == prop_protocol::FrameType::Preview)
    {
        const std::string ff_line = "FF " + hex + "\n";
        _data.tx_started_ms = millis();
        uart_write_bytes(PROP_UART_PORT, ff_line.data(), ff_line.size());
        _remember_ff_command(prop_protocol::FrameType::Preview, encoded);  // FF-retry-on-ERR
        _save_sequence();
        _set_status("NAHLED");
        return;
    }

    std::string line = "SEND " + hex + "\n";
    _data.pending_sequence = frame.sequence;
    _data.pending_nonce = frame.nonce;
    _data.pending_type = frame.type;
    _data.pending_encoded = encoded;
    _data.pending_retry_count = 0;
    _data.pending_deadline_ms = millis() + ACK_RETRY_TIMEOUT_MS;
    _data.pending_palette_rev = 0;
    _data.awaiting_ack = true;
    _data.tx_started_ms = millis();
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
#if DEBUG_HUD || SELFTEST_FIRE
    if (frameType == prop_protocol::FrameType::Fire)
    {
        ++g_debug_hud.fireCount;
    }
#endif
    _save_sequence();
    _set_status("ODESILAM");
}

#if FIRE_MODE_FF
void PropTx::_send_fire_burst()
{
    prop_protocol::Frame frame;
    frame.type = prop_protocol::FrameType::Fire;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_DESTINATION;
    frame.sequence = _data.sequence++;
    frame.nonce = make_session_nonce(_data.session_boot_count);
    prop_protocol::encodeLedPayload(PROP_TX_LED_PAYLOAD_BRIGHTNESS, first4_colors(_data.colors), frame.payload);

    _data.ff_encoded.clear();
    if (!prop_protocol::encodeFrame(frame, SHARED_KEY, sizeof(SHARED_KEY), _data.ff_encoded))
    {
        _set_status("ENCODE FAIL");
        return;
    }

    _data.pending_sequence = frame.sequence;
    _data.pending_nonce = frame.nonce;
    _data.pending_type = frame.type;

    std::string hex = prop_protocol::bytesToHex(_data.ff_encoded.data(), _data.ff_encoded.size());
    std::string line = "FF " + hex + "\n";
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    _remember_ff_command(prop_protocol::FrameType::Fire, _data.ff_encoded);
    _data.ff_copies_left = FF_REDUNDANCY - 1;
    _data.ff_next_ms = millis() + FF_JITTER_MIN_MS + (esp_random() % FF_JITTER_SPAN_MS);
    ++_data.ffSent;
    _data.ff_confirmed_this_burst = false;   // new event: not yet confirmed (dedupe the FIRE+DUP acks)
#if DEBUG_HUD || SELFTEST_FIRE
    ++g_debug_hud.fireCount;
#endif
    _save_sequence();
    _set_status("ODESLANO");
}
#endif

void PropTx::_send_arm(int copies)
{
    // Sprint A (0.1): tell the receiver to ARM. Fire is rejected by the receiver
    // unless it is locally ARMED, so this MUST reach it before a FIRE.
    // A2 (0.3): also used as a sparse dual-band ARM-heartbeat (copies=1) so the
    // receiver's ARM TTL is refreshed while the Dial stays armed; if the link dies
    // the receiver lapses to SAFE within the TTL. Dual-band (not ESP-NOW only) so a
    // long-range LoRa-only prop is still kept armed.
    prop_protocol::Frame frame;
    frame.type = prop_protocol::FrameType::Arm;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_DESTINATION;
    frame.sequence = _data.sequence++;
    frame.nonce = make_session_nonce(_data.session_boot_count);
    const bool track_arm_ack = !_data.armed;

    std::vector<uint8_t> encoded;
    if (!prop_protocol::encodeFrame(frame, SHARED_KEY, sizeof(SHARED_KEY), encoded))
    {
        _set_status("ENCODE FAIL");
        return;
    }

    if (track_arm_ack)
    {
        _data.last_arm_sequence = frame.sequence;
        _data.last_arm_nonce = frame.nonce;
        _data.last_arm_ack_pending = true;
        _data.arm_ack_deadline_ms = millis() + ACK_RETRY_TIMEOUT_MS;
    }

    // Fire-and-forget: do NOT set awaiting_ack (it must never block a following
    // FIRE). The receiver dedups duplicate copies by sequence and the modem
    // dual-bands each "FF" copy (LoRa + ESP-NOW).
    std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
    std::string line = "FF " + hex + "\n";
    if (copies < 1) copies = 1;
    for (int i = 0; i < copies; ++i)
        uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    _remember_ff_command(prop_protocol::FrameType::Arm, encoded);
    if (track_arm_ack)
    {
        _save_sequence();
    }
    // No NVS write on heartbeat: the per-boot RANDOM epoch (see _load_settings)
    // already forces a receiver replay-window reset on reboot, so the running
    // sequence need NOT be persisted every 5 s.
}

void PropTx::_send_remote_led(uint8_t mask)
{
    // ON-only remote latch for SK6812 #3 / #5. Fire-and-forget ("FF"), modeled on
    // _send_arm: it MUST NOT set awaiting_ack (no UI lock) and MUST NOT arm — it is a
    // status LED, independent of the pyro/ARM FSM. OFF travels ONLY as STOP (the acked,
    // order-dominant master clear), so a lost/dup ON can never strand an LED on.
    //
    // Refresh the palette first if it drifted, so the DinMeter holds the current colours
    // — including LED#5's slot (palette index 4) — before it lights anything. Mirrors the
    // FIRE path; LED#5's colour rides PaletteSet, never the 13-byte LED payload.
    // Always (re)send the palette before lighting a remote LED, even if palette_rev did not drift:
    // a freshly-flashed / NVS-wiped DinMeter (or a lost prior palette FF) would otherwise light
    // #3/#5 from its local default colour instead of the Dial's slot. PaletteSet is idempotent.
    _send_palette(false);

    prop_protocol::Frame frame;
    frame.type = prop_protocol::FrameType::RemoteLed;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_DESTINATION;
    frame.sequence = _data.sequence++;
    frame.nonce = make_session_nonce(_data.session_boot_count);
    if (!prop_protocol::encodeRemoteLedPayload(mask, frame.payload))
    {
        _set_status("ENCODE FAIL");
        return;
    }

    std::vector<uint8_t> encoded;
    if (!prop_protocol::encodeFrame(frame, SHARED_KEY, sizeof(SHARED_KEY), encoded))
    {
        _set_status("ENCODE FAIL");
        return;
    }

    std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
    std::string line = "FF " + hex + "\n";
    // 2 copies: idempotent ON tolerates loss/dup (RX dedups by sequence anyway).
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    _remember_ff_command(prop_protocol::FrameType::RemoteLed, encoded);  // FF-retry-on-ERR path
    _save_sequence();
    _set_status((mask & prop_protocol::REMOTE_LED_BIT_LED3) ? "LED3 ON" : "LED5 ON");
}

void PropTx::_send_palette(bool track_ack)
{
    prop_protocol::Frame frame;
    frame.type = prop_protocol::FrameType::PaletteSet;
    frame.keyId = PROP_KEY_ID;
    frame.source = PROP_SOURCE;
    frame.destination = PROP_DESTINATION;
    frame.sequence = _data.sequence++;
    frame.nonce = make_session_nonce(_data.session_boot_count);

    prop_protocol::PalettePayload pal;
    pal.paletteRev = _data.palette_rev;
    pal.fade = _data.palette_fade;
    pal.colors.assign(_data.colors.begin(), _data.colors.begin() + PROP_TX_FIXED_LEDS);

    if (!prop_protocol::encodePalettePayload(pal, frame.payload))
    {
        _set_status("PAL ENC FAIL");
        return;
    }

    std::vector<uint8_t> encoded;
    if (!prop_protocol::encodeFrame(frame, SHARED_KEY, sizeof(SHARED_KEY), encoded))
    {
        _set_status("PAL ENC FAIL");
        return;
    }

    std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
    std::string line = std::string(track_ack ? "SEND " : "FF ") + hex + "\n";
    if (track_ack)
    {
        _data.pending_sequence = frame.sequence;
        _data.pending_nonce = frame.nonce;
        _data.pending_type = frame.type;
        _data.pending_encoded = encoded;
        _data.pending_retry_count = 0;
        _data.pending_deadline_ms = millis() + ACK_RETRY_TIMEOUT_MS;
        _data.pending_palette_rev = _data.palette_rev;
        _data.awaiting_ack = true;
        _data.tx_started_ms = millis();
    }
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    if (track_ack)
    {
        _save_sequence();
        _set_status("ODESILAM");
    }
    else
    {
        // Do NOT advance last_sent_palette_rev here: an FF PaletteSet is unacked and may
        // be lost. Marking it "delivered" let a future FIRE skip palette resend and light
        // the receiver with stale colours. The rev only advances on a real PALETTE ack
        // (the ack-tracked SEND path); until then the palette stays dirty and FIRE/RemoteLed
        // keep (idempotently) re-sending it, which is the safe behaviour.
        _remember_ff_command(prop_protocol::FrameType::PaletteSet, encoded);
        _save_sequence();
    }
}

bool PropTx::_retry_pending_ack()
{
    if (!_data.awaiting_ack ||
        !retryable_frame(_data.pending_type) ||
        _data.pending_retry_count >= ACK_RETRY_MAX ||
        _data.pending_encoded.empty())
    {
        return false;
    }

    const std::string hex = prop_protocol::bytesToHex(_data.pending_encoded.data(), _data.pending_encoded.size());
    const std::string line = "SEND " + hex + "\n";
    ++_data.pending_retry_count;
    const uint32_t now = millis();
    _data.tx_started_ms = now;
    _data.pending_deadline_ms = now + ACK_RETRY_TIMEOUT_MS;
    _data.awaiting_ack = true;
    uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
    _set_status("RETRY ACK");
    return true;
}

void PropTx::_handle_ack_timeout()
{
    if (_retry_pending_ack())
    {
        return;
    }

    _data.awaiting_ack = false;
    _data.send_preview_after_palette_ack = false;
    _disarm();
    _set_status("NO ACK");
}

void PropTx::_clear_pending_ack_state()
{
    _data.awaiting_ack = false;
    _data.pending_sequence = 0;
    _data.pending_nonce = 0;
    _data.pending_type = prop_protocol::FrameType::Ping;
    _data.pending_encoded.clear();
    _data.pending_retry_count = 0;
    _data.pending_deadline_ms = 0;
    _data.pending_palette_rev = 0;
    _data.send_preview_after_palette_ack = false;
}

void PropTx::_remember_ff_command(prop_protocol::FrameType frameType, const std::vector<uint8_t>& encoded)
{
    // Push into the FF retry ring (newest overwrites the oldest only after the ring
    // fills). A multi-frame action (PaletteSet FF + RemoteLed FF) thus keeps BOTH, so
    // an uncorrelated ERR BUSY/DUTY retries every still-fresh frame instead of clobbering
    // the palette retry with the LED retry (which lit LED3/5 with stale colours).
    PROP_TX::Data_t::RecentFf& slot = _data.recent_ff[_data.recent_ff_next];
    slot.type = frameType;
    slot.encoded = encoded;
    slot.until_ms = millis() + RECENT_FF_COMMAND_MS;
    slot.retries_left = RECENT_FF_RETRIES;
    _data.recent_ff_next = (_data.recent_ff_next + 1) % PROP_TX::Data_t::RECENT_FF_SLOTS;
}

bool PropTx::_handle_recent_ff_error(const char* line)
{
    if (line == nullptr ||
        (strncmp(line, "ERR BUSY", 8) != 0 && strncmp(line, "ERR DUTY", 8) != 0))
    {
        return false;
    }

    // Modem ERR BUSY/DUTY is uncorrelated (no seq/nonce), so we cannot know which recent
    // FF it belongs to. Resend EVERY still-fresh FF that has a retry left: all FF frames
    // are idempotent on the receiver (deduped by sequence), so a redundant resend is
    // harmless, while missing the real loser would strand a stale-colour LED.
    const uint32_t now = millis();
    bool handled = false;
    for (PROP_TX::Data_t::RecentFf& slot : _data.recent_ff)
    {
        if (slot.until_ms == 0 || static_cast<int32_t>(now - slot.until_ms) > 0)
        {
            continue;   // empty or expired
        }
        if (slot.retries_left == 0 || slot.encoded.empty())
        {
            continue;
        }
        --slot.retries_left;
        handled = true;
        const std::string hex =
            prop_protocol::bytesToHex(slot.encoded.data(), slot.encoded.size());
        const std::string retry_line = "FF " + hex + "\n";
        uart_write_bytes(PROP_UART_PORT, retry_line.data(), retry_line.size());
#if FIRE_MODE_FF
        if (slot.type == prop_protocol::FrameType::Fire)
        {
            _data.ff_copies_left = FF_REDUNDANCY - 1;
            _data.ff_next_ms = now + FF_JITTER_MIN_MS + (esp_random() % FF_JITTER_SPAN_MS);
        }
#endif
    }

    if (!handled)
    {
        return false;   // no fresh FF to retry -> let the normal ERR path run
    }

    _set_status("%s", strncmp(line, "ERR DUTY", 8) == 0 ? "FF DUTY" : "FF BUSY");
    return true;
}

void PropTx::_poll_uart()
{
    uint8_t bytes[64] = {0};
    int read_count = uart_read_bytes(PROP_UART_PORT, bytes, sizeof(bytes), 0);
    for (int i = 0; i < read_count; ++i)
    {
        char c = static_cast<char>(bytes[i]);
        if (c == '\r')
        {
            continue;
        }
        if (c == '\n')
        {
            // A line that overflowed the buffer is unparseable; drop it whole rather than
            // feeding a truncated tail to _handle_modem_line (which would parse as a bogus
            // frame). The newline resyncs us to the next clean line.
            if (!_data.uart_line_overflow)
            {
                _data.uart_line[_data.uart_line_len] = '\0';
                if (_data.uart_line_len > 0)
                {
                    _handle_modem_line(_data.uart_line);
                }
            }
            _data.uart_line_len = 0;
            _data.uart_line_overflow = false;
            continue;
        }
        if (_data.uart_line_overflow)
        {
            continue;   // discard everything until the terminating newline
        }
        if (_data.uart_line_len + 1 < sizeof(_data.uart_line))
        {
            _data.uart_line[_data.uart_line_len++] = c;
        }
        else
        {
            // Out of room: mark overflow and discard the rest of this line. Do NOT reset
            // len to 0 mid-line (the old bug) -- that restarted accumulation and let the
            // tail be parsed as a standalone (corrupt) frame.
            _data.uart_line_overflow = true;
        }
    }
}

void PropTx::_handle_modem_line(const char* line)
{
    if (line == nullptr || line[0] == '\0')
    {
        return;
    }

    if (strncmp(line, "ERR ACK_TIMEOUT", 15) == 0)
    {
        // Only a timeout for a send we are actually tracking may disarm; a stray
        // timeout (e.g. for a fire-and-forget ARM heartbeat) must NOT drop the armed
        // state. The receiver's ARM TTL is the backstop if the link truly dies.
        if (!_data.awaiting_ack)
            return;
#if DEBUG_HUD || SELFTEST_FIRE
        if (_data.awaiting_ack)
        {
            ++g_debug_hud.ackTimeoutCount;
#if SELFTEST_FIRE && !FIRE_MODE_FF
            if (_data.pending_type == prop_protocol::FrameType::Fire)
            {
                printf("STAT TIMEOUT to=%lu max=%lu lm=%lu\n",
                       static_cast<unsigned long>(g_debug_hud.ackTimeoutCount),
                       static_cast<unsigned long>(g_debug_hud.maxRttMs),
                       static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000));
            }
#endif
        }
#endif
        _handle_ack_timeout();
        return;
    }

    if (strncmp(line, "ERR ", 4) == 0)
    {
        // Stray async modem error (ERR BUSY / RADIO_NOT_READY / BAD_FRAME) outside a
        // tracked send must NOT silently disarm the console; only fail an in-flight
        // tracked send. (Receiver ARM TTL lapses to SAFE if the link is genuinely dead.)
        if (!_data.awaiting_ack)
        {
            if (_handle_recent_ff_error(line))
            {
                return;
            }
            return;
        }
        _data.awaiting_ack = false;
        _data.send_preview_after_palette_ack = false;
        _disarm();
        _set_status("%.40s", line);
        return;
    }

    if (strncmp(line, "RX ", 3) == 0)
    {
        const char* hex = strrchr(line, ' ');
        if (hex == nullptr || *(hex + 1) == '\0')
        {
            _set_status("BAD ACK");
            return;
        }
        hex++;

        std::vector<uint8_t> encoded;
        prop_protocol::Frame decoded;
        if (!prop_protocol::hexToBytes(std::string(hex), encoded) ||
            !prop_protocol::decodeFrame(encoded.data(), encoded.size(), SHARED_KEY, sizeof(SHARED_KEY), decoded))
        {
            _set_status("RX IGNORED");
            return;
        }

        if (decoded.type == prop_protocol::FrameType::LedColorSet)
        {
            if (decoded.keyId != PROP_KEY_ID ||
                decoded.source != PROP_DESTINATION ||
                decoded.destination != PROP_SOURCE)
            {
                return;
            }
            if (decoded.payload.size() != prop_protocol::LED_PAYLOAD_LENGTH)
            {
                return;
            }
            if (_data.has_last_led_color_set &&
                decoded.sequence == _data.last_led_color_set_sequence &&
                decoded.nonce == _data.last_led_color_set_nonce)
            {
                return;
            }

            for (size_t i = 0; i < 4; ++i)
            {
                const size_t offset = 1 + i * 3;
                _data.colors[i][0] = decoded.payload[offset];
                _data.colors[i][1] = decoded.payload[offset + 1];
                _data.colors[i][2] = decoded.payload[offset + 2];
                _data.hues[i] = hue_from_rgb(_data.colors[i]);
            }
            _data.has_last_led_color_set = true;
            _data.last_led_color_set_sequence = decoded.sequence;
            _data.last_led_color_set_nonce = decoded.nonce;
            _save_settings();
            _set_status("BARVY SYNC");
            return;
        }

        const bool ack_route_matches =
            decoded.type == prop_protocol::FrameType::Ack &&
            decoded.keyId == PROP_KEY_ID &&
            decoded.source == PROP_DESTINATION &&
            decoded.destination == PROP_SOURCE;
        const std::string ack_payload(decoded.payload.begin(), decoded.payload.end());
        const bool pending_ack_matches =
            ack_route_matches &&
            decoded.sequence == _data.pending_sequence &&
            decoded.nonce == _data.pending_nonce;
        const bool ack_matches = pending_ack_matches && _ack_payload_matches(decoded);

        if (ack_route_matches &&
            _data.last_arm_ack_pending &&
            decoded.sequence == _data.last_arm_sequence &&
            decoded.nonce == _data.last_arm_nonce)
        {
            _data.last_arm_ack_pending = false;
            _data.arm_ack_deadline_ms = 0;
            if (ack_payload == "ARMED")
            {
                _data.armed = true;
                _data.armed_started_ms = millis();
                _data.mode = PROP_TX::MODE_COMMAND;
                _data.selected_action = PROP_TX::ACTION_FIRE;
                _data.armed_hb_ms = millis();
                _set_status("NABITO");
                return;
            }
            if (ack_payload == "LOCKOUT")
            {
                _disarm();
                _set_status("BLOKOVANO");
                return;
            }
            _disarm();
            _set_status("ARM FAIL");
            return;
        }

        if (ack_matches)
        {
#if FIRE_MODE_FF
            if (_data.pending_type == prop_protocol::FrameType::Fire && !_data.ff_confirmed_this_burst)
            {
                _data.ff_confirmed_this_burst = true;
                ++_data.ffConfirmed;
#if SELFTEST_FIRE
                printf("STAT ff_sent=%lu conf=%lu ratio=%lu lm=%lu\n",
                       static_cast<unsigned long>(_data.ffSent),
                       static_cast<unsigned long>(_data.ffConfirmed),
                       static_cast<unsigned long>(_data.ffSent ? _data.ffConfirmed * 100 / _data.ffSent : 0),
                       static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000));
#endif
                if (!_data.awaiting_ack)
                {
                    _set_status("POTVRZENO");
                    return;
                }
            }
#endif
        }

        if (pending_ack_matches && rejected_ack_payload(ack_payload))
        {
            _clear_pending_ack_state();
            _disarm();
            _set_status("ZAMITNUTO");
            return;
        }

        if (_data.awaiting_ack && ack_matches)
        {
#if DEBUG_HUD || SELFTEST_FIRE
            const uint32_t rtt = millis() - _data.tx_started_ms;
            g_debug_hud.lastRttMs = rtt;
            if (rtt > g_debug_hud.maxRttMs)
            {
                g_debug_hud.maxRttMs = rtt;
            }
            ++g_debug_hud.ackOkCount;
#if SELFTEST_FIRE
#if !FIRE_MODE_FF
            if (_data.pending_type == prop_protocol::FrameType::Fire)
            {
                printf("STAT rtt=%lu max=%lu ok=%lu to=%lu lm=%lu heap=%lu\n",
                       static_cast<unsigned long>(g_debug_hud.lastRttMs),
                       static_cast<unsigned long>(g_debug_hud.maxRttMs),
                       static_cast<unsigned long>(g_debug_hud.ackOkCount),
                       static_cast<unsigned long>(g_debug_hud.ackTimeoutCount),
                       static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000),
                       static_cast<unsigned long>(g_debug_hud.minFreeHeap));
            }
#endif
#endif
#endif
            const prop_protocol::FrameType acked_type = _data.pending_type;
            _data.awaiting_ack = false;
            if (acked_type == prop_protocol::FrameType::PaletteSet)
            {
                _data.last_sent_palette_rev = _data.pending_palette_rev;
            }
            else
            {
                _disarm();
            }
            _set_status("POTVRZENO");
            if (acked_type == prop_protocol::FrameType::PaletteSet &&
                _data.send_preview_after_palette_ack)
            {
                _data.send_preview_after_palette_ack = false;
                _send_frame(prop_protocol::FrameType::Preview);
            }
            return;
        }

        // Fire-and-forget sends (RemoteLed, FF Preview, FF PaletteSet) still draw a best-effort
        // ack from the receiver ("REMOTE"/"PREVIEW"/"PALETTE"), but they are not pending-tracked,
        // so they would otherwise fall through to a scary "RX OTHER" and clobber the just-set
        // operator status ("LED5 ON"/"NAHLED"/etc). Benignly consume these routed non-pending acks.
        if (ack_route_matches &&
            (ack_payload == "REMOTE" || ack_payload == "PREVIEW" || ack_payload == "PALETTE"))
            return;
        _set_status("RX OTHER");
        return;
    }

    _set_status("%.40s", line);
}

bool PropTx::_ack_payload_matches(const prop_protocol::Frame& ack) const
{
    const char* expected = nullptr;
    switch (_data.pending_type)
    {
        case prop_protocol::FrameType::Preview:
            expected = "PREVIEW";
            break;
        case prop_protocol::FrameType::Fire:
            expected = "FIRE";
            break;
        case prop_protocol::FrameType::Arm:
            expected = "ARMED";
            break;
        case prop_protocol::FrameType::Stop:
            expected = "STOP";
            break;
        case prop_protocol::FrameType::Ping:
        case prop_protocol::FrameType::Status:
            expected = "PONG";
            break;
        case prop_protocol::FrameType::PaletteSet:
            expected = "PALETTE";
            break;
        default:
            return false;
    }

    const std::string payload(ack.payload.begin(), ack.payload.end());
    return payload == expected || payload == "DUP";
}

void PropTx::_adjust_selected_field(int direction)
{
    if (direction == 0)
    {
        return;
    }

    if (_is_command_mode())
    {
        _adjust_selected_action(direction);
        return;
    }

    switch (_data.selected_field)
    {
        case PROP_TX::FIELD_LED:
        {
            int led = static_cast<int>(_data.selected_led) + direction;
            if (led < 0)
            {
                led = 0;
            }
            if (led >= PROP_TX_FIXED_LEDS)
            {
                led = PROP_TX_FIXED_LEDS - 1;
            }
            _data.selected_led = static_cast<uint8_t>(led);
            break;
        }

        case PROP_TX::FIELD_HUE:
        {
            int index = static_cast<int>(color_preset_index(_data.colors[_data.selected_led])) + direction;
            while (index < 0)
            {
                index += prop_colors::NUM_COLOR_PRESETS;
            }
            index %= prop_colors::NUM_COLOR_PRESETS;
            const prop_colors::ColorPreset& preset = prop_colors::COLOR_PRESETS[index];
            const std::array<uint8_t, 3> preset_color = {{preset.r, preset.g, preset.b}};
            _data.colors[_data.selected_led] = preset_color;
            if (color_has_hue(preset_color))
            {
                _data.hues[_data.selected_led] = hue_from_rgb(preset_color);
            }
            bump_palette_rev(_data.palette_rev);
            _save_settings();
            break;
        }

        case PROP_TX::FIELD_MODE:
            _data.palette_fade = !_data.palette_fade;
            bump_palette_rev(_data.palette_rev);
            _save_settings();
            break;

        default:
            break;
    }
}

void PropTx::_adjust_selected_action(int direction)
{
    int index = command_action_index(_data.selected_action) + direction;
    while (index < 0)
    {
        index += static_cast<int>(COMMAND_ACTIONS.size());
    }
    index %= static_cast<int>(COMMAND_ACTIONS.size());
    _data.selected_action = COMMAND_ACTIONS[index];
}

void PropTx::_next_field()
{
    switch (_data.selected_field)
    {
        case PROP_TX::FIELD_LED:
            _data.selected_field = PROP_TX::FIELD_HUE;
            break;
        case PROP_TX::FIELD_HUE:
            _data.selected_field = PROP_TX::FIELD_MODE;
            break;
        case PROP_TX::FIELD_MODE:
            _data.selected_field = PROP_TX::FIELD_LED;
            break;
        default:
            _data.selected_field = PROP_TX::FIELD_LED;
            break;
    }
}

void PropTx::_toggle_mode()
{
    if (_data.mode == PROP_TX::MODE_SETUP)
    {
        // Leaving colour setup -> land on PREVIEW and auto-send the colours (real
        // update). FIRE only triggers the effect; colours travel on this Preview.
        _data.mode = PROP_TX::MODE_COMMAND;
        _data.selected_action = PROP_TX::ACTION_PREVIEW;
        if (_data.palette_rev != _data.last_sent_palette_rev)
        {
            _data.send_preview_after_palette_ack = true;
            _send_palette();
            if (!_data.awaiting_ack)
            {
                _data.send_preview_after_palette_ack = false;
            }
        }
        else
        {
            _send_frame(prop_protocol::FrameType::Preview);
        }
    }
    else
    {
        _data.mode = PROP_TX::MODE_SETUP;
        _set_status("SETUP");
    }
}

void PropTx::_handle_back()
{
    // Touch BACK is a fallback for the encoder: cancel when armed, else toggle mode.
    if (_data.awaiting_ack || _data.armed || _data.last_arm_ack_pending)
    {
        _cancel_to_safe();
        return;
    }
    _toggle_mode();
}

bool PropTx::_poll_fire_button()
{
    if (!_data.chain_key_detected)
    {
        return false;
    }

    const uint32_t now = millis();
    if (_data.chain_key_last_poll_ms != 0 && now - _data.chain_key_last_poll_ms < CHAIN_KEY_POLL_MS)
    {
        return false;
    }
    _data.chain_key_last_poll_ms = now;

    bool down = false;
    if (!_chain_key.readPressed(&down))
    {
        return false;
    }

    const bool pressed = down && !_data.chain_key_was_down;
    _data.chain_key_was_down = down;

    if (!pressed)
    {
        return false;
    }

    if (_data.armed && !_data.awaiting_ack)
    {
        _run_selected_action(PROP_TX::ACTION_FIRE);
        return true;
    }

    return false;
}

void PropTx::_select_led_from_touch(int x)
{
    int led = (x - (PROP_TX_LED_START_X - PROP_TX_LED_SPACING / 2)) / PROP_TX_LED_SPACING;
    if (led < 0)
    {
        led = 0;
    }
    if (led > PROP_TX_FIXED_LEDS - 1)
    {
        led = PROP_TX_FIXED_LEDS - 1;   // 5 LEDs now: 5th dot is touch-selectable too
    }
    _data.selected_led = static_cast<uint8_t>(led);
    _data.selected_field = PROP_TX::FIELD_HUE;
    _set_status("LED %u BARVA", _data.selected_led + 1);
}

bool PropTx::_touch_in_action_button(int x, int y) const
{
    return x >= PROP_TX_ACTION_TOUCH_LEFT &&
           x <= PROP_TX_ACTION_TOUCH_RIGHT &&
           y >= PROP_TX_ACTION_TOUCH_TOP &&
           y <= PROP_TX_ACTION_TOUCH_BOTTOM;
}

bool PropTx::_touch_in_led_strip(int x, int y) const
{
    return x >= PROP_TX_LED_TOUCH_LEFT &&
           x <= PROP_TX_LED_TOUCH_RIGHT &&
           y >= PROP_TX_LED_TOUCH_TOP &&
           y <= PROP_TX_LED_TOUCH_BOTTOM;
}

void PropTx::_run_selected_action()
{
    _run_selected_action(_data.selected_action);
}

void PropTx::_run_selected_action(PROP_TX::Action_t action)
{
    if (_data.awaiting_ack)
    {
        _set_status("WAIT ACK");
        return;
    }

    switch (action)
    {
        case PROP_TX::ACTION_PREVIEW:
            _send_frame(prop_protocol::FrameType::Preview);
            break;

        case PROP_TX::ACTION_ARM:
            _data.mode = PROP_TX::MODE_COMMAND;
            _data.selected_action = PROP_TX::ACTION_ARM;
            _set_status("ARMING");
            _send_arm();                 // Sprint A: arm the RECEIVER, not just the Dial UI (2 copies)
            break;

        case PROP_TX::ACTION_FIRE:
            if (!_data.armed)
            {
                _set_status("ARM FIRST");
                break;
            }
            if (_data.palette_rev != _data.last_sent_palette_rev)
            {
                _send_palette(false);
            }
#if FIRE_MODE_FF
            _send_fire_burst();
#else
            _send_frame(prop_protocol::FrameType::Fire);
#endif
            _disarm();
            _data.shot_count++;
            _save_sequence();
            break;

        case PROP_TX::ACTION_STOP:
            _send_frame(prop_protocol::FrameType::Stop);
            _disarm();
            break;

        case PROP_TX::ACTION_PING:
            _send_frame(prop_protocol::FrameType::Ping);
            break;

        case PROP_TX::ACTION_LED3_ON:
            _send_remote_led(prop_protocol::REMOTE_LED_BIT_LED3);
            break;

        case PROP_TX::ACTION_LED5_ON:
            _send_remote_led(prop_protocol::REMOTE_LED_BIT_LED5);
            break;

        default:
            break;
    }
}

void PropTx::_render()
{
    _gui.renderPage(_view());
#if DEBUG_HUD
    draw_debug_hud(_data.hal == nullptr ? nullptr : _data.hal->canvas, _data);
#endif
}

PROP_TX::View_t PropTx::_view() const
{
    PROP_TX::View_t view;
    view.action_label = _action_label();
    view.field_label = _field_label();
    view.status = _data.status;
    view.command_mode = _is_command_mode();
    view.armed = _data.armed;
    view.awaiting_ack = _data.awaiting_ack || _data.last_arm_ack_pending;
    view.selected_led = _data.selected_led;
    view.selected_hue_degrees = _data.hues[_data.selected_led];
    view.shot_count = _data.shot_count;
    view.status_age_ms = (_data.status_started_ms == 0) ? STATUS_TOKEN_MS + 1 : (millis() - _data.status_started_ms);
    view.arm_remaining_ms = _arm_remaining_ms();
    for (size_t i = 0; i < view.colors.size(); ++i)
    {
        view.colors[i] = _data.colors[i];
    }
    switch (_data.selected_field)
    {
        case PROP_TX::FIELD_HUE:
            view.field = PROP_TX::VIEW_FIELD_HUE;
            break;
        case PROP_TX::FIELD_MODE:
            view.field = PROP_TX::VIEW_FIELD_MODE;
            break;
        case PROP_TX::FIELD_LED:
        default:
            view.field = PROP_TX::VIEW_FIELD_LED;
            break;
    }
    _field_value(view.field_value, sizeof(view.field_value));
    return view;
}

const char* PropTx::_action_label() const
{
    if (_data.armed)
    {
        return action_to_label(PROP_TX::ACTION_FIRE);
    }
    return action_to_label(_data.selected_action);
}

const char* PropTx::_field_label() const
{
    switch (_data.selected_field)
    {
        case PROP_TX::FIELD_LED:
            return "LED";
        case PROP_TX::FIELD_HUE:
            return "BARVA";
        case PROP_TX::FIELD_MODE:
            return "MODE";
        default:
            return "?";
    }
}

void PropTx::_field_value(char* buffer, size_t buffer_size) const
{
    if (buffer == nullptr || buffer_size == 0)
    {
        return;
    }

    switch (_data.selected_field)
    {
        case PROP_TX::FIELD_LED:
            snprintf(buffer, buffer_size, "%u", _data.selected_led + 1);
            break;
        case PROP_TX::FIELD_HUE:
        {
            const auto& c = _data.colors[_data.selected_led];
            snprintf(buffer, buffer_size, "%s", prop_colors::exactPresetName(c[0], c[1], c[2]));
            break;
        }
        case PROP_TX::FIELD_MODE:
            snprintf(buffer, buffer_size, "%s", _data.palette_fade ? "FADE" : "STEP");
            break;
        default:
            snprintf(buffer, buffer_size, "?");
            break;
    }
}

void PropTx::onSetup()
{
    setAppName("Prop TX");
    setAllowBgRunning(false);

    PROP_TX::Data_t default_data;
    _data = default_data;
    _data.hal = (HAL::HAL*)getUserData();
    if (_data.hal != nullptr)
    {
        _data.last_enc_count = _data.hal->encoder.getCount();
    }
    _data.status_started_ms = millis();
#if DEBUG_HUD || SELFTEST_FIRE
    g_debug_hud = DebugHudStats{};
#endif
}

void PropTx::onCreate()
{
    _log("onCreate");
#if DEBUG_HUD || SELFTEST_FIRE
    const char* bootReason = reset_reason_name(esp_reset_reason());
#endif
#if DEBUG_HUD
    g_debug_hud.bootReason = bootReason;
    g_debug_hud.bootUntilMs = millis() + DEBUG_HUD_BOOT_MS;
#endif
#if SELFTEST_FIRE
    selftestLastMs = 0;
    selftestShots = 0;
    selftestActive = true;
    printf("SELFTEST READY boot=%s\n", bootReason);
#endif
    // Bind the shared HAL canvas to our GUI. When launched from the Mooncake
    // launcher this is done by the launcher (getGui()->init); booting straight
    // into PropTx we must do it ourselves, otherwise renderPage() dereferences a
    // null canvas (LoadProhibited crash / boot loop). setCanvas (not init) avoids
    // the derived init() override hiding the base 2-arg overload.
    _gui.setCanvas(_data.hal->canvas, nullptr);
    _load_settings();
    _uart_init();
    _init_chain_key();
    _render();

    while (_data.hal->tp.isTouched())
    {
        delay(5);
    }
}

bool PropTx::_service_link_during_input_wait()
{
    bool needs_render = false;
    const uint32_t status_seen_ms = _data.status_started_ms;
    _poll_uart();
    if (_data.status_started_ms != status_seen_ms)
    {
        needs_render = true;
    }

    const uint32_t now = millis();
    if (_data.last_arm_ack_pending &&
        _data.arm_ack_deadline_ms != 0 &&
        static_cast<int32_t>(now - _data.arm_ack_deadline_ms) >= 0)
    {
        _data.last_arm_ack_pending = false;
        _data.arm_ack_deadline_ms = 0;
        _send_frame(prop_protocol::FrameType::Stop);
        _disarm();
        _set_status("ARM FAIL");
        needs_render = true;
    }

    if (_data.awaiting_ack && static_cast<int32_t>(now - _data.pending_deadline_ms) >= 0)
    {
        _handle_ack_timeout();
        needs_render = true;
    }

    if (_data.armed && millis() - _data.armed_hb_ms >= ARM_HEARTBEAT_MS)
    {
        _send_arm(1);
        _data.armed_hb_ms = millis();
        needs_render = true;
    }

#if FIRE_MODE_FF
    if (_data.ff_copies_left > 0 && millis() >= _data.ff_next_ms)
    {
        std::string hex = prop_protocol::bytesToHex(_data.ff_encoded.data(), _data.ff_encoded.size());
        std::string line = "FF " + hex + "\n";
        uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
        --_data.ff_copies_left;
        _data.ff_next_ms = millis() + FF_JITTER_MIN_MS + (esp_random() % FF_JITTER_SPAN_MS);
    }
#endif

    delay(5);
    return needs_render;
}

void PropTx::onRunning()
{
#if DEBUG_HUD || SELFTEST_FIRE
    const int64_t loopStartUs = esp_timer_get_time();
#endif
    bool needs_render = false;
    const uint32_t status_seen_ms = _data.status_started_ms;
    _poll_uart();
    if (_data.status_started_ms != status_seen_ms)
    {
        needs_render = true;
    }

    if (_poll_fire_button())
    {
        needs_render = true;
    }

    // A2 (0.3): ARM-heartbeat. While the Dial is armed, periodically refresh the
    // receiver's ARM (1 copy, dual-band). If the Dial powers off / link is jammed,
    // the heartbeat stops and the receiver lapses to SAFE within its TTL. A running
    // effect on the receiver completes regardless (it does not depend on _armed).
    if (_data.armed && millis() - _data.armed_hb_ms >= ARM_HEARTBEAT_MS)
    {
        _send_arm(1);
        _data.armed_hb_ms = millis();
    }

#if FIRE_MODE_FF
    if (_data.ff_copies_left > 0 && millis() >= _data.ff_next_ms)
    {
        std::string hex = prop_protocol::bytesToHex(_data.ff_encoded.data(), _data.ff_encoded.size());
        std::string line = "FF " + hex + "\n";
        uart_write_bytes(PROP_UART_PORT, line.data(), line.size());
        --_data.ff_copies_left;
        _data.ff_next_ms = millis() + FF_JITTER_MIN_MS + (esp_random() % FF_JITTER_SPAN_MS);
    }
#endif

#if SELFTEST_FIRE
    if (selftestActive)
    {
        const uint32_t now = millis();
#if FIRE_MODE_FF
        if (_data.ff_copies_left == 0 && now - selftestLastMs >= SELFTEST_INTERVAL_MS)
#else
        if (!_data.awaiting_ack && now - selftestLastMs >= SELFTEST_INTERVAL_MS)
#endif
        {
            selftestLastMs = now;
            _data.armed = true;
            _send_arm();   // Sprint A: receiver requires ARM before FIRE
            _run_selected_action(PROP_TX::ACTION_FIRE);
            ++selftestShots;
            printf("SELFTEST fire#%lu sent\n", static_cast<unsigned long>(selftestShots));
            if (SELFTEST_MAX_SHOTS != 0 && selftestShots >= SELFTEST_MAX_SHOTS)
            {
                selftestActive = false;
            }
            needs_render = true;
        }
    }
#endif

    const uint32_t input_now = millis();
    if (_data.encoder_render_pending &&
        _data.next_encoder_render_ms != 0 &&
        static_cast<int32_t>(input_now - _data.next_encoder_render_ms) >= 0)
    {
        _data.encoder_render_pending = false;
        _data.next_encoder_render_ms = input_now + ENCODER_RENDER_THROTTLE_MS;
        needs_render = true;
    }

    const int64_t enc_count = _data.hal->encoder.getCount();
    if (enc_count != _data.last_enc_count)
    {
        const int raw_delta = static_cast<int>(enc_count - _data.last_enc_count);
        _data.last_enc_count = enc_count;

        const uint32_t now = millis();
        _data.last_move_ms = now;
        _data.encoder_button_released_after_move = false;
        // Arm a hard click-suppress window keyed to wall-clock time, independent of the
        // debounced release state. The M5Dial's rotary contacts emit a brief button-line
        // glitch on rotation; relying only on encoder_button_released_after_move let that
        // glitch slip through if it debounced low mid-window. Any press handled before this
        // deadline is treated as rotation noise.
        _data.suppress_button_until_ms = now + ENCODER_BUTTON_QUIET_MS;
        if (_data.enc_accum != 0 && (now - _data.enc_last_count_ms) > ENCODER_IDLE_FLUSH_MS)
        {
            _data.enc_accum = 0;
        }
        if (_data.enc_accum != 0 && ((raw_delta > 0) != (_data.enc_accum > 0)))
        {
            _data.enc_accum = 0;
        }
        _data.enc_accum += raw_delta;
        _data.enc_last_count_ms = now;

        const int steps = _data.enc_accum / ENC_COUNTS_PER_DETENT;
        if (steps != 0)
        {
            _data.enc_accum -= steps * ENC_COUNTS_PER_DETENT;
            if (!_locked())
            {
                const int direction = (steps < 0) ? 1 : -1;  // match knob rotation to selection
                int remaining = abs(steps);
                while (remaining-- > 0)
                {
                    _adjust_selected_field(direction);
                }
                if (_data.next_encoder_render_ms == 0 ||
                    static_cast<int32_t>(now - _data.next_encoder_render_ms) >= 0)
                {
                    _data.next_encoder_render_ms = now + ENCODER_RENDER_THROTTLE_MS;
                    _data.encoder_render_pending = false;
                    needs_render = true;
                }
                else
                {
                    _data.encoder_render_pending = true;
                }
            }
        }
    }

    const bool encoder_button_released = _data.hal->encoder.btn.read();
    if (encoder_button_released && !_data.encoder_button_released_after_move)
    {
        _data.encoder_button_released_after_move = true;
    }
    if (!encoder_button_released)
    {
        const uint32_t now = millis();
        // Suppress when we are still inside the rotation quiet window (timestamp-based, so a
        // button-line glitch that debounces low mid-window is still caught). The old release-
        // flag condition is kept only as a secondary guard.
        const bool suppress_activation =
            (_data.suppress_button_until_ms != 0 &&
             static_cast<int32_t>(now - _data.suppress_button_until_ms) < 0) ||
            (!_data.encoder_button_released_after_move &&
             _data.last_move_ms != 0 &&
             (now - _data.last_move_ms) < ENCODER_BUTTON_QUIET_MS);
        if (_data.armed || _data.awaiting_ack || _data.last_arm_ack_pending)
        {
            // Armed/awaiting: cancel immediately on press (reliable physical-button
            // cancel, independent of the touch BACK zone).
            _cancel_to_safe();
            needs_render = true;
        }
        else if (suppress_activation)
        {
            // Drain this press but do not treat rotation-edge noise as a click.
        }
        else
        {
            const uint32_t press_start = millis();
            bool fired_long = false;
            while (!_data.hal->encoder.btn.read())
            {
                if (!fired_long && (millis() - press_start) >= ENCODER_LONG_PRESS_MS)
                {
                    // Fire the mode switch AT the threshold while still held (not on
                    // release): buzz + redraw give immediate feedback.
                    _toggle_mode();  // COMMAND<->SETUP; commits colours on leaving SETUP
                    _data.hal->buzz.tone(4000, 30);
                    _render();
                    fired_long = true;
                }
                needs_render = _service_link_during_input_wait() || needs_render;
            }
            if (!fired_long)
            {
                if (_data.mode == PROP_TX::MODE_COMMAND)
                {
                    _run_selected_action();
                }
                else
                {
                    _next_field();
                }
            }
            needs_render = true;
        }

        // Wait for a debounced release so a single physical press is never handled
        // twice (release bounces were re-triggering the long press).
        uint32_t stable_since = millis();
        while (millis() - stable_since < 50)
        {
            if (!_data.hal->encoder.btn.read())  // bounced back to pressed -> restart
            {
                stable_since = millis();
            }
            needs_render = _service_link_during_input_wait() || needs_render;
        }
        _data.encoder_button_released_after_move = true;
        // The press has been drained to a stable release; the rotation-noise window is over.
        // Clear the suppress deadline so a deliberate quick follow-up press is not eaten.
        _data.suppress_button_until_ms = 0;
    }

    if (_data.hal->tp.isTouched())
    {
        _data.hal->tp.update();
        int x = _data.hal->tp.getTouchPointBuffer().x;
        int y = _data.hal->tp.getTouchPointBuffer().y;
        if (y > 220)
        {
            _handle_back();
            needs_render = true;
        }
        else if (!_locked() && !_is_command_mode() && _touch_in_led_strip(x, y))
        {
            _select_led_from_touch(x);
            needs_render = true;
        }
        else if (!_locked() && _is_command_mode() && _touch_in_action_button(x, y))
        {
            _run_selected_action();
            needs_render = true;
        }
        else if (!_locked() && !_is_command_mode())
        {
            _next_field();
            needs_render = true;
        }

        while (_data.hal->tp.isTouched())
        {
            needs_render = _service_link_during_input_wait() || needs_render;
        }
    }

    if ((millis() - _data.last_status_ms) > 250)
    {
        const uint32_t now = millis();
        _data.last_status_ms = now;
        if (_data.last_arm_ack_pending &&
            _data.arm_ack_deadline_ms != 0 &&
            static_cast<int32_t>(now - _data.arm_ack_deadline_ms) >= 0)
        {
            // The ARM ack was lost, but the ARM itself may have reached the receiver (which
            // then stays armed until its ~12s TTL). Send STOP/master-off before clearing the
            // pending arm so we never leave the receiver silently armed. STOP is ack-tracked
            // (retries on its own), so clear the arm-pending flags first to avoid _send_frame
            // racing the stale arm state.
            _data.last_arm_ack_pending = false;
            _data.arm_ack_deadline_ms = 0;
            _send_frame(prop_protocol::FrameType::Stop);
            _disarm();
            _set_status("ARM FAIL");
            needs_render = true;
        }
        if (_data.awaiting_ack && static_cast<int32_t>(now - _data.pending_deadline_ms) >= 0)
        {
#if DEBUG_HUD || SELFTEST_FIRE
            ++g_debug_hud.ackTimeoutCount;
#if SELFTEST_FIRE && !FIRE_MODE_FF
            if (_data.pending_type == prop_protocol::FrameType::Fire)
            {
                printf("STAT TIMEOUT to=%lu max=%lu lm=%lu\n",
                       static_cast<unsigned long>(g_debug_hud.ackTimeoutCount),
                       static_cast<unsigned long>(g_debug_hud.maxRttMs),
                       static_cast<unsigned long>(g_debug_hud.loopMaxUs / 1000));
            }
#endif
#endif
            _handle_ack_timeout();
        }
        // Permanent ARM (Filip): no auto-disarm. ARM holds until FIRE (Chain Key)
        // or CANCEL (back), so the operator can arm and wait for an external cue.
        if (_data.armed || _data.awaiting_ack || _data.last_arm_ack_pending ||
            (_data.status_started_ms != 0 && now - _data.status_started_ms <= STATUS_TOKEN_MS + 300))
        {
            needs_render = true;
        }
    }

#if DEBUG_HUD
    {
        const uint32_t now = millis();
        if (g_debug_hud.loopLastShowMs == 0 ||
            now - g_debug_hud.loopLastShowMs >= DEBUG_HUD_REFRESH_MS)
        {
            needs_render = true;
        }
    }
#endif

    if (needs_render)
    {
        _render();
    }

#if DEBUG_HUD || SELFTEST_FIRE
    record_debug_loop_stats(loopStartUs);
#endif
}

void PropTx::onDestroy()
{
    _log("onDestroy");
    // If we are leaving the app while the receiver may be live (armed, an arm ack still
    // pending, or a tracked send in flight), push a STOP/master-off first so the receiver
    // does not stay armed until its TTL. _send_frame queues STOP over UART; we then block
    // for the TX FIFO to drain before deleting the driver (otherwise the bytes are lost).
    if (_data.armed || _data.last_arm_ack_pending || _data.awaiting_ack)
    {
        _send_frame(prop_protocol::FrameType::Stop);
        // Best-effort drain; 100 ms is ample for a ~50-byte line at 115200 baud.
        uart_wait_tx_done(PROP_UART_PORT, pdMS_TO_TICKS(100));
    }
    _disarm();
    _save_settings();
    _save_sequence();
    _chain_key.end();
    uart_driver_delete(PROP_UART_PORT);
}
