#pragma once
// =============================================================================
//  prop_tx_config.h  --  M5Dial (dial-tx) TUNING / CONFIGURATION
// =============================================================================
//  Marlin-style "Configuration.h": the ONE place to tune the M5Dial transmitter
//  (the pyro CONSOLE) without digging through app_prop_tx.cpp logic. Change a
//  value here, rebuild dial-tx (ESP-IDF), reflash. Everything in this file is a
//  USER KNOB. The companion file for the DinMeter receiver is
//  firmware/din-rx/src/prop_config.h -- this header mirrors its layout.
//
//  Internal / SECURITY-critical constants deliberately STAY in app_prop_tx.cpp
//  and are NOT exposed here -- editing them can break the radio link or its
//  authentication:
//    * SHARED_KEY[]                 -- the 16-byte HMAC secret (never move it)
//    * PROP_NVS_NAMESPACE / _TAG    -- NVS blob namespace + log tag
//    * the per-boot RANDOM session epoch + sequence handling
//    * the 13-byte LED payload rule -- FIRE/Preview always send EXACTLY 4 RGB
//      colours (first4_colors); LED#5's colour rides the separate PaletteSet
//      frame. Do NOT try to widen the LED payload from here.
//
//  HOW TO USE THIS FILE
//    1. Find the section you care about in the SECTION INDEX below.
//    2. Change the value (or 1<->0 for a build flag -- but see [A]: the build
//       flags are -D defines, documented here, NOT redefined here).
//    3. Rebuild dial-tx and reflash. The SANITY CHECKS block (bottom of this
//       file) refuses to compile if a value is out of range, so a typo is
//       caught at build time, not on the bench.
//  Every default here reproduces the CURRENT shipping behaviour exactly --
//  starting from a fresh flash, changing nothing, the console behaves as before.
//
//  SECTION INDEX
//    [0] QUICK RECIPES       -- copy/paste cookbook for the most common tweaks
//    [1] STRIP / LEDS        -- transmitted LED-slot count + payload brightness
//    [2] MODEM UART (PORT A) -- serial link to the LoRa/ESP-NOW modem
//    [3] ENCODER / INPUT     -- rotary detents, click-suppress, render pacing
//    [4] TIMINGS / ARM       -- arm window + heartbeat, status/poll cadences
//    [5] ACK RETRY           -- ack-tracked SEND retry budget + timeout
//    [6] FIRE BURST (FF)     -- fire-and-forget redundancy + jitter (FIRE_MODE_FF)
//    [7] TOUCH ZONES         -- on-screen LED-strip + ACTION hit rectangles
//    [8] PROTOCOL            -- HMAC key id + frame routing (source/destination)
//    [A] FEATURE FLAGS       -- compile-time -D switches (documented, not defined)
//    [B] DEFAULTS (FACTORY)  -- factory per-slot palette (colours + hues)
//    [C] NAMED LED ROLES     -- human names for the five transmitted LED slots
//    [D] SANITY CHECKS       -- compile-time validation (do not edit)
// =============================================================================

