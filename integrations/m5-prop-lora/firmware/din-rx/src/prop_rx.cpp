#include "prop_rx.h"

#include "factory_test/factory_test.h"
#include <Wire.h>
#include <seesaw_neopixel.h>   // Adafruit NeoDriver: SK6812 over I2C (defines NEO_* itself; do NOT also include Adafruit_NeoPixel.h here)
#include <unit_byte.hpp>       // M5 Unit ByteButton: switch + buttons over I2C
#include <Arduino.h>
#include "driver/gpio.h"
#include <esp_system.h>
#include <Preferences.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "prop_colors.h"
#include "prop_protocol.h"
#include "prop_runtime_key.h"
#include "prop_xiao_link.h"
#include "terminal_setup_receiver.h"
#include "prop_config.h"   // Marlin-style tuning/configuration (all user knobs)
#include "fonts/din_bold_8.h"
#include "fonts/din_bold_15.h"
#include "fonts/din_bold_23.h"
#include "fonts/din_reg_8.h"
#include "fonts/din_reg_15.h"
#include "fonts/din_reg_23.h"
#include "ui_theme_generated.h"   // colours + layout: single source tools/m5_theme.json (gen: tools/gen_firmware_theme.py)

#ifndef DEBUG_HUD
#define DEBUG_HUD 1
#endif

// DIAG_DISPLAY: the on-LCD diagnostic overlay (boot heap splash + perf HUD strip).
// OFF (default) = clean operator display. USB serial telemetry ([hb]/[bb]) stays under
// DEBUG_HUD so bring-up logging via read_com.py still works; build with -DDEBUG_HUD=0
// to compile out ALL diagnostics (display + serial + per-loop stats) for a release flash.
#ifndef DIAG_DISPLAY
#define DIAG_DISPLAY 0
#endif

#if DEBUG_HUD
#include <esp_system.h>
#include <esp_timer.h>
#endif

namespace
{
using namespace prop_config;   // user knobs live in prop_config.h (Marlin-style Configuration)

using prop_colors::ColorPreset;
using prop_colors::COLOR_PRESETS;
using prop_colors::NUM_COLOR_PRESETS;

constexpr std::uint32_t LED_COLORS_MAGIC  = 0x4C454443;   // 'LEDC'
constexpr std::uint8_t  LED_COLORS_VERSION_V1 = 1;
constexpr std::uint8_t  LED_COLORS_VERSION = 4;   // v4: re-defaulted ch0=green/ch1=red for the wired LED order; v3 was the 4->5 blob grow
constexpr const char*   LED_COLORS_KEY    = "ledc1";
constexpr std::uint32_t LED_BRIGHTNESS_MAGIC = 0x4C425254; // 'LBRT'
constexpr std::uint8_t  LED_BRIGHTNESS_VERSION = 2;   // v2: LED_COUNT 4->5 grew the blob (value[]), discard old 4-wide blob
constexpr const char*   LED_BRIGHTNESS_KEY = "ledbrite";
constexpr std::uint32_t TERMINAL_SETUP_MAGIC = 0x54534554; // 'TSET'
constexpr std::uint8_t  TERMINAL_SETUP_VERSION = 1;
constexpr const char*   TERMINAL_SETUP_KEY = "tset1";
constexpr std::uint32_t ODPAL_CFG_MAGIC   = 0x4F44504C;   // 'ODPL'
constexpr std::uint8_t  ODPAL_CFG_VERSION = 1;
constexpr const char*   ODPAL_CFG_KEY     = "odpl1";
constexpr std::uint8_t TERMINAL_ODPAL_LANE = 3;
constexpr std::uint8_t DEFAULT_TERMINAL_EFFECT_PREVIEW_MASK =
    static_cast<std::uint8_t>(1U << TERMINAL_ODPAL_LANE);
constexpr std::uint8_t PROP_SOURCE = 0x22;
constexpr std::uint8_t PROP_DESTINATION = 0x11;
constexpr int SCREEN_W = 240;
constexpr int SCREEN_H = 135;
// Layout / geometry (STATUS_H, SPINE_W, PLOT_*, EFEKT_*, PALETTE_Y, ROW_*, PLOT_MAX_CYCLES)
// now come from ui_theme_generated.h (single source: tools/m5_theme.json).

#if DEBUG_HUD
constexpr std::uint32_t DEBUG_HUD_BOOT_MS = 1500;
constexpr std::uint32_t DEBUG_HUD_REFRESH_MS = 500;
#endif

// Shared theme colours (COLOR_BG/TEXT/MUTED/GOOD/WARN/BAD/BLUE/KLID/TEAL, CHIP_KLID_BG/TEXT)
// now come from ui_theme_generated.h (single source: tools/m5_theme.json).
// Derived + firmware-only colours stay here (not part of the shared theme JSON):
constexpr std::uint32_t SELECT_BG = 0x26313B;
constexpr std::uint32_t LABEL_DIM = 0x88898B;
constexpr std::uint32_t TRACK_DIM = 0x22292B;

// Palette persistence (Stage B5): a SEPARATE NVS key from the effect config so the
// received PALETTE_SET survives a receiver-only reboot mid-show without coupling to
// the effect-config blob layout/version. DMP1 = "DinMeter Palette v1".
constexpr std::uint32_t EFFECT_PALETTE_MAGIC = 0x444D5031UL; // DMP1
constexpr std::uint8_t EFFECT_PALETTE_VERSION = 1;
constexpr const char* EFFECT_PALETTE_KEY = "pal1";

HardwareSerial propSerial(1);
HardwareSerial propIoSerial(2);
seesaw_NeoPixel pixels(LED_STRIP_MAX, NEODRIVER_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800, &Wire1);
UnitByte byteBtn;   // M5 Unit ByteButton on the Port B I2C bus
Preferences preferences;

void useUiFont(LGFX_Sprite* canvas, int tier, bool bold)
{
    const uint8_t* arr =
        tier <= 1 ? (bold ? din_bold_8  : din_reg_8)  :
        tier == 2 ? (bold ? din_bold_15 : din_reg_15) :
                    (bold ? din_bold_23 : din_reg_23);
    // Cache: loadFont parses the glyph table on every call; skip it when the font is
    // unchanged. Safe because after the VLW port ALL UI text goes through useUiFont,
    // so the cached pointer stays in sync with the canvas's active font.
    static const std::uint8_t* loaded = nullptr;
    if (arr != loaded)
    {
        canvas->loadFont(arr);
        loaded = arr;
    }
    canvas->setTextSize(1);
}

#if DEBUG_HUD
struct DebugHudStats
{
    std::uint32_t loopMaxUs = 0;
    std::uint32_t loopLastShowMs = 0;
    std::uint32_t rxTotal = 0;
    std::uint32_t rxEspnow = 0;
    std::uint32_t rxLora = 0;
    std::uint32_t rxValid = 0;
    std::uint32_t rxDup = 0;
    std::uint32_t rxStale = 0;
    std::uint32_t rxBad = 0;
    std::uint32_t ackSent = 0;
    std::uint32_t healthForeign = 0;
    std::uint32_t healthQdrop = 0;
    std::uint32_t healthRxfree = 0;
    std::uint32_t minFreeHeap = 0xFFFFFFFF;
    const char* bootReason = "?";
};

const char* resetReasonName(esp_reset_reason_t reason)
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
#endif

struct RenderColor
{
    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;
    RenderColor() = default;
    RenderColor(std::uint8_t rr, std::uint8_t gg, std::uint8_t bb) : r(rr), g(gg), b(bb) {}
};

// Persisted palette blob (Stage B5). Fixed-size (MAX_PALETTE_COLORS slots) so the
// stored length is constant regardless of how many colors are active -> a simple
// length+magic+version+checksum validation on load, identical to the effect config.
struct __attribute__((packed)) PersistedPalette
{
    std::uint32_t magic = EFFECT_PALETTE_MAGIC;
    std::uint8_t version = EFFECT_PALETTE_VERSION;
    std::uint8_t count = 0;       // active colors, 0..MAX_PALETTE_COLORS
    std::uint8_t fade = 0;        // bool: smooth vs hard
    std::uint8_t paletteRev = 0;  // Dial-side revision (carried for parity, not validated)
    std::uint8_t rgb[prop_protocol::MAX_PALETTE_COLORS][3] = {};
    std::uint32_t checksum = 0;
};

struct PersistedLedColorsV1
{
    std::uint32_t magic;
    std::uint8_t  version;
    std::uint8_t  idx[LED_COUNT];
    std::uint32_t checksum;
};

struct PersistedLedColors
{
    std::uint32_t magic;
    std::uint8_t  version;
    std::uint8_t  idx[LED_COUNT];
    std::uint8_t  rgb[LED_COUNT][3];
    std::uint32_t checksum;
};

struct __attribute__((packed)) PersistedLedBrightness
{
    std::uint32_t magic;
    std::uint8_t  version;
    std::uint8_t  value[LED_COUNT];
    std::uint32_t checksum;
};

struct __attribute__((packed)) PersistedTerminalSetup
{
    std::uint32_t magic;
    std::uint8_t  version;
    std::uint8_t  onMask;
    std::uint8_t  effectMask;
    std::uint8_t  brightness[LED_COUNT];
    std::uint8_t  rgb[LED_COUNT][3];
    std::uint32_t checksum;
};

struct StaticColorFade
{
    RenderColor start;
    RenderColor target;
    RenderColor current;
    std::uint32_t startMs = 0;
    bool active = false;
};

// LED4 odpal brightness envelope: ramp-up (nabeh) -> hold (svit) -> fade-out (zhasnuti),
// each in ms, plus the curve SHAPE applied to the ramp/fade ramps. Colour = the LED4 preset
// (_ledColorIdx[3]). Editable on the DinMeter Settings screen, persisted to its own NVS blob.
struct OdpalEnvelope
{
    std::uint16_t rampMs = 150;
    std::uint16_t holdMs = 400;
    std::uint16_t fadeMs = 650;
    std::uint8_t  curve  = 0;     // index into ODPAL_CURVE_NAMES: 0=HRANA 1=LIN 2=SINUS
};

struct PersistedOdpal
{
    std::uint32_t magic;
    std::uint8_t  version;
    std::uint16_t rampMs;
    std::uint16_t holdMs;
    std::uint16_t fadeMs;
    std::uint8_t  curve;
    std::uint32_t checksum;
};

enum class UiPage
{
    Stav,
    Barvy,
    Cas,
    Jas
};

enum class ReplayDecision : std::uint8_t
{
    EXECUTE,
    DROP_DUP,
    DROP_STALE
};

std::uint8_t clampByte(int value)
{
    return static_cast<std::uint8_t>(std::max(0, std::min(255, value)));
}

std::uint8_t scaleByteRound(std::uint8_t value, std::uint8_t scale)
{
    return static_cast<std::uint8_t>(
        (static_cast<std::uint32_t>(value) * scale + 127U) / 255U);
}

std::uint8_t scaleByteRound(std::uint8_t value, std::uint8_t scaleA, std::uint8_t scaleB)
{
    constexpr std::uint32_t denom = 255U * 255U;
    return static_cast<std::uint8_t>(
        (static_cast<std::uint32_t>(value) * scaleA * scaleB + denom / 2U) / denom);
}

bool sameColor(const RenderColor& a, const RenderColor& b)
{
    return a.r == b.r && a.g == b.g && a.b == b.b;
}

RenderColor presetRenderColor(std::uint8_t idx)
{
    const ColorPreset& p = COLOR_PRESETS[idx < NUM_COLOR_PRESETS ? idx : 0];
    return RenderColor(p.r, p.g, p.b);
}

RenderColor lerpColor(const RenderColor& from, const RenderColor& to,
                      std::uint32_t elapsedMs, std::uint32_t durationMs)
{
    if (durationMs == 0 || elapsedMs >= durationMs)
        return to;
    const auto mix = [elapsedMs, durationMs](std::uint8_t a, std::uint8_t b) -> std::uint8_t
    {
        const int delta = static_cast<int>(b) - static_cast<int>(a);
        const int value = static_cast<int>(a) + delta * static_cast<int>(elapsedMs) / static_cast<int>(durationMs);
        return clampByte(value);
    };
    return RenderColor(mix(from.r, to.r), mix(from.g, to.g), mix(from.b, to.b));
}

std::uint32_t rgb(std::uint8_t r, std::uint8_t g, std::uint8_t b)
{
    return (static_cast<std::uint32_t>(r) << 16) |
           (static_cast<std::uint32_t>(g) << 8) |
           static_cast<std::uint32_t>(b);
}

std::uint32_t dimRgb(std::uint32_t color, std::uint8_t level)
{
    const std::uint8_t r = static_cast<std::uint8_t>(((color >> 16) & 0xFF) * level / 255);
    const std::uint8_t g = static_cast<std::uint8_t>(((color >> 8) & 0xFF) * level / 255);
    const std::uint8_t b = static_cast<std::uint8_t>((color & 0xFF) * level / 255);
    return rgb(r, g, b);
}

std::uint32_t checksumBytes(const std::uint8_t* data, std::size_t len)
{
    std::uint32_t hash = 2166136261UL;
    for (std::size_t i = 0; i < len; ++i)
    {
        hash ^= data[i];
        hash *= 16777619UL;
    }
    return hash;
}

class PropRxApp
{
public:
    explicit PropRxApp(FactoryTest* ft) : _ft(ft) {}

