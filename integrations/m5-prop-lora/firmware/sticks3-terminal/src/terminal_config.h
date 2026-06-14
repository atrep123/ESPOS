#pragma once

#include <array>
#include <cstdint>

#include "terminal_hardware_topology.h"

namespace terminal_config {

#ifndef TERMINAL_UPLOAD_SWITCH_PIN
#define TERMINAL_UPLOAD_SWITCH_PIN -1
#endif

#ifndef TERMINAL_SIM_FIRE_SWITCH_PIN
#define TERMINAL_SIM_FIRE_SWITCH_PIN -1
#endif

#ifndef TERMINAL_SWITCH_DEBOUNCE_MS
#define TERMINAL_SWITCH_DEBOUNCE_MS 30
#endif

#ifndef TERMINAL_FADER_RAW_MIN
#define TERMINAL_FADER_RAW_MIN 0
#endif

#ifndef TERMINAL_FADER_RAW_MAX
#define TERMINAL_FADER_RAW_MAX 4095
#endif

#ifndef TERMINAL_FADER_DEADBAND_PERCENT
#define TERMINAL_FADER_DEADBAND_PERCENT 1
#endif

#ifndef TERMINAL_FADER_ADC_ENABLED
#define TERMINAL_FADER_ADC_ENABLED 0
#endif

#ifndef TERMINAL_FADER_LANE1_ADC_PIN
#define TERMINAL_FADER_LANE1_ADC_PIN -1
#endif

#ifndef TERMINAL_FADER_LANE2_ADC_PIN
#define TERMINAL_FADER_LANE2_ADC_PIN -1
#endif

#ifndef TERMINAL_FADER_LANE3_ADC_PIN
#define TERMINAL_FADER_LANE3_ADC_PIN -1
#endif

#ifndef TERMINAL_FADER_LANE4_ADC_PIN
#define TERMINAL_FADER_LANE4_ADC_PIN -1
#endif

#ifndef TERMINAL_FADER_LANE5_ADC_PIN
#define TERMINAL_FADER_LANE5_ADC_PIN -1
#endif

#ifndef TERMINAL_ENCODER_DEGREES_PER_DETENT
#define TERMINAL_ENCODER_DEGREES_PER_DETENT 6
#endif

#ifndef TERMINAL_LIVE_DEBUG
#define TERMINAL_LIVE_DEBUG 0
#endif

#ifndef TERMINAL_CHAIN_RX_PIN
#define TERMINAL_CHAIN_RX_PIN -1
#endif

#ifndef TERMINAL_CHAIN_TX_PIN
#define TERMINAL_CHAIN_TX_PIN -1
#endif

#ifndef TERMINAL_CHAIN_BAUD
#define TERMINAL_CHAIN_BAUD 115200
#endif

#ifndef TERMINAL_REQUIRE_CHAIN_UART
#define TERMINAL_REQUIRE_CHAIN_UART 0
#endif

#ifndef TERMINAL_CHAIN_UART_SMOKE
#define TERMINAL_CHAIN_UART_SMOKE 0
#endif

#ifndef TERMINAL_CHAIN_UART_SELECT_PAHUB
#define TERMINAL_CHAIN_UART_SELECT_PAHUB 0
#endif

#ifndef TERMINAL_CHAIN_PAHUB_ADDRESS
#define TERMINAL_CHAIN_PAHUB_ADDRESS 0x70
#endif

#ifndef TERMINAL_CHAIN_PAHUB_CHANNEL
#define TERMINAL_CHAIN_PAHUB_CHANNEL 0
#endif

#ifndef TERMINAL_CHAIN_PAHUB_SDA_PIN
#define TERMINAL_CHAIN_PAHUB_SDA_PIN TERMINAL_CHAIN_RX_PIN
#endif

#ifndef TERMINAL_CHAIN_PAHUB_SCL_PIN
#define TERMINAL_CHAIN_PAHUB_SCL_PIN TERMINAL_CHAIN_TX_PIN
#endif

#ifndef TERMINAL_EXTERNAL_OLED_ENABLED
#define TERMINAL_EXTERNAL_OLED_ENABLED 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_SDA_PIN
#define TERMINAL_EXTERNAL_OLED_SDA_PIN -1
#endif

#ifndef TERMINAL_EXTERNAL_OLED_SCL_PIN
#define TERMINAL_EXTERNAL_OLED_SCL_PIN -1
#endif

#ifndef TERMINAL_EXTERNAL_OLED_I2C_ADDRESS
#define TERMINAL_EXTERNAL_OLED_I2C_ADDRESS 0x3C
#endif

#ifndef TERMINAL_EXTERNAL_OLED_I2C_PORT
#define TERMINAL_EXTERNAL_OLED_I2C_PORT 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_I2C_FREQ
#define TERMINAL_EXTERNAL_OLED_I2C_FREQ 400000
#endif

#ifndef TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2
#define TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_DRIVER_SSD1309
#define TERMINAL_EXTERNAL_OLED_DRIVER_SSD1309 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED
#define TERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_I2C_SCAN_SMOKE
#define TERMINAL_EXTERNAL_OLED_I2C_SCAN_SMOKE 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_DRAW_SMOKE
#define TERMINAL_EXTERNAL_OLED_DRAW_SMOKE 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_SELECT_PAHUB
#define TERMINAL_EXTERNAL_OLED_SELECT_PAHUB 0
#endif

#ifndef TERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS
#define TERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS 0x70
#endif

#ifndef TERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL
#define TERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL 3
#endif

#ifndef TERMINAL_I2C_SCAN_PAHUB_CHANNELS
#define TERMINAL_I2C_SCAN_PAHUB_CHANNELS 0
#endif

// M5StickS3 Terminal setup controller. It has no radio module; setup traffic is
// a local USB setup link to the prop-side service.
constexpr int USB_SETUP_BAUD = 115200;
constexpr std::uint16_t USB_LINE_MAX = 160;
constexpr std::uint8_t TERMINAL_LANE_COUNT = 5;
constexpr std::uint32_t STATUS_REDRAW_MS = 250;
constexpr std::uint32_t UPLOAD_ACK_TIMEOUT_MS = 1500;
constexpr std::uint32_t SWITCH_DEBOUNCE_MS = TERMINAL_SWITCH_DEBOUNCE_MS;
constexpr int FADER_RAW_MIN = TERMINAL_FADER_RAW_MIN;
constexpr int FADER_RAW_MAX = TERMINAL_FADER_RAW_MAX;
constexpr int FADER_DEADBAND_PERCENT = TERMINAL_FADER_DEADBAND_PERCENT;
constexpr bool FADER_ADC_ENABLED = TERMINAL_FADER_ADC_ENABLED != 0;
constexpr std::array<int, TERMINAL_LANE_COUNT> FADER_ADC_PINS = {
    TERMINAL_FADER_LANE1_ADC_PIN,
    TERMINAL_FADER_LANE2_ADC_PIN,
    TERMINAL_FADER_LANE3_ADC_PIN,
    TERMINAL_FADER_LANE4_ADC_PIN,
    TERMINAL_FADER_LANE5_ADC_PIN};
constexpr int ENCODER_DEGREES_PER_DETENT = TERMINAL_ENCODER_DEGREES_PER_DETENT;
constexpr int CHAIN_RX_PIN = TERMINAL_CHAIN_RX_PIN;
constexpr int CHAIN_TX_PIN = TERMINAL_CHAIN_TX_PIN;
constexpr bool CHAIN_UART_CONFIGURED = CHAIN_RX_PIN >= 0 && CHAIN_TX_PIN >= 0;
constexpr bool CHAIN_UART_REQUIRED = TERMINAL_REQUIRE_CHAIN_UART != 0;
constexpr int CHAIN_BAUD = TERMINAL_CHAIN_BAUD;
constexpr bool CHAIN_UART_SMOKE = TERMINAL_CHAIN_UART_SMOKE != 0;
constexpr bool CHAIN_UART_SELECT_PAHUB = TERMINAL_CHAIN_UART_SELECT_PAHUB != 0;
constexpr int CHAIN_PAHUB_ADDRESS = TERMINAL_CHAIN_PAHUB_ADDRESS;
constexpr int CHAIN_PAHUB_CHANNEL = TERMINAL_CHAIN_PAHUB_CHANNEL;
constexpr int CHAIN_PAHUB_SDA_PIN = TERMINAL_CHAIN_PAHUB_SDA_PIN;
constexpr int CHAIN_PAHUB_SCL_PIN = TERMINAL_CHAIN_PAHUB_SCL_PIN;
constexpr bool EXTERNAL_OLED_ENABLED = TERMINAL_EXTERNAL_OLED_ENABLED != 0;
constexpr int EXTERNAL_OLED_SDA_PIN = TERMINAL_EXTERNAL_OLED_SDA_PIN;
constexpr int EXTERNAL_OLED_SCL_PIN = TERMINAL_EXTERNAL_OLED_SCL_PIN;
constexpr int EXTERNAL_OLED_I2C_ADDRESS = TERMINAL_EXTERNAL_OLED_I2C_ADDRESS;
constexpr int EXTERNAL_OLED_I2C_PORT = TERMINAL_EXTERNAL_OLED_I2C_PORT;
constexpr int EXTERNAL_OLED_I2C_FREQ = TERMINAL_EXTERNAL_OLED_I2C_FREQ;
constexpr bool EXTERNAL_OLED_DRIVER_M5UNITGLASS2 = TERMINAL_EXTERNAL_OLED_DRIVER_M5UNITGLASS2 != 0;
constexpr bool EXTERNAL_OLED_DRIVER_SSD1309 = TERMINAL_EXTERNAL_OLED_DRIVER_SSD1309 != 0;
constexpr bool EXTERNAL_OLED_LIVE_SINK_CONFIRMED = TERMINAL_EXTERNAL_OLED_LIVE_SINK_CONFIRMED != 0;
constexpr bool EXTERNAL_OLED_I2C_SCAN_SMOKE = TERMINAL_EXTERNAL_OLED_I2C_SCAN_SMOKE != 0;
constexpr bool EXTERNAL_OLED_DRAW_SMOKE = TERMINAL_EXTERNAL_OLED_DRAW_SMOKE != 0;
constexpr bool EXTERNAL_OLED_SELECT_PAHUB = TERMINAL_EXTERNAL_OLED_SELECT_PAHUB != 0;
constexpr int EXTERNAL_OLED_PAHUB_ADDRESS = TERMINAL_EXTERNAL_OLED_PAHUB_ADDRESS;
constexpr int EXTERNAL_OLED_PAHUB_CHANNEL = TERMINAL_EXTERNAL_OLED_PAHUB_CHANNEL;
constexpr bool I2C_SCAN_PAHUB_CHANNELS = TERMINAL_I2C_SCAN_PAHUB_CHANNELS != 0;
constexpr bool EXTERNAL_OLED_I2C_CONFIGURED =
    EXTERNAL_OLED_ENABLED || EXTERNAL_OLED_I2C_SCAN_SMOKE || EXTERNAL_OLED_DRAW_SMOKE;
constexpr int UPLOAD_SWITCH_PIN = TERMINAL_UPLOAD_SWITCH_PIN;      // wiring open by default
constexpr int SIM_FIRE_SWITCH_PIN = TERMINAL_SIM_FIRE_SWITCH_PIN;  // wiring open by default
constexpr int activePin(bool enabled, int pin) {
    return enabled ? pin : -1;
}
constexpr std::size_t CONFIGURED_GPIO_PIN_COUNT = 2 + TERMINAL_LANE_COUNT + 2 + 2;
constexpr int CONFIGURED_GPIO_PINS[CONFIGURED_GPIO_PIN_COUNT] = {
    UPLOAD_SWITCH_PIN,
    SIM_FIRE_SWITCH_PIN,
    activePin(FADER_ADC_ENABLED, TERMINAL_FADER_LANE1_ADC_PIN),
    activePin(FADER_ADC_ENABLED, TERMINAL_FADER_LANE2_ADC_PIN),
    activePin(FADER_ADC_ENABLED, TERMINAL_FADER_LANE3_ADC_PIN),
    activePin(FADER_ADC_ENABLED, TERMINAL_FADER_LANE4_ADC_PIN),
    activePin(FADER_ADC_ENABLED, TERMINAL_FADER_LANE5_ADC_PIN),
    activePin(CHAIN_UART_CONFIGURED, CHAIN_RX_PIN),
    activePin(CHAIN_UART_CONFIGURED, CHAIN_TX_PIN),
    activePin(EXTERNAL_OLED_I2C_CONFIGURED, EXTERNAL_OLED_SDA_PIN),
    activePin(EXTERNAL_OLED_I2C_CONFIGURED, EXTERNAL_OLED_SCL_PIN),
};

constexpr bool configuredPinsShare(int left, int right) {
    return left >= 0 && right >= 0 && left == right;
}

constexpr bool configuredPinIsChain(std::size_t index) {
    return index == 7 || index == 8;
}

constexpr bool configuredPinIsExternalOled(std::size_t index) {
    return index == 9 || index == 10;
}

constexpr bool configuredPinsShareAllowed(int pin) {
    return pin >= 0 && CHAIN_UART_SELECT_PAHUB && EXTERNAL_OLED_SELECT_PAHUB &&
           (pin == CHAIN_RX_PIN || pin == CHAIN_TX_PIN) &&
           (pin == EXTERNAL_OLED_SDA_PIN || pin == EXTERNAL_OLED_SCL_PIN);
}

constexpr bool configuredPinsShareAllowedAt(std::size_t left, std::size_t right) {
    return CONFIGURED_GPIO_PINS[left] == CONFIGURED_GPIO_PINS[right] &&
           configuredPinsShareAllowed(CONFIGURED_GPIO_PINS[left]) &&
           ((configuredPinIsChain(left) && configuredPinIsExternalOled(right)) ||
            (configuredPinIsExternalOled(left) && configuredPinIsChain(right)));
}

constexpr bool configuredPinsAreUniqueFrom(std::size_t left, std::size_t right) {
    return left >= CONFIGURED_GPIO_PIN_COUNT
               ? true
               : right >= CONFIGURED_GPIO_PIN_COUNT
                     ? configuredPinsAreUniqueFrom(left + 1, left + 2)
                     : configuredPinsShare(CONFIGURED_GPIO_PINS[left], CONFIGURED_GPIO_PINS[right])
                           ? (configuredPinsShareAllowedAt(left, right)
                                  ? configuredPinsAreUniqueFrom(left, right + 1)
                                  : false)
                           : configuredPinsAreUniqueFrom(left, right + 1);
}

constexpr bool configuredPinsAreUnique() {
    return configuredPinsAreUniqueFrom(0, 1);
}

static_assert(USB_SETUP_BAUD > 0, "USB setup baud must be positive");
static_assert(TERMINAL_LANE_COUNT == terminal_hardware_topology::CONTROL_LANE_COUNT,
              "configured lane count must match the planned hardware topology");
static_assert(terminal_hardware_topology::UNIT_FADER_COUNT == TERMINAL_LANE_COUNT,
              "configured lane count must have one Unit Fader per lane");
static_assert(terminal_hardware_topology::CHAIN_ENCODER_COUNT == TERMINAL_LANE_COUNT,
              "configured lane count must have one Chain Encoder per lane");
static_assert(!terminal_hardware_topology::TERMINAL_HAS_LORA_MODULE,
              "Terminal config must stay radio-free");
static_assert(USB_LINE_MAX >= sizeof("SETUP_ERR 9999") - 1, "USB reply line buffer must fit setup replies");
static_assert(UPLOAD_ACK_TIMEOUT_MS > 0, "upload ACK timeout must be positive");
static_assert(SWITCH_DEBOUNCE_MS <= 1000, "switch debounce must stay within a bring-up-safe range");
static_assert(FADER_RAW_MIN != FADER_RAW_MAX, "fader raw calibration must have non-zero span");
static_assert(FADER_DEADBAND_PERCENT >= 0 && FADER_DEADBAND_PERCENT <= 20,
              "fader deadband must stay within a bring-up-safe range");
static_assert(!FADER_ADC_ENABLED ||
                  (TERMINAL_FADER_LANE1_ADC_PIN >= 0 && TERMINAL_FADER_LANE2_ADC_PIN >= 0 &&
                   TERMINAL_FADER_LANE3_ADC_PIN >= 0 && TERMINAL_FADER_LANE4_ADC_PIN >= 0 &&
                   TERMINAL_FADER_LANE5_ADC_PIN >= 0),
              "all fader ADC pins must be configured when fader ADC is enabled");
static_assert(ENCODER_DEGREES_PER_DETENT > 0 && ENCODER_DEGREES_PER_DETENT <= 90,
              "encoder detent scale must stay within a bring-up-safe range");
static_assert(CHAIN_BAUD > 0, "chain UART baud must be positive");
static_assert((CHAIN_RX_PIN < 0 && CHAIN_TX_PIN < 0) || (CHAIN_RX_PIN >= 0 && CHAIN_TX_PIN >= 0),
              "chain UART RX/TX pins must be configured together");
static_assert(!CHAIN_UART_REQUIRED || CHAIN_UART_CONFIGURED,
              "chain UART pins must be configured when the terminal hardware build requires Chain Encoder input");
static_assert(!CHAIN_UART_SMOKE || CHAIN_UART_CONFIGURED,
              "chain UART smoke requires RX/TX pins");
static_assert(!CHAIN_UART_CONFIGURED || CHAIN_RX_PIN != CHAIN_TX_PIN,
              "chain UART RX/TX pins must not share a configured pin");
static_assert(!CHAIN_UART_SELECT_PAHUB || (CHAIN_PAHUB_SDA_PIN >= 0 && CHAIN_PAHUB_SCL_PIN >= 0),
              "chain UART PaHUB select requires SDA/SCL pins");
static_assert(!CHAIN_UART_SELECT_PAHUB || CHAIN_PAHUB_SDA_PIN != CHAIN_PAHUB_SCL_PIN,
              "chain UART PaHUB select SDA/SCL pins must not share a configured pin");
static_assert(CHAIN_PAHUB_ADDRESS >= 0x03 && CHAIN_PAHUB_ADDRESS <= 0x77,
              "chain UART PaHUB address must be a 7-bit address");
static_assert(CHAIN_PAHUB_CHANNEL >= 0 && CHAIN_PAHUB_CHANNEL < terminal_hardware_topology::PAHUB_PORT_COUNT,
              "chain UART PaHUB channel must be a valid primary mux port");
static_assert(!EXTERNAL_OLED_ENABLED || (EXTERNAL_OLED_SDA_PIN >= 0 && EXTERNAL_OLED_SCL_PIN >= 0),
              "external OLED SDA/SCL pins must be configured when OLED is enabled");
static_assert(!EXTERNAL_OLED_I2C_SCAN_SMOKE || (EXTERNAL_OLED_SDA_PIN >= 0 && EXTERNAL_OLED_SCL_PIN >= 0),
              "external OLED I2C scan requires SDA/SCL pins");
static_assert(!EXTERNAL_OLED_DRAW_SMOKE || (EXTERNAL_OLED_SDA_PIN >= 0 && EXTERNAL_OLED_SCL_PIN >= 0),
              "external OLED draw smoke requires SDA/SCL pins");
static_assert(!I2C_SCAN_PAHUB_CHANNELS || EXTERNAL_OLED_I2C_SCAN_SMOKE,
              "PaHUB channel scan requires the I2C scan smoke environment");
static_assert(!(EXTERNAL_OLED_I2C_SCAN_SMOKE && EXTERNAL_OLED_ENABLED),
              "external OLED I2C scan smoke must not enable the display sink");
static_assert(!(EXTERNAL_OLED_DRAW_SMOKE && EXTERNAL_OLED_ENABLED),
              "external OLED draw smoke must not enable the display sink");
static_assert(!EXTERNAL_OLED_ENABLED || EXTERNAL_OLED_DRIVER_M5UNITGLASS2 || EXTERNAL_OLED_DRIVER_SSD1309,
              "external OLED enabled requires an explicit supported driver selection");
static_assert(!EXTERNAL_OLED_ENABLED || EXTERNAL_OLED_LIVE_SINK_CONFIRMED,
              "external OLED live sink requires bench confirmation");
static_assert(!EXTERNAL_OLED_I2C_CONFIGURED || EXTERNAL_OLED_SDA_PIN != EXTERNAL_OLED_SCL_PIN,
              "external OLED SDA/SCL pins must not share a configured pin");
static_assert(!EXTERNAL_OLED_SELECT_PAHUB || (EXTERNAL_OLED_SDA_PIN >= 0 && EXTERNAL_OLED_SCL_PIN >= 0),
              "external OLED PaHUB select requires SDA/SCL pins");
static_assert(EXTERNAL_OLED_I2C_ADDRESS >= 0x03 && EXTERNAL_OLED_I2C_ADDRESS <= 0x77,
              "external OLED I2C address must be a 7-bit address");
static_assert(EXTERNAL_OLED_PAHUB_ADDRESS >= 0x03 && EXTERNAL_OLED_PAHUB_ADDRESS <= 0x77,
              "external OLED PaHUB address must be a 7-bit address");
static_assert(EXTERNAL_OLED_PAHUB_CHANNEL >= 0 &&
                  EXTERNAL_OLED_PAHUB_CHANNEL < terminal_hardware_topology::PAHUB_PORT_COUNT,
              "external OLED PaHUB channel must be a valid primary mux port");
static_assert(EXTERNAL_OLED_I2C_PORT >= 0 && EXTERNAL_OLED_I2C_PORT <= 1,
              "external OLED I2C port must be 0 or 1");
static_assert(EXTERNAL_OLED_I2C_FREQ > 0 && EXTERNAL_OLED_I2C_FREQ <= 1000000,
              "external OLED I2C frequency must stay within a bring-up-safe range");
static_assert(UPLOAD_SWITCH_PIN < 0 || SIM_FIRE_SWITCH_PIN < 0 || UPLOAD_SWITCH_PIN != SIM_FIRE_SWITCH_PIN,
              "upload and sim-fire switches must not share a configured pin");
static_assert(configuredPinsAreUnique(),
              "configured shared Grove pins require explicit PaHUB routing");

}  // namespace terminal_config
