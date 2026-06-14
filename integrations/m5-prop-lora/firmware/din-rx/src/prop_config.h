#pragma once
// =============================================================================
//  prop_config.h  --  DinMeter (din-rx) TUNING / CONFIGURATION
// =============================================================================
//  Marlin-style "Configuration.h": the ONE place to tune the DinMeter receiver
//  without digging through prop_rx.cpp logic. Change a value here, rebuild
//  din-rx, reflash. Everything in this file is a USER KNOB.
//
//  Internal / protocol-critical constants (NVS blob magic + versions, HMAC
//  framing, frame types) deliberately stay in prop_rx.cpp / the shared protocol
//  -- editing those can corrupt saved settings or break the radio link.
//
//  HOW TO USE THIS FILE
//    1. Find the section you care about in the SECTION INDEX below.
//    2. Change the value (or 1<->0 for a CONFIG_* flag).
//    3. Rebuild din-rx and reflash. The SANITY CHECKS block (bottom of this
//       file) will refuse to compile if a value is out of range, so a typo is
//       caught at build time, not on the bench.
//  Every default here reproduces the CURRENT shipping behaviour exactly --
//  starting from a fresh flash, changing nothing, the rig behaves as before.
//
//  SECTION INDEX
//    [0] QUICK RECIPES       -- copy/paste cookbook for the most common tweaks
//    [1] STRIP & LED ORDER   -- pixel count + which channel lights which pixel
//    [2] POWER / BRIGHTNESS  -- SK6812 current budget + brightness
//    [3] BUTTONS / SWITCH    -- ByteButton input -> function mapping
//    [4] I2C (PORT B)        -- bus pins/speed + device addresses
//    [5] MODEM UART (PORT A) -- serial link to the LoRa modem
//    [6] STOP BEHAVIOUR      -- remote-only vs full master-off
//    [7] TIMINGS             -- debounce / pacing / ack delays
//    [8] ODPAL ENVELOPE      -- fire-flash edit limits + curve names
//    [9] PROTOCOL            -- key id + replay window
//    [A] FEATURE FLAGS       -- compile-time on/off switches (boot self-test...)
//    [B] DEFAULTS (FACTORY)  -- factory LED colours / brightness / odpal envelope
//    [C] NAMED LED ROLES     -- human names for the logical channels
//    [D] SANITY CHECKS       -- compile-time validation (do not edit)
// =============================================================================

// =============================================================================
//  [0] QUICK RECIPES  --  the cookbook. Copy a line, apply the change, rebuild.
// =============================================================================
//  Each recipe names the REAL knob below so you can jump straight to it.
//
//   * Instant boot (skip the LED self-test):
//       set  CONFIG_BOOT_SELFTEST  0      (section [A])
//
//   * Faster boot self-test (keep the dead-pixel chase, just speed it up):
//       lower  BOOT_SELFTEST_DWELL_MS  (e.g. 40 -> 20)   (section [A])
//
//   * Swap physical LED 1 and 2 without rewiring:
//       in  LED_ORDER  swap the values 0 and 2           (section [1])
//
//   * Make STOP kill ALL local LEDs (not just the remote ones):
//       set  STOP_CLEARS_ALL_LOCAL_DEFAULT = true        (section [6])
//
//   * Brighter strip (ONLY if the 5V rail can supply it):
//       raise  LED_CURRENT_BUDGET_MA                      (section [2])
//
//   * Change a channel's factory colour (e.g. button-1 LED red instead of green):
//       edit  DEFAULT_LED_PRESET_IDX[0]  to a prop_colors preset index
//       (0=CERVENA 1=ZELENA 2=MODRA 3=BILA 4=ORANZOVA 5=AZUROVA 6=FIALOVA 7=ZHASNUTO)
//       NOTE: a saved NVS colour still overrides this until "factory" is re-flashed
//       or the colour is re-edited on the device.            (section [B])
//
//   * Dimmer-by-default strip (every channel starts dimmer):
//       lower  DEFAULT_LED_BRIGHTNESS  (0..255)            (section [B])
//
//   * Longer / shorter fire flash out of the box:
//       edit  DEFAULT_ODPAL_RAMP_MS / _HOLD_MS / _FADE_MS  (section [B])
//
//   * Different fire-flash shape by default (step / linear / sine):
//       set  DEFAULT_ODPAL_CURVE  to 0=HRANA 1=LIN 2=SINUS (section [B])
//
//   * Re-map a ByteButton input to a different function:
//       change the matching  BB_*_IDX  (keep all four distinct)  (section [3])
//
//   * Quieter NVS writes (save settings only after a longer pause):
//       raise  SETTINGS_SAVE_DEBOUNCE_MS                   (section [7])
// =============================================================================