    void begin()
    {
#if DEBUG_HUD
        _debug.bootReason = resetReasonName(esp_reset_reason());
        // Only arm the on-screen boot splash when the display diagnostics are enabled;
        // with DIAG_DISPLAY off the boot HUD never shows (clean operator screen).
        _debugBootUntilMs = DIAG_DISPLAY ? (millis() + DEBUG_HUD_BOOT_MS) : 0;
#endif
        preferences.begin("prop_rx", false);
        loadRuntimeKey();
        // FACTORY DEFAULTS (single source of truth = prop_config.h section [B]).
        // Seed the live LED colour/brightness + odpal envelope from the config
        // defaults BEFORE any NVS load below, so a fresh flash reproduces the
        // configured factory state AND a valid saved blob still overrides it
        // (loadLedColors/loadOdpalCfg/loadLedBrightness all run after this).
        for (int i = 0; i < LED_COUNT; ++i)
        {
            _ledColorIdx[i]   = DEFAULT_LED_PRESET_IDX[i];
            _ledColors[i]     = presetRenderColor(_ledColorIdx[i]);
            _ledBrightness[i] = DEFAULT_LED_BRIGHTNESS;
        }
        _odpal.rampMs = DEFAULT_ODPAL_RAMP_MS;
        _odpal.holdMs = DEFAULT_ODPAL_HOLD_MS;
        _odpal.fadeMs = DEFAULT_ODPAL_FADE_MS;
        _odpal.curve  = DEFAULT_ODPAL_CURVE;
        if (DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
        {
            loadPalette();   // bench/legacy local editor state
            loadLedColors(); // bench/legacy local editor state
        }
        // Seed the Dial-pushed colour buffer from the persisted defaults so it is never
        // stale-zero before the first PaletteSet. Guards LED#5 (idx4): applyLedPayload seeds
        // channel 4 from this buffer, and a RemoteLed LED5-ON arriving before any palette must
        // light the configured colour, not black. _dialColorsValid stays false until a real
        // Dial push, so localColor() still falls back to _ledColors until then.
        for (int i = 0; i < LED_COUNT; ++i)
            _dialColors[i] = _ledColors[i];
        if (DINMETER_LOCAL_SETUP_EDITOR_ENABLED && _hasPalette)
            reflectPaletteColors(false); // re-apply boot-restored palette without a redundant NVS write
        if (DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
            loadOdpalCfg();  // bench/legacy local editor state
        _txEpoch = esp_random();   // unique TX epoch for DinMeter-originated colour-sync frames
        if (DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
            loadLedBrightness();
        loadTerminalSetupState();  // authoritative Terminal setup blob: colors + brightness + on/effect masks
        _lastAcceptedSequence = preferences.getUInt("lastSeq", 0);
        _lastPersistedSequence = _lastAcceptedSequence;
        _lastEpoch = preferences.getUInt("epoch", 0);
        _rxWindowBase = _lastAcceptedSequence;
        // After a receiver-only reboot mid-session the per-frame replay mask is gone, so
        // treat the whole window below the persisted base as ALREADY SEEN (all-ones) to
        // block re-firing up to 32 already-executed sequences. Only NEW sequences (> base)
        // advance; a genuine new Dial session resets this via the epoch branch. (Zero NVS.)
        _rxWindowMask = 0xFFFFFFFFu;
        // Active physical LED count. The rig is a fixed 4x SK6812. The "nLeds" NVS key was
        // READ here but is NEVER written anywhere in the firmware, so a stale/garbage value
        // (e.g. 2 or 3) would stick forever -- collapsing channelForLed's mapping so LED2/LED4
        // never get data ("only ~2 LEDs run"). Force the known hardware count and scrub any
        // bad persisted value once so the rig self-heals.
        _activeLeds = LED_COUNT;
        if (preferences.getUInt("nLeds", LED_COUNT) != static_cast<std::uint32_t>(LED_COUNT))
            preferences.putUInt("nLeds", LED_COUNT);

        Serial.begin(115200);   // bring USB-CDC up first so the boot scan output is visible
        // NOTE: do NOT probe Port A (G13/G15) as I2C -- the C6L modem drives those UART pins
        // (push-pull) and the contention hangs the bus. Port B is the only I2C bus here.

        propSerial.setRxBufferSize(512);   // headroom so a slow Port-B I2C burst can't overflow the modem RX ring
        propSerial.begin(MODEM_BAUD, SERIAL_8N1, UART1_RX_PIN, UART1_TX_PIN);
        // 0.4 root-fix: idle-high the modem UART via internal pull-ups (see Dial side):
        // a booting/disconnected peer never reads as boot garbage at either end.
        gpio_pullup_en((gpio_num_t)UART1_TX_PIN);
        gpio_pullup_en((gpio_num_t)UART1_RX_PIN);
        // --- Prop I/O bus on Port B (G1/G2) = Wire1. RTC keeps Wire; modem keeps UART. ---
        Serial.begin(115200);   // USB-serial bring-up diagnostics (harmless if already up)
        // Port B (G1/G2) I2C orientation auto-detect: try SDA=G2/SCL=G1, and if NEITHER target
        // device (ByteButton 0x47 / NeoDriver 0x60) answers, retry with the pins swapped -- so the
        // Grove cable orientation never silently breaks the bus. Whichever order responds is used
        // for byteBtn.begin too.
        // BOOT SPEEDUP: probe ONLY the two target addresses for the orientation decision instead of
        // sweeping all 126 (a stalled/empty bus at 15ms/addr was up to 126*15=1890ms, doubled to
        // ~3.8s with the swapped retry). The decision is also now based on TARGET hits, not total
        // device count, so an unrelated/spurious ACK no longer suppresses the swapped retry. A full
        // 126-address diagnostic scan still runs, but only when DIAG_DISPLAY is enabled.
        if (PROP_IO_XIAO_UART_ENABLED)
        {
            beginXiaoPropIo();
        }
        else
        {
        int sda = I2C_SDA_PIN, scl = I2C_SCL_PIN;
        Wire1.end();
        Wire1.begin(sda, scl, I2C_SPEED);
        Wire1.setTimeOut(15);   // bound every I2C transaction so a stalled bus never wedges the loop
        if (probeTargets() == 0)
        {
            Serial.println("[i2c] no target (0x47/0x60) on SDA=G2/SCL=G1 -> retry swapped (SDA=G1/SCL=G2)");
            std::swap(sda, scl);
            Wire1.end();
            Wire1.begin(sda, scl, I2C_SPEED);
            Wire1.setTimeOut(15);
            probeTargets();
        }
#if DIAG_DISPLAY
        scanI2cBus();   // full 1..126 diagnostic sweep (debug builds only; logs every responder)
#endif
        _i2cSda = sda;   // remember the resolved Port-B orientation for ByteButton hot-plug begin()
        _i2cScl = scl;

        // Inputs: M5 Unit ByteButton if present; otherwise fall back to the onboard
        // encoder + button emulation (so the rig is testable without the ByteButton module).
        if (_byteBtnPresent)
        {
            if (!byteBtn.begin(&Wire1, BYTEBUTTON_ADDR, sda, scl, I2C_SPEED))
            {
                Serial.println("[bb] ByteButton begin() failed @0x47 -> emulation");
                _byteBtnPresent = false;   // begin failed: fall back to encoder emulation, don't poll a dead unit
            }
            else
            {
                // BOOT edge-prime (parity with the hot-plug path in serviceByteButtonPresence):
                // seed _bbPrev1/2/3/_bbPrevSw + _switchEngaged from a VALIDATED 0/1 read BEFORE the
                // first poll, so a button/switch HELD at power-on cannot read as a fresh rising edge
                // and phantom-toggle a LED or phantom-FIRE the odpal. A bad (0xFF) read leaves the
                // prevs at their safe defaults and the first clean poll re-primes via the same gate.
                const std::uint8_t rsw = byteBtn.getSwitchStatus(BB_SWITCH_IDX);
                const std::uint8_t rb1 = byteBtn.getSwitchStatus(BB_BTN1_IDX);
                const std::uint8_t rb2 = byteBtn.getSwitchStatus(BB_BTN2_IDX);
                const std::uint8_t rb3 = byteBtn.getSwitchStatus(BB_FIRE_IDX);
                if (rsw <= 1 && rb1 <= 1 && rb2 <= 1 && rb3 <= 1)
                {
                    _bbPrevSw = (rsw == BB_PRESSED);
                    _bbPrev1  = (rb1 == BB_PRESSED);
                    _bbPrev2  = (rb2 == BB_PRESSED);
                    _bbPrev3  = (rb3 == BB_PRESSED);
                    _switchEngaged = _bbPrevSw;   // reflect a switch already engaged at boot (#3 priority input)
                    Serial.printf("[bb] boot-primed sw=%d b1=%d b2=%d fire=%d\n",
                                  _bbPrevSw, _bbPrev1, _bbPrev2, _bbPrev3);
                }
                else
                    Serial.println("[bb] boot prime read invalid (0xFF) -> will re-prime on first clean poll");
            }
        }
        else
            Serial.println("[bb] ByteButton 0x47 absent -> onboard encoder/button emulation active");

        // Output: 4x SK6812 RGBW via Adafruit NeoDriver (seesaw NeoPixel @0x60).
        if (_neoDriverPresent)
        {
            const bool seesawOk = pixels.begin(NEODRIVER_ADDR);
            Serial.printf("[neo] seesaw begin @0x%02X -> %s\n", NEODRIVER_ADDR,
                          seesawOk ? "OK (is a seesaw -> NeoDriver)" : "FAILED (device is NOT a seesaw)");
            // CRASH GUARD: the address ACKed during the scan (so _neoDriverPresent was set true),
            // but if pixels.begin() then FAILS the seesaw NeoPixel buffer is left uninitialised --
            // a later showBudgetedFrame()->setPixelColor()/show() on it can crash. Clear the flag so
            // ALL LED writes are skipped (showBudgetedFrame early-returns) and the UI shows CHYBA.
            _neoDriverPresent = seesawOk;
            if (seesawOk)   // only drive it if it really is a seesaw (else writes can wedge the bus)
            {
                pixels.updateLength(LED_COUNT);   // buffer sized to the real strip (was LED_STRIP_MAX=30
                                                  // -> a 120-byte clear() per frame; now 16 bytes)
#if CONFIG_BOOT_SELFTEST   // prop_config.h [A]: 1 = run the dead-pixel chase; 0 = instant boot (strip still cleared below)
                // Boot self-test: walk EACH pixel individually through R,G,B,W (a "chase") so a
                // dead first pixel / cold DIN solder is visually UNAMBIGUOUS vs a dead chain --
                // this is what tells whether the "LED1 dark" report is a hardware fault.
                // Per-pixel dwell = BOOT_SELFTEST_DWELL_MS (config [A]; default 40ms, was 150ms).
                // The dwell is split into ~10ms slices that PUMP readModem() and ABORT on a
                // STOP/e-stop frame, so an e-stop during boot is serviced instead of waiting out
                // the whole diagnostic. (Default 40 -> 4 slices of 10ms == prior behaviour.)
                pixels.setBrightness(LOCAL_BRIGHTNESS);
                static const std::uint8_t kSelfTest[4][4] =
                    {{70, 0, 0, 0}, {0, 70, 0, 0}, {0, 0, 70, 0}, {0, 0, 0, 70}};   // R, G, B, W
                // Slice the configured dwell into ~10ms chunks (at least one) so the modem is
                // pumped roughly every 10ms regardless of the dwell value, then add any leftover.
                constexpr std::uint32_t kDwellSlice = 10;   // ms per modem-pump slice
                const int dwellSlices = static_cast<int>(BOOT_SELFTEST_DWELL_MS / kDwellSlice);
                const std::uint32_t dwellRemainder = BOOT_SELFTEST_DWELL_MS % kDwellSlice;
                bool aborted = false;
                for (int phase = 0; phase < 4 && !aborted; ++phase)
                    for (int i = 0; i < _activeLeds && !aborted; ++i)
                    {
                        pixels.clear();
                        pixels.setPixelColor(i, kSelfTest[phase][0], kSelfTest[phase][1],
                                             kSelfTest[phase][2], kSelfTest[phase][3]);
                        pixels.show();
                        // Pump the modem across the dwell so a STOP during boot aborts the chase.
                        for (int t = 0; t < dwellSlices && !aborted; ++t)
                        {
                            readModem();
                            if (_lockout) aborted = true;   // STOP frame arrived -> bail out of the self-test
                            else delay(kDwellSlice);
                        }
                        if (!aborted)
                        {
                            readModem();
                            if (_lockout) aborted = true;
                            else if (dwellRemainder) delay(dwellRemainder);   // leftover < one slice
                        }
                    }
#endif  // CONFIG_BOOT_SELFTEST
                // ALWAYS (even with the self-test skipped): init the strip to a known-dark state
                // so the first runtime frame writes cleanly through the content-guard.
                pixels.setBrightness(0);
                pixels.clear();
                pixels.show();
                _forceShow = true;   // make the first runtime frame always write through the content-guard
            }
        }
        else
            Serial.printf("[neo] no module at 0x%02X -> LED output disabled\n", NEODRIVER_ADDR);
        }

        _lastEncoderPos = _ft ? _ft->_enc.getPosition() : 0;
        readBattery(true);
        setStatus(_runtimeKey.loaded() ? "KLID" : "KEY MISSING");
        render(true);
    }

    void end()
    {
        stopOutput(false);
        preferences.end();
    }

    void update()
    {
#if DEBUG_HUD
        const std::int64_t loopStartUs = esp_timer_get_time();
#endif
        readControls();
        if (PROP_IO_XIAO_UART_ENABLED)
            readXiaoPropIo();           // prop switch + 3 buttons via the Port B XIAO UART bridge
        else
        {
            serviceByteButtonPresence();   // hot-plug: bring up a ByteButton connected after boot
            readByteButton();    // prop switch + 2 buttons via the I2C ByteButton (module = primary input)
        }
        readModem();
        flushPendingAck();   // transmit any deferred fire-and-forget ack once due
        readUsbSetup();
        serviceDeferredPersistence(); // drain colour/palette NVS after ACKs, on a debounce timer
        updateBattery();
        serviceArmTtl();     // Sprint A: drop ARM back to SAFE after TTL if no Fire came
        if (_odpalActive)   // pace the #4 odpal redraw (~40 Hz) + end the flash when the envelope completes
        {
            const std::uint32_t nowMs = millis();
            if (nowMs - _odpalStartMs >= odpalTotalMs())   // lifecycle end (moved out of odpalColor getter)
            {
                _odpalActive = false;
                setStatus("KLID");
                markStatusDirty();
                markLocalDirty();   // push the final off frame
                _forceShow = true;
            }
            else if (nowMs - _lastOdpalDrawMs >= ODPAL_FRAME_MS)
            {
                _lastOdpalDrawMs = nowMs;
                markLocalDirty();
            }
        }
        serviceStaticColorFade();
        servicePreviewOverlay();
        applyLocalControlIfIdle();   // drive SK6812 #1-4 from local controls / odpal when no Dial effect owns the LEDs
        render(false);
#if DEBUG_HUD
        recordLoopStats(loopStartUs);
        const std::uint32_t hbNow = millis();
        if (hbNow - _lastHeartbeatMs >= 3000)
        {
            _lastHeartbeatMs = hbNow;
            // Telemetry for read_com.py (non-resetting reads see the live state).
            // led3 shows the EFFECTIVE #3 (live switch level OR remote-on), not the vestigial
            // _led3On latch; led5 = the remote-only #5 latch (no physical LED yet -> serial is
            // the only way to verify LED5). leds = #1 #2 #3eff; odpal = #4; led5 = #5.
            const bool xiaoFresh = xiaoLinkOk(hbNow);
            const bool ioIn = PROP_IO_XIAO_UART_ENABLED ? xiaoFresh : _byteBtnPresent;
            const bool ioOut = PROP_IO_XIAO_UART_ENABLED ? xiaoFresh : _neoDriverPresent;
            Serial.printf("[hb] bb=%d neo=%d found=0x%02X leds=%d%d%d odpal=%d led5=%d vin=%d\n",
                          ioIn ? 1 : 0, ioOut ? 1 : 0, _foundAddr & 0xFF,
                          _led1On ? 1 : 0, _led2On ? 1 : 0, (_switchEngaged || _led3RemoteOn) ? 1 : 0,
                          _odpalActive ? 1 : 0, _led5RemoteOn ? 1 : 0, _row);
        }
#endif
    }

    bool shouldExit() const
    {
        return _exitRequested;
    }

private:
#if DEBUG_HUD
    void recordLoopStats(std::int64_t loopStartUs)
    {
        _debug.minFreeHeap = std::min(_debug.minFreeHeap, esp_get_free_heap_size());

        const std::int64_t deltaUs = esp_timer_get_time() - loopStartUs;
        if (deltaUs <= 0)
            return;

        const std::uint32_t deltaUs32 = deltaUs > 0xFFFFFFFFLL
            ? 0xFFFFFFFFUL
            : static_cast<std::uint32_t>(deltaUs);
        _debug.loopMaxUs = std::max(_debug.loopMaxUs, deltaUs32);
    }
#endif

    void resetLedColorsFromPresets()
    {
        for (int i = 0; i < LED_COUNT; ++i)
            _ledColors[i] = presetRenderColor(_ledColorIdx[i]);
    }

    // On-device LED colours (Settings screen). V2 stores both the preset cursor and the
    // effective RGB, so arbitrary Dial colours survive a receiver reboot. V1 index-only
    // blobs still load and derive RGB from the saved presets.
    void loadLedColors()
    {
        PersistedLedColors blob;
        if (preferences.getBytesLength(LED_COLORS_KEY) == sizeof(blob) &&
            preferences.getBytes(LED_COLORS_KEY, &blob, sizeof(blob)) == sizeof(blob))
        {
            const std::uint32_t expected = checksumBytes(
                reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
            if (blob.magic == LED_COLORS_MAGIC && blob.version == LED_COLORS_VERSION && blob.checksum == expected)
            {
                for (int i = 0; i < LED_COUNT; ++i)
                {
                    _ledColorIdx[i] = (blob.idx[i] < NUM_COLOR_PRESETS) ? blob.idx[i] : 0;
                    _ledColors[i] = RenderColor(blob.rgb[i][0], blob.rgb[i][1], blob.rgb[i][2]);
                }
                return;
            }
        }

        PersistedLedColorsV1 oldBlob;
        if (preferences.getBytesLength(LED_COLORS_KEY) == sizeof(oldBlob) &&
            preferences.getBytes(LED_COLORS_KEY, &oldBlob, sizeof(oldBlob)) == sizeof(oldBlob))
        {
            const std::uint32_t expected = checksumBytes(
                reinterpret_cast<const std::uint8_t*>(&oldBlob), sizeof(oldBlob) - sizeof(oldBlob.checksum));
            if (oldBlob.magic == LED_COLORS_MAGIC && oldBlob.version == LED_COLORS_VERSION_V1 &&
                oldBlob.checksum == expected)
            {
                for (int i = 0; i < LED_COUNT; ++i)
                    _ledColorIdx[i] = (oldBlob.idx[i] < NUM_COLOR_PRESETS) ? oldBlob.idx[i] : 0;
                resetLedColorsFromPresets();
                return;
            }
        }

        resetLedColorsFromPresets();
    }

    bool storeLedColors(bool showBadge = true)
    {
        PersistedLedColors blob{};
        blob.magic = LED_COLORS_MAGIC;
        blob.version = LED_COLORS_VERSION;
        for (int i = 0; i < LED_COUNT; ++i)
        {
            blob.idx[i] = _ledColorIdx[i];
            blob.rgb[i][0] = _ledColors[i].r;
            blob.rgb[i][1] = _ledColors[i].g;
            blob.rgb[i][2] = _ledColors[i].b;
        }
        blob.checksum = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
        if (preferences.putBytes(LED_COLORS_KEY, &blob, sizeof(blob)) != sizeof(blob))
        {
            _savedUntilMs = 0;
            setStatus("SAVE ERR");
            markStatusDirty();
            return false;
        }
        if (showBadge)
        {
            _savedUntilMs = millis() + SAVED_BADGE_MS;
            setStatus("ULOZENO");
            markStatusDirty();
        }
        // A committed LOCAL colour edit must win over any stale persisted palette on the next
        // boot (boot applies pal1 AFTER ledc1). Drop pal1 so the just-saved ledc1 is authoritative.
        if (_localColorEditPending)
        {
            clearPersistedPalette();
            _localColorEditPending = false;
        }
        _ledColorsPersistDirty = false;
        return true;
    }

    void loadLedBrightness()
    {
        PersistedLedBrightness blob{};
        if (preferences.getBytesLength(LED_BRIGHTNESS_KEY) == sizeof(blob) &&
            preferences.getBytes(LED_BRIGHTNESS_KEY, &blob, sizeof(blob)) == sizeof(blob))
        {
            const std::uint32_t expected = checksumBytes(
                reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
            if (blob.magic == LED_BRIGHTNESS_MAGIC && blob.version == LED_BRIGHTNESS_VERSION &&
                blob.checksum == expected)
            {
                for (int i = 0; i < LED_COUNT; ++i)
                    _ledBrightness[i] = (blob.value[i] < 15) ? 15 : blob.value[i];
                return;
            }
        }

        // Migration path for the previous bare 4-byte "ledbrite" blob.
        std::uint8_t legacyPerLed[LED_COUNT] = {};
        if (preferences.getBytesLength(LED_BRIGHTNESS_KEY) == sizeof(legacyPerLed) &&
            preferences.getBytes(LED_BRIGHTNESS_KEY, legacyPerLed, sizeof(legacyPerLed)) == sizeof(legacyPerLed))
        {
            for (int i = 0; i < LED_COUNT; ++i)
                _ledBrightness[i] = (legacyPerLed[i] < 15) ? 15 : legacyPerLed[i];
            return;
        }

        const std::uint8_t legacy = static_cast<std::uint8_t>(std::min<std::uint32_t>(255,
            std::max<std::uint32_t>(15, preferences.getUInt("brite", LOCAL_BRIGHTNESS))));
        for (int i = 0; i < LED_COUNT; ++i)
            _ledBrightness[i] = legacy;
    }

    void loadTerminalSetupState()
    {
        PersistedTerminalSetup blob{};
        if (preferences.getBytesLength(TERMINAL_SETUP_KEY) != sizeof(blob) ||
            preferences.getBytes(TERMINAL_SETUP_KEY, &blob, sizeof(blob)) != sizeof(blob))
            return;

        const std::uint32_t expected = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
        if (blob.magic != TERMINAL_SETUP_MAGIC || blob.version != TERMINAL_SETUP_VERSION ||
            blob.checksum != expected)
            return;

        const std::uint8_t validMask = static_cast<std::uint8_t>((1U << LED_COUNT) - 1U);
        blob.onMask &= validMask;
        blob.effectMask &= validMask;
        for (int i = 0; i < LED_COUNT; ++i)
        {
            _ledColors[i] = RenderColor(blob.rgb[i][0], blob.rgb[i][1], blob.rgb[i][2]);
            _dialColors[i] = _ledColors[i];
            _ledBrightness[i] = blob.brightness[i];
        }
        _led1On = (blob.onMask & (1U << 0)) != 0;
        _led2On = (blob.onMask & (1U << 1)) != 0;
        _led3RemoteOn = (blob.onMask & (1U << 2)) != 0;
        _led5RemoteOn = (blob.onMask & (1U << 4)) != 0;
        _terminalEffectMask = blob.effectMask & validMask;
        _terminalPreviewMask = _terminalEffectMask;
    }

    bool storeTerminalSetup(const terminal_setup_apply::AppliedSetup& setup)
    {
        PersistedTerminalSetup blob{};
        blob.magic = TERMINAL_SETUP_MAGIC;
        blob.version = TERMINAL_SETUP_VERSION;
        blob.onMask = setup.onMask;
        blob.effectMask = setup.effectMask;
        for (int i = 0; i < LED_COUNT; ++i)
        {
            const terminal_setup_apply::AppliedLane& lane = setup.lanes[i];
            blob.brightness[i] = lane.brightness;
            blob.rgb[i][0] = lane.color.r;
            blob.rgb[i][1] = lane.color.g;
            blob.rgb[i][2] = lane.color.b;
        }
        blob.checksum = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));

        PersistedTerminalSetup existing{};
        if (preferences.getBytesLength(TERMINAL_SETUP_KEY) == sizeof(existing) &&
            preferences.getBytes(TERMINAL_SETUP_KEY, &existing, sizeof(existing)) == sizeof(existing) &&
            std::memcmp(&existing, &blob, sizeof(blob)) == 0)
            return true;

        if (preferences.putBytes(TERMINAL_SETUP_KEY, &blob, sizeof(blob)) != sizeof(blob))
        {
            _savedUntilMs = 0;
            setStatus("SAVE ERR");
            markStatusDirty();
            return false;
        }
        return true;
    }

    // LED4 odpal envelope persistence -- same magic/version/checksum pattern as the LED colours,
    // in its OWN NVS key so its layout is independent of the colour blob (no silent wipe).
    void loadOdpalCfg()
    {
        PersistedOdpal blob;
        if (preferences.getBytesLength(ODPAL_CFG_KEY) == sizeof(blob) &&
            preferences.getBytes(ODPAL_CFG_KEY, &blob, sizeof(blob)) == sizeof(blob))
        {
            const std::uint32_t expected = checksumBytes(
                reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
            if (blob.magic == ODPAL_CFG_MAGIC && blob.version == ODPAL_CFG_VERSION && blob.checksum == expected)
            {
                _odpal.rampMs = std::min<std::uint16_t>(blob.rampMs, ODPAL_MAX_MS);
                _odpal.holdMs = std::min<std::uint16_t>(blob.holdMs, ODPAL_MAX_MS);
                _odpal.fadeMs = std::min<std::uint16_t>(blob.fadeMs, ODPAL_MAX_MS);
                _odpal.curve  = (blob.curve < NUM_ODPAL_CURVES) ? blob.curve : 0;
            }
        }
    }

    bool storeOdpalCfg()
    {
        PersistedOdpal blob{};
        blob.magic = ODPAL_CFG_MAGIC;
        blob.version = ODPAL_CFG_VERSION;
        blob.rampMs = _odpal.rampMs;
        blob.holdMs = _odpal.holdMs;
        blob.fadeMs = _odpal.fadeMs;
        blob.curve  = _odpal.curve;
        blob.checksum = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));
        if (preferences.putBytes(ODPAL_CFG_KEY, &blob, sizeof(blob)) != sizeof(blob))
        {
            _savedUntilMs = 0;
            setStatus("SAVE ERR");
            markStatusDirty();
            return false;
        }
        return true;
    }

    // Stage B5: restore the last received palette from NVS on boot, so a receiver-only
    // reboot mid-show keeps the configured colors instead of reverting to no-palette.
    // Validates magic/version/checksum + a sane count; on any mismatch leaves the
    // RAM palette untouched (_hasPalette stays false -> default brightness rendering).
    void loadPalette()
    {
        PersistedPalette blob;
        if (preferences.getBytesLength(EFFECT_PALETTE_KEY) != sizeof(blob) ||
            preferences.getBytes(EFFECT_PALETTE_KEY, &blob, sizeof(blob)) != sizeof(blob))
            return;

        const std::uint32_t expected = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob),
            sizeof(blob) - sizeof(blob.checksum));
        if (blob.magic != EFFECT_PALETTE_MAGIC || blob.version != EFFECT_PALETTE_VERSION ||
            blob.checksum != expected)
            return;
        if (blob.count == 0 || blob.count > prop_protocol::MAX_PALETTE_COLORS)
            return;

        _paletteCount = blob.count;
        for (std::uint8_t i = 0; i < _paletteCount; ++i)
            _palette[i] = RenderColor(blob.rgb[i][0], blob.rgb[i][1], blob.rgb[i][2]);
        _paletteFade = blob.fade != 0;
        _paletteRev = blob.paletteRev;
        _hasPalette = true;
    }

