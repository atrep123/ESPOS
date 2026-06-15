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

#ifndef TERMINAL_FADER_PBHUB_ENABLED
#define TERMINAL_FADER_PBHUB_ENABLED 0
#endif

#ifndef TERMINAL_FADER_PBHUB_RGB_ENABLED
#define TERMINAL_FADER_PBHUB_RGB_ENABLED TERMINAL_FADER_PBHUB_ENABLED
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

#ifndef TERMINAL_PROP_LINK_SMOKE
#define TERMINAL_PROP_LINK_SMOKE 0
#endif

#ifndef TERMINAL_SETUP_TRANSPORT_USB
#define TERMINAL_SETUP_TRANSPORT_USB 1
#endif

#ifndef TERMINAL_SETUP_TRANSPORT_PROP_LINK
#define TERMINAL_SETUP_TRANSPORT_PROP_LINK 0
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

#ifndef TERMINAL_PBHUB_I2C_ADDRESS
#define TERMINAL_PBHUB_I2C_ADDRESS 0x61
#endif

#ifndef TERMINAL_PBHUB_I2C_PORT
#define TERMINAL_PBHUB_I2C_PORT 0
#endif

#ifndef TERMINAL_PBHUB_I2C_FREQ
#define TERMINAL_PBHUB_I2C_FREQ 400000
#endif

#ifndef TERMINAL_PBHUB_SDA_PIN
#define TERMINAL_PBHUB_SDA_PIN 9
#endif

#ifndef TERMINAL_PBHUB_SCL_PIN
#define TERMINAL_PBHUB_SCL_PIN 10
#endif

#ifndef TERMINAL_PBHUB_SELECT_PAHUB
#define TERMINAL_PBHUB_SELECT_PAHUB 1
#endif

#ifndef TERMINAL_PBHUB_PAHUB_ADDRESS
#define TERMINAL_PBHUB_PAHUB_ADDRESS 0x70
#endif

#ifndef TERMINAL_PBHUB_PAHUB_CHANNEL
#define TERMINAL_PBHUB_PAHUB_CHANNEL 5
#endif

#ifndef TERMINAL_PBHUB_RGB_MAX_BRIGHTNESS
#define TERMINAL_PBHUB_RGB_MAX_BRIGHTNESS 24
#endif

#ifndef TERMINAL_I2C_SCAN_PAHUB_CHANNELS
#define TERMINAL_I2C_SCAN_PAHUB_CHANNELS 0
#endif

#ifndef TERMINAL_PROP_LINK_RX_PIN
#define TERMINAL_PROP_LINK_RX_PIN -1
#endif

#ifndef TERMINAL_PROP_LINK_TX_PIN
#define TERMINAL_PROP_LINK_TX_PIN -1
#endif

#ifndef TERMINAL_PROP_LINK_BAUD
#define TERMINAL_PROP_LINK_BAUD 115200
#endif

#ifndef TERMINAL_UPLOAD_ACK_TIMEOUT_MS
#define TERMINAL_UPLOAD_ACK_TIMEOUT_MS 4000
#endif

// M5StickS3 Terminal setup controller. It has no radio module; setup traffic is
// a build-selected local setup link to the prop-side service.
constexpr int USB_SETUP_BAUD = 115200;
constexpr std::uint16_t USB_LINE_MAX = 160;
constexpr std::uint8_t TERMINAL_LANE_COUNT = 5;
constexpr std::uint32_t STATUS_REDRAW_MS = 250;
constexpr std::uint32_t UPLOAD_ACK_TIMEOUT_MS = TERMINAL_UPLOAD_ACK_TIMEOUT_MS;
constexpr std::uint32_t SWITCH_DEBOUNCE_MS = TERMINAL_SWITCH_DEBOUNCE_MS;
constexpr int FADER_RAW_MIN = TERMINAL_FADER_RAW_MIN;
constexpr int FADER_RAW_MAX = TERMINAL_FADER_RAW_MAX;
constexpr int FADER_DEADBAND_PERCENT = TERMINAL_FADER_DEADBAND_PERCENT;
constexpr bool FADER_ADC_ENABLED = TERMINAL_FADER_ADC_ENABLED != 0;
constexpr bool FADER_PBHUB_ENABLED = TERMINAL_FADER_PBHUB_ENABLED != 0;
constexpr bool FADER_PBHUB_RGB_ENABLED = TERMINAL_FADER_PBHUB_RGB_ENABLED != 0;
constexpr std::array<int, TERMINAL_LANE_COUNT> FADER_ADC_PINS = {
    TERMINAL_FADER_LANE1_ADC_PIN,
    TERMINAL_FADER_LANE2_ADC_PIN,
    TERMINAL_FADER_LANE3_ADC_PIN,
    TERMINAL_FADER_LANE4_ADC_PIN,
    TERMINAL_FADER_LANE5_ADC_PIN};