#include <cstdint>
#include "prop_colors.h"   // prop_colors::NUM_COLOR_PRESETS + COLOR_PRESETS (single source: shared/protocol). On the -I include path (din-rx platformio.ini: -I../../shared/protocol). Used by the factory-colour defaults [B] + sanity checks [D].

namespace prop_config
{

// ============================ [1] STRIP & LED ORDER ==========================
// Number of logical LED channels driven by the DinMeter:
//   #1/#2 = local toggle buttons, #3 = switch + remote, #4 = odpal (fire),
//   #5 = remote-only. Change this only if you add/remove physical LEDs.
constexpr int LED_COUNT = 5;

// Physical strip buffer upper bound. The NeoPixel buffer is sized to this so
// EVERY physical LED gets data on every show() (no stray/garbage LEDs lit
// beyond the active range). The actually-driven count is the runtime
// _activeLeds (1..LED_STRIP_MAX, default LED_COUNT). Raise this for a longer strip.
constexpr int LED_STRIP_MAX = 30;

// ----- LED ORDER REMAP (THE ONE PLACE TO REORDER WITHOUT REWIRING) -----------
// Array INDEX  = logical channel (0..4 == LED #1..#5 behaviour).
// Array VALUE  = physical pixel index on the SK6812 strip (0 == position 1).
// Applied at every pixel write (showBudgetedFrame, incl. odpal #4 + remote #5).
//   Identity {0,1,2,3,4} = no remap.  Example: swap phys #3 and #5 -> {0,1,4,3,2}.
// MUST be a permutation of 0..LED_COUNT-1 (each physical index exactly once);
// a duplicate / out-of-range value leaves a pixel unwritten (stale/dark).
// Current WIRED mapping {0,2,3,4,1}:
//   ch0 green-toggle -> phys 0 (pos 1) | ch1 red-toggle -> phys 2 (pos 3)
//   ch2 switch       -> phys 3 (pos 4) | ch3 odpal       -> phys 4 (pos 5)
//   ch4 remote       -> phys 1 (pos 2)
constexpr std::uint8_t LED_ORDER[LED_COUNT] = {0, 2, 3, 4, 1};
static_assert(LED_ORDER[0] < LED_COUNT && LED_ORDER[1] < LED_COUNT && LED_ORDER[2] < LED_COUNT &&
              LED_ORDER[3] < LED_COUNT && LED_ORDER[4] < LED_COUNT,
              "LED_ORDER values must each be < LED_COUNT (keep it a permutation of 0..LED_COUNT-1)");

// ============================ [2] POWER / BRIGHTNESS =========================
constexpr std::uint16_t LED_CURRENT_BUDGET_MA = 280;  // 5V-rail current cap; whole frame auto-dims to fit (was 220 for 4 LEDs)
constexpr std::uint8_t  WS2812_CHANNEL_MA     = 20;   // modelled mA per fully-on R/G/B channel of one pixel
constexpr std::uint8_t  WS2812_IDLE_MA        = 1;    // modelled mA per pixel just powered (all channels off)
constexpr std::uint8_t  LOCAL_BRIGHTNESS      = 200;  // static-colour brightness 0..255 (budget above still caps)

// =========================== [3] BUTTONS / SWITCH ============================
// M5 Unit ByteButton (8 inputs, I2C, active-low). The DinMeter uses inputs 0..3.
constexpr std::uint8_t BYTEBUTTON_ADDR = 0x47;   // ByteButton I2C address
constexpr std::uint8_t BB_SWITCH_IDX   = 0;      // input 0 = prepinac (level) -> SK6812 #3
constexpr std::uint8_t BB_BTN1_IDX     = 1;      // input 1 = tlacitko 1 (edge->toggle) -> SK6812 #1
constexpr std::uint8_t BB_BTN2_IDX     = 2;      // input 2 = tlacitko 2 (edge->toggle) -> SK6812 #2
constexpr std::uint8_t BB_FIRE_IDX     = 3;      // input 3 = local FIRE -> odpal (immediate, lockout-only)
constexpr std::uint8_t BB_PRESSED      = 0;      // getSwitchStatus() value meaning pressed (module is active-low: 1=released,0=pressed)

// ============================== [4] I2C (PORT B) =============================
// Prop I/O backend on Port B (G1/G2).
//
// Production prop electronics now use a Seeed XIAO RP2040 coprocessor on Port B
// UART. The legacy I2C backend (ByteButton + NeoDriver) is kept compiled for
// bench fallback, but must not run at the same time because it uses the same
// G1/G2 wires.
constexpr bool PROP_IO_XIAO_UART_ENABLED = true;

// Legacy Port B I2C pin order. Pin order matches the factory I/O test
// (Wire1.begin(2,1)): SDA=G2, SCL=G1. (Modem keeps Port A UART; onboard RTC
// keeps the primary Wire bus G11/G12.)
constexpr int          I2C_SDA_PIN            = 2;       // Port B G2
constexpr int          I2C_SCL_PIN            = 1;       // Port B G1
constexpr std::uint32_t I2C_SPEED             = 100000;  // 100 kHz: robust over long Grove wiring / weak pull-ups
constexpr std::uint8_t NEODRIVER_ADDR         = 0x60;    // Adafruit NeoDriver (seesaw) -> SK6812 RGBW
constexpr int          NEODRIVER_NEOPIXEL_PIN = 15;      // NeoDriver's fixed seesaw NeoPixel output pin

// XIAO UART on DinMeter Port B:
//   DinMeter TX G2/yellow/GO -> XIAO RX D7/GPIO1
//   DinMeter RX G1/white/GI  <- XIAO TX D6/GPIO0
// Both sides are 3.3V UART logic. LEDs still need their own 5V supply and data
// level shifting on the XIAO outputs.
constexpr int           PROP_IO_UART_TX_PIN = 2;
constexpr int           PROP_IO_UART_RX_PIN = 1;
constexpr std::uint32_t PROP_IO_UART_BAUD   = 115200;
constexpr std::uint8_t  XIAO_BARREL_WS2812_COUNT = 18;
constexpr std::uint8_t  XIAO_STATUS_LED_COUNT    = 4;

// =========================== [5] MODEM UART (PORT A) =========================
constexpr int          UART1_TX_PIN = 13;       // Grove Port A TX -> modem RX
constexpr int          UART1_RX_PIN = 15;       // Grove Port A RX <- modem TX
constexpr std::uint32_t MODEM_BAUD  = 115200;   // host<->modem line rate

// ============================== [6] STOP BEHAVIOUR ===========================
//   false (DEFAULT): STOP is a REMOTE master-off -- clears the remote #3/#5
//                    latches + odpal, but LEAVES the local button latches
//                    (#1/#2) and the physical switch (#3) live, so a standalone
//                    DinMeter keeps its locally-set LEDs after a Dial STOP.
//   true           : STOP is a FULL master-off -- ALSO clears #1/#2 and raises
//                    an inhibit latch that forces #1/#2/#3 dark + ignores the
//                    switch until the next LOCAL input/edge releases it.
constexpr bool STOP_CLEARS_ALL_LOCAL_DEFAULT = false;

// ================================ [7] TIMINGS ===============================
constexpr std::uint32_t LONG_PRESS_EXIT_MS       = 900;   // hold-to-exit a settings page
constexpr std::uint32_t SETTINGS_SAVE_DEBOUNCE_MS = 500;  // quiet time before a settings NVS write
constexpr std::uint32_t SAVED_BADGE_MS           = 800;   // "ULOZENO" badge visible time
constexpr std::uint32_t BATTERY_READ_MS          = 3000;  // battery sample interval
constexpr std::uint32_t FIRE_ACK_DELAY_MS        = 90;    // defer the FIRE ack past the sender's ~70ms 3x burst (half-duplex)
constexpr std::uint32_t FIRE_ACK_JITTER_MS       = 40;    // random spread added to the FIRE ack delay
constexpr std::uint32_t ODPAL_FRAME_MS           = 25;    // odpal redraw pacing (~40 Hz) -> bounded Wire1 traffic
constexpr std::uint32_t PREVIEW_OVERLAY_MS       = 1800;  // Dial Preview: visible, non-arming full-strip overlay time
constexpr std::uint32_t STATIC_COLOR_FADE_MS     = 400;   // PaletteSet fade mode: crossfade duration for static channels
constexpr std::uint32_t STATIC_COLOR_FRAME_MS    = 25;    // redraw pacing for non-blocking static-channel fades

// ============================ [8] ODPAL ENVELOPE ============================
// The fire-flash on SK6812 #4: ramp-up -> hold -> fade-out, edited on the Cas page.
// (The factory STARTING values of the envelope live in section [B] below; these
//  are the EDIT LIMITS + the curve catalogue applied on top.)
constexpr std::uint32_t ODPAL_MS         = 1200;   // legacy default total (now derived from the envelope)
constexpr std::uint16_t ODPAL_MAX_MS     = 5000;   // per-phase (ramp/hold/fade) edit clamp
constexpr std::uint16_t ODPAL_STEP_MS    = 50;     // Settings edit step for the time fields
constexpr const char*   ODPAL_CURVE_NAMES[] = {"HRANA", "LIN", "SINUS"};  // 0=step 1=linear 2=sine-ease
constexpr int           NUM_ODPAL_CURVES = 3;

// =============================== [9] PROTOCOL ===============================
constexpr std::uint8_t  PROP_KEY_ID            = 1;   // HMAC key id this receiver accepts
constexpr std::uint32_t RX_REPLAY_WINDOW_BITS  = 32;  // sliding replay window size (frames)

// ============================== [A] FEATURE FLAGS ===========================
// Compile-time on/off switches. These add or remove whole behaviours -- unlike
// the numeric knobs above, flipping one changes WHETHER a feature runs at all.
//
// Production three-device stack:
//   false = DinMeter is indication + electronics/safety authority only. Setup
//           edits live on the M5StickS3 Terminal and arrive over USB.
//   true  = legacy local encoder editor is enabled for bench/debug builds.
constexpr bool DINMETER_LOCAL_SETUP_EDITOR_ENABLED = false;
//
// ----- Boot LED self-test (the power-on "chase") -----------------------------
// On boot the firmware walks EACH pixel individually through R, G, B, W (a
// "chase") so a dead first pixel / cold DIN solder joint is visually
// UNAMBIGUOUS versus a dead chain. It is the quickest way to confirm the strip
// on the bench. Turn it OFF for an instant, no-flash boot once the hardware is
// trusted. With it OFF the strip is still initialised + cleared (starts dark);
// only the diagnostic chase is skipped.
//   1 = run the chase (DEFAULT, today's behaviour)
//   0 = skip the chase -> instant boot
#define CONFIG_BOOT_SELFTEST 1

// Per-pixel dwell time of the boot chase, in milliseconds. The total chase time
// is roughly  4 phases * active-LED-count * BOOT_SELFTEST_DWELL_MS. Lower =
// faster boot but a briefer look at each pixel. (Internally the dwell is split
// into ~10ms slices so an arriving STOP / e-stop frame aborts the chase
// promptly instead of waiting it out.) Default 40 == today's behaviour.
constexpr std::uint32_t BOOT_SELFTEST_DWELL_MS = 40;

// ----- Build-time diagnostics (documented here; DEFINED in prop_rx.cpp) ------
// These two are NOT redefined here -- they are real -D build flags / #defines
// near the top of prop_rx.cpp (~lines 29-39). Listed so you know they exist and
// how to use them. To change them, pass them on the PlatformIO build_flags
// (e.g. -DDEBUG_HUD=0), do NOT add a #define here.
//
//   DEBUG_HUD     (default 1) -- master diagnostics switch. ON keeps the USB
//                 serial telemetry alive ([hb] heartbeat + [bb] ByteButton
//                 lines that read_com.py parses) and per-loop perf stats.
//                 Build with -DDEBUG_HUD=0 to compile OUT all diagnostics
//                 (serial + display + stats) for a lean release flash.
//   DIAG_DISPLAY  (default 0) -- the ON-LCD diagnostic overlay (boot heap
//                 splash + perf HUD strip + the full 1..126 I2C bus scan).
//                 OFF = clean operator display. Set -DDIAG_DISPLAY=1 for
//                 on-screen bring-up info. (Has no effect unless DEBUG_HUD is
//                 also on.)

// ===================== [B] DEFAULTS (FACTORY STATE) =========================
// The factory STARTING state of the run-time-editable settings. These are the
// single source of truth for the device's power-on defaults: prop_rx.cpp seeds
// its live state from these in begin() BEFORE loading NVS, so a saved value
// from the Settings screen STILL OVERRIDES them. They only take effect on a
// fresh flash (or after the matching NVS blob is wiped / version-bumped).
//
// ----- Factory per-channel colour (prop_colors preset index per channel) -----
// Index into prop_colors::COLOR_PRESETS (see [C]/the recipe list for the names).
// Current factory mapping = green / red / green / white / green:
//   ch0 (button1) = 1 ZELENA | ch1 (button2) = 0 CERVENA | ch2 (switch) = 1 ZELENA
//   ch3 (odpal)   = 3 BILA   | ch4 (remote)  = 1 ZELENA
constexpr std::uint8_t DEFAULT_LED_PRESET_IDX[LED_COUNT] = {1, 0, 1, 3, 1};

// ----- Factory per-channel brightness (0..255) -------------------------------
// Every channel starts at this brightness on a fresh flash (the Jas page edits
// it per channel afterwards, persisted to NVS). Equals LOCAL_BRIGHTNESS today.
constexpr std::uint8_t DEFAULT_LED_BRIGHTNESS = LOCAL_BRIGHTNESS;

// ----- Factory odpal (fire-flash) envelope -----------------------------------
// The SK6812 #4 flash shape out of the box: ramp-up -> hold -> fade-out (ms)
// plus the ramp/fade curve. The Cas page edits these (clamped to ODPAL_MAX_MS,
// stepped by ODPAL_STEP_MS -- both in section [8]) and persists them to NVS.
constexpr std::uint16_t DEFAULT_ODPAL_RAMP_MS = 150;   // nabeh: ramp-up duration
constexpr std::uint16_t DEFAULT_ODPAL_HOLD_MS = 400;   // svit: full-on hold duration
constexpr std::uint16_t DEFAULT_ODPAL_FADE_MS = 650;   // zhasnuti: fade-out duration
constexpr std::uint8_t  DEFAULT_ODPAL_CURVE   = 0;     // index into ODPAL_CURVE_NAMES: 0=HRANA 1=LIN 2=SINUS

// ========================= [C] NAMED LED ROLES ==============================
// Human names for the logical channels, so LED_ORDER / DEFAULT_LED_PRESET_IDX /
// the per-channel arrays read clearly. The INDEX is the logical channel
// (0..LED_COUNT-1); the wired physical pixel is LED_ORDER[index].
//
//   index 0  LED_ROLE_BUTTON1 -- local toggle button 1   (edge -> on/off)
//   index 1  LED_ROLE_BUTTON2 -- local toggle button 2   (edge -> on/off)
//   index 2  LED_ROLE_SWITCH  -- physical switch level + Dial remote-#3
//   index 3  LED_ROLE_ODPAL   -- odpal / FIRE flash       (envelope in [B]/[8])
//   index 4  LED_ROLE_REMOTE  -- Dial remote-only status LED (#5)
constexpr int LED_ROLE_BUTTON1 = 0;
constexpr int LED_ROLE_BUTTON2 = 1;
constexpr int LED_ROLE_SWITCH  = 2;
constexpr int LED_ROLE_ODPAL   = 3;
constexpr int LED_ROLE_REMOTE  = 4;

// XIAO drives four discrete status LEDs plus the 18-pixel barrel. The barrel is
// the ODPAL role; the four standalone LEDs keep the remaining visible roles.
constexpr std::uint8_t XIAO_STATUS_LED_CHANNELS[XIAO_STATUS_LED_COUNT] = {
    LED_ROLE_BUTTON1,
    LED_ROLE_BUTTON2,
    LED_ROLE_SWITCH,
    LED_ROLE_REMOTE,
};

// ========================== [D] SANITY CHECKS ===============================
// Compile-time validation of the knobs above. If you set something out of
// range, the build FAILS HERE with the message below -- a typo is caught now,
// not on the bench. Do not edit this block; fix the offending value instead.

static_assert(LED_COUNT >= 1 && LED_COUNT <= LED_STRIP_MAX,
              "[1] LED_COUNT must be in [1, LED_STRIP_MAX] (the strip buffer must hold every channel)");
static_assert(LED_STRIP_MAX >= 1,
              "[1] LED_STRIP_MAX must be at least 1");

static_assert(LED_CURRENT_BUDGET_MA > 0,
              "[2] LED_CURRENT_BUDGET_MA must be > 0 (a zero budget forces the whole strip dark)");
static_assert(WS2812_CHANNEL_MA > 0,
              "[2] WS2812_CHANNEL_MA must be > 0 (the current model divides by the per-pixel draw)");
// WS2812_IDLE_MA may legitimately be 0 (some users model no idle draw), so it is not range-checked.

// ByteButton input indices: each in [0,7] (the unit has 8 inputs) and all four distinct,
// or two functions would share one physical input.
static_assert(BB_SWITCH_IDX < 8 && BB_BTN1_IDX < 8 && BB_BTN2_IDX < 8 && BB_FIRE_IDX < 8,
              "[3] BB_*_IDX must each be < 8 (the ByteButton has 8 inputs, 0..7)");
static_assert(BB_SWITCH_IDX != BB_BTN1_IDX && BB_SWITCH_IDX != BB_BTN2_IDX && BB_SWITCH_IDX != BB_FIRE_IDX &&
              BB_BTN1_IDX  != BB_BTN2_IDX  && BB_BTN1_IDX  != BB_FIRE_IDX  &&
              BB_BTN2_IDX  != BB_FIRE_IDX,
              "[3] BB_SWITCH/BTN1/BTN2/FIRE indices must all be distinct (one input per function)");

// Curve catalogue: the name table and the declared count must agree, or
// ODPAL_CURVE_NAMES[curve] indexing in the UI can read past the array.
static_assert(NUM_ODPAL_CURVES == static_cast<int>(sizeof(ODPAL_CURVE_NAMES) / sizeof(ODPAL_CURVE_NAMES[0])),
              "[8] NUM_ODPAL_CURVES must equal the number of entries in ODPAL_CURVE_NAMES");
static_assert(ODPAL_MAX_MS > 0 && ODPAL_STEP_MS > 0,
              "[8] ODPAL_MAX_MS and ODPAL_STEP_MS must both be > 0");

// Factory colour indices must each name a real prop_colors preset.
static_assert(DEFAULT_LED_PRESET_IDX[0] < prop_colors::NUM_COLOR_PRESETS &&
              DEFAULT_LED_PRESET_IDX[1] < prop_colors::NUM_COLOR_PRESETS &&
              DEFAULT_LED_PRESET_IDX[2] < prop_colors::NUM_COLOR_PRESETS &&
              DEFAULT_LED_PRESET_IDX[3] < prop_colors::NUM_COLOR_PRESETS &&
              DEFAULT_LED_PRESET_IDX[4] < prop_colors::NUM_COLOR_PRESETS,
              "[B] each DEFAULT_LED_PRESET_IDX must be < prop_colors::NUM_COLOR_PRESETS (a valid preset)");

// Factory odpal envelope must fit inside the per-phase edit clamp and name a real curve.
static_assert(DEFAULT_ODPAL_RAMP_MS <= ODPAL_MAX_MS &&
              DEFAULT_ODPAL_HOLD_MS <= ODPAL_MAX_MS &&
              DEFAULT_ODPAL_FADE_MS <= ODPAL_MAX_MS,
              "[B] each DEFAULT_ODPAL_*_MS must be <= ODPAL_MAX_MS (within the per-phase edit clamp)");
static_assert(DEFAULT_ODPAL_CURVE < NUM_ODPAL_CURVES,
              "[B] DEFAULT_ODPAL_CURVE must be < NUM_ODPAL_CURVES (a valid curve index)");

// Named roles must address real channels.
static_assert(LED_ROLE_BUTTON1 < LED_COUNT && LED_ROLE_BUTTON2 < LED_COUNT &&
              LED_ROLE_SWITCH  < LED_COUNT && LED_ROLE_ODPAL   < LED_COUNT &&
              LED_ROLE_REMOTE  < LED_COUNT,
              "[C] every LED_ROLE_* must be < LED_COUNT (an addressable logical channel)");
static_assert(XIAO_STATUS_LED_COUNT == 4,
              "[4] XIAO_STATUS_LED_COUNT must stay 4 to match the STAT4 UART contract");
static_assert(XIAO_BARREL_WS2812_COUNT == 18,
              "[4] XIAO_BARREL_WS2812_COUNT must match the installed barrel strip");
static_assert(XIAO_STATUS_LED_CHANNELS[0] < LED_COUNT && XIAO_STATUS_LED_CHANNELS[1] < LED_COUNT &&
              XIAO_STATUS_LED_CHANNELS[2] < LED_COUNT && XIAO_STATUS_LED_CHANNELS[3] < LED_COUNT,
              "[C] XIAO_STATUS_LED_CHANNELS must address real logical LED channels");

}  // namespace prop_config