    // Persist the live palette to its own NVS key. Called when a PALETTE_SET is
    // accepted. PALETTE_SET arrives only on a Dial-side change, so NVS wear is
    // bounded. No-op if there is no palette to store.
    bool storePalette()
    {
        if (!_hasPalette || _paletteCount == 0)
            return false;

        PersistedPalette blob;
        blob.count = _paletteCount;
        blob.fade = _paletteFade ? 1 : 0;
        blob.paletteRev = _paletteRev;
        for (std::uint8_t i = 0; i < _paletteCount; ++i)
        {
            blob.rgb[i][0] = _palette[i].r;
            blob.rgb[i][1] = _palette[i].g;
            blob.rgb[i][2] = _palette[i].b;
        }
        blob.checksum = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob),
            sizeof(blob) - sizeof(blob.checksum));
        PersistedPalette existing{};
        if (preferences.getBytesLength(EFFECT_PALETTE_KEY) == sizeof(existing) &&
            preferences.getBytes(EFFECT_PALETTE_KEY, &existing, sizeof(existing)) == sizeof(existing) &&
            std::memcmp(&existing, &blob, sizeof(blob)) == 0)
            return true;

        if (preferences.putBytes(EFFECT_PALETTE_KEY, &blob, sizeof(blob)) != sizeof(blob))
        {
            _savedUntilMs = 0;
            setStatus("SAVE ERR");
            markStatusDirty();
            return false;
        }
        _palettePersistDirty = false;
        return true;
    }

    // Drop the persisted palette blob (pal1) so it can no longer override locally-edited
    // LED colours (ledc1) on the NEXT boot. Rationale: boot order is loadLedColors() ->
    // reflectPaletteColors(), so a stale pal1 silently wins over a fresh local Barvy save.
    // Called ONLY when the operator commits a LOCAL colour edit (received PaletteSet frames
    // re-create pal1 immediately after, so this never erases a live-synced palette). The
    // in-RAM _palette/_hasPalette are intentionally left untouched, so the CURRENT session's
    // palette-fade rendering is unchanged -- only boot precedence flips to ledc1.
    void clearPersistedPalette()
    {
        if (preferences.getBytesLength(EFFECT_PALETTE_KEY) > 0)
            preferences.remove(EFFECT_PALETTE_KEY);
        _palettePersistDirty = false;   // cancel any deferred re-write of the now-stale palette
    }

    void readControls()
    {
        if (!_ft)
            return;

        const std::uint32_t now = millis();
        const long encoderPos = _ft->_enc.getPosition();
        if (encoderPos != _lastEncoderPos)
        {
            // The ESP32Encoder is attached half-quad (~2 counts per detent) and the raw
            // count also jitters +/-1 at detent edges. Accumulate raw counts and emit ONE
            // logical step per full detent: collapses 2 counts -> 1 step AND cancels +/-1
            // bounce, so a single click never over-shoots the selection or the value.
            const int delta = static_cast<int>(encoderPos - _lastEncoderPos);
            _lastEncoderPos = encoderPos;
            // Direction-aware collapse: if the new motion opposes a pending half-detent
            // remainder, flush it first -- otherwise a +1 jitter then a full -2 detent nets
            // -1, truncates to 0, and SWALLOWS the real click ("every other reversal eats a
            // detent"). Also flush a stale remainder after an idle gap so a half-turn rest
            // never biases the next turn. This is the encoder-reliability fix.
            if (_encAccum != 0 && (now - _encLastCountMs) > 150)
                _encAccum = 0;
            if (_encAccum != 0 && ((delta > 0) != (_encAccum > 0)))
                _encAccum = 0;
            _encAccum += delta;
            _encLastCountMs = now;
            const int steps = _encAccum / ENC_COUNTS_PER_DETENT;
            if (steps != 0)
            {
                _encAccum -= steps * ENC_COUNTS_PER_DETENT;
                handleEncoder(steps, now);
            }
        }

        const bool released = _ft->_btn_pwr.read();
        if (!released && !_buttonDown)
        {
            _buttonDown = true;
            _buttonDownMs = now;
        }
        else if (released && _buttonDown)
        {
            const std::uint32_t heldMs = now - _buttonDownMs;
            _buttonDown = false;
            if (heldMs >= LONG_PRESS_EXIT_MS)
                handleLongPress();
            else
                handleShortPress();
        }
    }

    void beginXiaoPropIo()
    {
        Wire1.end();   // Port B is UART in XIAO mode; leave the I2C backend electrically idle.
        propIoSerial.setRxBufferSize(256);
        propIoSerial.begin(PROP_IO_UART_BAUD, SERIAL_8N1, PROP_IO_UART_RX_PIN, PROP_IO_UART_TX_PIN);
        gpio_pullup_en((gpio_num_t)PROP_IO_UART_TX_PIN);
        gpio_pullup_en((gpio_num_t)PROP_IO_UART_RX_PIN);

        _byteBtnPresent = false;
        _neoDriverPresent = false;
        _xiaoIoPresent = false;
        _xiaoLine = "";
        _xiaoLine.reserve(prop_xiao_link::MAX_LINE_LENGTH);
        Serial.printf("[xiao] Port B UART enabled tx=G%d rx=G%d baud=%u barrel=%u stat=%u\n",
                      PROP_IO_UART_TX_PIN, PROP_IO_UART_RX_PIN,
                      static_cast<unsigned>(PROP_IO_UART_BAUD),
                      static_cast<unsigned>(XIAO_BARREL_WS2812_COUNT),
                      static_cast<unsigned>(XIAO_STATUS_LED_COUNT));
        _xiaoPingSeq = 1;
        sendXiaoLine(prop_xiao_link::formatHelloLine());
        sendXiaoLine(prop_xiao_link::formatPingLine(nextXiaoPingSeq()));
        _forceShow = true;
        markLocalDirty();
    }

    void sendXiaoLine(const std::string& line)
    {
        propIoSerial.println(line.c_str());
#if DEBUG_HUD
        Serial.printf("[xiao tx] %s\n", line.c_str());
#endif
    }

    bool xiaoLinkOk(std::uint32_t now) const
    {
        return _xiaoIoPresent && now - _xiaoLastSeenMs < 2500;
    }

    bool xiaoOutputReady(std::uint32_t now) const
    {
        return !PROP_IO_XIAO_UART_ENABLED || xiaoLinkOk(now);
    }

    std::uint16_t nextXiaoPingSeq()
    {
        const std::uint16_t sequence = _xiaoPingSeq;
        _xiaoPingSeq = _xiaoPingSeq >= prop_xiao_link::MAX_SEQUENCE ? 1 : static_cast<std::uint16_t>(_xiaoPingSeq + 1);
        return sequence;
    }

    void markXiaoOutputMissing()
    {
        _odpalActive = false;
        _forceShow = true;
        setStatus("XIAO?");
        markStatusDirty();
        markLocalDirty();
    }

    void readXiaoPropIo()
    {
        while (propIoSerial.available() > 0)
        {
            const char c = static_cast<char>(propIoSerial.read());
            if (c == '\r')
                continue;
            if (c == '\n')
            {
                if (!_xiaoLineOverflow && _xiaoLine.length() > 0)
                    handleXiaoLine(_xiaoLine);
                _xiaoLine = "";
                _xiaoLineOverflow = false;
                continue;
            }
            if (_xiaoLineOverflow)
                continue;
            if (_xiaoLine.length() >= prop_xiao_link::MAX_LINE_LENGTH - 1)
            {
                _xiaoLine = "";
                _xiaoLineOverflow = true;
                continue;
            }
            _xiaoLine += c;
        }

        const std::uint32_t now = millis();
        if (now - _xiaoLastPingMs >= 1000)
        {
            _xiaoLastPingMs = now;
            sendXiaoLine(prop_xiao_link::formatPingLine(nextXiaoPingSeq()));
        }
    }

    void handleXiaoLine(const String& line)
    {
        const auto parsed = prop_xiao_link::parseLine(line.c_str());
        if (parsed.kind == prop_xiao_link::CommandKind::Error)
        {
#if DEBUG_HUD
            Serial.printf("[xiao rx] bad line: %s\n", line.c_str());
#endif
            return;
        }

        _xiaoIoPresent = true;
        _xiaoLastSeenMs = millis();
#if DEBUG_HUD
        Serial.printf("[xiao rx] %s\n", line.c_str());
#endif

        switch (parsed.kind)
        {
            case prop_xiao_link::CommandKind::Hello:
                setStatus("XIAO OK");
                markStatusDirty();
                _forceShow = true;
                markLocalDirty();
                break;
            case prop_xiao_link::CommandKind::Ping:
                sendXiaoLine(prop_xiao_link::formatPongLine(parsed.sequence));
                break;
            case prop_xiao_link::CommandKind::Pong:
                break;
            case prop_xiao_link::CommandKind::Button:
                if (parsed.input.index == 1) _xiaoBtn1 = parsed.input.active;
                if (parsed.input.index == 2) _xiaoBtn2 = parsed.input.active;
                if (parsed.input.index == 3) _xiaoFire = parsed.input.active;
                applyLocalInputLevels(_xiaoSwitch, _xiaoBtn1, _xiaoBtn2, _xiaoFire, "xiao");
                break;
            case prop_xiao_link::CommandKind::Switch:
                _xiaoSwitch = parsed.input.active;
                applyLocalInputLevels(_xiaoSwitch, _xiaoBtn1, _xiaoBtn2, _xiaoFire, "xiao");
                break;
            case prop_xiao_link::CommandKind::Empty:
            case prop_xiao_link::CommandKind::Stat4:
            case prop_xiao_link::CommandKind::Barrel:
            case prop_xiao_link::CommandKind::Error:
                break;
        }
    }

    void applyLocalInputLevels(bool sw, bool b1, bool b2, bool b3, const char* source)
    {
        // Release the configurable STOP master-off inhibit on ANY real local input/edge (button
        // press or switch level change) -- cleared BEFORE the toggles below so this same edge then
        // drives the LED normally. No-op unless _stopClearsAllLocal raised the inhibit on a STOP.
        if (_masterOffInhibit &&
            ((b1 && !_bbPrev1) || (b2 && !_bbPrev2) || (b3 && !_bbPrev3) || (sw != _bbPrevSw)))
        {
            _masterOffInhibit = false;
            markLocalDirty();
        }

        // idx0 switch: LED#3 LOCAL follows the LIVE physical level (D3) -- #3 lights locally ONLY
        // while the switch is actually engaged (sw HIGH); the render gate reads _switchEngaged.
        // STRICT (D2): the LOW->HIGH (engage) edge clears any pending remote/menu-on for #3 so the
        // physical switch always wins and a stale latch can't outlive it.
        if (sw && !_bbPrevSw)     { _led3RemoteOn = false; markLocalDirty(); }   // engage edge: clear remote #3 (switch takes priority)
        if (sw != _bbPrevSw)      markLocalDirty();       // level changed -> re-arbitrate #3 promptly
        _switchEngaged = sw;                              // LIVE switch level (priority input for #3; remote ignored while HIGH)
        if (b1 && !_bbPrev1)      { _led1On = !_led1On;    markLocalDirty(); }   // button 1: edge -> toggle
        if (b2 && !_bbPrev2)      { _led2On = !_led2On;    markLocalDirty(); }   // button 2: edge -> toggle
        if (b3 && !_bbPrev3)      tryLocalFire();          // local FIRE button: edge -> odpal unless STOP lockout is latched
        _bbPrevSw = sw;
        _bbPrev1 = b1;
        _bbPrev2 = b2;
        _bbPrev3 = b3;

#if DEBUG_HUD
        // Bring-up aid: log the (polarity-resolved) input + LED latches on any change, so
        // press polarity and live-vs-latched button behaviour are visible on USB serial.
        const int snap = (sw ? 1 : 0) | (b1 ? 2 : 0) | (b2 ? 4 : 0) | (b3 ? 8 : 0);
        if (snap != _bbRawPrev)
        {
            Serial.printf("[%s] sw=%d b1=%d b2=%d fire=%d -> LED #1=%d #2=%d #3=%d odpal=%d\n",
                          source, sw, b1, b2, b3, _led1On, _led2On,
                          (_switchEngaged || _led3RemoteOn) ? 1 : 0, _odpalActive);
            _bbRawPrev = snap;
        }
#endif
    }

    // ---- Prop local controls (M5 Unit ByteButton) -> SK6812 #1..#3 -------------------
    // #1 <- button 1 (press toggles on/off), #2 <- button 2 (toggles), #3 <- switch level.
    // SK6812 #4 stays off here -- reserved for the LoRa "odpal"/Fire (TBD). Static colours
    // come from the Dial (Preview -> _dialColors) when available, else defaults red/red/green.
    // Hot-plug: the ByteButton may be connected AFTER boot (Filip plugs it in before the
    // Adafruit NeoDriver on the same Port-B bus). Probe for its ARRIVAL at a low rate (never
    // mid-odpal), and on detect bring it up + PRIME the edge state from the current levels so
    // a button held at plug-in can't fire a phantom toggle/odpal. Module = primary input.
    void serviceByteButtonPresence()
    {
        if (_byteBtnPresent || _odpalActive)
            return;
        const std::uint32_t now = millis();
        if (now - _bbPresenceMs < 750)
            return;
        _bbPresenceMs = now;
        Wire1.beginTransmission(BYTEBUTTON_ADDR);
        if (Wire1.endTransmission() != 0)
            return;   // still absent -> stay in encoder emulation
        byteBtn.begin(&Wire1, BYTEBUTTON_ADDR, _i2cSda, _i2cScl, I2C_SPEED);
        // Prime edges from a VALIDATED read (0/1 only). If the hot-plug read is bad (0xFF), stay
        // absent and retry next probe -- priming from a bad read would record a false "released"
        // and the first clean poll would fire a phantom edge (per regression review).
        const std::uint8_t rsw = byteBtn.getSwitchStatus(BB_SWITCH_IDX);
        const std::uint8_t rb1 = byteBtn.getSwitchStatus(BB_BTN1_IDX);
        const std::uint8_t rb2 = byteBtn.getSwitchStatus(BB_BTN2_IDX);
        const std::uint8_t rb3 = byteBtn.getSwitchStatus(BB_FIRE_IDX);
        if (rsw > 1 || rb1 > 1 || rb2 > 1 || rb3 > 1)
            return;   // bad prime read -> stay in EMU, try again on the next presence probe
        _bbPrevSw = (rsw == BB_PRESSED);
        _bbPrev1  = (rb1 == BB_PRESSED);
        _bbPrev2  = (rb2 == BB_PRESSED);
        _bbPrev3  = (rb3 == BB_PRESSED);
        _bbFailCount = 0;
        _bbLastPollMs = now;
        _byteBtnPresent = true;
        setStatus("MODUL OK");
        markStatusDirty();
    }

    void readByteButton()
    {
        if (!_byteBtnPresent)   // module absent -> presence is (re)acquired by serviceByteButtonPresence()
            return;
        const std::uint32_t now = millis();
        if (now - _bbLastPollMs < 25)   // throttle: bounded I2C, never a per-loop blocking burst
            return;
        _bbLastPollMs = now;
        // Validity gate: require an ACK before trusting any byte. A NACK (unplugged / marginal
        // bus) must NOT be read as "all pressed" -> that would phantom-fire the odpal. On
        // repeated failure fall back to EMU and FREEZE the latches (do not zero them).
        Wire1.beginTransmission(BYTEBUTTON_ADDR);
        if (Wire1.endTransmission() != 0)
        {
            if (++_bbFailCount >= 5)
                _byteBtnPresent = false;
            return;
        }
        // Read all 4 inputs RAW and validate: a failed register read returns 0xFF, which must NOT
        // be treated as "released" (that turns a held button into a phantom rising edge on the next
        // clean poll -> phantom toggle / phantom FIRE). A valid status is 0 or 1; anything else =
        // bad read -> skip + freeze latches (anti-phantom-fire, per regression review).
        const std::uint8_t rsw = byteBtn.getSwitchStatus(BB_SWITCH_IDX);
        const std::uint8_t rb1 = byteBtn.getSwitchStatus(BB_BTN1_IDX);
        const std::uint8_t rb2 = byteBtn.getSwitchStatus(BB_BTN2_IDX);
        const std::uint8_t rb3 = byteBtn.getSwitchStatus(BB_FIRE_IDX);
        if (rsw > 1 || rb1 > 1 || rb2 > 1 || rb3 > 1)
        {
            if (++_bbFailCount >= 5)
                _byteBtnPresent = false;
            return;
        }
        _bbFailCount = 0;
        const bool sw = (rsw == BB_PRESSED);
        const bool b1 = (rb1 == BB_PRESSED);
        const bool b2 = (rb2 == BB_PRESSED);
        const bool b3 = (rb3 == BB_PRESSED);

        applyLocalInputLevels(sw, b1, b2, b3, "bb");
    }

    RenderColor localColor(int led) const
    {
        const int i = (led < 0) ? 0 : (led >= LED_COUNT ? LED_COUNT - 1 : led);
        // Dial-pushed colours (Preview/Fire/PaletteSet) take precedence once received.
        // On-device Settings re-takes ownership when the operator edits a colour; the
        // fallback is the persisted effective RGB, not just the preset cursor.
        if (_dialColorsValid)
            return _dialColors[i];
        return _ledColors[i];
    }

    bool staticColorFadeActive() const
    {
        for (int i = 0; i < 3; ++i)
            if (_staticFade[i].active)
                return true;
        return false;
    }

    RenderColor currentStaticFadeColor(int i, std::uint32_t now)
    {
        StaticColorFade& f = _staticFade[i];
        if (!f.active)
            return f.current;

        const std::uint32_t elapsed = now - f.startMs;
        if (elapsed >= STATIC_COLOR_FADE_MS)
        {
            f.current = f.target;
            f.active = false;
            return f.current;
        }

        f.current = lerpColor(f.start, f.target, elapsed, STATIC_COLOR_FADE_MS);
        return f.current;
    }

    void applyStaticColorTransitions(RenderColor frame[LED_COUNT], std::uint32_t now)
    {
        for (int i = 0; i < 3; ++i)
        {
            const RenderColor target = frame[i];
            StaticColorFade& f = _staticFade[i];
            const RenderColor current = currentStaticFadeColor(i, now);

            if (!_paletteFade)
            {
                f.start = target;
                f.target = target;
                f.current = target;
                f.active = false;
                frame[i] = target;
                continue;
            }

            if (!sameColor(target, f.target))
            {
                f.start = current;
                f.target = target;
                f.current = current;
                f.startMs = now;
                f.active = !sameColor(current, target);
                frame[i] = current;
                continue;
            }

            frame[i] = current;
        }
    }

    bool staticChannelOn(int i) const
    {
        // channel 2 (#3) reflects the EFFECTIVE rendered state (live switch level OR remote),
        // matching applyLocalControl so a PaletteSet fade re-arms the channel that is actually lit.
        return (i == 0) ? _led1On : (i == 1) ? _led2On : (_switchEngaged || _led3RemoteOn);
    }

    void rearmActiveStaticFades()
    {
        for (int i = 0; i < 3; ++i)
        {
            if (!staticChannelOn(i))
                continue;
            const RenderColor target = localColor(i);
            StaticColorFade& f = _staticFade[i];
            f.start = RenderColor(0, 0, 0);
            f.current = RenderColor(0, 0, 0);
            f.target = RenderColor(static_cast<std::uint8_t>(target.r ^ 0xFF),
                                   static_cast<std::uint8_t>(target.g ^ 0xFF),
                                   static_cast<std::uint8_t>(target.b ^ 0xFF));
            f.startMs = millis();
            f.active = false;
        }
        markLocalDirty();
    }

    void serviceStaticColorFade()
    {
        if (staticColorFadeActive() && millis() - _lastStaticFadeDrawMs >= STATIC_COLOR_FRAME_MS)
            markLocalDirty();
    }

    void servicePreviewOverlay()
    {
        if (_previewUntilMs == 0 && _terminalPreviewUntilMs == 0)
            return;

        const std::uint32_t now = millis();
        bool expired = false;
        if (_previewUntilMs != 0 && static_cast<std::int32_t>(now - _previewUntilMs) >= 0)
        {
            _previewUntilMs = 0;
            expired = true;
        }
        if (_terminalPreviewUntilMs != 0 &&
            static_cast<std::int32_t>(now - _terminalPreviewUntilMs) >= 0)
        {
            _terminalPreviewUntilMs = 0;
            expired = true;
        }
        if (!expired)
        {
            return;
        }

        _forceShow = true;
        markLocalDirty();
    }

    void applyLocalControl()
    {
        RenderColor frame[LED_COUNT] = {};
        const std::uint32_t now = millis();
        // STOP/master-off is output-dominant. It must beat any later local USB
        // preview overlay as well as the normal local latch renderer.
        if (_masterOffInhibit)
        {
            showBudgetedFrame(frame);   // frame is all-zero -> strip dark
            _lastStaticFadeDrawMs = now;
            return;
        }

        if (_previewUntilMs != 0 && static_cast<std::int32_t>(now - _previewUntilMs) < 0 && _dialColorsValid)
        {
            for (int i = 0; i < LED_COUNT; ++i)
                frame[i] = _dialColors[i];
            showBudgetedFrame(frame);
            return;
        }
        if (_terminalPreviewUntilMs != 0 &&
            static_cast<std::int32_t>(now - _terminalPreviewUntilMs) < 0)
        {
            for (int i = 0; i < LED_COUNT; ++i)
            {
                const bool previewChangesState =
                    (_terminalPreviewMask & static_cast<std::uint8_t>(1U << i)) != 0U;
                const bool previewOn = terminalLaneBaseOn(i) != previewChangesState;
                if (previewOn)
                    frame[i] = localColor(i);
            }
            showBudgetedFrame(frame);
            _lastStaticFadeDrawMs = now;
            return;
        }

        if (_led1On) frame[0] = localColor(0);   // SK6812 #1 <- button 1 toggle
        if (_led2On) frame[1] = localColor(1);   // SK6812 #2 <- button 2 toggle
        // SK6812 #3: LOCAL SWITCH HAS HARD PRIORITY (D3, live physical level).
        //   switch engaged (HIGH) -> #3 = localColor(2); the switch owns it, remote is ignored.
        //   switch released (LOW)  -> #3 = remote-on ? localColor(2) : off.
        if (_switchEngaged)        frame[2] = localColor(2);   // live switch level owns #3
        else if (_led3RemoteOn)    frame[2] = localColor(2);   // switch OFF only: Dial may light #3
        frame[3] = odpalColor();                 // SK6812 #4 <- generic odpal flash (off when idle)
        if (_led5RemoteOn)         frame[4] = localColor(4);   // SK6812 #5 <- remote ON-only status LED
        applyStaticColorTransitions(frame, now);  // channels 0..2 only; LED4 odpal + LED5 status own their channels
        showBudgetedFrame(frame);
        _lastStaticFadeDrawMs = now;
    }

    bool terminalLaneBaseOn(int led) const
    {
        switch (led)
        {
            case 0: return _led1On;
            case 1: return _led2On;
            case 2: return _switchEngaged || _led3RemoteOn;
            case 3: return false;
            case 4: return _led5RemoteOn;
            default: return false;
        }
    }

    // Drives the local-control frame whenever no Dial-driven effect owns the LEDs.
    void applyLocalControlIfIdle()
    {
        if (!_localDirty)
            return;
        applyLocalControl();
        _localDirty = false;
    }

    void markLocalDirty() { _localDirty = true; }

    void scheduleLedColorsPersist()
    {
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
            return;
        _ledColorsPersistDirty = true;
        _deferredPersistDueMs = millis() + SETTINGS_SAVE_DEBOUNCE_MS;
    }

    void schedulePalettePersist()
    {
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
            return;
        _palettePersistDirty = true;
        _deferredPersistDueMs = millis() + SETTINGS_SAVE_DEBOUNCE_MS;
    }

    void serviceDeferredPersistence()
    {
        if (!_ledColorsPersistDirty && !_palettePersistDirty)
            return;

        const std::uint32_t now = millis();
        if (static_cast<std::int32_t>(now - _deferredPersistDueMs) < 0)
            return;

        if (_ledColorsPersistDirty && storeLedColors(false))
            _ledColorsPersistDirty = false;
        if (_palettePersistDirty && storePalette())
            _palettePersistDirty = false;

        if (_ledColorsPersistDirty || _palettePersistDirty)
            _deferredPersistDueMs = now + SETTINGS_SAVE_DEBOUNCE_MS;
    }

    // --- ByteButton-absent emulation: drive the 4 inputs from the onboard encoder+button ---
    const char* vInputName(int v) const
    {
        switch (v)
        {
            case 0:  return "> LED1";
            case 1:  return "> LED2";
            case 2:  return "> SPINAC";
            case 3:  return "> ODPAL";
            default: return "> LED5";
        }
    }

    void activateVInput(int input)
    {
        // A local menu/encoder activation is a local input -> release any STOP master-off inhibit
        // (configurable mode) before applying it, so this action drives the LED normally.
        _masterOffInhibit = false;
        switch (input)
        {
            case 0:  _led1On = !_led1On; setStatus(_led1On ? "LED1 ON" : "LED1 OFF"); markLocalDirty(); break;
            case 1:  _led2On = !_led2On; setStatus(_led2On ? "LED2 ON" : "LED2 OFF"); markLocalDirty(); break;
            // SPINAC drives #3 via the SAME override latch the Dial uses (_led3RemoteOn) -- but ONLY
            // while the switch is OFF: the physical switch has hard priority, and setting the latch
            // under an engaged switch would strand #3 on after release. The engage edge also clears it.
            case 2:  if (!_switchEngaged) _led3RemoteOn = !_led3RemoteOn; setStatus((_switchEngaged || _led3RemoteOn) ? "SPIN ON" : "SPIN OFF"); markLocalDirty(); break;
            case 3:  tryLocalFire(); break;   // ODPAL row: emulated FIRE -> same gated local odpal
            // LED5 is remote ON-only via the Dial (STOP is the master clear). The LOCAL panel can
            // TOGGLE it so a standalone DinMeter (no Dial) can still turn #5 on/off for test/manual use.
            default: _led5RemoteOn = !_led5RemoteOn; setStatus(_led5RemoteOn ? "LED5 ON" : "LED5 OFF"); markLocalDirty(); break;
        }
        markStatusDirty();
    }

    void tryLocalFire()
    {
        if (_lockout)
        {
            setStatus("STOP");
            markStatusDirty();
            return;
        }
        triggerOdpal();
    }

    bool terminalEffectAllowsOdpal() const
    {
        return (_terminalEffectMask & static_cast<std::uint8_t>(1U << TERMINAL_ODPAL_LANE)) != 0U;
    }

    // Generic placeholder "odpal" on SK6812 #4: a LoRa Fire triggers a single bright flash
    // of #4's colour that fades to off over ODPAL_MS. Replace later with the real behaviour.
    bool triggerOdpal()
    {
        _previewUntilMs = 0;
        _terminalPreviewUntilMs = 0;
        if (!terminalEffectAllowsOdpal())
        {
            _odpalActive = false;
            _forceShow = true;
            setStatus("ODPAL VYP");
            markStatusDirty();
            markLocalDirty();
            return false;
        }
        if (!xiaoOutputReady(millis()))
        {
            markXiaoOutputMissing();
            return false;
        }
        _odpalStartMs = millis();
        _odpalActive  = true;
        _forceShow    = true;   // guarantee the strip write at the start of the flash
        setStatus("ODPAL");
        markStatusDirty();
        markLocalDirty();
        return true;
    }

    std::uint32_t odpalTotalMs() const
    {
        return static_cast<std::uint32_t>(_odpal.rampMs) + _odpal.holdMs + _odpal.fadeMs;
    }

    // Curve shape for a RISING progress p (0..1); the fade phase inverts it. No side effects.
    static float curveShape(float p, std::uint8_t curve)
    {
        if (p <= 0.0f) return 0.0f;
        if (p >= 1.0f) return 1.0f;
        if (curve == 0) return 1.0f;                       // HRANA: instant full (square pulse)
        if (curve == 2) return std::sin(p * 1.57079633f);  // SINUS: smooth ease 0 -> 1
        return p;                                          // LIN: linear
    }

    // PURE brightness compute (the end-of-odpal lifecycle now lives in update(), not here, so
    // this getter can be called every frame without double-firing the end transition).
    RenderColor odpalColor()
    {
        if (!_odpalActive)
            return RenderColor(0, 0, 0);
        const std::uint32_t elapsed = millis() - _odpalStartMs;
        float amt;
        if (elapsed >= odpalTotalMs())
            amt = 0.0f;
        else if (elapsed < _odpal.rampMs)
            amt = curveShape(_odpal.rampMs ? static_cast<float>(elapsed) / _odpal.rampMs : 1.0f, _odpal.curve);
        else if (elapsed < static_cast<std::uint32_t>(_odpal.rampMs) + _odpal.holdMs)
            amt = 1.0f;
        else
        {
            const std::uint32_t into = elapsed - _odpal.rampMs - _odpal.holdMs;
            amt = 1.0f - curveShape(_odpal.fadeMs ? static_cast<float>(into) / _odpal.fadeMs : 1.0f, _odpal.curve);
        }
        if (amt < 0.0f) amt = 0.0f;
        if (amt > 1.0f) amt = 1.0f;
        const RenderColor base = localColor(3);
        return RenderColor(static_cast<std::uint8_t>(base.r * amt),
                           static_cast<std::uint8_t>(base.g * amt),
                           static_cast<std::uint8_t>(base.b * amt));
    }

    // Fast boot probe: check ONLY the two target addresses (ByteButton 0x47 + NeoDriver 0x60)
    // and set the present flags from their ACKs. Used for the orientation decision so an empty/
    // stalled bus costs at most 2 (not 126) bounded I2C transactions per orientation. Returns the
    // number of TARGET devices that ACKed (0 -> caller retries with swapped SDA/SCL).
    int probeTargets()
    {
        _byteBtnPresent = false;
        _neoDriverPresent = false;
        int hits = 0;
        const std::uint8_t targets[2] = {BYTEBUTTON_ADDR, NEODRIVER_ADDR};
        for (std::uint8_t addr : targets)
        {
            Wire1.beginTransmission(addr);
            if (Wire1.endTransmission() == 0)
            {
                _foundAddr = addr;
                if (addr == BYTEBUTTON_ADDR) _byteBtnPresent = true;
                if (addr == NEODRIVER_ADDR)  _neoDriverPresent = true;
                ++hits;
            }
        }
        Serial.printf("[i2c] target probe: ByteButton(0x47)=%d NeoDriver(0x60)=%d\n",
                      _byteBtnPresent, _neoDriverPresent);
        return hits;
    }

    // Boot diagnostic: list every responder on the Port B (Wire1) bus.
    int scanI2cBus()
    {
        Serial.println("[i2c] scanning Port B (Wire1)...");
        int found = 0;
        _byteBtnPresent = false;
        _neoDriverPresent = false;
        for (std::uint8_t addr = 1; addr < 127; ++addr)
        {
            Wire1.beginTransmission(addr);
            if (Wire1.endTransmission() == 0)
            {
                Serial.printf("[i2c]  device @ 0x%02X\n", addr);
                _foundAddr = addr;
                if (addr == BYTEBUTTON_ADDR) _byteBtnPresent = true;
                if (addr == NEODRIVER_ADDR)  _neoDriverPresent = true;
                ++found;
            }
        }
        Serial.printf("[i2c] %d device(s); ByteButton(0x47)=%d NeoDriver(0x60)=%d\n",
                      found, _byteBtnPresent, _neoDriverPresent);
        return found;
    }

    void handleEncoder(int delta, std::uint32_t now)
    {
        (void)now;
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
        {
            return;
        }
        if (delta == 0)
            return;

        if (_page == UiPage::Cas && _editing)
        {
            adjustOdpalField(LED_COUNT + _row, delta);   // ADJUST mode: encoder changes the selected ms value
            _dirtyAll = true;
            return;
        }
        if (_page == UiPage::Jas && _editing && _row < LED_COUNT)
        {
            const int v = static_cast<int>(_ledBrightness[_row]) + delta * 13;   // ~5% step (255/~20)
            _ledBrightness[_row] = static_cast<std::uint8_t>(v < 15 ? 15 : (v > 255 ? 255 : v));   // floor 15 -> never fully dark
            markLocalDirty();
            _forceShow = true;
            _dirtyAll = true;
            return;
        }

        _row = wrapIndex(_row + delta, rowsForPage());
        if (_page == UiPage::Stav && _row < FN_ROWS)
            setStatus(vInputName(_row));
        _dirtyAll = true;
    }

    int wrapIndex(int value, int count) const
    {
        while (value < 0)
            value += count;
        while (value >= count)
            value -= count;
        return value;
    }

    // Function-row count is per-page: Stav/Barvy/Jas track FN_ROWS (= LED_COUNT, now 5 incl. LED#5),
    // but Cas is pinned to CAS_FN_ROWS (the 4 odpal envelope fields: NABEH/SVIT/ZHASNUTI/KRIVKA) --
    // it is NOT LED_COUNT-driven, so growing LED_COUNT must NOT add a 5th (garbage) odpal row.
    static constexpr int CAS_FN_ROWS = 4;
    int fnRowsForPage() const { return (_page == UiPage::Cas) ? CAS_FN_ROWS : FN_ROWS; }
    int rowsForPage() const { return fnRowsForPage() + 1; }   // function rows + the navigation arrow
    bool onArrowRow() const { return _row == rowsForPage() - 1; }

    static std::uint16_t clampOdpalMs(int v)
    {
        if (v < 0) v = 0;
        if (v > ODPAL_MAX_MS) v = ODPAL_MAX_MS;
        return static_cast<std::uint16_t>(v);
    }

    // Settings odpal rows: row LED_COUNT+0=ramp, +1=hold, +2=fade (ms, step ODPAL_STEP_MS).
    // Curve is click-cycled on its row; encoder ADJUST mode only applies to the three time rows.
    void adjustOdpalField(int row, int delta)
    {
        const int f = row - LED_COUNT;
        if (f == 0)      _odpal.rampMs = clampOdpalMs(static_cast<int>(_odpal.rampMs) + delta * ODPAL_STEP_MS);
        else if (f == 1) _odpal.holdMs = clampOdpalMs(static_cast<int>(_odpal.holdMs) + delta * ODPAL_STEP_MS);
        else if (f == 2) _odpal.fadeMs = clampOdpalMs(static_cast<int>(_odpal.fadeMs) + delta * ODPAL_STEP_MS);
    }

    void handleShortPress()
    {
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
        {
            return;
        }

        if (onArrowRow())
        {
            advancePage();
            return;
        }

        switch (_page)
        {
            case UiPage::Stav:
                // The ByteButton is the PRIMARY input, but the encoder is NEVER locked out: the
                // display can always override (e.g. switch a LED off) even with the module present.
                // Both sources edge-toggle the SAME latches, so they cooperate without blocking.
                activateVInput(_row);
                break;
            case UiPage::Barvy:
                _ledColorIdx[_row] = (_ledColorIdx[_row] + 1) % NUM_COLOR_PRESETS;
                _ledColors[_row] = presetRenderColor(_ledColorIdx[_row]);
                _dialColorsValid = false;   // on-device colour edit re-takes ownership from the Dial
                _localColorEditPending = true;   // on save, drop pal1 so this edit wins on next boot
                markLocalDirty();
                break;
            case UiPage::Cas:
                if (_row == 3)
                    _odpal.curve = static_cast<std::uint8_t>(wrapIndex(static_cast<int>(_odpal.curve) + 1, NUM_ODPAL_CURVES));
                else
                    _editing = !_editing;   // time rows: toggle ADJUST mode (encoder then changes the ms)
                break;
            case UiPage::Jas:
                _editing = !_editing;   // toggle ADJUST mode (encoder then changes the brightness)
                break;
        }
        _dirtyAll = true;
    }

    void handleLongPress()
    {
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
        {
            return;
        }

        if (_page == UiPage::Barvy)
        {
            storeLedColors();
            sendLedColorSet();   // bidirectional sync: push the new colours to the Dial
        }
        if (_page == UiPage::Cas)
            storeOdpalCfg();
        if (_page == UiPage::Jas)
            storeLedBrightness();

        // Long-press is now a fast home/save action; page navigation lives on the arrow row.
        _editing = false;
        _page = UiPage::Stav;
        _row = 0;
        _dirtyAll = true;
        render(true);
    }

    void advancePage()
    {
        if (!DINMETER_LOCAL_SETUP_EDITOR_ENABLED)
        {
            _editing = false;
            _page = UiPage::Stav;
            _row = 0;
            _dirtyAll = true;
            return;
        }

        if (_page == UiPage::Barvy)
        {
            storeLedColors();
            sendLedColorSet();   // bidirectional sync: push the new colours to the Dial
        }
        if (_page == UiPage::Cas)
            storeOdpalCfg();
        if (_page == UiPage::Jas)
            storeLedBrightness();

        _editing = false;
        _page = (_page == UiPage::Stav)  ? UiPage::Barvy :
                (_page == UiPage::Barvy) ? UiPage::Cas :
                (_page == UiPage::Cas)   ? UiPage::Jas : UiPage::Stav;
        _row = 0;
        _dirtyAll = true;
        render(true);
    }

    void readModem()
    {
        while (propSerial.available() > 0)
        {
            const char c = static_cast<char>(propSerial.read());
            if (c == '\r')
                continue;

            if (c == '\n')
            {
                if (!_lineOverflow && _line.length() > 0)
                    handleLine(_line);
                _line = "";
                _lineOverflow = false;   // a newline ends any over-long-line discard
                continue;
            }

            if (_lineOverflow)
                continue;                // drop the rest of an over-long line until the newline

            if (_line.length() < prop_protocol::MAX_HOST_RX_LINE_LENGTH)
                _line += c;
            else
            {
                // Over-long line: discard it ENTIRELY rather than truncating (truncation let
                // the bytes after the 160th be parsed as a spurious new line). Drop to newline.
                _line = "";
                _lineOverflow = true;
            }
        }
    }

    void handleLine(String line)
    {
        line.trim();
        if (line.length() == 0)
            return;

        _lastLine = line;
        String upper = line;
        upper.toUpperCase();

        if (upper.startsWith("RX "))
        {
            handleRxFrame(line);
            return;
        }

        // Any non-"RX " line is an informational modem status/diagnostic message
        // (OK TX, OK RADIO_READY, BOOT C6L_MODEM, ERR ...). It carries no frame and
        // needs NO reply. We must stay silent here: replying with a non-"RX " line
        // makes the modem answer "ERR BAD_FRAME" (also non-"RX "), which loops back
        // here forever -> a UART ping-pong storm that saturates the link and starves
        // real RX/ACK traffic. _lastLine (set above) keeps it available for the HUD.
#if DEBUG_HUD
        if (upper.startsWith("OK HEALTH"))
            recordDebugHealth(line);
#endif
        if (upper.startsWith("OK") || upper.startsWith("BOOT"))
        {
            _modemLastSeenMs = millis();   // modem liveness heartbeat
            _modemEverSeen = true;         // standalone: before first contact, "no Dial" is normal, not SPOJ?
        }
    }

    void readUsbSetup()
    {
        while (Serial.available() > 0)
        {
            const char c = static_cast<char>(Serial.read());
            if (c == '\r')
                continue;

            if (c == '\n')
            {
                if (!_usbSetupOverflow && _usbSetupLine.length() > 0)
                    handleUsbSetupLine(_usbSetupLine);
                _usbSetupLine = "";
                _usbSetupOverflow = false;
                continue;
            }

            if (_usbSetupOverflow)
                continue;

            if (_usbSetupLine.length() < prop_protocol::MAX_HOST_RX_LINE_LENGTH)
                _usbSetupLine += c;
            else
            {
                _usbSetupLine = "";
                _usbSetupOverflow = true;
                Serial.println(terminal_setup_link::formatUnscopedResponseLine(terminal_setup_link::RESPONSE_ERR).c_str());
            }
        }
    }

    static bool commitTerminalSetupCallback(void* ctx, const terminal_setup_apply::AppliedSetup& setup)
    {
        return static_cast<PropRxApp*>(ctx)->commitTerminalSetup(setup);
    }

    static bool previewTerminalSimFireCallback(void* ctx)
    {
        return static_cast<PropRxApp*>(ctx)->previewTerminalSimFire();
    }

    void handleUsbSetupLine(String line)
    {
        line.trim();
        terminal_setup_receiver::ReceiverCallbacks callbacks{
            this,
            commitTerminalSetupCallback,
            previewTerminalSimFireCallback,
        };
        const terminal_setup_receiver::ReplyResult reply =
            terminal_setup_receiver::handleLineResult(line.c_str(), callbacks);
        const std::string replyLine = terminal_setup_receiver::replyLine(reply);
        if (!replyLine.empty())
            Serial.println(replyLine.c_str());
    }

    bool terminalSetupSafeToCommit() const
    {
        return !_lockout && !_masterOffInhibit && !_armed && !_odpalActive;
    }

    bool commitTerminalSetup(const terminal_setup_apply::AppliedSetup& setup)
    {
        if (!terminalSetupSafeToCommit())
        {
            setStatus("SETUP BUSY");
            markStatusDirty();
            return false;
        }

        RenderColor oldColors[LED_COUNT] = {};
        std::uint8_t oldBrightness[LED_COUNT] = {};
        for (int i = 0; i < LED_COUNT; ++i)
        {
            oldColors[i] = _ledColors[i];
            oldBrightness[i] = _ledBrightness[i];
        }
        const bool oldLed1On = _led1On;
        const bool oldLed2On = _led2On;
        const bool oldLed3RemoteOn = _led3RemoteOn;
        const bool oldLed5RemoteOn = _led5RemoteOn;
        const bool oldDialColorsValid = _dialColorsValid;
        const std::uint8_t oldTerminalEffectMask = _terminalEffectMask;
        const std::uint8_t oldTerminalPreviewMask = _terminalPreviewMask;

        for (int i = 0; i < LED_COUNT; ++i)
        {
            const terminal_setup_apply::AppliedLane& lane = setup.lanes[i];
            _ledColors[i] = RenderColor(lane.color.r, lane.color.g, lane.color.b);
            _ledBrightness[i] = lane.brightness;
        }
        _led1On = setup.lanes[0].on;
        _led2On = setup.lanes[1].on;
        _led3RemoteOn = setup.lanes[2].on;
        _led5RemoteOn = setup.lanes[4].on;
        _terminalEffectMask = setup.effectMask;
        _terminalPreviewMask = setup.effectPreviewMask;
        _dialColorsValid = false;
        _localColorEditPending = false;

        const bool savedSetup = storeTerminalSetup(setup);
        if (!savedSetup)
        {
            for (int i = 0; i < LED_COUNT; ++i)
            {
                _ledColors[i] = oldColors[i];
                _ledBrightness[i] = oldBrightness[i];
            }
            _led1On = oldLed1On;
            _led2On = oldLed2On;
            _led3RemoteOn = oldLed3RemoteOn;
            _led5RemoteOn = oldLed5RemoteOn;
            _dialColorsValid = oldDialColorsValid;
            _terminalEffectMask = oldTerminalEffectMask;
            _terminalPreviewMask = oldTerminalPreviewMask;
            setStatus("SETUP ERR");
            markStatusDirty();
            markLocalDirty();
            return false;
        }

        _savedUntilMs = millis() + SAVED_BADGE_MS;
        setStatus("NAHRANO");
        markStatusDirty();
        markLocalDirty();
        _forceShow = true;
        return true;
    }

    bool previewTerminalSimFire()
    {
        if (_lockout || _masterOffInhibit || _armed || _odpalActive)
        {
            _terminalPreviewUntilMs = 0;
            _forceShow = true;
            markLocalDirty();
            setStatus("STOP");
            markStatusDirty();
            return false;
        }
        _terminalPreviewUntilMs = millis() + PREVIEW_OVERLAY_MS;
        _forceShow = true;
        markLocalDirty();
        setStatus("SIM FIRE");
        markStatusDirty();
        return true;
    }