constexpr std::array<std::uint8_t, TERMINAL_LANE_COUNT> PBHUB_FADER_PORTS = {
    terminal_hardware_topology::PBHUB_PORT_POT1,
    terminal_hardware_topology::PBHUB_PORT_POT2,
    terminal_hardware_topology::PBHUB_PORT_POT3,
    terminal_hardware_topology::PBHUB_PORT_POT4,
    terminal_hardware_topology::PBHUB_PORT_POT5};
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
constexpr int PBHUB_I2C_ADDRESS = TERMINAL_PBHUB_I2C_ADDRESS;
constexpr int PBHUB_I2C_PORT = TERMINAL_PBHUB_I2C_PORT;
constexpr int PBHUB_I2C_FREQ = TERMINAL_PBHUB_I2C_FREQ;
constexpr int PBHUB_SDA_PIN = TERMINAL_PBHUB_SDA_PIN;
constexpr int PBHUB_SCL_PIN = TERMINAL_PBHUB_SCL_PIN;
constexpr bool PBHUB_SELECT_PAHUB = TERMINAL_PBHUB_SELECT_PAHUB != 0;
constexpr int PBHUB_PAHUB_ADDRESS = TERMINAL_PBHUB_PAHUB_ADDRESS;
constexpr int PBHUB_PAHUB_CHANNEL = TERMINAL_PBHUB_PAHUB_CHANNEL;
constexpr int PBHUB_RGB_MAX_BRIGHTNESS = TERMINAL_PBHUB_RGB_MAX_BRIGHTNESS;
constexpr bool I2C_SCAN_PAHUB_CHANNELS = TERMINAL_I2C_SCAN_PAHUB_CHANNELS != 0;
constexpr bool SETUP_TRANSPORT_USB = TERMINAL_SETUP_TRANSPORT_USB != 0;
constexpr bool SETUP_TRANSPORT_PROP_LINK = TERMINAL_SETUP_TRANSPORT_PROP_LINK != 0;
constexpr bool PROP_LINK_SMOKE = TERMINAL_PROP_LINK_SMOKE != 0;
constexpr int PROP_LINK_RX_PIN = TERMINAL_PROP_LINK_RX_PIN;
constexpr int PROP_LINK_TX_PIN = TERMINAL_PROP_LINK_TX_PIN;
constexpr int PROP_LINK_BAUD = TERMINAL_PROP_LINK_BAUD;
constexpr bool PROP_LINK_CONFIGURED = PROP_LINK_RX_PIN >= 0 && PROP_LINK_TX_PIN >= 0;
constexpr bool EXTERNAL_OLED_I2C_CONFIGURED =
    EXTERNAL_OLED_ENABLED || EXTERNAL_OLED_I2C_SCAN_SMOKE || EXTERNAL_OLED_DRAW_SMOKE;
constexpr bool PBHUB_I2C_CONFIGURED = FADER_PBHUB_ENABLED || FADER_PBHUB_RGB_ENABLED;
constexpr int UPLOAD_SWITCH_PIN = TERMINAL_UPLOAD_SWITCH_PIN;      // wiring open by default
constexpr int SIM_FIRE_SWITCH_PIN = TERMINAL_SIM_FIRE_SWITCH_PIN;  // wiring open by default
constexpr int activePin(bool enabled, int pin) {
    return enabled ? pin : -1;
}
constexpr std::size_t CONFIGURED_GPIO_PIN_COUNT = 2 + TERMINAL_LANE_COUNT + 2 + 2 + 2 + 2;
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
    activePin(PROP_LINK_CONFIGURED, PROP_LINK_RX_PIN),
    activePin(PROP_LINK_CONFIGURED, PROP_LINK_TX_PIN),
    activePin(PBHUB_I2C_CONFIGURED, PBHUB_SDA_PIN),
    activePin(PBHUB_I2C_CONFIGURED, PBHUB_SCL_PIN),
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

constexpr bool configuredPinIsPbHub(std::size_t index) {
    return index == 13 || index == 14;
}

constexpr bool configuredPinIsPahubRouted(std::size_t index) {
    return (configuredPinIsChain(index) && CHAIN_UART_SELECT_PAHUB) ||
           (configuredPinIsExternalOled(index) && EXTERNAL_OLED_SELECT_PAHUB) ||
           (configuredPinIsPbHub(index) && PBHUB_SELECT_PAHUB);
}

constexpr int PAHUB_ROLE_NONE = 0;
constexpr int PAHUB_ROLE_CHAIN = 1;
constexpr int PAHUB_ROLE_EXTERNAL_OLED = 2;
constexpr int PAHUB_ROLE_PBHUB = 3;