// =============================================================================
//  [0] QUICK RECIPES  --  the cookbook. Copy a line, apply the change, rebuild.
// =============================================================================
//  Each recipe names the REAL knob below so you can jump straight to it.
//
//   * Change a slot's factory colour (e.g. LED #1 starts BILA instead of red):
//       edit  DEFAULT_COLORS[0]  to {255,255,255}  (and, if you want the HUE
//       wheel to match, DEFAULT_HUES[0])            (section [B])
//       NOTE: a saved NVS colour still OVERRIDES this until the Dial's NVS is
//       wiped/reflashed or the colour is re-edited on the device.
//
//   * Re-wire the modem to different Grove pins (custom cable / board):
//       set  PROP_UART_TX_GPIO / PROP_UART_RX_GPIO  (section [2])
//       (defaults are Grove Port A: TX=GPIO13 -> modem RX, RX=GPIO15 <- modem TX)
//
//   * Run the modem link faster/slower (must match the modem firmware):
//       set  PROP_UART_BAUD                          (section [2])
//
//   * Fewer / more FIRE copies on the air (reliability vs duty cycle):
//       set  FF_REDUNDANCY  (>=1; 3 = today: one immediate + two jittered)  ([6])
//
//   * Tighten / loosen the FIRE-burst spacing (anti-collision jitter):
//       edit  FF_JITTER_MIN_MS / FF_JITTER_SPAN_MS   (section [6])
//
//   * Make the acked sends (Preview/Palette/Ping/Stop) retry more before giving
//     up (weak link):
//       raise  ACK_RETRY_MAX  and/or  ACK_RETRY_TIMEOUT_MS   (section [5])
//
//   * Encoder feels twitchy / a turn is misread as a click:
//       raise  ENCODER_BUTTON_QUIET_MS (rotation click-suppress window) ([3])
//       (the physical button DEBOUNCE itself is hal.cpp encoder.btn.setDebounce(30),
//        see [3] note -- it lives in the HAL, not here)
//
//   * Two detents per selection step feels wrong (too coarse/fine):
//       set  ENC_COUNTS_PER_DETENT  (M5Dial encoder = 2 counts/detent)    ([3])
//
//   * Hold-to-switch COMMAND<->SETUP feels too long/short:
//       set  ENCODER_LONG_PRESS_MS                   (section [3])
//
//   * Keep the receiver armed longer between heartbeats (lower LoRa duty):
//       raise  ARM_HEARTBEAT_MS (must stay BELOW the receiver's ~12 s ARM TTL) ([4])
// =============================================================================

#include <array>
#include <cstdint>
#include "prop_colors.h"   // prop_colors::NUM_COLOR_PRESETS + COLOR_PRESETS (single source: shared/protocol). On the include path via dial-tx main/CMakeLists.txt INCLUDE_DIRS "../../../shared/protocol". Used by the SANITY CHECKS [D] that validate the factory palette.