#if DEBUG_HUD
    void recordDebugRxBand(const String& line)
    {
        const int first = line.indexOf(' ');
        const int second = first < 0 ? -1 : line.indexOf(' ', first + 1);
        const int third = second < 0 ? -1 : line.indexOf(' ', second + 1);
        if (third < 0)
            return;

        String rssi = line.substring(first + 1, second);
        String snr = line.substring(second + 1, third);
        rssi.trim();
        snr.trim();

        if (rssi == "0.0" && snr == "0.0")
            ++_debug.rxEspnow;
        else
            ++_debug.rxLora;
    }

    std::uint32_t parseDebugHealthValue(const String& line, const char* key) const
    {
        const int pos = line.indexOf(key);
        if (pos < 0)
            return 0;
        return static_cast<std::uint32_t>(line.substring(pos + static_cast<int>(strlen(key))).toInt());
    }

    void recordDebugHealth(const String& line)
    {
        _debug.healthForeign = parseDebugHealthValue(line, "foreign=");
        _debug.healthQdrop = parseDebugHealthValue(line, "qdrop=");
        _debug.healthRxfree = parseDebugHealthValue(line, "rxfree=");
    }
#endif

    bool validateFrameRoute(const prop_protocol::Frame& frame)
    {
        if (frame.keyId != PROP_KEY_ID)
        {
            setStatus("BAD KEY");
            return false;
        }
        if (frame.source != PROP_DESTINATION)
        {
            setStatus("BAD SRC");
            return false;
        }
        if (frame.destination != PROP_SOURCE)
        {
            setStatus("BAD DST");
            return false;
        }
        return true;
    }

    bool loadRuntimeKeyFromPreferences()
    {
        Preferences keyPrefs;
        if (!keyPrefs.begin(prop_runtime_key::NVS_NAMESPACE, true))
        {
            _runtimeKey.clear();
            return false;
        }

        const std::size_t size = keyPrefs.getBytesLength(prop_runtime_key::NVS_KEY);
        std::array<std::uint8_t, prop_runtime_key::MAX_KEY_LENGTH> buffer = {};
        bool ok = false;
        if (size >= prop_runtime_key::MIN_KEY_LENGTH && size <= buffer.size() &&
            keyPrefs.getBytes(prop_runtime_key::NVS_KEY, buffer.data(), size) == size)
        {
            ok = _runtimeKey.set(buffer.data(), size);
        }
        keyPrefs.end();
        prop_runtime_key::secureZero(buffer);
        if (!ok)
        {
            _runtimeKey.clear();
        }
        return ok;
    }

    bool loadRuntimeKey()
    {
        if (loadRuntimeKeyFromPreferences())
        {
            return true;
        }
        _runtimeKey.clear();
        setStatus("KEY MISSING");
        return false;
    }

    const prop_runtime_key::RuntimeKey* runtimeKeyOrStatus()
    {
        if (_runtimeKey.loaded())
        {
            return &_runtimeKey;
        }
        setStatus("KEY MISSING");
        return nullptr;
    }

    ReplayDecision classifyReplay(std::uint32_t sequence)
    {
        if ((_rxWindowBase == 0 && sequence > 0) || sequence > _rxWindowBase)
        {
            const std::uint32_t shift = sequence - _rxWindowBase;
            if (shift > RX_REPLAY_WINDOW_BITS)
                _rxWindowMask = 0;
            else
            {
                const std::uint32_t acceptedBaseBit = static_cast<std::uint32_t>(1) << (shift - 1);
                if (shift == RX_REPLAY_WINDOW_BITS)
                    _rxWindowMask = acceptedBaseBit;
                else
                    _rxWindowMask = (_rxWindowMask << shift) | acceptedBaseBit;
            }
            _rxWindowBase = sequence;
            return ReplayDecision::EXECUTE;
        }

        if (sequence == _rxWindowBase)
            return ReplayDecision::DROP_DUP;

        const std::uint32_t diff = _rxWindowBase - sequence;
        if (diff > RX_REPLAY_WINDOW_BITS)
            return ReplayDecision::DROP_STALE;

        const std::uint32_t seenBit = static_cast<std::uint32_t>(1) << (diff - 1);
        if ((_rxWindowMask & seenBit) != 0)
            return ReplayDecision::DROP_DUP;

        _rxWindowMask |= seenBit;
        return ReplayDecision::EXECUTE;
    }

    static bool persistsLastSeq(prop_protocol::FrameType type)
    {
        return type == prop_protocol::FrameType::Fire || type == prop_protocol::FrameType::Stop;
    }

    // STOP order-dominance for OUTPUT-affecting non-Fire frames (Preview/LedColorSet/
    // RemoteLed/PaletteSet). STOP records _lockoutSeq; ARM/FIRE already reject same-session
    // frames with sequence <= _lockoutSeq, but the output handlers below did NOT -- so a
    // delayed/replayed pre-STOP frame still inside the 32-frame replay window could re-light
    // LED3/LED5 (or push a colour) AFTER an e-stop, because the modem's STOP priority can
    // reorder STOP ahead of older queued frames. This drops those stale frames before they
    // touch the strip. A genuine post-STOP frame (sequence > _lockoutSeq) is unaffected.
    // NOTE: acceptedNewSession is intentionally NOT consulted here (unlike the old ARM bypass):
    // the TX epoch is RANDOM per boot, not monotonic, so "new epoch" is not proof the frame
    // post-dates the STOP -- a replayed old-epoch frame would otherwise slip through.
    bool droppedByStopOrder(const prop_protocol::Frame& frame)
    {
        return _lockout && frame.sequence <= _lockoutSeq;
    }

    void rememberStopFence(const prop_protocol::Frame& frame)
    {
        if (!_lockout || frame.sequence > _lockoutSeq)
        {
            _lockoutSeq = frame.sequence;
        }
    }

    // Canonical ACK payload to RE-SEND when a duplicate of an idempotent / ack-tracked frame
    // arrives (the Dial retrying because our first ACK was lost). Returns nullptr for frame
    // types that must stay silent-drop on duplicate -- only FIRE (its 3x burst copies must not
    // trigger a return transmission mid-burst; the deferred FIRE ack is its sole confirmation).
    // Payload strings MUST match what the live handler sent so the Dial's (sequence,nonce)+
    // payload match re-fires. For ARM the answer depends on the current STOP fence, recomputed
    // here exactly as the live ARM gate does.
    const char* duplicateReAckPayload(const prop_protocol::Frame& frame)
    {
        switch (frame.type)
        {
            case prop_protocol::FrameType::Stop:        return "STOP";
            case prop_protocol::FrameType::Ping:
            case prop_protocol::FrameType::Status:      return "PONG";
            case prop_protocol::FrameType::Preview:     return "PREVIEW";
            case prop_protocol::FrameType::PaletteSet:  return "PALETTE";
            case prop_protocol::FrameType::LedColorSet: return "COLORSET";
            case prop_protocol::FrameType::RemoteLed:   return "REMOTE";
            case prop_protocol::FrameType::Arm:
            {
                // Replay-fence still applies: a dup ARM that does not post-date the STOP -> LOCKOUT.
                if (_lockout && frame.sequence <= _lockoutSeq)
                    return "LOCKOUT";
                // Re-ACK "ARMED" ONLY if THIS exact ARM is the one still authorising (same epoch+
                // seq, not TTL-lapsed). Otherwise stay silent so we never tell the Dial "armed"
                // while the receiver has already dropped to SAFE (would desync the two). The
                // Dial's ARM heartbeat (new sequence each time) is the real keep-alive path.
                const std::uint32_t armEpoch = static_cast<std::uint32_t>(frame.nonce >> 32);
                if (_armed && armEpoch == _armEpoch && frame.sequence == _armSeq &&
                    static_cast<std::int32_t>(millis() - _armExpiryMs) < 0)
                    return "ARMED";
                return nullptr;
            }
            case prop_protocol::FrameType::Fire:
            default:
                return nullptr;   // FIRE burst copies (and unknown types) stay silent-drop
        }
    }

    void rememberAcceptedSequence(prop_protocol::FrameType type)
    {
        _lastAcceptedSequence = _rxWindowBase;
        if (persistsLastSeq(type))
        {
            if (_lastAcceptedSequence != _lastPersistedSequence)
                preferences.putUInt("lastSeq", _lastAcceptedSequence);
            preferences.putUInt("epoch", _lastEpoch);
            _lastPersistedSequence = _lastAcceptedSequence;
        }
    }

    void handleRxFrame(const String& line)
    {
#if DEBUG_HUD
        ++_debug.rxTotal;
        recordDebugRxBand(line);
#endif
        std::vector<std::uint8_t> encoded;
        if (!extractFrameHex(line, encoded))
        {
#if DEBUG_HUD
            ++_debug.rxBad;
#endif
            setStatus("BAD RX");
            return;
        }

        prop_protocol::Frame frame;
        const prop_runtime_key::RuntimeKey* key = runtimeKeyOrStatus();
        if (key == nullptr)
        {
#if DEBUG_HUD
            ++_debug.rxBad;
#endif
            return;
        }
        if (!prop_protocol::decodeFrame(encoded.data(), encoded.size(), key->data(), key->size(), frame))
        {
#if DEBUG_HUD
            ++_debug.rxBad;
#endif
            setStatus("BAD MAC");
            return;
        }

        if (!validateFrameRoute(frame))
        {
#if DEBUG_HUD
            ++_debug.rxBad;
#endif
            return;
        }

        bool acceptedNewSession = false;
        // Option A: 32-bit RANDOM per-boot epoch (top 32 bits of nonce). ANY different
        // epoch = a fresh Dial session -> reset the dedup window. No monotonic ordering
        // / rollback-reject, so an erased or reflashed Dial can NEVER be permanently
        // rejected (no brick). Fixes the old 8-bit (1/256) epoch collision that dropped
        // the first FIRE(s) after a Dial reboot.
        //
        // SAFETY (replay hardening): the epoch is random, but the Dial's SEQUENCE is
        // NVS-persisted and monotonic across Dial reboots (nvs "seq"). So even on an epoch
        // change we must NOT lower the STOP fence (_lockoutSeq): a genuine new/continuing
        // Dial session always advances the sequence ABOVE the last STOP, whereas a replayed
        // OLD-epoch capture carries a LOWER sequence. Previously this branch reset _lockoutSeq
        // down to the (old, low) replayed sequence and the ARM handler bypassed the STOP-order
        // check for acceptedNewSession -- together that let a captured old ARM+FIRE clear a
        // live STOP lockout and fire. We now keep _lockoutSeq intact across epoch changes and
        // (below) require any lockout-clearing ARM to post-date the STOP regardless of epoch.
        const std::uint32_t epoch = static_cast<std::uint32_t>(frame.nonce >> 32);
        if (epoch != _lastEpoch)
        {
            _rxWindowBase = frame.sequence;
            _rxWindowMask = 0;
            _lastAcceptedSequence = frame.sequence;
            _lastEpoch = epoch;
            _armed = false;
            _armExpiryMs = 0;
            _armEpoch = 0;
            _armSeq = 0;
            // Deliberately do NOT touch _lockoutSeq here (see SAFETY note above): the STOP
            // fence stays at the STOP's sequence so a lower-sequence replay cannot pass.
            acceptedNewSession = true;
        }

        if (!acceptedNewSession)
        {
            const ReplayDecision replayDecision = classifyReplay(frame.sequence);
            if (replayDecision == ReplayDecision::DROP_STALE)
            {
#if DEBUG_HUD
                ++_debug.rxStale;
#endif
                setStatus("STALE");
                return;
            }

            if (replayDecision == ReplayDecision::DROP_DUP)
            {
#if DEBUG_HUD
                ++_debug.rxDup;
#endif
                // A duplicate (same sequence,nonce) we already executed. Two cases:
                //  - FIRE burst copy: drop SILENTLY (do NOT ack). The sender bursts FIRE 3x and
                //    both radios are half-duplex; ack-ing each copy makes our modem transmit
                //    during the burst -> mutual deafness drops the remaining copies and floods
                //    the return channel. The single deferred EXECUTE ack is the only successful
                //    FIRE confirm; disabled/no-output odpal returns NO_EFFECT/NO_XIAO immediately.
                //  - ack-tracked / idempotent type (Stop/Ping/Status/Preview/PaletteSet/Arm):
                //    the duplicate is the Dial RE-SENDING because our original ACK was lost. It
                //    matches the ACK by (sequence,nonce)+payload, so we MUST re-emit that ACK or
                //    the Dial's retry loop ends in a false "NO ACK"/disarm. Re-ACK idempotently.
                const char* reAck = duplicateReAckPayload(frame);
                if (reAck != nullptr)
                {
                    setStatus("DUP ACK");
                    sendAckFrame(frame, reAck);
                }
                return;
            }

            rememberAcceptedSequence(frame.type);
        }
        else
            rememberAcceptedSequence(frame.type);

        if (frame.type == prop_protocol::FrameType::Preview)
        {
            // ACK-without-applying with the type's normal payload ("PREVIEW") so the Dial's
            // ack-tracked retry stops, but the overlay is NOT shown (STOP order-dominance).
            if (droppedByStopOrder(frame))
            {
                setStatus("STOP");
                sendAckFrame(frame, "PREVIEW");
                return;
            }
            if (!applyLedPayload(frame.payload))
            {
#if DEBUG_HUD
                ++_debug.rxBad;
#endif
                _terminalPreviewUntilMs = 0;
                markLocalDirty();
                setStatus("SPATNA DATA");
                sendAckFrame(frame, "BAD_PAYLOAD");
                return;
            }
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            // Preview NEVER arms: it shows the received colours as an ephemeral full-strip
            // overlay, then falls back to the local latches / odpal renderer.
            _previewUntilMs = millis() + PREVIEW_OVERLAY_MS;
            _forceShow = true;
            markLocalDirty();
            setStatus("BARVY OK");
            markStatusDirty();
            sendAckFrame(frame, "PREVIEW");
            return;
        }

        if (frame.type == prop_protocol::FrameType::LedColorSet)
        {
            // Bidirectional colour sync from the Dial: apply the 4 RGB colours (same LED payload
            // as Preview) with precedence via _dialColorsValid; pure colour state, no arm/effect.
            if (droppedByStopOrder(frame))
            {
                setStatus("STOP");
                sendAckFrame(frame, "COLORSET");
                return;
            }
            if (!applyLedPayload(frame.payload))
            {
                setStatus("SPATNA DATA");
                sendAckFrame(frame, "BAD_PAYLOAD");
                return;
            }
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            setStatus("BARVY SYNC");
            markStatusDirty();
            sendAckFrame(frame, "COLORSET");
            return;
        }

        if (frame.type == prop_protocol::FrameType::RemoteLed)
        {
            // ON-only remote latch for LED#3 + LED#5. A set bit turns the LED ON; this handler
            // NEVER clears a latch -- OFF travels only as STOP (the master clear). Deliberately
            // NOT gated by _armed / _lockout: these are status LEDs, not pyro, so STOP must not
            // wedge them off until a re-ARM. Colour comes from the synced palette slots on-device.
            // BUT a delayed/replayed pre-STOP RemoteLed (seq <= the STOP's seq, accepted only as
            // in-window backfill) must NOT resurrect LED3/LED5 that STOP just cleared. A real
            // post-STOP RemoteLed (seq > _lockoutSeq) still turns the status LEDs on normally.
            if (droppedByStopOrder(frame))
            {
                setStatus("STOP");
                sendAckFrame(frame, "REMOTE");   // ack so the Dial's FF path doesn't retry
                return;
            }
            std::uint8_t mask = 0;
            if (!prop_protocol::parseRemoteLedPayload(frame.payload, mask))
            {
                setStatus("SPATNA DATA");
                sendAckFrame(frame, "BAD_PAYLOAD");
                return;
            }
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            if (mask & prop_protocol::REMOTE_LED_BIT_LED5) _led5RemoteOn = true;   // always honoured
            if (mask & prop_protocol::REMOTE_LED_BIT_LED3)
            {
                if (!_switchEngaged) _led3RemoteOn = true;   // STRICT: honoured only while the switch is OFF
                // else: switch owns #3 -> remote ON is honoured-as-noop (still ACK so the Dial won't retry)
            }
            markLocalDirty();
            setStatus("DALKOVE LED");
            markStatusDirty();
            sendAckFrame(frame, "REMOTE");
            return;
        }

        if (frame.type == prop_protocol::FrameType::Arm)
        {
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            // STOP is order-dominant: an ARM whose sequence does NOT post-date the active STOP
            // (sequence <= the STOP's sequence) must NOT re-arm or clear the lockout -- otherwise
            // a reordered/replayed stale ARM+FIRE burst could fire AFTER an e-stop. Only an ARM
            // that post-dates the STOP (a deliberate re-arm, or a continuing Dial session whose
            // NVS-persisted sequence is necessarily higher) clears the latch.
            // The old `&& !acceptedNewSession` exemption was REMOVED: because the TX epoch is
            // random (not monotonic), "new epoch" was NOT proof of freshness, so a replayed
            // old-epoch ARM was wrongly treated as a new session and cleared the lockout. The
            // sequence comparison alone is the correct, replay-safe gate.
            if (_lockout && frame.sequence <= _lockoutSeq)
            {
                setStatus("STOP");
                sendAckFrame(frame, "LOCKOUT");
                return;
            }
            // Sprint A (0.1): explicit receiver-side ARM authority with TTL backstop.
            _armed = true;
            _armExpiryMs = millis() + ARM_TTL_MS;
            _armEpoch = epoch;
            _armSeq = frame.sequence;
            _lockout = false;            // a deliberate (post-STOP) ARM clears the latch
            _masterOffInhibit = false;   // re-arm un-stops the system -> release the local master-off inhibit
            setStatus("NABITO");
            applyIdleOutput();           // show pre-trigger glow if configured
            markStatusDirty();
            sendAckFrame(frame, "ARMED");
            return;
        }

        if (frame.type == prop_protocol::FrameType::Fire)
        {
            // Sprint A (0.1): FIRE is rejected unless the receiver is locally ARMED
            // (fresh, not locked out). This is THE safety gate: a stray/replayed/
            // glitched Fire, or a Preview, can no longer trigger an output.
            // Also reject any FIRE whose sequence is <= the last STOP's sequence: such a
            // frame predates the e-stop (only accepted as in-window backfill) and must not
            // fire even after a legitimate later re-arm.
            if (!_armed || _lockout || epoch != _armEpoch || frame.sequence <= _armSeq ||
                frame.sequence <= _lockoutSeq ||
                static_cast<std::int32_t>(millis() - _armExpiryMs) >= 0)
            {
#if DEBUG_HUD
                ++_debug.rxBad;
#endif
                setStatus("NEARM");
                sendAckFrame(frame, "NOT_ARMED");
                return;
            }
            // Accepted Fire -> consume ARM IMMEDIATELY (one-shot, fail-closed) BEFORE parsing the
            // payload, so even a BAD_PAYLOAD Fire cannot leave the receiver hot until TTL.
            _armed = false;
            _armExpiryMs = 0;
            _armEpoch = 0;
            _armSeq = 0;
            if (!applyLedPayload(frame.payload))
            {
#if DEBUG_HUD
                ++_debug.rxBad;
#endif
                _terminalPreviewUntilMs = 0;
                markLocalDirty();
                setStatus("SPATNA DATA");
                sendAckFrame(frame, "BAD_PAYLOAD");
                return;
            }
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            if (!triggerOdpal())   // Terminal setup mask disabled the odpal lane.
            {
                sendAckFrame(frame, xiaoOutputReady(millis()) ? "NO_EFFECT" : "NO_XIAO");
                return;
            }
            scheduleFireAck(frame);   // deferred best-effort ack (avoids burst collision)
            return;
        }

        if (frame.type == prop_protocol::FrameType::Stop)
        {
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            // Sprint A (0.2): STOP latches a lockout: outputs off, disarmed, and
            // a delayed/stray Fire afterwards cannot re-fire until a fresh Arm.
            _armed = false;
            _armExpiryMs = 0;
            _armEpoch = 0;
            _armSeq = 0;
            rememberStopFence(frame);
            _lockout = true;
            _hasPendingAck = false;         // cancel any deferred FIRE ack so a STOP is not
                                            // followed ~100 ms later by a stale "FIRE" confirm
            stopOutput(false);
            setStatus("STOP");
            sendAckFrame(frame, "STOP");
            return;
        }

        if (frame.type == prop_protocol::FrameType::Ping || frame.type == prop_protocol::FrameType::Status)
        {
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            setStatus("PING");
            sendAckFrame(frame, "PONG");
            return;
        }

        if (frame.type == prop_protocol::FrameType::PaletteSet)
        {
            // ACK-without-applying a pre-STOP PaletteSet (ack-tracked on the Dial): do not let a
            // stale/replayed palette re-drive the static channels (and via fade re-arm) after STOP.
            if (droppedByStopOrder(frame))
            {
                setStatus("STOP");
                sendAckFrame(frame, "PALETTE");
                return;
            }
            prop_protocol::PalettePayload pal;
            if (!prop_protocol::parsePalettePayload(frame.payload, pal) ||
                pal.colors.empty() || pal.colors.size() > prop_protocol::MAX_PALETTE_COLORS)
            {
#if DEBUG_HUD
                ++_debug.rxBad;
#endif
                setStatus("SPATNA PAL");
                sendAckFrame(frame, "BAD_PALETTE");
                return;
            }
#if DEBUG_HUD
            ++_debug.rxValid;
#endif
            const bool fadeRising = !_paletteFade && pal.fade;
            _paletteCount = static_cast<std::uint8_t>(pal.colors.size());
            for (std::uint8_t i = 0; i < _paletteCount; ++i)
                _palette[i] = RenderColor(pal.colors[i][0], pal.colors[i][1], pal.colors[i][2]);
            _paletteFade = pal.fade;
            _paletteRev  = pal.paletteRev;
            _hasPalette  = true;
            reflectPaletteColors();   // PaletteSet now drives the same colour path as Preview
            if (fadeRising)
                rearmActiveStaticFades();
            schedulePalettePersist();  // NVS write is deferred until after the ACK path
            setStatus("PALETA OK");
            sendAckFrame(frame, "PALETTE");
            return;
        }

#if DEBUG_HUD
        ++_debug.rxBad;
#endif
        setStatus("NEZNAME");
        sendAckFrame(frame, "ERR");
    }

    bool extractFrameHex(const String& line, std::vector<std::uint8_t>& encoded)
    {
        const int first = line.indexOf(' ');
        const int second = first < 0 ? -1 : line.indexOf(' ', first + 1);
        const int third = second < 0 ? -1 : line.indexOf(' ', second + 1);
        if (third < 0)
            return false;

        String hex = line.substring(third + 1);
        hex.trim();
        return prop_protocol::hexToBytes(std::string(hex.c_str()), encoded);
    }

    void reflectReceivedColors(const RenderColor colors[LED_COUNT], bool persistLedColors = true)
    {
        bool changed = !_dialColorsValid;
        bool persistedRgbChanged = false;
        for (int i = 0; i < LED_COUNT; ++i)
        {
            if (!sameColor(_dialColors[i], colors[i]))
                changed = true;
            if (!sameColor(_ledColors[i], colors[i]))
            {
                _ledColors[i] = colors[i];
                persistedRgbChanged = true;
            }
            _dialColors[i] = colors[i];
        }

        _dialColorsValid = true;
        if (persistedRgbChanged && persistLedColors)
            scheduleLedColorsPersist();
        if (changed || persistedRgbChanged)
        {
            markLocalDirty();
            _dirtyAll = true;
        }
    }

    void reflectPaletteColors(bool persistLedColors = true)
    {
        if (!_hasPalette || _paletteCount == 0)
            return;

        RenderColor colors[LED_COUNT] = {};
        for (int i = 0; i < LED_COUNT; ++i)
        {
            const std::uint8_t paletteIdx = static_cast<std::uint8_t>(
                i < _paletteCount ? i : (_paletteCount - 1));
            colors[i] = _palette[paletteIdx];
        }
        reflectReceivedColors(colors, persistLedColors);
    }

    bool applyLedPayload(const std::vector<std::uint8_t>& payload)
    {
        if (payload.size() != prop_protocol::LED_PAYLOAD_LENGTH)
            return false;

        RenderColor colors[LED_COUNT] = {};
        // The 13-byte LED_PAYLOAD carries EXACTLY 4 colours (brightness + 4xRGB). Bounding the
        // loop to 4 is REQUIRED at LED_COUNT=5: looping to LED_COUNT would read payload[13..15],
        // an out-of-bounds vector read (heap garbage / crash) on every Preview/Fire.
        for (int i = 0; i < 4; ++i)
        {
            colors[i].r = payload[1 + i * 3];
            colors[i].g = payload[2 + i * 3];
            colors[i].b = payload[3 + i * 3];
        }
        // LED#5 colour is NOT in this payload (it rides PaletteSet). Seed it from the
        // colour-PRESERVING accessor, never the raw _dialColors buffer: before the first
        // PaletteSet _dialColors[4]==(0,0,0), and feeding that to reflectReceivedColors below
        // would overwrite the persisted LED#5 default green with black AND persist it to NVS.
        // localColor(4) returns _dialColors[4] when valid, else the persisted _ledColors[4].
        colors[4] = localColor(4);
        reflectReceivedColors(colors);
        return true;
    }

    // Map a physical LED index to one of the LED_COUNT logical colour channels,
    // stretching the LED_COUNT channels across however many LEDs are currently active.
    // For _activeLeds == LED_COUNT this is the identity (i -> i); for more it groups, for
    // fewer it samples. Result is always clamped to a valid channel.
    int channelForLed(int i) const
    {
        // 5-LED rig (the documented hardware): physical pixel i == logical channel i, so the
        // odpal channel (3) is ALWAYS reachable (the old (i*LED_COUNT)/n integer division
        // dropped the top channel whenever _activeLeds != 4). Only stretch/sample for a
        // physically longer strip.
        if (_activeLeds <= LED_COUNT)
            return (i < LED_COUNT) ? i : (LED_COUNT - 1);
        const int n = _activeLeds;
        int c = (i * LED_COUNT) / n;
        if (c < 0) c = 0;
        if (c > LED_COUNT - 1) c = LED_COUNT - 1;
        return c;
    }

    bool storeLedBrightness()
    {
        PersistedLedBrightness blob{};
        blob.magic = LED_BRIGHTNESS_MAGIC;
        blob.version = LED_BRIGHTNESS_VERSION;
        for (int i = 0; i < LED_COUNT; ++i)
            blob.value[i] = _ledBrightness[i];
        blob.checksum = checksumBytes(
            reinterpret_cast<const std::uint8_t*>(&blob), sizeof(blob) - sizeof(blob.checksum));

        PersistedLedBrightness existing{};
        if (preferences.getBytesLength(LED_BRIGHTNESS_KEY) == sizeof(existing) &&
            preferences.getBytes(LED_BRIGHTNESS_KEY, &existing, sizeof(existing)) == sizeof(existing) &&
            std::memcmp(&existing, &blob, sizeof(blob)) == 0)
            return true;

        if (preferences.putBytes(LED_BRIGHTNESS_KEY, &blob, sizeof(blob)) != sizeof(blob))
        {
            _savedUntilMs = 0;
            setStatus("SAVE ERR");
            markStatusDirty();
            return false;
        }
        return true;
    }

    std::uint8_t budgetedBrightness(const RenderColor frame[LED_COUNT], std::uint8_t requested) const
    {
        std::uint32_t channelSum = 0;
        for (int i = 0; i < _activeLeds; ++i)
        {
            const RenderColor& c = frame[channelForLed(i)];
            channelSum += c.r + c.g + c.b;
        }

        if (channelSum == 0 || requested == 0)
            return requested;

        const std::uint32_t currentTimes255 = static_cast<std::uint32_t>(_activeLeds) * WS2812_IDLE_MA * 255UL +
                                              channelSum * WS2812_CHANNEL_MA * requested / 255UL;
        const std::uint32_t budgetTimes255 = LED_CURRENT_BUDGET_MA * 255UL;
        if (currentTimes255 <= budgetTimes255)
            return requested;

        const std::uint32_t scaled = static_cast<std::uint32_t>(requested) * budgetTimes255 / currentTimes255;
        return static_cast<std::uint8_t>(std::max<std::uint32_t>(1, std::min<std::uint32_t>(requested, scaled)));
    }

    static std::uint8_t maxRgb(const RenderColor& c)
    {
        return std::max<std::uint8_t>(c.r, std::max<std::uint8_t>(c.g, c.b));
    }

    void sendXiaoOutputFrame(const RenderColor frame[LED_COUNT])
    {
        std::array<prop_xiao_link::Rgb, prop_xiao_link::STATUS_LED_COUNT> status = {};
        for (std::size_t i = 0; i < status.size(); ++i)
        {
            const std::uint8_t logical = XIAO_STATUS_LED_CHANNELS[i];
            const RenderColor& c = frame[logical];
            status[i].r = c.r;
            status[i].g = c.g;
            status[i].b = c.b;
        }
        sendXiaoLine(prop_xiao_link::formatStat4Line(status));

        const std::uint8_t barrel = maxRgb(frame[LED_ROLE_ODPAL]);
        if (barrel == 0)
            sendXiaoLine(prop_xiao_link::formatBarrelOffLine());
        else
            sendXiaoLine(prop_xiao_link::formatBarrelRedLine(barrel));
        _xiaoLastTxMs = millis();
    }

    // Drives the first _activeLeds physical LEDs from the LED_COUNT logical channels and
    // clears the rest of the (LED_STRIP_MAX-sized) buffer, so a longer physical
    // strip never shows stray power-on garbage beyond the active range.
    void showBudgetedFrame(const RenderColor frame[LED_COUNT])
    {
        if (!PROP_IO_XIAO_UART_ENABLED && !_neoDriverPresent)   // NeoDriver absent at boot -> skip LED writes (never stall the loop)
            return;
        RenderColor preBudget[LED_COUNT] = {};
        for (int i = 0; i < LED_COUNT; ++i)
        {
            preBudget[i].r = scaleByteRound(frame[i].r, _ledBrightness[i]);
            preBudget[i].g = scaleByteRound(frame[i].g, _ledBrightness[i]);
            preBudget[i].b = scaleByteRound(frame[i].b, _ledBrightness[i]);
        }
        const std::uint8_t budgetScale = budgetedBrightness(preBudget, 255);

        RenderColor scaled[LED_COUNT] = {};
        for (int i = 0; i < LED_COUNT; ++i)
        {
            scaled[i].r = scaleByteRound(frame[i].r, _ledBrightness[i], budgetScale);
            scaled[i].g = scaleByteRound(frame[i].g, _ledBrightness[i], budgetScale);
            scaled[i].b = scaleByteRound(frame[i].b, _ledBrightness[i], budgetScale);
        }

        // Content guard: skip the (blocking) I2C strip write entirely if the final
        // budgeted RGB frame is identical to what is already on the strip.
        bool changed = _forceShow || (_lastShownBrightness != 0);
        for (int i = 0; i < LED_COUNT && !changed; ++i)
            if (scaled[i].r != _lastShown[i].r || scaled[i].g != _lastShown[i].g || scaled[i].b != _lastShown[i].b)
                changed = true;
        if (!changed)
            return;

        if (PROP_IO_XIAO_UART_ENABLED)
            sendXiaoOutputFrame(scaled);
        else
        {
            pixels.setBrightness(0);
            for (int i = 0; i < _activeLeds; ++i)
            {
                const RenderColor& c = scaled[channelForLed(i)];
                // LED ORDER REMAP (D4): logical channel -> physical pixel. This is the ONE place the
                // final frame[channel] is committed to the strip (odpal #4 and remote #5 included),
                // so reordering which physical LED a channel drives is a single edit to LED_ORDER.
                const int phys = (i < LED_COUNT) ? LED_ORDER[i] : i;
                pixels.setPixelColor(phys, c.r, c.g, c.b, 0);   // RGBW; white channel unused (Dial sends RGB)
            }
            pixels.show();
        }
        for (int i = 0; i < LED_COUNT; ++i)
            _lastShown[i] = scaled[i];
        _lastShownBrightness = 0;
        _forceShow = false;
    }

    void applyIdleOutput()
    {
        markLocalDirty();
    }

    void stopOutput(bool preserveArmed)
    {
        if (!preserveArmed)
        {
            _armed = false;
            _armExpiryMs = 0;
            _armEpoch = 0;
            _armSeq = 0;
        }
        _previewUntilMs = 0;
        _terminalPreviewUntilMs = 0;
        _odpalActive = false;   // SAFETY: a STOP / e-stop must kill an in-progress odpal IMMEDIATELY
                                // (was left burning for the rest of the ramp/hold/fade envelope).
        _led3RemoteOn = false;  // STOP is the master OFF for the REMOTE LED states (#3 remote, #5).
        _led5RemoteOn = false;
        // CONFIGURABLE master-off (default OFF -> local #1/#2 + physical switch #3 are preserved).
        // When enabled, STOP is a TOTAL kill: clear the local button latches AND raise an inhibit
        // that forces #1/#2/#3 dark and ignores the live switch until the next local input/edge
        // (released in readByteButton / activateVInput on any real edge, or on a fresh ARM).
        if (_stopClearsAllLocal)
        {
            _led1On = false;
            _led2On = false;
            _masterOffInhibit = true;
        }
        _forceShow = true;      // force the next strip write so LED4/LED5 actually go dark this frame
        applyIdleOutput();
        markLocalDirty();   // resume local LEDs #1-3 after a UI-stop / STOP frame (else they stay dark until next input)
        markStatusDirty();
    }

    void sendAck(const char* message)
    {
        // Diagnostic/status text ONLY -> USB console. This MUST NOT be written to
        // the modem (propSerial): the modem would treat it as a host command,
        // reply "ERR BAD_*", and that reply (being a non-"RX " line) would loop
        // back into handleLine() -> another sendAck -> a self-sustaining UART
        // ping-pong storm that saturates the link. Real frames go via sendAckFrame.
        Serial.println(message);
    }

    bool encodeAck(const prop_protocol::Frame& request, const char* message,
                   std::vector<std::uint8_t>& encoded)
    {
        prop_protocol::Frame ack;
        ack.type = prop_protocol::FrameType::Ack;
        ack.keyId = PROP_KEY_ID;
        ack.source = PROP_SOURCE;
        ack.destination = request.source;
        ack.sequence = request.sequence;
        ack.nonce = request.nonce;
        ack.payload.assign(message, message + strlen(message));
        const prop_runtime_key::RuntimeKey* key = runtimeKeyOrStatus();
        return key != nullptr && prop_protocol::encodeFrame(ack, key->data(), key->size(), encoded);
    }

    void transmitAck(const std::vector<std::uint8_t>& encoded)
    {
        const std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
        propSerial.print("ACK ");
        propSerial.println(hex.c_str());
        Serial.print("ACK ");
        Serial.println(hex.c_str());
#if DEBUG_HUD
        ++_debug.ackSent;
#endif
    }

    // Bidirectional colour sync (DinMeter -> Dial): push the 4 on-device preset colours as a
    // fire-and-forget LedColorSet (best-effort, no ack-wait) when the operator edits colours
    // locally, so the Dial's palette converges. Sent on leaving the Barvy page / on save.
    void sendLedColorSet()
    {
        prop_protocol::Frame f;
        f.type = prop_protocol::FrameType::LedColorSet;
        f.keyId = PROP_KEY_ID;
        f.source = PROP_SOURCE;
        f.destination = PROP_DESTINATION;
        f.sequence = ++_txSeq;
        f.nonce = (static_cast<std::uint64_t>(_txEpoch) << 32) | esp_random();
        f.payload.push_back(LOCAL_BRIGHTNESS);   // LED_PAYLOAD: brightness + 4x RGB (13 bytes, fixed)
        // Pin to 4 colours: this frame is the fixed 13-byte LED_PAYLOAD the Dial validates as
        // payload.size()==LED_PAYLOAD_LENGTH. Looping to LED_COUNT (5) would push 16 bytes and the
        // Dial silently drops the whole frame, breaking DinMeter->Dial colour sync. LED#5 rides
        // PaletteSet, never this payload (matches applyLedPayload's 4-colour bound + Dial first4).
        for (int i = 0; i < 4; ++i)
        {
            f.payload.push_back(_ledColors[i].r);
            f.payload.push_back(_ledColors[i].g);
            f.payload.push_back(_ledColors[i].b);
        }
        std::vector<std::uint8_t> encoded;
        const prop_runtime_key::RuntimeKey* key = runtimeKeyOrStatus();
        if (key == nullptr || !prop_protocol::encodeFrame(f, key->data(), key->size(), encoded))
            return;
        const std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
        propSerial.print("FF ");   // fire-and-forget (no ack-wait); modem parses FF as no-wait send
        propSerial.println(hex.c_str());
    }

    std::uint8_t nextTxPaletteRev()
    {
        _txPaletteRev = static_cast<std::uint8_t>(_txPaletteRev + 1U);
        if (_txPaletteRev == 0)
            _txPaletteRev = 1;
        return _txPaletteRev;
    }

    void sendPaletteSet()
    {
        prop_protocol::Frame f;
        f.type = prop_protocol::FrameType::PaletteSet;
        f.keyId = PROP_KEY_ID;
        f.source = PROP_SOURCE;
        f.destination = PROP_DESTINATION;
        f.sequence = ++_txSeq;
        f.nonce = (static_cast<std::uint64_t>(_txEpoch) << 32) | esp_random();

        prop_protocol::PalettePayload pal;
        pal.paletteRev = nextTxPaletteRev();
        pal.fade = false;
        pal.colors.reserve(LED_COUNT);
        for (int i = 0; i < LED_COUNT; ++i)
            pal.colors.push_back({_ledColors[i].r, _ledColors[i].g, _ledColors[i].b});

        if (!prop_protocol::encodePalettePayload(pal, f.payload))
            return;

        std::vector<std::uint8_t> encoded;
        const prop_runtime_key::RuntimeKey* key = runtimeKeyOrStatus();
        if (key == nullptr || !prop_protocol::encodeFrame(f, key->data(), key->size(), encoded))
            return;
        const std::string hex = prop_protocol::bytesToHex(encoded.data(), encoded.size());
        propSerial.print("FF ");
        propSerial.println(hex.c_str());
    }

    // Immediate ack -- for the request/response commands the sender actively waits
    // on (Preview / Stop / Ping / PaletteSet). These are single transmissions, so
    // no half-duplex burst collision.
    void sendAckFrame(const prop_protocol::Frame& request, const char* message)
    {
        std::vector<std::uint8_t> encoded;
        if (!encodeAck(request, message, encoded))
        {
            sendAck("ERR ACK_ENCODE");   // -> USB console only
            return;
        }
        transmitAck(encoded);
    }

    // Deferred ack -- ONLY for a fire-and-forget FIRE that actually starts the odpal
    // effect. Disabled/no-output odpal lanes reply NO_EFFECT/NO_XIAO immediately instead.
    // The sender transmits FIRE as a
    // 3x redundancy burst (~70 ms) and both radios are half-duplex, so an immediate
    // ack would land while the sender's modem is still bursting (deaf) and be lost.
    // We hold the ack and transmit it after the burst, inside the sender's long
    // RX-listen gap, so the best-effort confirmation actually arrives. A new FIRE
    // simply replaces any still-pending ack (latest event wins).
    void scheduleFireAck(const prop_protocol::Frame& request)
    {
        if (!encodeAck(request, "FIRE", _pendingAck))
        {
            _hasPendingAck = false;
            return;
        }
        _pendingAckMs = millis() + FIRE_ACK_DELAY_MS + (esp_random() % FIRE_ACK_JITTER_MS);
        _hasPendingAck = true;
    }

    void flushPendingAck()
    {
        if (_hasPendingAck && static_cast<std::int32_t>(millis() - _pendingAckMs) >= 0)
        {
            transmitAck(_pendingAck);
            _hasPendingAck = false;
        }
    }

    void serviceArmTtl()
    {
        // Sprint A (0.1): an ARM that is never followed by a Fire must not stay hot
        // forever. After the TTL it lapses back to SAFE (and drops any glow).
        if (_armed && static_cast<std::int32_t>(millis() - _armExpiryMs) >= 0)
        {
            _armed = false;
            _armExpiryMs = 0;
            _armEpoch = 0;
            _armSeq = 0;
            applyIdleOutput();
            setStatus("SAFE");
            markStatusDirty();
        }
    }

    void updateBattery()
    {
        if (millis() - _lastBatteryReadMs >= BATTERY_READ_MS)
            readBattery(false);
    }

    void readBattery(bool force)
    {
        const std::uint32_t now = millis();
        if (!force && _lastBatteryReadMs != 0 && now - _lastBatteryReadMs < BATTERY_READ_MS)
            return;

        _lastBatteryReadMs = now;
        _batteryMv = static_cast<std::uint16_t>(analogReadMilliVolts(10) * 2);
        const int percent = (static_cast<int>(_batteryMv) - 3300) * 100 / 900;
        // BUG FIX: clampByte() clamps to 0..255, so on USB power (mV high) the % overflowed
        // past 100 and showed e.g. "255%". A percentage must clamp to 0..100.
        const std::uint8_t newPct = static_cast<std::uint8_t>(std::max(0, std::min(100, percent)));
        if (newPct != _batteryPercent)   // only repaint the status bar when the % actually changes
        {
            _batteryPercent = newPct;
            markStatusDirty();
        }
    }

    void setStatus(const char* status)
    {
        if (_lastStatus != status)
        {
            _lastStatus = status;
            markStatusDirty();
        }
    }

    struct StateChip
    {
        const char* text;
        std::uint32_t fill;
        std::uint32_t textColor;
    };

    bool linkOk(std::uint32_t now) const
    {
        return now - _modemLastSeenMs < 2000;
    }

    // True when a received Fire would currently be honoured -- mirrors the RX Fire gate
    // (_armed && !_lockout && ARM not expired). Shared by the status chip AND the ODPAL row
    // so the two can never disagree. Wrap-safe signed millis() compare, as at the Fire gate.
    bool fireWouldArm() const
    {
        return _armed && !_lockout &&
               static_cast<std::int32_t>(millis() - _armExpiryMs) < 0;
    }

    StateChip dynamicStateChip() const
    {
        const std::uint32_t now = millis();
        if (_odpalActive)
            return {"PALI", COLOR_BAD, 0xFFFFFF};       // firing now
        if (_lockout)
            return {"STOP", COLOR_BAD, 0xFFFFFF};       // e-stop latched
        if (fireWouldArm())
            return {"NABITO", COLOR_WARN, 0x0A0C10};    // HOT: a Fire will trigger -> must be visible (Dial self-arms!)
        if (PROP_IO_XIAO_UART_ENABLED && !xiaoLinkOk(now))
            return {"XIAO?", COLOR_WARN, 0x0A0C10};
        if (!PROP_IO_XIAO_UART_ENABLED && !_neoDriverPresent)
            return {"CHYBA", COLOR_BAD, 0xFFFFFF};
        if (_modemEverSeen && !linkOk(now))
            return {"SPOJ?", COLOR_WARN, 0x0A0C10};     // link lost AFTER first contact (not pure standalone)
        if (_lastStatus == "SAVE ERR")
            return {"SAVE ERR", COLOR_BAD, 0xFFFFFF};
        if (now < _savedUntilMs)
            return {"ULOZ", COLOR_GOOD, 0x0A0C10};
        return {"KLID", dimRgb(COLOR_MUTED, 80), COLOR_MUTED};
    }

    void updateTransientUiState()
    {
        const std::uint32_t now = millis();
        const bool savedVisible = now < _savedUntilMs;
        const bool odpalVisible = _odpalActive;
        const bool currentLinkOk = linkOk(now);
        const bool currentXiaoLinkOk = !PROP_IO_XIAO_UART_ENABLED || xiaoLinkOk(now);
        if (savedVisible != _savedVisible ||
            odpalVisible != _odpalVisible ||
            currentLinkOk != _linkOkVisible ||
            currentXiaoLinkOk != _xiaoLinkOkVisible)
        {
            _savedVisible = savedVisible;
            _odpalVisible = odpalVisible;
            _linkOkVisible = currentLinkOk;
            _xiaoLinkOkVisible = currentXiaoLinkOk;
            markStatusDirty();
        }
#if DEBUG_HUD
        const bool bootVisible = now < _debugBootUntilMs;
        if (bootVisible != _debugBootVisible)
        {
            _debugBootVisible = bootVisible;
            _dirtyAll = true;
        }
#endif
    }

    void render(bool force)
    {
        if (!_ft || !_ft->_canvas)
            return;

        if (force)
        {
            _dirtyAll = true;
            _dirtyStatus = true;
        }

        updateTransientUiState();

#if DEBUG_HUD
        const std::uint32_t now = millis();
        const bool debugHudDue = shouldDrawDebugHud() &&
            (_debug.loopLastShowMs == 0 || now - _debug.loopLastShowMs >= DEBUG_HUD_REFRESH_MS);
#endif

        if (!_dirtyAll && !_dirtyStatus
#if DEBUG_HUD
            && !debugHudDue
#endif
        )
            return;

        auto* canvas = _ft->_canvas;

#if DEBUG_HUD
        if (_debugBootVisible)
        {
            drawDebugBootHud(canvas);
            clearDirtyFlags();
            _ft->_canvas_update();
            return;
        }
#endif

        if (_dirtyAll)
            canvas->fillScreen(COLOR_BG);

        switch (_page)
        {
            case UiPage::Stav:  drawStav(canvas); break;
            case UiPage::Barvy: drawBarvy(canvas); break;
            case UiPage::Cas:   drawCas(canvas); break;
            case UiPage::Jas:   drawJas(canvas); break;
        }

#if DEBUG_HUD
        if (shouldDrawDebugHud())
            drawDebugHud(canvas, now);
#endif

        clearDirtyFlags();
        _ft->_canvas_update();
    }

    void drawStav(LGFX_Sprite* canvas)
    {
        drawStatusBar(canvas);

        // FN_ROWS grew 4->5 (added LED#5). Pack the function rows + arrow into the area below the
        // status bar (y=22..135) by deriving rowH from the count so the 5th row + arrow stay on
        // the 135px screen (previously a fixed rowH=24 + arrow@118 overflowed / collided at 5 rows).
        constexpr int rowTop = 22;
        const int rowH = (SCREEN_H - rowTop) / (FN_ROWS + 1);   // function rows + 1 arrow slot
        for (int i = 0; i < FN_ROWS; ++i)
            drawFunctionRow(canvas, i, rowTop + i * rowH, rowH, _row == i);
        drawArrowRow(canvas, rowTop + FN_ROWS * rowH, rowH, onArrowRow(), "BARVY");
    }

    void drawStatusBar(LGFX_Sprite* canvas)
    {
        constexpr int barH = 21;
        canvas->fillRect(0, 0, SCREEN_W, barH, COLOR_BG);

        // Polish (Gemini lens 7): RF link dot FIRST (far left) so it never crowds the centre
        // chip; the mode token sits just right of it; the chip is slimmer for breathing room.
        const bool linkNow = linkOk(millis());
        const int dotX = 9;
        if (linkNow)
            canvas->fillCircle(dotX, barH / 2, 4, COLOR_GOOD);
        else
            canvas->drawCircle(dotX, barH / 2, 4, COLOR_BAD);

        const char* mode = PROP_IO_XIAO_UART_ENABLED ? "XIO" : (_byteBtnPresent ? "BB" : "EMU");
        const std::uint32_t modeColor = PROP_IO_XIAO_UART_ENABLED ? LABEL_DIM : (_byteBtnPresent ? LABEL_DIM : COLOR_WARN);
        drawStringVCenter(canvas, mode, dotX + 8, barH / 2, modeColor, COLOR_BG, 1, true);

        const StateChip chip = dynamicStateChip();
        useUiFont(canvas, 1, true);
        const int chipW = canvas->textWidth(chip.text) + 14;   // slimmer chip
        const int chipX = (SCREEN_W - chipW) / 2;
        canvas->fillRoundRect(chipX, 2, chipW, 17, 5, chip.fill);
        drawStringVCenter(canvas, chip.text, chipX + 7, barH / 2, chip.textColor, chip.fill, 1, true);

        drawBattery(canvas);
    }

    void drawFunctionRow(LGFX_Sprite* canvas, int row, int y, int h, bool selected)
    {
        static const char* LABELS[LED_COUNT] = {"LED 1", "LED 2", "SPINAC", "ODPAL", "LED 5"};
        const std::uint32_t bg = selected ? SELECT_BG : COLOR_BG;

        canvas->fillRect(0, y, SCREEN_W, h, COLOR_BG);
        if (selected)
        {
            canvas->fillRect(4, y + 1, SCREEN_W - 8, h - 2, SELECT_BG);
            canvas->fillRect(4, y + 1, 3, h - 2, COLOR_WARN);
        }
        // (ODPAL no longer gets a static left accent bar -- it was ambiguous with the
        //  selection cursor; the "READY"/"FIRE!" amber state already marks the action row.)

        const int cy = y + h / 2;
        // #3 (row 2) shows the EFFECTIVE state (D3): the live switch level, or remote-on while the
        // switch is OFF. #5 (row 4) shows the remote ON-only latch. #4 (row 3) is the odpal flash.
        const bool led3Effective = _switchEngaged || (!_switchEngaged && _led3RemoteOn);
        const bool on = (row == 0) ? _led1On : (row == 1) ? _led2On :
                        (row == 2) ? led3Effective : (row == 3) ? _odpalActive : _led5RemoteOn;
        const RenderColor c = localColor(row);
        const std::uint32_t dot = rgb(c.r, c.g, c.b);
        canvas->drawCircle(17, cy, 5, dimRgb(COLOR_MUTED, 130));
        canvas->fillCircle(17, cy, 4, on ? dot : dimRgb(dot, 85));   // dim the colour dot when the LED is off

        drawStringVCenter(canvas, LABELS[row], 29, cy, selected ? COLOR_TEXT : LABEL_DIM, bg, 2, true);
        if (row == 3 && _odpalActive)
        {
            constexpr int pillW = 48;
            constexpr int pillH = 16;
            const int pillX = SCREEN_W - 12 - pillW;
            canvas->fillRoundRect(pillX, cy - pillH / 2, pillW, pillH, 4, COLOR_BAD);
            drawCenterString(canvas, "FIRE!", pillX + pillW / 2, cy - 7, 0xFFFFFF, COLOR_BAD, 1, true);
        }
        else if (row == 3)
        {
            // ODPAL row shows the REAL fire-authority state (was a static "READY" lie even
            // when disarmed / STOP-latched). Mirrors dynamicStateChip via fireWouldArm().
            const char* token = _lockout ? "STOP" : (fireWouldArm() ? "NABITO" : "SAFE");
            const std::uint32_t tokenColor = _lockout ? COLOR_BAD
                                           : fireWouldArm() ? COLOR_WARN
                                           : (selected ? COLOR_TEXT : LABEL_DIM);
            drawRightString(canvas, token, SCREEN_W - 10, cy - 8, tokenColor, bg, 2, true);   // bigger state text
        }
        else if (row == 2)
        {
            // SPINAC is a level SWITCH (latch), not a toggle button -> draw a two-position
            // slider so it reads distinctly from the LED1/LED2 ON/OFF buttons (owner's #4).
            constexpr int trkW = 36, trkH = 16;
            const int tx = SCREEN_W - 12 - trkW;
            const int ty = cy - trkH / 2;
            canvas->fillRoundRect(tx, ty, trkW, trkH, trkH / 2, on ? dimRgb(COLOR_GOOD, 110) : TRACK_DIM);
            const int kr = (trkH - 4) / 2;
            const int kcx = on ? (tx + trkW - 2 - kr) : (tx + 2 + kr);
            canvas->fillCircle(kcx, cy, kr, on ? COLOR_GOOD : dimRgb(COLOR_MUTED, 170));
        }
        else
        {
            const char* token = on ? "ON" : "OFF";
            const std::uint32_t tokenColor = on ? COLOR_GOOD : (selected ? COLOR_TEXT : LABEL_DIM);   // OFF readable on the blue selection
            drawRightString(canvas, token, SCREEN_W - 10, cy - 8, tokenColor, bg, 2, true);   // bigger state text
        }
    }

    void drawArrowRow(LGFX_Sprite* canvas, int y, int h, bool selected, const char* nextHint)
    {
        canvas->fillRect(0, y, SCREEN_W, h, COLOR_BG);
        const std::uint32_t bg = selected ? SELECT_BG : COLOR_BG;
        if (selected)
        {
            canvas->fillRect(4, y + 1, SCREEN_W - 8, h - 2, SELECT_BG);
            canvas->fillRect(4, y + 1, 3, h - 2, COLOR_WARN);
        }

        const int cy = y + h / 2;
        drawStringVCenter(canvas, nextHint, 29, cy, selected ? COLOR_TEXT : LABEL_DIM, bg, 2, true);
        const int ax = SCREEN_W - 18;
        canvas->fillTriangle(ax, cy - 7, ax, cy + 7, ax + 11, cy, selected ? COLOR_WARN : COLOR_MUTED);
    }

    void drawBarvy(LGFX_Sprite* canvas)
    {
        static const char* LABELS[LED_COUNT] = {"LED 1", "LED 2", "SPINAC", "ODPAL", "LED 5"};
        // rowH derived from the count (FN_ROWS grew 4->5) so the 5th row + arrow fit the 135px screen.
        const int rowH = SCREEN_H / (FN_ROWS + 1);   // function rows + 1 arrow slot

        for (int i = 0; i < FN_ROWS; ++i)
        {
            const int y = i * rowH;
            const int cy = y + rowH / 2;
            const bool selected = (_row == i);
            const std::uint32_t bg = selected ? SELECT_BG : COLOR_BG;
            canvas->fillRect(0, y, SCREEN_W, rowH, COLOR_BG);
            if (selected)
            {
                canvas->fillRect(4, y + 1, SCREEN_W - 8, rowH - 2, SELECT_BG);
                canvas->fillRect(4, y + 1, 3, rowH - 2, COLOR_WARN);
            }

            const RenderColor c = localColor(i);
            const char* colorName = prop_colors::exactPresetName(c.r, c.g, c.b);
            canvas->fillRect(11, cy - 8, 26, 16, rgb(c.r, c.g, c.b));
            canvas->drawRect(11, cy - 8, 26, 16, dimRgb(COLOR_MUTED, 150));
            drawStringVCenter(canvas, LABELS[i], 44, cy, selected ? COLOR_TEXT : LABEL_DIM, bg, 2, true);
            drawRightString(canvas, colorName, SCREEN_W - 10, cy - 8, selected ? COLOR_TEXT : COLOR_MUTED, bg, 2, true);
        }

        drawArrowRow(canvas, FN_ROWS * rowH, rowH, onArrowRow(), "CAS");
    }

    void drawCas(LGFX_Sprite* canvas)
    {
        // Cas is pinned to CAS_FN_ROWS (4 odpal fields), NOT FN_ROWS: growing LED_COUNT must not
        // add a 5th (label-less / out-of-range) odpal row. rowH=27 keeps 4 rows + arrow at 135px.
        static const char* LABELS[CAS_FN_ROWS] = {"NABEH", "SVIT", "ZHASNUTI", "KRIVKA"};
        constexpr int rowH = 27;
        char value[14] = {0};

        for (int i = 0; i < CAS_FN_ROWS; ++i)
        {
            const int y = i * rowH;
            const int cy = y + rowH / 2;
            const bool selected = (_row == i);
            const bool editing = _editing && selected && i < 3;

            if (i == 0)
                snprintf(value, sizeof(value), "%u ms", static_cast<unsigned>(_odpal.rampMs));
            else if (i == 1)
                snprintf(value, sizeof(value), "%u ms", static_cast<unsigned>(_odpal.holdMs));
            else if (i == 2)
                snprintf(value, sizeof(value), "%u ms", static_cast<unsigned>(_odpal.fadeMs));
            else
                snprintf(value, sizeof(value), "%s",
                         ODPAL_CURVE_NAMES[_odpal.curve < NUM_ODPAL_CURVES ? _odpal.curve : 0]);

            const std::uint32_t bg = selected ? (editing ? COLOR_WARN : SELECT_BG) : COLOR_BG;
            const std::uint32_t fg = selected ? (editing ? 0x0A0C10 : COLOR_TEXT) : LABEL_DIM;
            canvas->fillRect(0, y, SCREEN_W, rowH, COLOR_BG);
            if (selected)
            {
                canvas->fillRect(4, y + 1, SCREEN_W - 8, rowH - 2, editing ? COLOR_WARN : SELECT_BG);
                if (!editing)
                    canvas->fillRect(4, y + 1, 3, rowH - 2, COLOR_WARN);
            }

            drawStringVCenter(canvas, LABELS[i], 29, cy, fg, bg, 2, true);
            drawRightString(canvas, value, SCREEN_W - 10, cy - 8, (selected || editing) ? fg : COLOR_MUTED, bg, 2, true);
        }

        drawArrowRow(canvas, CAS_FN_ROWS * rowH, rowH, onArrowRow(), "JAS");
    }

    // Jas page: per-LED brightness (FN_ROWS rows, ADJUST=amber) + arrow.
    void drawJas(LGFX_Sprite* canvas)
    {
        static const char* LABELS[FN_ROWS] = {"LED1", "LED2", "LED3", "LED4", "LED5"};
        // rowH derived from the count (FN_ROWS grew 4->5) so the 5th row + arrow fit the 135px screen.
        const int rowH = SCREEN_H / (FN_ROWS + 1);   // function rows + 1 arrow slot
        char value[8] = {0};

        for (int i = 0; i < FN_ROWS; ++i)
        {
            const int y = i * rowH;
            const int cy = y + rowH / 2;
            const bool selected = (_row == i);
            const bool editing = _editing && selected;
            const int pct = (static_cast<int>(_ledBrightness[i]) * 100 + 127) / 255;
            snprintf(value, sizeof(value), "%d%%", pct);

            const std::uint32_t bg = selected ? (editing ? COLOR_WARN : SELECT_BG) : COLOR_BG;
            const std::uint32_t fg = selected ? (editing ? 0x0A0C10 : COLOR_TEXT) : LABEL_DIM;
            canvas->fillRect(0, y, SCREEN_W, rowH, COLOR_BG);
            if (selected)
            {
                canvas->fillRect(4, y + 1, SCREEN_W - 8, rowH - 2, editing ? COLOR_WARN : SELECT_BG);
                if (!editing)
                    canvas->fillRect(4, y + 1, 3, rowH - 2, COLOR_WARN);
            }

            drawStringVCenter(canvas, LABELS[i], 29, cy, fg, bg, 2, true);
            // Per-LED brightness bar (Gemini UI review): a dark track so the fill pops on both the
            // select-grey and the edit-amber row; the fill is THIS LED's actual colour at full luma
            // (at-a-glance "which LED am I dimming") while browsing, and WHITE while editing (max
            // contrast so the level stays readable as the encoder turns). Wider bar tightens the
            // bar->value gap while the % stays right-aligned (consistent with the sibling pages).
            constexpr int barX = 86, barW = 80, barH = 8;
            const int barY = cy - barH / 2;
            canvas->fillRoundRect(barX, barY, barW, barH, barH / 2, 0x0A0C10);
            const int fillW = std::max(barH, barW * pct / 100);
            std::uint32_t barColor;
            if (editing)
                barColor = 0xFFFFFF;
            else
            {
                const RenderColor lc = localColor(i);
                const int peak = std::max(lc.r, std::max(lc.g, lc.b));
                barColor = (peak == 0) ? COLOR_MUTED
                         : rgb(lc.r * 255 / peak, lc.g * 255 / peak, lc.b * 255 / peak);
            }
            canvas->fillRoundRect(barX, barY, fillW, barH, barH / 2, barColor);
            drawRightString(canvas, value, SCREEN_W - 10, cy - 8, (selected || editing) ? fg : COLOR_MUTED, bg, 2, true);
        }

        // 1px separator sets the STAV navigation arrow apart from the per-LED controls.
        const int arrowY = FN_ROWS * rowH;
        drawArrowRow(canvas, arrowY, rowH, onArrowRow(), "STAV");
        canvas->fillRect(8, arrowY, SCREEN_W - 16, 1, dimRgb(COLOR_MUTED, 90));
    }

    void drawRectOutline(
        LGFX_Sprite* canvas,
        int x,
        int y,
        int w,
        int h,
        std::uint32_t color,
        int width)
    {
        for (int i = 0; i < width; ++i)
            canvas->drawRect(x + i, y + i, w - i * 2, h - i * 2, color);
    }

    void drawStringVCenter(
        LGFX_Sprite* canvas,
        const char* text,
        int x,
        int cy,
        std::uint32_t fg,
        std::uint32_t bg,
        int tier,
        bool bold)
    {
        useUiFont(canvas, tier, bold);
        canvas->setTextColor(fg, bg);
        const int y = cy - canvas->fontHeight() / 2;
        canvas->drawString(text, x, y);
    }

    void drawWarningGlyph(
        LGFX_Sprite* canvas,
        int cx,
        int cy,
        int size,
        std::uint32_t triColor,
        std::uint32_t bangColor,
        std::uint32_t bgColor,
        bool solid)
    {
        const int h = static_cast<int>(size * 1.6f);
        const int x0 = cx;
        const int y0 = cy - h / 2;
        const int x1 = cx - size;
        const int y1 = cy + h / 2;
        const int x2 = cx + size;
        const int y2 = cy + h / 2;
        if (solid)
        {
            canvas->fillTriangle(x0, y0, x1, y1, x2, y2, triColor);
        }
        else
        {
            canvas->drawLine(x0, y0, x1, y1, triColor);
            canvas->drawLine(x1, y1, x2, y2, triColor);
            canvas->drawLine(x2, y2, x0, y0, triColor);
            canvas->drawLine(x0, y0 + 1, x1, y1 + 1, triColor);
            canvas->drawLine(x1, y1 - 1, x2, y2 - 1, triColor);
            canvas->drawLine(x2, y2 + 1, x0, y0 + 1, triColor);
        }

        useUiFont(canvas, 1, true);
        canvas->setTextColor(solid ? bangColor : triColor, solid ? triColor : bgColor);
        const int bangW = canvas->textWidth("!");
        const int bangY = cy + 1 - canvas->fontHeight() / 2;
        canvas->drawString("!", cx - bangW / 2, bangY);
    }