constexpr int configuredPahubRoleFor(std::size_t index) {
    return CONFIGURED_GPIO_PINS[index] < 0
               ? PAHUB_ROLE_NONE
               : configuredPinIsChain(index) && CHAIN_UART_SELECT_PAHUB
                     ? PAHUB_ROLE_CHAIN
                     : configuredPinIsExternalOled(index) && EXTERNAL_OLED_SELECT_PAHUB
                           ? PAHUB_ROLE_EXTERNAL_OLED
                           : configuredPinIsPbHub(index) && PBHUB_SELECT_PAHUB
                                 ? PAHUB_ROLE_PBHUB
                                 : PAHUB_ROLE_NONE;
}

constexpr int configuredPahubAddressFor(std::size_t index) {
    return configuredPinIsChain(index) ? CHAIN_PAHUB_ADDRESS
           : configuredPinIsExternalOled(index) ? EXTERNAL_OLED_PAHUB_ADDRESS
           : configuredPinIsPbHub(index) ? PBHUB_PAHUB_ADDRESS
                                         : -1;
}

constexpr int configuredPahubChannelFor(std::size_t index) {
    return configuredPinIsChain(index) ? CHAIN_PAHUB_CHANNEL
           : configuredPinIsExternalOled(index) ? EXTERNAL_OLED_PAHUB_CHANNEL
           : configuredPinIsPbHub(index) ? PBHUB_PAHUB_CHANNEL
                                         : -1;
}

constexpr bool configuredPahubChannelsShare(std::size_t left, std::size_t right) {
    return configuredPahubRoleFor(left) != PAHUB_ROLE_NONE &&
           configuredPahubRoleFor(right) != PAHUB_ROLE_NONE &&
           configuredPahubRoleFor(left) != configuredPahubRoleFor(right) &&
           configuredPahubAddressFor(left) == configuredPahubAddressFor(right) &&
           configuredPahubChannelFor(left) == configuredPahubChannelFor(right);
}

constexpr bool configuredPahubChannelsAreUniqueFrom(std::size_t left, std::size_t right) {
    return left >= CONFIGURED_GPIO_PIN_COUNT
               ? true
               : right >= CONFIGURED_GPIO_PIN_COUNT
                     ? configuredPahubChannelsAreUniqueFrom(left + 1, left + 2)
                     : configuredPahubChannelsShare(left, right)
                           ? false
                           : configuredPahubChannelsAreUniqueFrom(left, right + 1);
}

constexpr bool configuredPahubChannelsAreUnique() {
    return configuredPahubChannelsAreUniqueFrom(0, 1);
}