namespace prop_tx_config
{

// ============================ [1] STRIP / LEDS ==============================
// Number of LED slots the Dial EDITS and TRANSMITS in a PaletteSet (the five
// physical DinMeter LEDs: #1/#2 buttons, #3 switch, #4 odpal, #5 remote). The
// SETUP colour editor (FIELD_LED) and the touch strip reach slots 0..4.
//   IMPORTANT: this is the PALETTE slot count, NOT the LED payload width. The
//   13-byte FIRE/Preview LED payload ALWAYS carries exactly 4 colours
//   (first4_colors in app_prop_tx.cpp); LED#5 (slot 4) is delivered only via the
//   separate PaletteSet frame. Changing this does NOT change the 13-byte payload.
constexpr std::uint8_t PROP_TX_FIXED_LEDS = 5;

// Brightness byte stamped into the transmitted LED payload (FIRE/Preview). The
// receiver scales the 4 payload colours by this. 255 = send colours at full
// scale and let the DinMeter apply its own per-channel brightness. 0..255.
constexpr std::uint8_t PROP_TX_LED_PAYLOAD_BRIGHTNESS = 255;

// ----- Backing-array width (NVS compatibility) -------------------------------
// The Dial keeps 8-slot backing arrays for colours + hues so the on-flash NVS
// blob layout never changes, even though only PROP_TX_FIXED_LEDS (5) are used.
// This is the size of std::array<...,8> colors/hues in Data_t; do not shrink it
// or a loaded NVS "colors"/"hueDeg" blob would mismatch its stored size.
constexpr std::size_t PROP_TX_PALETTE_SLOTS = 8;

// ========================== [2] MODEM UART (PORT A) =========================
// Serial link from the Dial (host) to its LoRa/ESP-NOW modem, over Grove Port A.
// The modem RX expects our TX; our RX listens to the modem TX. Both lines are
// idle-high (internal pull-ups, set in _uart_init) so neither side samples boot
// garbage. Pins are GPIO numbers on the M5Dial (ESP32-S3).
constexpr int      PROP_UART_PORT_NUM = 1;        // UART_NUM_1 (see [D]/the .cpp cast to uart_port_t)
constexpr int      PROP_UART_TX_GPIO  = 13;       // Grove Port A TX -> modem RX (GPIO_NUM_13)
constexpr int      PROP_UART_RX_GPIO  = 15;       // Grove Port A RX <- modem TX (GPIO_NUM_15)
constexpr int      PROP_UART_BAUD     = 115200;   // host<->modem line rate (must match modem firmware)

// ============================ [3] ENCODER / INPUT ===========================
// The M5Dial rotary encoder + its push-button. The encoder emits ENC_COUNTS_PER_
// DETENT raw counts per physical detent; rotation also injects a brief glitch on
// the BUTTON line, so a click-suppress window keyed to wall-clock time drains any
// press handled within ENCODER_BUTTON_QUIET_MS of the last rotation.
constexpr std::uint32_t ENCODER_LONG_PRESS_MS      = 600;  // hold encoder button >=0.6s = switch COMMAND<->SETUP
constexpr std::uint32_t ENCODER_IDLE_FLUSH_MS      = 150;  // stale partial-detent accumulator flush after this idle gap
constexpr std::uint32_t ENCODER_BUTTON_QUIET_MS    = 180;  // rotation->click suppress window (raise if a turn registers as a press)
constexpr std::uint32_t ENCODER_RENDER_THROTTLE_MS = 35;   // min gap between encoder-driven redraws (~28 Hz cap)
constexpr int           ENC_COUNTS_PER_DETENT      = 2;    // raw encoder counts per physical detent (one selection step)

// ----- Physical button DEBOUNCE (documented here; SET in the HAL) ------------
// The encoder push-button's contact debounce is NOT configured here -- it is set
// once in firmware/dial-tx/main/hal/hal.cpp as  encoder.btn.setDebounce(30);
// (30 ms), implemented by Button::setDebounce in hal/utils/Button/Button.cpp.
// It is shared HAL state (the same Button class backs other inputs), so it stays
// in the HAL by design. To change the debounce, edit that hal.cpp call; the
// ENCODER_BUTTON_QUIET_MS knob above is the app-level rotation-noise guard and is
// a SEPARATE mechanism (timestamp window vs contact debounce).

// ============================ [4] TIMINGS / ARM =============================
// Arm-window + heartbeat cadence and the periodic status/poll timings.
constexpr std::uint32_t ARM_WINDOW_MS    = 10000;  // legacy: only feeds the on-screen _arm_remaining_ms countdown (no auto-disarm; ARM holds until FIRE or CANCEL)
constexpr std::uint32_t ARM_HEARTBEAT_MS = 5000;   // re-send ARM every 5s while armed to refresh the receiver's ~12s TTL (~0.86% LoRa duty). MUST stay below that TTL.
constexpr std::uint32_t STATUS_TOKEN_MS  = 1800;   // how long a status line is considered "fresh" for the render gate
constexpr std::uint32_t CHAIN_KEY_POLL_MS = 50;    // min gap between Chain-Key (physical FIRE button) reads

// ============================== [5] ACK RETRY ===============================
// The ack-tracked "SEND" path (Preview / PaletteSet / Ping / Stop): if no
// matching ack arrives within ACK_RETRY_TIMEOUT_MS, re-send up to ACK_RETRY_MAX
// times before giving up (NO ACK + disarm). FIRE does NOT use this path -- it is
// fire-and-forget burst, see [6]. STOP keeps retrying even through a CANCEL
// (safety-critical master-off).
constexpr std::uint8_t  ACK_RETRY_MAX        = 2;     // max re-sends after the first transmission (>=1)
constexpr std::uint32_t ACK_RETRY_TIMEOUT_MS = 2500;  // per-attempt ack wait before retry/timeout

// =========================== [6] FIRE BURST (FF) ============================
// Fire-and-forget burst tuning. Active only when the build flag FIRE_MODE_FF=1
// (see [A]; it is the default). A FIRE sends one immediate copy then
// (FF_REDUNDANCY-1) more, each spaced by a random delay in
// [FF_JITTER_MIN_MS, FF_JITTER_MIN_MS + FF_JITTER_SPAN_MS) ms to dodge
// collisions. The receiver dedups copies by sequence, so extra copies are
// harmless redundancy -- they only cost air time / duty cycle.
//   (These three are inside the FIRE_MODE_FF guard in app_prop_tx.cpp.)
constexpr std::uint8_t  FF_REDUNDANCY    = 3;   // total FIRE copies on the air (1 immediate + 2 jittered). >=1.
constexpr std::uint32_t FF_JITTER_MIN_MS = 18;  // floor of the inter-copy random delay
constexpr std::uint32_t FF_JITTER_SPAN_MS = 22; // span added on top of the floor (>=1, used as esp_random() % span)

// ----- FF retry-on-ERR (the recent-FF ring) ----------------------------------
// An uncorrelated modem "ERR BUSY"/"ERR DUTY" cannot be tied to one frame, so
// every still-fresh fire-and-forget frame (FIRE/ARM/RemoteLed/Preview/PaletteSet)
// in a small ring is re-sent once. These bound that ring's freshness + budget.
constexpr std::uint32_t RECENT_FF_COMMAND_MS = 900;  // how long a recorded FF stays eligible for an ERR-driven resend
constexpr std::uint8_t  RECENT_FF_RETRIES    = 1;    // resends allowed per recorded FF on ERR BUSY/DUTY

// ============================== [7] TOUCH ZONES =============================
// On-screen touch hit-rectangles (M5Dial 240x240 round LCD, pixel coords). The
// LED strip row (SETUP) selects a colour slot; the ACTION button (COMMAND) runs
// the selected action. The LED dots are laid out at START_X + n*SPACING.
//   (Touch below y>220 is the BACK gesture, handled separately in onRunning.)
constexpr int PROP_TX_LED_TOUCH_LEFT   = 52;
constexpr int PROP_TX_LED_TOUCH_RIGHT  = 221;  // widened for the 5th LED column (linear map: 70 + 4*33 = 202)
constexpr int PROP_TX_LED_TOUCH_TOP    = 168;
constexpr int PROP_TX_LED_TOUCH_BOTTOM = 220;
constexpr int PROP_TX_LED_START_X      = 70;   // x of LED-dot #1 centre
constexpr int PROP_TX_LED_SPACING      = 33;   // x gap between adjacent LED dots

constexpr int PROP_TX_ACTION_TOUCH_LEFT   = 72;
constexpr int PROP_TX_ACTION_TOUCH_RIGHT  = 168;
constexpr int PROP_TX_ACTION_TOUCH_TOP    = 74;
constexpr int PROP_TX_ACTION_TOUCH_BOTTOM = 166;

// ----- Colour-wheel range -----------------------------------------------------
constexpr int HUE_MAX = 360;   // hue degrees wrap modulo this (0..359)

// =============================== [8] PROTOCOL ===============================
// Frame addressing for the authenticated link. The HMAC SECRET (SHARED_KEY) is
// deliberately NOT here -- it stays in app_prop_tx.cpp. These three only route +
// tag frames; the receiver must use the mirror routing (its source==our
// destination and vice-versa) and the same key id.
constexpr std::uint8_t PROP_KEY_ID      = 1;     // HMAC key id stamped into every frame (receiver must accept this id)
constexpr std::uint8_t PROP_SOURCE      = 0x11;  // this Dial's frame source address
constexpr std::uint8_t PROP_DESTINATION = 0x22;  // the receiver's address (acks come back source=0x22 dest=0x11)

// ============================== [A] FEATURE FLAGS ===========================
// Compile-time on/off switches. UNLIKE the numeric knobs above, these are real
// -D build defines (set in app_prop_tx.cpp with #ifndef fallbacks, ~lines 14-24)
// -- they are DOCUMENTED here, NOT redefined here. To change one, pass it on the
// ESP-IDF build (e.g. add -DDEBUG_HUD=1 to the component/build flags); do NOT add
// a #define in this file (that would clash with the .cpp guard).
//
//   FIRE_MODE_FF   (default 1) -- FIRE delivery mode. 1 = fire-and-forget burst
//                  (FF_REDUNDANCY copies, jittered; see [6]) with no UI-blocking
//                  ack. 0 = the legacy single ack-tracked Fire (uses [5]'s retry
//                  budget instead). Production ships 1.
//   SELFTEST_FIRE  (default 0) -- bench auto-fire loop. 1 = the Dial arms + fires
//                  on a timer (SELFTEST_INTERVAL_MS / _MAX_SHOTS, defined under
//                  the flag in the .cpp) and prints STAT lines for RF/RTT
//                  bring-up. 0 = production (no auto-fire). Leave 0 for a live rig.
//   DEBUG_HUD      (default 0) -- on-screen diagnostics HUD + USB STAT telemetry
//                  (delivery ratio / FF counts / loop time / RTT, boot reason,
//                  min heap). 0 = clean operator display. Set -DDEBUG_HUD=1 for
//                  bring-up. (SELFTEST also pulls in the same stats block.)

// ===================== [B] DEFAULTS (FACTORY STATE) =========================
// The factory STARTING palette: the per-slot colours + hue-wheel positions the
// Dial powers on with. These are the single source of truth for Data_t's colour
// initialisers (app_prop_tx.h seeds `colors`/`hues` from them). _load_settings()
// then OVERRIDES them from NVS, so a colour saved on the device still wins; these
// only take effect on a fresh flash (or after the "colors"/"hueDeg" NVS keys are
// wiped). All PROP_TX_PALETTE_SLOTS (8) backing slots are seeded for NVS-blob
// size stability, but only the first PROP_TX_FIXED_LEDS (5) are edited/transmitted.
//
// ----- Factory per-slot RGB colour -------------------------------------------
// Slot order = LED #1..#5 (then 3 spare backing slots). Current factory palette:
//   slot0 #1 = red    {255,0,0}   | slot1 #2 = green {0,255,0}
//   slot2 #3 = blue   {0,0,255}   | slot3 #4 = azure {0,128,255}
//   slot4 #5 = yellow {255,255,0} | slots 5..7 = spare (cyan/magenta/orange)
constexpr std::array<std::array<std::uint8_t, 3>, PROP_TX_PALETTE_SLOTS> DEFAULT_COLORS = {{
    {255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {0, 128, 255},
    {255, 255, 0}, {0, 255, 255}, {255, 0, 255}, {255, 128, 0}}};

// ----- Factory per-slot hue (degrees, 0..359) --------------------------------
// The colour-wheel anchor for each slot, kept alongside DEFAULT_COLORS so the
// HUE field starts in sync with the RGB above. (On NVS load, if only "colors"
// exists, hues are recomputed from RGB; these are the bare factory anchors.)
constexpr std::array<std::uint16_t, PROP_TX_PALETTE_SLOTS> DEFAULT_HUES =
    {{0, 120, 240, 210, 60, 180, 300, 30}};

// ========================= [C] NAMED LED ROLES ==============================
// Human names for the five TRANSMITTED LED slots, so DEFAULT_COLORS / the touch
// strip / the SETUP editor read clearly. The INDEX is the palette slot
// (0..PROP_TX_FIXED_LEDS-1); each maps to the same-numbered physical DinMeter LED.
//
//   index 0  LED_SLOT_BUTTON1 -- DinMeter LED #1 (local toggle button 1)
//   index 1  LED_SLOT_BUTTON2 -- DinMeter LED #2 (local toggle button 2)
//   index 2  LED_SLOT_SWITCH  -- DinMeter LED #3 (switch + remote LED3 latch)
//   index 3  LED_SLOT_ODPAL   -- DinMeter LED #4 (odpal / FIRE flash)
//   index 4  LED_SLOT_REMOTE  -- DinMeter LED #5 (remote-only; rides PaletteSet)
constexpr int LED_SLOT_BUTTON1 = 0;
constexpr int LED_SLOT_BUTTON2 = 1;
constexpr int LED_SLOT_SWITCH  = 2;
constexpr int LED_SLOT_ODPAL   = 3;
constexpr int LED_SLOT_REMOTE  = 4;

// ========================== [D] SANITY CHECKS ===============================
// Compile-time validation of the knobs above. If you set something out of
// range, the build FAILS HERE with the message below -- a typo is caught now,
// not on the bench. Do not edit this block; fix the offending value instead.

// Transmitted-slot count must be in [1,8]: at least one editable LED, and never
// more than the 8 backing slots (PROP_TX_FIXED_LEDS slots are sliced out of the
// 8-wide colours/hues arrays for the PaletteSet).
static_assert(PROP_TX_FIXED_LEDS >= 1 && PROP_TX_FIXED_LEDS <= PROP_TX_PALETTE_SLOTS,
              "[1] PROP_TX_FIXED_LEDS must be in [1, PROP_TX_PALETTE_SLOTS] (sliced from the 8-slot backing arrays)");
static_assert(PROP_TX_PALETTE_SLOTS == 8,
              "[1] PROP_TX_PALETTE_SLOTS must stay 8 (NVS colors/hueDeg blob layout); do not resize the backing arrays");

// UART: a valid ESP32 port index and three DISTINCT GPIO/port choices (TX and RX
// must not be the same pin, or the link self-shorts).
static_assert(PROP_UART_PORT_NUM >= 0 && PROP_UART_PORT_NUM <= 2,
              "[2] PROP_UART_PORT_NUM must be a valid ESP32-S3 UART index (0..2)");
static_assert(PROP_UART_TX_GPIO != PROP_UART_RX_GPIO,
              "[2] PROP_UART_TX_GPIO and PROP_UART_RX_GPIO must be different pins");
static_assert(PROP_UART_BAUD > 0,
              "[2] PROP_UART_BAUD must be > 0");

// Encoder: a positive detent divisor (0 would divide-by-zero the step math) and
// a sane long-press threshold.
static_assert(ENC_COUNTS_PER_DETENT > 0,
              "[3] ENC_COUNTS_PER_DETENT must be > 0 (it divides the raw count into selection steps)");
static_assert(ENCODER_LONG_PRESS_MS > 0,
              "[3] ENCODER_LONG_PRESS_MS must be > 0");

// Arm heartbeat must be positive AND shorter than the legacy arm window it is
// meant to refresh (and, in turn, the receiver's TTL), or the receiver could
// lapse to SAFE between heartbeats.
static_assert(ARM_HEARTBEAT_MS > 0 && ARM_HEARTBEAT_MS < ARM_WINDOW_MS,
              "[4] ARM_HEARTBEAT_MS must be > 0 and < ARM_WINDOW_MS (refresh before the window lapses)");

// Ack retry: at least one resend allowed and a non-zero wait per attempt.
static_assert(ACK_RETRY_MAX >= 1,
              "[5] ACK_RETRY_MAX must be >= 1 (at least one resend before giving up)");
static_assert(ACK_RETRY_TIMEOUT_MS > 0,
              "[5] ACK_RETRY_TIMEOUT_MS must be > 0");

// FIRE burst: at least one copy on the air, and a non-zero jitter span (it is
// used as esp_random() % FF_JITTER_SPAN_MS, which is undefined for 0).
static_assert(FF_REDUNDANCY >= 1,
              "[6] FF_REDUNDANCY must be >= 1 (at least one FIRE copy is sent)");
static_assert(FF_JITTER_SPAN_MS >= 1,
              "[6] FF_JITTER_SPAN_MS must be >= 1 (used as esp_random() % span)");
static_assert(RECENT_FF_RETRIES >= 1,
              "[6] RECENT_FF_RETRIES must be >= 1 (else an ERR BUSY/DUTY resend is a no-op)");

// Touch zones: each hit-rectangle must be non-empty (right>left, bottom>top).
static_assert(PROP_TX_LED_TOUCH_RIGHT > PROP_TX_LED_TOUCH_LEFT &&
              PROP_TX_LED_TOUCH_BOTTOM > PROP_TX_LED_TOUCH_TOP,
              "[7] LED touch rectangle must be non-empty (RIGHT>LEFT, BOTTOM>TOP)");
static_assert(PROP_TX_ACTION_TOUCH_RIGHT > PROP_TX_ACTION_TOUCH_LEFT &&
              PROP_TX_ACTION_TOUCH_BOTTOM > PROP_TX_ACTION_TOUCH_TOP,
              "[7] ACTION touch rectangle must be non-empty (RIGHT>LEFT, BOTTOM>TOP)");
static_assert(PROP_TX_LED_SPACING > 0,
              "[7] PROP_TX_LED_SPACING must be > 0 (it divides the touch-x into a slot index)");
static_assert(HUE_MAX > 0,
              "[7] HUE_MAX must be > 0 (hue wraps modulo this)");

// Protocol routing: a frame must not be addressed from a node to itself, or the
// receiver's mirror-route check (source==our destination) could never match.
static_assert(PROP_SOURCE != PROP_DESTINATION,
              "[8] PROP_SOURCE and PROP_DESTINATION must differ (a frame cannot be addressed to its own sender)");

// Factory palette: the backing arrays must fill all 8 slots (NVS-blob size), and
// the transmitted slots must each name a real colour. (DEFAULT_HUES anchors are
// 0..359, kept < HUE_MAX.)
static_assert(DEFAULT_COLORS.size() == PROP_TX_PALETTE_SLOTS &&
              DEFAULT_HUES.size() == PROP_TX_PALETTE_SLOTS,
              "[B] DEFAULT_COLORS and DEFAULT_HUES must each have PROP_TX_PALETTE_SLOTS entries (the NVS-blob width)");
static_assert(DEFAULT_HUES[0] < HUE_MAX && DEFAULT_HUES[1] < HUE_MAX && DEFAULT_HUES[2] < HUE_MAX &&
              DEFAULT_HUES[3] < HUE_MAX && DEFAULT_HUES[4] < HUE_MAX && DEFAULT_HUES[5] < HUE_MAX &&
              DEFAULT_HUES[6] < HUE_MAX && DEFAULT_HUES[7] < HUE_MAX,
              "[B] every DEFAULT_HUES entry must be < HUE_MAX (a valid hue degree)");

// Named slots must address real transmitted LEDs.
static_assert(LED_SLOT_BUTTON1 < PROP_TX_FIXED_LEDS && LED_SLOT_BUTTON2 < PROP_TX_FIXED_LEDS &&
              LED_SLOT_SWITCH  < PROP_TX_FIXED_LEDS && LED_SLOT_ODPAL   < PROP_TX_FIXED_LEDS &&
              LED_SLOT_REMOTE  < PROP_TX_FIXED_LEDS,
              "[C] every LED_SLOT_* must be < PROP_TX_FIXED_LEDS (a transmitted slot)");

// Cross-check against the shared colour table: the factory palette references the
// same prop_colors single-source the editor cycles, so this header and the device
// agree there ARE presets to land on. (The slots hold raw RGB, not preset indices,
// so we assert the table is non-empty rather than indexing it.)
static_assert(prop_colors::NUM_COLOR_PRESETS > 0,
              "[D] prop_colors::COLOR_PRESETS must be non-empty (the editor cycles it; factory RGB are drawn from it)");

}  // namespace prop_tx_config