#if DEBUG_HUD
    bool shouldDrawDebugHud() const
    {
        if (!DIAG_DISPLAY)   // on-LCD HUD compiled-out by default -> clean operator screen
            return false;
        if (_debugBootVisible || _page != UiPage::Stav)
            return false;
        return true;
    }

    void drawDebugBootHud(LGFX_Sprite* canvas)
    {
        char text[48] = {0};
        const std::uint32_t freeKb = esp_get_free_heap_size() / 1024;
        snprintf(text, sizeof(text), "BOOT: %s heap%lu",
                 _debug.bootReason,
                 static_cast<unsigned long>(freeKb));

        canvas->fillScreen(COLOR_BG);
        useUiFont(canvas, 2, false);
        if (canvas->textWidth(text) > SCREEN_W - 8)
            drawCenterString(canvas, text, SCREEN_W / 2, (SCREEN_H - 16) / 2, COLOR_MUTED, COLOR_BG, 1, false);
        else
            drawCenterString(canvas, text, SCREEN_W / 2, (SCREEN_H - 16) / 2, COLOR_MUTED, COLOR_BG, 2, false);
    }

    void drawDebugHud(LGFX_Sprite* canvas, std::uint32_t now)
    {
        const int y = 118;
        const std::uint32_t heapBytes = _debug.minFreeHeap == 0xFFFFFFFF
            ? esp_get_free_heap_size()
            : _debug.minFreeHeap;

        char text[72] = {0};
        snprintf(text, sizeof(text), "Lm%lu RX%lu D%lu R%lu B%lu H%lu",
                 static_cast<unsigned long>(_debug.loopMaxUs / 1000),
                 static_cast<unsigned long>(_debug.rxValid),
                 static_cast<unsigned long>(_debug.rxDup),
                 static_cast<unsigned long>(_debug.rxStale),
                 static_cast<unsigned long>(_debug.rxBad),
                 static_cast<unsigned long>(heapBytes / 1024));
        char text2[64] = {0};
        snprintf(text2, sizeof(text2), "E:%lu L:%lu F:%lu Q:%lu",
                 static_cast<unsigned long>(_debug.rxEspnow),
                 static_cast<unsigned long>(_debug.rxLora),
                 static_cast<unsigned long>(_debug.healthForeign),
                 static_cast<unsigned long>(_debug.healthQdrop));

        canvas->fillRect(0, y, SCREEN_W, SCREEN_H - y, COLOR_BG);
        useUiFont(canvas, 1, false);
        canvas->setTextColor(COLOR_MUTED, COLOR_BG);
        canvas->drawString(text, 2, y);
        canvas->drawString(text2, 2, y + canvas->fontHeight());

        _debug.loopMaxUs = 0;
        _debug.loopLastShowMs = now;
    }