constexpr bool configuredPinsShareAllowedAt(std::size_t left, std::size_t right) {
    return CONFIGURED_GPIO_PINS[left] == CONFIGURED_GPIO_PINS[right] &&
           CONFIGURED_GPIO_PINS[left] >= 0 &&
           configuredPinIsPahubRouted(left) &&
           configuredPinIsPahubRouted(right);
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
static_assert(!(FADER_ADC_ENABLED && FADER_PBHUB_ENABLED),
              "direct ADC and PbHUB fader readers are mutually exclusive");
static_assert(!FADER_ADC_ENABLED ||
                  (TERMINAL_FADER_LANE1_ADC_PIN >= 0 && TERMINAL_FADER_LANE2_ADC_PIN >= 0 &&
                   TERMINAL_FADER_LANE3_ADC_PIN >= 0 && TERMINAL_FADER_LANE4_ADC_PIN >= 0 &&
                   TERMINAL_FADER_LANE5_ADC_PIN >= 0),
              "all fader ADC pins must be configured when fader ADC is enabled");
static_assert(!FADER_PBHUB_ENABLED || PBHUB_I2C_CONFIGURED,
              "PbHUB fader ADC requires PbHUB I2C configuration");
static_assert(!FADER_PBHUB_RGB_ENABLED || PBHUB_I2C_CONFIGURED,
              "PbHUB fader RGB reflection requires PbHUB I2C configuration");
static_assert(ENCODER_DEGREES_PER_DETENT > 0 && ENCODER_DEGREES_PER_DETENT <= 90,
              "encoder detent scale must stay within a bring-up-safe range");
static_assert(CHAIN_BAUD > 0, "chain UART baud must be positive");
static_assert((CHAIN_RX_PIN < 0 && CHAIN_TX_PIN < 0) || (CHAIN_RX_PIN >= 0 && CHAIN_TX_PIN >= 0),
              "chain UART RX/TX pins must be configured together");
static_assert(!CHAIN_UART_REQUIRED || CHAIN_UART_CONFIGURED,
              "chain UART pins must be configured when the terminal hardware build requires Chain Encoder input");
static_assert(!CHAIN_UART_SMOKE || CHAIN_UART_CONFIGURED,
              "chain UART smoke requires RX/TX pins");
static_assert(SETUP_TRANSPORT_USB != SETUP_TRANSPORT_PROP_LINK,
              "setup transport must select exactly one transport");
static_assert(!PROP_LINK_SMOKE || PROP_LINK_CONFIGURED,
              "prop link smoke requires RX/TX pins");
static_assert(!SETUP_TRANSPORT_PROP_LINK || PROP_LINK_CONFIGURED,
              "prop-link setup transport requires RX/TX pins");
static_assert((PROP_LINK_RX_PIN < 0 && PROP_LINK_TX_PIN < 0) ||
                  (PROP_LINK_RX_PIN >= 0 && PROP_LINK_TX_PIN >= 0),
              "prop link RX/TX pins must be configured together");
static_assert(!PROP_LINK_CONFIGURED || PROP_LINK_RX_PIN != PROP_LINK_TX_PIN,
              "prop link RX/TX pins must not share a configured pin");
static_assert(PROP_LINK_BAUD > 0, "prop link baud must be positive");
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
static_assert(PBHUB_I2C_ADDRESS >= 0x03 && PBHUB_I2C_ADDRESS <= 0x77,
              "PbHUB I2C address must be a 7-bit address");
static_assert(PBHUB_I2C_ADDRESS == terminal_hardware_topology::PBHUB_I2C_ADDRESS,
              "PbHUB I2C address must match the topology contract");
static_assert(PBHUB_I2C_PORT >= 0 && PBHUB_I2C_PORT <= 1,
              "PbHUB I2C port must be 0 or 1");
static_assert(PBHUB_I2C_FREQ > 0 && PBHUB_I2C_FREQ <= 1000000,
              "PbHUB I2C frequency must stay within a bring-up-safe range");
static_assert(!PBHUB_I2C_CONFIGURED || (PBHUB_SDA_PIN >= 0 && PBHUB_SCL_PIN >= 0),
              "PbHUB I2C requires SDA/SCL pins");
static_assert(!PBHUB_I2C_CONFIGURED || PBHUB_SDA_PIN != PBHUB_SCL_PIN,
              "PbHUB SDA/SCL pins must not share a configured pin");
static_assert(!PBHUB_I2C_CONFIGURED || PBHUB_SELECT_PAHUB,
              "PbHUB must remain behind the primary PaHUB mux in this topology");
static_assert(PBHUB_PAHUB_ADDRESS >= 0x03 && PBHUB_PAHUB_ADDRESS <= 0x77,
              "PbHUB parent PaHUB address must be a 7-bit address");
static_assert(PBHUB_PAHUB_CHANNEL >= 0 &&
                  PBHUB_PAHUB_CHANNEL < terminal_hardware_topology::PAHUB_PORT_COUNT,
              "PbHUB parent PaHUB channel must be a valid primary mux port");
static_assert(PBHUB_PAHUB_CHANNEL == terminal_hardware_topology::PRIMARY_PAHUB_PORT_PBHUB,
              "PbHUB parent PaHUB channel must match the topology contract");
static_assert(PBHUB_RGB_MAX_BRIGHTNESS >= 0 && PBHUB_RGB_MAX_BRIGHTNESS <= 64,
              "PbHUB RGB reflection brightness cap must stay within the bring-up power budget");
static_assert(PBHUB_FADER_PORTS[0] == terminal_hardware_topology::PBHUB_PORT_POT1 &&
                  PBHUB_FADER_PORTS[1] == terminal_hardware_topology::PBHUB_PORT_POT2 &&
                  PBHUB_FADER_PORTS[2] == terminal_hardware_topology::PBHUB_PORT_POT3 &&
                  PBHUB_FADER_PORTS[3] == terminal_hardware_topology::PBHUB_PORT_POT4 &&
                  PBHUB_FADER_PORTS[4] == terminal_hardware_topology::PBHUB_PORT_POT5,
              "PbHUB fader ports map logical LED lanes to Pot1-to-Pot5 order");
static_assert(UPLOAD_SWITCH_PIN < 0 || SIM_FIRE_SWITCH_PIN < 0 || UPLOAD_SWITCH_PIN != SIM_FIRE_SWITCH_PIN,
              "upload and sim-fire switches must not share a configured pin");
static_assert(configuredPinsAreUnique(),
              "configured shared Grove pins require explicit PaHUB routing");
static_assert(configuredPahubChannelsAreUnique(),
              "configured PaHUB-routed devices must use unique channels");

}  // namespace terminal_config
