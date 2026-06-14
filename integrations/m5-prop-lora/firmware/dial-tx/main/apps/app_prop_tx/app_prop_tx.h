#pragma once

#include "../app.h"
#include "../../hal/hal.h"
#include "chain_key_poller.h"
#include "gui/gui_prop_tx.h"
#include "prop_protocol.h"
#include "prop_runtime_key.h"
#include "prop_tx_config.h"  // factory palette defaults (DEFAULT_COLORS / DEFAULT_HUES) seed Data_t below

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace MOONCAKE
{
    namespace USER_APP
    {
        namespace PROP_TX
        {
            enum Action_t : uint8_t
            {
                ACTION_PREVIEW = 0,
                ACTION_ARM,
                ACTION_FIRE,
                ACTION_STOP,
                ACTION_PING,
                ACTION_COUNT,
            };

            struct Data_t
            {
                HAL::HAL* hal = nullptr;
                Action_t selected_action = ACTION_PREVIEW;
                bool armed = false;
                // Keep the old 8-slot backing arrays for NVS compatibility; the UI and
                // transmitted palette are fixed to the five physical DinMeter LEDs
                // (PROP_TX_FIXED_LEDS; slot 4 = LED#5, lit remotely via RemoteLed).
                // Factory START values live ONCE in prop_tx_config.h ([B] DEFAULTS);
                // seeded here so a tweak there changes the power-on palette. NVS still
                // overrides both in _load_settings() on a saved device.
                std::array<uint16_t, 8> hues = prop_tx_config::DEFAULT_HUES;
                std::array<std::array<uint8_t, 3>, 8> colors = prop_tx_config::DEFAULT_COLORS;
                uint8_t palette_rev = 1;
                uint32_t last_sent_palette_rev = 0;  // 0 = jeste neposlano
                bool palette_fade = false;
                bool chain_key_detected = false;
                bool chain_key_was_down = false;
                uint32_t chain_key_last_poll_ms = 0;
                uint32_t session_boot_count = 0;
                uint32_t sequence = 1;
                uint32_t pending_sequence = 0;
                uint64_t pending_nonce = 0;
                prop_protocol::FrameType pending_type = prop_protocol::FrameType::Ping;
                std::vector<uint8_t> pending_encoded;
                uint8_t pending_retry_count = 0;
                uint32_t pending_deadline_ms = 0;
                uint8_t pending_palette_rev = 0;
                bool send_preview_after_palette_ack = false;
                uint32_t last_arm_sequence = 0;
                uint64_t last_arm_nonce = 0;
                bool last_arm_ack_pending = false;
                uint32_t arm_ack_deadline_ms = 0;
                bool has_last_led_color_set = false;
                uint32_t last_led_color_set_sequence = 0;
                uint64_t last_led_color_set_nonce = 0;
                bool has_last_palette_set = false;
                uint32_t last_palette_set_sequence = 0;
                uint64_t last_palette_set_nonce = 0;
                // FF retry FIFO. A single multi-frame action (e.g. RemoteLed sends a
                // PaletteSet FF then a RemoteLed FF) registers >1 FF in quick succession;
                // a single slot would let the later frame overwrite the earlier one, so an
                // ERR BUSY/DUTY for the PALETTE would retry the wrong (RemoteLed) frame and
                // light LED3/5 with stale colours. The ring keeps the last few FF frames so
                // _handle_recent_ff_error() resends ALL still-fresh ones (idempotent on RX).
                struct RecentFf
                {
                    prop_protocol::FrameType type = prop_protocol::FrameType::Ping;
                    std::vector<uint8_t> encoded;
                    uint32_t until_ms = 0;       // 0 = empty slot
                    uint8_t retries_left = 0;
                };
                static constexpr size_t RECENT_FF_SLOTS = 4;
                std::array<RecentFf, RECENT_FF_SLOTS> recent_ff{};
                size_t recent_ff_next = 0;       // ring write cursor
                int64_t last_enc_count = 0;
                int enc_accum = 0;
                uint32_t enc_last_count_ms = 0;
                uint32_t last_move_ms = 0;
                // Click-suppress deadline set on encoder rotation. Independent of the
                // debounced release state: any encoder press whose handling time is before
                // this deadline is rotation-edge noise and must be drained, not actioned.
                uint32_t suppress_button_until_ms = 0;
                bool encoder_button_released_after_move = true;
                bool encoder_render_pending = false;
                uint32_t next_encoder_render_ms = 0;
                uint32_t shot_count = 0;
                uint32_t last_status_ms = 0;
                uint32_t status_started_ms = 0;
                uint32_t tx_started_ms = 0;
                uint32_t armed_started_ms = 0;
                uint32_t armed_hb_ms = 0;   // A2: last ARM-heartbeat tx while armed (link-loss watchdog)
                bool awaiting_ack = false;
                uint8_t ff_copies_left = 0;
                uint32_t ff_next_ms = 0;
                std::vector<uint8_t> ff_encoded;
                uint32_t ffSent = 0;
                uint32_t ffConfirmed = 0;
                bool ff_confirmed_this_burst = false;   // count confirm once per FIRE event (RX ACKs every copy incl. DUP)
                // Sized for a max legal frame's RX line: "RX " (3) + 2*MAX_FRAME_LENGTH
                // hex (192) + NUL = 196 chars. 192 truncated the longest ACKs and, worse,
                // the old overflow path reset len mid-line so the tail parsed as a bogus
                // frame. 256 fits the longest line; uart_line_overflow discards until '\n'.
                char uart_line[256] = {0};
                size_t uart_line_len = 0;
                bool uart_line_overflow = false;
                char status[48] = "ready";
            };
        }

        class PropTx : public APP_BASE
        {
            private:
                const char* _tag = "prop_tx";
                PROP_TX::Data_t _data;
                PROP_TX::ChainKeyPoller _chain_key;
                prop_runtime_key::RuntimeKey _runtime_key;

                void _load_settings();
                bool _load_runtime_key();
                const prop_runtime_key::RuntimeKey* _runtime_key_or_status();
                void _save_settings();
                void _save_sequence();
                void _uart_init();
                void _init_chain_key();
                void _sync_colors_from_hues();
                void _set_status(const char* fmt, ...);
                void _disarm();
                void _cancel_to_safe();
                bool _locked() const;
                bool _is_command_mode() const;
                uint32_t _arm_remaining_ms() const;
                void _send_frame(prop_protocol::FrameType frameType);
                void _send_fire_burst();
                void _send_arm(int copies = 2);
                void _poll_uart();
                void _handle_modem_line(const char* line);
                bool _ack_payload_matches(const prop_protocol::Frame& ack) const;
                void _clear_pending_ack_state();
                void _remember_ff_command(prop_protocol::FrameType frameType, const std::vector<uint8_t>& encoded);
                bool _handle_recent_ff_error(const char* line);
                bool _retry_pending_ack();
                void _handle_ack_timeout();
                void _adjust_selected_action(int direction);
                void _handle_back();
                void _toggle_mode();
                bool _poll_fire_button();
                bool _service_link_during_input_wait();
                bool _touch_in_action_button(int x, int y) const;
                void _run_selected_action(PROP_TX::Action_t action);
                void _run_selected_action();
                void _render();
                PROP_TX::View_t _view() const;
                const char* _action_label() const;

            public:
                GUI_PropTx _gui;
                PropTx() = default;
                ~PropTx() = default;

                GUI_Base* getGui() override { return &_gui; }

                void onSetup();
                void onCreate();
                void onRunning();
                void onDestroy();
        };
    }
}