#endif

    void drawBattery(LGFX_Sprite* canvas)
    {
        constexpr int right = 234;
        constexpr int barW = 24;   // bigger battery glyph (was 18)
        constexpr int barH = 13;   // (was 10)
        constexpr int nubW = 3;
        char pct[8] = {0};
        snprintf(pct, sizeof(pct), "%u%%", static_cast<unsigned>(_batteryPercent));

        useUiFont(canvas, 2, true);   // bigger % text (tier 2, was tier 1)
        const int textW = canvas->textWidth(pct);
        const int barX = right - textW - 6 - nubW - barW;
        constexpr int barY = 4;
        canvas->drawRect(barX, barY, barW, barH, COLOR_TEXT);
        canvas->fillRect(barX + barW, barY + 4, nubW, barH - 8, COLOR_TEXT);
        const int fillW = std::max(0, std::min(barW - 4, (_batteryPercent * (barW - 4)) / 100));
        canvas->fillRect(barX + 2, barY + 2, fillW, barH - 4, batteryColor());
        canvas->setTextColor(batteryColor(), COLOR_BG);
        canvas->drawString(pct, right - textW, 2);
    }

    std::uint32_t batteryColor() const
    {
        if (_batteryPercent > 40)
            return COLOR_GOOD;
        if (_batteryPercent >= 20)
            return COLOR_WARN;
        return COLOR_BAD;
    }

    void drawRightString(
        LGFX_Sprite* canvas,
        const char* text,
        int right,
        int y,
        std::uint32_t fg,
        std::uint32_t bg,
        int tier,
        bool bold)
    {
        useUiFont(canvas, tier, bold);
        canvas->setTextColor(fg, bg);
        canvas->drawString(text, right - canvas->textWidth(text), y);
    }

    void drawCenterString(
        LGFX_Sprite* canvas,
        const char* text,
        int cx,
        int y,
        std::uint32_t fg,
        std::uint32_t bg,
        int tier,
        bool bold)
    {
        useUiFont(canvas, tier, bold);
        canvas->setTextColor(fg, bg);
        canvas->drawString(text, cx - canvas->textWidth(text) / 2, y);
    }

    void markStatusDirty()
    {
        _dirtyStatus = true;
    }

    void clearDirtyFlags()
    {
        _dirtyAll = false;
        _dirtyStatus = false;
    }

    FactoryTest* _ft;
    RenderColor _dialColors[LED_COUNT] = {};
    bool _dialColorsValid = false;   // true once Dial Preview/Fire/PaletteSet pushed colours (precedence over on-device state)
    std::uint32_t _txSeq = 0;        // DinMeter-originated frame sequence (colour/palette sync)
    std::uint8_t _txPaletteRev = 1;  // DinMeter-originated palette sync revision for Terminal uploads
    std::uint32_t _txEpoch = 0;      // DinMeter TX epoch (random per boot; top 32 bits of nonce)
    // Local prop controls (ByteButton) -> SK6812 #1-3 state; #4 reserved for odpal (TBD).
    bool _led1On = false;     // SK6812 #1 latch (button 1)
    bool _led2On = false;     // SK6812 #2 latch (button 2)
    bool _led3On = false;     // legacy switch-edge latch (Stav indicator / encoder-EMU only; no longer drives #3)
    bool _switchEngaged = false;  // LIVE level of the ByteButton switch (idx0), tracked every poll -> drives #3 locally (D3)
    bool _led3RemoteOn  = false;  // Dial wants LED#3 on (honoured ON-only, and only while the switch is OFF -- strict, D2)
    bool _led5RemoteOn  = false;  // Dial wants LED#5 on (always honoured; ON-only; cleared by STOP)
    bool _bbPrev1 = false;    // previous pressed-state of button 1 (edge detect)
    bool _bbPrev2 = false;    // previous pressed-state of button 2 (edge detect)
    bool _bbPrev3 = false;    // previous pressed-state of the local fire button (edge detect)
    bool _bbPrevSw = false;   // previous pressed-state of the switch input (idx0 edge -> latch)
    std::uint32_t _bbLastPollMs = 0;   // ByteButton read throttle (non-blocking; bounded I2C)
    std::uint32_t _bbPresenceMs = 0;   // ByteButton hot-plug probe throttle
    int _bbFailCount = 0;              // consecutive I2C read failures -> fall back to EMU (anti-phantom)
    int _i2cSda = I2C_SDA_PIN;         // resolved Port-B orientation (for hot-plug begin)
    int _i2cScl = I2C_SCL_PIN;
    // Factory defaults for these now live in prop_config.h section [B] and are
    // applied at the TOP of begin() (DEFAULT_LED_PRESET_IDX / DEFAULT_LED_BRIGHTNESS /
    // DEFAULT_ODPAL_*) before any NVS load. The member initialisers here are just
    // a harmless zero-fill so an instance is never indeterminate -- begin() is the
    // single source of truth, and a valid NVS blob then overrides it.
    std::uint8_t _ledColorIdx[LED_COUNT] = {};   // seeded in begin() from DEFAULT_LED_PRESET_IDX (config [B])
    RenderColor _ledColors[LED_COUNT] = {};      // seeded in begin() = presetRenderColor(DEFAULT_LED_PRESET_IDX[i])
    OdpalEnvelope _odpal;     // LED4 odpal envelope (ramp/hold/fade ms + curve); seeded in begin() from DEFAULT_ODPAL_* (config [B])
    std::uint8_t _ledBrightness[LED_COUNT] = {}; // seeded in begin() from DEFAULT_LED_BRIGHTNESS (config [B]); Jas page edits per-LED, persisted; budget still caps the sum
    int _row = 0;             // per-page cursor; row 4 is the navigation arrow
    bool _editing = false;    // Cas page: SELECT vs ADJUST (encoder changes value) for ms rows only
    static constexpr int FN_ROWS = LED_COUNT;
    static constexpr int ARROW_ROW = FN_ROWS;
    static constexpr int ROWS_PER_PAGE = FN_ROWS + 1;
    std::uint32_t _lastHeartbeatMs = 0;   // serial telemetry pacing for read_com.py
    int _foundAddr = -1;      // last I2C address the Port B scan saw (diagnostic for unknown modules)
    bool _localDirty = true;  // redraw the local-control frame on the next idle loop
    std::uint32_t _previewUntilMs = 0; // nonzero while Dial Preview owns a visible full-strip overlay
    std::uint32_t _terminalPreviewUntilMs = 0; // nonzero while Terminal SIM_FIRE owns an effect-mask overlay
    bool _ledColorsPersistDirty = false;
    bool _palettePersistDirty = false;
    bool _localColorEditPending = false;  // a local Barvy edit awaits save -> drop pal1 so it wins on next boot
    std::uint32_t _deferredPersistDueMs = 0;
    // Content-guard cache for showBudgetedFrame -> skip redundant (blocking) I2C strip writes.
    RenderColor _lastShown[LED_COUNT] = {};
    std::uint8_t _lastShownBrightness = 0;
    bool _forceShow = true;   // force the next strip write (boot self-test / settings preview / odpal start)
    StaticColorFade _staticFade[3] = {};   // channels 0..2 only; channel 3 is the odpal envelope
    std::uint32_t _lastStaticFadeDrawMs = 0;
    int  _bbRawPrev = -1;     // last logged ByteButton snapshot (DEBUG_HUD bring-up only)
    bool _byteBtnPresent   = false;   // ByteButton 0x47 answered the boot scan (else skip its I2C polls)
    bool _neoDriverPresent = false;   // NeoDriver 0x60 answered the boot scan (else skip LED writes)
    bool _odpalActive = false;        // generic odpal flash on SK6812 #4 in progress
    std::uint32_t _odpalStartMs = 0;
    std::uint32_t _lastOdpalDrawMs = 0;   // throttle for the odpal animation redraw
    RenderColor _palette[prop_protocol::MAX_PALETTE_COLORS] = {};
    std::uint8_t _paletteCount = 0;
    bool         _paletteFade  = false;
    std::uint8_t _paletteRev   = 0;
    bool         _hasPalette   = false;
    UiPage _page = UiPage::Stav;
    String _line;
    bool _lineOverflow = false;   // true while discarding the tail of an over-long UART line
    String _usbSetupLine;
    bool _usbSetupOverflow = false;
    String _xiaoLine;
    bool _xiaoLineOverflow = false;
    bool _xiaoIoPresent = false;
    bool _xiaoBtn1 = false;
    bool _xiaoBtn2 = false;
    bool _xiaoFire = false;
    bool _xiaoSwitch = false;
    std::uint32_t _xiaoLastSeenMs = 0;
    std::uint32_t _xiaoLastPingMs = 0;
    std::uint32_t _xiaoLastTxMs = 0;
    std::uint16_t _xiaoPingSeq = 1;
    String _lastLine = "-";
    String _lastStatus = "BOOT";
    std::uint32_t _modemLastSeenMs = 0;   // last OK/BOOT seen from modem (liveness)
    bool _modemEverSeen = false;          // a modem/link was seen at least once (standalone: no Dial != error)
    int _activeLeds = LED_COUNT;          // physical LEDs driven (1..LED_STRIP_MAX); rest forced off
    std::vector<std::uint8_t> _pendingAck;   // deferred fire-and-forget ack bytes
    std::uint32_t _pendingAckMs = 0;         // millis() when the deferred ack is due
    bool _hasPendingAck = false;
    std::uint32_t _lastAcceptedSequence = 0;
    std::uint32_t _lastPersistedSequence = 0;
    std::uint32_t _lastEpoch = 0;
    std::uint32_t _rxWindowBase = 0;
    std::uint32_t _rxWindowMask = 0;
    std::uint32_t _buttonDownMs = 0;
    std::uint32_t _lastBatteryReadMs = 0;
    std::uint32_t _savedUntilMs = 0;
    bool _savedVisible = false;
    bool _odpalVisible = false;
    bool _linkOkVisible = true;
    bool _xiaoLinkOkVisible = true;
    long _lastEncoderPos = 0;
    int _encAccum = 0;                              // raw encoder counts pending a full detent
    std::uint32_t _encLastCountMs = 0;              // last raw-count time (idle-flush of a stale half-detent)
    static constexpr int ENC_COUNTS_PER_DETENT = 2; // half-quad: ~2 raw counts == 1 click
    std::uint16_t _batteryMv = 0;
    std::uint8_t _batteryPercent = 0;
    bool _buttonDown = false;
    bool _exitRequested = false;
    bool _armed = false;                          // Sprint A: set ONLY by Arm frame (no longer by Preview)
    std::uint32_t _armExpiryMs = 0;               // Sprint A: ARM has a safety TTL backstop
    std::uint32_t _armEpoch = 0;                  // epoch of the ARM currently authorising one FIRE
    std::uint32_t _armSeq = 0;                    // FIRE must post-date this ARM sequence
    bool _lockout = false;                         // Sprint A: latched after STOP until next Arm
    std::uint32_t _lockoutSeq = 0;                 // sequence of the latching STOP; backfilled
                                                   // ARM/FIRE with seq <= this cannot re-arm/fire
    // STOP master-off mode (see STOP_CLEARS_ALL_LOCAL_DEFAULT). When _stopClearsAllLocal is true a
    // STOP also clears the local #1/#2 latches and raises _masterOffInhibit, which forces the local
    // channels (#1/#2/#3) dark and ignores the physical switch until the next LOCAL input/edge.
    bool _stopClearsAllLocal = STOP_CLEARS_ALL_LOCAL_DEFAULT;
    bool _masterOffInhibit = false;                // true: suppress ALL local LED output until a local edge
    std::uint8_t _terminalEffectMask = DEFAULT_TERMINAL_EFFECT_PREVIEW_MASK;   // Terminal USB setup: effect lanes
    std::uint8_t _terminalPreviewMask = DEFAULT_TERMINAL_EFFECT_PREVIEW_MASK;  // lanes that invert state during Terminal SIM_FIRE
    // A2 (0.3): TTL is refreshed by the Dial's 5 s ARM-heartbeat. If the heartbeat
    // stops (Dial off / link jammed) the receiver lapses to SAFE within this window.
    static constexpr std::uint32_t ARM_TTL_MS = 12000;  // ~2 missed 5 s heartbeats
    bool _dirtyAll = true;
    bool _dirtyStatus = true;
    prop_runtime_key::RuntimeKey _runtimeKey;
#if DEBUG_HUD
    DebugHudStats _debug;
    std::uint32_t _debugBootUntilMs = 0;
    bool _debugBootVisible = false;
#endif
};
} // namespace

// --- software watchdog (0.4) ----------------------------------------------
// Reboot the receiver if its main loop stops being serviced (hang detection).
// Deliberately framework-AGNOSTIC: din-rx's Arduino framework ping-pongs between
// IDF 4.4 (esp_task_wdt_init(timeout,bool)) and IDF 5.x (struct API), whose
// hardware Task-WDT APIs are source-incompatible; this uses only stable FreeRTOS
// + esp_restart() calls so it builds in either state. A reboot is fail-safe:
// begin() comes up disarmed, outputs off, status "KLID", and the persisted
// lastSeq/epoch block any replay re-fire after the reset.
static volatile std::uint32_t s_wdtLastFeedMs = 0;
static TaskHandle_t s_wdtTask = nullptr;              // handle so the watchdog can be stopped on exit
static constexpr std::uint32_t WDT_TIMEOUT_MS = 8000;  // >> worst-case loop (<1s); < ARM TTL 12s

static void propWatchdogTask(void*)
{
    for (;;)
    {
        vTaskDelay(pdMS_TO_TICKS(500));
        const std::uint32_t fed = s_wdtLastFeedMs;
        if (fed != 0 && (millis() - fed) > WDT_TIMEOUT_MS)
        {
            esp_restart();  // fail-safe reboot -> receiver returns to disarmed/KLID
        }
    }
}

void prop_rx_run(FactoryTest* ft)
{
    PropRxApp app(ft);
    app.begin();

    // Arm the software watchdog only AFTER begin() so the boot splash (delay 1600
    // in setup()) and init can never trip it. Pinned to core 0 (the receiver loop
    // runs on core 1) at top priority, so a wedged loop is always preempted and
    // detected even if core 1 is 100% busy.
    s_wdtLastFeedMs = millis();
    if (s_wdtTask == nullptr)   // exactly one watchdog task per run -- never leak or duplicate
    {
        xTaskCreatePinnedToCore(propWatchdogTask, "propWdt", 2048, nullptr,
                                configMAX_PRIORITIES - 1, &s_wdtTask, 0);
    }

    while (!app.shouldExit())
    {
        app.update();
        s_wdtLastFeedMs = millis();  // fed after real work each iteration
        delay(5);
    }

    // Clean exit: disarm the watchdog (it only fires when fed != 0) then delete its task, so
    // leaving the receiver app never triggers a spurious reboot, leaks the task, or spawns a
    // duplicate watchdog on re-entry.
    s_wdtLastFeedMs = 0;
    if (s_wdtTask != nullptr)
    {
        vTaskDelete(s_wdtTask);
        s_wdtTask = nullptr;
    }

    app.end();
}
